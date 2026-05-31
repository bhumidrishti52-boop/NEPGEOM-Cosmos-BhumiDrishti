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