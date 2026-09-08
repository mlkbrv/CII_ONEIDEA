from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str

    # Secret used to sign JWT access tokens. Must be kept secret (it lives
    # in .env, which is gitignored). Never hardcode it in source.
    secret_key: str

    # How long an access token stays valid, in minutes. After this the JWT
    # "exp" claim expires and the client must log in again. Telegram clients
    # cannot prompt for a password, so the default is generous (7 days) —
    # they simply re-authenticate with fresh initData.
    access_token_expire_minutes: int = 10080

    # How often the background competition-expiration sweeper checks PostgreSQL
    # for ACTIVE competitions whose end_time has passed. Seconds.
    auto_complete_interval_seconds: int = 30

    # The sweeper and the notification delivery loop belong to the worker
    # process, not the API. Running them in the API too would double every
    # sweep once the API scales past one uvicorn worker.
    run_sweeper: bool = False

    # --- Telegram -------------------------------------------------------
    # Token from @BotFather. Signs nothing of ours — it is the shared secret
    # Telegram uses to sign initData, so we need it to VERIFY that a Mini App
    # request really came from Telegram. Empty disables Telegram auth.
    telegram_bot_token: str = ""

    # The bot's @handle, without the @. The browser/PWA sign-in path needs it
    # to render the Telegram Login Widget; inside Telegram it is unused.
    telegram_bot_username: str = ""

    # https URL the Mini App is served from, e.g. https://cci.example.com/app/.
    # Must match what is configured in BotFather or the button does nothing.
    telegram_webapp_url: str = ""

    # How old signed initData may be before we reject it. Telegram's own
    # guidance is to check this; it bounds how long a leaked initData string
    # stays usable.
    telegram_init_data_max_age_seconds: int = 86400

    # How many minutes before a competition ends to send the "ending soon"
    # reminder (TZ section 16).
    competition_reminder_minutes: int = 10

    # How often the worker polls for undelivered notifications. Seconds.
    notification_poll_interval_seconds: int = 5

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
