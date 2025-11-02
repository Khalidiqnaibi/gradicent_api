'''
user_service.py
----------------
User service module for managing user data.
'''
from firebase_admin import db
from flask import session
from datetime import datetime

def get_userD(google_id):
        if 'binder' in session and session['binder']== 'lab':
            session['wtype']='lab'

        typee=session.get('wtype', 'drs')
        drssref = db.reference(f'/{typee}/{google_id}')
        doc = drssref.get()
        name = session.get("name")
        source = session.get("source","organic")
        year=datetime.now().year

        if doc:
            user_data=dict(doc)

            return user_data
        else:
            user_data = {
                        "no":1,
                        "first": datetime.now().isoformat(),
                        "google_id": google_id,
                        "name": name,
                        "source":source,
                        "payed": 0,
                        "plan": "free",
                        'settings':{
                            'msg':'',
                            'pkey':"",
                            "send":False,
                            'drname':''
                        },
                        "patients":[
                            {
                                "location" :"",
                                "age":1000,"debit" :0,
                                "phone":0,
                                "pmh":"","allergies":"",
                                "visits":
                                    [
                                        {
                                            "debit":0,"details" :"",
                                            "diagnosis":" " ,
                                            "lab":"",
                                            "height":"",
                                            "wight":"",
                                            "treatment":"",
                                            "visit_date":f"{year}-01-01",
                                            "drname":'',
                                            "printed":False,#if the visit is printed u cant change the data
                                            "vno" :1 
                                        }
                                    ],
                                "id":0,"name":"",
                                'btype':''
                            }
                        ]
                }
            drssref.set(user_data)
            #doc_ref.set(user_data)
        return user_data
    
def get_user_info_by_google_id(google_id):
    # Reference to the Firebase Realtime Database
    ref = db.reference('/users')  # '/users' is the path where user data is stored

    # Query the database to find the user with the matching google_id
    query = ref.order_by_child('google_id').equal_to(google_id).limit_to_first(1)

    # Execute the query
    result = query.get()

    if not result:
        # User with the provided google_id not found
        return None

    # The result is a dictionary where keys are unique identifiers (Firebase push IDs)
    # We need to extract the user data from this dictionary
    user_id, user_data = next(iter(result.items()))

    if user_id:
        print("User found:")
        return user_data
    else:
        return None

class UserService:
    def __init__(self, storage):
        self.storage = storage

    def create_user(self, user_data):
        # Logic to create a user
        pass

    def get_user(self, user_id):
        # Logic to retrieve a user
        pass

    def update_user(self, user_id, user_data):
        # Logic to update a user
        pass

    def delete_user(self, user_id):
        # Logic to delete a user
        pass