"""
Monister Deadline Tracker - Document deadline/renewal tracking.

Tracks:
- Document expiration dates
- Renewal deadlines
- Compliance filing deadlines
- Custom reminders

Provides:
- Upcoming deadline alerts
- Overdue notifications
- Calendar integration data
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum

from config import settings


class DeadlineStatus(str, Enum):
    ACTIVE = "active"
    UPCOMING = "upcoming"  # Within 7 days
    OVERDUE = "overdue"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class DeadlinePriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Deadline:
    """A tracked deadline."""
    id: str
    title: str
    title_uz: str
    description: str = ""
    document_type: str = ""
    industry_module: str = ""
    due_date: str = ""  # ISO format
    created_at: str = ""
    completed_at: str = ""
    status: DeadlineStatus = DeadlineStatus.ACTIVE
    priority: DeadlinePriority = DeadlinePriority.MEDIUM
    related_file: str = ""
    user_id: int = 0
    reminder_days: list[int] = field(default_factory=lambda: [7, 3, 1])
    tags: list[str] = field(default_factory=list)
    auto_renew: bool = False
    renew_days: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "title_uz": self.title_uz,
            "description": self.description,
            "document_type": self.document_type,
            "industry_module": self.industry_module,
            "due_date": self.due_date,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "status": self.status.value,
            "priority": self.priority.value,
            "related_file": self.related_file,
            "user_id": self.user_id,
            "tags": self.tags,
            "days_remaining": self.days_remaining,
            "is_overdue": self.is_overdue,
        }

    @property
    def days_remaining(self) -> int:
        """Days until deadline."""
        if not self.due_date:
            return -1
        try:
            due = datetime.fromisoformat(self.due_date)
            return (due - datetime.now()).days
        except Exception:
            return -1

    @property
    def is_overdue(self) -> bool:
        """Check if deadline has passed."""
        return self.days_remaining < 0

    def update_status(self):
        """Auto-update status based on dates."""
        if self.status in (DeadlineStatus.COMPLETED, DeadlineStatus.CANCELLED):
            return

        days = self.days_remaining
        if days < 0:
            self.status = DeadlineStatus.OVERDUE
            self.priority = DeadlinePriority.CRITICAL
        elif days <= 7:
            self.status = DeadlineStatus.UPCOMING
            if days <= 1:
                self.priority = DeadlinePriority.CRITICAL
            elif days <= 3:
                self.priority = DeadlinePriority.HIGH


class DeadlineTracker:
    """Manages deadline tracking and notifications."""

    def __init__(self):
        self.deadlines: dict[str, Deadline] = {}
        self._data_dir = settings.data_dir / "deadlines"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._load()

    def add(self, deadline: Deadline) -> Deadline:
        """Add a new deadline."""
        if not deadline.created_at:
            deadline.created_at = datetime.now().isoformat()
        deadline.update_status()
        self.deadlines[deadline.id] = deadline
        self._save()
        return deadline

    def complete(self, deadline_id: str) -> Deadline | None:
        """Mark a deadline as completed."""
        dl = self.deadlines.get(deadline_id)
        if not dl:
            return None

        dl.status = DeadlineStatus.COMPLETED
        dl.completed_at = datetime.now().isoformat()

        # Auto-renew if configured
        if dl.auto_renew and dl.renew_days > 0:
            new_dl = Deadline(
                id=f"dl-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                title=dl.title,
                title_uz=dl.title_uz,
                description=dl.description,
                document_type=dl.document_type,
                industry_module=dl.industry_module,
                due_date=(datetime.now() + timedelta(days=dl.renew_days)).isoformat(),
                user_id=dl.user_id,
                tags=dl.tags,
                auto_renew=True,
                renew_days=dl.renew_days,
            )
            self.add(new_dl)

        self._save()
        return dl

    def cancel(self, deadline_id: str) -> bool:
        """Cancel a deadline."""
        dl = self.deadlines.get(deadline_id)
        if not dl:
            return False
        dl.status = DeadlineStatus.CANCELLED
        self._save()
        return True

    def get_upcoming(self, days: int = 30, user_id: int = None) -> list[dict]:
        """Get deadlines due within N days."""
        self._refresh_statuses()
        results = []
        for dl in self.deadlines.values():
            if dl.status in (DeadlineStatus.COMPLETED, DeadlineStatus.CANCELLED):
                continue
            if user_id and dl.user_id != user_id:
                continue
            if 0 <= dl.days_remaining <= days or dl.is_overdue:
                results.append(dl.to_dict())

        results.sort(key=lambda x: x.get("days_remaining", 999))
        return results

    def get_overdue(self, user_id: int = None) -> list[dict]:
        """Get all overdue deadlines."""
        self._refresh_statuses()
        results = []
        for dl in self.deadlines.values():
            if dl.status == DeadlineStatus.OVERDUE:
                if user_id and dl.user_id != user_id:
                    continue
                results.append(dl.to_dict())
        return results

    def get_all(self, user_id: int = None) -> list[dict]:
        """Get all active deadlines."""
        self._refresh_statuses()
        results = []
        for dl in self.deadlines.values():
            if dl.status in (DeadlineStatus.COMPLETED, DeadlineStatus.CANCELLED):
                continue
            if user_id and dl.user_id != user_id:
                continue
            results.append(dl.to_dict())
        results.sort(key=lambda x: x.get("days_remaining", 999))
        return results

    def get_alerts(self, user_id: int = None) -> list[dict]:
        """Generate alert messages for urgent deadlines."""
        self._refresh_statuses()
        alerts = []

        for dl in self.deadlines.values():
            if dl.status in (DeadlineStatus.COMPLETED, DeadlineStatus.CANCELLED):
                continue
            if user_id and dl.user_id != user_id:
                continue

            if dl.is_overdue:
                alerts.append({
                    "type": "overdue",
                    "level": "critical",
                    "message": f"⚠️ MUDDATI O'TGAN: {dl.title_uz} ({abs(dl.days_remaining)} kun oldin)",
                    "deadline": dl.to_dict(),
                })
            elif dl.days_remaining <= 1:
                alerts.append({
                    "type": "urgent",
                    "level": "critical",
                    "message": f"🔴 BUGUN/ERTAGA: {dl.title_uz}",
                    "deadline": dl.to_dict(),
                })
            elif dl.days_remaining <= 3:
                alerts.append({
                    "type": "warning",
                    "level": "high",
                    "message": f"🟡 {dl.days_remaining} kun qoldi: {dl.title_uz}",
                    "deadline": dl.to_dict(),
                })
            elif dl.days_remaining <= 7:
                alerts.append({
                    "type": "reminder",
                    "level": "medium",
                    "message": f"🔵 {dl.days_remaining} kun qoldi: {dl.title_uz}",
                    "deadline": dl.to_dict(),
                })

        alerts.sort(key=lambda x: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(x["level"], 4))
        return alerts

    def _refresh_statuses(self):
        """Update all deadline statuses."""
        for dl in self.deadlines.values():
            dl.update_status()

    def _save(self):
        """Persist all deadlines to disk."""
        try:
            data = {did: dl.to_dict() for did, dl in self.deadlines.items()}
            with open(self._data_dir / "deadlines.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Deadline save error: {e}")

    def _load(self):
        """Load deadlines from disk."""
        fpath = self._data_dir / "deadlines.json"
        if not fpath.exists():
            return
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            for did, d in data.items():
                dl = Deadline(
                    id=d["id"],
                    title=d["title"],
                    title_uz=d.get("title_uz", d["title"]),
                    description=d.get("description", ""),
                    document_type=d.get("document_type", ""),
                    industry_module=d.get("industry_module", ""),
                    due_date=d.get("due_date", ""),
                    created_at=d.get("created_at", ""),
                    completed_at=d.get("completed_at", ""),
                    status=DeadlineStatus(d.get("status", "active")),
                    priority=DeadlinePriority(d.get("priority", "medium")),
                    related_file=d.get("related_file", ""),
                    user_id=d.get("user_id", 0),
                    tags=d.get("tags", []),
                )
                self.deadlines[dl.id] = dl
        except Exception as e:
            print(f"Deadline load error: {e}")


# Global instance
deadline_tracker = DeadlineTracker()


# ============== Exports ==============
__all__ = [
    "Deadline",
    "DeadlineStatus",
    "DeadlinePriority",
    "DeadlineTracker",
    "deadline_tracker",
]
