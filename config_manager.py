import os
import sys
from typing import Optional
# Make sure project directory is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import config

ENV_FILE_PATH = ".env"

def get_current_env_values() -> dict:
    """Read .env file directly and return keys/values."""
    values = {
        "LARK_APP_ID": "",
        "LARK_APP_SECRET": "",
        "LINK_TABLE_TIKTOK": "",
        "LINK_TABLE_TVV": "",
        "LARK_BASE_TOKEN": "",
        "LARK_BASE_TOKEN_TVV": "",
        "TABLE_TIKTOK_ID": "",
        "TABLE_TVV_ID": "",
        "MAX_ASSIGNMENTS_PER_DAY": "2",
        "COOLDOWN_MINUTES_BETWEEN_CALLS": "30",
        "PORT": "8000"
    }
    
    if os.path.exists(ENV_FILE_PATH):
        with open(ENV_FILE_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    parts = line.split("=", 1)
                    k = parts[0].strip()
                    v = parts[1].strip().strip('"').strip("'")
                    if k in values:
                        values[k] = v
    else:
        # Fallback to current config values
        values["LARK_APP_ID"] = config.LARK_APP_ID
        values["LARK_APP_SECRET"] = config.LARK_APP_SECRET
        values["LINK_TABLE_TIKTOK"] = config.LINK_TABLE_TIKTOK
        values["LINK_TABLE_TVV"] = config.LINK_TABLE_TVV
        values["LARK_BASE_TOKEN"] = config.LARK_BASE_TOKEN
        values["LARK_BASE_TOKEN_TVV"] = config.LARK_BASE_TOKEN_TVV
        values["TABLE_TIKTOK_ID"] = config.TABLE_TIKTOK_ID
        values["TABLE_TVV_ID"] = config.TABLE_TVV_ID
        values["MAX_ASSIGNMENTS_PER_DAY"] = str(config.MAX_ASSIGNMENTS_PER_DAY)
        values["COOLDOWN_MINUTES_BETWEEN_CALLS"] = str(config.COOLDOWN_MINUTES_BETWEEN_CALLS)
        values["PORT"] = str(config.PORT)
        
    return values

def discover_table_id(app_id: str, app_secret: str, base_token: str, table_type: str) -> Optional[str]:
    """
    Query Lark API to list all tables in a base and try to auto-detect the correct Table ID
    based on table name keywords.
    """
    if not app_id or not app_secret or not base_token:
        return None
    import requests
    try:
        # Get tenant access token
        url = "https://open.larksuite.com/open-apis/auth/v3/tenant_access_token/internal"
        payload = {"app_id": app_id, "app_secret": app_secret}
        res = requests.post(url, json=payload, timeout=10)
        res_data = res.json()
        if res_data.get("code") != 0:
            return None
        token = res_data.get("tenant_access_token")
        if not token:
            return None
        
        # Get list of tables
        tables_url = f"https://open.larksuite.com/open-apis/bitable/v1/apps/{base_token}/tables"
        headers = {"Authorization": f"Bearer {token}"}
        r = requests.get(tables_url, headers=headers, timeout=10)
        data = r.json()
        if data.get("code") == 0:
            tables = data.get("data", {}).get("items", [])
            if not tables:
                return None
            
            # If only 1 table exists in the Bitable, auto-select it
            if len(tables) == 1:
                return tables[0].get("table_id")
                
            # Otherwise, check name keywords
            if table_type == "tiktok":
                # Look for tiktok/lead/customer
                for t in tables:
                    name_lower = t.get("name", "").lower()
                    if any(kw in name_lower for kw in ["tiktok", "customer", "lead", "khách", "data"]):
                        return t.get("table_id")
            elif table_type == "tvv":
                # Look for tvv/tư vấn/nhân sự
                for t in tables:
                    name_lower = t.get("name", "").lower()
                    if any(kw in name_lower for kw in ["tvv", "tư vấn", "nhân sự", "agent", "member", "staff"]):
                        return t.get("table_id")
            
            # Fallback to the first table in the list
            return tables[0].get("table_id")
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Failed to auto-discover table ID for base {base_token}: {e}")
    return None

def update_env_values(new_values: dict):
    """Update .env file with new values and reload config."""
    import re
    from typing import Optional
    
    app_id = new_values.get("LARK_APP_ID", "")
    app_secret = new_values.get("LARK_APP_SECRET", "")

    # Parse LINK_TABLE_TIKTOK for base token and table ID
    link_tiktok = new_values.get("LINK_TABLE_TIKTOK", "")
    if link_tiktok:
        base_match = re.search(r'/(?:base|sheets)/([a-zA-Z0-9]+)', link_tiktok)
        table_match = re.search(r'[?&]table=([a-zA-Z0-9]+)', link_tiktok) or re.search(r'/table/([a-zA-Z0-9]+)', link_tiktok)
        if base_match:
            new_values["LARK_BASE_TOKEN"] = base_match.group(1)
        if table_match:
            new_values["TABLE_TIKTOK_ID"] = table_match.group(1)
        else:
            # Table ID not in URL, try auto-discovery
            base_token = new_values.get("LARK_BASE_TOKEN")
            if base_token:
                discovered_id = discover_table_id(app_id, app_secret, base_token, "tiktok")
                if discovered_id:
                    new_values["TABLE_TIKTOK_ID"] = discovered_id

    # Parse LINK_TABLE_TVV for base token and table ID
    link_tvv = new_values.get("LINK_TABLE_TVV", "")
    if link_tvv:
        base_match = re.search(r'/(?:base|sheets)/([a-zA-Z0-9]+)', link_tvv)
        table_match = re.search(r'[?&]table=([a-zA-Z0-9]+)', link_tvv) or re.search(r'/table/([a-zA-Z0-9]+)', link_tvv)
        if base_match:
            new_values["LARK_BASE_TOKEN_TVV"] = base_match.group(1)
        if table_match:
            new_values["TABLE_TVV_ID"] = table_match.group(1)
        else:
            # Table ID not in URL, try auto-discovery
            base_token_tvv = new_values.get("LARK_BASE_TOKEN_TVV")
            if base_token_tvv:
                discovered_id = discover_table_id(app_id, app_secret, base_token_tvv, "tvv")
                if discovered_id:
                    new_values["TABLE_TVV_ID"] = discovered_id

    lines = []
    existing_keys = set()
    
    if os.path.exists(ENV_FILE_PATH):
        with open(ENV_FILE_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
    updated_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            parts = stripped.split("=", 1)
            k = parts[0].strip()
            if k in new_values:
                updated_lines.append(f'{k}="{new_values[k]}"\n')
                existing_keys.add(k)
                continue
        updated_lines.append(line)
        
    # Append keys that were not in the file
    for k, v in new_values.items():
        if k not in existing_keys:
            updated_lines.append(f'{k}="{v}"\n')
            
    with open(ENV_FILE_PATH, "w", encoding="utf-8") as f:
        f.writelines(updated_lines)
        
    # Reload config in config.py
    config.reload_config()

