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
    r = requests.get(url, headers=headers, timeout=10)
    
    if r.status_code == 200:
        data = r.json()
        if data.get("code") == 0:
            fields = data.get("data", {}).get("items", [])
            with open("scratch/tiktok_fields.txt", "w", encoding="utf-8") as f:
                f.write(f"Total fields: {len(fields)}\n")
                for field in fields:
                    f.write(f"Name: '{field.get('field_name')}' | ID: {field.get('field_id')} | Type: {field.get('type')}\n")
            print("Successfully written fields to scratch/tiktok_fields.txt")
        else:
            print("API Error:", data.get("msg"))
    else:
        print("HTTP Error:", r.status_code, r.text)

if __name__ == "__main__":
    main()
