// =============================================================================
// CIB-DIVS Check Error Module Client Logic
// =============================================================================

let checkErrorColumns = [];
let checkErrorAllRows = [];
let checkErrorFilteredRows = [];

let currentPage = 1;
const pageSize = 50;

document.addEventListener('DOMContentLoaded', () => {
    // Perform initial check error data load if connected
    setTimeout(() => {
        if (typeof isDBConnected === 'function' && isDBConnected()) {
            loadCheckErrors();
        } else {
            showCheckErrorDisconnectedUI();
        }
    }, 400);
});

async function loadCheckErrors() {
    const btnRefresh = document.getElementById('btn-refresh-errors');
    const loadingState = document.getElementById('error-loading-state');
    const disconnectedState = document.getElementById('error-disconnected-state');
    const tableWrapper = document.getElementById('error-table-wrapper');
    const emptyState = document.getElementById('error-empty-state');
    const paginationBar = document.getElementById('error-pagination-bar');
    const totalCountEl = document.getElementById('error-total-count');

    if (btnRefresh) {
        btnRefresh.disabled = true;
        btnRefresh.textContent = '⏳ Checking errors...';
    }

    if (loadingState) loadingState.style.display = 'block';
    if (disconnectedState) disconnectedState.style.display = 'none';
    if (tableWrapper) tableWrapper.style.display = 'none';
    if (emptyState) emptyState.style.display = 'none';
    if (paginationBar) paginationBar.style.display = 'none';

    try {
        const res = await fetch('/api/check-error');
        const data = await res.json();

        if (!res.ok) {
            if (res.status === 400 && data.detail && data.detail.includes("Database Connection Required")) {
                showCheckErrorDisconnectedUI();
            } else {
                alert(`Error Check Failed\n\n${data.detail || 'Unable to execute CIB error checking procedure.'}`);
            }
            return;
        }

        checkErrorColumns = data.columns || [];
        checkErrorAllRows = data.rows || [];
        checkErrorFilteredRows = [...checkErrorAllRows];

        const totalNum = data.total || 0;
        if (totalCountEl) totalCountEl.textContent = totalNum.toLocaleString();

        const kpiErrEl = document.getElementById('kpi-total-errors');
        if (kpiErrEl) kpiErrEl.textContent = totalNum.toLocaleString();

        if (!checkErrorAllRows.length) {
            if (emptyState) emptyState.style.display = 'block';
        } else {
            currentPage = 1;
            renderErrorTableHead();
            renderErrorTablePage();
            if (tableWrapper) tableWrapper.style.display = 'block';
            if (paginationBar) paginationBar.style.display = 'flex';
        }

    } catch (err) {
        console.error("Check Error fetch exception:", err);
        alert("Network Error\n\nUnable to reach server to execute error check.");
    } finally {
        if (loadingState) loadingState.style.display = 'none';
        if (btnRefresh) {
            btnRefresh.disabled = false;
            btnRefresh.textContent = '🔄 Refresh Errors';
        }
        if (typeof window.checkSchedulerSummaryAccess === 'function') {
            window.checkSchedulerSummaryAccess();
        }
    }
}

async function refreshErrorSummaryCount(silent = false) {
    if (typeof isDBConnected === 'function' && !isDBConnected()) {
        const kpiErrEl = document.getElementById('kpi-total-errors');
        const totalCountEl = document.getElementById('error-total-count');
        if (kpiErrEl) kpiErrEl.textContent = '0';
        if (totalCountEl) totalCountEl.textContent = '0';
        return;
    }
    if (!silent) {
        return loadCheckErrors();
    }
    try {
        const res = await fetch('/api/check-error');
        if (!res.ok) return;
        const data = await res.json();
        const totalNum = data.total || 0;
        const totalCountEl = document.getElementById('error-total-count');
        const kpiErrEl = document.getElementById('kpi-total-errors');
        if (totalCountEl) totalCountEl.textContent = totalNum.toLocaleString();
        if (kpiErrEl) kpiErrEl.textContent = totalNum.toLocaleString();
        checkErrorColumns = data.columns || [];
        checkErrorAllRows = data.rows || [];
        checkErrorFilteredRows = [...checkErrorAllRows];
    } catch (err) {
        console.warn("Silent error summary refresh failed:", err);
    }
}

function showCheckErrorDisconnectedUI() {
    const disconnectedState = document.getElementById('error-disconnected-state');
    const tableWrapper = document.getElementById('error-table-wrapper');
    const loadingState = document.getElementById('error-loading-state');
    const emptyState = document.getElementById('error-empty-state');
    const paginationBar = document.getElementById('error-pagination-bar');
    const totalCountEl = document.getElementById('error-total-count');
    const kpiErrEl = document.getElementById('kpi-total-errors');

    if (disconnectedState) disconnectedState.style.display = 'block';
    if (tableWrapper) tableWrapper.style.display = 'none';
    if (loadingState) loadingState.style.display = 'none';
    if (emptyState) emptyState.style.display = 'none';
    if (paginationBar) paginationBar.style.display = 'none';
    if (totalCountEl) totalCountEl.textContent = '0';
    if (kpiErrEl) kpiErrEl.textContent = '0';
}

function formatHSCode(val) {
    if (val === null || val === undefined) return '';
    let str = String(val).trim();
    if (/^\d+$/.test(str) && str.length < 8) {
        return str.padStart(8, '0');
    }
    return str;
}

function renderErrorTableHead() {
    const thead = document.getElementById('error-table-head');
    if (!thead) return;

    // Allocate 5% for SL No., 8% for Action button, and divide remaining 87% among dynamic columns
    let html = '<tr><th style="width:5%;min-width:45px;text-align:center;">SL No.</th>';

    const numCols = checkErrorColumns.length;
    if (numCols > 0) {
        let totalWeight = 0;
        const colWeights = checkErrorColumns.map(col => {
            const c = col.toUpperCase();
            if (c.includes('REMARKS') || c.includes('MESSAGE')) return 36;
            if (c.includes('REFERENCE_NUMBER') || c.includes('REFERENCE_NO') || c.includes('REF_NO')) return 20;
            if (c.includes('REFERENCE_COLUMN')) return 16;
            if (c.includes('TABLE_NAME') || c.includes('TABLE')) return 15;
            return 15;
        });
        totalWeight = colWeights.reduce((a, b) => a + b, 0) || 1;
        const availablePct = 87;

        checkErrorColumns.forEach((col, idx) => {
            const pct = Math.max(8, Math.round((colWeights[idx] / totalWeight) * availablePct));
            html += `<th style="width:${pct}%;" title="${escapeHTML(col)}">${escapeHTML(col)}</th>`;
        });
    }

    html += '<th style="width:8%;min-width:70px;text-align:center;">Action</th></tr>';
    thead.innerHTML = html;
}

function renderErrorTablePage() {
    const tbody = document.getElementById('error-table-body');
    const paginationInfo = document.getElementById('pagination-info');
    const pageIndicator = document.getElementById('pagination-page-indicator');
    const btnPrev = document.getElementById('btn-page-prev');
    const btnNext = document.getElementById('btn-page-next');

    if (!tbody) return;

    const totalRows = checkErrorFilteredRows.length;
    const totalPages = Math.ceil(totalRows / pageSize) || 1;

    if (currentPage > totalPages) currentPage = totalPages;
    if (currentPage < 1) currentPage = 1;

    const startIdx = (currentPage - 1) * pageSize;
    const endIdx = Math.min(startIdx + pageSize, totalRows);
    const pageRows = checkErrorFilteredRows.slice(startIdx, endIdx);

    let html = '';
    pageRows.forEach((row, index) => {
        const globalRowNumber = startIdx + index + 1;
        html += `<tr>`;
        html += `<td style="text-align:center;font-weight:400;color:#60a5fa;font-size:0.78rem;">${globalRowNumber}</td>`;

        const refColVal = String(row['REFERENCE_COLUMN'] || row['reference_column'] || '').toUpperCase();
        const isRefHSCode = refColVal.includes('HS_CODE') || refColVal.includes('HSCODE');
        
        checkErrorColumns.forEach(col => {
            let val = row[col] !== undefined ? String(row[col]) : '';
            const colUpper = col.toUpperCase();

            if (colUpper.includes('HS_CODE') || colUpper.includes('HSCODE') || (isRefHSCode && (colUpper.includes('REF') || colUpper.includes('NUMBER')))) {
                val = formatHSCode(val);
            }

            if (colUpper.includes('REMARKS') || colUpper.includes('MESSAGE')) {
                // Also pad 1-7 digit HS_CODE in remarks text if present
                val = val.replace(/\b(HS_?CODE\s*[:=\-]?\s*)(\d{1,7})\b/gi, (m, p1, p2) => p1 + p2.padStart(8, '0'));
                html += `<td><div class="cell-long-text" title="${escapeHTML(val)}">${escapeHTML(val)}</div></td>`;
            } else if (colUpper === 'TABLE_NAME' || colUpper.includes('TABLE')) {
                html += `<td><code class="cell-code-purple" title="${escapeHTML(val)}">${escapeHTML(val)}</code></td>`;
            } else if (colUpper === 'REFERENCE_COLUMN') {
                html += `<td><span class="cell-ref-col" title="${escapeHTML(val)}">${escapeHTML(val)}</span></td>`;
            } else if (colUpper.includes('CODE') || colUpper.includes('REF') || colUpper.includes('NUMBER')) {
                html += `<td><span class="cell-ref-num" title="${escapeHTML(val)}">${escapeHTML(val)}</span></td>`;
            } else {
                html += `<td><div class="cell-long-text" title="${escapeHTML(val)}">${escapeHTML(val)}</div></td>`;
            }
        });

        // Edit button passing stringified record JSON
        const recordJSON = escapeHTML(JSON.stringify(row));
        html += `<td style="text-align:center;"><button type="button" class="btn-edit-row" onclick="openEditModal(${recordJSON})" title="Edit Error Record">✏️ Edit</button></td>`;
        html += `</tr>`;
    });

    tbody.innerHTML = html;

    if (paginationInfo) {
        paginationInfo.textContent = `Showing ${totalRows === 0 ? 0 : startIdx + 1}–${endIdx} of ${totalRows.toLocaleString()} error records`;
    }
    if (pageIndicator) {
        pageIndicator.textContent = `Page ${currentPage} of ${totalPages}`;
    }
    if (btnPrev) btnPrev.disabled = currentPage <= 1;
    if (btnNext) btnNext.disabled = currentPage >= totalPages;
}

function changePage(delta) {
    currentPage += delta;
    renderErrorTablePage();
}

function handleSearchInput() {
    const input = document.getElementById('error-search-input');
    const query = input ? input.value.trim().toLowerCase() : '';

    if (!query) {
        checkErrorFilteredRows = [...checkErrorAllRows];
    } else {
        checkErrorFilteredRows = checkErrorAllRows.filter(row => {
            return Object.values(row).some(val => 
                String(val).toLowerCase().includes(query)
            );
        });
    }

    currentPage = 1;
    const totalCountEl = document.getElementById('error-total-count');
    if (totalCountEl) totalCountEl.textContent = checkErrorFilteredRows.length.toLocaleString();

    renderErrorTablePage();
}

function openEditModal(record) {
    const overlay = document.getElementById('edit-placeholder-modal-overlay');
    const inputTable = document.getElementById('edit-table-name');
    const inputRef = document.getElementById('edit-reference-no');
    const inputRemarks = document.getElementById('edit-remarks');
    const inputActualRef = document.getElementById('edit-actual-reference');
    const alertBox = document.getElementById('edit-modal-alert');
    const btnSubmit = document.getElementById('btn-submit-update');

    if (!overlay) return;

    // Extract values from selected error row record automatically
    const tableName = record.TABLE_NAME || record.table_name || '';
    let referenceNo = record.REFERENCE_NUMBER || record.reference_number || record.REFERENCE_NO || '';
    const remarks = record.REMARKS || record.remarks || '';
    const refCol = String(record.REFERENCE_COLUMN || record.reference_column || '').toUpperCase();

    if (refCol.includes('HS_CODE') || refCol.includes('HSCODE') || remarks.toUpperCase().includes('HS_CODE') || remarks.toUpperCase().includes('HSCODE')) {
        referenceNo = formatHSCode(referenceNo);
    }

    if (inputTable) inputTable.value = tableName;
    if (inputRef) inputRef.value = referenceNo;
    if (inputRemarks) inputRemarks.value = remarks;
    if (inputActualRef) inputActualRef.value = '';

    if (alertBox) {
        alertBox.style.display = 'none';
        alertBox.className = 'modal-alert';
        alertBox.textContent = '';
    }

    if (btnSubmit) {
        btnSubmit.disabled = false;
        btnSubmit.textContent = 'Update';
    }

    overlay.style.display = 'flex';
    setTimeout(() => {
        if (inputActualRef) inputActualRef.focus();
    }, 100);
}

function closeEditModal() {
    const overlay = document.getElementById('edit-placeholder-modal-overlay');
    if (overlay) overlay.style.display = 'none';
}

async function handleUpdateErrorSubmit(event) {
    if (event) event.preventDefault();

    const inputTable = document.getElementById('edit-table-name');
    const inputRef = document.getElementById('edit-reference-no');
    const inputRemarks = document.getElementById('edit-remarks');
    const inputActualRef = document.getElementById('edit-actual-reference');
    const alertBox = document.getElementById('edit-modal-alert');
    const btnSubmit = document.getElementById('btn-submit-update');

    const tableName = inputTable ? inputTable.value.trim() : '';
    const referenceNo = inputRef ? inputRef.value.trim() : '';
    const remarks = inputRemarks ? inputRemarks.value.trim() : '';
    const actualRef = inputActualRef ? inputActualRef.value.trim() : '';

    // 1. Verify DB Connection active
    if (typeof isDBConnected === 'function' && !isDBConnected()) {
        showModalAlert(alertBox, 'error', 'Database Connection Required: Please connect to the Oracle database before updating the error record.');
        return;
    }

    // 2. Validate input fields
    if (!tableName || !referenceNo || !remarks) {
        showModalAlert(alertBox, 'error', 'Invalid Error Record Selected: Missing required record identifier fields.');
        return;
    }

    if (!actualRef) {
        showModalAlert(alertBox, 'error', 'Actual Reference Required: Please enter the Actual Reference before updating.');
        if (inputActualRef) inputActualRef.focus();
        return;
    }

    // 3. Lock button state during processing
    if (btnSubmit) {
        btnSubmit.disabled = true;
        btnSubmit.textContent = 'Updating...';
    }
    if (alertBox) alertBox.style.display = 'none';

    try {
        const res = await fetch('/api/check-error/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                table_name: tableName,
                reference_no: referenceNo,
                remarks: remarks,
                actual_reference: actualRef
            })
        });

        const data = await res.json();

        if (!res.ok) {
            const errDetail = data.detail || 'Update Failed: The error record could not be updated. No changes were committed.';
            showModalAlert(alertBox, 'error', errDetail);
            if (btnSubmit) {
                btnSubmit.disabled = false;
                btnSubmit.textContent = 'Update';
            }
            return;
        }

        // Close edit modal
        closeEditModal();

        // Display success notice to user
        alert("Update Completed Successfully\n\nThe error record has been updated.\n\nPlease click Refresh Errors to view the latest error list.");

        // Automatically trigger error list refresh
        loadCheckErrors();

    } catch (err) {
        console.error("Update error exception:", err);
        showModalAlert(alertBox, 'error', 'Update Failed: Network error while submitting update request.');
        if (btnSubmit) {
            btnSubmit.disabled = false;
            btnSubmit.textContent = 'Update';
        }
    }
}

function showModalAlert(element, type, message) {
    if (!element) return;
    element.className = `modal-alert ${type}`;
    element.textContent = message;
    element.style.display = 'block';
}

function escapeHTML(str) {
    if (str === null || str === undefined) return '';
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

window.loadCheckErrors = loadCheckErrors;
window.refreshErrorSummaryCount = refreshErrorSummaryCount;
window.changePage = changePage;
window.handleSearchInput = handleSearchInput;
window.openEditModal = openEditModal;
window.closeEditModal = closeEditModal;
window.handleUpdateErrorSubmit = handleUpdateErrorSubmit;
