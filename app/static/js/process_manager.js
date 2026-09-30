// =============================================================================
// CIB-DIVS Scheduler & Summary Process Manager Client Logic
// =============================================================================

document.addEventListener('DOMContentLoaded', () => {
    // Initial error status check to set dropdown visibility
    setTimeout(() => {
        checkSchedulerSummaryAccess();
    }, 500);

    // Close dropdown menu when clicking outside
    document.addEventListener('click', (e) => {
        const dropdowns = document.querySelectorAll('.nav-scheduler-summary-dropdown');
        dropdowns.forEach(dropdown => {
            if (!dropdown.contains(e.target)) {
                const menu = dropdown.querySelector('.dropdown-menu');
                if (menu) menu.classList.remove('show');
            }
        });
    });
});

function toggleSchedulerSummaryDropdown(event) {
    if (event) {
        event.stopPropagation();
        event.preventDefault();
    }

    // Auto-expand sidebar if it is currently collapsed
    const layout = document.querySelector('.app-layout');
    if (layout && layout.classList.contains('sidebar-collapsed')) {
        layout.classList.remove('sidebar-collapsed');
    }

    const btn = event ? event.currentTarget : document.querySelector('#nav-tab-scheduler-summary');
    const parentDropdown = btn ? btn.closest('.nav-scheduler-summary-dropdown') : document.querySelector('.nav-scheduler-summary-dropdown');

    // Check if button is disabled due to database status or un-cleared error log
    if (btn && btn.classList.contains('disabled')) {
        const reason = btn.getAttribute('data-disabled-reason');
        if (reason === 'db') {
            alert("Database Connection Required\n\nPlease connect to the Oracle database before continuing.");
        } else {
            const errCount = btn.getAttribute('data-error-count');
            const errSuffix = (errCount && parseInt(errCount, 10) > 0) ? ` (Total Errors: ${errCount})` : '';
            alert(`Operation Not Allowed${errSuffix}\n\nPlease clear error log before running Scheduler or Summary.`);
        }
        return;
    }

    if (parentDropdown) {
        const menu = parentDropdown.querySelector('.dropdown-menu');
        if (menu) menu.classList.toggle('show');
    }
}

function handleSchedulerItemClick(event) {
    if (event) event.stopPropagation();
    const menus = document.querySelectorAll('.dropdown-menu');
    menus.forEach(m => m.classList.remove('show'));
    openSchedulerModal();
}

function handleSummaryItemClick(event) {
    if (event) event.stopPropagation();
    const menus = document.querySelectorAll('.dropdown-menu');
    menus.forEach(m => m.classList.remove('show'));
    openSummaryModal();
}

function handleReconciliationItemClick(event) {
    if (event) event.stopPropagation();
    const menus = document.querySelectorAll('.dropdown-menu');
    menus.forEach(m => m.classList.remove('show'));
    openReconciliationModal();
}

// =============================================================================
// REAL-TIME SEQUENTIAL WORKFLOW LOCKING & SYNCHRONIZATION ENGINE
// =============================================================================

window.getCompletedCSVs = function() {
    try {
        const raw = sessionStorage.getItem('cib_completed_csvs');
        return raw ? JSON.parse(raw) : [];
    } catch (e) {
        return [];
    }
};

window.recordCompletedCSV = function(targetTable) {
    if (!targetTable) return;
    const current = window.getCompletedCSVs();
    const tbl = targetTable.toLowerCase().trim();
    if (!current.includes(tbl)) {
        current.push(tbl);
        sessionStorage.setItem('cib_completed_csvs', JSON.stringify(current));
    }
    syncWorkflowStatus();
};

window.workflowState = window.workflowState || {
    connected: false,
    all_6_completed: false,
    completed_tables_count: 0,
    completed_tables: [],
    error_count: 0,
    process_monitoring_completed: false,
    unlocked: {
        upload_validation: true,
        error_summary: false,
        process_monitoring: false,
        download_reports: true
    }
};

/**
 * Super-fast UI update for both Sidebar Buttons & Dashboard Cards (0ms execution)
 */
function renderWorkflowUI(unlocked) {
    const state = unlocked || (window.workflowState && window.workflowState.unlocked) || {};

    // 1. Upload & Validation (Always Enabled)
    setWorkflowItemState('#nav-tab-validation', true);
    setWorkflowItemState('#card-upload-validation', true);

    // 2. Activity & Upload Logs (Always Enabled)
    setWorkflowItemState('#nav-tab-logs', true);
    setWorkflowItemState('#card-logs', true);

    // 3. Download Reports (Always Enabled per user directive)
    setWorkflowItemState('#nav-tab-download-report', true);
    setWorkflowItemState('#card-download-reports', true);
    setWorkflowItemState('#wf-card-step-4', true);

    // Check session CSV completion count vs required 6 tables
    const sessionCSVs = window.getCompletedCSVs();
    const REQUIRED_6 = ["a1_o1", "arv", "e2_p2", "c_form", "e3_p3", "bbreturn_manual_tm"];
    const sessionAll6Done = REQUIRED_6.every(t => sessionCSVs.includes(t));

    // 4. Error Summary: Always unlocked to allow inspecting errors or verifying clean status
    const errSummaryUnlocked = true;
    setWorkflowItemState('#nav-tab-check-error', true);
    setWorkflowItemState('#card-check-error', true);
    setWorkflowItemState('#wf-card-step-2', true);

    // 5. Process Monitoring: Unlocked when Error Summary is clean (error count == 0)
    const errCount = (window.workflowState && window.workflowState.error_count) || 0;
    const pmUnlocked = (errCount === 0) || Boolean(state.process_monitoring);
    const pmMsg = errCount > 0 
        ? `Step Locked: CIB validation errors exist (Total: ${errCount}). Please resolve all errors in Error Summary before running Process Monitoring.`
        : '';
    setWorkflowItemState('#nav-tab-scheduler-summary', pmUnlocked, pmMsg);
    setWorkflowItemState('#card-process-monitoring', pmUnlocked, pmMsg);
    setWorkflowItemState('#wf-card-step-3', pmUnlocked, pmMsg);

    // 6. Update Real-time Workflow Carousel Animation Panel
    updateWorkflowCarouselUI();
}

/**
 * Real-time Workflow Carousel Sync & Animation Handler
 */
function updateWorkflowCarouselUI() {
    const track = document.getElementById('workflow-carousel-track');
    const orbitStage = document.getElementById('circular-orbit-stage');
    if (!track && !orbitStage) return;

    const sessionCSVs = window.getCompletedCSVs();
    const REQUIRED_6 = ["a1_o1", "arv", "e2_p2", "c_form", "e3_p3", "bbreturn_manual_tm"];
    const sessionAll6Done = REQUIRED_6.every(t => sessionCSVs.includes(t));
    const isStep1Done = Boolean(sessionAll6Done || (window.workflowState && window.workflowState.all_6_completed));

    const errCount = (window.workflowState && window.workflowState.error_count) || 0;
    const isStep2Done = errCount === 0;

    const pmDone = Boolean(window.workflowState && window.workflowState.process_monitoring_completed);
    const isStep3Done = isStep2Done && pmDone;

    // Determine current active focus step (1 to 5)
    let activeStep = 1;
    if (isStep1Done && errCount > 0) {
        activeStep = 2; // Error Summary focus
    } else if (isStep1Done && errCount === 0 && !pmDone) {
        activeStep = 3; // Process Monitoring focus
    } else if (pmDone) {
        activeStep = 4; // Download Reports focus
    }

    // Step 1: Upload & Validation
    setCarouselCardState(1, isStep1Done ? 'completed' : 'active', isStep1Done ? '✓ Completed' : '● Active');

    // Step 2: Error Summary (Never dimmed when clean; green completed badge when 0 errors)
    if (errCount > 0) {
        setCarouselCardState(2, 'warning', `⚠️ ${errCount} Errors`);
    } else {
        setCarouselCardState(2, 'completed', '✓ 0 Errors (Clean)');
    }

    // Step 3: Process Monitoring
    if (errCount > 0) {
        setCarouselCardState(3, 'locked', '🔒 Resolve Errors');
    } else if (!pmDone) {
        setCarouselCardState(3, 'active', '● Ready');
    } else {
        setCarouselCardState(3, 'completed', '✓ Completed');
    }

    // Step 4: Download Reports (Always enabled/unlocked)
    setCarouselCardState(4, pmDone ? 'completed' : 'active', pmDone ? '✓ Ready' : '● Unlocked');

    // Step 5: Activity Logs (Always active)
    setCarouselCardState(5, 'active', '● Ready');

    // Highlight active focus card
    for (let s = 1; s <= 5; s++) {
        const card = document.getElementById(`wf-card-step-${s}`);
        if (card) {
            if (s === activeStep) {
                card.classList.add('active');
            } else if (!card.classList.contains('completed') && !card.classList.contains('locked')) {
                card.classList.remove('active');
            }
        }
    }

    // Update connector arrows
    updateConnectorArrow(1, isStep1Done);
    updateConnectorArrow(2, isStep2Done);
    updateConnectorArrow(3, isStep3Done);
    updateConnectorArrow(4, true);

    // Update step indicator
    const stepIndicator = document.getElementById('workflow-step-indicator');
    if (stepIndicator) {
        stepIndicator.textContent = `Step ${activeStep} of 5`;
    }

    // Auto focus scroll / rotate circular wheel to active step if changed
    if (window.lastActiveWorkflowStep !== activeStep) {
        window.lastActiveWorkflowStep = activeStep;
        autoFocusActiveWorkflowStep(activeStep);
    }
}

let currentWheelRotation = 0;
let isOrbitAutoPlay = true;
let orbitIntervalTimer = null;

function autoFocusActiveWorkflowStep(stepNum) {
    window.currentActiveStepIndex = stepNum;
    
    // Calculate target angle to bring active step to top position (0 deg)
    const targetDeg = - (stepNum - 1) * 72;
    
    let diff = (targetDeg - currentWheelRotation) % 360;
    if (diff > 180) diff -= 360;
    if (diff < -180) diff += 360;

    currentWheelRotation += diff;
    applyWheelRotation();
}

function rotateCircularWorkflow(direction) {
    // Stop continuous drift temporarily on manual navigation
    currentWheelRotation += direction * 72;
    applyWheelRotation();
}

function applyWheelRotation() {
    const wheel = document.getElementById('circular-orbit-wheel');
    if (!wheel) return;

    wheel.style.setProperty('--wheel-rotation', `${currentWheelRotation}deg`);

    // Calculate focused step index (1 to 5)
    let normalized = ((-currentWheelRotation % 360) + 360) % 360;
    let stepIndex = Math.round(normalized / 72) + 1;
    if (stepIndex > 5) stepIndex = 1;

    const stepIndicator = document.getElementById('workflow-step-indicator');
    if (stepIndicator) {
        stepIndicator.textContent = `Step ${stepIndex} of 5`;
    }

    const hubStatus = document.getElementById('hub-status-text');
    if (hubStatus) {
        const stepNames = ["Upload & Validation", "Error Summary", "Process Monitoring", "Download Reports", "Activity Logs"];
        hubStatus.textContent = `Focus: ${stepNames[stepIndex - 1]}`;
    }
}

function toggleOrbitAutoRotate() {
    isOrbitAutoPlay = !isOrbitAutoPlay;
    const btn = document.getElementById('wf-orbit-toggle');
    if (isOrbitAutoPlay) {
        if (btn) btn.textContent = '⏸';
        startOrbitSlowRotation();
    } else {
        if (btn) btn.textContent = '▶';
        stopOrbitSlowRotation();
    }
}

function startOrbitSlowRotation() {
    if (orbitIntervalTimer) clearInterval(orbitIntervalTimer);
    orbitIntervalTimer = setInterval(() => {
        if (!isOrbitAutoPlay) return;
        // Gentle continuous circular drift (0.35deg per interval)
        currentWheelRotation -= 0.35;
        const wheel = document.getElementById('circular-orbit-wheel');
        if (wheel) {
            wheel.style.setProperty('--wheel-rotation', `${currentWheelRotation}deg`);
        }
    }, 100);
}

function stopOrbitSlowRotation() {
    if (orbitIntervalTimer) {
        clearInterval(orbitIntervalTimer);
        orbitIntervalTimer = null;
    }
}

window.rotateCircularWorkflow = rotateCircularWorkflow;
window.toggleOrbitAutoRotate = toggleOrbitAutoRotate;
window.autoFocusActiveWorkflowStep = autoFocusActiveWorkflowStep;

function handleWorkflowCardClick(stepKey) {
    if (stepKey === 'upload_validation') {
        if (typeof showValidationView === 'function') showValidationView();
    } else if (stepKey === 'error_summary') {
        if (typeof validateWorkflowStep === 'function' && !validateWorkflowStep('error_summary')) {
            return;
        }
        if (typeof showCheckErrorView === 'function') {
            showCheckErrorView(window.event);
        }
    } else if (stepKey === 'process_monitoring') {
        if (typeof validateWorkflowStep === 'function' && !validateWorkflowStep('process_monitoring')) {
            return;
        }
        if (typeof openProcessMonitoringModal === 'function') {
            openProcessMonitoringModal();
        }
    } else if (stepKey === 'download_reports') {
        if (typeof validateWorkflowStep === 'function' && !validateWorkflowStep('download_reports')) {
            return;
        }
        if (typeof openReportModal === 'function') {
            openReportModal();
        }
    } else if (stepKey === 'activity_logs') {
        window.location.href = '/logs';
    }
}

window.moveWorkflowCarousel = moveWorkflowCarousel;
window.handleWorkflowCardClick = handleWorkflowCardClick;
window.updateWorkflowCarouselUI = updateWorkflowCarouselUI;

/**
 * Helper to toggle disabled class, opacity, cursor & pointer-events on element matches
 */
function setWorkflowItemState(selector, enabled, disabledReason) {
    const elements = document.querySelectorAll(selector);
    elements.forEach(el => {
        if (enabled) {
            el.classList.remove('disabled');
            el.removeAttribute('data-disabled-reason');
            el.style.opacity = '1';
            el.style.pointerEvents = 'auto';
            el.style.cursor = 'pointer';
            el.style.filter = 'none';
        } else {
            el.classList.add('disabled');
            if (disabledReason) el.setAttribute('data-disabled-reason', disabledReason);
            el.style.opacity = '0.35';
            el.style.pointerEvents = 'auto';
            el.style.cursor = 'not-allowed';
            el.style.filter = 'grayscale(1) brightness(0.6)';
        }
    });
}

/**
 * Fetch real-time workflow status from backend and trigger immediate UI sync
 */
async function syncWorkflowStatus() {
    try {
        const res = await fetch('/api/workflow/status');
        if (!res.ok) return;
        const data = await res.json();
        if (data && data.success) {
            // Ensure download_reports is always true in client state as well
            if (data.unlocked) data.unlocked.download_reports = true;
            window.workflowState = data;

            // Sync DB process completion status for Reconciliation button visibility
            if (data.scheduler_completed) {
                sessionStorage.setItem('recon_scheduler_completed', 'true');
            }
            if (data.summary_completed) {
                sessionStorage.setItem('recon_summary_completed', 'true');
            }
            updateReconciliationVisibility();

            renderWorkflowUI(data.unlocked);
        }
    } catch (err) {
        console.warn("Workflow status sync error:", err);
    }
}

/**
 * Direct Access Validation Guard for Route Switchers / Modals
 */
function validateWorkflowStep(stepKey) {
    if (stepKey === 'download_reports' || stepKey === 'error_summary' || stepKey === 'upload_validation' || stepKey === 'activity_logs') {
        return true; // Always enabled steps
    }

    const errCount = (window.workflowState && window.workflowState.error_count) || 0;

    if (stepKey === 'process_monitoring' && errCount > 0) {
        alert(`Sequential Workflow Locked 🔒\n(Unresolved Errors: ${errCount})\n\nPlease resolve all validation errors in Error Summary before running Process Monitoring.`);
        return false;
    }

    return true;
}

async function checkSchedulerSummaryAccess() {
    await syncWorkflowStatus();
    return Boolean(window.workflowState && window.workflowState.unlocked && window.workflowState.unlocked.process_monitoring);
}

async function validateAccessOrAlert() {
    const allowed = validateWorkflowStep('process_monitoring');
    return allowed;
}

// -----------------------------------------------------------------------------
// SCHEDULER MODAL HANDLERS
// -----------------------------------------------------------------------------

async function openSchedulerModal() {
    const allowed = await validateAccessOrAlert();
    if (!allowed) return;

    const overlay = document.getElementById('scheduler-modal-overlay');
    const inputBranch = document.getElementById('scheduler-branch-input');
    const selectMonth = document.getElementById('scheduler-month-select');
    const inputYear = document.getElementById('scheduler-year-input');
    const alertBox = document.getElementById('scheduler-modal-alert');
    const btnRun = document.getElementById('btn-run-scheduler');

    if (!overlay) return;

    if (inputBranch) inputBranch.value = '';
    if (selectMonth) selectMonth.value = '';
    if (inputYear) inputYear.value = new Date().getFullYear();
    if (alertBox) alertBox.style.display = 'none';
    if (btnRun) {
        btnRun.disabled = false;
        btnRun.textContent = 'Run Scheduler';
    }

    overlay.style.display = 'flex';
}

function closeSchedulerModal() {
    const overlay = document.getElementById('scheduler-modal-overlay');
    if (overlay) overlay.style.display = 'none';
}

async function handleSchedulerSubmit(event) {
    if (event) event.preventDefault();

    const inputBranch = document.getElementById('scheduler-branch-input');
    const selectMonth = document.getElementById('scheduler-month-select');
    const inputYear = document.getElementById('scheduler-year-input');
    const alertBox = document.getElementById('scheduler-modal-alert');
    const btnRun = document.getElementById('btn-run-scheduler');

    const branchVal = inputBranch ? inputBranch.value.trim() : '';
    const selectedMonth = selectMonth ? selectMonth.value.trim() : '';
    const yearVal = inputYear ? inputYear.value.trim() : '';

    if (!selectedMonth) {
        showProcessAlert(alertBox, 'error', 'Month Required: Please select a month before continuing.');
        return;
    }

    if (!yearVal) {
        showProcessAlert(alertBox, 'error', 'Year Required: Please enter or select a year before continuing.');
        return;
    }

    if (typeof isDBConnected === 'function' && !isDBConnected()) {
        showProcessAlert(alertBox, 'error', 'Database Connection Required: Please connect to the Oracle database before continuing.');
        return;
    }

    // Lock button state & show loading indicator
    if (btnRun) {
        btnRun.disabled = true;
        btnRun.textContent = 'Running Scheduler... Please wait.';
    }
    if (alertBox) alertBox.style.display = 'none';

    try {
        const res = await fetch('/api/scheduler/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                branch_id: branchVal,
                month: selectedMonth,
                year: yearVal
            })
        });

        const data = await res.json();

        if (!res.ok) {
            const errDetail = data.detail || 'Process Failed: The requested scheduler process could not be completed.';
            // Mark scheduler as failed — reset reconciliation visibility
            setReconciliationCompleted('scheduler', false);
            showProcessAlert(alertBox, 'error', errDetail);
            if (btnRun) {
                btnRun.disabled = false;
                btnRun.textContent = 'Run Scheduler';
            }
            // Re-verify error status
            checkSchedulerSummaryAccess();
            return;
        }

        // Mark scheduler as completed and update reconciliation visibility
        setReconciliationCompleted('scheduler', true);

        closeSchedulerModal();
        showProcessSuccessModal(
            data.title || 'Scheduler Completed Successfully',
            data.branch || (branchVal || 'All Branches'),
            data.month || selectedMonth,
            data.year || yearVal,
            data.detail
        );

    } catch (err) {
        console.error("Scheduler run exception:", err);
        // Mark scheduler as failed and update reconciliation visibility
        setReconciliationCompleted('scheduler', false);
        showProcessAlert(alertBox, 'error', 'Operation Failed: Network error while executing scheduler.');
        if (btnRun) {
            btnRun.disabled = false;
            btnRun.textContent = 'Run Scheduler';
        }
    }
}

// -----------------------------------------------------------------------------
// SUMMARY MODAL HANDLERS
// -----------------------------------------------------------------------------

async function openSummaryModal() {
    const allowed = await validateAccessOrAlert();
    if (!allowed) return;

    const overlay = document.getElementById('summary-modal-overlay');
    const inputBranch = document.getElementById('summary-branch-input');
    const selectMonth = document.getElementById('summary-month-select');
    const inputYear = document.getElementById('summary-year-input');
    const alertBox = document.getElementById('summary-modal-alert');
    const btnRun = document.getElementById('btn-run-summary');

    if (!overlay) return;

    if (inputBranch) inputBranch.value = '';
    if (selectMonth) selectMonth.value = '';
    if (inputYear) inputYear.value = new Date().getFullYear();
    if (alertBox) alertBox.style.display = 'none';
    if (btnRun) {
        btnRun.disabled = false;
        btnRun.textContent = 'Run Summary';
    }

    overlay.style.display = 'flex';
}

function closeSummaryModal() {
    const overlay = document.getElementById('summary-modal-overlay');
    if (overlay) overlay.style.display = 'none';
}

async function handleSummarySubmit(event) {
    if (event) event.preventDefault();

    const inputBranch = document.getElementById('summary-branch-input');
    const selectMonth = document.getElementById('summary-month-select');
    const inputYear = document.getElementById('summary-year-input');
    const alertBox = document.getElementById('summary-modal-alert');
    const btnRun = document.getElementById('btn-run-summary');

    const branchVal = inputBranch ? inputBranch.value.trim() : '';
    const selectedMonth = selectMonth ? selectMonth.value.trim() : '';
    const yearVal = inputYear ? inputYear.value.trim() : '';

    if (!selectedMonth) {
        showProcessAlert(alertBox, 'error', 'Month Required: Please select a month before continuing.');
        return;
    }

    if (!yearVal) {
        showProcessAlert(alertBox, 'error', 'Year Required: Please enter or select a year before continuing.');
        return;
    }

    if (typeof isDBConnected === 'function' && !isDBConnected()) {
        showProcessAlert(alertBox, 'error', 'Database Connection Required: Please connect to the Oracle database before continuing.');
        return;
    }

    // Lock button state & show loading indicator
    if (btnRun) {
        btnRun.disabled = true;
        btnRun.textContent = 'Generating Summary... Please wait.';
    }
    if (alertBox) alertBox.style.display = 'none';

    try {
        const res = await fetch('/api/summary/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                branch_id: branchVal,
                month: selectedMonth,
                year: yearVal
            })
        });

        const data = await res.json();

        if (!res.ok) {
            const errDetail = data.detail || 'Process Failed: The requested summary process could not be completed.';
            // Mark summary as failed — reset reconciliation visibility
            setReconciliationCompleted('summary', false);
            showProcessAlert(alertBox, 'error', errDetail);
            if (btnRun) {
                btnRun.disabled = false;
                btnRun.textContent = 'Run Summary';
            }
            // Re-verify error status
            checkSchedulerSummaryAccess();
            return;
        }

        // Mark summary as completed and update reconciliation visibility
        setReconciliationCompleted('summary', true);

        closeSummaryModal();
        showProcessSuccessModal(
            data.title || 'Summary Completed Successfully',
            data.branch || (branchVal || 'All Branches'),
            data.month || selectedMonth,
            data.year || yearVal,
            data.detail
        );

    } catch (err) {
        console.error("Summary run exception:", err);
        // Mark summary as failed and update reconciliation visibility
        setReconciliationCompleted('summary', false);
        showProcessAlert(alertBox, 'error', 'Operation Failed: Network error while generating summary.');
        if (btnRun) {
            btnRun.disabled = false;
            btnRun.textContent = 'Run Summary';
        }
    }
}

// -----------------------------------------------------------------------------
// PROCESS SUCCESS MODAL
// -----------------------------------------------------------------------------

function showProcessSuccessModal(title, branch, month, year, detail) {
    const overlay = document.getElementById('process-success-modal-overlay');
    const elTitle = document.getElementById('process-success-title');
    const elBranch = document.getElementById('process-success-branch');
    const elMonth = document.getElementById('process-success-month');
    const elYear = document.getElementById('process-success-year');
    const elDetail = document.getElementById('process-success-detail');

    if (elTitle) elTitle.textContent = title;
    if (elBranch) elBranch.textContent = branch || 'All Branches';
    if (elMonth) elMonth.textContent = month;
    if (elYear) elYear.textContent = year;
    if (elDetail) elDetail.textContent = detail || 'The process has completed and changes have been committed successfully.';

    if (overlay) overlay.style.display = 'flex';
}

function closeProcessSuccessModal() {
    const overlay = document.getElementById('process-success-modal-overlay');
    if (overlay) overlay.style.display = 'none';
}

function showProcessAlert(element, type, message) {
    if (!element) return;
    element.className = `modal-alert ${type}`;
    element.textContent = message;
    element.style.display = 'block';
}

// -----------------------------------------------------------------------------
// DOWNLOAD REPORT MODAL HANDLERS
// -----------------------------------------------------------------------------

function handleReportItemClick(event) {
    if (event) event.stopPropagation();
    const menus = document.querySelectorAll('.dropdown-menu');
    menus.forEach(m => m.classList.remove('show'));
    openReportModal();
}

async function openReportModal() {
    if (typeof isDBConnected === 'function' && !isDBConnected()) {
        alert("Database Connection Required\n\nPlease connect to the Oracle database before downloading reports.");
        return;
    }

    const overlay = document.getElementById('download-report-modal-overlay');
    const inputBranch = document.getElementById('report-branch-input');
    const selectMonth = document.getElementById('report-month-select');
    const inputYear = document.getElementById('report-year-input');
    const selectSched = document.getElementById('report-schedule-name-select');
    const alertBox = document.getElementById('report-modal-alert');
    const btnRun = document.getElementById('btn-run-report');

    if (!overlay) return;

    if (inputBranch) inputBranch.value = '';
    if (selectMonth) selectMonth.value = '';
    if (inputYear) inputYear.value = new Date().getFullYear();
    if (selectSched) selectSched.value = '';
    if (alertBox) alertBox.style.display = 'none';
    if (btnRun) {
        btnRun.disabled = false;
        btnRun.textContent = 'Download Report';
    }

    overlay.style.display = 'flex';
}

function closeReportModal() {
    const overlay = document.getElementById('download-report-modal-overlay');
    if (overlay) overlay.style.display = 'none';
}

async function handleReportSubmit(event) {
    if (event) event.preventDefault();

    const inputBranch = document.getElementById('report-branch-input');
    const selectMonth = document.getElementById('report-month-select');
    const inputYear = document.getElementById('report-year-input');
    const selectSched = document.getElementById('report-schedule-name-select');
    const alertBox = document.getElementById('report-modal-alert');
    const btnRun = document.getElementById('btn-run-report');

    const branchVal = inputBranch ? inputBranch.value.trim() : '';
    const selectedMonth = selectMonth ? selectMonth.value.trim() : '';
    const yearVal = inputYear ? inputYear.value.trim() : '';
    const schedVal = selectSched ? selectSched.value.trim() : '';

    if (!selectedMonth) {
        showProcessAlert(alertBox, 'error', 'Month Required: Please select a month before continuing.');
        return;
    }

    if (!yearVal) {
        showProcessAlert(alertBox, 'error', 'Year Required: Please enter or select a year before continuing.');
        return;
    }

    if (!schedVal) {
        showProcessAlert(alertBox, 'error', 'Schedule Name Required: Please select a schedule name before continuing.');
        return;
    }

    if (typeof isDBConnected === 'function' && !isDBConnected()) {
        showProcessAlert(alertBox, 'error', 'Database Connection Required: Please connect to the Oracle database before continuing.');
        return;
    }

    // Lock button state & show loading indicator
    if (btnRun) {
        btnRun.disabled = true;
        btnRun.textContent = 'Generating Report... Please wait.';
    }
    if (alertBox) alertBox.style.display = 'none';

    try {
        const res = await fetch('/api/schedule-report/download', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                pbranch_id: branchVal,
                pmonth: selectedMonth,
                pyear: yearVal,
                pschedule_nm: schedVal
            })
        });

        if (!res.ok) {
            let errDetail = 'Process Failed: The requested report could not be generated.';
            try {
                const data = await res.json();
                if (data && data.detail) errDetail = data.detail;
            } catch (e) { }
            showProcessAlert(alertBox, 'error', errDetail);
            if (btnRun) {
                btnRun.disabled = false;
                btnRun.textContent = 'Download Report';
            }
            checkSchedulerSummaryAccess();
            return;
        }

        // Trigger file download in browser
        const blob = await res.blob();
        let filename = `${schedVal}_${yearVal}_${selectedMonth.padStart(2, '0')}.txt`;
        const disposition = res.headers.get('Content-Disposition');
        if (disposition && disposition.includes('filename=')) {
            const matches = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(disposition);
            if (matches != null && matches[1]) {
                filename = matches[1].replace(/['"]/g, '');
            }
        }

        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(downloadUrl);

        if (btnRun) {
            btnRun.disabled = false;
            btnRun.textContent = 'Download Report';
        }

        closeReportModal();

    } catch (err) {
        console.error("Report download exception:", err);
        showProcessAlert(alertBox, 'error', 'Operation Failed: Network error while downloading report.');
        if (btnRun) {
            btnRun.disabled = false;
            btnRun.textContent = 'Download Report';
        }
    }
}

function openProcessMonitoringModal() {
    const overlay = document.getElementById('process-monitoring-modal-overlay') || document.getElementById('automation-tools-modal-overlay');
    if (overlay) overlay.style.display = 'flex';
}

function closeProcessMonitoringModal() {
    const overlay = document.getElementById('process-monitoring-modal-overlay') || document.getElementById('automation-tools-modal-overlay');
    if (overlay) overlay.style.display = 'none';
}

function openAutomationToolsModal() {
    openProcessMonitoringModal();
}

function closeAutomationToolsModal() {
    closeProcessMonitoringModal();
}

window.openProcessMonitoringModal = openProcessMonitoringModal;
window.closeProcessMonitoringModal = closeProcessMonitoringModal;
window.openAutomationToolsModal = openAutomationToolsModal;
window.closeAutomationToolsModal = closeAutomationToolsModal;
window.checkSchedulerSummaryAccess = checkSchedulerSummaryAccess;
window.toggleSchedulerSummaryDropdown = toggleSchedulerSummaryDropdown;
window.handleSchedulerItemClick = handleSchedulerItemClick;
window.handleSummaryItemClick = handleSummaryItemClick;
window.handleReportItemClick = handleReportItemClick;
window.openSchedulerModal = openSchedulerModal;
window.closeSchedulerModal = closeSchedulerModal;
window.handleSchedulerSubmit = handleSchedulerSubmit;
window.openSummaryModal = openSummaryModal;
window.closeSummaryModal = closeSummaryModal;
window.handleSummarySubmit = handleSummarySubmit;
window.openReportModal = openReportModal;
window.closeReportModal = closeReportModal;
window.handleReportSubmit = handleReportSubmit;
window.closeProcessSuccessModal = closeProcessSuccessModal;
document.addEventListener('DOMContentLoaded', () => {
    syncWorkflowStatus();
    setInterval(syncWorkflowStatus, 3000);
    // Restore reconciliation visibility from sessionStorage on page load
    updateReconciliationVisibility();
});

// =============================================================================
// RECONCILIATION FEATURE — STATE MANAGEMENT & MODAL HANDLERS
// =============================================================================

/**
 * Read reconciliation completion state from sessionStorage or URL test flag.
 * Keys: recon_scheduler_completed, recon_summary_completed
 */
function getReconciliationState() {
    // Instant test mode via URL parameter ?test_recon=1 or sessionStorage flag
    try {
        const params = new URLSearchParams(window.location.search);
        if (params.get('test_recon') === '1' || params.get('test_recon') === 'true' || sessionStorage.getItem('test_recon') === 'true') {
            return {
                scheduler_completed: true,
                summary_completed: true
            };
        }
    } catch (e) {}

    return {
        scheduler_completed: sessionStorage.getItem('recon_scheduler_completed') === 'true',
        summary_completed:   sessionStorage.getItem('recon_summary_completed')   === 'true',
    };
}

/**
 * Set scheduler_completed or summary_completed in sessionStorage.
 * Immediately re-evaluates and updates UI visibility.
 * @param {'scheduler'|'summary'} process
 * @param {boolean} completed
 */
function setReconciliationCompleted(process, completed) {
    if (process === 'scheduler') {
        sessionStorage.setItem('recon_scheduler_completed', completed ? 'true' : 'false');
    } else if (process === 'summary') {
        sessionStorage.setItem('recon_summary_completed', completed ? 'true' : 'false');
    }
    updateReconciliationVisibility();
}

/**
 * Evaluates scheduler_completed && summary_completed and shows/hides
 * the Reconciliation button in both the sidebar dropdown and the
 * Process Monitoring modal. Uses CSS class 'recon-hidden' so that
 * display:none !important beats the collapsed-sidebar flex override.
 */
function updateReconciliationVisibility() {
    const state   = getReconciliationState();
    const visible = state.scheduler_completed && state.summary_completed;

    // 1. Sidebar dropdown item
    const navItem = document.getElementById('nav-reconciliation-item');
    if (navItem) {
        if (visible) {
            navItem.classList.remove('recon-hidden');
        } else {
            navItem.classList.add('recon-hidden');
        }
    }

    // 2. Process Monitoring modal button
    const btnModal = document.getElementById('btn-process-monitoring-reconciliation');
    if (btnModal) {
        if (visible) {
            btnModal.classList.remove('recon-hidden');
        } else {
            btnModal.classList.add('recon-hidden');
        }
    }
}

// -----------------------------------------------------------------------------
// RECONCILIATION PARAMETER MODAL
// -----------------------------------------------------------------------------

function openReconciliationModal() {
    // Close Process Monitoring modal if open (mirrors Scheduler/Summary pattern)
    closeProcessMonitoringModal();

    const overlay    = document.getElementById('reconciliation-modal-overlay');
    const selMonth   = document.getElementById('reconciliation-month-select');
    const inputYear  = document.getElementById('reconciliation-year-input');
    const alertBox   = document.getElementById('reconciliation-modal-alert');
    const btnRun     = document.getElementById('btn-run-reconciliation');

    if (!overlay) return;

    if (selMonth)  selMonth.value  = '';
    if (inputYear) inputYear.value = new Date().getFullYear();
    if (alertBox)  alertBox.style.display = 'none';
    if (btnRun) {
        btnRun.disabled  = false;
        btnRun.textContent = 'Run Reconciliation';
    }

    overlay.style.display = 'flex';
}

function closeReconciliationModal() {
    const overlay = document.getElementById('reconciliation-modal-overlay');
    if (overlay) overlay.style.display = 'none';
}

async function handleReconciliationSubmit(event) {
    if (event) event.preventDefault();

    const selMonth  = document.getElementById('reconciliation-month-select');
    const inputYear = document.getElementById('reconciliation-year-input');
    const alertBox  = document.getElementById('reconciliation-modal-alert');
    const btnRun    = document.getElementById('btn-run-reconciliation');

    const selectedMonth = selMonth  ? selMonth.value.trim()  : '';
    const yearVal       = inputYear ? inputYear.value.trim() : '';

    // Client-side validation
    if (!selectedMonth) {
        showProcessAlert(alertBox, 'error', 'Month Required: Please select a month before continuing.');
        return;
    }
    if (!yearVal) {
        showProcessAlert(alertBox, 'error', 'Year Required: Please enter or select a year before continuing.');
        return;
    }
    if (typeof isDBConnected === 'function' && !isDBConnected()) {
        showProcessAlert(alertBox, 'error', 'Database Connection Required: Please connect to the Oracle database before continuing.');
        return;
    }

    // Lock button & show loading state
    if (btnRun) {
        btnRun.disabled    = true;
        btnRun.textContent = 'Running Reconciliation... Please wait.';
    }
    if (alertBox) alertBox.style.display = 'none';

    try {
        const res = await fetch('/api/reconciliation/run', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({
                month: selectedMonth,
                year:  yearVal
            })
        });

        const data = await res.json();

        if (!res.ok) {
            const errDetail = (data && data.detail)
                ? data.detail
                : 'Reconciliation Failed: The crosscheck procedure could not be completed.';
            
            closeReconciliationModal();
            showReconciliationErrorModal(errDetail);
            
            if (btnRun) {
                btnRun.disabled    = false;
                btnRun.textContent = 'Run Reconciliation';
            }
            return;
        }

        // Success — close param modal, open result modal
        closeReconciliationModal();
        showReconciliationResultModal(
            data.title   || 'Reconciliation Completed',
            data.month   || selectedMonth,
            data.year    || yearVal,
            data.presult || 'Reconciliation procedure executed successfully.',
            data.results || []
        );

    } catch (err) {
        console.error('Reconciliation run exception:', err);
        closeReconciliationModal();
        showReconciliationErrorModal('Operation Failed: Network error or unexpected exception while executing reconciliation.');
        if (btnRun) {
            btnRun.disabled    = false;
            btnRun.textContent = 'Run Reconciliation';
        }
    }
}

// -----------------------------------------------------------------------------
// RECONCILIATION RESULT & ERROR MODALS
// -----------------------------------------------------------------------------

function showReconciliationResultModal(title, month, year, presult, results) {
    const overlay   = document.getElementById('reconciliation-result-modal-overlay');
    const elTitle   = document.getElementById('reconciliation-result-title');
    const elMonth   = document.getElementById('reconciliation-result-month');
    const elYear    = document.getElementById('reconciliation-result-year');
    const elPresult = document.getElementById('reconciliation-result-presult');
    const tbody     = document.getElementById('reconciliation-table-body');

    if (elTitle)   elTitle.textContent   = title;
    if (elMonth)   elMonth.textContent   = month;
    if (elYear)    elYear.textContent    = year;
    if (elPresult) elPresult.textContent = presult;

    if (tbody) {
        tbody.innerHTML = '';
        if (results && results.length > 0) {
            results.forEach(row => {
                const tr = document.createElement('tr');
                tr.style.borderBottom = '1px solid rgba(255,255,255,0.05)';
                
                const reportType = row.REPORT_TYPE || row.report_type || 'N/A';
                const countSched = row.NO_IN_SCHEDULES !== undefined ? row.NO_IN_SCHEDULES : (row.no_in_schedules || 0);
                const countRaw   = row.NO_IN_RAW_DATA !== undefined ? row.NO_IN_RAW_DATA : (row.no_in_raw_data || 0);
                const remarks    = (row.REMARKS || row.remarks || 'OK').toString();

                const isOk = remarks.toUpperCase() === 'OK';
                
                // OK is non-clickable normal text/badge. Mismatch is an active clickable action button.
                const badgeHtml = isOk
                    ? '<span style="background:rgba(16,185,129,0.15);color:#34d399;padding:0.25rem 0.6rem;border-radius:6px;font-weight:600;font-size:0.75rem;cursor:default;display:inline-block;">✓ OK</span>'
                    : `<button type="button" onclick="openReconciliationDetailsParamModal('${reportType}', '${month}', '${year}')" style="background:linear-gradient(135deg, rgba(239,68,68,0.3), rgba(225,29,72,0.4));color:#fca5a5;border:1px solid rgba(239,68,68,0.6);padding:0.25rem 0.6rem;border-radius:6px;font-weight:700;font-size:0.75rem;cursor:pointer;transition:all 0.2s ease;display:inline-flex;align-items:center;gap:0.35rem;box-shadow:0 2px 8px rgba(239,68,68,0.25);" title="Click to inspect mismatch details for ${reportType}">⚠️ Mismatch &nbsp;🔍 Details</button>`;

                tr.innerHTML = `
                    <td style="padding:0.55rem 0.8rem;font-weight:600;color:#e2e8f0;">${reportType}</td>
                    <td style="padding:0.55rem 0.8rem;text-align:right;font-family:monospace;color:#60a5fa;">${countSched}</td>
                    <td style="padding:0.55rem 0.8rem;text-align:right;font-family:monospace;color:#34d399;">${countRaw}</td>
                    <td style="padding:0.55rem 0.8rem;text-align:center;">${badgeHtml}</td>
                `;
                tbody.appendChild(tr);
            });
        } else {
            tbody.innerHTML = `
                <tr>
                    <td colspan="4" style="padding:1rem;text-align:center;color:var(--text-muted);">
                        No data items returned for cross-check.
                    </td>
                </tr>
            `;
        }
    }

    if (overlay) overlay.style.display = 'flex';
}

function closeReconciliationResultModal() {
    const overlay = document.getElementById('reconciliation-result-modal-overlay');
    if (overlay) overlay.style.display = 'none';
}

function showReconciliationErrorModal(message, title) {
    const overlay = document.getElementById('reconciliation-error-modal-overlay');
    const elTitle = document.getElementById('reconciliation-error-title');
    const elMsg   = document.getElementById('reconciliation-error-message');

    if (elTitle) elTitle.textContent = title || 'Reconciliation Notice';
    if (elMsg)   elMsg.textContent   = message || 'An error occurred during reconciliation cross-check.';

    if (overlay) overlay.style.display = 'flex';
}

function closeReconciliationErrorModal() {
    const overlay = document.getElementById('reconciliation-error-modal-overlay');
    if (overlay) overlay.style.display = 'none';
}

// -----------------------------------------------------------------------------
// RECONCILIATION DETAILS (MISMATCH DRILL-DOWN) HANDLERS
// -----------------------------------------------------------------------------

function openReconciliationDetailsParamModal(reportType, currentMonth, currentYear) {
    const overlay   = document.getElementById('reconciliation-details-param-modal-overlay');
    const inputType = document.getElementById('details-report-type-input');
    const selMonth  = document.getElementById('details-month-select');
    const inputYear = document.getElementById('details-year-input');
    const alertBox  = document.getElementById('reconciliation-details-modal-alert');
    const btnRun    = document.getElementById('btn-run-reconciliation-details');

    if (!overlay) return;

    if (inputType) inputType.value = reportType || '';
    if (selMonth)  selMonth.value  = currentMonth || '';
    if (inputYear) inputYear.value = currentYear  || new Date().getFullYear();
    if (alertBox)  alertBox.style.display = 'none';
    if (btnRun) {
        btnRun.disabled  = false;
        btnRun.textContent = 'Run Details';
    }

    overlay.style.display = 'flex';
}

function closeReconciliationDetailsParamModal() {
    const overlay = document.getElementById('reconciliation-details-param-modal-overlay');
    if (overlay) overlay.style.display = 'none';
}

async function handleReconciliationDetailsSubmit(event) {
    if (event) event.preventDefault();

    const inputType = document.getElementById('details-report-type-input');
    const selMonth  = document.getElementById('details-month-select');
    const inputYear = document.getElementById('details-year-input');
    const alertBox  = document.getElementById('reconciliation-details-modal-alert');
    const btnRun    = document.getElementById('btn-run-reconciliation-details');

    const reportType    = inputType ? inputType.value.trim() : '';
    const selectedMonth = selMonth  ? selMonth.value.trim()  : '';
    const yearVal       = inputYear ? inputYear.value.trim() : '';

    if (!reportType) {
        showProcessAlert(alertBox, 'error', 'Report Type Required: No report type selected.');
        return;
    }
    if (!selectedMonth) {
        showProcessAlert(alertBox, 'error', 'Month Required: Please select a month before continuing.');
        return;
    }
    if (!yearVal) {
        showProcessAlert(alertBox, 'error', 'Year Required: Please enter or select a year before continuing.');
        return;
    }

    if (btnRun) {
        btnRun.disabled    = true;
        btnRun.textContent = 'Fetching Details... Please wait.';
    }
    if (alertBox) alertBox.style.display = 'none';

    try {
        const res = await fetch('/api/reconciliation/details', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({
                month:       selectedMonth,
                year:        yearVal,
                report_type: reportType
            })
        });

        const data = await res.json();

        if (!res.ok) {
            const errDetail = (data && data.detail)
                ? data.detail
                : 'Reconciliation Details Failed: Unable to fetch mismatch reference numbers.';
            
            closeReconciliationDetailsParamModal();
            showReconciliationErrorModal(errDetail, 'Mismatch Details Error');

            if (btnRun) {
                btnRun.disabled    = false;
                btnRun.textContent = 'Run Details';
            }
            return;
        }

        closeReconciliationDetailsParamModal();
        showReconciliationDetailsResultModal(
            data.title       || `Mismatch Details: ${reportType}`,
            data.month       || selectedMonth,
            data.year        || yearVal,
            data.report_type || reportType,
            data.presult     || `Found reference details for ${reportType}`,
            data.results     || []
        );

    } catch (err) {
        console.error('Reconciliation details exception:', err);
        closeReconciliationDetailsParamModal();
        showReconciliationErrorModal('Operation Failed: Network error while fetching mismatch details.', 'Network Error');
        if (btnRun) {
            btnRun.disabled    = false;
            btnRun.textContent = 'Run Details';
        }
    }
}

function showReconciliationDetailsResultModal(title, month, year, reportType, summary, results) {
    const overlay   = document.getElementById('reconciliation-details-result-modal-overlay');
    const elTitle   = document.getElementById('details-result-title');
    const elType    = document.getElementById('details-result-report-type');
    const elMonth   = document.getElementById('details-result-month');
    const elYear    = document.getElementById('details-result-year');
    const elSummary = document.getElementById('details-result-summary');
    const tbody     = document.getElementById('details-table-body');

    if (elTitle)   elTitle.textContent   = title;
    if (elType)    elType.textContent    = reportType;
    if (elMonth)   elMonth.textContent   = month;
    if (elYear)    elYear.textContent    = year;
    if (elSummary) elSummary.textContent = summary;

    if (tbody) {
        tbody.innerHTML = '';
        if (results && results.length > 0) {
            results.forEach((row, idx) => {
                const tr = document.createElement('tr');
                tr.style.borderBottom = '1px solid rgba(255,255,255,0.05)';
                
                const slNo  = row.SL_NO !== undefined ? row.SL_NO : (row.sl_no !== undefined ? row.sl_no : (idx + 1));
                const refNo = row.REFERENCE_NO || row.reference_no || 'N/A';

                tr.innerHTML = `
                    <td style="padding:0.5rem 0.8rem;text-align:center;font-weight:600;color:var(--text-muted);">${slNo}</td>
                    <td style="padding:0.5rem 0.8rem;font-family:monospace;color:#fca5a5;font-weight:600;letter-spacing:0.03em;">${refNo}</td>
                `;
                tbody.appendChild(tr);
            });
        } else {
            tbody.innerHTML = `
                <tr>
                    <td colspan="2" style="padding:1rem;text-align:center;color:var(--text-muted);">
                        No mismatch reference records returned.
                    </td>
                </tr>
            `;
        }
    }

    if (overlay) overlay.style.display = 'flex';
}

function closeReconciliationDetailsResultModal() {
    const overlay = document.getElementById('reconciliation-details-result-modal-overlay');
    if (overlay) overlay.style.display = 'none';
}

// Expose to global scope (mirrors existing window.* exports at bottom of file)
window.openReconciliationModal               = openReconciliationModal;
window.closeReconciliationModal              = closeReconciliationModal;
window.handleReconciliationSubmit            = handleReconciliationSubmit;
window.handleReconciliationItemClick         = handleReconciliationItemClick;
window.showReconciliationResultModal         = showReconciliationResultModal;
window.closeReconciliationResultModal        = closeReconciliationResultModal;
window.showReconciliationErrorModal          = showReconciliationErrorModal;
window.closeReconciliationErrorModal         = closeReconciliationErrorModal;
window.openReconciliationDetailsParamModal   = openReconciliationDetailsParamModal;
window.closeReconciliationDetailsParamModal  = closeReconciliationDetailsParamModal;
window.handleReconciliationDetailsSubmit     = handleReconciliationDetailsSubmit;
window.showReconciliationDetailsResultModal = showReconciliationDetailsResultModal;
window.closeReconciliationDetailsResultModal= closeReconciliationDetailsResultModal;
window.updateReconciliationVisibility        = updateReconciliationVisibility;
window.setReconciliationCompleted            = setReconciliationCompleted;
window.getReconciliationState                = getReconciliationState;


