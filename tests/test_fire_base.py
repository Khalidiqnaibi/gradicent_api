from  config import DefaultConfig
import firebase_admin , os
from firebase_admin import credentials , initialize_app ,db

from typing import Optional

config = DefaultConfig()

def _resolve_file_path(path_from_config: str) -> str:
    """
    Try to make config paths robust:
    - If path exists as given, return it.
    - Otherwise, try to resolve it relative to project base dir.
    - Otherwise return the original (so caller can fail with a clear error).
    """
    if not path_from_config:
        return path_from_config

    # if already absolute and exists, use it
    if os.path.isabs(path_from_config) and os.path.exists(path_from_config):
        return path_from_config

    # attempt to resolve relative to project base dir
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidate = os.path.join(base_dir, os.path.basename(path_from_config))
    if os.path.exists(candidate):
        return candidate

    # last attempt: join full relative path from base_dir
    candidate2 = os.path.join(base_dir, path_from_config)
    if os.path.exists(candidate2):
        return candidate2

    # give back original — caller will likely raise useful error if it's wrong
    return path_from_config


firebase_cred_path = _resolve_file_path(config.FIREBASE["credentials_path"])
oauth_secrets_path = _resolve_file_path(config.OAUTH_CLIENT_SECRETS_FILE)

if not os.path.exists(firebase_cred_path):
    raise RuntimeError(f"Firebase credentials file not found: {firebase_cred_path}")
# Initialize Firebase only once (safe for reloading)
cred = credentials.Certificate(firebase_cred_path)
if not firebase_admin._apps:
    initialize_app(cred, {
        'databaseURL': config.FIREBASE["databaseURL"],
        'storageBucket': config.FIREBASE["storageBucket"]
    })


def _nested_ref(
        user_id: str,
        collection: str,
        child_id: str,
        nested: str,
        nested_id: Optional[str] = None,
    ):
        ref = db.reference(f"/Gradicent/business/{user_id}/{collection}/{child_id}/{nested}")
        return ref if not nested_id else ref.child(str(nested_id))


def add_nested(user_id, collection, child_id, nested, obj):
        ref = _nested_ref(user_id, collection, child_id, nested)
        content = ref.get()
        if isinstance(content,list) :
            nested_id = len(content)
            print("list")
            full_ref = _nested_ref(user_id,collection,child_id,nested,nested_id).set(obj)
        elif content:
            nested_id = 1
            interactions = {0:content,1:obj}
            full_ref = _nested_ref(user_id,collection,child_id,nested).set(interactions)
        else:
            nested_id = 0
            interactions = {0:obj}
            full_ref = _nested_ref(user_id,collection,child_id,nested).set(interactions)
        
        print(nested_id) 
        print(content)
        print(full_ref.get())


add_nested("101597446369752496399","clients",'0',"interactions",{
  "amount": 0,
  "balance": 0,
  "date": "2026-01-02",
  "description": "",
  "handled_by": "",
  "notes": "",
  "paid": 0,
  "service_name": "rdfdgdg",
  "vno": 1
})