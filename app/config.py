from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///grocery.db"
    admin_api_key: str = "admin-change-me"
    user_api_key: str = "user-change-me"
    app_title: str = "Grocery List"
    secret_key: str = "change-me-session-secret"
    default_admin_password: str = "mechou"
    setup_token: str = ""
    seed_on_startup: bool = True
    upload_dir: str = ""
    obsidian_api_url: str = ""
    obsidian_api_key: str = ""
    # Vault-relative folder that contains recipe markdown notes.
    # Example: "Family/Recipes/"
    obsidian_recipes_folder: str = "Family/Recipes/"
    # Safety limit when auto-syncing a folder on first recipe list access.
    obsidian_recipes_max_files: int = 5000
    # Keep recipe DB in sync with Obsidian automatically.
    obsidian_recipes_auto_sync: bool = True
    # Minimum seconds between automatic folder sync attempts.
    obsidian_recipes_sync_interval_seconds: int = 300

    model_config = {"env_prefix": "GROCERY_"}


settings = Settings()
