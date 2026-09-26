"""
Monister Admin - Admin panel API endpoints.
"""

import os
import shutil
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pathlib import Path

from database import get_db, User, File, get_file_category
from auth import get_admin_user

router = APIRouter(prefix="/api/admin", tags=["admin"])


# Dashboard Stats
@router.get("/stats")
async def get_dashboard_stats(
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get dashboard statistics."""
    # User stats
    total_users = db.query(func.count(User.id)).scalar()
    active_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar()
    admin_users = db.query(func.count(User.id)).filter(User.is_admin == True).scalar()
    
    # File stats
    total_files = db.query(func.count(File.id)).scalar()
    total_storage = db.query(func.sum(File.size)).scalar() or 0
    
    # Files by type
    files_by_type = db.query(
        File.file_type, 
        func.count(File.id).label('count'),
        func.sum(File.size).label('size')
    ).group_by(File.file_type).all()
    
    # Recent users (last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)
    new_users_this_week = db.query(func.count(User.id)).filter(
        User.created_at >= week_ago
    ).scalar()
    
    # Recent files (last 7 days)
    new_files_this_week = db.query(func.count(File.id)).filter(
        File.created_at >= week_ago
    ).scalar()
    
    # Recent uploads (last 10)
    recent_files = db.query(File).order_by(File.created_at.desc()).limit(10).all()
    
    # Recent users (last 5)
    recent_users = db.query(User).order_by(User.created_at.desc()).limit(5).all()
    
    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "admins": admin_users,
            "new_this_week": new_users_this_week,
        },
        "files": {
            "total": total_files,
            "storage_bytes": total_storage,
            "storage_formatted": format_bytes(total_storage),
            "new_this_week": new_files_this_week,
            "by_type": [
                {"type": t, "count": c, "size": s or 0, "size_formatted": format_bytes(s or 0)}
                for t, c, s in files_by_type
            ],
        },
        "recent_files": [f.to_dict() for f in recent_files],
        "recent_users": [u.to_dict() for u in recent_users],
    }


# Users Management
@router.get("/users")
async def get_all_users(
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
):
    """Get all users with pagination and search."""
    query = db.query(User)
    
    if search:
        query = query.filter(
            (User.username.contains(search)) | 
            (User.email.contains(search))
        )
    
    total = query.count()
    users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
    
    # Add file stats to each user
    user_data = []
    for user in users:
        data = user.to_dict()
        data["files_count"] = db.query(func.count(File.id)).filter(File.user_id == user.id).scalar()
        data["storage_used"] = db.query(func.sum(File.size)).filter(File.user_id == user.id).scalar() or 0
        data["storage_formatted"] = format_bytes(data["storage_used"])
        user_data.append(data)
    
    return {
        "total": total,
        "users": user_data,
    }


@router.get("/users/{user_id}")
async def get_user_detail(
    user_id: int,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Get detailed user information."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    data = user.to_dict()
    
    # File breakdown
    files_by_type = db.query(
        File.file_type,
        func.count(File.id).label('count'),
        func.sum(File.size).label('size')
    ).filter(File.user_id == user_id).group_by(File.file_type).all()
    
    data["files_breakdown"] = [
        {"type": t, "count": c, "size": s or 0, "size_formatted": format_bytes(s or 0)}
        for t, c, s in files_by_type
    ]
    
    # Recent files
    recent_files = db.query(File).filter(
        File.user_id == user_id
    ).order_by(File.created_at.desc()).limit(20).all()
    data["recent_files"] = [f.to_dict() for f in recent_files]
    
    return data


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Delete a user and all their files."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    if user.username == "system":
        raise HTTPException(status_code=400, detail="Cannot delete system user")
    
    # Delete user's folder
    from config import settings
    user_folder = settings.data_dir / user.username
    if user_folder.exists():
        shutil.rmtree(user_folder)
    
    # Delete user (cascade deletes files in DB)
    db.delete(user)
    db.commit()
    
    return {"success": True, "message": f"User '{user.username}' deleted"}


@router.patch("/users/{user_id}/toggle-admin")
async def toggle_user_admin(
    user_id: int,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Toggle admin status for a user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot modify your own admin status")
    
    user.is_admin = not user.is_admin
    db.commit()
    
    return {"success": True, "is_admin": user.is_admin}


# Files Management
@router.get("/files")
async def get_all_files(
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user_id: Optional[int] = None,
    file_type: Optional[str] = None,
    search: Optional[str] = None,
):
    """Get all files with filtering."""
    query = db.query(File)
    
    if user_id:
        query = query.filter(File.user_id == user_id)
    
    if file_type:
        query = query.filter(File.file_type == file_type)
    
    if search:
        query = query.filter(
            (File.filename.contains(search)) |
            (File.original_name.contains(search))
        )
    
    total = query.count()
    files = query.order_by(File.created_at.desc()).offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "files": [f.to_dict() for f in files],
    }


@router.delete("/files/{file_id}")
async def delete_file(
    file_id: int,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Delete a file."""
    file = db.query(File).filter(File.id == file_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Delete physical file
    file_path = Path(file.path)
    if file_path.exists():
        file_path.unlink()
    
    # Delete from DB
    db.delete(file)
    db.commit()
    
    return {"success": True, "message": f"File '{file.original_name}' deleted"}


# Utilities
def format_bytes(size: int) -> str:
    """Format bytes to human readable."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"
