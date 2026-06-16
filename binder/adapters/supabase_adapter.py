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
            "events": os.getenv("DB_TABLE_EVENTS", "analytics_events_v1"),
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
    
    def update_user(self, domain: str, user_id: str, user_data: Dict[str, Any]) -> None:
        table = self._get_table("users")
        self.supabase.table(table).upsert({
            "id": user_id,
            "domain": domain,
            "record_data": user_data
        }).execute()

    def delete_user(self, domain: str, user_id: str) -> None:
        table = self._get_table("users")
        self.supabase.table(table).delete().eq("id", user_id).eq("domain", domain).execute()

    def add_user(self, domain: str, user_id: str, user: Dict) -> None:
        table = self._get_table("users")
        self.supabase.table(table).upsert({
            "id": user_id,
            "domain": domain,
            "record_data": user
        }).execute()

    def get_user(self, domain: str, user_id: str) -> Optional[Dict]:
        table = self._get_table("users")
        response = self.supabase.table(table).select("*").eq("id", user_id).eq("domain", domain).execute()
        if response.data:
            return self._format_result(response.data)[0]
        return None

    def update_user(self, domain: str, user_id: str, user: Dict) -> None:
        self.add_user(domain, user_id, user) 

    def delete_user(self, domain: str, user_id: str) -> None:
        table = self._get_table("users")
        self.supabase.table(table).delete().eq("id", user_id).eq("domain", domain).execute()

    def add_child(self, domain: str, user_id: str, collection: str, obj: Dict) -> str:
        table = self._get_table(collection)
        response = self.supabase.table(table).select("id", count="exact").eq("domain", domain).eq("owner_id", user_id).execute()
        count = response.count if response.count is not None else 0
        child_id = str(count + 1)
        
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

    def list_children(
        self, domain: str, user_id: str, collection: str, limit: int = 30, start_at: Optional[str] = None
    ) -> List[Dict]:
        table = self._get_table(collection)
        query = self.supabase.table(table).select("*").eq("domain", domain).eq("owner_id", user_id).limit(limit)
        
        # Pagination using Postgres offset or ID bounds (simplified for adapter)
        if start_at:
            query = query.gte("id", start_at) 
            
        response = query.execute()
        return self._format_result(response.data)

    def get_child(self, domain: str, user_id: str, collection: str, child_id: str = None) -> Any:
        table = self._get_table(collection)
        response = self.supabase.table(table).select("*").eq("id", child_id).eq("domain", domain).eq("owner_id", user_id).execute()
        if response.data:
            return self._format_result(response.data)[0]
        return {}

    def delete_child(self, domain: str, user_id: str, collection: str, child_id: str = None) -> None:
        table = self._get_table(collection)
        self.supabase.table(table).delete().eq("id", child_id).eq("domain", domain).eq("owner_id", user_id).execute()

    def list_child(self, domain: str, user_id: str, collection: str, limit: int = 30, start_at: Optional[str] = None) -> List[Dict]:
        table = self._get_table(collection)
        query = self.supabase.table(table).select("*").eq("domain", domain).eq("owner_id", user_id).order("id")
        if start_at:
            query = query.gte("id", start_at)
        query = query.limit(limit)
        response = query.execute()
        return self._format_result(response.data)

    def list_nested(self, domain: str, user_id: str, collection: str, child_id: str, nested: str, limit: int = 30, start_at: Optional[str] = None) -> List[Dict]:
        table = self._get_table(nested)
        query = self.supabase.table(table).select("*").eq("domain", domain).eq("owner_id", user_id).eq("parent_id", child_id).order("id")
        if start_at:
            query = query.gte("id", start_at)
        query = query.limit(limit)
        response = query.execute()
        return self._format_result(response.data)

    def log_event(self, domain: str, user_id: str, event_code: int, event_name: str, entity_id: str = None, metadata: dict = None):
        table = self._get_table("events")
        data = {
            "domain": domain,
            "user_id": user_id,
            "event_code": event_code,
            "event_name": event_name,
            "entity_id": entity_id,
            "metadata": metadata or {}
        }
        return self.supabase.table(table).insert(data).execute()

    def add_nested(self, domain: str, user_id: str, collection: str, child_id: str, nested: str, obj: Dict) -> str:
        table = self._get_table(nested)
        response = self.supabase.table(table).select("id", count="exact").eq("domain", domain).eq("owner_id", user_id).execute()
        count = response.count if response.count is not None else 0
        nested_id = str(count + 1)
        
        payload = {
            "id": nested_id,
            "domain": domain,
            "owner_id": user_id,
            "parent_id": child_id,
            "record_data": obj
        }
        self.supabase.table(table).insert(payload).execute()
        return nested_id

    def update_nested(self, domain: str, user_id: str, collection: str, child_id: str, nested: str, nested_id: str, patch: Dict) -> None:
        table = self._get_table(nested)
        self.supabase.table(table).update({"record_data": patch}).eq("id", nested_id).eq("parent_id", child_id).execute()

    def delete_nested(self, domain: str, user_id: str, collection: str, child_id: str, nested: str, nested_id: str) -> None:
        table = self._get_table(nested)
        self.supabase.table(table).delete().eq("id", nested_id).eq("parent_id", child_id).execute()

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