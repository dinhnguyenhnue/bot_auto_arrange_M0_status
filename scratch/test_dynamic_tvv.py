import os
import sys
import requests
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

def test():
    # Get config values
    app_id = config.LARK_APP_ID
    app_secret = config.LARK_APP_SECRET
    base_token_tvv = config.LARK_BASE_TOKEN_TVV
    table_tvv_id = config.TABLE_TVV_ID

    # Get token
    url = "https://open.larksuite.com/open-apis/auth/v3/tenant_access_token/internal"
    res = requests.post(url, json={"app_id": app_id, "app_secret": app_secret}, timeout=10)
    token = res.json().get("tenant_access_token")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # Try list records
    rec_url = f"https://open.larksuite.com/open-apis/bitable/v1/apps/{base_token_tvv}/tables/{table_tvv_id}/records"
    r = requests.get(rec_url, headers=headers, timeout=10)
    print("List records response status:", r.status_code)
    try:
        print("List records response:", json.dumps(r.json(), indent=2, ensure_ascii=False))
    except Exception:
        print("Raw response:", r.text[:1000])

if __name__ == "__main__":
    test()
