"""
Monister Admin Config — Platform konfiguratsiya API endpoints.

Telegram bot tokenni saqlash, soha modullarini boshqarish,
agent sozlamalarini o'zgartirish.
"""

import json
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db, User
from auth import get_admin_user

router = APIRouter(prefix="/api/admin/config", tags=["admin-config"])

# Config file path
CONFIG_DIR = Path(__file__).parent.parent / "data"
CONFIG_FILE = CONFIG_DIR / "platform_config.json"


# ============== Pydantic Models ==============
class TelegramConfig(BaseModel):
    bot_token: str = ""
    default_caption: str = "Monister AI orqali yuborildi"
    enabled: bool = False


class IndustryConfig(BaseModel):
    industry_id: str
    enabled: bool


class AgentConfig(BaseModel):
    model_name: str = ""
    auto_approve: bool = False
    max_recursion: int = 50
    system_prompt_override: str = ""


class PlatformConfig(BaseModel):
    telegram: TelegramConfig = TelegramConfig()
    industries: list[IndustryConfig] = []
    agent: AgentConfig = AgentConfig()


# ============== Config IO ==============
def load_config() -> dict:
    """Load platform config from JSON file."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_config(data: dict) -> None:
    """Save platform config to JSON file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ============== Endpoints ==============
@router.get("")
async def get_config(
    admin: User = Depends(get_admin_user),
):
    """Get full platform configuration."""
    config = load_config()
    # Mask telegram token for security
    if "telegram" in config and config["telegram"].get("bot_token"):
        token = config["telegram"]["bot_token"]
        config["telegram"]["bot_token_masked"] = f"{token[:8]}...{token[-4:]}" if len(token) > 12 else "***"
    return {"success": True, "config": config}


@router.put("")
async def update_config(
    config: PlatformConfig,
    admin: User = Depends(get_admin_user),
):
    """Update full platform configuration."""
    data = config.model_dump()
    save_config(data)

    # Apply telegram token immediately
    if config.telegram.bot_token:
        try:
            from telegram_bot import set_bot_token
            set_bot_token(config.telegram.bot_token)
        except Exception:
            pass

    return {"success": True, "message": "Konfiguratsiya saqlandi"}


# ============== Telegram Endpoints ==============
@router.put("/telegram")
async def update_telegram_config(
    tg_config: TelegramConfig,
    admin: User = Depends(get_admin_user),
):
    """Update Telegram bot configuration."""
    config = load_config()
    config["telegram"] = tg_config.model_dump()
    save_config(config)

    if tg_config.bot_token:
        try:
            from telegram_bot import set_bot_token
            set_bot_token(tg_config.bot_token)
        except Exception:
            pass

    return {"success": True, "message": "Telegram sozlamalari saqlandi"}


@router.post("/telegram/test")
async def test_telegram_token(
    tg_config: TelegramConfig,
    admin: User = Depends(get_admin_user),
):
    """Test if a Telegram bot token is valid."""
    if not tg_config.bot_token:
        raise HTTPException(400, "Bot token kiritilmagan")

    try:
        from telegram_bot import test_bot_token
        result = await test_bot_token(tg_config.bot_token)
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============== Industry Endpoints ==============
@router.get("/industries")
async def get_industries_config(
    admin: User = Depends(get_admin_user),
):
    """Get industry modules configuration."""
    try:
        from industry_modules import get_all_modules
        industries = get_all_modules()

        config = load_config()
        disabled = set()
        for ic in config.get("industries", []):
            if not ic.get("enabled", True):
                disabled.add(ic.get("industry_id"))

        result = []
        for ind in industries:
            result.append({
                **ind,
                "enabled": ind.get("id", "") not in disabled,
            })

        return {"success": True, "industries": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.put("/industries")
async def update_industries_config(
    industries: list[IndustryConfig],
    admin: User = Depends(get_admin_user),
):
    """Enable/disable industry modules."""
    config = load_config()
    config["industries"] = [ic.model_dump() for ic in industries]
    save_config(config)
    return {"success": True, "message": f"{len(industries)} soha sozlamasi saqlandi"}


# ============== Agent Config Endpoints ==============
@router.get("/agent")
async def get_agent_config(
    admin: User = Depends(get_admin_user),
):
    """Get agent configuration."""
    config = load_config()
    return {"success": True, "agent": config.get("agent", {})}


@router.put("/agent")
async def update_agent_config(
    agent_config: AgentConfig,
    admin: User = Depends(get_admin_user),
):
    """Update agent configuration."""
    config = load_config()
    config["agent"] = agent_config.model_dump()
    save_config(config)
    return {"success": True, "message": "Agent sozlamalari saqlandi"}
