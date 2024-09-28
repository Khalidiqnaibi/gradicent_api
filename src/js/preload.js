const { contextBridge, ipcRenderer, shell} = require('electron');
const crypto = require('crypto');
const fs = require('fs').promises;
const axios = require('axios');
//const sqlite3 = require('sqlite3').verbose();
const admin = require('firebase-admin');

// Initialize Firebase Admin SDK
admin.initializeApp({
  credential: admin.credential.cert("key.json"),
  databaseURL: 'https://monydb-f2cdb-default-rtdb.europe-west1.firebasedatabase.app/'
});

const db = admin.firestore();


function createFernet() {
    // Derive a key from the password using PBKDF2HMAC
    const password = Buffer.from(pssword, 'utf-8');
    const salt = Buffer.from('MY_Potatolikesme_too', 'utf-8');  // Change this to a unique salt
    const key = crypto.pbkdf2Sync(password, salt, 100000, 32, 'sha256');
  
    return {
        encrypt: (data) => {
            const cipher = crypto.createCipher('aes-256-cbc', key);
            let encrypted = cipher.update(JSON.stringify(data), 'utf-8', 'base64');
            encrypted += cipher.final('base64');
            return encrypted;
        },
        decrypt: (encryptedData) => {
          const decipher = crypto.createDecipher('aes-256-cbc', key);
          let decrypted = decipher.update(encryptedData, 'base64', 'utf-8');
          decrypted += decipher.final('utf-8');
          return JSON.parse(decrypted);
      }            
    };
}

const fernet = createFernet();
const pssword = '@Ksoftkhaafif1';
const cname = 'Ria Software';
const appname = 'Binder Medical'; 
//const dbFile = `C:/${cname}/${appname}/db.sqlite`; 
const appPrice= 315;
var internet=true;
var apiurl = 'http://riasoftware.pythonanywhere.com';
var payed =false;

// Function to fetch data from Firestore
async function fetchData(collectionPath, queryField, queryValue) {
    try {
        const snapshot = await db.collection(collectionPath)
            .where(queryField, '==', queryValue)
            .get();

        if (snapshot.empty) {
            return null;
        }

        return snapshot.docs.map(doc => doc.data());
    } catch (error) {
        console.error('Error fetching data:', error);
        throw error;
    }
}

// Function to get patient by ID
async function getPatientById(patientId) {
    try {
        const patients = await fetchData('patients', 'id', patientId);

        if (!patients || patients.length === 0) {
            return null;
        }

        // Assuming only one patient with this ID exists (based on SQLite query)
        const patientData = patients[0];
        return {
            "no": patientData.no,
            "name": patientData.name,
            "id": patientData.id,
            "phone": patientData.phone,
            "location": patientData.location,
            "pmh": patientData.pmh,
            "payed": patientData.payed,
            "debit": patientData.debit,
            "age": patientData.age
        };
    } catch (error) {
        console.error('Error fetching patient by ID:', error);
        throw error;
    }
}

// Function to get patient by phone number
async function getPatientByPhone(phoneNumber) {
    try {
        const patients = await fetchData('patients', 'phone', phoneNumber);

        if (!patients || patients.length === 0) {
            return null;
        }

        // Assuming only one patient with this phone number exists (based on SQLite query)
        const patientData = patients[0];
        return {
            "no": patientData.no,
            "name": patientData.name,
            "id": patientData.id,
            "phone": patientData.phone,
            "location": patientData.location,
            "pmh": patientData.pmh,
            "payed": patientData.payed,
            "debit": patientData.debit,
            "age": patientData.age
        };
    } catch (error) {
        console.error('Error fetching patient by phone number:', error);
        throw error;
    }
}

// Function to get patient by patient number (no)
async function getPatientByNo(patientNo) {
    try {
        const patients = await fetchData('patients', 'no', patientNo);

        if (!patients || patients.length === 0) {
            return null;
        }

        // Assuming only one patient with this patient number exists (based on SQLite query)
        const patientData = patients[0];
        return {
            "no": patientData.no,
            "name": patientData.name,
            "id": patientData.id,
            "phone": patientData.phone,
            "location": patientData.location,
            "pmh": patientData.pmh,
            "payed": patientData.payed,
            "debit": patientData.debit,
            "age": patientData.age
        };
    } catch (error) {
        console.error('Error fetching patient by patient number:', error);
        throw error;
    }
}

// Function to get visit by date and patient number
async function getVisitByDate(date, patientNo) {
    try {
        const visits = await fetchData('visits', 'visit_date', date);

        if (!visits || visits.length === 0) {
            return null;
        }

        // Find the visit that matches the patient number
        const visitData = visits.find(visit => visit.patient_no === patientNo);

        if (!visitData) {
            return null;
        }

        return {
            "avno": visitData.avno, // Assuming avno is available in Firestore document
            "vno": visitData.vno,
            "visit_date": visitData.visit_date,
            "treatment": visitData.treatment,
            "payed": visitData.payed,
            "diagnosis": visitData.diagnosis,
            "debit": visitData.debit,
            "coast": visitData.coast,
            "lab": visitData.lab,
            "details": visitData.details,
            "patient_no": patientNo
        };
    } catch (error) {
        console.error('Error fetching visit by date and patient number:', error);
        throw error;
    }
}

// Function to get all visits for a patient
async function getAllVisitsForPatient(patientNo) {
    try {
        const visits = await fetchData('visits', 'patient_no', patientNo);

        if (!visits || visits.length === 0) {
            return [];
        }

        return visits.map(visit => ({
            "no": visit.no,
            "patient_no": visit.patient_no,
            "visit_date": visit.visit_date,
            "treatment": visit.treatment,
            "payed": visit.payed,
            "diagnosis": visit.diagnosis,
            "coast": visit.coast,
            "debit": visit.debit,
            "lab": visit.lab,
            "details": visit.details
        }));
    } catch (error) {
        console.error('Error fetching all visits for patient:', error);
        throw error;
    }
}

function encryptData(data) {
  return fernet.encrypt(data);
}

function decryptData(encryptedData) {
  return fernet.decrypt(encryptedData);
}

async function loadUserData() {
  const path = `C:/${cname}/${appname}/user_data.txt`;

  try {
      await fs.mkdir(`C:/${cname}`, { recursive: true });
      await fs.mkdir(`C:/${cname}/${appname}`, { recursive: true });

      let user_data = {
          "first": new Date().toISOString().split('T')[0],
          "google_id": 1,
          "name": "non",
          "payed": 0,
          'plan': 'free'
      };

      if (await fs.access(path).then(() => true).catch(() => false)) {
        const encryptedData = await fs.readFile(path);
          console.log(`encryptedData == ${encryptedData}`)
          user_data = fernet.decrypt(encryptedData.toString());
          console.log(`user_data decrypted == ${user_data}`)
      } else {
          const encryptedData = fernet.encrypt(user_data);
          await fs.writeFile(path, encryptedData);
      }

      if (user_data['name'] === 'non') {
          const app_data = await loadAppData();
          const jid = { 'id': app_data['google_id'] };
          try {
              const response = await axios.post(`${apiurl}/usr_me`, jid);
              if (response.status === 200) {
                  user_data = response.data;
                  const encryptedData = fernet.encrypt(user_data);
                  await fs.writeFile(path, encryptedData);
              } else {
                  console.log('Handle user_me failure');
              }
          } catch (e) {
              console.log('Handle exception');
          }
      }

      if (user_data['plan'] === 'free') {
          try {
              const response = await axios.get(`${apiurl}/plan_me`);
              if (response.status === 200) {
                  const c = response.data;
                  user_data['plan'] = c['plan'];
                  user_data['payed'] = c['payed'];
                  const app_data = await appDataMe(apiurl);
                  const encryptedData = fernet.encrypt(user_data);
                  await fs.writeFile(path, encryptedData);
              } else {
                  console.log('Handle plan_me failure');
              }
          } catch (e) {
              console.log('Handle exception');
          }
      }

      if ('db' in user_data) {
          //await fs.writeFile(dbFile, user_data['db'], 'latin-1');

          const raw = user_data;
          const d = {};
          for (const i in raw) {
              if (i !== 'db') {
                  d[i] = user_data[i];
              }
          }

          const encryptedData = fernet.encrypt(d);
          await fs.writeFile(path, encryptedData);

          user_data = d;
      }

      return user_data;
  } catch (error) {
      console.error(`Error loading user data: ${error.message}`);
      return null;
  }
}

async function loadAppData() {
  const app_data_path = `C:/${cname}/${appname}/data.txt`;

  try {
      await fs.mkdir(`C:/${cname}`, { recursive: true });
      await fs.mkdir(`C:/${cname}/${appname}`, { recursive: true });

      let app_data;

      if (!await fs.access(app_data_path).then(() => true).catch(() => false)) {
          app_data = await appDataMe(apiurl);
      } else {
          const encryptedData = await fs.readFile(app_data_path);
          app_data = decryptData(encryptedData.toString());
          apiurl = app_data['url'] || '';
      }

      if (app_data['google_id'] === 1) {
          app_data = await appDataMe(apiurl);
      }

      if (app_data['plan'] === 'free') {
          try {
              const response = await axios.get(`${apiurl}/plan_me`);
              if (response.status === 200) {
                  const c = response.data;
                  app_data['plan'] = c['plan'];
                  app_data['payed'] = c['payed'];
                  const encryptedData = encryptData(app_data);
                  await fs.writeFile(app_data_path, encryptedData);
              } else {
                console.log('Handle plan_me failure')
              }
          } catch (e) {
            console.log('Handle exception')
          }
      }

      return app_data;
  } catch (error) {
      console.error(`Error loading app data: ${error.message}`);
      return null;
  }
}

async function appDataMe() {
  try {
      const response = await axios.get(`${apiurl}/app_data_me`);
      if (response.status === 200) {
          const app_data = response.data;
          const encryptedData = encryptData(app_data);
          await fs.writeFile(`C:/${cname}/${appname}/data.txt`, encryptedData);
          apiurl = app_data['url'] || '';
          return app_data;
      } else {
          console.error(`Failed to make the request: ${response.status}`);
          return null;
      }
  } catch (error) {
      console.error(`Failed to make the request: ${error.message}`);
      return null;
  }
}

function checkAppPayment() {
    const appData = loadAppData();
    async function usrd() {
        const userdat = await loadUserData();
        return userdat;
    }
    var userdata =usrd();
    
    if (appData.payed && appData.payed>0) {
        payed = true;
    } else {
        const userPaid = userdata.payed > (appPrice - 1);
        if (userPaid) {
            appData.payed = true;
            payed = true;
            const txt = `C:/${cname}/${appname}/data.txt`;
            const encryptedData = encryptData(appData);
            fs.writeFileSync(txt, encryptedData);
        } else {
            payed = false;
        }
    }
    
    return payed;//appData
}

function calculateTrialDaysLeft(firstDateStr) {
    try {
        const firstDate = new Date(firstDateStr);
        const today = new Date();
        const trialDuration = 7 * 24 * 60 * 60 * 1000; // 7 days in milliseconds
        const trialEndDate = new Date(firstDate.getTime() + trialDuration);
        const daysLeft = Math.max(0, Math.ceil((trialEndDate - today) / (1000 * 60 * 60 * 24))); // Convert milliseconds to days
        return daysLeft;
    } catch (error) {
        return 0;
    }
}

function calculatePayDaysLeft(firstDateStr) {
    try {
        const firstDate = new Date();
        const last = new Date(firstDateStr);
        const trialDuration = 1 * 24 * 60 * 60 * 1000; // 1 day in milliseconds 'i think it should be like 30 for max profit'
        const trialEndDate = new Date(firstDate.getTime() + trialDuration);
        const daysLeft = Math.ceil((trialEndDate - last) / (1000 * 60 * 60 * 24)); // Convert milliseconds to days
        return daysLeft;
    } catch (error) {
        return 0;
    }
}

function opentab(url){
    shell.openExternal(url);
}

contextBridge.exposeInMainWorld('BinderApi', {
  ipcRenderer: ipcRenderer,
  require: async (module) => {
    try {
        // Load the specified module and return it
        const loadedModule = await require(module);
        return loadedModule;
    } catch (error) {
        console.error(error);
        throw error;
    }
  },
  decrypt_Data: (data) => {
    return decryptData(data);
  },
  encrypt_Data: (data) => {
    return encryptData(data);
  },
  fixedapi:() => {
    return 'http://riasoftware.pythonanywhere.com'
  },
  create_connection: () => createConnection(),
  fetch_data: (query,data) => fetchData(query,data),
  get_patient_by_id: (data) => getPatientById(data),
  get_patient_by_phone: (phone_number) => getPatientByPhone(phone_number),
  get_patient_by_no: (patient_no) => getPatientByNo(patient_no),
  get_visit_by_date: (date,patientNo) => getVisitByDate(date,patientNo),
  get_all_visits_for_patient: (patient_no) => getAllVisitsForPatient(patient_no),
  insert_or_update_data_to_visits: (data) => insertOrUpdateDataToVisits(data),
  insert_or_update_data_to_patients: (data) => insertOrUpdateDataToPatients(data),
  loadappD: () => loadAppData(),
  AppPayment: () => checkAppPayment(),
  TrialDaysLeft: (firstDate) => calculateTrialDaysLeft(firstDate),
  PayDaysLeft : (firstDate) => calculatePayDaysLeft(firstDate),
  loaduserD: () => loadUserData(),
  opentab:(url) => opentab(url),
  //createNewDb: () => createNewDatabase(dbFile),
  potato:(msg) => ipcRenderer.send('potato',msg),
  sure: (data) => ipcRenderer.send('opdata',data),
  outt: (func) => ipcRenderer.on('outt', (event, message) => func(message)),
  openFile: (path) => ipcRenderer.send('openFile', path),
  out: (data) => ipcRenderer.send('out', data),
  updateEntries: (data) => ipcRenderer.send('updateEntries', data),
  createPatFolder: (fname) => ipcRenderer.send('createPatFolder', fname),
  createDateFolder: (fname) => ipcRenderer.send('createDateFolder', fname),
  parseDate: (dateStr) => ipcRenderer.send('parseDate', dateStr),
  search: () => ipcRenderer.send('search'),
  nextEntry: (event, entryWidget) => ipcRenderer.send('nextEntry', event, entryWidget),
  getVByNo: (vno, pno) => ipcRenderer.send('getVByNo', vno, pno),
  upLast: () => ipcRenderer.send('upLast'),
  last: () => ipcRenderer.send('last'),
  blank: () => ipcRenderer.send('blank'),
  first: () => ipcRenderer.send('first'),
  nextt: () => ipcRenderer.send('nextt'),
  pervv: () => ipcRenderer.send('pervv'),
  upAllDbt: () => ipcRenderer.send('upAllDbt'),
  updatePatientDebit: (payed, debit) => ipcRenderer.send('updatePatientDebit', payed, debit),
});
