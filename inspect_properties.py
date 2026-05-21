import requests
import json

APP_ID = "cli_aa873a1aee789e18"
APP_SECRET = "9ESCyqVBJvOBA6A3DCmuzf3OkowWI2ZW"
BASE_TOKEN = "IV3Gb2bGmawOBXs0OhojrU5Bpxb"
TABLE_ID = "tbl3BdmUlnsvb3Zm"

def get_tenant_access_token():
    url = "https://open.larksuite.com/open-apis/auth/v3/tenant_access_token/internal"
    payload = {
        "app_id": APP_ID,
        "app_secret": APP_SECRET
    }
    response = requests.post(url, json=payload)
    return response.json().get("tenant_access_token")

def inspect_properties():
    token = get_tenant_access_token()
    if not token:
        return
        
    url = f"https://open.larksuite.com/open-apis/bitable/v1/apps/{BASE_TOKEN}/tables/{TABLE_ID}/fields"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    response = requests.get(url, headers=headers)
    data = response.json()
    
    if data.get("code") == 0:
        fields = data.get("data", {}).get("items", [])
        target = None
        for f in fields:
            if f.get("field_name") == "Tư vấn viên":
                target = f
                break
        if target:
            with open("properties.json", "w", encoding="utf-8") as file:
                json.dump(target, file, indent=4, ensure_ascii=False)
            print("Property written to properties.json successfully.")
        else:
            print("Field not found.")
    else:
        print("Error:", data.get("msg"))

if __name__ == "__main__":
    inspect_properties()
