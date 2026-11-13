"""Persistent local import, receipt drafts and restaurant settings."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.models import TimestampMixin, utcnow


class ImportJob(TimestampMixin, db.Model):
    __tablename__ = "import_jobs"
    __table_args__ = (
        CheckConstraint("status IN ('uploaded','preview','confirmed')", name="valid_status"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    filename: Mapped[str] = mapped_column(db.String(180))
    file_hash: Mapped[str] = mapped_column(db.String(64), index=True)
    content: Mapped[bytes] = mapped_column(db.LargeBinary)
    status: Mapped[str] = mapped_column(db.String(20), default="uploaded")
    mode: Mapped[str | None] = mapped_column(db.String(20))
    sheet: Mapped[str | None] = mapped_column(db.String(100))
    mapping: Mapped[dict | None] = mapped_column(JSONB)
    preview: Mapped[list | None] = mapped_column(JSONB)
    errors: Mapped[list | None] = mapped_column(JSONB)
    fingerprint: Mapped[str | None] = mapped_column(db.String(64), unique=True)
    result: Mapped[dict | None] = mapped_column(JSONB)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    confirmed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    operation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("inventory_operations.id", ondelete="RESTRICT"), unique=True
    )


class ReceiptDraft(TimestampMixin, db.Model):
    __tablename__ = "inventory_receipt_drafts"
    __table_args__ = (
        CheckConstraint("status IN ('draft','confirmed','discarded')", name="valid_status"),
        CheckConstraint("revision > 0", name="positive_revision"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    payload: Mapped[dict] = mapped_column(JSONB)
    revision: Mapped[int] = mapped_column(default=1)
    status: Mapped[str] = mapped_column(db.String(20), default="draft")
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    operation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("inventory_operations.id", ondelete="RESTRICT"), unique=True
    )


class SystemSettings(db.Model):
    __tablename__ = "system_settings"
    __table_args__ = (
        CheckConstraint("id = 1 AND expiry_alert_days BETWEEN 1 AND 90", name="valid_settings"),
    )
    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    expiry_alert_days: Mapped[int] = mapped_column()
    updated_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
