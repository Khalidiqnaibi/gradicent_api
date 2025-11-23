from datetime import datetime
import secrets
import string

from firebase_admin import db


def save_code(code,plan,gid=""):
    # Reference to the Firebase Realtime Database
    ref = db.reference('/codes')  # '/codes' is the path where you want to store codes ref.order_by_child('code').equal_to(code)

    v= {"code":code,"date":datetime.now().date().isoformat(),'plan':plan,"used":False,"google_id":gid}
    # Push the code to the database

    ref.child(code).set(v)
    #new_code_ref = ref.push(v)

def save_seccode(code,domain,gid=""):

    v= {"code":code,"date":datetime.now().date().isoformat(),'plan':'sec',"users":0,"google_id":gid}
    if domain == "medical" :
        typee='drs' 
    elif domain=="business" :
        typee = "business"
    else :
        typee = domain
    dr_ref = db.reference(f'/{typee}/{gid}')
    nn=dr_ref.get()
    if 'settings' not in nn:
        nn["settings"]={'ac':v}
    else:
        nn["settings"]['ac']=v
    dr_ref.update(nn)

def generate_strong_password(length=12):
    characters = string.ascii_letters + string.digits
    password = ''.join(secrets.choice(characters) for _ in range(length))
    return password

def gencode():
    code=f"{generate_strong_password(4)}-{generate_strong_password(4)}-{generate_strong_password(4)}"
    return code