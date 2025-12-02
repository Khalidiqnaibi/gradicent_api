from firebase_admin import db  
from flask import jsonify

def get_appopintments(adapter,date,user_id):
    user=adapter.get_user(user_id=user_id)
    dr_ref = db.reference(f'/drs/{user_id}/msg')
    nn=dr_ref.get()

    #today_key = datetime.now().date().isoformat()
    
    return nn.get(date, [])