import requests
import json
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from lark_client import LarkClient

def main():
    client = LarkClient()
    token = client.get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    url = f"https://open.larksuite.com/open-apis/bitable/v1/apps/{config.LARK_BASE_TOKEN}/tables/{config.TABLE_TIKTOK_ID}/fields"
    
    payload = {
        "field_name": "Thời gian phân phối",
        "type": 5
    }
    
    r = requests.post(url, headers=headers, json=payload, timeout=10)
    print("Add field status:", r.status_code)
    print("Response:", json.dumps(r.json(), indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
