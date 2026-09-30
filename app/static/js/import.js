function toggleSidebar() {
    const layout = document.querySelector('.app-layout');
    if (layout) {
        layout.classList.toggle('sidebar-collapsed');
    }
}
window.toggleSidebar = toggleSidebar;

document.addEventListener('DOMContentLoaded', () => {
    // 1. Initial DB Status check
    checkDBStatus();

    // Check query params for view switching
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('view') === 'validation') {
        showValidationView();
    } else if (urlParams.get('view') === 'check-error') {
        showCheckErrorView();
    }

    // 2. CSV Import Form, Drag & Drop, and File Input Change Listeners
    document.querySelectorAll('.upload-form').forEach(form => {
        const key = form.dataset.key;
        const expectedFile = form.dataset.expected;
        const fileInput = form.querySelector('input[type="file"]');
        const btn = form.querySelector('button[type="submit"]');
        const dropzone = document.getElementById(`dropzone-${key}`);

        if (dropzone && fileInput) {
            // Click dropzone to trigger hidden native file input
            dropzone.addEventListener('click', (e) => {
                if (e.target.classList && e.target.classList.contains('file-remove-btn')) return;
                if (!fileInput.disabled) {
                    fileInput.click();
                } else if (!isDBConnected()) {
                    alert('Oracle Database Disconnected\n\nPlease connect to database first using [ Database Connection ] modal.');
                }
            });

            // Drag and drop event listeners
            ['dragenter', 'dragover'].forEach(eventName => {
                dropzone.addEventListener(eventName, (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    if (!fileInput.disabled) {
                        dropzone.classList.add('drag-over');
                    }
                }, false);
            });

            ['dragleave', 'drop'].forEach(eventName => {
                dropzone.addEventListener(eventName, (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    dropzone.classList.remove('drag-over');
                }, false);
            });

            dropzone.addEventListener('drop', (e) => {
                const dt = e.dataTransfer;
                const files = dt ? dt.files : null;
                if (files && files.length > 0) {
                    if (fileInput.disabled) {
                        alert('Database Disconnected. Please connect to Oracle Database first.');
                        return;
                    }
                    fileInput.files = files;
                    handleFileSelection(key, files[0], expectedFile, btn);
                }
            });
        }

        if (fileInput) {
            fileInput.addEventListener('change', () => {
                if (fileInput.files.length > 0) {
                    handleFileSelection(key, fileInput.files[0], expectedFile, btn);
                }
            });
        }

        form.addEventListener('submit', async (e) => {
            e.preventDefault();

            if (!fileInput || !fileInput.files.length) {
                alert('Please select or drop a CSV file to upload.');
                if (btn) btn.disabled = true;
                return;
            }

            const file = fileInput.files[0];
            if (file.name !== expectedFile) {
                alert(`Incorrect File Uploaded!\n\nThis section expects: ${expectedFile}\nYou selected: ${file.name}`);
                setCardStatusBadge(key, 'ERROR', 'badge-error');
                return;
            }

            // Show progress section and set badge to PROCESSING
            const progSection = document.getElementById(`prog-${key}`);
            if (progSection) progSection.style.display = 'block';

            const cardEl = document.getElementById(`card-${key}`);
            if (cardEl) {
                cardEl.classList.remove('card-completed', 'card-error');
                cardEl.classList.add('card-processing');
            }

            setCardStatusBadge(key, 'PROCESSING…', 'badge-processing');

            if (btn) {
                btn.disabled = true;
                btn.innerHTML = '<span class="btn-spinner"></span> Importing…';
            }

            // Log activity to Live Feed
            const cardTitleEl = cardEl ? cardEl.querySelector('.module-card-title') : null;
            const targetTagEl = cardEl ? cardEl.querySelector('.module-accent-tag') : null;
            logLiveActivity(
                new Date().toLocaleTimeString(),
                cardTitleEl ? cardTitleEl.textContent : key.toUpperCase(),
                targetTagEl ? targetTagEl.textContent : '-',
                file.name,
                'PROCESSING',
                'badge-processing',
                'In Progress'
            );

            const fd = new FormData();
            fd.append('file', file);
            fd.append('expected_filename', expectedFile);

            let jobId;
            try {
                const res = await fetch('/import', { method: 'POST', body: fd });
                const data = await res.json();
                if (!res.ok) {
                    alert(data.detail || 'Upload failed.');
                    setCardStatusBadge(key, 'ERROR', 'badge-error');
                    if (cardEl) {
                        cardEl.classList.remove('card-processing');
                        cardEl.classList.add('card-error');
                    }
                    resetBtn(btn);
                    return;
                }
                jobId = data.job_id;
            } catch (err) {
                alert('Network error during file upload.');
                setCardStatusBadge(key, 'ERROR', 'badge-error');
                if (cardEl) {
                    cardEl.classList.remove('card-processing');
                    cardEl.classList.add('card-error');
                }
                resetBtn(btn);
                return;
            }

            // Connect WebSocket for real-time progress
            openWS(jobId, key, expectedFile, btn);
        });
    });
});

// Helper for file selection, inspection, size & format validation
function handleFileSelection(key, file, expectedFile, btn) {
    const detailsPill = document.getElementById(`details-${key}`);
    const dropzone = document.getElementById(`dropzone-${key}`);
    const fnameEl = document.getElementById(`fname-${key}`);
    const fmetaEl = document.getElementById(`fmeta-${key}`);

    if (fnameEl) fnameEl.textContent = file.name;

    const sizeFormatted = formatFileSize(file.size);
    const isValidName = (file.name === expectedFile);

    if (fmetaEl) {
        fmetaEl.innerHTML = `${sizeFormatted} &bull; ${isValidName ? '<span style="color:#10b981">Format Valid ✓</span>' : '<span style="color:#ef4444">Filename Mismatch ✗</span>'}`;
    }

    if (isValidName) {
        setCardStatusBadge(key, 'READY', 'badge-ready');
        if (btn && isDBConnected()) {
            btn.disabled = false;
        }
    } else {
        setCardStatusBadge(key, 'INVALID NAME', 'badge-error');
        if (btn) btn.disabled = true;
    }

    if (detailsPill) detailsPill.style.display = 'flex';
    if (dropzone) dropzone.style.display = 'none';
}

function clearSelectedFile(key) {
    const form = document.querySelector(`.upload-form[data-key="${key}"]`);
    if (form) {
        const fileInput = form.querySelector('input[type="file"]');
        const btn = form.querySelector('button[type="submit"]');
        if (fileInput) fileInput.value = '';
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<span class="btn-icon">⚡</span> <span class="btn-text">Validate &amp; Import</span>';
        }
    }

    const detailsPill = document.getElementById(`details-${key}`);
    const dropzone = document.getElementById(`dropzone-${key}`);
    const cardEl = document.getElementById(`card-${key}`);

    if (detailsPill) detailsPill.style.display = 'none';
    if (dropzone) dropzone.style.display = 'flex';
    if (cardEl) cardEl.classList.remove('card-completed', 'card-error', 'card-processing');

    setCardStatusBadge(key, 'READY', 'badge-ready');
}
window.clearSelectedFile = clearSelectedFile;

function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function setCardStatusBadge(key, text, badgeClass) {
    const badge = document.getElementById(`badge-${key}`);
    if (badge) {
        badge.textContent = text;
        badge.className = `status-badge ${badgeClass}`;
    }
}

function logLiveActivity(timestamp, moduleName, targetTable, filename, status, statusClass, records) {
    const tbody = document.getElementById('activity-log-tbody');
    if (!tbody) return;

    const emptyRow = document.getElementById('activity-empty-row');
    if (emptyRow) emptyRow.style.display = 'none';

    const tr = document.createElement('tr');
    tr.className = 'activity-row-anim';
    tr.innerHTML = `
        <td><span class="time-txt">${timestamp}</span></td>
        <td><strong>${moduleName}</strong></td>
        <td><code>${targetTable}</code></td>
        <td><span class="file-name-code">${filename}</span></td>
        <td><span class="status-badge ${statusClass}">${status}</span></td>
        <td><strong>${records}</strong></td>
    `;
    tbody.insertBefore(tr, tbody.firstChild);

    // Keep max 10 recent items
    while (tbody.children.length > 11) {
        tbody.removeChild(tbody.lastChild);
    }
}

function clearLiveActivityLog() {
    const tbody = document.getElementById('activity-log-tbody');
    if (tbody) {
        tbody.innerHTML = `
            <tr class="activity-empty-row" id="activity-empty-row">
                <td colspan="6">
                    <div class="empty-log-state">
                        <span>📡</span> Ready for CSV imports. Select or drop a CSV file above to execute validation.
                    </div>
                </td>
            </tr>
        `;
    }
}
window.clearLiveActivityLog = clearLiveActivityLog;

// =============================================================================
// TAB VIEW SWITCHING (HOME VS CIB CSV VALIDATION VS CHECK ERROR)
let isDashboardCardsVisible = false;

function showHomeView() {
    const homeView = document.getElementById('home-view');
    const valView = document.getElementById('validation-view');
    const errView = document.getElementById('check-error-view');

    const tabHome = document.getElementById('nav-tab-home');
    const tabVal = document.getElementById('nav-tab-validation');
    const tabErr = document.getElementById('nav-tab-check-error');

    const cardsGrid = document.getElementById('dashboard-cards-grid');

    const wasHomeHidden = homeView && (homeView.style.display === 'none');

    if (homeView) homeView.style.display = 'block';
    if (valView) valView.style.display = 'none';
    if (errView) errView.style.display = 'none';

    if (tabHome) tabHome.classList.add('active');
    if (tabVal) tabVal.classList.remove('active');
    if (tabErr) tabErr.classList.remove('active');

    // Toggle show / hide circular orbit workflow container on Dashboard click
    const orbitContainer = document.getElementById('workflow-carousel-container');
    if (orbitContainer) {
        if (wasHomeHidden) {
            // Coming from another view -> show orbit with entrance animation
            orbitContainer.style.display = 'block';
            orbitContainer.classList.remove('orbit-collapsing', 'orbit-emerging');
            void orbitContainer.offsetWidth; // Force CSS reflow
            orbitContainer.classList.add('orbit-emerging');
            window.isOrbitPanelVisible = true;
        } else {
            // Clicked Dashboard while already on Dashboard -> toggle show / hide!
            if (window.isOrbitPanelVisible !== false) {
                // Smoothly collapse / disappear
                orbitContainer.classList.remove('orbit-emerging');
                orbitContainer.classList.add('orbit-collapsing');
                setTimeout(() => {
                    if (window.isOrbitPanelVisible === false) {
                        orbitContainer.style.display = 'none';
                    }
                }, 380);
                window.isOrbitPanelVisible = false;
            } else {
                // Smoothly emerge / appear
                orbitContainer.style.display = 'block';
                orbitContainer.classList.remove('orbit-collapsing');
                void orbitContainer.offsetWidth; // Force CSS reflow
                orbitContainer.classList.add('orbit-emerging');
                window.isOrbitPanelVisible = true;
            }
        }
    }

    // Keep home view viewport fit clean without page vertical scrollbars
    document.body.style.overflow = 'hidden';
    const cont = document.querySelector('.container');
    if (cont) { cont.style.paddingBottom = '0'; cont.style.overflowY = 'hidden'; }
}

function showValidationView() {
    const homeView = document.getElementById('home-view');
    const valView = document.getElementById('validation-view');
    const errView = document.getElementById('check-error-view');

    const tabHome = document.getElementById('nav-tab-home');
    const tabVal = document.getElementById('nav-tab-validation');
    const tabErr = document.getElementById('nav-tab-check-error');

    if (homeView) homeView.style.display = 'none';
    if (valView) valView.style.display = 'block';
    if (errView) errView.style.display = 'none';

    if (tabHome) tabHome.classList.remove('active');
    if (tabVal) tabVal.classList.add('active');
    if (tabErr) tabErr.classList.remove('active');
    // Enable normal page scrollbar
    document.body.style.overflow = 'auto';
    const cont = document.querySelector('.container');
    if (cont) { cont.style.paddingBottom = ''; cont.style.overflowY = ''; }
}

function showCheckErrorView() {
    const homeView = document.getElementById('home-view');
    const valView = document.getElementById('validation-view');
    const errView = document.getElementById('check-error-view');

    const tabHome = document.getElementById('nav-tab-home');
    const tabVal = document.getElementById('nav-tab-validation');
    const tabErr = document.getElementById('nav-tab-check-error');

    if (homeView) homeView.style.display = 'none';
    if (valView) valView.style.display = 'none';
    if (errView) errView.style.display = 'block';

    if (tabHome) tabHome.classList.remove('active');
    if (tabVal) tabVal.classList.remove('active');
    if (tabErr) tabErr.classList.add('active');
    // Restore scroll + container spacing for check-error view
    document.body.style.overflow = 'auto';
    const cont2 = document.querySelector('.container');
    if (cont2) { cont2.style.paddingBottom = ''; cont2.style.overflowY = ''; }

    // Automatically trigger error load logic if connected
    if (typeof loadCheckErrors === 'function') {
        if (typeof isDBConnected === 'function' && isDBConnected()) {
            loadCheckErrors();
        } else {
            if (typeof showCheckErrorDisconnectedUI === 'function') {
                showCheckErrorDisconnectedUI();
            }
        }
    }
}

window.showHomeView = showHomeView;
window.showValidationView = showValidationView;
window.showCheckErrorView = showCheckErrorView;

// =============================================================================
// DATABASE CONNECTION MANAGER (FRONTEND)
// =============================================================================

let isDBConnectedState = false;

function isDBConnected() {
    return isDBConnectedState;
}

async function checkDBStatus() {
    try {
        const res = await fetch('/api/db/status');
        if (!res.ok) return;
        const data = await res.json();
        updateDBStatusUI(data.connected, data);
    } catch (err) {
        console.warn("Could not fetch DB status:", err);
        updateDBStatusUI(false, null);
    }
}

function updateDBStatusUI(isConnected, info) {
    isDBConnectedState = isConnected;
    const badge = document.getElementById('nav-db-badge');
    const text = document.getElementById('nav-db-status-text');
    const banner = document.getElementById('db-access-banner');
    const disconnectBtn = document.getElementById('db-disconnect-btn');
    const homeDbVal = document.getElementById('home-db-status-val');
    const forms = document.querySelectorAll('.upload-form');

    if (isConnected) {
        if (badge) {
            badge.className = 'db-status-badge connected';
            text.textContent = 'Connected';
        }
        if (homeDbVal) {
            homeDbVal.textContent = 'Connected';
            homeDbVal.style.color = '#34d399';
        }
        if (banner) banner.style.display = 'none';
        if (disconnectBtn) disconnectBtn.style.display = 'inline-block';

        // Enable CSV inputs, but enable Execute button ONLY if a file is selected
        forms.forEach(form => {
            const input = form.querySelector('input[type="file"]');
            const btn = form.querySelector('button[type="submit"]');
            if (input) input.disabled = false;
            if (btn) btn.disabled = (!input || !input.files.length);
        });
        if (typeof window.refreshErrorSummaryCount === 'function') {
            window.refreshErrorSummaryCount(true);
        }
    } else {
        if (badge) {
            badge.className = 'db-status-badge disconnected';
            text.textContent = 'Database Disconnected';
        }
        if (homeDbVal) {
            homeDbVal.textContent = 'Disconnected';
            homeDbVal.style.color = '#fca5a5';
        }
        if (banner) banner.style.display = 'flex';
        if (disconnectBtn) disconnectBtn.style.display = 'none';

        // Disable CSV inputs and buttons
        forms.forEach(form => {
            const input = form.querySelector('input[type="file"]');
            const btn = form.querySelector('button[type="submit"]');
            if (input) input.disabled = true;
            if (btn) btn.disabled = true;
        });

        const kpiErrEl = document.getElementById('kpi-total-errors');
        if (kpiErrEl) kpiErrEl.textContent = '0';
    }

    // Refresh Scheduler & Summary button access status
    if (typeof window.checkSchedulerSummaryAccess === 'function') {
        window.checkSchedulerSummaryAccess();
    }
}

function openDBModal() {
    const modal = document.getElementById('db-modal-overlay');
    if (modal) {
        modal.style.display = 'flex';
    } else {
        console.error("db-modal-overlay element not found");
    }
    checkDBStatus();
}

function closeDBModal() {
    const modal = document.getElementById('db-modal-overlay');
    const alertBox = document.getElementById('db-modal-alert');
    if (modal) modal.style.display = 'none';
    if (alertBox) alertBox.style.display = 'none';
}

async function handleDBConnect(event) {
    if (event) event.preventDefault();

    const host = document.getElementById('db-host').value.trim();
    const port = parseInt(document.getElementById('db-port').value.trim(), 10);
    const service = document.getElementById('db-service').value.trim();
    const username = document.getElementById('db-username').value.trim();
    const password = document.getElementById('db-password').value;

    const alertBox = document.getElementById('db-modal-alert');
    const btn = document.getElementById('db-connect-btn');

    alertBox.style.display = 'block';
    alertBox.className = 'modal-alert info';
    alertBox.textContent = '⏳ Testing connection to Oracle Database... Please wait.';

    btn.disabled = true;
    btn.textContent = 'Connecting...';

    try {
        const res = await fetch('/api/db/connect', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ host, port, service, username, password })
        });

        const data = await res.json();

        if (res.ok && data.connected) {
            alertBox.className = 'modal-alert success';
            alertBox.textContent = `✓ ${data.message}`;
            updateDBStatusUI(true, data);

            setTimeout(() => {
                closeDBModal();
            }, 1200);
        } else {
            alertBox.className = 'modal-alert error';
            alertBox.textContent = `❌ ${data.detail || data.message || 'Connection failed.'}`;
            updateDBStatusUI(false, null);
        }
    } catch (err) {
        alertBox.className = 'modal-alert error';
        alertBox.textContent = '❌ Network error while attempting to connect to server.';
        updateDBStatusUI(false, null);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Connect';
    }
}

async function handleDBDisconnect() {
    if (!confirm('Are you sure you want to disconnect from the Oracle Database?')) {
        return;
    }

    const alertBox = document.getElementById('db-modal-alert');
    try {
        const res = await fetch('/api/db/disconnect', { method: 'POST' });
        const data = await res.json();

        updateDBStatusUI(false, null);
        if (alertBox) {
            alertBox.style.display = 'block';
            alertBox.className = 'modal-alert info';
            alertBox.textContent = 'Database disconnected.';
        }
    } catch (err) {
        alert('Error disconnecting database.');
    }
}

// Global window assignments so inline onclick handlers never fail
window.openDBModal = openDBModal;
window.closeDBModal = closeDBModal;
window.handleDBConnect = handleDBConnect;
window.handleDBDisconnect = handleDBDisconnect;

// =============================================================================
// FINALIZE IMPORTED DATA (BRANCH ID & SL_NO SEQUENTIAL UPDATE)
// =============================================================================

let pendingFinalizeTable = null;

function openFinalizeModal() {
    if (!isDBConnected()) {
        alert("Database Connection Required\n\nPlease connect to the Oracle database before finalizing imported data.");
        openDBModal();
        return;
    }

    const alertBox = document.getElementById('finalize-modal-alert');
    if (alertBox) alertBox.style.display = 'none';

    const modal = document.getElementById('finalize-modal-overlay');
    if (modal) modal.style.display = 'flex';
}

function closeFinalizeModal() {
    const modal = document.getElementById('finalize-modal-overlay');
    if (modal) modal.style.display = 'none';
    pendingFinalizeTable = null;
}

async function handleFinalizeSelect(event) {
    if (event) event.preventDefault();

    if (!isDBConnected()) {
        alert("Database Connection Required\n\nPlease connect to the Oracle database before finalizing imported data.");
        closeFinalizeModal();
        openDBModal();
        return;
    }

    const selectEl = document.getElementById('finalize-table-select');
    const tableName = selectEl ? selectEl.value : '';

    if (!tableName) {
        alert("Please select a table from the list.");
        return;
    }

    const alertBox = document.getElementById('finalize-modal-alert');
    const okBtn = document.getElementById('finalize-ok-btn');

    alertBox.style.display = 'block';
    alertBox.className = 'modal-alert info';
    alertBox.textContent = `⏳ Checking table '${tableName.toUpperCase()}'...`;
    okBtn.disabled = true;

    try {
        const res = await fetch('/api/finalize/check', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ table_name: tableName })
        });
        const data = await res.json();

        if (!res.ok) {
            alertBox.className = 'modal-alert error';
            alertBox.textContent = `❌ ${data.detail || data.message || 'Validation failed.'}`;
            okBtn.disabled = false;
            return;
        }

        pendingFinalizeTable = tableName;
        closeFinalizeModal();

        if (data.status === 'no_data') {
            alert(`No Data Found\n\nThe selected table '${tableName.toUpperCase()}' does not contain any records to finalize.`);
            return;
        }

        if (data.status === 'existing_data') {
            const confirmText = document.getElementById('finalize-confirm-text');
            if (confirmText) {
                confirmText.innerHTML = `
                    The selected table (<strong>${tableName.toUpperCase()}</strong>) already contains imported data.<br>
                    This data may already have been processed previously.<br><br>
                    <strong>Do you want to overwrite/update the existing data?</strong>
                `;
            }
            const confirmOverlay = document.getElementById('finalize-confirm-overlay');
            if (confirmOverlay) confirmOverlay.style.display = 'flex';
        } else {
            // Ready to finalize
            executeFinalize(tableName, false);
        }

    } catch (err) {
        alertBox.className = 'modal-alert error';
        alertBox.textContent = '❌ Network error while checking table status.';
    } finally {
        if (okBtn) okBtn.disabled = false;
    }
}

function cancelFinalizeOverwrite() {
    const confirmOverlay = document.getElementById('finalize-confirm-overlay');
    if (confirmOverlay) confirmOverlay.style.display = 'none';
    pendingFinalizeTable = null;
    alert("Operation Cancelled\n\nNo existing data was modified.");
}

function executeFinalizeOverwrite() {
    const confirmOverlay = document.getElementById('finalize-confirm-overlay');
    if (confirmOverlay) confirmOverlay.style.display = 'none';
    if (pendingFinalizeTable) {
        executeFinalize(pendingFinalizeTable, true);
    }
}

async function executeFinalize(tableName, confirmOverwrite) {
    const successOverlay = document.getElementById('finalize-success-overlay');

    try {
        const res = await fetch('/api/finalize/process', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ table_name: tableName, confirm_overwrite: confirmOverwrite })
        });
        const data = await res.json();

        if (!res.ok) {
            alert(`Operation Failed\n\n${data.detail || data.message || 'An error occurred during finalization.'}`);
            return;
        }

        // Fill completion popup
        document.getElementById('fin-res-table').textContent = (data.table_name || tableName).toUpperCase();
        document.getElementById('fin-res-total').textContent = (data.total_records || 0).toLocaleString();
        document.getElementById('fin-res-range').textContent = `${data.sl_min || 1} to ${data.sl_max || data.total_records || 0}`;

        if (successOverlay) successOverlay.style.display = 'flex';

    } catch (err) {
        alert("Operation Failed\n\nAn unexpected error occurred while finalizing the selected table.\n\nPlease check the application log or contact the system administrator.");
    } finally {
        pendingFinalizeTable = null;
    }
}

function closeFinalizeSuccessModal() {
    const successOverlay = document.getElementById('finalize-success-overlay');
    if (successOverlay) successOverlay.style.display = 'none';
}

window.openFinalizeModal = openFinalizeModal;
window.closeFinalizeModal = closeFinalizeModal;
window.handleFinalizeSelect = handleFinalizeSelect;
window.cancelFinalizeOverwrite = cancelFinalizeOverwrite;
window.executeFinalizeOverwrite = executeFinalizeOverwrite;
window.closeFinalizeSuccessModal = closeFinalizeSuccessModal;

// =============================================================================
// WEBSOCKET & PROGRESS MANAGEMENT
// =============================================================================

function openWS(jobId, key, filename, btn) {
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${proto}//${location.host}/ws/progress/${jobId}`);

    ws.onmessage = ({ data }) => {
        const d = JSON.parse(data);
        updateUI(key, d);

        if (d.status === 'completed' || d.status === 'failed') {
            ws.close();
            resetBtn(btn);
            showModal(filename, d);
            if (d.status === 'completed') {
                const config = getMappingByKey(key);
                if (config && config.table && typeof window.recordCompletedCSV === 'function') {
                    window.recordCompletedCSV(config.table);
                }
            }
            if (typeof window.syncWorkflowStatus === 'function') {
                window.syncWorkflowStatus();
            }
        }
    };

    ws.onerror = () => {
        const statusEl = document.getElementById(`status-${key}`);
        if (statusEl) statusEl.textContent = 'Connection error';
        resetBtn(btn);
    };
}

window.moduleInsertedRecordsMap = window.moduleInsertedRecordsMap || {};

function updateKPISummary() {
    let totalInserted = 0;
    Object.values(window.moduleInsertedRecordsMap).forEach(m => {
        totalInserted += (m.inserted || 0);
    });
    const totalRecEl = document.getElementById('kpi-total-records');
    if (totalRecEl) totalRecEl.textContent = totalInserted.toLocaleString();
}

function updateUI(key, d) {
    const statusMap = {
        processing: 'Processing…',
        completed: 'COMPLETED ✓',
        failed: 'FAILED ✗',
        waiting: 'Waiting'
    };

    const statusEl = document.getElementById(`status-${key}`);
    const percEl = document.getElementById(`perc-${key}`);
    const fillEl = document.getElementById(`fill-${key}`);
    const counterEl = document.getElementById(`counter-${key}`);

    const statInsertedEl = document.getElementById(`stat-inserted-${key}`);
    const statDupEl = document.getElementById(`stat-dup-${key}`);
    const statFailEl = document.getElementById(`stat-fail-${key}`);
    const cardEl = document.getElementById(`card-${key}`);

    if (statusEl) statusEl.textContent = statusMap[d.status] || d.status;
    if (percEl) percEl.textContent = `${d.percentage}%`;
    if (fillEl) fillEl.style.width = `${d.percentage}%`;
    if (counterEl) counterEl.textContent = `${(d.processed || 0).toLocaleString()} / ${(d.total || 0).toLocaleString()}`;

    if (statInsertedEl) statInsertedEl.textContent = (d.inserted || 0).toLocaleString();
    if (statDupEl) statDupEl.textContent = (d.duplicates || 0).toLocaleString();
    if (statFailEl) statFailEl.textContent = (d.failed || 0).toLocaleString();

    // Track dynamic record totals
    window.moduleInsertedRecordsMap[key] = { inserted: d.inserted || 0, failed: d.failed || 0 };
    updateKPISummary();

    if (d.status === 'completed') {
        setCardStatusBadge(key, 'COMPLETED ✓', 'badge-completed');
        if (cardEl) {
            cardEl.classList.remove('card-processing', 'card-error');
            cardEl.classList.add('card-completed');
        }
        if (typeof window.refreshErrorSummaryCount === 'function') {
            window.refreshErrorSummaryCount(true);
        }
    } else if (d.status === 'failed') {
        setCardStatusBadge(key, 'ERROR ✗', 'badge-error');
        if (cardEl) {
            cardEl.classList.remove('card-processing', 'card-completed');
            cardEl.classList.add('card-error');
        }
        if (typeof window.refreshErrorSummaryCount === 'function') {
            window.refreshErrorSummaryCount(true);
        }
    } else if (d.status === 'processing') {
        setCardStatusBadge(key, 'PROCESSING…', 'badge-processing');
        if (cardEl) {
            cardEl.classList.remove('card-completed', 'card-error');
            cardEl.classList.add('card-processing');
        }
    }
}

function resetBtn(btn) {
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="btn-icon">⚡</span> <span class="btn-text">Validate &amp; Import</span>';
    }
}

function showModal(filename, d) {
    const title = document.getElementById('modal-title');
    const content = document.getElementById('modal-content');
    const overlay = document.getElementById('modal-overlay');

    if (title) {
        title.textContent = d.status === 'failed' ? 'IMPORT FAILED' : 'IMPORT COMPLETED';
        title.style.color = d.status === 'failed' ? 'var(--error)' : 'var(--success)';
    }

    if (content) {
        content.innerHTML = `
            <table class="modal-table">
                <tr><td>File</td><td><strong style="word-break:break-all;overflow-wrap:anywhere;display:inline-block;max-width:280px;text-align:right;">${filename}</strong></td></tr>
                <tr><td>Total Records</td><td><strong>${(d.total || 0).toLocaleString()}</strong></td></tr>
                <tr><td>Successfully Inserted</td><td><strong style="color:var(--success)">${(d.inserted || 0).toLocaleString()}</strong></td></tr>
                <tr><td>Duplicates Skipped</td><td><strong>${(d.duplicates || 0).toLocaleString()}</strong></td></tr>
                <tr><td>Failed</td><td><strong style="color:${(d.failed || 0) > 0 ? 'var(--error)' : 'inherit'}">${(d.failed || 0).toLocaleString()}</strong></td></tr>
                <tr><td>Finalization Status</td><td><strong style="color:var(--success)">✓ Auto-Finalized (Branch ID &amp; Serial Generated)</strong></td></tr>
            </table>
            ${d.message ? `<p style="color:var(--error);margin-top:1rem;">${d.message}</p>` : ''}
        `;
    }

    if (overlay) overlay.style.display = 'flex';
}

function closeModal() {
    const overlay = document.getElementById('modal-overlay');
    if (overlay) overlay.style.display = 'none';
}

window.closeModal = closeModal;
