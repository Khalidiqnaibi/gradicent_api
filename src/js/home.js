// Function to get patient information from the input fields
function get_info() {
    const PatientName = document.getElementById("PName");
    const idnum = document.getElementById("idnum");
    const PhoneNumber = document.getElementById("PNum");
    const loc = document.getElementById("loc");
    const medh = document.getElementById("medh");
    const age = document.getElementById("age");

    const fields = [
        PatientName,
        idnum,
        PhoneNumber,
        loc,
        medh,
        age
    ];

    var info = {
        "name": PatientName.value,
        "id": idnum.value,
        "phone": PhoneNumber.value,
        "location": loc.value,
        "pmh": medh.value,
        "payed": 0,
        "debit": 0,
        "age": age.value,
        "visits": [
            {
                "coast": 0,
                "debit": 0,
                "details": "",
                "diagnosis": " ",
                "lab": "",
                "payed": 0,
                "treatment": "",
                "visit_date": "02-07-2024",
                "vno": 1
            }
        ]
    };

    for (let i = 0, len = fields.length; i < len; i++) {
        fields[i].value = "";
    }

    return info;
}

// Function to add patient information to the backend
async function addPatient(data) {
    try {
        const response = await fetch('http://riasoftware.pythonanywhere.com/addPatient', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        const result = await response.json();
        console.log(result.message);
    } catch (error) {
        console.error('Error adding patient:', error);
    }
}

// Button click handler to add patient
function add_btn() {
    var info = get_info();
    var data = {
        google_id: "{{ user_data.google_id }}",  // Ensure the actual Google ID is used
        patient_info: info
    };
    addPatient(data);
}

