from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Date,
    ForeignKey, Text, UniqueConstraint,
)
from sqlalchemy.types import TypeDecorator
import json


class JSONType(TypeDecorator):
    """SQLite-compatible JSON column."""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value)
        return "{}"

    def process_result_value(self, value, dialect):
        if value is not None:
            return json.loads(value)
        return {}
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    api_key = Column(String(128), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    role = Column(String(20), nullable=False, default="user")  # admin | user
    language = Column(String(5), nullable=False, default="en")
    avatar = Column(Text, nullable=True)  # data URL (e.g. data:image/jpeg;base64,...)
    created_at = Column(DateTime, default=datetime.utcnow)


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    icon = Column(String(10), default="📦")
    sort_order = Column(Integer, default=0)
    translations = Column(JSONType, default=dict)

    items = relationship("LibraryItem", back_populates="category")


class LibraryItem(Base):
    __tablename__ = "library_items"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False, unique=True)
    icon = Column(String(10), nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    default_quantity = Column(Float, nullable=False, default=1.0)
    unit = Column(String(20), nullable=False, default="unit")
    image_url = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)
    translations = Column(JSONType, default=dict)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    category = relationship("Category", back_populates="items")
    reminders = relationship("RepurchaseReminder", back_populates="library_item")
    created_by = relationship("User", foreign_keys=[created_by_id])


class GroceryList(Base):
    __tablename__ = "grocery_lists"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    is_active = Column(Boolean, default=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = relationship("GroceryListItem", back_populates="grocery_list", cascade="all, delete-orphan")
    created_by = relationship("User", foreign_keys=[created_by_id])


class GroceryListItem(Base):
    __tablename__ = "grocery_list_items"
    __table_args__ = (
        UniqueConstraint("list_id", "library_item_id", name="uq_list_library_item"),
    )

    id = Column(Integer, primary_key=True)
    list_id = Column(Integer, ForeignKey("grocery_lists.id", ondelete="CASCADE"), nullable=False)
    library_item_id = Column(Integer, ForeignKey("library_items.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default="pending")  # pending | purchased
    added_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    added_by_display_name = Column(String(100), nullable=True)
    added_via = Column(String(50), nullable=True)  # e.g. "Telegram" for "Added by Primus on Telegram"
    purchased_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    purchased_by_display_name = Column(String(100), nullable=True)
    purchased_at = Column(DateTime, nullable=True)
    expiration_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    grocery_list = relationship("GroceryList", back_populates="items")
    library_item = relationship("LibraryItem")
    added_by = relationship("User", foreign_keys=[added_by_id])
    purchased_by = relationship("User", foreign_keys=[purchased_by_id])


class ActivityLog(Base):
    __tablename__ = "activity_log"

    id = Column(Integer, primary_key=True)
    list_id = Column(Integer, ForeignKey("grocery_lists.id", ondelete="CASCADE"), nullable=False)
    item_id = Column(Integer, nullable=True)
    action = Column(String(50), nullable=False)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    actor_display_name = Column(String(100), nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SupermarketPreset(Base):
    __tablename__ = "supermarket_presets"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False, unique=True)
    category_order = Column(JSONType, default=list)


class RepurchaseReminder(Base):
    __tablename__ = "repurchase_reminders"

    id = Column(Integer, primary_key=True)
    library_item_id = Column(Integer, ForeignKey("library_items.id"), nullable=False)
    interval_days = Column(Integer, nullable=False)
    last_purchased = Column(DateTime, nullable=True)
    next_due = Column(DateTime, nullable=True)
    active = Column(Boolean, default=True)

    library_item = relationship("LibraryItem", back_populates="reminders")


class Recipe(Base):
    """Recipe from Obsidian or manual entry. Ingredients stored as JSON."""
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True)
    name = Column(String(300), nullable=False)
    source_path = Column(String(500), nullable=True)  # e.g. Obsidian vault path
    default_servings = Column(Integer, nullable=False, default=4)
    ingredients = Column(JSONType, default=list)  # [{"name": str, "quantity": float, "unit": str}, ...]
    directions = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    ratings = relationship("RecipeRating", back_populates="recipe", cascade="all, delete-orphan")


class RecipeRating(Base):
    """User rating for a recipe (1-5)."""
    __tablename__ = "recipe_ratings"
    __table_args__ = (UniqueConstraint("user_id", "recipe_id", name="uq_recipe_rating_user_recipe"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    rating = Column(Integer, nullable=False)  # 1-5
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id])
    recipe = relationship("Recipe", back_populates="ratings")


class MealPlanEntry(Base):
    """Evening meal (dinner) for a weekday. day 1=Monday .. 5=Friday."""
    __tablename__ = "meal_plan_entries"
    __table_args__ = (UniqueConstraint("year", "week", "day", name="uq_meal_plan_year_week_day"),)

    id = Column(Integer, primary_key=True)
    year = Column(Integer, nullable=False)
    week = Column(Integer, nullable=False)  # ISO week 1-53
    day = Column(Integer, nullable=False)   # 1=Monday .. 5=Friday
    dinner = Column(String(300), nullable=False, default="")  # free text or recipe name
    recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="SET NULL"), nullable=True)
    recipe_servings = Column(Integer, nullable=True)  # override for this slot; null = use recipe default

    recipe = relationship("Recipe", foreign_keys=[recipe_id])
