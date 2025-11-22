// results.js — populate results UI from localStorage OR call backend if ?url= is present
console.log("RESULTS.JS LOADED");

const LOCAL_KEY = "analysis_result"; // same key your index page sets
const API_BASE = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') ? "http://127.0.0.1:5000" : `${window.location.protocol}//${window.location.host}`;

let priceChart = null;

document.addEventListener("DOMContentLoaded", () => {
  // attempt to get data from localStorage
  const stored = localStorage.getItem(LOCAL_KEY);
  const urlParam = new URLSearchParams(window.location.search).get("url");

  if (stored) {
    try {
      const parsed = JSON.parse(stored);
      // older responses saved {"detections": {...}} -> normalize
      const detections = parsed.detections ? parsed.detections : parsed;
      populateFromDetections(detections);
      return;
    } catch (e) {
      console.warn("Could not parse local analysis_result:", e);
    }
  }

  // if no local data but url param present -> call backend
  if (urlParam) {
    analyzeRemote(urlParam);
    return;
  }

  // nothing to show
  showError("No analysis result found. Go back and analyze a product.");
});

async function analyzeRemote(productUrl) {
  try {
    showLoading();
    const resp = await fetch(`${API_BASE}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: productUrl })
    });

    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || "Server error");

    const detections = data.detections || data;
    // store for subsequent visits
    localStorage.setItem(LOCAL_KEY, JSON.stringify({ detections }));
    populateFromDetections(detections);
  } catch (err) {
    console.error(err);
    showError(err.message || "Analysis failed");
  }
}

function showLoading() {
  document.getElementById("trustGrade").textContent = "…";
  const pill = document.querySelector(".risk-label");
  if (pill) pill.textContent = "Analyzing…";
}

function showError(msg) {
  document.getElementById("trustGrade").textContent = "?";
  const pill = document.querySelector(".risk-label");
  if (pill) pill.textContent = "Error";
  alert(msg);
}

function populateFromDetections(d) {
  // d is the "detections" object your backend returns
  // sample keys you used: addons, drip_pricing, price_history, price_info, scarcity, timer, etc.
  // 1) Trust grade: derive simple grade from findings (example heuristic)
  const riskScore = computeRiskScore(d);
  const grade = riskScoreToGrade(riskScore);
  setTrustGrade(grade);

  // 2) Risk pill label
  const riskLabel = document.querySelector(".risk-label");
  if (riskLabel) {
    const summary = d.scarcity?.detected ? "Scarcity detected" : "Manipulation signals";
    riskLabel.textContent = summary;
  }

  // 3) Violations grid
  const violations = buildViolationsList(d);
  renderViolations(violations);

  // 4) Price info & history
  const priceInfo = d.price_info || {};
  const priceHistory = (d.price_history && Array.isArray(d.price_history)) ? d.price_history : (d.price_history || []);
  renderPriceStats(priceInfo, priceHistory);

  // 5) Timer / scarcity
  renderTimerAndReasons(d);

  // 6) MRP Inflation Check
  renderMrpInflation(d);

  // 7) product summary
  const summaryEl = document.getElementById("productSummary");
  if (summaryEl) {
    const priceText = priceInfo.price ? `Current price ₹${priceInfo.price}` : "";
    summaryEl.textContent = `${priceText} — ${violations.length} suspicious signals found.`;
  }
}

/* small heuristics */
function computeRiskScore(d) {
  // 0..100, simplistic scoring: add points for each detection
  let score = 0;
  if (d.scarcity?.detected) score += 22;
  if (d.timer?.detected) score += 20;
  if (d.addons?.detected) score += 18;
  if (d.drip_pricing?.detected) score += 18;
  // price anomalies
  if (d.price_info?.price && d.price_info?.mrp) {
    const p = d.price_info.price, m = d.price_info.mrp;
    if (m && p && m > p * 1.4) score += 10;
  }
  return Math.min(100, score);
}
function riskScoreToGrade(score) {
  if (score <= 20) return "A";
  if (score <= 45) return "B";
  if (score <= 70) return "C";
  if (score <= 90) return "D";
  return "F";
}
function setTrustGrade(g) {
  const el = document.getElementById("trustGrade");
  if (el) el.textContent = g;
  // color pill
  const pill = document.querySelector(".risk-dot");
  if (pill) {
    if (g === "A") pill.style.background = "#16a34a";
    else if (g === "B") pill.style.background = "#facc15";
    else pill.style.background = "#ef4444";
  }
}

/* Violations conversion: convert backend detection object into an array of objects:
   { type, title, severity, confidence, explanation } */
function buildViolationsList(d) {
  const res = [];
  // example known detectors
  if (d.scarcity?.detected) {
    res.push({
      type: "scarcity",
      title: "Fake Scarcity / Low stock",
      severity: d.scarcity.confidence === "high" ? "high" : "medium",
      confidence: d.scarcity.confidence || "medium",
      explanation: `Matched text: ${Array.isArray(d.scarcity.matches) ? d.scarcity.matches.join(", ") : ""}`
    });
  }
  if (d.timer?.detected === true) {
    // Only add to violations if timer is detected AND has suspicious flags
    const flags = d.timer.flags || {};
    const hasSuspiciousFlags = Object.values(flags).some(v => v === true);
    
    if (hasSuspiciousFlags) {
      res.push({
        type: "fake_timer",
        title: "Fake Countdown Timer",
        severity: d.timer.confidence === "high" ? "high" : "medium",
        confidence: d.timer.confidence || "medium",
        explanation: d.timer.friendly_msg || `Suspicious flags: ${Object.keys(flags).filter(k=>flags[k]).join(", ")}`
      });
    }
  }
  if (d.addons?.detected) {
    res.push({
      type: "add_on",
      title: "Pre-ticked Add-on",
      severity: "low",
      confidence: d.addons.confidence || "low",
      explanation: `Found ${d.addons.matches?.length || 0} add-on matches`
    });
  }
  if (d.drip_pricing?.detected) {
    res.push({
      type: "drip_pricing",
      title: "Drip Pricing",
      severity: "medium",
      confidence: d.drip_pricing.confidence || "medium",
      explanation: d.drip_pricing.explanation || "Charges added later in the flow"
    });
  }

  // If backend provides a list of violations directly (common format), map them
  if (Array.isArray(d.violations)) {
    d.violations.forEach(v => {
      res.push({
        type: v.type || "violation",
        title: v.title || v.type || "Violation",
        severity: v.severity || "medium",
        confidence: v.confidence || "medium",
        explanation: v.explanation || v.reason || ""
      });
    });
  }

  return res;
}

function renderViolations(list) {
  const grid = document.getElementById("violationsGrid");
  if (!grid) return;
  grid.innerHTML = "";
  if (!list || list.length === 0) {
    grid.innerHTML = `<div class="pattern-card"><p class="muted">No dark patterns detected.</p></div>`;
    return;
  }
  list.forEach(v => {
    const art = document.createElement("article");
    art.className = "pattern-card";
    const sev = (v.severity || "medium").toLowerCase();
    art.innerHTML = `
      <div class="pattern-header">
        <h3>${escapeHtml(v.title)}</h3>
        <span class="severity ${sev}">${sev.charAt(0).toUpperCase()+sev.slice(1)}</span>
      </div>
      <p class="muted">${escapeHtml(v.explanation || "")}</p>
      <strong>Confidence: ${escapeHtml((v.confidence||"medium"))}</strong>
    `;
    grid.appendChild(art);
  });
}

/* price rendering */
function renderPriceStats(priceInfo, history) {
  const cur = document.getElementById("currentPrice");
  const siteMrp = document.getElementById("siteMrp");
  const last = document.getElementById("lastRecorded");
  const count = document.getElementById("historyCount");

  const current = priceInfo.price || null;
  const mrp = priceInfo.mrp || null;

  if (cur) cur.textContent = current ? `₹${Number(current).toLocaleString('en-IN')}` : "—";
  if (siteMrp) siteMrp.textContent = mrp ? `₹${Number(mrp).toLocaleString('en-IN')}` : "—";
  if (last) {
    if (history && history.length > 0) last.textContent = history[history.length-1].timestamp || history[history.length-1].ts || "—";
    else last.textContent = "—";
  }
  if (count) count.textContent = history ? history.length : 0;

  renderPriceHistoryList(history || []);
  renderPriceChart(history || [], current);
}

function renderPriceHistoryList(history) {
  const container = document.getElementById("priceHistoryList");
  if (!container) return;
  container.innerHTML = "";
  if (!history || history.length === 0) {
    container.innerHTML = `<div class="history-list"><div class="muted">No price history available.</div></div>`;
    return;
  }
  const wrap = document.createElement("div");
  wrap.className = "history-list";
  history.slice().reverse().forEach(item => {
    const row = document.createElement("div");
    row.className = "history-row";
    const time = item.timestamp || item.ts || item.time || "";
    const mrp = item.mrp ? `MRP ${item.mrp}` : "";
    row.innerHTML = `<div>${time}</div><div>₹${Number(item.price).toLocaleString('en-IN')} ${mrp}</div>`;
    wrap.appendChild(row);
  });
  container.appendChild(wrap);
}

function renderPriceChart(history, current) {
  const ctx = document.getElementById("priceChart");
  if (!ctx) return;
  const labels = (history || []).map(h => {
    const ts = h.timestamp || h.ts || h.time;
    try { return new Date(ts).toLocaleString('en-IN',{month:'short',day:'numeric'});} catch(e){return ts||"";}
  });
  const data = (history || []).map(h => Number(h.price));

  // if no data, create placeholder
  const labelsFinal = labels.length ? labels : ['Now'];
  const dataFinal = data.length ? data : [current || 0];

  if (priceChart) {
    priceChart.data.labels = labelsFinal;
    priceChart.data.datasets[0].data = dataFinal;
    priceChart.update();
    return;
  }

  priceChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labelsFinal,
      datasets: [{
        label: 'price',
        data: dataFinal,
        borderColor: getComputedStyle(document.documentElement).getPropertyValue('--risk-color') || '#facc15',
        backgroundColor: 'rgba(37,99,235,0.08)',
        fill: true,
        pointRadius: 0,
        tension: 0.35,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: '#94a3b8' } },
        y: { ticks: { color: '#94a3b8', callback: v => `₹${v.toLocaleString('en-IN')}`} }
      }
    }
  });
}

/* timer / reasons */
function renderTimerAndReasons(d) {
  const timerSection = document.getElementById("timerSection");
  const statusEl = document.getElementById("timerStatus");
  const confEl = document.getElementById("timerConfidence");
  const list = document.querySelector(".reason-list");

  // If no timer data, hide the section
  if (!d.timer) {
    if (timerSection) timerSection.style.display = "none";
    return;
  }

  // Show the section
  if (timerSection) timerSection.style.display = "";

  // If timer is NOT detected, hide the section or show minimal message
  if (d.timer.detected === false) {
    if (timerSection) {
      // Option 1: Hide entirely
      timerSection.style.display = "none";
      // Option 2: Show minimal message (uncomment if preferred)
      // timerSection.style.display = "";
      // if (statusEl) {
      //   statusEl.textContent = "No timer or countdown found on this product.";
      //   statusEl.style.background = "rgba(148,163,184,0.08)";
      //   statusEl.style.color = "#64748b";
      // }
      // if (confEl) confEl.textContent = "";
      // if (list) list.innerHTML = "";
    }
    return;
  }

  // Timer WAS detected - show full analysis
  if (d.timer.detected === true) {
    // Display friendly message
    if (d.timer.friendly_msg && list) {
      const friendlyLi = document.createElement('li');
      friendlyLi.style.fontWeight = "600";
      friendlyLi.style.marginBottom = "8px";
      friendlyLi.textContent = d.timer.friendly_msg;
      list.innerHTML = "";
      list.appendChild(friendlyLi);
    }

    // Determine if timer is suspicious based on flags
    const flags = d.timer.flags || {};
    const hasSuspiciousFlags = Object.values(flags).some(v => v === true);
    
    if (statusEl) {
      if (hasSuspiciousFlags) {
        statusEl.textContent = "Timer Detected: Suspicious";
        statusEl.style.background = "rgba(239,68,68,0.08)";
        statusEl.style.color = "#b91c1c";
      } else {
        statusEl.textContent = "Timer Detected: Legitimate";
        statusEl.style.background = "rgba(34,197,94,0.06)";
        statusEl.style.color = "#15803d";
      }
    }

    // Show confidence
    if (confEl) {
      const confidence = d.timer.confidence || "medium";
      confEl.textContent = `Confidence: ${confidence}`;
    }

    // Show flags
    if (list && flags) {
      const flagsList = document.createElement('ul');
      flagsList.style.marginTop = "12px";
      flagsList.style.paddingLeft = "20px";
      flagsList.style.listStyle = "disc";
      
      Object.entries(flags).forEach(([key, value]) => {
        if (value === true) {
          const li = document.createElement('li');
          const flagLabels = {
            "reset_on_refresh": "Timer resets on page refresh",
            "frontend_only": "Client-side only timer (no server validation)",
            "missing_tnc": "Missing expiry date or terms & conditions"
          };
          li.textContent = flagLabels[key] || `${key}: ${value}`;
          li.style.marginBottom = "4px";
          flagsList.appendChild(li);
        }
      });
      
      if (flagsList.children.length > 0) {
        list.appendChild(flagsList);
      }
    }

    // Show matches (detection evidence)
    if (d.timer.matches && Array.isArray(d.timer.matches) && d.timer.matches.length > 0 && list) {
      const matchesDiv = document.createElement('div');
      matchesDiv.style.marginTop = "12px";
      matchesDiv.style.fontSize = "0.875rem";
      matchesDiv.style.color = "#64748b";
      matchesDiv.innerHTML = `<strong>Detection evidence:</strong> ${d.timer.matches.join(", ")}`;
      list.appendChild(matchesDiv);
    }
  }
}

/* MRP Inflation Check */
function renderMrpInflation(d) {
  const el = document.getElementById("mrpCheckContent");
  if (!el) return;

  // Get MRP Reality Check data (new comprehensive check)
  const mrpReality = d.mrp_reality_check || {};
  const priceInfo = d.price_info || {};
  const mrpCheck = d.mrp_check || d.mrp_inflation || {};
  
  // Use MRP from mrp_reality_check first, then fallback
  const listedMrp = mrpReality.listed_mrp || priceInfo.mrp || mrpCheck.listed_mrp || null;
  const benchmarkMrp = mrpReality.benchmark_mrp || null;
  const inflationFactor = mrpReality.inflation_factor || null;
  const mrpSource = mrpReality.mrp_source || null;
  const confidence = mrpReality.confidence || null;
  const price = priceInfo.price || mrpCheck.price || null;

  // If no MRP found anywhere
  if (!listedMrp && listedMrp !== 0) {
    el.innerHTML = `
      <div class="mrp-status">
        <p class="muted">MRP not provided. Could not verify authenticity.</p>
      </div>
    `;
    return;
  }

  // If no price, can't compare
  if (!price && price !== 0) {
    el.innerHTML = `
      <div class="mrp-status">
        <p class="muted">MRP: ₹${Number(listedMrp).toLocaleString('en-IN')}</p>
        <p class="muted">Price information not available for comparison.</p>
      </div>
    `;
    return;
  }

  // Check if MRP is inflated
  const ratio = listedMrp / price;
  const isInflated = inflationFactor ? inflationFactor > 1.3 : ratio > 1.4;

  // Display based on MRP Reality Check data
  if (isInflated) {
    const multiplier = inflationFactor ? inflationFactor.toFixed(1) : ratio.toFixed(1);
    const severity = (inflationFactor || ratio) > 2.5 ? 'high' : 'medium';
    
    el.innerHTML = `
      <div class="mrp-status inflated ${severity}">
        <div class="mrp-warning">
          <h3>⚠️ Possible MRP Inflation</h3>
          <div class="mrp-details">
            <div class="mrp-comparison">
              <div><strong>Listed MRP:</strong> ₹${Number(listedMrp).toLocaleString('en-IN')}</div>
              ${benchmarkMrp ? `<div><strong>Benchmark MRP:</strong> ₹${Number(benchmarkMrp).toLocaleString('en-IN')}</div>` : ''}
              <div><strong>Selling Price:</strong> ₹${Number(price).toLocaleString('en-IN')}</div>
              ${inflationFactor ? `<div><strong>Inflation factor:</strong> ${multiplier}× inflated compared to ${benchmarkMrp ? 'market average' : 'selling price'}</div>` : `<div><strong>This MRP might be inflated by ${multiplier}×.</strong></div>`}
            </div>
            ${mrpSource ? `<small class="muted">MRP source: ${mrpSource} (${confidence || 'unknown'} confidence)</small>` : ''}
          </div>
        </div>
      </div>
    `;
    return;
  }

  // MRP appears reasonable
  el.innerHTML = `
    <div class="mrp-status genuine">
      <p>✔️ The MRP appears reasonable.</p>
      <div class="mrp-details">
        <div class="mrp-comparison">
          <div><strong>Listed MRP:</strong> ₹${Number(listedMrp).toLocaleString('en-IN')}</div>
          ${benchmarkMrp ? `<div><strong>Benchmark MRP:</strong> ₹${Number(benchmarkMrp).toLocaleString('en-IN')}</div>` : ''}
          <div><strong>Selling Price:</strong> ₹${Number(price).toLocaleString('en-IN')}</div>
        </div>
        ${mrpSource ? `<small class="muted">MRP source: ${mrpSource} (${confidence || 'unknown'} confidence)</small>` : ''}
      </div>
    </div>
  `;
}

/* tiny helper */
function escapeHtml(s) {
  if (!s) return "";
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":"&#39;"}[c]));
}
