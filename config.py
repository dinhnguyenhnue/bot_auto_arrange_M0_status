import os
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

# Global config variables
LARK_APP_ID = ""
LARK_APP_SECRET = ""
LINK_TABLE_TIKTOK = ""
LINK_TABLE_TVV = ""
LARK_BASE_TOKEN = ""
LARK_BASE_TOKEN_TVV = ""
TABLE_TIKTOK_ID = ""
TABLE_TVV_ID = ""
FIELD_TIKTOK_STATUS = ""
FIELD_TIKTOK_REGION = ""
FIELD_TIKTOK_CALLBACK_TIME = ""
FIELD_TIKTOK_ASSIGNED_USER = ""
FIELD_TIKTOK_ASSIGNED_TIME = ""
FIELD_TVV_USER = ""
FIELD_TVV_ACTIVE = ""
FIELD_TVV_REGION = ""
FIELD_TVV_ROLE = ""
MAX_ASSIGNMENTS_PER_DAY = 2
COOLDOWN_MINUTES_BETWEEN_CALLS = 30
PORT = 8000

def reload_config(dotenv_path=None):
    """Reload environment variables from .env file and update globals."""
    global LARK_APP_ID, LARK_APP_SECRET, LARK_BASE_TOKEN, LARK_BASE_TOKEN_TVV
    global LINK_TABLE_TIKTOK, LINK_TABLE_TVV
    global TABLE_TIKTOK_ID, TABLE_TVV_ID
    global FIELD_TIKTOK_STATUS, FIELD_TIKTOK_REGION, FIELD_TIKTOK_CALLBACK_TIME, FIELD_TIKTOK_ASSIGNED_USER, FIELD_TIKTOK_ASSIGNED_TIME
    global FIELD_TVV_USER, FIELD_TVV_ACTIVE, FIELD_TVV_REGION, FIELD_TVV_ROLE
    global MAX_ASSIGNMENTS_PER_DAY, COOLDOWN_MINUTES_BETWEEN_CALLS, PORT

    if dotenv_path is None:
        try:
            import config_manager
            dotenv_path = config_manager.ENV_FILE_PATH
        except (ImportError, AttributeError):
            dotenv_path = ".env"

    load_dotenv(dotenv_path=dotenv_path, override=True)

    LARK_APP_ID = os.getenv("LARK_APP_ID", "")
    LARK_APP_SECRET = os.getenv("LARK_APP_SECRET", "")
    LINK_TABLE_TIKTOK = os.getenv("LINK_TABLE_TIKTOK", "")
    LINK_TABLE_TVV = os.getenv("LINK_TABLE_TVV", "")
    LARK_BASE_TOKEN = os.getenv("LARK_BASE_TOKEN", "")
    LARK_BASE_TOKEN_TVV = os.getenv("LARK_BASE_TOKEN_TVV", "")

    TABLE_TIKTOK_ID = os.getenv("TABLE_TIKTOK_ID", "")
    TABLE_TVV_ID = os.getenv("TABLE_TVV_ID", "")

    FIELD_TIKTOK_STATUS = os.getenv("FIELD_TIKTOK_STATUS", "Trạng thái")
    FIELD_TIKTOK_REGION = os.getenv("FIELD_TIKTOK_REGION", "Khu vực")
    FIELD_TIKTOK_CALLBACK_TIME = os.getenv("FIELD_TIKTOK_CALLBACK_TIME", "Hẹn gọi lại")
    FIELD_TIKTOK_ASSIGNED_USER = os.getenv("FIELD_TIKTOK_ASSIGNED_USER", "Tư vấn viên")
    FIELD_TIKTOK_ASSIGNED_TIME = os.getenv("FIELD_TIKTOK_ASSIGNED_TIME", "Thời gian phân phối")

    FIELD_TVV_USER = os.getenv("FIELD_TVV_USER", "Nhân sự")
    FIELD_TVV_ACTIVE = os.getenv("FIELD_TVV_ACTIVE", "Đi làm hôm nay")
    FIELD_TVV_REGION = os.getenv("FIELD_TVV_REGION", "Khu vực hoạt động")
    FIELD_TVV_ROLE = os.getenv("FIELD_TVV_ROLE", "Vai trò")

    MAX_ASSIGNMENTS_PER_DAY = int(os.getenv("MAX_ASSIGNMENTS_PER_DAY", "2"))
    COOLDOWN_MINUTES_BETWEEN_CALLS = int(os.getenv("COOLDOWN_MINUTES_BETWEEN_CALLS", "30"))
    PORT = int(os.getenv("PORT", "8000"))

# Initialize variables on load
reload_config()

def validate_config():
    """Verify that all required environment variables are set."""
    missing = []
    if not LARK_APP_ID: missing.append("LARK_APP_ID")
    if not LARK_APP_SECRET: missing.append("LARK_APP_SECRET")
    if not LARK_BASE_TOKEN: missing.append("LARK_BASE_TOKEN")
    if not TABLE_TIKTOK_ID: missing.append("TABLE_TIKTOK_ID")
    if not TABLE_TVV_ID: missing.append("TABLE_TVV_ID")
    
    if missing:
        raise ValueError(f"Missing required environment variables in .env: {', '.join(missing)}")
