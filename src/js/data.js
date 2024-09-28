const admin = require('firebase-admin');

// Initialize Firebase Admin SDK
admin.initializeApp({
    credential: admin.credential.cert("key.json"),
    databaseURL: 'https://monydb-f2cdb-default-rtdb.europe-west1.firebasedatabase.app/'
});

const db = admin.firestore();

function getPatientRef(doctorId, patientId) {
    return db.collection('drs').doc(doctorId).collection('patients').doc(patientId);
}

async function fetchData(query) {
    try {
        const snapshot = await query.get();
        if (snapshot.exists) {
            return snapshot.data();
        } else {
            return null;
        }
    } catch (error) {
        console.error('Error fetching data:', error);
        throw error;
    }
}

async function getPatientById(doctorId, patientId) {
    const query = getPatientRef(doctorId, patientId);
    return await fetchData(query);
}

async function getPatientByPhone(doctorId, phoneNumber) {
    const query = db.collection('drs').doc(doctorId).collection('patients').where('phone', '==', phoneNumber);
    try {
        const snapshot = await query.get();
        if (!snapshot.empty) {
            return snapshot.docs[0].data();
        } else {
            return null;
        }
    } catch (error) {
        console.error('Error getting patient by phone:', error);
        throw error;
    }
}

async function getPatientByNo(doctorId, patientNo) {
    const query = db.collection('drs').doc(doctorId).collection('patients').where('no', '==', patientNo);
    try {
        const snapshot = await query.get();
        if (!snapshot.empty) {
            return snapshot.docs[0].data();
        } else {
            return null;
        }
    } catch (error) {
        console.error('Error getting patient by number:', error);
        throw error;
    }
}

async function getVisitByDate(doctorId, patientNo, date) {
    const query = db.collection('drs').doc(doctorId).collection('patients').where('no', '==', patientNo).where('visits.visit_date', '==', date);
    try {
        const snapshot = await query.get();
        if (!snapshot.empty) {
            return snapshot.docs[0].data();
        } else {
            return null;
        }
    } catch (error) {
        console.error('Error getting visit by date:', error);
        throw error;
    }
}

async function getAllVisitsForPatient(doctorId, patientNo) {
    const query = db.collection('drs').doc(doctorId).collection('patients').where('no', '==', patientNo);
    try {
        const snapshot = await query.get();
        const visits = snapshot.docs.map(doc => doc.data().visits).flat();
        return visits;
    } catch (error) {
        console.error('Error getting all visits for patient:', error);
        throw error;
    }
}

async function insertOrUpdateDataToPatients(doctorId, data) {
    try {
        const patientRef = getPatientRef(doctorId, data.no);
        await patientRef.set(data, { merge: true });
    } catch (error) {
        console.error('Error inserting or updating data to patients:', error);
        throw error;
    }
}

async function insertOrUpdateDataToVisits(doctorId, patientNo, data) {
    try {
        const patientRef = getPatientRef(doctorId, patientNo);
        const patientData = await fetchData(patientRef);
        const visits = patientData.visits || [];

        if (data.vno) {
            const visitIndex = visits.findIndex(visit => visit.vno === data.vno);
            if (visitIndex !== -1) {
                visits[visitIndex] = data;
            } else {
                visits.push(data);
            }
        } else {
            visits.push(data);
        }

        await patientRef.update({ visits });
    } catch (error) {
        console.error('Error inserting or updating data to visits:', error);
        throw error;
    }
}

function updateEntries(data) {
    document.getElementById('visitDate').value = data['visit_date'] || '';
    document.getElementById('patientNumber').value = data['patient_no'] || '';
    document.getElementById('treatment').value = data['treatment'] || '';
    document.getElementById('diagnosis').value = data['diagnosis'] || '';
    document.getElementById('lab').value = data['lab'] || '';
    document.getElementById('totalCoast').value = data['coast'] || '';
    document.getElementById('amountPaid').value = data['payed'] || '';
    document.getElementById('debit').value = data['debit'] || '';
    document.querySelector('.entry-details').value = data['details'] || '';
}

async function search(doctorId) {
    const searchInput = document.getElementById('search');
    const searchValue = searchInput.value.trim();
    searchInput.value = '';

    if (!searchValue) {
        console.log("Invalid date format.");
        return;
    }

    const patientNumber = document.getElementById('patientNumber').value;
    if (!patientNumber) {
        console.log("Patient number is required.");
        return;
    }

    try {
        const result = await getVisitByDate(doctorId, patientNumber, searchValue);
        if (result) {
            updateEntries(result);
        } else {
            console.log("Data not found for the entered date.");
        }
    } catch (error) {
        console.error('Error searching for visit:', error);
    }
}

async function getVisitByNumber(doctorId, vno, pno) {
    const visits = await getAllVisitsForPatient(doctorId, pno);
    if (vno < 1 || visits.length === 0) {
        return null;
    }
    if (vno <= visits.length) {
        return visits[vno - 1];
    }
    return null;
}

async function getLastVisit(doctorId, pno) {
    const visits = await getAllVisitsForPatient(doctorId, pno);
    return visits.length > 0 ? visits[visits.length - 1] : null;
}

async function last(doctorId) {
    const pno = document.getElementById('patientNumber').value;
    const lastVisit = await getLastVisit(doctorId, pno);
    const date = new Date().toISOString().split('T')[0];
    if (!lastVisit || lastVisit['visit_date'] !== date) {
        const newVisit = {
            "vno": lastVisit ? lastVisit.vno + 1 : 1,
            "visit_date": date,
            "treatment": "No Change",
            "payed": 0,
            "diagnosis": "No Change",
            "debit": 0,
            "lab": "No Change",
            "details": "",
            "patient_no": pno
        };
        await insertOrUpdateDataToVisits(doctorId, pno, newVisit);
        updateEntries(newVisit);
    } else {
        updateEntries(lastVisit);
    }
}

async function first(doctorId) {
    const pno = document.getElementById('patientNumber').value;
    const firstVisit = await getVisitByNumber(doctorId, 1, pno);
    if (firstVisit) {
        updateEntries(firstVisit);
    } else {
        console.log("Data not found for the search entry.");
    }
}

async function nextt(doctorId) {
    const pno = document.getElementById('patientNumber').value;
    let currentVisitNumber = parseInt(document.querySelector('.button-now').innerText) || 0;
    const newVisitNumber = currentVisitNumber + 1;
    const newVisit = await getVisitByNumber(doctorId, newVisitNumber, pno);
    if (newVisit) {
        updateEntries(newVisit);
        document.querySelector('.button-now').innerText = newVisitNumber;
    } else {
        console.log("No more visits available.");
    }
}

async function pervv(doctorId) {
    const pno = document.getElementById('patientNumber').value;
    let currentVisitNumber = parseInt(document.querySelector('.button-now').innerText) || 0;
    const newVisitNumber = currentVisitNumber - 1;
    if (newVisitNumber > 0) {
        const newVisit = await getVisitByNumber(doctorId, newVisitNumber, pno);
        if (newVisit) {
            updateEntries(newVisit);
            document.querySelector('.button-now').innerText = newVisitNumber;
        } else {
            console.log("No previous visits available.");
        }
    } else {
        console.log("This is the first visit.");
    }
}

async function updatePatientDebit(doctorId, payed, debit) {
    const pno = document.getElementById('patientNumber').value;
    const patientRef = getPatientRef(doctorId, pno);
    try {
        const patientData = await fetchData(patientRef);
        if (patientData) {
            const updatedPayed = payed + (patientData.payed || 0);
            const updatedDebit = (patientData.debit || 0) + debit;
            await patientRef.update({
                payed: updatedPayed,
                debit: updatedDebit
            });
        }
    } catch (error) {
        console.error('Error updating patient debit:', error);
    }
}

async function saveData(doctorId) {
    const data = {
        "visit_date": document.getElementById('visitDate').value,
        "patient_no": document.getElementById('patientNumber').value,
        "treatment": document.getElementById('treatment').value,
        "diagnosis": document.getElementById('diagnosis').value,
        "lab": document.getElementById('lab').value,
        "coast": parseFloat(document.getElementById('totalCoast').value) || 0,
        "payed": parseFloat(document.getElementById('amountPaid').value) || 0,
        "debit": parseFloat(document.getElementById('debit').value) || 0,
        "details": document.querySelector('.entry-details').value
    };

    if (data['payed'] !== 0) {
        await updatePatientDebit(doctorId, data['payed'], data['debit']);
    }
    
    await insertOrUpdateDataToVisits(doctorId, data['patient_no'], data);
}
