import requests
import json
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

def main():
    app_id = config.LARK_APP_ID
    app_secret = config.LARK_APP_SECRET
    base_token_tvv = config.LARK_BASE_TOKEN_TVV
    table_tvv_id = config.TABLE_TVV_ID

    url = "https://open.larksuite.com/open-apis/auth/v3/tenant_access_token/internal"
    res = requests.post(url, json={"app_id": app_id, "app_secret": app_secret}, timeout=10)
    token = res.json().get("tenant_access_token")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Test Bitable App Info
    bitable_url = f"https://open.larksuite.com/open-apis/bitable/v1/apps/{base_token_tvv}"
    r_bitable = requests.get(bitable_url, headers=headers, timeout=10)
    print("Bitable App Info status:", r_bitable.status_code)
    print("Bitable App Info response:", r_bitable.text[:1000])

    # Test Spreadsheet Info
    sheet_url = f"https://open.larksuite.com/open-apis/sheets/v3/spreadsheets/{base_token_tvv}"
    r_sheet = requests.get(sheet_url, headers=headers, timeout=10)
    print("\nSpreadsheet Info status:", r_sheet.status_code)
    print("Spreadsheet Info response:", r_sheet.text[:1000])

    # Test Spreadsheet v2 Metainfo
    sheet_v2_url = f"https://open.larksuite.com/open-apis/sheets/v2/spreadsheets/{base_token_tvv}/metainfo"
    r_sheet_v2 = requests.get(sheet_v2_url, headers=headers, timeout=10)
    print("\nSpreadsheet v2 Metainfo status:", r_sheet_v2.status_code)
    print("Spreadsheet v2 Metainfo response:", r_sheet_v2.text[:1000])

if __name__ == "__main__":
    main()
