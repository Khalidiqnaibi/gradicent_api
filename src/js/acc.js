const btn1herf = 'https://www.google.com';
const btn2herf = "https://www.google.com/search?client=opera&hs=a7O&sca_esv=a56599857971a1ee&sca_upv=1&sxsrf=ACQVn0-wUK10bMtc0-jHwLG5RZwUQWhZbQ:1707302539870&q=potato&tbm=isch&source=lnms&sa=X&ved=2ahUKEwiduabLhZmEAxVucvEDHW7IC1MQ0pQJegQIDBAB&biw=1278&bih=588&dpr=1.5";

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

function opentab(url) {
    window.open(url);
}

window.addEventListener('DOMContentLoaded', async () => {
    try {
        const userData = "{{ user_data }}"; // Replace with actual Google ID
        const { name, first, payed, plan } = userData;
        const trialDaysLeft = calculateTrialDaysLeft(first);
        const trialStatus = trialDaysLeft > 0 ? "gud" : "bad";

        const HH = document.getElementById("hello");
        const Msg = document.getElementById("msg");
        const Btn1 = document.getElementById("btn1");
        const Btn2 = document.getElementById("btn2");

        if (userData.google_id === 1) {
            HH.textContent = "Please sign up with Google";
            Msg.textContent = "";
            Btn1.textContent = "Sign Up with Google";
            btn1herf = "/logme";
            Btn2.style.display = "none";
        } else if (plan === "free" && trialStatus === "gud") {
            HH.textContent = `Welcome, ${name}`;
            Msg.textContent = `Trial ends in ${trialDaysLeft} days`;
            Btn2.style.margin = "5px";
            Btn2.style.display = "inline-block";
            Btn1.textContent = "Get the full version";
            Btn1.style.margin = "5px";
            btn1herf = "/med_sub";
            btn2herf = "/logme";
        } else if (plan === "free" && trialStatus === "bad") {
            HH.textContent = `Welcome, ${name}`;
            Msg.textContent = "Subscription has ended\n Please pay to continue using the app";
            Btn2.style.display = "inline-block";
            Btn2.style.margin = "5px";
            Btn1.textContent = "Get the full version";
            Btn1.style.margin = "5px";
            btn1herf = "/med_sub";
            btn2herf = "/logme";
        } else {
            HH.textContent = `Welcome, ${name}`;
            Msg.textContent = `Thank you for supporting us \n Subscription ends in ${payed} days`; // Assuming payed is available in user data
            Btn2.style.display = "inline-block";
            Btn1.textContent = "Save Database";
            btn1herf = "/";
            btn2herf = "/logme";
        }
    } catch (error) {
        console.error('Error initializing app:', error);
    }
});
