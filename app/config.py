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

    model_config = {"env_prefix": "GROCERY_"}


settings = Settings()
