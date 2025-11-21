 lucide.createIcons();

    function analyze() {
      const url = document.getElementById("urlInput").value;
      if (url.trim() === "") {
        alert("Please paste a valid product link.");
        return;
      }
      alert("Analyzing URL: " + url);
      // Redirect to analysis page later
    }