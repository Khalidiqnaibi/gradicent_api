from abc import ABC, abstractmethod

class Binder(ABC):
    @abstractmethod
    def add_user():
        pass
    
    @abstractmethod
    def get_user():
        pass
    
    @abstractmethod
    def add_clint():
        pass
    
    @abstractmethod
    def get_clint():
        pass
    
    @abstractmethod
    def add_interaction():
        pass
    
    @abstractmethod
    def get_interaction():
        pass
    
    def add_clint():
        data = request.get_json()
        google_id = data.get('google_id')
        patient_info = data.get('patient_info')

        if not google_id or not patient_info:
            return jsonify({"message": "Invalid data"}), 400
        
        typee=session.get('wtype', 'drs')
        drs_ref = db.reference(f'/{typee}')
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

        log_event(session['google_id'], "New Patient", {"patient_id": nno})
        return jsonify({"message": "Patient added successfully"}), 200