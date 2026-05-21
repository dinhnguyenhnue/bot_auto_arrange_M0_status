import os
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

# Lark API settings
LARK_APP_ID = os.getenv("LARK_APP_ID", "")
LARK_APP_SECRET = os.getenv("LARK_APP_SECRET", "")
LARK_BASE_TOKEN = os.getenv("LARK_BASE_TOKEN", "")

# Table IDs
TABLE_TIKTOK_ID = os.getenv("TABLE_TIKTOK_ID", "tblw9IGc8PmB3wR2")
TABLE_TVV_ID = os.getenv("TABLE_TVV_ID", "")

# TikTok Table Field Names
FIELD_TIKTOK_STATUS = os.getenv("FIELD_TIKTOK_STATUS", "Trạng thái")
FIELD_TIKTOK_REGION = os.getenv("FIELD_TIKTOK_REGION", "Khu vực")
FIELD_TIKTOK_CALLBACK_TIME = os.getenv("FIELD_TIKTOK_CALLBACK_TIME", "Hẹn gọi lại")
FIELD_TIKTOK_ASSIGNED_USER = os.getenv("FIELD_TIKTOK_ASSIGNED_USER", "Tư vấn viên")
FIELD_TIKTOK_ASSIGNED_TIME = os.getenv("FIELD_TIKTOK_ASSIGNED_TIME", "Thời gian phân phối")

# TVV Table Field Names
FIELD_TVV_USER = os.getenv("FIELD_TVV_USER", "Nhân sự")
FIELD_TVV_ACTIVE = os.getenv("FIELD_TVV_ACTIVE", "Đi làm hôm nay")
FIELD_TVV_REGION = os.getenv("FIELD_TVV_REGION", "Khu vực hoạt động")
FIELD_TVV_ROLE = os.getenv("FIELD_TVV_ROLE", "Vai trò")

# Algorithm configuration
MAX_ASSIGNMENTS_PER_DAY = int(os.getenv("MAX_ASSIGNMENTS_PER_DAY", "2"))
COOLDOWN_MINUTES_BETWEEN_CALLS = int(os.getenv("COOLDOWN_MINUTES_BETWEEN_CALLS", "30"))
PORT = int(os.getenv("PORT", "8000"))

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
