import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.notification import Notification

router = APIRouter()


class NotificationOut(BaseModel):
    id: uuid.UUID
    title: str
    message: str
    notification_type: str
    read: bool
    created_at: str

    model_config = {"from_attributes": True}


class UnreadCount(BaseModel):
    unread: int


@router.get("", response_model=list[NotificationOut])
async def list_notifications(
    unread_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Notification).order_by(Notification.created_at.desc()).limit(50)
    if unread_only:
        stmt = stmt.where(Notification.read == False)  # noqa: E712
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/count", response_model=UnreadCount)
async def unread_count(db: AsyncSession = Depends(get_db)):
    stmt = select(func.count()).select_from(Notification).where(Notification.read == False)  # noqa: E712
    result = await db.execute(stmt)
    count = result.scalar()
    return UnreadCount(unread=count or 0)


@router.post("/{notification_id}/read", status_code=200)
async def mark_as_read(notification_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    notification = await db.get(Notification, notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    notification.read = True
    await db.commit()
    return {"ok": True}


@router.delete("/{notification_id}", status_code=204)
async def delete_notification(notification_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    notification = await db.get(Notification, notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    await db.delete(notification)
    await db.commit()
