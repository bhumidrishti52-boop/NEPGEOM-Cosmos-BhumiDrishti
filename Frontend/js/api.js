// Update this URL if deploying or using a different tunnel
const BACKEND_URL = '/analyze-plot';

// Track the latest geometry drawn so we can re-request analysis
let lastGeometry = null;

// UI Helper Functions
function showPanel(panelId) {
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    document.getElementById(panelId).classList.add('active');
}