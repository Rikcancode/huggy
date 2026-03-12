from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///grocery.db"
    admin_api_key: str = "admin-change-me"
    user_api_key: str = "user-change-me"
    app_title: str = "Grocery List"
    secret_key: str = "change-me-session-secret"
    seed_on_startup: bool = True
    upload_dir: str = ""

    model_config = {"env_prefix": "GROCERY_"}


settings = Settings()
