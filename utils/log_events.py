from datetime import datetime


def log_with_service(service, event_type, metadata=None):
    """Save user activity for analytics"""
    log_with_binder(service._binder,event_type,metadata)
    
def log_time(service, seconds):
    """Save user time spend using binder for analytics"""
    now = datetime.now()
    meta = service._binder.adapter.get_child(service._binder.domain,service._binder.current_user,"metadata")
    meta["analytics"] = meta.get("analytics" , {})
    meta["analytics"][now.date().isoformat()] = meta["analytics"].get(now.date().isoformat(),{})
    meta["analytics"][now.date().isoformat()]["time_tracking"] = meta["analytics"][now.date().isoformat()].get("time_tracking",[])
    meta["analytics"][now.date().isoformat()]["time_tracking"].append({
        "seconds": seconds,
        "timestamp": now.isoformat()
    })
    service._binder.adapter.update_child(service._binder.domain,service._binder.current_user,"metadata",meta)


def log_with_binder(binder, event_type, metadata=None):
    """Save user activity for analytics"""
    now = datetime.now()
    meta = binder.adapter.get_child(binder.domain,binder.current_user,"metadata")
    if not meta.get("analytics"):
        meta["analytics"] = meta.get("analytics" , {})
    
    if not meta.get(now.date().isoformat()) :
        meta["analytics"][now.date().isoformat()] = meta["analytics"].get(now.date().isoformat(),{})
    
    if not meta["analytics"][now.date().isoformat()].get("events") :
        meta["analytics"][now.date().isoformat()]["events"] = meta["analytics"][now.date().isoformat()].get("events",[])
    
    meta["analytics"][now.date().isoformat()]["events"].append({
        "user": binder.current_user,
        "type": event_type,
        "meta": metadata or {},
        "timestamp":now.isoformat()
    })
    binder.adapter.update_child(binder.domain,binder.current_user,"metadata",meta)