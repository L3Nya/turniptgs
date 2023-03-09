import os


class ConfigError(Exception):
    pass


API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")

if not API_ID or not API_HASH:
    raise ConfigError("no API credentials set")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ConfigError("no bot token set")

TEST_MODE = os.getenv("TELEGRAM_TEST_MODE", "")
TEST_MODE = TEST_MODE.lower() == "true" or TEST_MODE == "1"

WEB_APP_URL = os.getenv("WEB_APP_URL", None)
VIDEO_STICKERS_ENABLED = os.getenv("VIDEO_STICKERS_ENABLED", "true").lower() == "true"
STATIC_STICKERS_ENABLED = os.getenv("STATIC_STICKERS_ENABLED", "true").lower() == "true"
KEEP_CACHE = os.getenv("KEEP_CACHE", "true").lower() == "true"

CONCURRENT_SPLITTERS = int(os.getenv("CONCURRENT_SPLITTERS", "5"))
SPLITTER_WORKERS = int(os.getenv("SPLITTER_WORKERS", "3"))

LOG_CHAT_ID = os.getenv("LOG_CHAT_ID")
