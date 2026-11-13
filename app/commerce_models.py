"""Versioned recipes and persistent internal sales; quantities stay in base units."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models import QTY, Ingredient, TimestampMixin, utcnow

PESOS = Numeric(14, 2)


class MenuItem(TimestampMixin, db.Model):
    __tablename__ = "menu_items"
    __table_args__ = (
        CheckConstraint("price >= 0", name="price_nonnegative"),
        CheckConstraint("kind IN ('prepared','direct')", name="valid_kind"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str | None] = mapped_column(db.String(50), unique=True)
    name: Mapped[str] = mapped_column(db.String(150), unique=True)
    category: Mapped[str] = mapped_column(db.String(80), index=True)
    description: Mapped[str | None] = mapped_column(db.Text)
    price: Mapped[Decimal] = mapped_column(PESOS)
    kind: Mapped[str] = mapped_column(db.String(20), default="prepared")
    active: Mapped[bool] = mapped_column(default=True, server_default=db.true())
    updated_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))


class RecipeVersion(db.Model):
    __tablename__ = "recipe_versions"
    __table_args__ = (
        UniqueConstraint("menu_item_id", "version"),
        CheckConstraint("yield_quantity > 0", name="positive_yield"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    menu_item_id: Mapped[int] = mapped_column(
        ForeignKey("menu_items.id", ondelete="RESTRICT"), index=True
    )
    version: Mapped[int] = mapped_column()
    yield_quantity: Mapped[Decimal] = mapped_column(QTY)
    notes: Mapped[str | None] = mapped_column(db.String(500))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    lines: Mapped[list["RecipeIngredient"]] = relationship(
        lazy="selectin", order_by="RecipeIngredient.id"
    )


class RecipeIngredient(db.Model):
    __tablename__ = "recipe_ingredients"
    __table_args__ = (
        UniqueConstraint("recipe_version_id", "ingredient_id"),
        CheckConstraint("quantity > 0", name="positive_quantity"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_version_id: Mapped[int] = mapped_column(
        ForeignKey("recipe_versions.id", ondelete="RESTRICT"), index=True
    )
    ingredient_id: Mapped[int] = mapped_column(
        ForeignKey("ingredients.id", ondelete="RESTRICT"), index=True
    )
    quantity: Mapped[Decimal] = mapped_column(QTY)
    unit_symbol: Mapped[str] = mapped_column(db.String(10))
    ingredient: Mapped[Ingredient] = relationship(lazy="joined")


class Sale(db.Model):
    __tablename__ = "sales"
    __table_args__ = (
        CheckConstraint("total >= 0 AND received >= total AND change >= 0", name="amounts_valid"),
        CheckConstraint("method IN ('cash','card','transfer')", name="valid_method"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    operation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("inventory_operations.id", ondelete="RESTRICT"), unique=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    total: Mapped[Decimal] = mapped_column(PESOS)
    received: Mapped[Decimal] = mapped_column(PESOS)
    change: Mapped[Decimal] = mapped_column(PESOS)
    method: Mapped[str] = mapped_column(db.String(20))
    cost: Mapped[Decimal | None] = mapped_column(Numeric(24, 6))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
    items: Mapped[list["SaleItem"]] = relationship(lazy="selectin", order_by="SaleItem.id")
    cancellation: Mapped["SaleCancellation | None"] = relationship(lazy="joined")


class SaleItem(db.Model):
    __tablename__ = "sale_items"
    __table_args__ = (
        CheckConstraint("quantity > 0 AND quantity <= 9999", name="positive_quantity"),
        CheckConstraint("unit_price >= 0 AND subtotal >= 0", name="amounts_nonnegative"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    sale_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sales.id", ondelete="RESTRICT"), index=True
    )
    menu_item_id: Mapped[int] = mapped_column(ForeignKey("menu_items.id", ondelete="RESTRICT"))
    recipe_version_id: Mapped[int] = mapped_column(
        ForeignKey("recipe_versions.id", ondelete="RESTRICT")
    )
    name: Mapped[str] = mapped_column(db.String(150))
    quantity: Mapped[int] = mapped_column()
    unit_price: Mapped[Decimal] = mapped_column(PESOS)
    subtotal: Mapped[Decimal] = mapped_column(PESOS)
    ingredients: Mapped[list["SaleIngredientSnapshot"]] = relationship(lazy="selectin")


class SaleIngredientSnapshot(db.Model):
    __tablename__ = "sale_item_ingredient_snapshots"
    __table_args__ = (CheckConstraint("quantity > 0", name="positive_quantity"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    sale_item_id: Mapped[int] = mapped_column(
        ForeignKey("sale_items.id", ondelete="RESTRICT"), index=True
    )
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredients.id", ondelete="RESTRICT"))
    movement_id: Mapped[int] = mapped_column(
        ForeignKey("inventory_movements.id", ondelete="RESTRICT")
    )
    name: Mapped[str] = mapped_column(db.String(150))
    unit_symbol: Mapped[str] = mapped_column(db.String(10))
    quantity: Mapped[Decimal] = mapped_column(QTY)


class SaleCancellation(db.Model):
    __tablename__ = "sale_cancellations"
    id: Mapped[int] = mapped_column(primary_key=True)
    sale_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sales.id", ondelete="RESTRICT"), unique=True
    )
    operation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("inventory_operations.id", ondelete="RESTRICT"), unique=True
    )
    restocked: Mapped[bool] = mapped_column()
    reason: Mapped[str] = mapped_column(db.String(300))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class InventoryCount(db.Model):
    __tablename__ = "inventory_counts"
    __table_args__ = (
        CheckConstraint(
            "before_quantity >= 0 AND counted_quantity >= 0", name="nonnegative_counts"
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    operation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("inventory_operations.id", ondelete="RESTRICT"), unique=True
    )
    ingredient_id: Mapped[int] = mapped_column(
        ForeignKey("ingredients.id", ondelete="RESTRICT"), index=True
    )
    before_quantity: Mapped[Decimal] = mapped_column(QTY)
    counted_quantity: Mapped[Decimal] = mapped_column(QTY)
