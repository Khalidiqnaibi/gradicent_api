import os
import io  # Import the io module
import shutil
import pathlib
import json
import html
import requests
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
from flask import sessions, Flask, jsonify, render_template, redirect, request, session, url_for, abort, send_file,make_response
from google.oauth2 import id_token
from datetime import datetime,timedelta
from google_auth_oauthlib.flow import Flow
from pip._vendor import cachecontrol
import google.auth.transport.requests
import webbrowser
import firebase_admin
from firebase_admin import credentials, db, firestore, storage
from google.cloud.firestore_v1.base_query import FieldFilter
from werkzeug.utils import secure_filename
from io import BytesIO
import paypalrestsdk
from paypalrestsdk import Payment
import secrets
import uuid
import string
from zenora import APIClient
import logging
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from time import sleep
from urllib.parse import quote
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

appname='Binder'
cname='RiaSoftware'
app = Flask(f"{cname} Api",static_url_path='/home/RiaSoftware/s/static',template_folder='/home/RiaSoftware/s/templates')


app.secret_key = "abcdefghijk123"
appurl='http://www.bindersoftware.com'
basicprice=22
premprice=300
medprice=215
global bPay
bPay =False
global closee
closee =False
global prePay
prePay= False
global password
password = "@Ksoftkhaafif1"  # Change this to your secure password

dCLIENT_ID = 1215723302987890758
CLIENTtt_SECRET = "pN9VuIwixzDvVIy6AaCKh2pQGNggWBKz"
REDIRECccT_URI ="http://www.bindersoftware.com/addcomm/callback"
BOTtt_TOKEN ="MTIxNTcyMzMwMjk4Nzg5MDc1OA.G5QNR9.ltin2yRaszigZAg-acMsgsRc_2bg8jG675AMUA"


# Initialize Firebase with your Firebase project's credentials
cred = credentials.Certificate(r"/home/RiaSoftware/s/key2.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://monydb-f2cdb-default-rtdb.europe-west1.firebasedatabase.app/',
    'storageBucket': 'monydb-f2cdb.appspot.com'
})
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

GOOGLE_CLIENT_ID = "107932074863-nlil9n5j9lmahqfb15cmn52u59evpse9.apps.googleusercontent.com"
client_secrets_file = os.path.join(pathlib.Path(__file__).parent, r"/home/RiaSoftware/s/client_secret1.json")

flow = Flow.from_client_secrets_file(
    client_secrets_file=client_secrets_file,
    scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email", "openid"],
    redirect_uri=f"{appurl}/callback"
)
def nameee():
    session['appname']=appname

def create_fernet():
    global password
    password = password.encode()  # Convert password to bytes
    salt = b"MY_Potatolikesme_too"  # Change this to a unique salt
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        iterations=100000,  # Adjust the number of iterations as needed
        salt=salt,
        length=32  # The length of the derived key
    )
    key = base64.urlsafe_b64encode(kdf.derive(password))  # Derive key
    return Fernet(key)

def encrypt_data(data):
    if isinstance(data, int):  # Convert integers to string before encryption
        data = str(data)
    return fernet.encrypt(data.encode())  # Convert to bytes and encrypt

def decrypt_data(encrypted_data):
    try:
        if isinstance(encrypted_data, str):
            encrypted_data = encrypted_data.encode()  # Convert to bytes if necessary
        decrypted_data = fernet.decrypt(encrypted_data).decode()  # Decrypt and decode to string

        # Try to convert back to integer if it was originally an integer
        if decrypted_data.isdigit():
            return int(decrypted_data)

        return decrypted_data  # Return the string if it's not an integer
    except InvalidToken:
        # Handle decryption failure (e.g., incorrect password or corrupted data)
        return None
    except TypeError as e:
        # Handle errors due to incorrect types
        print(f"TypeError: {e}")
        return None

def load_user_data():
        path = f"C:/{cname}/{appname}/user_data.txt"

        user_data = {
            "first": '2001-01-01',
            "google_id": 1,
            "name": "non",
            "payed": 0
        }

        if not os.path.exists(f"C:/{cname}"):
            os.makedirs(f"C:/{cname}")

        if not os.path.exists(f"C:/{cname}/{appname}"):
            os.makedirs(f"C:/{cname}/{appname}")

        if path and os.path.exists(path):
            with open(path, "rb") as json_file:
                encrypted_data = json_file.read()
                user_data = decrypt_data(encrypted_data)

        return user_data

def load_app_data():
        app_data_path = f"C:/{cname}/{appname}/data.txt"

        if not os.path.exists(f"C:/{cname}"):
            os.makedirs(f"C:/{cname}")

        if not os.path.exists(f"C:/{cname}/{appname}"):
            os.makedirs(f"C:/{cname}/{appname}")

        if os.path.exists(app_data_path):
            with open(app_data_path, 'rb') as file:
                encrypted_data = file.read()
                app_data = decrypt_data(encrypted_data)
        else:
            save_app_data()

        apiurl = app_data.get('url', '')  # Assuming 'url' might not always be present

        return app_data

def login_is_required(function):
    def wrapper(*args, **kwargs):
        if "google_id" not in session:
            return abort(401)  # Authorization required
        else:
            return function()

    return wrapper

def iscode(code):
    # Reference to the Firebase Realtime Database
    ref = db.reference('/codes')
    # Query the database to find the user with the matching google_id
    query = ref.order_by_child('code').equal_to(code).limit_to_first(1)

    # Execute the query
    result = query.get()

    if not result:
        # User with the provided google_id not found
        return None

    user_id, user_data = next(iter(result.items()))

    session['cd']=user_data

    if user_id and not user_data['used']:
        return user_data['plan']
    else:
        return None

def quittab():
    # Get a list of open browser tabs
    browser_tabs = webbrowser.get().tab_list()

    # Check if any tabs match the condition
    for tab in browser_tabs:
        if tab.url.endswith('/protected_area'):
            # Close the tab if the URL ends with '/protected_area'
            tab.close()

def add_user(user_data):
    # Reference to the Firebase Realtime Database
    ref = db.reference('/users')  # '/users' is the path where you want to store user data

    # Push user data to the database
    new_user_ref = ref.push(user_data)

def save_code(code,plan,gid=""):
    # Reference to the Firebase Realtime Database
    ref = db.reference('/codes')  # '/codes' is the path where you want to store codes ref.order_by_child('code').equal_to(code)

    v= {"code":code,"date":datetime.now().date().isoformat(),'plan':plan,"used":False,"google_id":gid}
    # Push the code to the database

    ref.child(code).set(v)
    #new_code_ref = ref.push(v)

def save_seccode(code,gid=""):

    v= {"code":code,"date":datetime.now().date().isoformat(),'plan':'sec',"users":0,"google_id":gid}
    typee=session.get('wtype', 'drs')
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

def create_patient_document(patient):
    # Create a new Document
    doc = Document()

    # Add the doctor's name as the title, bold and centered
    doctor_name = patient.get("dr", "Unknown Doctor")
    title = doc.add_heading(level=1)
    run = title.add_run(f"{doctor_name}")
    run.bold = True
    title.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    patient_no = session['patientno']+1

    # Add patient details
    doc.add_heading(f"Patient Name: {patient.get('name', 'Unknown')}", level=2)
    doc.add_paragraph(f"ID No.: {patient.get('id', ' ')}")
    doc.add_paragraph(f"Patient No.: {patient_no}")
    doc.add_paragraph(f"Location: {patient.get('location', ' ')}")
    doc.add_paragraph(f"Age: {patient.get('age', ' ')}")
    doc.add_paragraph(f"Phone: {patient.get('phone', ' ')}")
    doc.add_paragraph(f"Past Medical History: {patient.get('pmh', ' ')}")
    doc.add_paragraph(f"Allergies: {patient.get('allergies', ' ')}")
    nnn=patient.get('next', ' ')
    if nnn == "<built-in method date of datetime.datetime object at 0x79d2fbd5a700>":
        nnn=' '
    doc.add_paragraph(f"Next visit: {nnn}")

    for visit in patient.get("visits", []):
        table = doc.add_table(rows=6, cols=2)

        table.style = 'Table Grid'
        cells = table.rows[0].cells

        cells[0].text = 'Visit No:'
        cells[1].text = str(visit.get('vno', 'N/A'))
        cells = table.rows[1].cells

        cells[0].text = 'Visit Date:'
        cells[1].text = visit.get('visit_date', 'N/A')
        cells = table.rows[2].cells

        cells[0].text = 'Diagnosis:'
        cells[1].text = visit.get('diagnosis', 'N/A')
        cells = table.rows[3].cells

        cells[0].text = 'Notes:'
        cells[1].text = str(visit.get('details', 'N/A'))
        cells = table.rows[4].cells

        cells[0].text = 'Lab Results:'
        cells[1].text = visit.get('lab', 'N/A')
        cells = table.rows[5].cells

        cells[0].text = 'Treatment:'
        cells[1].text = visit.get('treatment', 'N/A')

        # Add a line break after each visit
        doc.add_paragraph("\n")

    # Save the document to an in-memory file-like object
    file_stream = io.BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)
    n=patient.get('name', 'Unknown')
    return file_stream, f"{n.replace(' ', '_')}_data.docx"

def create_visit_document(patient,vno):
    # Create a new Document
    doc = Document()

    # Add the doctor's name as the title, bold and centered
    doctor_name = patient.get("dr", "Unknown Doctor")
    title = doc.add_heading(level=1)
    run = title.add_run(f"{doctor_name}")
    run.bold = True
    title.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    patient_no = session['patientno']+1

    # Add patient details
    doc.add_heading(f"Patient Name: {patient.get('name', 'Unknown')}", level=2)
    doc.add_paragraph(f"ID No.: {patient.get('id', ' ')}")
    doc.add_paragraph(f"Patient No.: {patient_no}")
    doc.add_paragraph(f"Location: {patient.get('location', ' ')}")
    doc.add_paragraph(f"Age: {patient.get('age', ' ')}")
    doc.add_paragraph(f"Phone: {patient.get('phone', ' ')}")
    doc.add_paragraph(f"Past Medical History: {patient.get('pmh', ' ')}")
    doc.add_paragraph(f"Allergies: {patient.get('allergies', ' ')}")

    nnn=patient.get('next', ' ')
    if nnn == "<built-in method date of datetime.datetime object at 0x79d2fbd5a700>":
        nnn=' '
    doc.add_paragraph(f"Next visit: {nnn}")

    visit =patient["visits"][vno]

    if visit :
        table = doc.add_table(rows=6, cols=2)

        table.style = 'Table Grid'
        cells = table.rows[0].cells

        cells[0].text = 'Visit No:'
        cells[1].text = str(visit.get('vno', 'N/A'))
        cells = table.rows[1].cells

        cells[0].text = 'Visit Date:'
        cells[1].text = visit.get('visit_date', 'N/A')
        cells = table.rows[2].cells

        cells[0].text = 'Diagnosis:'
        cells[1].text = visit.get('diagnosis', 'N/A')
        cells = table.rows[3].cells

        cells[0].text = 'Notes:'
        cells[1].text = str(visit.get('details', 'N/A'))
        cells = table.rows[4].cells

        cells[0].text = 'Lab Results:'
        cells[1].text = visit.get('lab', 'N/A')
        cells = table.rows[5].cells

        cells[0].text = 'Treatment:'
        cells[1].text = visit.get('treatment', 'N/A')

        # Add a line break after each visit
        doc.add_paragraph("\n")

    # Save the document to an in-memory file-like object
    file_stream = io.BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)
    n=patient.get('name', 'Unknown')
    return file_stream, f"{n.replace(' ', '_')}_data.docx"

def get_appds_by_mac():
    user_ip = request.headers['X-Real-IP']
    # Reference to the Firebase Realtime Database
    ref = db.reference('/pcs')

    # Query the database to find the user with the matching mac_address
    query = ref.order_by_child('mac').equal_to(user_ip).limit_to_first(1)

    # Execute the query
    result = query.get()

    if not result:
        # User with the provided google_id not found
        return None

    # The result is a dictionary where keys are unique identifiers (Firebase push IDs)
    # We need to extract the user data from this dictionary
    d_id, app_data = next(iter(result.items()))

    if d_id:
        print("pc found:")
        return app_data
    else:
        return None

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

def get_db_temp():
    db_content =  get_user_info_by_google_id(1)['db']
    return db_content

def log_me_in(info):
    user_ip = request.headers['X-Real-IP']
    app_data=get_appds_by_mac()
    user_info= get_user_info_by_google_id(info['google_id'])
    if app_data:
        app_data['google_id']=info['google_id']
        ref = db.reference('/pcs')
        query = ref.order_by_child('mac').equal_to(user_ip).limit_to_first(1)
        result = query.get()
        appid, a_data = next(iter(result.items()))
        ref = db.reference('/pcs/'+ appid)
        ref.set(app_data)
    else:
        app_data = {
            'mac':user_ip,
            'google_id':info['google_id'],
            "payed": False,
            "plan": "free",
            "first": datetime.now().date().isoformat(),
            "url":appurl
            }
        add_appds(app_data)
    if not user_info:
        user_data = {
            "name": info['name'],
            "google_id": info['google_id'],
            "payed": 0,
            "plan":'free',
            "first": datetime.now().date().isoformat(),
        }
        add_user(user_data)
        session["plan"] = 'free'

def get_user_db_plz(google_id=10):
    user_data=get_user_info_by_google_id(google_id)

    if user_data and 'db' in user_data:
        return {'db':user_data['db']}
    else:
        try:
            response = requests.get(f"{appurl}/dbtemp")
            response.raise_for_status()  # Raise an exception for bad responses

            db_temp = response.json()
            return db_temp
        except requests.exceptions.RequestException as e:
            print(f"Failed to retrieve database: {e}")
            response = requests.get(f"{appurl}/dbtempplz")
            response.raise_for_status()  # Raise an exception for bad responses

            db_temp = response.json()
            return db_temp

def add_appds(data):
    # Reference to the Firebase Realtime Database
    ref = db.reference('/pcs')  # '/users' is the path where you want to store user data

    # Push user data to the database
    new_user_ref = ref.push(data)

def save_app_data(google_id=1):
    user_ip = request.headers['X-Real-IP']
    app_data = {
        'mac':user_ip,
        'google_id':google_id,
        "payed": False,
        "plan": "free",
        "first": datetime.now().date().isoformat(),
        "url":appurl
    }
    add_appds(app_data)
    return app_data

def get_pcs_by_mac(mac):
    # Reference to the Firebase Realtime Database
    ref = db.reference('/pcs')  # '/users' is the path where user data is stored

    # Query the database to find the user with the matching google_id
    query = ref.order_by_child('mac').equal_to(mac).limit_to_first(1)

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

fernet = create_fernet()

"""riasoftware api"""

@app.route("/")
def home():
    return render_template("index.html")#return "Are you lost?\n :)"# render_template(errors.html,msg='Are you lost?\n :)',err='Wow')

@app.route("/med")
def med():
    return render_template("med.html")

@app.route("/products")
def products():
    return render_template("watches.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/fillters")
def fillters():
    return render_template("fillters.html")

@app.route("/siraj")
def siraj():
    return render_template("madisyn.html")

@app.route("/hmmm")
def hmmm():
    return render_template("ap.html")

@app.route("/privacy")
def privacy():
    return render_template("privacy.html")

@app.route("/terms")
def terms():
    return render_template("terms.html")

@app.route("/ahha")
def fooled():
    return render_template("fooled.html")

@app.route("/Ar")
def homear():
    return render_template("indexar.html")

@app.route("/basic_sub")
def basicsub():
    nameee()
    return render_template("basic.html")

@app.route("/basic_sub_ar")
def basicsubar():
    nameee()
    return render_template("basic - ar.html")

@app.route("/med_sub")
def medbasic():
    session['appname']='Binder Medical'
    return render_template("basic.html")

@app.route("/medsub_ar")
def medbasicar():
    session['appname']='Binder Medical'
    return render_template("basic - ar.html")

@app.route("/Ekth-sAKY-KX-7NjnHTgIT085oc1j50T7c")
def codemebisc():
    return render_template('code_gen.html',code='')

@app.route("/Ekth-sAKY-KX-7NjnHTgIT085oc1j50T7")
def codmebisc():
    code=gencode()
    save_code(code,"basic")
    return render_template('code_gen.html',code=code)

@app.route("/codesec", methods=['POST'])
def codesec():
    if 'google_id' not in session or 'page' not in session:
        return jsonify({'error': 'Unauthorized access'}), 403
    if session['page'] not in ["settings"]:
        return jsonify({'error': 'Unauthorized access'}), 403

    code = request.json.get('code')
    if not code:
        return jsonify({'error': 'No code provided'}), 400

    typee=session.get('wtype', 'drs')
    dr_ref = db.reference(f'/{typee}/{session["google_id"]}')
    current_settings = dr_ref.child('settings').get()
    if current_settings and current_settings.get('ac', {}).get('code') == code:
        new_code = gencode()
        save_code(new_code, "sec", session["google_id"])
        save_seccode(new_code, session["google_id"])
        # Optionally delete the old code from /codes or update its status
        ref = db.reference(f'/codes/{code}')
        codes = ref.get()

        refff = db.reference(f'/{typee}/{code}')
        bshh = refff.get()

        if bshh:
            refff.delete()
        if codes and codes['code'] == code:
            ref.delete()
            return jsonify({'code': new_code})
        else:
            return jsonify({'error': 'Invalid code'}), 403
    else:
        return jsonify({'error': 'Invalid code'}), 403

@app.route('/ses')
def sess():
    i={}
    for j in session:
        i[j]=session[j]
    return i

@app.route('/check_bcode')
def check_Bactivation_code():
    global bPay
    gid=session['google_id']
    typee=session.get('wtype', 'drs')


    if 'cod' in session :
        activation_code = session['cod']
        ref = db.reference(f'/codes/{activation_code}')
        codes = ref.get()
        if activation_code in ["w>>b-J~PO-X8LJ"]:
            closee=True
            bPay=True
            return redirect("/basic_success")
        elif codes and typee == 'drs':###################
            gid=codes['google_id']
            reff = db.reference(f'/{typee}/{gid}/settings')
            bruh = reff.get()
            bruh['ac']['users']+=1
            reff.update(bruh)

            session['PLAN']='sec'
            session['google_id']=gid
            return redirect("/Binder_medical")
        else:
            c=iscode(activation_code)
            session['iscod']=c
            if c in['basic']:
                bPay=True
                return redirect("/basic_success")
            else:
                return redirect("/basic_cancel")
    else:
        return redirect("/basic_cancel")

@app.route('/check_bcode_ar')
def check_Bactivationar_code():
    gid=session['google_id']
    if 'cod' in session:
        activation_code = session['cod']
        c=iscode(activation_code)
        session['iscod']=c
        if c in['basic']:
            global bPay
            bPay=True
            return redirect("/basic_success_ar")
        else:
            return redirect("/basic_cancel_ar")
    else:
        return redirect("/basic_cancel_ar")

@app.route('/chk_bcode', methods=['POST'])
def chk_Bactivation_code():
    # Get the activation code from the request JSON
    data = request.get_json()
    activation_code = data.get('code')
    if activation_code:
        session["cod"] = activation_code
        return {"result":'accepted'}
    else:
        return {"result":'fail'}

@app.route('/backup_database', methods=['POST'])
def backup_database():
        # Get the activation code from the request JSON
        data = request.get_json()
        datab = data.get('db')
        if datab:
                user_info = load_user_data()


                gid=user_info['google_id']


                ref = db.reference('/users')
                query = ref.order_by_child('google_id').equal_to(gid).limit_to_first(1)
                result = query.get()
                c_id, c_data = next(iter(result.items()))

                c_data['db']=datab

                ref.child(c_id).set(c_data)
                return jsonify({"message": "Database backup successful"}), 200
        else:
            return jsonify({"error":"no data base found"}), 500

@app.route("/pay_basic_ar")
def paybasicar():
    global bPay
    if "google_id" in session:
        gid = session["google_id"]
        user_data = get_userD(gid)
        if 'PLAN' in session:
            PLAN = 'sec'
        else:
            PLAN = user_data['plan']
    else:
        return redirect("/fetchUserData")

    plan=str(user_data.get("plan"))
    logged_in = "google_id" in session
    if logged_in:
        if plan in ["fam"]:
            pass
        elif plan in ["free"]:
            try:
                paypalrestsdk.configure({
                "mode": "live",  # Use "live"sandbox in production
                "client_id": "AaH6jy2wDk69MEKa5aVYIwz06AMJwjym3qziA3wmF0qlbdKtcI-iIZCmj9qjK2mcHvEXgXbVnyq_6nP1",
                "client_secret": "EFFgbsOtPSMXBbRyivM5ogXekW4BMETUkjcBJf9LCMRuWGaqxTtAVOWHa30WkwP-w19eQ6b8aMHIxFf9"
                })
                payment = Payment({
                    "intent": "sale",
                    "payer": {
                        "payment_method": "paypal"
                    },
                    "transactions": [{
                        "amount": {
                            "total": f"{float(basicprice/2)}",
                            "currency": "USD"
                        }
                    }],
                    "redirect_urls": {
                        "return_url": f"{appurl}/basic_success",
                        "cancel_url": f"{appurl}/basic_cancel"
                    }
                })

                if payment.create():
                    for link in payment.links:
                        if link.method == "REDIRECT":
                            redirect_url = link.href
                            bPay=True
                            return redirect(redirect_url)
                else:
                    error_message = f"Error: {payment.error}"
                    return render_template("errors - ar.html",msg=error_message,err='Unexpected')
            except Exception as e:
                return render_template("errors - ar.html",msg=e,err='Unexpected')
        elif plan in ['basic']:
            try:
                paypalrestsdk.configure({
                "mode": "live",  # Use "live"sandbox in production
                "client_id": "AaH6jy2wDk69MEKa5aVYIwz06AMJwjym3qziA3wmF0qlbdKtcI-iIZCmj9qjK2mcHvEXgXbVnyq_6nP1",
                "client_secret": "EFFgbsOtPSMXBbRyivM5ogXekW4BMETUkjcBJf9LCMRuWGaqxTtAVOWHa30WkwP-w19eQ6b8aMHIxFf9"
                })
                payment = Payment({
                    "intent": "sale",
                    "payer": {
                        "payment_method": "paypal"
                    },
                    "transactions": [{
                        "amount": {
                            "total": f"{basicprice}.00",
                            "currency": "USD"
                        }
                    }],
                    "redirect_urls": {
                        "return_url": f"{appurl}/basic_success",
                        "cancel_url": f"{appurl}/basic_cancel"
                    }
                })

                if payment.create():
                    for link in payment.links:
                        if link.method == "REDIRECT":
                            redirect_url = link.href
                            bPay=True
                            return redirect(redirect_url)
                else:
                    error_message = f"Error: {payment.error}"
                    return render_template("errors - ar.html",msg=error_message,err='Unexpected')
            except Exception as e:
                return render_template("errors - ar.html",msg=e,err='Unexpected')
        else:
            return render_template("errors - ar.html",msg="plan issue",err='Unexpected')
    else:
        return render_template("errors - ar.html",msg="User not logged in",err='Unexpected')

@app.route("/pay_basic")
def paybasic():
    global bPay
    if "google_id" in session:
        gid = session["google_id"]
        user_data = get_userD(gid)

        if 'PLAN' in session:
            PLAN = 'sec'
        else:
            PLAN = user_data['plan']
    else:
        return redirect("/fetchUserData")

    plan=str(user_data.get("plan"))
    logged_in = "google_id" in session
    if logged_in:
        if plan in ["fam"]:
            pass
        elif plan in ["free"]:
            try:
                paypalrestsdk.configure({
                "mode": "live",  # Use "live"sandbox in production
                "client_id": "AaH6jy2wDk69MEKa5aVYIwz06AMJwjym3qziA3wmF0qlbdKtcI-iIZCmj9qjK2mcHvEXgXbVnyq_6nP1",
                "client_secret": "EFFgbsOtPSMXBbRyivM5ogXekW4BMETUkjcBJf9LCMRuWGaqxTtAVOWHa30WkwP-w19eQ6b8aMHIxFf9"
                })
                payment = Payment({
                    "intent": "sale",
                    "payer": {
                        "payment_method": "paypal"
                    },
                    "transactions": [{
                        "amount": {
                            "total": f"{float(basicprice/2)}",
                            "currency": "USD"
                        }
                    }],
                    "redirect_urls": {
                        "return_url": f"{appurl}/basic_success",
                        "cancel_url": f"{appurl}/basic_cancel"
                    }
                })

                if payment.create():
                    for link in payment.links:
                        if link.method == "REDIRECT":
                            redirect_url = link.href
                            bPay=True
                            return redirect(redirect_url)
                else:
                    error_message = f"Error: {payment.error}"
                    return render_template("errors.html",msg=error_message,err='Unexpected')
            except Exception as e:
                return render_template("errors.html",msg=e,err='Unexpected')
        elif plan in ['basic']:
            try:
                paypalrestsdk.configure({
                "mode": "live",  # Use "live"sandbox in production
                "client_id": "AaH6jy2wDk69MEKa5aVYIwz06AMJwjym3qziA3wmF0qlbdKtcI-iIZCmj9qjK2mcHvEXgXbVnyq_6nP1",
                "client_secret": "EFFgbsOtPSMXBbRyivM5ogXekW4BMETUkjcBJf9LCMRuWGaqxTtAVOWHa30WkwP-w19eQ6b8aMHIxFf9"
                })
                payment = Payment({
                    "intent": "sale",
                    "payer": {
                        "payment_method": "paypal"
                    },
                    "transactions": [{
                        "amount": {
                            "total": f"{basicprice}.00",
                            "currency": "USD"
                        }
                    }],
                    "redirect_urls": {
                        "return_url": f"{appurl}/basic_success",
                        "cancel_url": f"{appurl}/basic_cancel"
                    }
                })

                if payment.create():
                    for link in payment.links:
                        if link.method == "REDIRECT":
                            redirect_url = link.href
                            bPay=True
                            return redirect(redirect_url)
                else:
                    error_message = f"Error: {payment.error}"
                    return render_template("errors.html",msg=error_message,err='Unexpected')
            except Exception as e:
                return render_template("errors.html",msg=e,err='Unexpected')
        else:
            return render_template("errors.html",msg="plan issue",err='Unexpected')
    else:
        return render_template("errors.html",msg="User not logged in",err='Unexpected')

@app.route("/basic_success_ar")
def basic_successar():
    global bPay
    global closee
    if closee:
        gid=session['google_id']
        if 'google_id' in session :
            # Set 'plan' to 'basic' and update 'payed' with the amount paid
            activation_code = session['cod']
            ref = db.reference('/codes')
            query = ref.order_by_child('code').equal_to(activation_code).limit_to_first(1)
            result = query.get()
            c_id, c_data = next(iter(result.items()))
            c_data['google_id']=gid
            c_data['used']=True
            ref.child(c_id).set(c_data)

            google_id = session['google_id']
            drs_ref = db.reference('/drs')
            user_data = drs_ref.order_by_child('google_id').equal_to(google_id).get()
            if not user_data:
                return jsonify({"message": "User not found"}), 404
            user_data = list(user_data.values())[0]
            user_data['plan']="Fam"
            user_data['payed']=int(user_data['payed'])+basicprice
            user_data['first']=datetime.now().isoformat(),
            # Save the updated data back to Firebase
            drs_ref.child(google_id).update(user_data)
            # Return a response indicating success
            bPay=False
            #return render_template("pay_sucsess - ar.html")
            return redirect("/acc")
        else:
            bPay=False
            # Return a response indicating that the user information is not found
            return render_template("errors - ar.html",msg="User not loged in.",err='Unexpected')
    else:
        if bPay:
            gid=session['google_id']
            if 'google_id' in session :
                # Set 'plan' to 'basic' and update 'payed' with the amount paid
                activation_code = session['cod']
                ref = db.reference('/codes')
                query = ref.order_by_child('code').equal_to(activation_code).limit_to_first(1)
                result = query.get()
                c_id, c_data = next(iter(result.items()))
                c_data['google_id']=gid
                c_data['used']=True
                ref.child(c_id).set(c_data)
                google_id = session['google_id']
                drs_ref = db.reference('/drs')
                user_data = drs_ref.order_by_child('google_id').equal_to(google_id).get()
                if not user_data:
                    return jsonify({"message": "User not found"}), 404
                user_data = list(user_data.values())[0]
                user_data['plan']="basic"
                user_data['payed']=int(user_data['payed'])+basicprice
                user_data['first']=datetime.now().isoformat(),
                # Save the updated data back to Firebase
                drs_ref.child(google_id).update(user_data)
                # Return a response indicating success
                bPay=False
                #return render_template("pay_sucsess - ar.html")
                return redirect("/acc")
            else:
                bPay=False
                # Return a response indicating that the user information is not found
                return render_template("errors - ar.html",msg="User not loged in.",err='Unexpected')
        else:
            return render_template("errors - ar.html",msg="payment did not go through.",err='Unexpected')

@app.route("/basic_success")
def basic_success():
    global bPay
    global closee
    if closee:
        gid=session['google_id']
        if 'google_id' in session :
            # Set 'plan' to 'basic' and update 'payed' with the amount paid
            activation_code = session['cod']
            ref = db.reference('/codes')
            query = ref.order_by_child('code').equal_to(activation_code).limit_to_first(1)
            result = query.get()
            c_id, c_data = next(iter(result.items()))
            c_data['google_id']=gid
            c_data['used']=True
            ref.child(c_id).set(c_data)

            google_id = session['google_id']
            drs_ref = db.reference('/drs')
            user_data = drs_ref.order_by_child('google_id').equal_to(google_id).get()
            if not user_data:
                return jsonify({"message": "User not found"}), 404
            user_data = list(user_data.values())[0]
            user_data['plan']="Fam"
            user_data['payed']=int(user_data['payed'])+basicprice
            user_data['first']=datetime.now().isoformat(),
            # Save the updated data back to Firebase
            drs_ref.child(google_id).update(user_data)
            # Return a response indicating success
            bPay=False
            #return render_template("pay_sucsess.html")
            return redirect("/acc")
        else:
            bPay=False
            # Return a response indicating that the user information is not found
            return render_template("errors.html",msg="User not loged in.",err='Unexpected')
    else:
        if bPay:
            gid=session['google_id']
            if 'google_id' in session :
                # Set 'plan' to 'basic' and update 'payed' with the amount paid
                activation_code = session['cod']
                ref = db.reference('/codes')
                query = ref.order_by_child('code').equal_to(activation_code).limit_to_first(1)
                result = query.get()
                c_id, c_data = next(iter(result.items()))
                c_data['google_id']=gid
                c_data['used']=True
                ref.child(c_id).set(c_data)
                google_id = session['google_id']
                drs_ref = db.reference('/drs')
                user_data = drs_ref.order_by_child('google_id').equal_to(google_id).get()
                if not user_data:
                    return jsonify({"message": "User not found"}), 404
                user_data = list(user_data.values())[0]
                user_data['plan']="basic"
                user_data['payed']=int(user_data['payed'])+basicprice
                user_data['first']=datetime.now().isoformat(),
                # Save the updated data back to Firebase
                drs_ref.child(google_id).update(user_data)
                # Return a response indicating success
                bPay=False
                #return render_template("pay_sucsess.html")
                return redirect("/acc")
            else:
                bPay=False
                # Return a response indicating that the user information is not found
                return render_template("errors.html",msg="User not loged in.",err='Unexpected')
        else:
            return render_template("errors.html",msg="payment did not go through.",err='Unexpected')

@app.route("/urlme")
def urlme():
    ### change the api to send the info to the firebase db then get the info from the db on the clinet side ###
    path = f"C:/{cname}/{appname}/data.txt"
    app_data = load_app_data()
    if os.path.exists(f"C:/{cname}") and os.path.exists(f"C:/{cname}/{appname}") and 'plan' in app_data:
        # Set 'plan' to 'basic'
        app_data['url'] = appurl
        with open(path, 'wb') as file:
            ed=encrypt_data(app_data)
            file.write(ed)
    else:
        return render_template("app_error.html")

@app.route("/basic_cancel")
def pay_cancel():
    # Handle canceled payment
    return render_template("Payment_canceled.html")

@app.route("/basic_cancel_ar")
def pay_cancelar():
    # Handle canceled payment
    return render_template("Payment_canceled - ar.html")

@app.route("/en")
def en():
    session["lang"] = 'en'
    return {}

@app.route("/ar")
def ar():
    session["lang"] = 'ar'
    return {}

@app.route("/login_ar")
def loginar():
    authorization_url, state = flow.authorization_url()
    session["lang"] = 'ar'
    session["state"] = state
    return redirect(authorization_url)

@app.route("/loginb")
def loginbb():
    authorization_url, state = flow.authorization_url()
    if 'PLAN' in session and 'google_id' in session:
        gid=session['google_id']
        reff = db.reference(f'/drs/{gid}/settings')
        bruh = reff.get()
        bruh['ac']['users']-=1
        reff.update(bruh)

    session.pop("PLAN", None)
    session.pop("google_id", None)
    session["lang"] = 'en'
    session["state"] = state
    session["sec"] =True
    return redirect(authorization_url)

@app.route("/callback")
def callback():

    if session["state"] != request.args["state"]:
        app.logger.info("session[state] == request.args[state]: %s", session["state"] == request.args["state"])
        app.logger.info("session[state]: %s", session["state"])
        app.logger.info("request.args[state]: %s", request.args["state"])
        abort(500)  # State does not match!

    #app.logger.info("Request URL: %s", request.url)
    flow.fetch_token(authorization_response=request.url)

    credentials = flow.credentials
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(session=cached_session)

    id_info = id_token.verify_oauth2_token(
        id_token=credentials._id_token,
        request=token_request,
        audience=GOOGLE_CLIENT_ID
    )
    session.permanent = True
    session["google_id"] = id_info.get("sub")
    session["name"] = id_info.get("name")
    session["donee"]=True
    if "lang" in session and session["lang"] in ['ar']:
        return redirect('/protected_area_ar')
    else:
        return redirect("/protected_area")

@app.route("/login")
def login():
    #session.clear()
    authorization_url, state = flow.authorization_url()
    if 'PLAN' in session and 'google_id' in session:
        gid=session['google_id']
        reff = db.reference(f'/drs/{gid}/settings')
        bruh = reff.get()
        bruh['ac']['users']-=1
        reff.update(bruh)
        
    session.pop("PLAN", None)
    session.pop("google_id", None)
    session["lang"] = 'en'
    session["state"] = state
    return redirect(authorization_url)

@app.route("/app_data_me")
def app_data_me():
    user_ip = request.headers['X-Real-IP']
    c=get_pcs_by_mac(user_ip)
    if not c :
        c=save_app_data()
    return c

@app.route("/dbtempplz")
def dbtempplz():
    db_content =  get_user_info_by_google_id(10)['db']
    db={'db':db_content}
    return db

@app.route("/dbtemp")
def dbtemp():
    db={'db':get_db_temp()}
    return db

@app.route("/dbmeplz")
def dbmeplzz():
    path=f'c:/{cname}/{appname}/user_data.txt'
    if os.path.exists(path):
        user_data = load_user_data()
        google_id=user_data['google_id']
        c=get_user_db_plz(google_id)
    else:
        c=get_user_db_plz()
    return c

@app.route("/logout")
def logout():
    session.clear()
    session["donee"]=False
    return redirect("/logme")

@app.route("/logme")
def index():
    return render_template("login.html")

@app.route("/logme_ar")
def indexar():
    return render_template("login - ar.html")

@app.route("/sign_in")
def sign_in():
    return render_template("sign_in.html")

@app.route("/savesign" , methods=['POST'])
def savesign():
    data = request.json
    google_id = session.get('google_id', None)

    if not google_id:
        return jsonify({"message": "Invalid session data"}), 400

    dr_ref = db.reference(f'/drs/{google_id}')
    nn=dr_ref.get()
    for i in data:
        if i != 'phone':
            nn['settings'][i]= data[i]
        else:
            nn[i]= data[i]
    dr_ref.update(nn)

    return jsonify({"message": f"added data successfully "}), 200

@app.route("/protected_area")
@login_is_required
def done():
    logged_in = "google_id" in session
    if logged_in:
        google_id = session.get("google_id")
        name = session.get("name")
        info={"google_id":google_id,"name":name}
        try:
            #log_me_in(info)
            #quittab()
            if 'sec' in session:
                return redirect("/med_sub")
            else:
                return redirect("/acc")
        except Exception as e:
            return render_template("errors.html",msg=str(e),err='Unexpected')

    return render_template("errors.html",msg='User not loged in',err='Unexpected')

@app.route("/protected_area_ar")
def donear():
    logged_in = "google_id" in session
    if logged_in:
        google_id = session.get("google_id")
        name = session.get("name")
        info={"google_id":google_id,"name":name}
        try:
            log_me_in(info)
            #quittab()
            return render_template("loged_in - ar.html")
        except Exception as e:
            return render_template("errors - ar.html",msg=str(e),err='Unexpected')
    return render_template("loged_in _error - ar.html")

@app.route('/plan_me')
def planme():
    app_data=get_appds_by_mac()
    plan = app_data["plan"]
    paid=0
    if plan== 'basic':
        paid=basicprice
    elif plan=='prem':
        paid=premprice
    else:
        paid=0
    return {'plan':plan,'payed':paid}

@app.route('/usr_me', methods=['POST'])
def usr():
    # Get the activation code from the request JSON
    data = request.get_json()
    idd = data.get('id')
    if idd and not idd in [1]:
        user_info= get_user_info_by_google_id(idd)
        if user_info:
            i={}
            for j in user_info:
                if not j in ['db']:
                    i[j]=user_info[j]
            return i
    else:
        user_data = {
            "first": datetime.now().date().isoformat(),
            "google_id": 1,
            "name": "non",
            "payed": 0,
            'plan':'free'
            }
        return user_data

@app.route('/db_me', methods=['POST'])
def dbmee():
    # Get the activation code from the request JSON
    data = request.get_json()
    idd = data.get('id')
    if idd:
        db=get_user_info_by_google_id(idd)['db']
        return db

def calculate_trial_status(plan,first_date_str):
    if plan == "fam":
        return  "gud"
    elif plan in ['free']:
        return  "gud"
        #try:
        #    first_date = datetime.fromisoformat(first_date_str)
        #    today = datetime.now()
        #    trial_duration = timedelta(days=7)  # 7 days
        #    trial_end_date = first_date + trial_duration
        #    days_left = (trial_end_date - today).days
        #    trial_status = "gud" if days_left > 0 else "bad"
        #    return trial_status
        #except ValueError:
        #    return "bad"
    else:
        try:
            first_date = datetime.fromisoformat(first_date_str)
            today = datetime.now()
            trial_duration = timedelta(days=30)   # 30 days
            trial_end_date = first_date + trial_duration
            days_left = (trial_end_date - today).days
            trial_status = "gud" if days_left > 0 else "bad"
            return trial_status
        except ValueError:
            return "bad"

def get_userD(google_id):
        typee=session.get('wtype', 'drs')
        drssref = db.reference(f'/{typee}/{google_id}')
        doc = drssref.get()
        name = session.get("name")
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
                                            "printed":False,#fe hal alteba3a la yumkin ta5eer al ma3lomat
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

@app.route('/fetchUserData')
def fetch_user_data():
    logged_in = "google_id" in session
    if logged_in:
        google_id = session.get("google_id")
    else:
        return redirect("/logme")

    #session["user_data"]=user_data
    return redirect("/Binder_medical")

@app.route('/get_userD')
def get_userDD():
    if "google_id" in session:
        gid = session["google_id"]
        user_data = get_userD(gid)

        if 'PLAN' in session:
            PLAN = 'sec'
        else:
            PLAN = user_data['plan']
    else:
        return redirect("/logme")

    return  jsonify({"user_data": user_data}), 200

@app.route('/Binder_medical')
def get_last_page():
    if "google_id" in session:
        gid = session["google_id"]
        user_data = get_userD(gid)

        if 'PLAN' in session:
            cc=session['cod']
            ref = db.reference(f'/codes/{cc}')
            codes = ref.get()
            if codes:
                PLAN = session['PLAN']
            else:
                session.clear()
                return redirect("/fetchUserData")
        else:
            PLAN = user_data['plan']
    else:
        return redirect("/fetchUserData")
    typee=session.get('wtype', 'drs')
    if not "wtype" in session:
        session['wtype']='drs'
    drss_ref = db.reference(f'/{typee}/{gid}')
    drrr=drss_ref.get()

    if 'settings' not in drrr:
        drrr['settings']={
            'msg':'',
            'pkey':"",
            "send":False,
            'drname':'',
            "specialty": '',
            "location": ''
        }
        drss_ref.set(drrr)
        return redirect("/sign_in")
    elif 'specialty' not in drrr['settings'] or 'location' not in drrr['settings']:
        return redirect("/sign_in")

    first_date_str = str(user_data.get("first"))
    plan=str(user_data.get("plan"))
    trial_status = calculate_trial_status(plan,first_date_str)

    if trial_status == "bad":
        if typee == 'drs':
            session["page"]='acc'
            page=session["page"]
            user_data['patients'] = []
            return  render_template(f"{page}.html",user_data=user_data)

    if "page" in session:
        page=session["page"]
    elif typee=='drs':
        if user_data["plan"]== "free"  :
            page="acc"
        else:
            page='home'

    if page == 'acc':
        user_data['patients'] = []
        return  render_template(f"{page}.html",user_data=user_data)
    elif page == 'srch':
        
        pats='nope'
        if 'autoo' not in session :
            session["autoo"]='nope'
            
        nono=session["autoo"]
        session["autoo"]='nope'
        
        if 'stat' not in session :
            session["stat"]='nope'
            
        stat=session["stat"]
        session["stat"]='nope'
    
        return  render_template(f"{page}.html",plan=PLAN,nono=nono,pats=stat)
    elif page == 'settings':
        if 'settings' not in user_data:
            drs_ref = db.reference(f'/drs/{session["google_id"]}/settings')
            settings={
                'msg':'',
                'pkey':"",
                "send":False,
                'drname':''
            }
            drs_ref.set(settings)
        if PLAN not in ['sec']:
            if 'ac' not in user_data['settings']:
                code = gencode()
                save_code(code, "sec", session["google_id"])
                save_seccode(code,session['google_id'])
            user_data = get_userD(gid)

            user_data['patients'] = []
            user_data['settings']['ac']= []
        return  render_template(f"{page}.html",plan=PLAN)
    elif page == 'stats':
        return  render_template(f"{page}.html",plan=PLAN,user_data=user_data)
    elif page == 'data':
        patient=user_data['patients'][session["patientno"]]
        return  render_template(f"{page}.html",user_data=user_data)
    else:
        return  render_template(f"{page}.html",user_data=user_data)

@app.route('/acc')
def accc():
    session["page"]='acc'
    return redirect("/fetchUserData")
    #return render_template("acc.html",user_data=user_data,price=medprice)

@app.route('/home_page')
def homeeeepage():
    session["page"]='home'
    if "google_id" in session:
        gid = session["google_id"]
        user_data = get_userD(gid)

        if 'PLAN' in session:
            PLAN = 'sec'
        else:
            PLAN = user_data['plan']
    else:
        return redirect("/fetchUserData")

    first_date_str = str(user_data.get("first"))
    plan=str(user_data.get("plan"))
    trial_status = calculate_trial_status(plan,first_date_str)

    if trial_status == "bad":
        session["page"]='acc'
        return redirect("/fetchUserData")
    else:
        return redirect("/fetchUserData")

@app.route('/support')
def support():
    session["page"]='support'

    if "google_id" in session:
        gid = session["google_id"]
        user_data = get_userD(gid)

        if 'PLAN' in session:
            PLAN = 'sec'
        else:
            PLAN = user_data['plan']
    else:
        return redirect("/fetchUserData")

    first_date_str = str(user_data.get("first"))
    plan=str(user_data.get("plan"))
    trial_status = calculate_trial_status(plan,first_date_str)

    if trial_status == "bad":
        session["page"]='acc'
        return redirect("/fetchUserData")
    else:
        return redirect("/fetchUserData")

@app.route('/settings')
def settingssss():

    if "google_id" in session:
        gid = session["google_id"]
        user_data = get_userD(gid)

        if 'PLAN' in session:
            PLAN = 'sec'
        else:
            PLAN = user_data['plan']
    else:
        return redirect("/fetchUserData")
    
    typee=session.get('wtype', 'drs')

    if not user_data['plan'] in ['sec'] and typee=='drs':
        session["page"]='settings'

    first_date_str = str(user_data.get("first"))
    plan=str(user_data.get("plan"))
    trial_status = calculate_trial_status(plan,first_date_str)

    drs_ref = db.reference(f'/{typee}/{session["google_id"]}/settings')
    sett=drs_ref.get()
    if not sett:
            settings={
                'msg':'',
                'pkey':"",
                "send":False,
                'drname':''
            }
            drs_ref.set(settings)

    if trial_status == "bad":
        session["page"]='acc'
        return redirect("/fetchUserData")
    else:
        return redirect("/fetchUserData")

@app.route('/stats')
def statsss():
    session["page"]='stats'

    if "google_id" in session:
        gid = session["google_id"]
        user_data = get_userD(gid)

        if 'PLAN' in session:
            PLAN = 'sec'
        else:
            PLAN = user_data['plan']
    else:
        return redirect("/fetchUserData")

    first_date_str = str(user_data.get("first"))
    plan=str(user_data.get("plan"))
    trial_status = calculate_trial_status(plan,first_date_str)

    if trial_status == "bad":
        session["page"]='acc'
        return redirect("/fetchUserData")
    else:
        return redirect("/fetchUserData")

@app.route('/srch')
def srchhhhh():
    session["page"]='srch'
    if "google_id" in session:
        gid = session["google_id"]
        user_data = get_userD(gid)

        if 'PLAN' in session:
            PLAN = 'sec'
        else:
            PLAN = user_data['plan']
    else:
        return redirect("/fetchUserData")

    first_date_str = str(user_data.get("first"))
    plan=str(user_data.get("plan"))
    trial_status = calculate_trial_status(plan,first_date_str)

    if trial_status == "bad":
        session["page"]='acc'
        return redirect("/fetchUserData")
    else:
        session["autoo"]='nope'
        return redirect("/fetchUserData")

@app.route('/back')
def backkkk():
    session["page"]='srch'
    if "google_id" in session:
        gid = session["google_id"]
        user_data = get_userD(gid)

        if 'PLAN' in session:
            PLAN = 'sec'
        else:
            PLAN = user_data['plan']
    else:
        return redirect("/fetchUserData")

    first_date_str = str(user_data.get("first"))
    plan=str(user_data.get("plan"))
    trial_status = calculate_trial_status(plan,first_date_str)

    if trial_status == "bad":
        session["page"]='acc'
        return redirect("/fetchUserData")
    else:
        session["autoo"]='yup'
        session["stat"]='nope'
        return redirect("/fetchUserData")

@app.route('/meddata')
def meddata():
    if "google_id" in session:
        gid = session["google_id"]
        user_data = get_userD(gid)

        if 'PLAN' in session:
            PLAN = 'sec'
        else:
            PLAN = user_data['plan']
    else:
        return redirect("/fetchUserData")

    if not user_data['plan'] in ['sec']:
        session["page"] = 'data'

    first_date_str = str(user_data.get("first"))
    plan=str(user_data.get("plan"))
    trial_status = calculate_trial_status(plan,first_date_str)

    if trial_status == "bad":
        session["page"] = 'acc'
        return redirect("/fetchUserData")
    else:
        return redirect("/fetchUserData")

@app.route('/lab_page')
def lab_page():
    session["page"]='lab'

    if "google_id" in session:
        gid = session["google_id"]
        user_data = get_userD(gid)

        if 'PLAN' in session:
            PLAN = 'sec'
        else:
            PLAN = user_data['plan']
    else:
        return redirect("/fetchUserData")

    first_date_str = str(user_data.get("first"))
    plan=str(user_data.get("plan"))
    trial_status = calculate_trial_status(plan,first_date_str)

    if trial_status == "bad":
        session["page"]='acc'
        return redirect("/fetchUserData")
    else:
        return redirect("/fetchUserData")
    
@app.route('/getlab')
def getlab():
    google_id = session["google_id"]
    patient_id = session.get('patientno')
    drssref = db.reference(f'/drs/{google_id}/patients/{patient_id}')
    pat = drssref.get()

    if 'lab' in pat :
        return jsonify(pat['lab'])
    else:
        return jsonify({'k':"bruh"})
    
@app.route('/addlabreq', methods=['POST'])
def addlab():
    data = request.get_json()
    msg = data.get('msg')
    test = data.get('test')

    google_id = session["google_id"]
    patient_id = session.get('patientno')
    drssref = db.reference(f'/drs/{google_id}/patients/{patient_id}')
    pat = drssref.get()

    if 'lab' in pat :
        pat['lab'].append({
            "test":test,
            'msg':msg,
            "date":datetime.now().date().isoformat(),
            "time":datetime.now().strftime("%X")
        })
        
        drssref.update(pat)
    else:
        pat['lab']=[{
                'msg':msg,
                "test":test,
                "date":datetime.now().date().isoformat(),
                "time":datetime.now().strftime("%X")
            }]
        drssref.update(pat)
        
    return jsonify({"message": "lab request added successfully"}), 200

@app.route('/deletelabreq', methods=['POST'])
def delete_lab_request():
    data = request.json
    index = data.get('index')

    if index is None:
        return jsonify({'error': 'Index not provided.'}), 400

    google_id = session.get("google_id")
    if not google_id:
        return jsonify({"error": "Not authenticated"}), 403

    patient_id = session.get("patientno")

    drssref = db.reference(f'/drs/{google_id}/patients/{patient_id}')
    pat = drssref.get()

    if not pat or "lab" not in pat or index >= len(pat["lab"]):
        return jsonify({'error': 'Lab request not found.'}), 404

    # Remove the lab request from the list
    del pat["lab"][index]

    # Save the updated patient data
    drssref.update(pat)

    return jsonify({"success": "Lab request deleted."})

@app.route('/radio_page')
def radio_page():
    session["page"]='radio'

    if "google_id" in session:
        gid = session["google_id"]
        user_data = get_userD(gid)

        if 'PLAN' in session:
            PLAN = 'sec'
        else:
            PLAN = user_data['plan']
    else:
        return redirect("/fetchUserData")

    first_date_str = str(user_data.get("first"))
    plan=str(user_data.get("plan"))
    trial_status = calculate_trial_status(plan,first_date_str)

    if trial_status == "bad":
        session["page"]='acc'
        return redirect("/fetchUserData")
    else:
        return redirect("/fetchUserData")

@app.route('/pharma_page')
def pharma_page():
    session["page"]='pharma'

    if "google_id" in session:
        gid = session["google_id"]
        user_data = get_userD(gid)

        if 'PLAN' in session:
            PLAN = 'sec'
        else:
            PLAN = user_data['plan']
    else:
        return redirect("/fetchUserData")

    first_date_str = str(user_data.get("first"))
    plan=str(user_data.get("plan"))
    trial_status = calculate_trial_status(plan,first_date_str)

    if trial_status == "bad":
        session["page"]='acc'
        return redirect("/fetchUserData")
    else:
        return redirect("/fetchUserData")
    
@app.route('/getradio')
def getradio():
    google_id = session["google_id"]
    patient_id = session.get('patientno')
    drssref = db.reference(f'/drs/{google_id}/patients/{patient_id}')
    pat = drssref.get()

    if 'radio' in pat :
        return jsonify(pat['radio'])
    else:
        return jsonify({'k':"bruh"})
    
@app.route('/getpharma')
def getpharma():
    google_id = session["google_id"]
    patient_id = session.get('patientno')
    drssref = db.reference(f'/drs/{google_id}/patients/{patient_id}')
    pat = drssref.get()

    if 'pharma' in pat :
        return jsonify(pat['pharma'])
    else:
        return jsonify({'k':"bruh"})

@app.route('/addradioreq', methods=['POST'])
def addradio():
    data = request.get_json()
    msg = data.get('msg')
    test = data.get('test')

    google_id = session["google_id"]
    patient_id = session.get('patientno')
    drssref = db.reference(f'/drs/{google_id}/patients/{patient_id}')
    pat = drssref.get()

    if 'radio' in pat :
        pat['radio'].append({
            'msg':msg,
            "test":test,
            "date":datetime.now().date().isoformat(),
            "time":datetime.now().strftime("%X")
        })
        drssref.update(pat)
    else:
        pat['radio']=[{
                'msg':msg,
                "test":test,
                "date":datetime.now().date().isoformat(),
                "time":datetime.now().strftime("%X")
            }]
        drssref.update(pat)
        
    return jsonify({"message": "radio request added successfully"}), 200
    
@app.route('/addpharmareq', methods=['POST'])
def addpharma():
    data = request.get_json()
    msg = data.get('msg')
    test = data.get('test')

    google_id = session["google_id"]
    patient_id = session.get('patientno')
    drssref = db.reference(f'/drs/{google_id}/patients/{patient_id}')
    pat = drssref.get()

    if 'pharma' in pat :
        pat['pharma'].append({
            'msg':msg,
            "test":test,
            "date":datetime.now().date().isoformat(),
            "time":datetime.now().strftime("%X")
        })
        drssref.update(pat)
    else:
        pat['pharma']=[{
                'msg':msg,
                "test":test,
                "date":datetime.now().date().isoformat(),
                "time":datetime.now().strftime("%X")
            }]
        drssref.update(pat)
        
    return jsonify({"message": "pharma request added successfully"}), 200

@app.route('/deletepharmareq', methods=['POST'])
def delete_pharma_request():
    data = request.json
    index = data.get('index')


    if index is None:
        return jsonify({'error': 'Index not provided.'}), 400

    google_id = session.get("google_id")
    if not google_id:
        return jsonify({"error": "Not authenticated"}), 403

    patient_id = session.get("patientno")

    drssref = db.reference(f'/drs/{google_id}/patients/{patient_id}')
    pat = drssref.get()

    if not pat or "pharma" not in pat or index >= len(pat["pharma"]):
        return jsonify({'error': 'pharma request not found.'}), 404

    # Remove the lab request from the list
    del pat["pharma"][index]

    # Save the updated patient data
    drssref.update(pat)

    return jsonify({"success": "pharma request deleted."})

@app.route('/deleteradioreq', methods=['POST'])
def delete_radio_request():
    data = request.json
    index = data.get('index')


    if index is None:
        return jsonify({'error': 'Index not provided.'}), 400

    google_id = session.get("google_id")
    if not google_id:
        return jsonify({"error": "Not authenticated"}), 403

    patient_id = session.get("patientno")

    drssref = db.reference(f'/drs/{google_id}/patients/{patient_id}')
    pat = drssref.get()

    if not pat or "radio" not in pat or index >= len(pat["radio"]):
        return jsonify({'error': 'radio request not found.'}), 404

    # Remove the lab request from the list
    del pat["radio"][index]

    # Save the updated patient data
    drssref.update(pat)

    return jsonify({"success": "radio request deleted."})

@app.route('/addPatient', methods=['POST'])
def add_patient():
    data = request.get_json()
    google_id = data.get('google_id')
    patient_info = data.get('patient_info')

    if not google_id or not patient_info:
        return jsonify({"message": "Invalid data"}), 400

    drs_ref = db.reference('/drs')
    doc_ref = drs_ref.order_by_child('google_id').equal_to(google_id).limit_to_first(1)
    doc = doc_ref.get()
    if not doc:
        return jsonify({"message": "User not found"}), 404

    user_data = list(doc.values())[0]
    session['patientno'] = len(user_data['patients'])# Set the patient number
    if len(user_data['patients'])== 1 and (int(user_data['patients'][0]['age'])>150 or int(user_data['patients'][0]['age'])<0):
        session['patientno'] = 0# Set the patient number
        user_data['patients'][0]=patient_info
        user_data['patients'][0]['no']=1
    else:
        user_data['patients'].append(patient_info)
        user_data['patients'][-1]['no']=len(user_data['patients'])

    nno=session['patientno']
    user_data['patients'][nno]["visits"][0]['visit_date']=f'{datetime.now().date().isoformat()}'
    user_data['patients'][nno]["next"]=f'{datetime.now().date().isoformat()}'

    user_data['patients'][nno]['visits'][0]['div']=''

    drs_ref.child(google_id).set(user_data)

    return jsonify({"message": "Patient added successfully"}), 200

@app.route('/ssearch', methods=['POST']) #'''need place holder if the typee is not drs'''
def ssearch():
    try:
        data = request.json
        typee=session.get('wtype', 'drs')
        google_id = session.get("google_id")
        start_date = data.get('startDate')
        end_date = data.get('endDate')
        details = data.get('details', '').lower()
        location = data.get('location', '').lower()
        treatment = data.get('treatment', '').lower()
        diagnosis = data.get('diagnosis', '').lower()
        lab = data.get('lab', '').lower()
        show_date = data.get('showDate', False)
        show_visit_info = data.get('showVisitInfo', False)
        
        session['startDate'] = start_date
        session['endDate'] = end_date
        session['details'] = details
        session['Location'] = location
        session['treatment'] = treatment
        session['diagnosis'] = diagnosis
        session['lab'] = lab
        session['show_date'] = show_date
        session['show_visit_info'] = show_visit_info

        # Reference to the /drs path in Realtime Database
        drs_ref = db.reference(f'/{typee}/{google_id}/patients')
        patients = drs_ref.get()

        if not patients:
            return jsonify({'error': 'No data found for the user'}), 404

        # Initialize variables for results
        total_customers = 0
        total_debit = 0
        total_payed = 0
        unpaid_customers = 0
        matched_patients = []

        # Iterate over patients
        for patient in patients:
            patient_matches = False
            has_debit = False
            
            # Check patient-level criteria
            if location and patient.get('location', '').lower() != location:
                continue
            
            if details:
                visits = patient.get('visits', [])
                if not any(details in visit.get('details', '').lower() for visit in visits):
                    continue
            
            if show_visit_info:
                visits = patient.get('visits', [])
                if not any(
                    (not treatment or treatment in visit.get('treatment', '').lower()) and
                    (not diagnosis or diagnosis in visit.get('diagnosis', '').lower()) and
                    (not lab or lab in visit.get('lab', '').lower())
                    for visit in visits
                ):
                    continue

            if show_date:
                visit_dates = [visit['visit_date'] for visit in patient.get('visits', [])]
                visit_dates_matched = any(
                    (not start_date or not end_date or start_date <= date <= end_date) if start_date and end_date else
                    (start_date and date >= start_date) if start_date else
                    (end_date and date <= end_date) if end_date else
                    True
                    for date in visit_dates
                )
                if not visit_dates_matched:
                    continue
            
            # If patient matches all criteria, process their visits
            total_customers += 1
            for visit in patient.get('visits', []):
                visit_date = visit.get('visit_date', '')
                visit_details = visit.get('details', '').lower()
                visit_treatment = visit.get('treatment', '').lower()
                visit_diagnosis = visit.get('diagnosis', '').lower()
                visit_lab = visit.get('lab', '').lower()

                # Check visit-level criteria
                if (not details or details in visit_details) and \
                   (not treatment or treatment in visit_treatment) and \
                   (not diagnosis or diagnosis in visit_diagnosis) and \
                   (not lab or lab in visit_lab) and \
                   (not show_date or (start_date <= visit_date <= end_date if start_date and end_date else \
                   (start_date and visit_date >= start_date) if start_date else \
                   (end_date and visit_date <= end_date) if end_date else \
                   True)):

                    # Adjust for `div` in visit
                    if 'div' in visit:
                        visit['payed'] *= 10
                        visit['debit'] *= 10
                        
                    total_debit += float(visit.get('debit', 0) or 0)
                    total_payed += float(visit.get('payed', 0) or 0)
                    
                    # Set flag if any visit has debit
                    if float(visit.get('debit', 0) or 0) > 0:
                        has_debit = True

            # Increment unpaid_customers if any visit has debit
            if has_debit:
                unpaid_customers += 1

            # Add patient to matched_patients if they meet the criteria
            matched_patients.append(patient)

        return jsonify({
            'total_customers': total_customers,
            'unpaid_customers': unpaid_customers,
            'total_debit': total_debit,
            'total_payed': total_payed,
            'patients': matched_patients
        }), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/searchh_stats', methods=['POST'])
def searchh_stats():
    try:
        typee=session.get('wtype', 'drs')
        # Retrieve criteria from session
        data = {
            'startDate': session.get('startDate'),
            'endDate': session.get('endDate'),
            'details': session.get('details', '').lower(),
            'location': session.get('Location', '').lower(),
            'treatment': session.get('treatment', '').lower(),
            'diagnosis': session.get('diagnosis', '').lower(),
            'lab': session.get('lab', '').lower(),
            'show_date': session.get('show_date'),
            'show_visit_info': session.get('show_visit_info')
        }
        
        google_id = session.get("google_id")
        start_date = data['startDate']
        end_date = data['endDate']
        details = data['details']
        location = data['location']
        treatment = data['treatment']
        diagnosis = data['diagnosis']
        lab = data['lab']
        show_date = data['show_date']
        show_visit_info = data['show_visit_info']

        
        # Reference to the /drs path in Realtime Database
        drs_ref = db.reference(f'/{typee}/{google_id}/patients')
        patients = drs_ref.get()

        if not patients:
            return jsonify({'error': 'No data found for the user'}), 404

        # Initialize variables for results
        total_customers = 0
        total_debit = 0
        total_payed = 0
        unpaid_customers = 0
        matched_patients = []

        # Iterate over patients
        for patient in patients:
            patient_matches = False
            has_debit = False
            
            # Check patient-level criteria
            if location and patient.get('location', '').lower() != location:
                continue
            
            if details:
                visits = patient.get('visits', [])
                if not any(details in visit.get('details', '').lower() for visit in visits):
                    continue
            
            if show_visit_info:
                visits = patient.get('visits', [])
                if not any(
                    (not treatment or treatment in visit.get('treatment', '').lower()) and
                    (not diagnosis or diagnosis in visit.get('diagnosis', '').lower()) and
                    (not lab or lab in visit.get('lab', '').lower())
                    for visit in visits
                ):
                    continue

            if show_date:
                visit_dates = [visit['visit_date'] for visit in patient.get('visits', [])]
                visit_dates_matched = any(
                    (not start_date or not end_date or start_date <= date <= end_date) if start_date and end_date else
                    (start_date and date >= start_date) if start_date else
                    (end_date and date <= end_date) if end_date else
                    True
                    for date in visit_dates
                )
                if not visit_dates_matched:
                    continue
            
            # If patient matches all criteria, process their visits
            total_customers += 1
            for visit in patient.get('visits', []):
                visit_date = visit.get('visit_date', '')
                visit_details = visit.get('details', '').lower()
                visit_treatment = visit.get('treatment', '').lower()
                visit_diagnosis = visit.get('diagnosis', '').lower()
                visit_lab = visit.get('lab', '').lower()

                # Check visit-level criteria
                if (not details or details in visit_details) and \
                   (not treatment or treatment in visit_treatment) and \
                   (not diagnosis or diagnosis in visit_diagnosis) and \
                   (not lab or lab in visit_lab) and \
                   (not show_date or (start_date <= visit_date <= end_date if start_date and end_date else \
                   (start_date and visit_date >= start_date) if start_date else \
                   (end_date and visit_date <= end_date) if end_date else \
                   True)):

                    # Adjust for `div` in visit
                    if 'div' in visit:
                        visit['payed'] *= 10
                        visit['debit'] *= 10
                        
                    total_debit += float(visit.get('debit', 0) or 0)
                    total_payed += float(visit.get('payed', 0) or 0)
                    
                    # Set flag if any visit has debit
                    if float(visit.get('debit', 0) or 0) > 0:
                        has_debit = True

            # Increment unpaid_customers if any visit has debit
            if has_debit:
                unpaid_customers += 1

            # Add patient to matched_patients if they meet the criteria
            matched_patients.append(patient)

        return jsonify(matched_patients), 200#return jsonify(matched_patients), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/search_stats')
def search_stats():
    session["page"]='srch'
    session["stat"]='yup'
    return redirect("/Binder_medical")

@app.route('/search_by_name', methods=['POST'])
def search_by_name():
    try:
        name = request.json.get('name')
        if not name:
            return jsonify({'error': 'Name parameter is required'}), 400
        patients = get_patients_by_name(name)
        return jsonify(patients)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/search_by_number', methods=['POST'])
def search_by_number():
    number = request.json.get('number')
    return get_patient_by_number(number)

def get_patients_by_name(name):
    if "google_id" in session:
        gid = session["google_id"]
        user_data = get_userD(gid)

        if 'PLAN' in session:
            PLAN = 'sec'
        else:
            PLAN = user_data['plan']
    else:
        return redirect("/fetchUserData")
    google_id = user_data['google_id']
    typee=session.get('wtype', 'drs')
    drs_ref = db.reference(f'/{typee}/{google_id}')
    all_patients = []
    
    for i in all_patients:
        #if 'payed' in i and 'div' in i:   
        #    i['payed']=i['payed']*10
        #
        #if 'debit' in i and 'div' in i:  
        #    i['debit']=i['debit']*10

        if 'debit' in i:
            i['debit']=float(i.get('debit', 0) or 0)*10
    doc = drs_ref.get()

    patients = doc.get('patients', [])
    all_patients.extend(p for p in patients if name.lower() in p.get('name', '').lower())
    return all_patients if all_patients else 'non'

def get_patient_by_number(number):
    if "google_id" in session:
        gid = session["google_id"]
        user_data = get_userD(gid)

        if 'PLAN' in session:
            PLAN = 'sec'
        else:
            PLAN = user_data['plan']
    else:
        return redirect("/fetchUserData")

    # Validate input
    if not number:
        return jsonify({"message": "Invalid data"}), 400

    google_id = user_data.get('google_id')
    if not google_id:
        return jsonify({"message": "Invalid data"}), 400

    drs_ref = db.reference('/drs')
    user_data = drs_ref.order_by_child('google_id').equal_to(google_id).get()

    if not user_data:
        return jsonify({"message": "User not found"}), 404

    user_data = list(user_data.values())[0]
    patient = None

    # Convert number to a string to use string methods like isdigit() and len()
    number_str = str(number)

    # Check if the number is a phone number (9 digits)
    if number_str.isdigit() and len(number_str) == 9:
        # Handle as a phone number
        patient = next((p for p in user_data['patients'] if str(p['id']) == number_str), None)
    elif all(char.isdigit() or char in ["-", " "] for char in number_str) and len(number_str) in [10, 12]:
        # Handle as a formatted phone number
        patient = next((p for p in user_data['patients'] if str(p['phone']) == number_str), None)
    elif number_str.isdigit() and len(number_str) > 0:
        # Handle as a patient number
        patient_id = int(number_str) - 1  # Assuming patient numbers start from 1
        if 0 <= patient_id < len(user_data['patients']):
            patient = user_data['patients'][patient_id]
    else:
        return jsonify({"message": "Invalid patient, phone, or ID number format"}), 400

    # If patient is not found, return a 404 error
    if not patient:
        return jsonify({"message": "Patient not found"}), 404
    
    
    total_payed=0
    total_debit=0
    
    for i in patient['visits']:
        if 'div' in i:
            if 'payed' in i:
                total_payed+=float(i.get('payed', 0) or 0)*10

            if 'debit' in i:
                total_debit+=float(i.get('debit', 0) or 0)*10
        else:
            if 'payed' in i:
                total_payed+=float(i.get('payed', 0) or 0)
                
            if 'debit' in i:
                total_debit+=float(i.get('debit', 0) or 0)
               
    patient['payed'] = total_payed
    patient['debit'] = total_debit

    # Save patient number in the session
    session['patientno'] = patient['no']-1

    return jsonify(patient), 200

@app.route('/auto_search_by_number', methods=['POST'])
def auto_search_by_number():
    number = request.json.get('number')
    patient_id = session.get('patientno', None)
    return get_patient_by_number(patient_id+1)

@app.route('/show_search_by_number/<number>')
def show_search_by_number(number):
    session["autoo"]='yup'
    session["page"]='srch'
    session['patientno']=int(number)-1
    session["stat"]='nope'
    return redirect("/Binder_medical")

@app.route('/getPatientData', methods=['GET'])
def get_patient_data():
    google_id = session["google_id"]
    user_data = get_userD(google_id)
    patient_id = session.get('patientno')

    if not google_id:
        return jsonify({"message": "Invalid data"}), 400

    drs_ref = db.reference('/drs')
    user_data = drs_ref.order_by_child('google_id').equal_to(google_id).get()

    if not user_data:
        return jsonify({"message": "User not found"}), 404

    user_data = list(user_data.values())[0]
    patient = user_data['patients'][int(patient_id)]

    if not patient:
        return jsonify({"message": "Patient not found"}), 404
    
    
    if 'div' in patient:
        if 'payed' in patient:  
            patient['payed']=patient['payed']*10
        if 'debit' in patient:  
            patient['debit']=patient['debit']*10
            
    for i in patient['visits']:
        if 'div' in i:
            if 'payed' in i:  
                i['payed']=i['payed']*10
            if 'debit' in i:  
                i['debit']=i['debit']*10
            if 'coast' in i:  
                i['coast']=i['coast']*10

    response_data = patient

    response_data['patientss_number'] = patient_id  # Add patientno to the response

    return jsonify(response_data), 200

@app.route('/updatePatientTotals', methods=['POST'])
def update_patient_totals():
    data = request.json
    google_id = session['google_id']
    patient_no = session['patientno']
    typee=session.get('wtype', 'drs')
    total_payed = 0
    total_debit = 0

    if not google_id or not patient_no:
        return jsonify({"message": "Invalid session data"}), 400

    try:
        drs_ref = db.reference(f'/{typee}/{google_id}/patients/{int(patient_no)}')
        user_data = drs_ref.get()

        if not user_data:
            return jsonify({"message": "User not found"}), 404

        #patient = user_data['patients'][int(patient_no)]

        if not user_data:
            return jsonify({"message": "Patient not found"}), 404
        
        # Update the total payed and debit for the patient
        for i in user_data['visits']:
            if 'payed' in i:
                total_payed+=float(i['payed'] or 0)
                
            if 'debit' in i:
                total_debit+=float(i['debit'] or 0)

        user_data['payed'] = total_payed
        user_data['debit'] = total_debit


        # Save the updated data back to Firebase
        drs_ref.update(user_data)

        return jsonify({"message": f"Patient totals updated successfully {user_data} "}), 200
    except Exception as e:
        print(e)
        return jsonify({"message": f"An error occurred while updating patient totals {user_data}"}), 500

@app.route('/nnn')
def nnn():
    drs_ref = db.reference('/drs')
    nn=drs_ref.get()
    last =''
    ll=''
    name =[]
    activ=[]
    for i in nn:
        name.append(nn[i]['name'])
        #app.logger.info("nn[i]: %s", nn[i])
        if 'first' not in nn[i] or not isinstance(nn[i]['first'], str):
            continue
        if last == '' or datetime.fromisoformat(nn[i]['first'])<datetime.fromisoformat(last):
            last=nn[i]['first']
            ll=nn[i]['name']
            
    for i in nn:
        #app.logger.info("nn[i]: %s", nn[i])
        if 'patients' not in nn[i]:
            continue
        
        if len(nn[i]['patients'])>1:
            
            activ.append({nn[i]['name']:len(nn[i]['patients'])})


    return jsonify({"dr count": len(nn) , 'last':ll ,"name":name,'active users':len(activ),'active':activ})

@app.route('/updatePatientData', methods=['POST'])
def update_patient_data():
    data = request.json
    typee=session.get('wtype', 'drs')
    google_id = session.get('google_id', None)
    patient_no = data.get('patientNo', None)

    if not google_id:
        return jsonify({"message": "Invalid session data"}), 400

    patient_no-=1

    try:
        drs_ref = db.reference(f'/{typee}/{google_id}/patients/{int(patient_no)}')

        patient = drs_ref.get()

        if 'next' in patient:   
            dateee=patient['next']
        

        if not patient:
            return jsonify({"message": "Patient not found"}), 404


        # Update patient data
        for key, value in data.items():
            if key != 'patientNo':
                patient[key] = value
                
        
                
        if 'div' in patient:
            if 'payed' in patient:  
                patient['payed']=float(patient.get('payed', 0) or 0)/10
            if 'debit' in patient:  
                patient['debit']=float(patient.get('debit', 0) or 0)/10
        else:
            patient['div']='bruh'
            if 'payed' in patient:  
                patient['payed']=float(patient.get('payed', 0) or 0)/10
            if 'debit' in patient:  
                patient['debit']=float(patient.get('debit', 0) or 0)/10
            

        drs_ref.set(patient)

        #if 'next' in  data :
        #    dr_ref = db.reference(f'/drs/{google_id}')
        #    nn=dr_ref.get()
        #    if "msg" in nn:
        #        if data['next'] in nn["msg"] and data['phone'] in nn["msg"][data['next']]:
        #            nn["msg"][dateee].remove(patient['phone'])
        #            dr_ref.update(nn)

        if typee == 'drs':
            xx=0
            dr_ref = db.reference(f'/drs/{google_id}/msg')
            nn=dr_ref.get()

            if nn and dateee in nn:
                for i in nn[dateee]:
                    if i['no'] == patient_no+1:
                        nn[dateee].remove(nn[dateee][xx])
                    else:
                        xx+=1

            if 'next' in patient :# and datetime.fromisoformat(patient['next'])>datetime.today() :
                if nn:
                    if patient['next'] in nn:
                        add=True
                        for i in nn[patient['next']] :
                            if patient_no+1 == i["no"]:
                                add=False
                        if add:
                            nn[patient['next']].append({"phone":patient['phone'],"name":patient['name'],"no":patient_no+1,'msg':""})
                    else:
                        nn[patient['next']]=[{"phone":patient['phone'],"name":patient['name'],"no":patient_no+1,'msg':""}]
                else:
                    nn={patient['next'] :[{"phone":patient['phone'],"name":patient['name'],"no":patient_no+1,'msg':""}]}
                
                
                dr_ref.update(nn)


        return jsonify({"message": f"Patient data updated successfully"}), 200

    except Exception as e:
        app.logger.info("Error updating patient data: %s", e)
        app.logger.info("patient: %s", patient)
        app.logger.info("patient['next']: %s", patient['next'])
        return jsonify({"message": f"Error updating patient data: {str(e)}"}), 500

@app.route('/appointments')
def appointments():
    typee=session.get('wtype', 'drs')
    if typee == 'drs':
        session["page"]='appointments'
    elif typee == 'lab':
        session["page"]='appointments'

    if "google_id" in session:
        gid = session["google_id"]
        user_data = get_userD(gid)

        if 'PLAN' in session:
            PLAN = 'sec'
        else:
            PLAN = user_data['plan']
    else:
        return redirect("/fetchUserData")

    first_date_str = str(user_data.get("first"))
    plan=str(user_data.get("plan"))
    trial_status = calculate_trial_status(plan,first_date_str)
    if typee == "drs":
        if trial_status == "bad":
            session["page"]='acc'
            return redirect("/fetchUserData")
        else:
            return redirect("/fetchUserData")

@app.route('/get_appointments/<date>')
def getappointments(date):
    google_id = session.get('google_id', None)

    dr_ref = db.reference(f'/drs/{google_id}/msg')
    nn=dr_ref.get()

    #today_key = datetime.now().date().isoformat()
    
    return jsonify(nn.get(date, []))

@app.route('/save_appointments', methods=['POST'])
def saveappointments():
    data = request.json
    google_id = session.get('google_id', None)
    appointments = data.get('appointments', None)

    dr_ref = db.reference(f'/drs/{google_id}/msg')
    nn=dr_ref.get()

    # Save new appointments under the current timestamp
    timestamp = datetime.now().date().isoformat()
    nn[timestamp] = appointments
    dr_ref.update(nn)

    return jsonify({timestamp: nn[timestamp]})

@app.route('/updatesettings', methods=['POST'])
def settingsssfs():
    data = request.json
    google_id = session.get('google_id', None)
    typee=session.get('wtype', 'drs')

    if not google_id:
        return jsonify({"message": "Invalid session data"}), 400

    dr_ref = db.reference(f'/{typee}/{google_id}')
    nn=dr_ref.get()
    for key, value in data['correctedPatientData'].items():
        nn["settings"][key] = value
    dr_ref.update(nn)

    return jsonify({"message": f"Patient data updated successfully "}), 200

@app.route('/getsett')
def getsett():
    google_id = session.get('google_id', None)
    typee=session.get('wtype', 'drs')
    drs_ref = db.reference(f'/{typee}/{google_id}/settings')
    nn=drs_ref.get()

    settings={
        'msg':'',
        'pkey':"",
        "send":False,
        'drname':''
    }

    if nn:
        if 'ac'in nn:
            return nn
        else:
            code = gencode()
            save_code(code, "sec", session["google_id"])
            save_seccode(code,session['google_id'])
            return drs_ref.get()
    else:
        drs_ref.set(settings)
        code = gencode()
        save_code(code, "sec", session["google_id"])
        save_seccode(code,session['google_id'])
        return drs_ref.get()

@app.route('/updateVisitData', methods=['POST'])
def update_visit_data():
    data = request.json
    patient_id = session.get('patientno', None)
    google_id = session.get('google_id', None)
    typee=session.get('wtype', 'drs')
    
    data['payed']=data['payed']/10
    data['debit']=data['debit']/10
    data['coast']=data['coast']/10
    data['div']=''

    try:
        drs_ref = db.reference(f'/{typee}/{google_id}/patients/{patient_id}')
        patient = drs_ref.get()

        if not patient:
            return jsonify({"message": "Patient not found"}), 404

        visit_index = 0
        if not data.get("vno")-1<0 :
            visit_index=data.get("vno")-1

        if visit_index is not None and visit_index+1 <= len(patient['visits']):
            for i in data:
                patient['visits'][visit_index][i]=data[i]
                
        else:
            patient['visits'].append(data)
        
        # Save the updated data back to Firebase
        drs_ref.update(patient)


        return jsonify({"message": "Visit data updated successfully"}), 200

    except Exception as e:
        print(f"Error updating visit data: {e}")
        return jsonify({"message": f"Error updating visit data: {str(e)}"}), 500

@app.route('/getVisitByDate', methods=['GET'])
def get_visit_by_date():
    date = request.args.get('date')
    patient_no = request.args.get('patient_no')
    google_id = request.args.get('google_id')

    if not google_id or not date or not patient_no:
        return jsonify({"message": "Invalid data"}), 400

    drs_ref = db.reference('/drs')
    user_data = drs_ref.order_by_child('google_id').equal_to(google_id).get()

    if not user_data:
        return jsonify({"message": "User not found"}), 404

    user_data = list(user_data.values())[0]
    patient_data = next((p for p in user_data.get('patients', []) if p['no'] == patient_no), None)

    if not patient_data:
        return jsonify({"message": "Patient not found"}), 404

    visit_data = next((v for v in patient_data.get('visits', []) if v['visit_date'] == date), None)

    if not visit_data:
        return jsonify({"message": "Visit not found"}), 404
    
    if 'div' in visit_data:
        visit_data['payed']=visit_data['payed']*10
        visit_data['debit']=visit_data['debit']*10
        visit_data['coast']=visit_data['coast']*10
    return jsonify(visit_data), 200

@app.route('/insertVisit', methods=['POST'])
def insert_visit():
    data = request.get_json()
    google_id = data.get('google_id')
    visit_info = data.get('visit_info')
    patient_no = data.get('patient_no')
    
    visit_info['payed']=visit_info['payed']/10
    visit_info['debit']=visit_info['debit']/10
    visit_info['coast']=visit_info['coast']/10

    if not google_id or not visit_info or not patient_no:
        return jsonify({"message": "Invalid data"}), 400

    drs_ref = db.reference('/drs')
    user_data = drs_ref.order_by_child('google_id').equal_to(google_id).get()

    if not user_data:
        return jsonify({"message": "User not found"}), 404

    user_data = list(user_data.values())[0]
    patient_data = next((p for p in user_data.get('patients', []) if p['no'] == patient_no), None)

    if not patient_data:
        return jsonify({"message": "Patient not found"}), 404

    visits = patient_data.get('visits', [])
    visits.append(visit_info)
    patient_data['visits'] = visits
    user_data['patients'] = [p if p['no'] != patient_no else patient_data for p in user_data['patients']]
    
    drs_ref.child(google_id).set(user_data)

    return jsonify({"message": "Visit added successfully"}), 200

@app.route('/updateVisit', methods=['POST'])
def update_visit():
    data = request.get_json()
    google_id = data.get('google_id')
    visit_info = data.get('visit_info')
    patient_no = data.get('patient_no')
    
    visit_info['payed']=visit_info['payed']/10
    visit_info['debit']=visit_info['debit']/10
    visit_info['coast']=visit_info['coast']/10

    if not google_id or not visit_info or not patient_no:
        return jsonify({"message": "Invalid data"}), 400

    drs_ref = db.reference('/drs')
    user_data = drs_ref.order_by_child('google_id').equal_to(google_id).get()

    if not user_data:
        return jsonify({"message": "User not found"}), 404

    user_data = list(user_data.values())[0]
    patient_data = next((p for p in user_data.get('patients', []) if p['no'] == patient_no), None)

    if not patient_data:
        return jsonify({"message": "Patient not found"}), 404

    visits = patient_data.get('visits', [])
    for idx, visit in enumerate(visits):
        if visit['visit_date'] == visit_info['visit_date']:
            visits[idx] = visit_info
            break

    patient_data['visits'] = visits
    user_data['patients'] = [p if p['no'] != patient_no else patient_data for p in user_data['patients']]
    
    

    drs_ref.child(google_id).set(user_data)

    return jsonify({"message": "Visit updated successfully"}), 200

@app.route('/wtssignin')
def wtssignin():
    cwd = os.path.abspath(os.getcwd())
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Run in headless mode
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-disk-cache")
    cwd = os.path.abspath(os.getcwd())
    options.add_argument(f"--user-data-dir={cwd}/selenium")

    # Specify the path to ChromeDriver
    chromedriver_path = "https://www.pythonanywhere.com/user/RiaSoftware/files/home/RiaSoftware/s/assets/driver/chromedriver.exe"  # Change to your actual path

    # Initialize WebDriver
    driver = webdriver.Chrome(executable_path=chromedriver_path, options=options)

    whatsapp_url = 'https://web.whatsapp.com'
    print(f"Navigating to: {whatsapp_url}")
    driver.get(whatsapp_url)
    sleep(5)  # You may want to increase this sleep duration if necessary

    try:
        link_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(),'Link with phone number')]"))
        )
        link_button.click()

        phone_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[aria-label="Type your phone number."]'))
        )
        phone_input.clear()
        phone_input.send_keys('592840353')

        code_elements = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@class, 'x1c4vz4f')]//span"))
        )
        verification_code = "".join([element.text for element in code_elements])
        print(f"Verification Code: {verification_code}")

    except Exception as e:
        driver.quit()
        return jsonify(f"Error during auto messaging: {str(e)}")

    driver.quit()
    return render_template("wtssign.html", code=verification_code)

@app.route('/kprint')
def kprint():
    google_id = session.get('google_id', None)
    patient_no = session['patientno']
    drs_ref = db.reference(f'/drs/{google_id}')
    dr=drs_ref.get()
    patient = dr['patients'][patient_no]
    patient['dr']=dr['settings'].get("drname", dr['name'])
    file_stream, filename = create_patient_document(patient)

    # Send the file to the user for download without saving it to disk
    return send_file(file_stream, as_attachment=True, download_name=filename, mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')

@app.route('/kkprint', methods=['POST'])
def kkprint():
    google_id = session.get('google_id', None)
    patient_no = session['patientno']

    # Get the current visit number (vno) from the POST request
    vno = request.json.get('vno')

    # Fetch patient data
    drs_ref = db.reference(f'/drs/{google_id}')
    dr = drs_ref.get()
    patient = dr['patients'][patient_no]

    # Add doctor's name to the patient data
    patient['dr'] = dr['settings'].get("drname", dr['name'])

    # Create the visit document based on the patient and vno
    file_stream, filename = create_visit_document(patient, vno)
    
    
    v_ref = db.reference(f'/drs/{google_id}/patients/{patient_no}/visits/{vno}')
    
    visit = v_ref.get()
    
    visit["printed"]=True
    
    v_ref.set(visit)

    # Send the file to the user for download
    return send_file(file_stream, as_attachment=True, download_name=filename, mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')

dbst = firestore.client()
bucket = storage.bucket()

# Directory to store temporary files
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Utility function to upload file to Firebase Storage
def upload_to_storage(file, file_name):
    blob = bucket.blob(file_name)
    blob.upload_from_file(file)
    blob.make_public()
    return blob.public_url

@app.route('/uploadFile', methods=['POST'])
def upload_file():
    google_id = session.get('google_id', None)
    
    # Check if file exists in request
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    folder = request.form.get('folder', None)
    
    # Restrict uploads only to the 'drs' folder
    if folder != 'drs':
        return jsonify({"error": "Files can only be uploaded in the 'drs' folder"}), 403

    try:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Upload to Firebase Storage
        file_url = upload_to_storage(open(file_path, 'rb'), filename)

        file_info = {
            'name': filename,
            'upload_date': datetime.now().isoformat(),
            'data': file_url,
            'patient_no': request.form.get('patient_no'),
            "folder": folder,
            "gid": google_id,
            'file_type': file.content_type,
        }
        dbst.collection('files').add(file_info)

        os.remove(file_path)  # Remove the local file

        return jsonify({"message": "File uploaded successfully", "file_info": file_info}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/getFiles', methods=['GET'])
def get_files():
    google_id = session.get('google_id', None)
    patient_no = request.args.get('patient_no')
    folder = request.args.get('folder')
    
    print(f"Patient No: {patient_no}, Folder: {folder}, Google ID: {google_id}")
    
    if not patient_no:
        return jsonify({"error": "Patient number is required"}), 400
    
    files_ref = dbst.collection('files').where('patient_no', '==', patient_no).where('gid', '==', google_id)
    
    files = []
    
    if folder == 'drs':
        # Fetch files where folder is either 'drs' or missing (None)
        files_query = files_ref.stream()  # Get all files for this patient
        for doc in files_query:
            file_data = doc.to_dict()
            if 'folder' not in file_data or file_data['folder'] == 'drs':
                files.append(file_data)
    elif folder:
        # Fetch files only in the specified folder
        files = [doc.to_dict() for doc in files_ref.where('folder', '==', folder).stream()]
    
    print(f"Files fetched: {files}")
    return jsonify(files), 200

@app.route('/getFile/<file_id>', methods=['GET'])
def get_file(file_id):
    file_ref = dbst.collection('files').document(file_id)
    file_data = file_ref.get()
    if not file_data.exists:
        return jsonify({"error": "File not found"}), 404

    file_info = file_data.to_dict()
    response = jsonify(file_info)
    response.headers.set('Content-Type', file_info['file_type'])
    return response

logging.basicConfig(level=logging.INFO)

@app.route('/deleteFile', methods=['DELETE'])
def delete_file():
    try:
        file_url = request.args.get('url')
        if not file_url:
            return jsonify({"error": "URL parameter is required"}), 400

        # Query Firestore for the file document
        files_collection = dbst.collection("files")
        query = files_collection.where(filter=FieldFilter("data", "==", file_url)).get()

        if not query:
            return jsonify({"error": "File not found"}), 404

        # Assuming there's only one file with the given URL
        file_doc = query[0].reference
        file_doc.delete()

        return jsonify({"message": "File deleted successfully"}), 200
    except Exception as e:
        logging.error(f"Error deleting file: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@app.route('/gid')
def giid():
    session['google_id']="108738109636203771652"
    if 'PLAN' in session:
        del session['PLAN']
    i={}
    for j in session:
        i[j]=session[j]
    return i

@app.route('/giid/<google_id>')
def giiid(google_id):
    session["google_id"] = google_id
    session["lang"] = 'en'
    session["donee"]=True
    return redirect("/Binder_medical")

@app.route('/pgiid/<google_id>/<name>')
def pgiiid(google_id, name):
    session["google_id"] = google_id
    session["name"] = name
    session["lang"] = 'en'
    session["donee"]=True
    return redirect("/Binder_medical")

@app.route('/editFile', methods=['POST'])
def edit_file():
    file_id = request.form.get('file_id')
    new_content = request.form.get('new_content')

    if not file_id or not new_content:
        return jsonify({"error": "File ID and new content are required"}), 400

    file_ref = dbst.collection('files').document(file_id)
    file_data = file_ref.get()
    if not file_data.exists:
        return jsonify({"error": "File not found"}), 404

    file_info = file_data.to_dict()
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_info['name'])

    # Update the file content in Firestore and Firebase Storage
    with open(file_path, 'wb') as f:
        f.write(new_content.encode('utf-8'))

    file_url = upload_to_storage(open(file_path, 'rb'), file_info['name'])
    file_ref.update({
        'data': file_url,
        'upload_date': datetime.now().isoformat(),
    })

    # Remove the local file
    os.remove(file_path)

    return jsonify({"message": "File edited successfully"}), 200

#################################################################

"""discord bot"""

def just_do_it(server_id,name,val,des="try it"):
    ref = db.reference(f'/servers/{server_id}')
    server_data = ref.get()

    # Get existing commands or initialize if not present
    commands = server_data.get('commands', [])

    v= {"command":name,"val":val, "des": des}

    commands.append(v)

    # Update server data
    ref.update({'commands': commands})

def update_val(server_id, path, data):
    ref = db.reference(f'/servers/{server_id}/{path}')
    ref.update(data)

def get_command(server_id,command):
    # Reference to the Firebase Realtime Database
    ref = db.reference(f'/servers/{server_id}/suggestions/{user_id}')  # '/users' is the path where user data is stored

    # Query the database to find the user with the matching google_id
    query = ref.order_by_child('command').equal_to(command).limit_to_first(1)

    # Execute the query
    result = query.get()

    if not result:
        # User with the provided google_id not found
        return None

    # The result is a dictionary where keys are unique identifiers (Firebase push IDs)
    # We need to extract the user data from this dictionary
    user_id, user_data = next(iter(result.items()))
    if user_id:
        return user_data
    else:
        return None

def add_command_suggestion(guild_id, user_id,username,command, messages,des="try it"):
        suggestions = get_val(guild_id, f'suggestions/{user_id}')
        if suggestions:
            suggestions['val'].append({'command': command, 'messages': messages})
        else:
            suggestions = {'name':username,'val': [{'command': command, 'messages': messages}]}
        update_val(guild_id, f'suggestions/{user_id}', suggestions)

def get_val(server_id,name):
    # Reference to the Firebase Realtime Database
    ref = db.reference(f'/servers/{server_id}/val')  # '/users' is the path where user data is stored

    # Query the database to find the user with the matching google_id
    query = ref.order_by_child('name').equal_to(name).limit_to_first(1)

    # Execute the query
    result = query.get()

    if not result:
        # User with the provided google_id not found
        return None

    # The result is a dictionary where keys are unique identifiers (Firebase push IDs)
    # We need to extract the user data from this dictionary
    user_id, user_data = next(iter(result.items()))

    if user_id:
        return user_data
    else:
        return None

@app.route('/commands/meow')
def meow():
    idd=825778729904767037
    if "user" in session:
        return {'serverid': str(idd),"id":session["user"].id,"username": session["user"].username}
    else:
        return {'serverid': str(idd)}

@app.route('/server/<server_id>/check_user/<user_id>', methods=['GET'])
def check_user(server_id, user_id):
    ref = db.reference(f'/servers/{server_id}/allowed')
    allowed_users = ref.get()
    user_allowed = any(user['id'] == int(user_id) for user in allowed_users)
    return jsonify({'allowed': user_allowed})

@app.route('/server/<server_id>/add_command', methods=['POST'])
def add_commands(server_id):
    data = request.json
    des = data.get('des', "try it")

    just_do_it(server_id,data['command'],data['messages'],des)
    return jsonify({'success': True})

@app.route('/server/<server_id>/add_suggestion', methods=['POST'])
def add_suggs(server_id):
    data = request.json
    add_command_suggestion(server_id, data['id'],data['name'],data['command'],data['val'],data['des'])
    return jsonify({'success': True})

@app.route('/<server_id>/add_command', methods=['POST'])
def add_comms(server_id):
    data = request.json
    des = data.get('des', "try it")

    just_do_it(server_id,data['command'],data['val'],des)
    return jsonify({'success': True})

@app.route('/<server_id>/add_suggestion', methods=['POST'])
def add_suggestions(server_id):
    data = request.json
    add_command_suggestion(server_id, data['id'],data['name'],data['command'],data['val'],data['des'])
    return jsonify({'success': True})

@app.route('/commands/<server_id>', methods=['GET'])
def get_commands(server_id):
    for i in session:
        print(i)
    ref = db.reference(f'/servers/{server_id}/commands')
    commands = ref.get()
    return jsonify(commands)

@app.route('/suggestions/<server_id>', methods=['GET'])
def get_suggestions(server_id):
    ref = db.reference(f'/servers/{server_id}/suggestions')
    suggestions = ref.get()
    return jsonify(suggestions)

@app.route('/delete_command/<server_id>/<command_id>', methods=['DELETE'])
def delete_command(server_id, command_id):
    ref = db.reference(f'/servers/{server_id}/commands/{command_id}')
    ref.delete()
    return jsonify({"message": "Command deleted successfully"}), 200

@app.route('/add_suggestion/<server_id>', methods=['POST'])
def add_suggestion(server_id):
    data = request.json
    user_id = data['user_id']
    username = data['username']
    command = data['command']
    messages = data['messages']
    des = data.get('des', "try it")

    ref = db.reference(f'/servers/{server_id}/suggestions/{user_id}')
    suggestion_data = {'name': username, 'val': [{'command': command, 'messages': messages}]}
    ref.set(suggestion_data)
    return jsonify({"message": "Suggestion added successfully"}), 201

@app.route('/delete_suggestion/<server_id>/<user_id>/<command_name>', methods=['DELETE'])
def delete_suggestion(server_id, user_id, command_name):
    ref = db.reference(f'/servers/{server_id}/suggestions')
    suggestions = ref.get()
    if suggestions:
        hmm=suggestions[str(user_id)]['val']
        x=[j for j in hmm if not j['command']==command_name]
        if x == []:
            #y=[{j:suggestions[j]} for j in suggestions if not j==user_id]
            y=[]
            for j in suggestions:
                if not j==user_id:
                    y.append({j:suggestions[j]})

            ref = db.reference(f'servers/{server_id}')
            ref.child('suggestions').set(y)
        else:
            update_val(server_id, f'suggestions/{user_id}', x)

        return jsonify({'message': 'Suggestion deleted successfully'})
    else:
        return jsonify({'message': 'Suggestion not deleted'})

@app.route('/add_command/<server_id>')
def add_command(server_id):
    session["serverid"]=server_id
    app.logger.info("Session data for add_command page: %s", session)
    return redirect(url_for("indexxx"))

@app.route("/addcomm")
def homeeee():
    return render_template("adds.html")

@app.route('/server/<server_id>/update_command/<command_id>', methods=['PUT'])
def update_commanddd(server_id, command_id):
    data = request.json
    ref = db.reference(f'/servers/{server_id}/commands')
    commands = ref.get()

    if not commands:
        return jsonify({'error': 'Commands not found'}), 404

    command_id = int(command_id)
    if commands[command_id]:
        commands[command_id].update(data)
        x = commands[command_id]
        print(x)
        update_val(server_id, f"commands/{command_id}", x)
        return jsonify({'success': 'Command updated'}), 200
    else:
        return jsonify({'error': 'Command not found'}), 404

@app.route("/addcomm/callback")
def callbackkk():
    code = request.args.get("code")
    if not code:
        return redirect(url_for("homeeee"))

    # Create a temporary client for OAuth
    oauth_client = APIClient(BOTtt_TOKEN, client_secret=CLIENTtt_SECRET)

    try:
        token_response = oauth_client.oauth.get_access_token(code,REDIRECccT_URI)
        token = token_response.access_token
        session["token"] = token
    except Exception as e:
        return str(e)

    # Create a client using the retrieved OAuth token
    user_client = APIClient(token, bearer=True)

    user = user_client.users.get_current_user()
    print(user)
    session["user"] = {"id": user.id, "username": user.username, "discriminator": user.discriminator}

    return redirect(url_for("indexxx"))

@app.route("/indexx")
def indexxx():
    if "user" not in session:
        return redirect(url_for("homeeee"))
    user = session["user"]
    x="825778729904767037"
    if "serverid" in session:
        x=session["serverid"]

    ref = db.reference(f'/servers/{x}/allowed')
    allowed_users = ref.get()
    user_allowed = any(uuser['id'] == int(user['id']) for uuser in allowed_users)

    app.logger.info("Session data for index page: %s", session)
    if user_allowed:
        return render_template("comm.html",user=user,serverid=x)
    else:
        return render_template("add.html",user=user,serverid=x)
    #return render_template("index.html",user=user,serverid=x)

@app.route("/addcommand")
def addcommmand():
    if "user" not in session:
        return redirect(url_for("homeeee"))
    user = session["user"]
    x="825778729904767037"
    if "serverid" in session:
        x=session["serverid"]
    return render_template("addd.html",user=user,serverid=x)

@app.route("/sugg")
def sugggg():
    if "user" not in session:
        return redirect(url_for("homeeee"))
    user = session["user"]
    x="825778729904767037"
    if "serverid" in session:
        x=session["serverid"]
    return render_template("sugg.html",user=user,serverid=x)

@app.route("/login_dis")
def loginnnnn():
    discord_login_url = f"https://discord.com/oauth2/authorize?client_id={dCLIENT_ID}&response_type=code&redirect_uri=https%3A%2F%2Friasoftware.pythonanywhere.com%2Faddcomm%2Fcallback&scope=identify+email+guilds+guilds.members.read"
    return redirect(discord_login_url)

@app.route("/logout_dis")
def logouttttt():
    session.clear()
    return redirect(url_for("homeeee"))


if __name__ == "__main__":
    app.run(debug=False)


