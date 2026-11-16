"""Revocable device sessions. Only token digests are stored in PostgreSQL."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.models import utcnow


class MobileSession(db.Model):
    __tablename__ = "mobile_sessions"
    __table_args__ = (CheckConstraint("expires_at > created_at", name="positive_lifetime"),)
    token_hash: Mapped[str] = mapped_column(db.String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    auth_version: Mapped[int] = mapped_column()
    device_name: Mapped[str] = mapped_column(db.String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
