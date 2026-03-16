from datetime import datetime, date
from pydantic import BaseModel


# ---------- Category ----------

class CategoryCreate(BaseModel):
    name: str
    icon: str = "📦"
    sort_order: int = 0
    translations: dict = {}


class CategoryUpdate(BaseModel):
    name: str | None = None
    icon: str | None = None
    sort_order: int | None = None
    translations: dict | None = None


class CategoryOut(BaseModel):
    id: int
    name: str
    icon: str
    sort_order: int
    translations: dict
    model_config = {"from_attributes": True}


class UserRef(BaseModel):
    id: int
    name: str
    model_config = {"from_attributes": True}


# ---------- Library Item ----------

class LibraryItemCreate(BaseModel):
    name: str
    icon: str | None = None
    category_id: int
    default_quantity: float = 1.0
    unit: str = "unit"
    image_url: str | None = None
    notes: str | None = None
    translations: dict = {}


class LibraryItemUpdate(BaseModel):
    name: str | None = None
    icon: str | None = None
    category_id: int | None = None
    default_quantity: float | None = None
    unit: str | None = None
    image_url: str | None = None
    notes: str | None = None
    translations: dict | None = None


class LibraryItemOut(BaseModel):
    id: int
    name: str
    icon: str | None
    category_id: int
    default_quantity: float
    unit: str
    image_url: str | None
    notes: str | None
    translations: dict
    created_by_id: int | None = None
    created_at: datetime
    updated_at: datetime
    category: CategoryOut | None = None
    created_by: UserRef | None = None
    model_config = {"from_attributes": True}


# ---------- Grocery List ----------

class GroceryListCreate(BaseModel):
    name: str


class GroceryListUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None


class GroceryListItemOut(BaseModel):
    id: int
    list_id: int
    library_item_id: int
    quantity: float
    unit: str
    status: str
    added_by_id: int | None
    added_by_display_name: str | None = None
    added_via: str | None = None
    purchased_by_id: int | None
    purchased_by_display_name: str | None = None
    purchased_at: datetime | None
    expiration_date: date | None
    notes: str | None
    created_at: datetime
    updated_at: datetime | None = None
    library_item: LibraryItemOut | None = None
    added_by: UserRef | None = None
    purchased_by: UserRef | None = None
    model_config = {"from_attributes": True}


class ActivityOut(BaseModel):
    id: int
    list_id: int
    item_id: int | None
    action: str
    actor_id: int | None
    actor_display_name: str | None
    details: str | None
    created_at: datetime
    model_config = {"from_attributes": True}


class GroceryListOut(BaseModel):
    id: int
    name: str
    is_active: bool
    created_by_id: int | None = None
    created_at: datetime
    updated_at: datetime
    items: list[GroceryListItemOut] = []
    created_by: UserRef | None = None
    model_config = {"from_attributes": True}


class GroceryListSummary(BaseModel):
    id: int
    name: str
    is_active: bool
    created_by_id: int | None = None
    created_at: datetime
    updated_at: datetime
    item_count: int = 0
    created_by: UserRef | None = None
    model_config = {"from_attributes": True}


class RecentPurchaseOut(BaseModel):
    """Purchased list item with list name for Recent Purchases tab."""
    list_id: int
    list_name: str
    item: GroceryListItemOut
    model_config = {"from_attributes": True}


class AddItemToList(BaseModel):
    library_item_id: int
    quantity: float | None = None
    unit: str | None = None
    expiration_date: date | None = None
    notes: str | None = None


class UpdateListItem(BaseModel):
    quantity: float | None = None
    unit: str | None = None
    status: str | None = None
    expiration_date: date | None = None
    notes: str | None = None


# ---------- Supermarket Preset ----------

class SupermarketPresetCreate(BaseModel):
    name: str
    category_order: list[int] = []


class SupermarketPresetUpdate(BaseModel):
    name: str | None = None
    category_order: list[int] | None = None


class SupermarketPresetOut(BaseModel):
    id: int
    name: str
    category_order: list[int]
    model_config = {"from_attributes": True}


# ---------- Repurchase Reminder ----------

class ReminderCreate(BaseModel):
    library_item_id: int
    interval_days: int
    active: bool = True


class ReminderUpdate(BaseModel):
    interval_days: int | None = None
    active: bool | None = None


class ReminderOut(BaseModel):
    id: int
    library_item_id: int
    interval_days: int
    last_purchased: datetime | None
    next_due: datetime | None
    active: bool
    library_item: LibraryItemOut | None = None
    model_config = {"from_attributes": True}


# ---------- User ----------

class UserCreate(BaseModel):
    name: str
    role: str = "user"
    language: str = "en"
    password: str | None = None


class UserUpdate(BaseModel):
    name: str | None = None
    role: str | None = None
    language: str | None = None
    password: str | None = None


class UserOut(BaseModel):
    id: int
    name: str
    api_key: str
    role: str
    language: str
    avatar: str | None = None
    created_at: datetime
    model_config = {"from_attributes": True}


class UserMeUpdate(BaseModel):
    avatar: str | None = None


class UserLogin(BaseModel):
    name: str
    password: str


# ---------- Meal Plan ----------

class MealPlanEntryOut(BaseModel):
    id: int
    year: int
    week: int
    day: int  # 1=Mon .. 5=Fri
    dinner: str
    model_config = {"from_attributes": True}


class MealPlanDayUpdate(BaseModel):
    dinner: str = ""
