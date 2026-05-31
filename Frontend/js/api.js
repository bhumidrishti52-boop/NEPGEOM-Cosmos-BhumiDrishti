// Update this URL if deploying or using a different tunnel
const BACKEND_URL = '/analyze-plot';

// Track the latest geometry drawn so we can re-request analysis
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

    } catch (err) {
        console.error('renderResults error:', err);
        document.getElementById('summary-content').innerText = '⚠️ Error displaying results.';
    }
}