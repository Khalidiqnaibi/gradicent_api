function toggleDateEntries() {
    const showDateCheckbox = document.getElementById("show-date");
    const showVisitInfoCheckbox = document.getElementById("show-visit-info");
    const droppFrame = document.getElementById("dropp-frame");
    const dateFrame = document.getElementById("search-entries");
    const resultFrame = document.getElementById("result-frame");
    const searchButton = document.getElementById("searchButton");

    if (showDateCheckbox.checked && showVisitInfoCheckbox.checked) {
        resultFrame.style.display = "none";
        searchButton.style.display = "none";
        dateFrame.style.display = "none";
        droppFrame.style.display = "none";
        dateFrame.style.display = "flex";
        droppFrame.style.display = "flex";
        resultFrame.style.display = "flex";
        searchButton.style.display = "block";
    } else if (showDateCheckbox.checked) {
        resultFrame.style.display = "none";
        searchButton.style.display = "none";
        droppFrame.style.display = "none";
        dateFrame.style.display = "flex";
        resultFrame.style.display = "flex";
        searchButton.style.display = "block";
    } else if (showVisitInfoCheckbox.checked) {
        resultFrame.style.display = "none";
        searchButton.style.display = "none";
        dateFrame.style.display = "none";
        droppFrame.style.display = "flex";
        resultFrame.style.display = "flex";
        searchButton.style.display = "block";
    } else {
        resultFrame.style.display = "none";
        searchButton.style.display = "none";
        droppFrame.style.display = "none";
        dateFrame.style.display = "none";
        resultFrame.style.display = "flex";
        searchButton.style.display = "block";
    }
}

function ssearch() {
    const startDate = document.getElementById("start-date-entry").value;
    const endDate = document.getElementById("end-date-entry").value;
    const details = document.getElementById("details-entry").value;
    const patientNumber = document.getElementById("patientNumber").value;
    const treatment = document.getElementById("treatment").value;
    const diagnosis = document.getElementById("diagnosis").value;
    const lab = document.getElementById("lab").value;
    const showDateCheckbox = document.getElementById("show-date").checked;
    const showVisitInfoCheckbox = document.getElementById("show-visit-info").checked;

    const searchParams = {
        startDate: startDate,
        endDate: endDate,
        details: details,
        patientNumber: patientNumber,
        treatment: treatment,
        diagnosis: diagnosis,
        lab: lab,
        showDate: showDateCheckbox,
        showVisitInfo: showVisitInfoCheckbox
    };

    fetch('http://riasoftware.pythonanywhere.com/ssearch', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(searchParams)
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById("totalPatients").value = data.total_customers;
        document.getElementById("patientsWithDebit").value = data.unpaid_customers;
        document.getElementById("totalDebit").value = data.total_debit;
        document.getElementById("totalRevenue").value = data.total_payed;
    })
    .catch(error => {
        console.error('Error:', error);
    });
}