

def get_appointments(date,user):
    meta = user.get("metadata","appointments",{})
    appoint = meta.get("appointments",{})
    
    return appoint.get(date, [])