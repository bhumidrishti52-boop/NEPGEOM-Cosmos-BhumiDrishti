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