import requests
import json

APP_ID = "cli_aa873a1aee789e18"
APP_SECRET = "9ESCyqVBJvOBA6A3DCmuzf3OkowWI2ZW"
BASE_TOKEN = "IV3Gb2bGmawOBXs0OhojrU5Bpxb"

def get_tenant_access_token():
    url = "https://open.larksuite.com/open-apis/auth/v3/tenant_access_token/internal"
    payload = {
        "app_id": APP_ID,
        "app_secret": APP_SECRET
    }
    response = requests.post(url, json=payload)
    return response.json().get("tenant_access_token")

def list_tables():
    token = get_tenant_access_token()
    if not token:
        print("Failed to get token. Check App ID/Secret.")
        return
        
    url = f"https://open.larksuite.com/open-apis/bitable/v1/apps/{BASE_TOKEN}/tables"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    response = requests.get(url, headers=headers)
    data = response.json()
    
    if data.get("code") == 0:
        tables = data.get("data", {}).get("items", [])
        print("Tables found:")
        for t in tables:
            print(f"- Name: {t.get('name')}, Table ID: {t.get('table_id')}")
    else:
        print(f"Error listing tables: {data.get('msg')} (code: {data.get('code')})")

if __name__ == "__main__":
    list_tables()
