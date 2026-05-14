import os
import uuid
import re
from typing import Any, Dict, List, Optional
from supabase import create_client, Client
from ..interfaces.storage_adapter import StorageAdapter

def normalize_digits(s: str) -> str:
    return re.sub(r"\D", "", s or "")

def normalize_gov_id(s: str) -> str:
    return re.sub(r"[\s\-]", "", (s or "")).upper()

class SupabaseAdapter(StorageAdapter):
    def __init__(self,url: str = "", key: str = ""):
        self.supabase: Client = create_client(url, key)
        self.table_map = {
            "users": os.getenv("DB_TABLE_USERS", "user_accounts_v1"),
            "clients": os.getenv("DB_TABLE_CLIENTS", "CRM_entities_v1"),
            "employees": os.getenv("DB_TABLE_EMPLOYEES", "EMPLOYEE_entities_v1"),
            "products": os.getenv("DB_TABLE_PRODUCTS", "prod_v1"),
            "services": os.getenv("DB_TABLE_SERVICES", "service_catalog_v1"),
            "interactions": os.getenv("DB_TABLE_INTERACTIONS", "CRM_log_v1"),
            "transactions": os.getenv("DB_TABLE_TRANSACTIONS", "CRM_ledger_v1"),
        }

    def _get_table(self, collection: str) -> str:
        return self.table_map.get(collection, collection)

    def _format_result(self, data: List[Dict]) -> List[Dict]:
        return [{"id": row["id"], **row.get("record_data", {})} for row in data]

    def _normalize_payload(self, obj: Dict) -> Dict:
        """Normalizes searchable fields BEFORE saving to the DB."""
        payload = obj.copy()
        if "gov_id" in payload:
            payload["gov_id"] = normalize_gov_id(payload["gov_id"])
        if "phone" in payload:
            payload["phone"] = normalize_digits(payload["phone"])
        # Standardize role/sku to lowercase for easier exact matching
        if "role" in payload:
            payload["role"] = (payload["role"] or "").lower()
        if "metadata" in payload and "sku" in payload["metadata"]:
            payload["metadata"]["sku"] = (payload["metadata"]["sku"] or "").lower()
        return payload

    def add_child(self, domain: str, user_id: str, collection: str, obj: Dict) -> str:
        table = self._get_table(collection)
        child_id = obj.get("id", str(uuid.uuid4())) 
        
        clean_obj = self._normalize_payload(obj)
        
        payload = {
            "id": child_id,
            "domain": domain,
            "owner_id": user_id,
            "record_data": clean_obj
        }
        self.supabase.table(table).insert(payload).execute()
        return child_id

    def update_child(self, domain: str, user_id: str, collection: str, patch: Dict, child_id: str = None) -> None:
        table = self._get_table(collection)
        existing = self.get_child(domain, user_id, collection, child_id)
        if existing:
            updated_data = {**existing, **patch}
            updated_data = self._normalize_payload(updated_data)
            updated_data.pop("id", None) 
            self.supabase.table(table).update({"record_data": updated_data}).eq("id", child_id).execute()

    def find_children_by_field(self, domain: str, user_id: str, collection: str, field: str, value: Any) -> List[Dict]:
        table = self._get_table(collection)
        # SQL: SELECT * WHERE record_data->>'field' = 'value'
        response = self.supabase.table(table).select("*") \
            .eq("domain", domain).eq("owner_id", user_id) \
            .eq(f"record_data->>{field}", str(value)).execute()
        return self._format_result(response.data)

    def find_by_gov_id(self, domain: str, user_id: str, collection: str, gov_id: str) -> List[Dict]:
        table = self._get_table(collection)
        target = normalize_gov_id(gov_id)
        response = self.supabase.table(table).select("*") \
            .eq("domain", domain).eq("owner_id", user_id) \
            .eq("record_data->>gov_id", target).execute()
        return self._format_result(response.data)

    def find_by_phone(self, domain: str, user_id: str, collection: str, phone: str) -> List[Dict]:
        table = self._get_table(collection)
        target = normalize_digits(phone)
        response = self.supabase.table(table).select("*") \
            .eq("domain", domain).eq("owner_id", user_id) \
            .eq("record_data->>phone", target).execute()
        return self._format_result(response.data)

    def find_by_name_substring(self, domain: str, user_id: str, collection: str, name: str) -> List[Dict]:
        table = self._get_table(collection)
        response = self.supabase.table(table).select("*") \
            .eq("domain", domain).eq("owner_id", user_id) \
            .ilike("record_data->>name", f"%{name}%").execute()
        return self._format_result(response.data)

    def find_children_by_nested_field(self, domain: str, user_id: str, collection: str, parent_key: str, child_key: str, value: str) -> List[Dict]:
        """ Replaces the old lambda predicate for things like metadata/sku """
        table = self._get_table(collection)
        # SQL: SELECT * WHERE record_data->'metadata'->>'sku' = 'value'
        response = self.supabase.table(table).select("*") \
            .eq("domain", domain).eq("owner_id", user_id) \
            .eq(f"record_data->{parent_key}->>{child_key}", value.lower()).execute()
        return self._format_result(response.data)