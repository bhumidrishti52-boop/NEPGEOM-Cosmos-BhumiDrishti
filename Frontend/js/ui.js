// --- Modal Infrastructure ---

function openReportModal() {
    document.getElementById('report-modal').style.display = 'block';
}

function closeReportModal() {
    document.getElementById('report-modal').style.display = 'none';
}

// Stop propagation for clicks inside modal content to prevent closing when clicking content
document.querySelectorAll('.modal-content').forEach(content => {
    content.addEventListener('click', (e) => e.stopPropagation());
});

// Close modals when clicking outside (on the background)
window.onclick = function (event) {
    const reportModal = document.getElementById('report-modal');
    if (event.target == reportModal) {
        closeReportModal();
    }
}

// Global exposure
window.openReportModal = openReportModal;
window.closeReportModal = closeReportModal;
// --- Interactive Download Logic ---

function downloadReport() {
    const btn = document.getElementById('btn-download-report');
    if (!btn) return;
    
    const originalText = btn.innerHTML;

    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating PDF...';
    btn.disabled = true;

    // Simulate PDF generation delay
    setTimeout(() => {
        btn.innerHTML = '✅ Downloaded';
        
        // Reset state after 2 seconds
        setTimeout(() => {
            btn.innerHTML = originalText;
            btn.disabled = false;
        }, 2000);
        
        alert("Report PDF downloaded successfully!");
    }, 1500);
}

// Global exposure
window.downloadReport = downloadReport;