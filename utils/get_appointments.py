

def get_appointments(date,user):
    appoint = user.get("appointments",{})
    
    return appoint.get(date, [])