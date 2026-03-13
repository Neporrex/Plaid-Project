const API_URL = "https://plaid-api-6ddd.onrender.com";

async function loadStats() {
    try {
        const res = await fetch(`${API_URL}/api/stats/0`);
        const data = await res.json();
        document.getElementById("stat-trials").textContent = data.trials || 0;
        document.getElementById("stat-users").textContent = data.users || 0;
    } catch (e) {
        console.log("API pas encore connectée");
    }
}

if (document.getElementById("hero-stats")) {
    loadStats();
}
