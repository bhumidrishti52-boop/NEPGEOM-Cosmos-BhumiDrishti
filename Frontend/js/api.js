const BACKEND_URL = '/analyze-plot';


let lastGeometry = null;

// UI Helper Functions
function showPanel(panelId) {
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    document.getElementById(panelId).classList.add('active');
}

// ----------------------
// Core fetch helper
// ----------------------
async function fetchAnalysis(geometry) {
    showPanel('loading-panel');
    const response = await fetch(BACKEND_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ geometry })
    });

    if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
    }

    return await response.json();
}

// ----------------------
// API & Analysis Logic
// ----------------------
map.on('draw.create', async (e) => {
    const feature = e.features[0];
    lastGeometry = feature.geometry;

    try {
        const data = await fetchAnalysis(lastGeometry);
        console.log("Full Backend Response:", data);

        if (data.detail) {
            alert("Analysis Error: " + data.detail);
            showPanel('instructions-panel');
            return;
        }

        renderResults(data);
        lastAnalysisData = data;
        lastRawStats = data.raw_stats || {};
        showPanel('results-panel');

    } catch (err) {
        console.error('API Error:', err);
        alert("⚠️ Backend connection failed.");
        showPanel('instructions-panel');
    }
});

// Keep geometry updated if user edits the polygon after creation
map.on('draw.update', async (e) => {
    if (e.features && e.features.length) {
        lastGeometry = e.features[0].geometry;
        // Re-analyze on edit/move
        try {
            const data = await fetchAnalysis(lastGeometry);
            if (data.detail) {
                alert("Analysis Error: " + data.detail);
                return;
            }
            renderResults(data);
            lastAnalysisData = data;
            lastRawStats = data.raw_stats || {};
            showPanel('results-panel');
        } catch (err) {
            console.error('Update Analysis Error:', err);
        }
    }
});

function renderResults(data) {
    try {
        const qd = data.quantitative_data || {};
        const meta = data.metadata || {};
        const riskData = qd.indicators || [];
        const getMetric = (cat) => riskData.find(m => m.category === cat) || { value: 0, sub_value: 0 };

        const flood = getMetric('flood');
        const landslide = getMetric('landslide');
        const agri = getMetric('agri');

        // Values arrive as % already (0-100) from main.py
        const getColorClass = (val, isInverse = false) => {
            if (isInverse) {
                if (val >= 66) return 'risk-low';
                if (val >= 33) return 'risk-med';
                return 'risk-high';
            }
            if (val >= 50) return 'risk-high';
            if (val >= 20) return 'risk-med';
            return 'risk-low';
        };

        const updateCard = (idPrefix, metric, isInverse = false) => {
            const val = typeof metric.value === 'number' ? metric.value : 0;
            const colorClass = getColorClass(val, isInverse);

            // 1. Update primary value
            const valEl = document.getElementById(`val-${idPrefix}`);
            if (valEl) {
                valEl.innerText = `${val.toFixed(1)}%`;
                valEl.className = `card-value ${colorClass}`;
            }

            // 2. Update sub-label (e.g., Peak vs Localized Hotspot vs Not Applicable)
            const labelEl = document.getElementById(`label-${idPrefix}`);
            if (labelEl && metric.sub_label) {
                // Add colon only if it's a label for a value
                const showColon = metric.sub_label !== "Not Applicable";
                labelEl.innerText = metric.sub_label + (showColon ? ":" : "");
            }

            // 3. Update sub-value (numeric or override)
            const peakEl = document.getElementById(`peak-${idPrefix}`);
            if (peakEl) {
                if (typeof metric.sub_value === 'number') {
                    peakEl.innerText = `${metric.sub_value.toFixed(1)}%`;
                } else if (metric.sub_value === null || metric.sub_label === "Not Applicable") {
                    peakEl.innerText = ""; // Hide if N/A
                } else {
                    peakEl.innerText = metric.sub_value || '--%';
                }
            }

            // 4. Update info tooltip if note exists
            const infoEl = document.getElementById(`info-${idPrefix}`);
            if (infoEl) {
                if (metric.sub_note) {
                    infoEl.title = metric.sub_note;
                    infoEl.style.display = 'inline-block';
                } else {
                    infoEl.style.display = 'none';
                }
            }

            // 5. Update card border color
            const cardEl = document.getElementById(`card-${idPrefix}`);
            if (cardEl) {
                cardEl.classList.remove('border-high', 'border-med', 'border-low');
                if (val >= 50) cardEl.classList.add(isInverse ? 'border-low' : 'border-high');
                else if (val >= 20) cardEl.classList.add('border-med');
                else cardEl.classList.add(isInverse ? 'border-high' : 'border-low');
            }
        };

        updateCard('flood', flood);
        updateCard('landslide', landslide);
        updateCard('agri', agri, true);

        // ── Confidence badge ────────────────────────────────────────
        const confBadge = document.getElementById('confidence-badge');
        if (confBadge) {
            const conf = meta.confidence || 'UNKNOWN';
            const bufM = meta.buffer_m || 0;
            confBadge.innerText = `${conf} confidence${bufM > 0 ? ` · ${bufM} m buffer` : ''}`;
            confBadge.className = 'confidence-badge conf-' + conf.toLowerCase();
        }

        // ── Anomaly / warnings banner ───────────────────────────────
        const warnBanner = document.getElementById('warning-banner');
        if (warnBanner) {
            const warnings = [];
            if (meta.anomaly_flag) {
                warnings.push('⚠️ Model output anomaly detected — all three risk scores near zero. Please report to the Bhumi team.');
            }
            if (meta.outside_roi) {
                warnings.push('⚠️ Location may be outside the model ROI (elevation range 75–1267 m).');
            }
            if (meta.confidence === 'LOW') {
                warnings.push('ℹ️ Score derived from a 60 m buffer around the plot centroid. The parcel is smaller than one 30 m satellite pixel. Results are indicative only; on-site verification is recommended before any land-use decision.');
            }
            if (warnings.length > 0) {
                warnBanner.innerHTML = warnings.map(w => `<div class="warn-line">${w}</div>`).join('');
                warnBanner.style.display = 'block';
            } else {
                warnBanner.style.display = 'none';
            }
        }

        // ── Technical Details ───────────────────────────────────────
        const details = qd.details || {};
        const safeNum = (v, decimals, suffix) => {
            if (v == null || isNaN(v)) return '--' + (suffix || '');
            return v.toFixed(decimals) + (suffix || '');
        };

        document.getElementById('tech-slope').innerText   = safeNum(details.slope, 1, '°');
        document.getElementById('tech-elev').innerText    = safeNum(details.elevation, 0, ' m');
        document.getElementById('tech-lulc').innerText    = details.lulc || 'Unknown';

        // NDVI — show ndvi_wet and ndvi_delta, never raw NDVI
        const ndviEl = document.getElementById('tech-ndvi');
        const ndviSub = document.getElementById('tech-ndvi-sub');
        if (ndviEl) {
            if (details.ndvi_wet != null) {
                ndviEl.innerText = `${details.ndvi_wet.toFixed(3)} / ${(details.ndvi_delta||0).toFixed(3)}`;
                if (ndviSub) ndviSub.style.display = 'block';
            } else {
                ndviEl.innerText = 'non-informative';
                if (ndviSub) ndviSub.style.display = 'none';
            }
        }

        // Soil clay already in % from backend
        document.getElementById('tech-clay').innerText  = safeNum(details.soil_clay_pct, 1, '%');
        document.getElementById('tech-rain').innerText  = safeNum(details.rainfall_mm, 0, ' mm');
        document.getElementById('tech-twi').innerText   = safeNum(details.twi, 2);
        document.getElementById('tech-spi').innerText   = safeNum(details.spi, 2);
        document.getElementById('tech-river').innerText = safeNum(details.river_dist_m, 0, ' m');

        // ── Risk Summary ────────────────────────────────────────────
        const rawSummary = qd.risk_summary || 'No summary available.';
        const cleanSummary = rawSummary.replace(/\*\*/g, '');
        document.getElementById('summary-content').innerText = cleanSummary;

        // Reset payment state for new plot
        window.isPlotUnlocked = false;
        const unlockBtn = document.getElementById('btn-unlock-premium');
        if (unlockBtn) unlockBtn.style.display = 'block';
        const unlockedDiv = document.getElementById('unlocked-buttons');
        if (unlockedDiv) unlockedDiv.style.display = 'none';

        closePaywall();

    } catch (err) {
        console.error('renderResults error:', err);
        document.getElementById('summary-content').innerText = '⚠️ Error displaying results.';
    }
}

// ----------------------
// Store last analysis data for PDF/Chat
// ----------------------
let lastAnalysisData = null;
let lastRawStats = null;

// ----------------------
// PDF Download
// ----------------------
async function downloadReport() {
    if (!lastAnalysisData) {
        alert('Please analyze a plot first.');
        return;
    }

    // Gated Check
    if (!window.isPlotUnlocked) {
        showPaywall('report');
        return;
    }

    const btn = document.getElementById('btn-download-report');
    const origHTML = btn.innerHTML;
    btn.innerHTML = '<span class="btn-icon">⏳</span><span class="btn-label">Generating PDF...</span>';
    btn.disabled = true;

    try {
        const response = await fetch('/generate-report', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ analysis_data: lastAnalysisData })
        });

        if (!response.ok) throw new Error(`Server error: ${response.status}`);

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'bhumi_drishti_report.pdf';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        btn.innerHTML = '<span class="btn-icon">✅</span><span class="btn-label">Downloaded!</span>';
        setTimeout(() => { btn.innerHTML = origHTML; btn.disabled = false; }, 2000);

    } catch (err) {
        console.error('PDF download error:', err);
        alert('⚠️ Failed to generate report.');
        btn.innerHTML = origHTML;
        btn.disabled = false;
    }
}

// ----------------------
// Chat About Land — Paywall
// ----------------------
function openChat() {
    if (!lastAnalysisData) {
        alert('Please analyze a plot first.');
        return;
    }

    // Gated Check
    if (!window.isPlotUnlocked) {
        showPaywall('chat');
        return;
    }

    document.getElementById('chat-panel').style.display = 'block';
    document.getElementById('chat-input').focus();
}

function showPaywall(feature) {
    const modal = document.getElementById('paywall-modal');
    modal.style.display = 'flex';

    const title = document.querySelector('.paywall-card h2');
    const desc = document.querySelector('.paywall-desc');

    if (feature === 'report') {
        title.innerText = "Unlock Detailed Report";
        desc.innerText = "Get a comprehensive Due Diligence PDF report for this specific plot.";
    } else if (feature === 'chat') {
        title.innerText = "Chat About This Plot";
        desc.innerText = "Ask unlimited questions about risks and potential for this specific plot.";
    } else {
        // "premium" or default
        title.innerText = "Unlock Premium Features";
        desc.innerText = "Get a detailed Due Diligence Report (PDF) AND unlimited AI Chat for this specific plot.";
    }
}

function closePaywall() {
    document.getElementById('paywall-modal').style.display = 'none';
}

function processPayment() {
    // Mock payment flow
    const payBtn = document.querySelector('.btn-pay');
    payBtn.innerHTML = '⏳ Processing...';
    payBtn.disabled = true;

    setTimeout(() => {
        // Unlock THIS plot
        window.isPlotUnlocked = true;

        document.getElementById('paywall-modal').style.display = 'none';

        // Update UI: Hide "Unlock", Show "Action" buttons
        const unlockBtn = document.getElementById('btn-unlock-premium');
        if (unlockBtn) unlockBtn.style.display = 'none';

        const unlockedDiv = document.getElementById('unlocked-buttons');
        if (unlockedDiv) unlockedDiv.style.display = 'flex'; // or block

        // Reset pay button for future
        payBtn.innerHTML = '💳 Pay & Unlock (Rs 1500)';
        payBtn.disabled = false;

        alert("Payment Successful! Features unlocked for this plot.");

        // Auto-open chat if they were trying to chat? Or let them click?
        // Just let them click.
    }, 1500);
}

// ----------------------
// Chat Messaging
// ----------------------
async function sendChatMessage() {
    const input = document.getElementById('chat-input');
    const question = input.value.trim();
    if (!question) return;

    const messagesEl = document.getElementById('chat-messages');

    // Add user message
    const userDiv = document.createElement('div');
    userDiv.className = 'chat-msg user-msg';
    userDiv.textContent = question;
    messagesEl.appendChild(userDiv);

    input.value = '';

    // Add typing indicator
    const typingDiv = document.createElement('div');
    typingDiv.className = 'chat-msg typing-msg';
    typingDiv.textContent = 'Thinking...';
    messagesEl.appendChild(typingDiv);
    messagesEl.scrollTop = messagesEl.scrollHeight;

    try {
        const response = await fetch('/chat-land', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question: question,
                land_data: lastRawStats || {}
            })
        });

        const data = await response.json();

        // Replace typing with answer
        typingDiv.className = 'chat-msg bot-msg';
        typingDiv.textContent = data.answer || 'Sorry, I could not generate a response.';

    } catch (err) {
        console.error('Chat error:', err);
        typingDiv.className = 'chat-msg bot-msg';
        typingDiv.textContent = '⚠️ Error getting response. Please try again.';
    }

    messagesEl.scrollTop = messagesEl.scrollHeight;
}

// ----------------------
// Expose functions for other modules
// ----------------------
window.resetUI = function () {
    showPanel('instructions-panel');
    document.getElementById('chat-panel').style.display = 'none';
};
window.downloadReport = downloadReport;
window.openChat = openChat;
window.closePaywall = closePaywall;
window.processPayment = processPayment;
window.sendChatMessage = sendChatMessage;