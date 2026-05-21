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

def inspect_fields():
    token = get_tenant_access_token()
    if not token:
        print("Failed to get token.")
        return
        
    url = f"https://open.larksuite.com/open-apis/bitable/v1/apps/{BASE_TOKEN}/tables/{TABLE_ID}/fields"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    response = requests.get(url, headers=headers)
    data = response.json()
    
    if data.get("code") == 0:
        fields = data.get("data", {}).get("items", [])
        result = []
        for f in fields:
            result.append({
                "field_name": f.get('field_name'),
                "type": f.get('type'),
                "field_id": f.get('field_id')
            })
        with open("fields.json", "w", encoding="utf-8") as file:
            json.dump(result, file, indent=4, ensure_ascii=False)
        print("Fields written to fields.json successfully.")
    else:
        print(f"Error inspecting fields: {data.get('msg')} (code: {data.get('code')})")

if __name__ == "__main__":
    inspect_fields()
