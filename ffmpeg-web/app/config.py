import os


class ConfigError(Exception):
    pass


BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ConfigError("no bot token set")
