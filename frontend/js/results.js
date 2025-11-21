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

  // 6) product summary
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
  if (d.timer?.detected) {
    res.push({
      type: "fake_timer",
      title: "Fake Countdown Timer",
      severity: d.timer.confidence === "high" ? "high" : "medium",
      confidence: d.timer.confidence || "medium",
      explanation: `Flags: ${d.timer.flags ? Object.keys(d.timer.flags).filter(k=>d.timer.flags[k]).join(", ") : "client-only evidence"}`
    });
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
  const statusEl = document.getElementById("timerStatus");
  const confEl = document.getElementById("timerConfidence");
  const list = document.querySelector(".reason-list");

  // In your sample data: timer:{detected:true,confidence:"medium",flags:{frontend_only:true,...},matches:[..]}
  if (d.timer) {
    const fake = !!d.timer.detected;
    if (statusEl) {
      statusEl.textContent = fake ? "Timer status: Suspicious" : "Timer status: Real";
      statusEl.style.background = fake ? "rgba(239,68,68,0.08)" : "rgba(34,197,94,0.06)";
      statusEl.style.color = fake ? "#b91c1c" : "#15803d";
    }
    if (confEl) confEl.textContent = `Confidence: ${d.timer.confidence || 'medium'}`;
    if (list) {
      list.innerHTML = "";
      // prefer reasons if backend supplies them
      if (Array.isArray(d.timer.reasons) && d.timer.reasons.length) {
        d.timer.reasons.forEach(r => { const li = document.createElement('li'); li.textContent = r; list.appendChild(li); });
      } else {
        // build from flags and matches
        if (d.timer.flags) {
          Object.entries(d.timer.flags).forEach(([k,v]) => {
            const li = document.createElement('li'); li.textContent = `${k}: ${v}`; list.appendChild(li);
          });
        }
        if (Array.isArray(d.timer.matches) && d.timer.matches.length) {
          d.timer.matches.forEach(m => { const li = document.createElement('li'); li.textContent = `matched: ${m}`; list.appendChild(li);});
        }
      }
    }
  } else {
    if (statusEl) statusEl.textContent = "Timer not detected";
    if (confEl) confEl.textContent = "";
    if (list) list.innerHTML = "<li>No timer evidence provided.</li>";
  }
}

/* tiny helper */
function escapeHtml(s) {
  if (!s) return "";
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":"&#39;"}[c]));
}
