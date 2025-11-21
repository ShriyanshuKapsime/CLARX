console.log("INDEX.JS IS LOADED!");

lucide.createIcons();

async function analyze() {
    const url = document.getElementById("urlInput").value;

    if (url.trim() === "") {
        alert("Please paste a valid product link.");
        return;
    }

    const analyzeBtn = document.getElementById("analyzeBtn");
    analyzeBtn.innerText = "Analyzing...";
    analyzeBtn.disabled = true;

    try {
        const response = await fetch("http://127.0.0.1:5000/analyze", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ url: url })
        });

        if (!response.ok) {
            throw new Error("Server error. Please try again.");
        }

        const data = await response.json();
        console.log("Analysis Result:", data);

        // store result for next page
        localStorage.setItem("analysis_result", JSON.stringify(data));

        // FIX: redirect to actual results page
        window.location.href = "2ndPage.html";

    } catch (error) {
        console.error(error);
        alert("Error analyzing the URL. Make sure backend is running.");
    }

    analyzeBtn.innerText = "Analyze";
    analyzeBtn.disabled = false;
}

