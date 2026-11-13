import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from flask_login import UserMixin
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db

QTY = Numeric(18, 6)
MONEY = Numeric(18, 6)


def utcnow():
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, server_default=func.now()
    )


class User(UserMixin, TimestampMixin, db.Model):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('admin','manager','warehouse','cashier')", name="valid_role"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(db.String(100))
    email: Mapped[str] = mapped_column(db.String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(db.String(255))
    role: Mapped[str] = mapped_column(db.String(20))
    active: Mapped[bool] = mapped_column(default=True, server_default=db.true())
    auth_version: Mapped[int] = mapped_column(default=1, server_default="1")

    @property
    def is_active(self):
        return self.active

    def set_password(self, value):
        self.password_hash = generate_password_hash(value, method="scrypt")
        self.auth_version = (self.auth_version or 0) + 1

    def get_id(self):
        return f"{self.id}:{self.auth_version}"

    def check_password(self, value):
        return check_password_hash(self.password_hash, value)


class LoginThrottle(db.Model):
    __tablename__ = "login_throttles"
    key: Mapped[str] = mapped_column(db.String(64), primary_key=True)
    attempts: Mapped[int] = mapped_column(default=1)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    action: Mapped[str] = mapped_column(db.String(80))
    detail: Mapped[str] = mapped_column(db.Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )


class Unit(db.Model):
    __tablename__ = "measurement_units"
    __table_args__ = (
        CheckConstraint("dimension IN ('mass','volume','count')", name="dimension"),
        CheckConstraint("factor > 0", name="positive_factor"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(db.String(10), unique=True)
    name: Mapped[str] = mapped_column(db.String(50))
    dimension: Mapped[str] = mapped_column(db.String(10))
    factor: Mapped[Decimal] = mapped_column(QTY)


class Category(db.Model):
    __tablename__ = "ingredient_categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(db.String(100), unique=True)


class Supplier(TimestampMixin, db.Model):
    __tablename__ = "suppliers"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(db.String(150), unique=True)
    legal_name: Mapped[str | None] = mapped_column(db.String(200))
    contact: Mapped[str | None] = mapped_column(db.String(100))
    phone: Mapped[str | None] = mapped_column(db.String(30))
    email: Mapped[str | None] = mapped_column(db.String(254))
    address: Mapped[str | None] = mapped_column(db.Text)
    notes: Mapped[str | None] = mapped_column(db.Text)
    active: Mapped[bool] = mapped_column(default=True, server_default=db.true())


class Ingredient(TimestampMixin, db.Model):
    __tablename__ = "ingredients"
    __table_args__ = (
        CheckConstraint("minimum >= 0", name="minimum_nonnegative"),
        CheckConstraint("maximum IS NULL OR maximum >= minimum", name="maximum_valid"),
        CheckConstraint("reference_cost IS NULL OR reference_cost >= 0", name="cost_nonnegative"),
        Index("ix_ingredients_name_lower", func.lower(db.column("name")), unique=True),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str | None] = mapped_column(db.String(50), unique=True)
    name: Mapped[str] = mapped_column(db.String(150))
    description: Mapped[str | None] = mapped_column(db.Text)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("ingredient_categories.id", ondelete="RESTRICT"), index=True
    )
    unit_id: Mapped[int] = mapped_column(ForeignKey("measurement_units.id", ondelete="RESTRICT"))
    supplier_id: Mapped[int | None] = mapped_column(
        ForeignKey("suppliers.id", ondelete="RESTRICT"), index=True
    )
    minimum: Mapped[Decimal] = mapped_column(QTY, default=Decimal("0"))
    maximum: Mapped[Decimal | None] = mapped_column(QTY)
    reference_cost: Mapped[Decimal | None] = mapped_column(MONEY)
    active: Mapped[bool] = mapped_column(default=True, server_default=db.true())
    updated_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    category: Mapped[Category] = relationship(lazy="joined")
    unit: Mapped[Unit] = relationship(lazy="joined")
    supplier: Mapped[Supplier | None] = relationship(lazy="joined")


class Presentation(db.Model):
    __tablename__ = "purchase_presentations"
    __table_args__ = (
        CheckConstraint("base_quantity > 0", name="positive_quantity"),
        UniqueConstraint("ingredient_id", "name"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    ingredient_id: Mapped[int] = mapped_column(
        ForeignKey("ingredients.id", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(db.String(100))
    base_quantity: Mapped[Decimal] = mapped_column(QTY)


class Operation(db.Model):
    __tablename__ = "inventory_operations"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('receipt','issue','reversal','waste','adjustment','sale','sale_cancel','opening','receipt_reversal')",
            name="valid_kind",
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    idempotency_key: Mapped[uuid.UUID] = mapped_column(unique=True)
    payload_hash: Mapped[str] = mapped_column(db.String(64))
    kind: Mapped[str] = mapped_column(db.String(20))
    reason: Mapped[str] = mapped_column(db.String(300))
    reference: Mapped[str | None] = mapped_column(db.String(100))
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id", ondelete="RESTRICT"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    reverses_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("inventory_operations.id", ondelete="RESTRICT"), unique=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
    user: Mapped[User] = relationship()


class Lot(db.Model):
    __tablename__ = "inventory_lots"
    __table_args__ = (
        CheckConstraint("original_quantity > 0", name="original_positive"),
        CheckConstraint(
            "remaining_quantity >= 0 AND remaining_quantity <= original_quantity",
            name="balance_valid",
        ),
        CheckConstraint("unit_cost IS NULL OR unit_cost >= 0", name="cost_nonnegative"),
        CheckConstraint("source IN ('receipt','recovered','opening')", name="valid_source"),
        Index("ix_lots_fifo", "ingredient_id", "received_at", "id"),
        Index("ix_lots_expires", "expires_on"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredients.id", ondelete="RESTRICT"))
    operation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("inventory_operations.id", ondelete="RESTRICT"), index=True
    )
    code: Mapped[str | None] = mapped_column(db.String(100))
    source: Mapped[str] = mapped_column(db.String(20), default="receipt", server_default="receipt")
    original_quantity: Mapped[Decimal] = mapped_column(QTY)
    remaining_quantity: Mapped[Decimal] = mapped_column(QTY)
    unit_cost: Mapped[Decimal | None] = mapped_column(MONEY)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_on: Mapped[date | None] = mapped_column(db.Date)
    ingredient: Mapped[Ingredient] = relationship(lazy="joined")


class Movement(db.Model):
    __tablename__ = "inventory_movements"
    __table_args__ = (CheckConstraint("quantity <> 0", name="nonzero_quantity"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    operation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("inventory_operations.id", ondelete="RESTRICT"), index=True
    )
    ingredient_id: Mapped[int] = mapped_column(
        ForeignKey("ingredients.id", ondelete="RESTRICT"), index=True
    )
    quantity: Mapped[Decimal] = mapped_column(QTY)
    cost: Mapped[Decimal | None] = mapped_column(Numeric(24, 6))
    ingredient: Mapped[Ingredient] = relationship(lazy="joined")
    operation: Mapped[Operation] = relationship(lazy="joined")


class Allocation(db.Model):
    __tablename__ = "inventory_movement_allocations"
    __table_args__ = (
        CheckConstraint("quantity <> 0", name="nonzero_quantity"),
        CheckConstraint("unit_cost IS NULL OR unit_cost >= 0", name="cost_nonnegative"),
        UniqueConstraint("movement_id", "lot_id"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    movement_id: Mapped[int] = mapped_column(
        ForeignKey("inventory_movements.id", ondelete="RESTRICT"), index=True
    )
    lot_id: Mapped[int] = mapped_column(
        ForeignKey("inventory_lots.id", ondelete="RESTRICT"), index=True
    )
    quantity: Mapped[Decimal] = mapped_column(QTY)
    unit_cost: Mapped[Decimal | None] = mapped_column(MONEY)
