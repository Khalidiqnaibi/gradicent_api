

def get_appointments(date,user):
    meta = user.get("metadata",{})
    appoint = meta.get("appointments",{})
    
    return appoint.get(date, [])