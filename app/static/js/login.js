// =============================================================================
// MEGHNA SMART RETURN — Interactive Umbrella & Pull-Rope Login Engine
// =============================================================================

document.addEventListener('DOMContentLoaded', () => {
    initLoginOverlayState();
    initRopeInteraction();
});

function initLoginOverlayState() {
    const overlay = document.getElementById('login-screen-overlay');
    if (!overlay) return;

    // Check if user is authenticated in session
    const isAuthenticated = sessionStorage.getItem('cib_authenticated') === 'true';

    if (isAuthenticated) {
        overlay.style.display = 'none';
        document.body.classList.remove('login-locked');
        updateHeaderUserProfile();
    } else {
        overlay.style.display = 'flex';
        overlay.style.opacity = '1';
        overlay.style.transform = 'scale(1)';
        document.body.classList.add('login-locked');
        resetLoginOverlayToWelcome();
    }
}

function resetLoginOverlayToWelcome() {
    const welcomeStage = document.getElementById('login-welcome-stage');
    const loginCardContainer = document.getElementById('login-card-container');
    const umbrellaHero = document.getElementById('umbrella-hero-container');
    const canopy = document.getElementById('umbrella-canopy-path');
    const ropeKnobWrapper = document.getElementById('rope-knob-wrapper');
    const brandHeader = document.querySelector('.login-brand-header');
    const welcomeFooter = document.querySelector('.login-welcome-footer');

    if (welcomeStage) {
        welcomeStage.style.display = 'flex';
        welcomeStage.style.opacity = '1';
        welcomeStage.style.transform = 'translateY(0)';
    }

    if (loginCardContainer) {
        loginCardContainer.style.display = 'none';
        loginCardContainer.classList.remove('card-appeared');
    }

    if (umbrellaHero) {
        umbrellaHero.classList.remove('umbrella-unfurled');
    }

    if (canopy) {
        canopy.classList.remove('canopy-open');
        canopy.style.transform = '';
    }

    if (ropeKnobWrapper) {
        ropeKnobWrapper.style.transform = 'translateY(0)';
        ropeKnobWrapper.style.transition = '';
    }

    if (brandHeader) {
        brandHeader.style.opacity = '1';
        brandHeader.style.transform = 'translateY(0)';
    }

    if (welcomeFooter) {
        welcomeFooter.style.opacity = '1';
        welcomeFooter.style.transform = 'translateY(0)';
    }

    window.hasTriggeredUnfurl = false;
}

// -----------------------------------------------------------------------------
// INTERACTIVE ROPE PULL & DRAG PHYSICS
// -----------------------------------------------------------------------------

function initRopeInteraction() {
    const heroContainer = document.getElementById('umbrella-hero-container');
    const pendulumGroup = document.getElementById('pendulum-swing-group');
    const canopy = document.getElementById('umbrella-canopy-path');

    if (!heroContainer) return;

    let isDragging = false;
    let startY = 0;
    let currentDeltaY = 0;
    const PULL_THRESHOLD = 70; // px pull distance required to unfurl (PULL ONLY!)

    function onPointerDown(e) {
        if (window.hasTriggeredUnfurl) return;
        isDragging = true;
        startY = e.type.includes('touch') ? e.touches[0].clientY : e.clientY;
        currentDeltaY = 0;

        // Pause pendulum swing while dragging physically
        if (pendulumGroup) pendulumGroup.classList.add('dragging');
        if (heroContainer) heroContainer.classList.add('dragging');

        document.addEventListener('mousemove', onPointerMove);
        document.addEventListener('mouseup', onPointerUp);
        document.addEventListener('touchmove', onPointerMove, { passive: false });
        document.addEventListener('touchend', onPointerUp);
    }

    function onPointerMove(e) {
        if (!isDragging || window.hasTriggeredUnfurl) return;
        if (e.cancelable) e.preventDefault();

        const clientY = e.type.includes('touch') ? e.touches[0].clientY : e.clientY;
        let deltaY = clientY - startY;

        // Clamp drag distance between 0 and 140px
        deltaY = Math.max(0, Math.min(140, deltaY));
        currentDeltaY = deltaY;

        // Apply physical pull stretch transform to the J-Hook Pendulum assembly
        if (pendulumGroup) {
            pendulumGroup.style.transform = `translateY(${deltaY}px)`;
        }

        // Flex umbrella canopy downward under pull tension
        if (canopy) {
            const flexScale = 1 + (deltaY / 400);
            canopy.style.transform = `scaleY(${flexScale})`;
        }

        // Trigger unfurl sequence ONLY if pulled past threshold
        if (deltaY >= PULL_THRESHOLD && !window.hasTriggeredUnfurl) {
            isDragging = false;
            onPointerUp();
            triggerUnfurlSequence();
        }
    }

    function onPointerUp() {
        if (!window.hasTriggeredUnfurl && currentDeltaY < PULL_THRESHOLD) {
            springBackRope();
        }

        isDragging = false;
        if (heroContainer) heroContainer.classList.remove('dragging');

        document.removeEventListener('mousemove', onPointerMove);
        document.removeEventListener('mouseup', onPointerUp);
        document.removeEventListener('touchmove', onPointerMove);
        document.removeEventListener('touchend', onPointerUp);
    }

    function springBackRope() {
        if (pendulumGroup) {
            pendulumGroup.style.transition = 'transform 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275)';
            pendulumGroup.style.transform = 'translateY(0)';
        }

        if (canopy) {
            canopy.style.transition = 'transform 0.5s ease';
            canopy.style.transform = 'scaleY(1)';
        }

        setTimeout(() => {
            if (pendulumGroup) pendulumGroup.style.transition = '';
            if (canopy) canopy.style.transition = '';
            if (pendulumGroup && !window.hasTriggeredUnfurl) {
                pendulumGroup.classList.remove('dragging');
            }
        }, 500);
    }

    heroContainer.addEventListener('mousedown', onPointerDown);
    heroContainer.addEventListener('touchstart', onPointerDown, { passive: false });
}

// -----------------------------------------------------------------------------
// UNFURL ENTRANCE & LOGIN FORM APPEARANCE SEQUENCE
// -----------------------------------------------------------------------------

function triggerUnfurlSequence() {
    if (window.hasTriggeredUnfurl) return;
    window.hasTriggeredUnfurl = true;

    const welcomeStage = document.getElementById('login-welcome-stage');
    const loginCardContainer = document.getElementById('login-card-container');
    const umbrellaHero = document.getElementById('umbrella-hero-container');
    const canopy = document.getElementById('umbrella-canopy-path');
    const ropeKnobWrapper = document.getElementById('rope-knob-wrapper');
    const brandHeader = document.querySelector('.login-brand-header');
    const welcomeFooter = document.querySelector('.login-welcome-footer');

    // 1. Spring tension release animation on rope knob
    if (ropeKnobWrapper) {
        ropeKnobWrapper.style.transition = 'transform 0.4s cubic-bezier(0.34, 1.56, 0.64, 1)';
        ropeKnobWrapper.style.transform = 'translateY(110px)';
    }

    // 2. Umbrella canopy opens wide and gently floats upward into top header
    setTimeout(() => {
        if (umbrellaHero) {
            umbrellaHero.classList.add('umbrella-unfurled');
        }
        if (canopy) {
            canopy.classList.add('canopy-open');
        }

        // 3. Fade out welcome header & footer
        if (brandHeader) {
            brandHeader.style.transition = 'all 0.5s ease';
            brandHeader.style.opacity = '0';
            brandHeader.style.transform = 'translateY(-25px)';
        }
        if (welcomeFooter) {
            welcomeFooter.style.transition = 'all 0.5s ease';
            welcomeFooter.style.opacity = '0';
            welcomeFooter.style.transform = 'translateY(25px)';
        }

        // 4. Gracefully reveal Secure Login Form Card
        setTimeout(() => {
            if (welcomeStage) welcomeStage.style.display = 'none';
            if (loginCardContainer) {
                loginCardContainer.style.display = 'flex';
                void loginCardContainer.offsetWidth; // Force CSS reflow
                loginCardContainer.classList.add('card-appeared');
            }
            
            // Auto-focus username input
            const usernameInput = document.getElementById('login-username');
            if (usernameInput) usernameInput.focus();

        }, 400);

    }, 250);
}

// -----------------------------------------------------------------------------
// LOGIN AUTHENTICATION HANDLERS
// -----------------------------------------------------------------------------

function togglePasswordVisibility() {
    const passwordInput = document.getElementById('login-password');
    const toggleIcon = document.getElementById('password-toggle-icon');
    if (!passwordInput || !toggleIcon) return;

    if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        toggleIcon.textContent = '🙈';
    } else {
        passwordInput.type = 'password';
        toggleIcon.textContent = '👁️';
    }
}

async function handleLoginSubmit(event) {
    if (event) event.preventDefault();

    const usernameInput = document.getElementById('login-username');
    const passwordInput = document.getElementById('login-password');
    const btnSubmit = document.getElementById('btn-login-submit');
    const btnText = document.getElementById('login-btn-text');
    const alertBox = document.getElementById('login-alert-box');

    const username = usernameInput ? usernameInput.value.trim() : '';
    const password = passwordInput ? passwordInput.value.trim() : '';

    if (!username || !password) {
        showLoginAlert('Username & Password Required: Please fill out both fields.');
        return;
    }

    if (alertBox) alertBox.style.display = 'none';

    // Lock button state & show loading spinner text
    if (btnSubmit) btnSubmit.disabled = true;
    if (btnText) btnText.innerHTML = '<span class="login-spinner">⏳</span> Authenticating Securely…';

    try {
        const res = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        const data = await res.json();

        if (!res.ok || !data.success) {
            const errDetail = (data && data.detail) || 'Invalid Credentials: Please enter valid Username and Password.';
            showLoginAlert(errDetail);
            if (btnSubmit) btnSubmit.disabled = false;
            if (btnText) btnText.textContent = 'Secure Sign In →';
            return;
        }

        // Authentication Success!
        if (btnText) btnText.innerHTML = 'Access Granted ✓';
        if (btnSubmit) btnSubmit.classList.add('success-state');

        sessionStorage.setItem('cib_authenticated', 'true');
        sessionStorage.setItem('cib_username', username);
        updateHeaderUserProfile(username, data.role);

        // Smooth transition to Dashboard
        setTimeout(() => {
            const overlay = document.getElementById('login-screen-overlay');
            if (overlay) {
                overlay.style.transition = 'all 0.6s cubic-bezier(0.4, 0, 0.2, 1)';
                overlay.style.opacity = '0';
                overlay.style.transform = 'scale(1.05)';
                setTimeout(() => {
                    overlay.style.display = 'none';
                    document.body.classList.remove('login-locked');
                    if (typeof showHomeView === 'function') showHomeView();
                }, 600);
            }
        }, 500);

    } catch (err) {
        // Client-side fallback authentication (admin / admin)
        if (username.toLowerCase() === 'admin' && password === 'admin') {
            if (btnText) btnText.innerHTML = 'Access Granted ✓';
            sessionStorage.setItem('cib_authenticated', 'true');
            sessionStorage.setItem('cib_username', username);
            updateHeaderUserProfile(username, 'Internal Admin');

            setTimeout(() => {
                const overlay = document.getElementById('login-screen-overlay');
                if (overlay) {
                    overlay.style.transition = 'all 0.6s cubic-bezier(0.4, 0, 0.2, 1)';
                    overlay.style.opacity = '0';
                    overlay.style.transform = 'scale(1.05)';
                    setTimeout(() => {
                        overlay.style.display = 'none';
                        document.body.classList.remove('login-locked');
                        if (typeof showHomeView === 'function') showHomeView();
                    }, 600);
                }
            }, 500);
        } else {
            showLoginAlert('Invalid Credentials: Username or Password incorrect.');
            if (btnSubmit) btnSubmit.disabled = false;
            if (btnText) btnText.textContent = 'Secure Sign In →';
        }
    }
}

function updateHeaderUserProfile(username, role) {
    const user = username || sessionStorage.getItem('cib_username') || 'admin';
    const displayUser = user.charAt(0).toUpperCase() + user.slice(1);
    const initials = user.slice(0, 2).toUpperCase();

    const nameEl = document.getElementById('header-user-name');
    const avatarEl = document.getElementById('header-user-avatar');
    const roleEl = document.getElementById('header-user-role');

    if (nameEl) nameEl.textContent = displayUser;
    if (avatarEl) avatarEl.textContent = initials;
    if (roleEl) roleEl.textContent = role || 'Internal Admin';
}

function showLoginAlert(message) {
    const alertBox = document.getElementById('login-alert-box');
    if (!alertBox) return;
    alertBox.textContent = message;
    alertBox.style.display = 'block';
}

function handleLogoutClick() {
    sessionStorage.removeItem('cib_authenticated');
    sessionStorage.removeItem('cib_username');
    const overlay = document.getElementById('login-screen-overlay');
    if (overlay) {
        overlay.style.display = 'flex';
        void overlay.offsetWidth;
        overlay.style.transition = 'all 0.4s ease';
        overlay.style.opacity = '1';
        overlay.style.transform = 'scale(1)';
        document.body.classList.add('login-locked');
        resetLoginOverlayToWelcome();
    }
}

window.togglePasswordVisibility = togglePasswordVisibility;
window.handleLoginSubmit = handleLoginSubmit;
window.handleLogoutClick = handleLogoutClick;
window.triggerUnfurlSequence = triggerUnfurlSequence;
