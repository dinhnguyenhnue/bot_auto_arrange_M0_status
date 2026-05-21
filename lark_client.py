import time
import logging
import requests
from typing import Dict, Any, List, Optional
import config

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

class LarkClient:
    def __init__(self):
        self.app_id = config.LARK_APP_ID
        self.app_secret = config.LARK_APP_SECRET
        self.base_token = config.LARK_BASE_TOKEN
        self._token: Optional[str] = None
        self._token_expires_at: float = 0.0

    def get_token(self) -> str:
        """Get the cached tenant_access_token or request a new one if expired."""
        current_time = time.time()
        # If token is still valid (with a 5-minute safety buffer)
        if self._token and current_time < self._token_expires_at - 300:
            return self._token

        url = "https://open.larksuite.com/open-apis/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        
        try:
            logger.info("Requesting new tenant_access_token...")
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") == 0:
                self._token = data.get("tenant_access_token")
                # expire_seconds = data.get("expire", 7200)
                # For safety, use 7200 or the API-provided expire time
                expire_seconds = data.get("expire", 7200)
                self._token_expires_at = current_time + expire_seconds
                logger.info("Successfully fetched tenant_access_token.")
                return self._token
            else:
                raise ValueError(f"Failed to get token from Lark: {data.get('msg')} (code: {data.get('code')})")
        except Exception as e:
            logger.error(f"Error fetching tenant_access_token: {e}")
            raise

    def get_headers(self) -> Dict[str, str]:
        """Get standard headers with the Bearer authorization token."""
        token = self.get_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8"
        }

    def list_records(self, table_id: str, filter_json: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        List all records from a table, automatically handling pagination.
        
        :param table_id: Bitable table ID
        :param filter_json: Optional filter JSON body for the API
        :return: List of record dictionaries (containing record_id and fields)
        """
        url = f"https://open.larksuite.com/open-apis/bitable/v1/apps/{self.base_token}/tables/{table_id}/records"
        records = []
        page_token = None
        has_more = True
        
        while has_more:
            params = {
                "page_size": 500,
            }
            if page_token:
                params["page_token"] = page_token

            headers = self.get_headers()
            
            try:
                # Lark's List Records is GET
                # If we have a filter, we can pass it as a JSON payload or in the query.
                # Actually, standard GET request doesn't take a JSON body, but Lark's API accepts filter parameter.
                # If we need complex filtering, we will do it in-memory to prevent complex URL encoding and API mismatches.
                response = requests.get(url, headers=headers, params=params, timeout=15)
                response.raise_for_status()
                data = response.json()
                
                if data.get("code") == 0:
                    page_data = data.get("data", {})
                    items = page_data.get("items", [])
                    records.extend(items)
                    
                    has_more = page_data.get("has_more", False)
                    page_token = page_data.get("page_token")
                else:
                    raise ValueError(f"Error listing records: {data.get('msg')} (code: {data.get('code')})")
            except Exception as e:
                logger.error(f"Failed to list records for table {table_id}: {e}")
                raise
                
        return records

    def get_record(self, table_id: str, record_id: str) -> Dict[str, Any]:
        """
        Fetch a single record by its ID.
        """
        url = f"https://open.larksuite.com/open-apis/bitable/v1/apps/{self.base_token}/tables/{table_id}/records/{record_id}"
        headers = self.get_headers()
        try:
            logger.info(f"Fetching record {record_id} from table {table_id}...")
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data.get("code") == 0:
                return data.get("data", {}).get("record", {})
            else:
                raise ValueError(f"Failed to get record: {data.get('msg')} (code: {data.get('code')})")
        except Exception as e:
            logger.error(f"Error fetching record {record_id}: {e}")
            raise

    def update_record(self, table_id: str, record_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update fields of a single record.
        """
        url = f"https://open.larksuite.com/open-apis/bitable/v1/apps/{self.base_token}/tables/{table_id}/records/{record_id}"
        payload = {"fields": fields}
        headers = self.get_headers()
        
        try:
            logger.info(f"Updating record {record_id} in table {table_id}...")
            response = requests.put(url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") == 0:
                logger.info(f"Successfully updated record {record_id}.")
                return data.get("data", {})
            else:
                raise ValueError(f"Failed to update record: {data.get('msg')} (code: {data.get('code')})")
        except Exception as e:
            logger.error(f"Error updating record {record_id}: {e}")
            raise

    def batch_update_records(self, table_id: str, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Batch update records. Max 500 records at a time.
        
        :param records: List of dicts, each with keys 'record_id' and 'fields'.
                        Example: [{'record_id': 'rec1', 'fields': {'Status': 'Completed'}}]
        """
        if not records:
            return {}
            
        url = f"https://open.larksuite.com/open-apis/bitable/v1/apps/{self.base_token}/tables/{table_id}/records/batch_update"
        headers = self.get_headers()
        
        # Split into chunks of 500 records
        chunk_size = 500
        for i in range(0, len(records), chunk_size):
            chunk = records[i:i + chunk_size]
            payload = {"records": chunk}
            
            try:
                logger.info(f"Batch updating {len(chunk)} records in table {table_id}...")
                response = requests.post(url, headers=headers, json=payload, timeout=15)
                response.raise_for_status()
                data = response.json()
                
                if data.get("code") != 0:
                    raise ValueError(f"Failed to batch update records: {data.get('msg')} (code: {data.get('code')})")
            except Exception as e:
                logger.error(f"Error batch updating records: {e}")
                raise
                
        logger.info(f"Successfully batch updated {len(records)} records.")
        return {"code": 0, "msg": "success"}
