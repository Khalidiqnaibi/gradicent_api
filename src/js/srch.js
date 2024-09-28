function searchByName() {
    const nameEntry = document.getElementById('idEntry').value;
    const srchMain = document.getElementById('srchMain');

    fetch('/search_by_name', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name: nameEntry }),
    })
    .then(response => response.json())
    .then(data => {
        renderSearchResult(data, srchMain);
    });
}

function searchByNumber() {
    const numberEntry = document.getElementById('idEntry').value;
    const srchMain = document.getElementById('srchMain');

    fetch('/search_by_number', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ number: numberEntry }),
    })
    .then(response => response.json())
    .then(data => {
        renderPatientInfo(data, srchMain);
    });
}

function renderSearchResult(patients, srchMain) {
    srchMain.innerHTML = '';
    const s = document.getElementById('idFrame');
    s.classList.add('aha');

    if (patients === 'non') {
        const message = document.createElement('label');
        message.textContent = 'The name is not registered';
        message.classList.add('label');
        srchMain.appendChild(message);
    } else {
        patients.forEach((patient) => {
            const patientDiv = createPatientDiv(patient);
            srchMain.appendChild(patientDiv);
        });
    }
}

function renderPatientInfo(patient, srchMain) {
    srchMain.innerHTML = '';

    if (patient) {
        const infoDiv = createPatientInfoDiv(patient);
        srchMain.appendChild(infoDiv);
    } else {
        const message = document.createElement('label');
        message.textContent = 'The number is not registered';
        message.classList.add('label');
        srchMain.appendChild(message);
    }
}

function createPatientDiv(patient) {
    const patientDiv = document.createElement('div');
    patientDiv.classList.add('frame');
    
    const inpuu = document.createElement('div');
    inpuu.classList.add('inpuu');
    const idLabel = createLabel('Patient Number:');
    const idEntry = createEntry(patient.no);
    inpuu.appendChild(idLabel);
    inpuu.appendChild(idEntry);
    patientDiv.appendChild(inpuu);

    const inpuun = document.createElement('div');
    inpuun.classList.add('inpuu');
    const nameLabel = createLabel('Patient Name:');
    const nameEntry = createEntry(patient.name);
    inpuun.appendChild(nameLabel);
    inpuun.appendChild(nameEntry);
    patientDiv.appendChild(inpuun);

    const inpuud = document.createElement('div');
    inpuud.classList.add('inpuu');
    const debitLabel = createLabel('Debit:');
    const debitEntry = createEntry(patient.debit);
    inpuud.appendChild(debitLabel);
    inpuud.appendChild(debitEntry);
    patientDiv.appendChild(inpuud);

    return patientDiv;
}

function createPatientInfoDiv(patient) {
    const infoDiv = document.createElement('div');
    infoDiv.classList.add('frame');

    const labels = [
        { key: 'name', text: 'Patient Name' },
        { key: 'id', text: 'ID Number' },
        { key: 'phone', text: 'Phone Number' },
        { key: 'location', text: 'Location' },
        { key: 'pmh', text: 'Medical History' },
        { key: 'age', text: 'Age' },
        { key: 'payed', text: 'Paid' },
        { key: 'debit', text: 'Debit' }
    ];

    labels.forEach((label) => {
        const labelElement = createLabel(label.text);
        const entryElement = createEntry(patient[label.key]);
        const inpuu = document.createElement('div');
        inpuu.classList.add('inpuu');
        inpuu.appendChild(labelElement);
        inpuu.appendChild(entryElement);
        infoDiv.appendChild(inpuu);
    });

    const saveButton = createButton('Save', () => savePatientInfo(patient.no));
    const openButton = createButton('Open', () => showPage('pat'));

    infoDiv.appendChild(saveButton);
    infoDiv.appendChild(openButton);

    return infoDiv;
}

function createLabel(text) {
    const label = document.createElement('label');
    label.textContent = text;
    label.classList.add('label');
    return label;
}

function createEntry(value) {
    const entry = document.createElement('input');
    entry.type = 'text';
    entry.value = value;
    entry.classList.add('entry');
    entry.readOnly = true;
    return entry;
}

function createButton(text, clickHandler) {
    const button = document.createElement('button');
    button.textContent = text;
    button.classList.add('button');
    button.addEventListener('click', clickHandler);
    return button;
}

function savePatientInfo(patientNo) {
    // Implement the logic to save patient information
    alert('Functionality to save patient info to be implemented.');
}

function showPage(page) {
    // Implement the logic to show the specified page
}
