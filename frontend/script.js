/**
 * GazeboExpress - Smart Campus Food Ordering & Queue Management
 * Frontend SPA Application Logic with Official Authgear Web SDK Integration
 */

// ==============================================================================
// AUTHENTICATION & GLOBAL STATE
// ==============================================================================
let authgearClient = null;
const authState = {
    isAuthenticated: false,
    user: null,
    role: 'student', // 'student' | 'admin' (determined server-side)
    token: null
};

const state = {
    currentView: 'menu',
    menuItems: [],
    categories: [],
    selectedCategory: 'all',
    searchQuery: '',
    sortBy: 'rating_desc',
    cart: JSON.parse(localStorage.getItem('ge_cart') || '[]'),
    orders: [],
    orderFilter: 'All',
    reviewsData: { reviews: [], total_reviews: 0, average_rating: 0.0, distribution: {} },
    queueData: { active_orders: 0, queue_status: 'Low', estimated_wait: '5-10 mins', placed_orders: 0, preparing_orders: 0, ready_orders: 0 },
    notifications: [],
    unreadNotifCount: 0,
    selectedPickupTime: 'In 10 mins',
    itemPendingDeleteId: null,
    reviewRatingVal: 5,
    onboardingSelectedRole: 'student'
};

// Dedicated Verified Local Menu Item Images
const MENU_ITEM_LOCAL_IMAGES = {
    'Veg Samosa': 'images/menu/veg-samosa.jpg',
    'Veg Puff': 'images/menu/veg-puff.jpg',
    'Chicken Puff': 'images/menu/chicken-puff.jpg',
    'Peri Peri French Fries': 'images/menu/peri-peri-french-fries.jpg',
    'Veg Sandwich': 'images/menu/veg-sandwich.jpg',
    'Crispy Chicken Tenders': 'images/menu/crispy-chicken-tenders.jpg',
    'Peanut Butter Chicken Burger': 'images/menu/peanut-butter-chicken-burger.jpg',
    'Texas Style BBQ Burger': 'images/menu/texas-style-bbq-burger.jpg',
    'The Country Style Hamburger': 'images/menu/the-country-style-hamburger.jpg',
    'The Legendary Burger': 'images/menu/the-legendary-burger.jpg',
    'Veggies Delight Burger': 'images/menu/veggies-delight-burger.jpg',
    'Chicha Melt Burger': 'images/menu/chicha-melt-burger.jpg',
    'Crispy Paneer Grilled Sandwich': 'images/menu/crispy-paneer-grilled-sandwich.jpg',
    'Chicken Club Sandwich': 'images/menu/chicken-club-sandwich.jpg',
    'Veg Cheese Sandwich': 'images/menu/veg-cheese-sandwich.jpg',
    'Tandoori Paneer Sandwich': 'images/menu/tandoori-paneer-sandwich.jpg',
    'Corn & Cheese Sandwich': 'images/menu/corn-cheese-sandwich.jpg',
    'BBQ Chicken Sandwich': 'images/menu/bbq-chicken-sandwich.jpg',
    'White Sauce Pasta (Alfredo Penne)': 'images/menu/white-sauce-pasta-alfredo-penne.jpg',
    'Red Sauce Pasta': 'images/menu/red-sauce-pasta.jpg',
    'Signature Cold Coffee': 'images/menu/signature-cold-coffee.jpg',
    'Fresh Mint Lime Cooler': 'images/menu/fresh-mint-lime-cooler.jpg',
    'Iced Lemon Tea': 'images/menu/iced-lemon-tea.jpg',
    'Mango Smoothie': 'images/menu/mango-smoothie.jpg',
    'Fresh Lime Soda': 'images/menu/fresh-lime-soda.jpg',
    'Packaged Water': 'images/menu/packaged-water.jpg',
    'Hot Chocolate Brownie Sundae': 'images/menu/hot-chocolate-brownie-sundae.jpg',
    'Chocolate Mousse': 'images/menu/chocolate-mousse.jpg',
    'Vanilla Ice Cream': 'images/menu/vanilla-ice-cream.jpg',
    'Gulab Jamun': 'images/menu/gulab-jamun.jpg'
};

// Verified Category Thumbnails (using local verified assets)
const CATEGORY_THUMBS = {
    'Burgers': 'images/menu/texas-style-bbq-burger.jpg',
    'Sandwiches': 'images/menu/tandoori-paneer-sandwich.jpg',
    'Pasta': 'images/menu/red-sauce-pasta.jpg',
    'Desserts': 'images/menu/hot-chocolate-brownie-sundae.jpg',
    'Beverages': 'images/menu/signature-cold-coffee.jpg',
    'Snacks': 'images/menu/veg-samosa.jpg',
    'All': 'images/menu/veg-samosa.jpg'
};

const DEFAULT_FOOD_IMG = 'images/fallback-food.svg';

function getMenuItemImage(item) {
    if (!item) return DEFAULT_FOOD_IMG;
    const name = item.name ? String(item.name).trim() : '';
    if (MENU_ITEM_LOCAL_IMAGES[name]) {
        return MENU_ITEM_LOCAL_IMAGES[name];
    }
    if (item.image_url && typeof item.image_url === 'string' && item.image_url.trim()) {
        return item.image_url.trim();
    }
    return CATEGORY_THUMBS[item.category] || DEFAULT_FOOD_IMG;
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function getNeutralAvatar(name, role) {
    const trimmed = (name || '').trim();
    let initials = 'GE';
    if (trimmed) {
        const parts = trimmed.split(/\s+/).filter(Boolean);
        if (parts.length >= 2) {
            initials = (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
        } else if (parts.length === 1 && parts[0].length >= 2) {
            initials = parts[0].slice(0, 2).toUpperCase();
        } else if (parts.length === 1) {
            initials = parts[0][0].toUpperCase();
        }
    }
    const bg = role === 'admin' ? '#EA580C' : '#FF5E1E';
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
        <circle cx="50" cy="50" r="50" fill="${bg}"/>
        <text x="50%" y="54%" text-anchor="middle" dominant-baseline="middle" fill="#ffffff" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-weight="700" font-size="38">${initials}</text>
    </svg>`;
    return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
}


// ==============================================================================
// AUTHENTICATION: AUTHGEAR WEB SDK INITIALIZATION & FLOW
// ==============================================================================

function getRedirectURI() {
    // Dynamic redirect URI ensuring it works on both localhost and deployed HTTPS
    const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    if (isLocal) {
        return window.location.origin.replace(/\/+$/, '');
    }
    // On production HTTPS origin, ensure exact trailing slash matching Authgear Web SDK's finishAuthentication()
    const base = (window.GAZEBO_AUTH_CONFIG && window.GAZEBO_AUTH_CONFIG.redirectURI)
        ? window.GAZEBO_AUTH_CONFIG.redirectURI
        : window.location.origin;
    return base.replace(/\/+$/, '') + '/';
}

async function initAuthgear() {
    const authScreen = document.getElementById('authScreen');
    const appContainer = document.getElementById('appContainer');
    const authStatusBox = document.getElementById('authStatusBox');
    const authStatusText = document.getElementById('authStatusText');
    const authActionBtns = document.getElementById('authActionBtns');

    // 1. Check for quick test token in URL or session (e.g. for automated test suites or local demo)
    const urlParams = new URLSearchParams(window.location.search);
    const demoTokenParam = urlParams.get('demo_token');
    if (demoTokenParam) {
        sessionStorage.setItem('ge_test_token', `test_token_${demoTokenParam}_user`);
        window.history.replaceState({}, document.title, window.location.pathname);
    }
    const savedTestToken = sessionStorage.getItem('ge_test_token');

    if (savedTestToken) {
        await loadAuthenticatedSession(savedTestToken);
        return;
    }

    // 2. Official Authgear Web SDK Initialization
    if (!window.authgear) {
        console.warn('Authgear Web SDK script not loaded yet, checking configuration...');
    }

    let endpoint = window.GAZEBO_AUTH_CONFIG?.endpoint || '';
    let clientID = window.GAZEBO_AUTH_CONFIG?.clientID || '';

    // If config is missing, fetch from backend endpoint
    if (!endpoint || !clientID) {
        try {
            const configRes = await fetch('/api/auth/config');
            if (configRes.ok) {
                const cfg = await configRes.json();
                endpoint = cfg.endpoint || endpoint;
                clientID = cfg.clientID || clientID;
                window.GAZEBO_AUTH_CONFIG = cfg;
            }
        } catch (e) {
            console.warn('Could not fetch /api/auth/config:', e);
        }
    }

    try {
        if (window.authgear?.default && endpoint && clientID) {
            authgearClient = window.authgear.default;

            await authgearClient.configure({
                clientID: clientID,
                endpoint: endpoint,
                sessionType: 'refresh_token'
            });

            // Safeguard hook: ensure token exchange redirect_uri strictly matches startAuthentication redirect_uri
            const targetApiClient = authgearClient.apiClient || authgearClient.baseContainer?.apiClient;
            if (targetApiClient && targetApiClient._oidcTokenRequest) {
                const origTokenReq = targetApiClient._oidcTokenRequest.bind(targetApiClient);
                targetApiClient._oidcTokenRequest = async function(req) {
                    const storedURI = sessionStorage.getItem('gazebo_auth_redirect_uri');
                    if (storedURI && req && req.grant_type === 'authorization_code') {
                        req.redirect_uri = storedURI;
                    }
                    return origTokenReq(req);
                };
            }

            showUnauthenticatedScreen();

            // Check if returning from Authgear OAuth redirect
            const hasAuthCode = urlParams.has('code');
            if (hasAuthCode) {
                if (authStatusBox) {
                    authStatusBox.style.display = 'flex';
                    authStatusText.textContent = 'Verifying authentication with Authgear...';
                    if (authActionBtns) authActionBtns.style.display = 'none';
                }

                try {
                    await authgearClient.finishAuthentication();
                    sessionStorage.removeItem('gazebo_auth_redirect_uri');
                    window.history.replaceState({}, document.title, window.location.pathname);
                } catch (finishErr) {
                    console.error('Error in finishAuthentication:', finishErr);
                    sessionStorage.removeItem('gazebo_auth_redirect_uri');
                    showToast('Authentication failed or expired. Please sign in again.', 'error');
                }
            }

            // Check session state
            const sessionState = authgearClient.sessionState;
            if (sessionState === 'AUTHENTICATED') {
                let userInfo = null;
                try {
                    userInfo = await authgearClient.fetchUserInfo();
                } catch (uErr) {
                    console.warn('Could not fetch userInfo directly from SDK:', uErr);
                }
                // Prefer idToken because it is a signed JWT containing sub, email, and name claims
                const token = authgearClient.idToken || authgearClient.accessToken;
                await loadAuthenticatedSession(token, userInfo);
                return;
            }
        }
    } catch (sdkErr) {
        console.warn('Authgear SDK initialization note:', sdkErr);
    }

    // Unauthenticated state
    showUnauthenticatedScreen();
}

function showUnauthenticatedScreen() {
    const authScreen = document.getElementById('authScreen');
    const appContainer = document.getElementById('appContainer');
    const authStatusBox = document.getElementById('authStatusBox');
    const authActionBtns = document.getElementById('authActionBtns');

    if (authScreen) authScreen.style.display = 'flex';
    if (appContainer) appContainer.style.display = 'none';
    if (authStatusBox) authStatusBox.style.display = 'none';
    if (authActionBtns) authActionBtns.style.display = 'flex';

    // Setup Login & Signup button actions
    const loginBtn = document.getElementById('authgearLoginBtn');
    const signupBtn = document.getElementById('authgearSignupBtn');

    if (loginBtn) {
        loginBtn.onclick = async () => {
            const ep = window.GAZEBO_AUTH_CONFIG?.endpoint;
            if (authgearClient && ep) {
                try {
                    const redirectURI = getRedirectURI();
                    sessionStorage.setItem('gazebo_auth_redirect_uri', redirectURI);
                    await authgearClient.startAuthentication({
                        redirectURI: redirectURI,
                        page: 'login',
                        scope: ['openid', 'profile', 'email', 'offline_access']
                    });
                } catch (e) {
                    console.error('Authgear login error:', e);
                    showToast('Could not redirect to Authgear login. Please check configuration.', 'error');
                }
            } else {
                showToast('Authentication service is initializing. Please try again.', 'warning');
            }
        };
    }

    if (signupBtn) {
        signupBtn.onclick = async () => {
            const ep = window.GAZEBO_AUTH_CONFIG?.endpoint;
            if (authgearClient && ep) {
                try {
                    const redirectURI = getRedirectURI();
                    sessionStorage.setItem('gazebo_auth_redirect_uri', redirectURI);
                    await authgearClient.startAuthentication({
                        redirectURI: redirectURI,
                        page: 'signup',
                        scope: ['openid', 'profile', 'email', 'offline_access']
                    });
                } catch (e) {
                    console.error('Authgear signup error:', e);
                    showToast('Could not redirect to Authgear signup. Please check configuration.', 'error');
                }
            } else {
                showToast('Authentication service is initializing. Please try again.', 'warning');
            }
        };
    }
}

async function loadAuthenticatedSession(token, authgearUserInfo = null) {
    const authScreen = document.getElementById('authScreen');
    const appContainer = document.getElementById('appContainer');

    try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 20000);

        const res = await fetch('/api/auth/me', {
            headers: { 'Authorization': `Bearer ${token}` },
            signal: controller.signal
        });

        clearTimeout(timeout);

        if (!res.ok) {
            throw new Error(`Profile lookup failed with HTTP ${res.status}`);
        }

        const profile = await res.json();

        // If user is freshly registered with Authgear and has no MongoDB profile yet
        if (profile.is_new) {
            const authStatusBox = document.getElementById('authStatusBox');
            const authActionBtns = document.getElementById('authActionBtns');

            if (authStatusBox) authStatusBox.style.display = 'none';
            if (authActionBtns) authActionBtns.style.display = 'none';

            promptRoleOnboarding(token, profile, authgearUserInfo);
            return;
        }

        // Set authenticated user state
        authState.isAuthenticated = true;
        authState.user = profile;
        authState.role = profile.role || 'student';
        authState.token = token;

        // Hide auth screen and show main application
        if (authScreen) authScreen.style.display = 'none';
        if (appContainer) appContainer.style.display = 'flex';

        // Update UI displays
        updateProfileUI();
        enforceRolePermissions();

        // Initial Data Fetch
        fetchMenu();
        fetchQueueStatus();
        fetchOrders();
        fetchNotifications();

    } catch (err) {
        console.error('Error loading session:', err);
        sessionStorage.removeItem('ge_test_token');
        showToast(`Authentication note: ${err.message || 'Please sign in again.'}`, 'warning');
        showUnauthenticatedScreen();
    }
}

function promptRoleOnboarding(token, initialInfo, authgearUserInfo) {
    const modal = document.getElementById('roleOnboardingModalOverlay');
    const nameInput = document.getElementById('onboardName');
    const regNoInput = document.getElementById('onboardRegNo');
    const phoneInput = document.getElementById('onboardPhone');
    const regNoGroup = document.getElementById('onboardRegNoGroup');
    const confirmBtn = document.getElementById('confirmOnboardingBtn');
    const errorBanner = document.getElementById('onboardErrorMsg');

    const roleIcon = document.getElementById('onboardRoleIcon');
    const roleTitle = document.getElementById('onboardRoleTitle');
    const roleBadge = document.getElementById('onboardRoleBadge');
    const roleDesc = document.getElementById('onboardRoleDesc');
    const roleEmail = document.getElementById('onboardRoleEmail');

    const role = initialInfo.role || 'student';
    const email = initialInfo.email || authgearUserInfo?.email || '';
    const initialName = initialInfo.name || authgearUserInfo?.name || '';

    if (nameInput) nameInput.value = initialName;
    if (roleEmail) roleEmail.textContent = email ? `Verified Email: ${email}` : '';

    if (role === 'admin') {
        if (roleIcon) roleIcon.textContent = '🧑‍🍳';
        if (roleTitle) roleTitle.textContent = 'Canteen Administrator';
        if (roleBadge) {
            roleBadge.textContent = 'Admin Verified';
            roleBadge.className = 'badge badge-primary';
        }
        if (roleDesc) roleDesc.textContent = 'Full administrative management for menu items, kitchen flow, analytics, and canteen settings.';
        if (regNoGroup) regNoGroup.style.display = 'none';
    } else {
        if (roleIcon) roleIcon.textContent = '🎓';
        if (roleTitle) roleTitle.textContent = 'Student Account';
        if (roleBadge) {
            roleBadge.textContent = 'Verified Student';
            roleBadge.className = 'badge badge-success';
        }
        if (roleDesc) roleDesc.textContent = 'Standard campus ordering, smart queue tracking, and meal pickup access.';
        if (regNoGroup) regNoGroup.style.display = 'block';
    }

    if (errorBanner) {
        errorBanner.style.display = 'none';
        errorBanner.textContent = '';
    }

    modal.classList.add('show');

    confirmBtn.onclick = async () => {
        if (errorBanner) {
            errorBanner.style.display = 'none';
            errorBanner.textContent = '';
        }

        const name = (nameInput ? nameInput.value : '').trim();
        const regNo = (regNoInput ? regNoInput.value : '').trim();
        const phone = (phoneInput ? phoneInput.value : '').trim();

        if (!name) {
            if (errorBanner) {
                errorBanner.textContent = 'Please enter your full name.';
                errorBanner.style.display = 'block';
            }
            if (nameInput) nameInput.focus();
            return;
        }

        if (role === 'student' && !regNo) {
            if (errorBanner) {
                errorBanner.textContent = 'Student Register Number / ID is required.';
                errorBanner.style.display = 'block';
            }
            if (regNoInput) regNoInput.focus();
            return;
        }

        if (!phone) {
            if (errorBanner) {
                errorBanner.textContent = 'Please enter a contact phone number for order updates.';
                errorBanner.style.display = 'block';
            }
            if (phoneInput) phoneInput.focus();
            return;
        }

        confirmBtn.disabled = true;
        confirmBtn.textContent = 'Creating Profile...';

        try {
            const createRes = await fetch('/api/auth/profile', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    name,
                    email,
                    role,
                    register_number: role === 'student' ? regNo : (regNo || 'STAFF'),
                    student_id: role === 'student' ? regNo : (regNo || 'STAFF'),
                    phone
                })
            });

            if (!createRes.ok) {
                const errData = await createRes.json().catch(() => ({}));
                throw new Error(errData.error || 'Failed to create user profile');
            }

            modal.classList.remove('show');
            await loadAuthenticatedSession(token);
            showToast(`Welcome ${name}! Your ${role === 'admin' ? 'admin' : 'student'} account is ready.`);
        } catch (e) {
            if (errorBanner) {
                errorBanner.textContent = e.message || 'Error creating profile';
                errorBanner.style.display = 'block';
            }
            showToast(e.message || 'Error creating profile', 'error');
        } finally {
            confirmBtn.disabled = false;
            confirmBtn.textContent = 'Confirm & Enter GazeboExpress';
        }
    };
}

async function handleLogout() {
    sessionStorage.removeItem('ge_test_token');
    localStorage.removeItem('ge_role');

    if (authgearClient && authState.token && !authState.token.startsWith('test_token_')) {
        try {
            await authgearClient.logout({ redirectURI: getRedirectURI() });
        } catch (e) {
            console.warn('Authgear logout warning:', e);
        }
    }

    authState.isAuthenticated = false;
    authState.user = null;
    authState.role = 'student';
    authState.token = null;

    // Reset dropdown
    document.getElementById('profileDropdown')?.classList.remove('show');

    showUnauthenticatedScreen();
    showToast('Logged out successfully.');
}


// ==============================================================================
// ROLE-BASED UI ENFORCEMENT & PROFILE DISPLAY
// ==============================================================================

function enforceRolePermissions() {
    const isStudent = authState.role === 'student';

    // Sidebar navigation access
    const navOverview = document.getElementById('navOverview');
    const navAnalytics = document.getElementById('navAnalytics');
    const navSettings = document.getElementById('navSettings');

    if (navOverview) navOverview.style.display = isStudent ? 'none' : 'flex';
    if (navAnalytics) navAnalytics.style.display = isStudent ? 'none' : 'flex';
    if (navSettings) navSettings.style.display = isStudent ? 'none' : 'flex';

    // Menu add button
    const openAddMenuBtn = document.getElementById('openAddMenuModalBtn');
    if (openAddMenuBtn) {
        openAddMenuBtn.style.display = isStudent ? 'none' : 'inline-flex';
    }

    // Default view for students: Menu; for admins: Overview
    if (isStudent && (state.currentView === 'overview' || state.currentView === 'analytics' || state.currentView === 'settings')) {
        switchView('menu');
    }
}

function updateProfileUI() {
    if (!authState.user) return;
    const user = authState.user;
    const isStudent = authState.role === 'student';

    // Header Pill
    const avatar = document.getElementById('userAvatar');
    const nameDisplay = document.getElementById('userNameDisplay');
    const roleBadge = document.getElementById('userRoleBadge');
    const regBadge = document.getElementById('userRegNoBadge');

    const avatarUrl = user.profile_image || getNeutralAvatar(user.name, authState.role);

    if (avatar) avatar.src = avatarUrl;
    if (nameDisplay) nameDisplay.textContent = user.name || 'Gazebo User';
    if (roleBadge) {
        roleBadge.textContent = isStudent ? 'Student' : 'Admin';
        roleBadge.className = `user-role-badge ${isStudent ? 'role-student' : 'role-admin'}`;
    }
    if (regBadge) {
        const regText = user.register_number || (isStudent ? '' : 'STAFF');
        regBadge.textContent = regText;
        regBadge.style.display = regText ? 'inline-block' : 'none';
    }

    // Dropdown Pop-up
    const dropAvatar = document.getElementById('dropdownAvatar');
    const dropName = document.getElementById('dropdownName');
    const dropRole = document.getElementById('dropdownRole');
    const dropId = document.getElementById('dropdownId');
    const dropEmail = document.getElementById('dropdownEmail');

    if (dropAvatar) dropAvatar.src = avatarUrl;
    if (dropName) dropName.textContent = user.name || 'Gazebo User';
    if (dropRole) {
        dropRole.textContent = isStudent ? 'Student' : 'Canteen Admin';
        dropRole.className = `dropdown-role-tag ${isStudent ? 'role-student' : 'role-admin'}`;
    }
    if (dropId) dropId.textContent = user.register_number ? `ID: ${user.register_number}` : '';
    if (dropEmail) dropEmail.textContent = user.email || '';

    // "My Profile" Page View
    const pHeroAvatar = document.getElementById('profileHeroAvatar');
    const pHeroRole = document.getElementById('profileHeroRole');
    const pHeroName = document.getElementById('profileHeroName');
    const pHeroEmail = document.getElementById('profileHeroEmail');
    const pHeroId = document.getElementById('profileHeroId');
    const pHeroRoleText = document.getElementById('profileHeroRoleText');

    if (pHeroAvatar) pHeroAvatar.src = avatarUrl;
    if (pHeroRole) pHeroRole.textContent = isStudent ? 'Student' : 'Admin';
    if (pHeroName) pHeroName.textContent = user.name || 'Gazebo User';
    if (pHeroEmail) pHeroEmail.textContent = user.email || '';
    if (pHeroId) pHeroId.textContent = user.register_number ? `ID: ${user.register_number}` : '';
    if (pHeroRoleText) pHeroRoleText.textContent = isStudent ? 'Student Member' : 'Canteen Manager';

    const pDetailName = document.getElementById('profileDetailName');
    const pDetailEmail = document.getElementById('profileDetailEmail');
    const pDetailId = document.getElementById('profileDetailId');
    const pDetailPhone = document.getElementById('profileDetailPhone');
    const pDetailRole = document.getElementById('profileDetailRole');
    const pDetailCreated = document.getElementById('profileDetailCreated');

    if (pDetailName) pDetailName.textContent = user.name || 'Gazebo User';
    if (pDetailEmail) pDetailEmail.textContent = user.email || '';
    if (pDetailId) pDetailId.textContent = user.register_number || '-';
    if (pDetailPhone) pDetailPhone.textContent = user.phone || '-';
    if (pDetailRole) pDetailRole.textContent = isStudent ? 'Campus Student' : 'Canteen Administrator';
    if (pDetailCreated) {
        pDetailCreated.textContent = user.created_at ? new Date(user.created_at).toLocaleDateString('en-US', { month: 'long', year: 'numeric' }) : 'September 2026';
    }

    // Auto-fill student info in Cart Drawer
    if (isStudent) {
        const cartName = document.getElementById('cartStudentName');
        const cartId = document.getElementById('cartStudentId');
        if (cartName) cartName.value = user.name;
        if (cartId) cartId.value = user.register_number || '';
    }
}


// ==============================================================================
// INITIALIZATION
// ==============================================================================
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initProfileDropdown();
    initSearch();
    initCartDrawer();
    initModals();
    initSettings();
    initMobileNav();
    initReviews();
    initProfileEditing();

    // Start Authgear verification
    initAuthgear();

    // Auto-refresh queue and notifications every 30s
    setInterval(() => {
        if (authState.isAuthenticated) {
            fetchQueueStatus();
            fetchNotifications();
            if (state.currentView === 'orders') fetchOrders();
            if (state.currentView === 'delivery') fetchOrders();
        }
    }, 30000);
});


// ==============================================================================
// NAVIGATION & VIEWS
// ==============================================================================
function initNavigation() {
    const navItems = document.querySelectorAll('.sidebar-nav .nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const targetView = item.getAttribute('data-view');
            switchView(targetView);

            // Close mobile sidebar if open
            document.getElementById('sidebar').classList.remove('mobile-open');
        });
    });
}

function switchView(viewName) {
    state.currentView = viewName;

    // Update active nav link
    document.querySelectorAll('.sidebar-nav .nav-item').forEach(link => {
        link.classList.toggle('active', link.getAttribute('data-view') === viewName);
    });

    // Update view visibility
    document.querySelectorAll('.content-view').forEach(view => {
        view.classList.toggle('active', view.id === `view-${viewName}`);
    });

    // View-specific data refreshes
    if (viewName === 'overview') loadOverviewDashboard();
    if (viewName === 'orders') fetchOrders();
    if (viewName === 'delivery') loadSmartQueueKanban();
    if (viewName === 'reviews') loadReviewsView();
    if (viewName === 'analytics') loadAnalyticsView();
    if (viewName === 'settings') loadSettingsView();
    if (viewName === 'profile') loadUserProfileStats();
}

function initMobileNav() {
    const mobileMenuBtn = document.getElementById('mobileMenuBtn');
    const mobileCloseBtn = document.getElementById('mobileCloseBtn');
    const sidebar = document.getElementById('sidebar');

    if (mobileMenuBtn) {
        mobileMenuBtn.addEventListener('click', () => {
            sidebar.classList.add('mobile-open');
        });
    }

    if (mobileCloseBtn) {
        mobileCloseBtn.addEventListener('click', () => {
            sidebar.classList.remove('mobile-open');
        });
    }

    // Close on outside click on mobile
    document.addEventListener('click', (e) => {
        if (sidebar && sidebar.classList.contains('mobile-open')) {
            if (!sidebar.contains(e.target) && !mobileMenuBtn.contains(e.target)) {
                sidebar.classList.remove('mobile-open');
            }
        }
    });
}


// ==============================================================================
// PROFILE POPUP DROPDOWN & PROFILE MANAGEMENT
// ==============================================================================
function initProfileDropdown() {
    const userProfileBtn = document.getElementById('userProfileBtn');
    const dropdown = document.getElementById('profileDropdown');

    if (userProfileBtn && dropdown) {
        userProfileBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            dropdown.classList.toggle('show');
            userProfileBtn.setAttribute('aria-expanded', dropdown.classList.contains('show'));
        });

        // Close on outside click
        document.addEventListener('click', (e) => {
            if (!dropdown.contains(e.target) && !userProfileBtn.contains(e.target)) {
                dropdown.classList.remove('show');
                userProfileBtn.setAttribute('aria-expanded', 'false');
            }
        });
    }

    // Dropdown Items
    const viewProfileBtn = document.getElementById('dropdownViewProfile');
    const editProfileBtn = document.getElementById('dropdownEditProfile');
    const settingsBtn = document.getElementById('dropdownSettings');
    const logoutBtn = document.getElementById('dropdownLogout');

    if (viewProfileBtn) {
        viewProfileBtn.onclick = () => {
            dropdown.classList.remove('show');
            switchView('profile');
        };
    }

    if (editProfileBtn) {
        editProfileBtn.onclick = () => {
            dropdown.classList.remove('show');
            openProfileEditModal();
        };
    }

    if (settingsBtn) {
        settingsBtn.onclick = () => {
            dropdown.classList.remove('show');
            if (authState.role === 'admin') {
                switchView('settings');
            } else {
                switchView('profile');
            }
        };
    }

    if (logoutBtn) {
        logoutBtn.onclick = handleLogout;
    }
}

function initProfileEditing() {
    const openEditBtn = document.getElementById('openEditProfilePageBtn');
    const modal = document.getElementById('profileEditModalOverlay');
    const closeBtn = document.getElementById('closeProfileModalBtn');
    const cancelBtn = document.getElementById('cancelProfileEditBtn');
    const form = document.getElementById('profileEditForm');

    if (openEditBtn) {
        openEditBtn.onclick = openProfileEditModal;
    }

    const closeModal = () => modal.classList.remove('show');
    if (closeBtn) closeBtn.onclick = closeModal;
    if (cancelBtn) cancelBtn.onclick = closeModal;

    // Avatar Presets Click Handler
    const presetGrid = document.getElementById('avatarPresetsGrid');
    if (presetGrid) {
        presetGrid.querySelectorAll('.avatar-preset').forEach(img => {
            img.onclick = () => {
                document.getElementById('editProfileImage').value = img.src;
                presetGrid.querySelectorAll('.avatar-preset').forEach(p => p.classList.remove('active'));
                img.classList.add('active');
            };
        });
    }

    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const submitBtn = document.getElementById('saveProfileEditBtn');
            submitBtn.disabled = true;
            submitBtn.textContent = 'Saving...';

            const name = document.getElementById('editProfileName').value.trim();
            const regNo = document.getElementById('editProfileRegisterNo').value.trim();
            const phone = document.getElementById('editProfilePhone').value.trim();
            const profileImage = document.getElementById('editProfileImage').value.trim();

            try {
                const res = await fetch('/api/auth/profile', {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${authState.token}`
                    },
                    body: JSON.stringify({
                        name,
                        register_number: regNo,
                        student_id: regNo,
                        phone,
                        profile_image: profileImage
                    })
                });

                if (!res.ok) throw new Error('Failed to update profile');

                const updated = await res.json();
                authState.user = updated;
                updateProfileUI();
                closeModal();
                showToast('Profile updated successfully!');
            } catch (err) {
                showToast(err.message || 'Error updating profile', 'error');
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Save Changes';
            }
        });
    }
}

function openProfileEditModal() {
    const modal = document.getElementById('profileEditModalOverlay');
    if (!modal || !authState.user) return;

    document.getElementById('editProfileName').value = authState.user.name || '';
    document.getElementById('editProfileRegisterNo').value = authState.user.register_number || authState.user.student_id || '';
    document.getElementById('editProfilePhone').value = authState.user.phone || '';
    document.getElementById('editProfileImage').value = authState.user.profile_image || '';

    modal.classList.add('show');
}

function loadUserProfileStats() {
    if (!authState.user) return;
    updateProfileUI();

    // Calculate user's order stats from genuine persisted orders
    const userOrders = (state.orders || []).filter(o =>
        (authState.user.authgear_user_id && o.authgear_user_id === authState.user.authgear_user_id) ||
        (authState.user.register_number && o.student_id === authState.user.register_number)
    );

    const totalSpent = userOrders.reduce((sum, o) => sum + (Number(o.total_amount) || 0), 0);

    const orderStat = document.getElementById('userStatOrders');
    const spentStat = document.getElementById('userStatSpent');
    const revStat = document.getElementById('userStatReviews');

    if (orderStat) orderStat.textContent = userOrders.length;
    if (spentStat) spentStat.textContent = `₹${Math.round(totalSpent)}`;
    if (revStat) {
        const revList = Array.isArray(state.reviewsData?.reviews) ? state.reviewsData.reviews : (Array.isArray(state.reviewsData) ? state.reviewsData : []);
        const userReviews = revList.filter(r =>
            (authState.user.authgear_user_id && r.authgear_user_id === authState.user.authgear_user_id) ||
            r.student_name === authState.user.name ||
            (authState.user.register_number && r.student_id === authState.user.register_number)
        );
        revStat.textContent = userReviews.length;
    }
}


// ==============================================================================
// MENU MANAGEMENT & RENDERING
// ==============================================================================
async function fetchMenu() {
    try {
        const res = await fetch('/api/menu');
        if (!res.ok) throw new Error('Failed to fetch menu');
        state.menuItems = await res.json();
        buildCategories();
        renderCategoryCarousel();
        renderFoodGrid();
    } catch (err) {
        console.error('Error fetching menu:', err);
        showToast('Unable to load menu. Please check your connection.', 'error');
    }
}

function buildCategories() {
    const categoryCounts = {};
    state.menuItems.forEach(item => {
        const cat = item.category || 'General';
        categoryCounts[cat] = (categoryCounts[cat] || 0) + 1;
    });

    state.categories = Object.keys(categoryCounts).map(cat => ({
        name: cat,
        count: categoryCounts[cat],
        thumb: CATEGORY_THUMBS[cat] || DEFAULT_FOOD_IMG
    }));
}

function renderCategoryCarousel() {
    const carousel = document.getElementById('categoryCarousel');
    if (!carousel) return;

    let html = `
        <div class="category-card ${state.selectedCategory === 'all' ? 'active' : ''}" data-cat="all">
            <img src="${CATEGORY_THUMBS['All']}" alt="All Items" class="category-thumb" onerror="this.onerror=null; this.src='${DEFAULT_FOOD_IMG}';">
            <div class="category-meta">
                <h4>All Items</h4>
                <span>${state.menuItems.length} items</span>
            </div>
        </div>
    `;

    state.categories.forEach(cat => {
        const isActive = state.selectedCategory.toLowerCase() === cat.name.toLowerCase();
        html += `
            <div class="category-card ${isActive ? 'active' : ''}" data-cat="${cat.name}">
                <img src="${cat.thumb}" alt="${cat.name}" class="category-thumb" onerror="this.onerror=null; this.src='${DEFAULT_FOOD_IMG}';">
                <div class="category-meta">
                    <h4>${cat.name}</h4>
                    <span>${cat.count} items</span>
                </div>
            </div>
        `;
    });

    carousel.innerHTML = html;

    carousel.querySelectorAll('.category-card').forEach(card => {
        card.addEventListener('click', () => {
            const cat = card.getAttribute('data-cat');
            state.selectedCategory = cat;
            renderCategoryCarousel();
            renderFoodGrid();
        });
    });
}

function renderFoodGrid() {
    const foodGrid = document.getElementById('foodGrid');
    const emptyState = document.getElementById('menuEmptyState');
    const countTag = document.getElementById('itemsCountTag');
    const categoryTitle = document.getElementById('currentCategoryTitle');

    if (!foodGrid) return;

    // Filter items
    let filtered = state.menuItems.filter(item => {
        const matchesCategory = state.selectedCategory === 'all' ||
            (item.category && item.category.toLowerCase() === state.selectedCategory.toLowerCase());

        const q = state.searchQuery.toLowerCase().trim();
        const matchesSearch = !q ||
            (item.name && item.name.toLowerCase().includes(q)) ||
            (item.category && item.category.toLowerCase().includes(q)) ||
            (item.description && item.description.toLowerCase().includes(q));

        return matchesCategory && matchesSearch;
    });

    // Sort items
    filtered.sort((a, b) => {
        if (state.sortBy === 'price_asc') return a.price - b.price;
        if (state.sortBy === 'price_desc') return b.price - a.price;
        if (state.sortBy === 'rating_asc') return (a.rating || 4.5) - (b.rating || 4.5);
        if (state.sortBy === 'popularity') return (b.order_count || 0) - (a.order_count || 0);
        return (b.rating || 4.5) - (a.rating || 4.5);
    });

    if (categoryTitle) {
        categoryTitle.textContent = state.selectedCategory === 'all' ? 'All Items' : state.selectedCategory;
    }
    if (countTag) {
        countTag.textContent = `${filtered.length} items found`;
    }

    if (filtered.length === 0) {
        foodGrid.innerHTML = '';
        emptyState.style.display = 'block';
        return;
    }

    emptyState.style.display = 'none';

    foodGrid.innerHTML = filtered.map(item => {
        const cartEntry = state.cart.find(c => c._id === item._id);
        const qtyInCart = cartEntry ? cartEntry.quantity : 0;
        const ratingScore = item.rating ? Number(item.rating).toFixed(1) : '4.7';
        const ratingsCount = item.ratings_count || 32;
        const orderCount = item.order_count || 45;
        const imgSrc = getMenuItemImage(item);
        const isOutOfStock = !item.available;

        let actionHtml = '';

        if (authState.role === 'student') {
            if (isOutOfStock) {
                actionHtml = `<span class="badge-stock" style="position:static;">Unavailable</span>`;
            } else if (qtyInCart > 0) {
                actionHtml = `
                    <div class="tray-qty-stepper">
                        <button class="qty-step-btn" onclick="updateItemQuantity('${item._id}', -1)">-</button>
                        <span class="qty-val-num">${qtyInCart}</span>
                        <button class="qty-step-btn" onclick="updateItemQuantity('${item._id}', 1)">+</button>
                    </div>
                `;
            } else {
                actionHtml = `
                    <button class="btn-add-tray" onclick="addItemToTray('${item._id}')">
                        Add to Cart
                    </button>
                `;
            }
        } else {
            // Admin Actions
            actionHtml = `
                <div class="admin-card-actions">
                    <label class="switch-label" title="Toggle Available">
                        <input type="checkbox" ${item.available ? 'checked' : ''} onchange="toggleItemAvailability('${item._id}', this.checked)">
                        <span class="switch-slider" style="width:34px;height:18px;"></span>
                    </label>
                    <button class="icon-action-btn" title="Edit Item" onclick="openEditMenuModal('${item._id}')">
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>
                    </button>
                    <button class="icon-action-btn btn-delete" title="Delete Item" onclick="confirmDeleteItem('${item._id}')">
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                    </button>
                </div>
            `;
        }

        return `
            <div class="food-card ${isOutOfStock ? 'out-of-stock' : ''}" id="card-${item._id}">
                <div class="card-img-wrap">
                    <img src="${imgSrc}" alt="${escapeHtml(item.name)}" class="food-img" loading="lazy" onerror="this.onerror=null; this.src='${DEFAULT_FOOD_IMG}';">
                    ${item.bestseller ? '<span class="badge-bestseller">BESTSELLER</span>' : ''}
                    ${isOutOfStock ? '<span class="badge-stock">Out of Stock</span>' : ''}
                </div>
                <div class="food-card-body">
                    <h4 class="food-card-title">${item.name}</h4>
                    <div class="food-card-rating">
                        <span class="rating-stars">★★★★★</span>
                        <span class="rating-score">${ratingScore}</span>
                        <span class="rating-meta">(${ratingsCount} reviews | ${orderCount} served)</span>
                    </div>
                    <p class="food-card-desc">${item.description || 'Delicious campus specialty prepared fresh upon order.'}</p>
                    <div class="food-card-footer">
                        <span class="food-price">₹${item.price}</span>
                        ${actionHtml}
                    </div>
                </div>
            </div>
        `;
    }).join('');
}


// ==============================================================================
// SEARCH & SORT CONTROLS
// ==============================================================================
function initSearch() {
    const searchInput = document.getElementById('globalSearchInput');
    const clearBtn = document.getElementById('clearSearchBtn');
    const sortSelect = document.getElementById('sortSelect');
    const resetFiltersBtn = document.getElementById('resetFiltersBtn');

    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            state.searchQuery = e.target.value;
            clearBtn.style.display = state.searchQuery ? 'block' : 'none';
            renderFoodGrid();
        });
    }

    if (clearBtn) {
        clearBtn.addEventListener('click', () => {
            searchInput.value = '';
            state.searchQuery = '';
            clearBtn.style.display = 'none';
            renderFoodGrid();
        });
    }

    if (sortSelect) {
        sortSelect.addEventListener('change', (e) => {
            state.sortBy = e.target.value;
            renderFoodGrid();
        });
    }

    if (resetFiltersBtn) {
        resetFiltersBtn.addEventListener('click', () => {
            state.selectedCategory = 'all';
            state.searchQuery = '';
            if (searchInput) searchInput.value = '';
            if (clearBtn) clearBtn.style.display = 'none';
            renderCategoryCarousel();
            renderFoodGrid();
        });
    }
}


// ==============================================================================
// CART & STUDENT ORDERING
// ==============================================================================
function initCartDrawer() {
    const openBtn = document.getElementById('openCartBtn');
    const closeBtn = document.getElementById('closeCartBtn');
    const overlay = document.getElementById('cartOverlay');
    const drawer = document.getElementById('cartDrawer');
    const placeOrderBtn = document.getElementById('placeOrderSubmitBtn');

    const toggleCart = (open) => {
        drawer.classList.toggle('show', open);
        overlay.classList.toggle('show', open);
    };

    if (openBtn) openBtn.addEventListener('click', () => toggleCart(true));
    if (closeBtn) closeBtn.addEventListener('click', () => toggleCart(false));
    if (overlay) overlay.addEventListener('click', () => toggleCart(false));

    // Pickup time chips
    const timeChips = document.querySelectorAll('.pickup-time-chips .pickup-chip');
    const customPickupInput = document.getElementById('cartCustomPickup');

    timeChips.forEach(chip => {
        chip.addEventListener('click', () => {
            timeChips.forEach(c => c.classList.remove('active'));
            chip.classList.add('active');
            const timeVal = chip.getAttribute('data-time');

            if (timeVal === 'Custom') {
                customPickupInput.style.display = 'block';
                customPickupInput.focus();
                state.selectedPickupTime = customPickupInput.value || 'Custom';
            } else {
                customPickupInput.style.display = 'none';
                state.selectedPickupTime = timeVal;
            }
        });
    });

    if (customPickupInput) {
        customPickupInput.addEventListener('input', (e) => {
            state.selectedPickupTime = e.target.value.trim() || 'Custom';
        });
    }

    if (placeOrderBtn) {
        placeOrderBtn.addEventListener('click', handlePlaceOrder);
    }

    renderCartUI();
}

function addItemToTray(itemId) {
    const item = state.menuItems.find(m => m._id === itemId);
    if (!item) return;

    const existing = state.cart.find(c => c._id === itemId);
    if (existing) {
        existing.quantity += 1;
    } else {
        state.cart.push({
            _id: item._id,
            name: item.name,
            price: item.price,
            quantity: 1,
            image_url: getMenuItemImage(item)
        });
    }

    saveCart();
    renderCartUI();
    renderFoodGrid();
    showToast(`Added ${item.name} to tray!`);
}

function updateItemQuantity(itemId, delta) {
    const existingIndex = state.cart.findIndex(c => c._id === itemId);
    if (existingIndex === -1) return;

    state.cart[existingIndex].quantity += delta;
    if (state.cart[existingIndex].quantity <= 0) {
        state.cart.splice(existingIndex, 1);
    }

    saveCart();
    renderCartUI();
    renderFoodGrid();
}

function saveCart() {
    localStorage.setItem('ge_cart', JSON.stringify(state.cart));
}

function renderCartUI() {
    const container = document.getElementById('cartItemsContainer');
    const emptyState = document.getElementById('cartEmptyState');
    const orderForm = document.getElementById('cartOrderForm');
    const countBadge = document.getElementById('cartCountBadge');
    const totalBadge = document.getElementById('cartTotalBadge');
    const billSubtotal = document.getElementById('billSubtotal');
    const billTotal = document.getElementById('billTotal');

    const totalQty = state.cart.reduce((sum, item) => sum + item.quantity, 0);
    const subtotal = state.cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);

    if (countBadge) countBadge.textContent = `${totalQty} Item${totalQty === 1 ? '' : 's'}`;
    if (totalBadge) totalBadge.textContent = `₹${subtotal}`;
    if (billSubtotal) billSubtotal.textContent = `₹${subtotal}`;
    if (billTotal) billTotal.textContent = `₹${subtotal}`;

    if (!container) return;

    if (state.cart.length === 0) {
        container.innerHTML = '';
        emptyState.style.display = 'block';
        orderForm.style.display = 'none';
        return;
    }

    emptyState.style.display = 'none';
    orderForm.style.display = 'block';

    container.innerHTML = state.cart.map(item => `
        <div class="cart-item-row">
            <img src="${item.image_url || getMenuItemImage(item)}" alt="${escapeHtml(item.name)}" class="cart-item-thumb" onerror="this.onerror=null; this.src='${DEFAULT_FOOD_IMG}';">
            <div class="cart-item-details">
                <h4>${item.name}</h4>
                <span>₹${item.price} each</span>
            </div>
            <div class="tray-qty-stepper">
                <button class="qty-step-btn" onclick="updateItemQuantity('${item._id}', -1)">-</button>
                <span class="qty-val-num">${item.quantity}</span>
                <button class="qty-step-btn" onclick="updateItemQuantity('${item._id}', 1)">+</button>
            </div>
            <span class="cart-item-price">₹${item.price * item.quantity}</span>
        </div>
    `).join('');

    const queueTitle = document.getElementById('cartQueueTitle');
    const queueDesc = document.getElementById('cartQueueDesc');
    if (queueTitle) queueTitle.textContent = `Queue: ${state.queueData.queue_status}`;
    if (queueDesc) queueDesc.textContent = state.queueData.estimated_wait;
}

async function handlePlaceOrder() {
    if (state.cart.length === 0) {
        showToast('Please add items to your cart first.', 'error');
        return;
    }

    const studentNameInput = document.getElementById('cartStudentName');
    const studentIdInput = document.getElementById('cartStudentId');
    const studentName = studentNameInput?.value.trim() || authState.user?.name;
    const studentId = studentIdInput?.value.trim() || authState.user?.register_number;

    if (!studentName || !studentId) {
        showToast('Please enter both your Student Name and Student ID.', 'error');
        return;
    }

    const subtotal = state.cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    const orderItems = state.cart.map(item => ({
        name: item.name,
        quantity: item.quantity,
        price: item.price
    }));

    const placeOrderBtn = document.getElementById('placeOrderSubmitBtn');
    placeOrderBtn.disabled = true;
    placeOrderBtn.textContent = 'Placing Order...';

    try {
        const headers = { 'Content-Type': 'application/json' };
        if (authState.token) {
            headers['Authorization'] = `Bearer ${authState.token}`;
        }

        const res = await fetch('/api/orders', {
            method: 'POST',
            headers,
            body: JSON.stringify({
                student_name: studentName,
                student_id: studentId,
                items: orderItems,
                total_amount: subtotal,
                pickup_time: state.selectedPickupTime
            })
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Failed to place order');

        state.cart = [];
        saveCart();
        renderCartUI();
        renderFoodGrid();

        document.getElementById('cartDrawer').classList.remove('show');
        document.getElementById('cartOverlay').classList.remove('show');

        showOrderSuccessModal(data.id, state.selectedPickupTime, subtotal);

        fetchOrders();
        fetchQueueStatus();
        fetchNotifications();
    } catch (err) {
        console.error('Order error:', err);
        showToast(err.message || 'Error placing order. Please try again.', 'error');
    } finally {
        placeOrderBtn.disabled = false;
        placeOrderBtn.innerHTML = `<span>Confirm & Place Order</span><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="9 18 15 12 9 6"></polyline></svg>`;
    }
}

function showOrderSuccessModal(orderId, pickupTime, total) {
    const modal = document.getElementById('orderSuccessModal');
    const orderRef = document.getElementById('receiptOrderId');
    const pickupDisplay = document.getElementById('receiptPickupTime');
    const queueBadge = document.getElementById('receiptQueueStatus');
    const totalDisplay = document.getElementById('receiptTotalAmount');

    if (orderRef) orderRef.textContent = `#GE-${orderId.slice(-6).toUpperCase()}`;
    if (pickupDisplay) pickupDisplay.textContent = pickupTime;
    if (queueBadge) queueBadge.textContent = `${state.queueData.queue_status} (${state.queueData.estimated_wait})`;
    if (totalDisplay) totalDisplay.textContent = `₹${total}`;

    modal.classList.add('show');

    document.getElementById('viewPlacedOrderBtn').onclick = () => {
        modal.classList.remove('show');
        switchView('orders');
    };

    document.getElementById('closeReceiptBtn').onclick = () => {
        modal.classList.remove('show');
    };
}


// ==============================================================================
// ORDERS MANAGEMENT VIEW
// ==============================================================================
async function fetchOrders() {
    try {
        const headers = {};
        if (authState.token) {
            headers['Authorization'] = `Bearer ${authState.token}`;
        }

        const res = await fetch('/api/orders', { headers });
        if (!res.ok) throw new Error('Failed to fetch orders');
        state.orders = await res.json();

        const badge = document.getElementById('sidebarOrdersBadge');
        if (badge) badge.textContent = state.orders.length;

        if (state.currentView === 'orders') renderOrdersTable();
        if (state.currentView === 'delivery') loadSmartQueueKanban();
        if (state.currentView === 'profile') loadUserProfileStats();
    } catch (err) {
        console.error('Error fetching orders:', err);
    }
}

function renderOrdersTable() {
    const tbody = document.getElementById('ordersTableBody');
    const emptyState = document.getElementById('ordersEmptyState');
    if (!tbody) return;

    const filterChips = document.querySelectorAll('#orderStatusFilters .filter-chip');
    filterChips.forEach(chip => {
        chip.onclick = () => {
            filterChips.forEach(c => c.classList.remove('active'));
            chip.classList.add('active');
            state.orderFilter = chip.getAttribute('data-filter');
            renderOrdersTable();
        };
    });

    let filtered = state.orders;
    if (state.orderFilter !== 'All') {
        filtered = filtered.filter(o => o.status === state.orderFilter);
    }

    if (filtered.length === 0) {
        tbody.innerHTML = '';
        emptyState.style.display = 'block';
        return;
    }

    emptyState.style.display = 'none';

    tbody.innerHTML = filtered.map(order => {
        const itemsSummary = (order.items || []).map(i => `${i.quantity}x ${i.name}`).join(', ');
        const orderShortId = `#GE-${(order._id || '').slice(-6).toUpperCase()}`;

        // Only Admin can change order status; Student views status badge with cancel option if 'Placed'
        let statusActionHtml = '';
        if (authState.role === 'admin') {
            statusActionHtml = `
                <select class="table-status-select" onchange="updateOrderStatus('${order._id}', this.value)">
                    <option value="Placed" ${order.status === 'Placed' ? 'selected' : ''}>Placed</option>
                    <option value="Preparing" ${order.status === 'Preparing' ? 'selected' : ''}>Preparing</option>
                    <option value="Ready" ${order.status === 'Ready' ? 'selected' : ''}>Ready</option>
                    <option value="Completed" ${order.status === 'Completed' ? 'selected' : ''}>Completed</option>
                    <option value="Cancelled" ${order.status === 'Cancelled' ? 'selected' : ''}>Cancelled</option>
                </select>
            `;
        } else if (order.status === 'Placed') {
            statusActionHtml = `<button class="btn-cancel-order" style="padding: 4px 10px; font-size: 11px; background: #ef4444; color: white; border: none; border-radius: var(--radius-sm); font-weight: 600; cursor: pointer;" onclick="updateOrderStatus('${order._id}', 'Cancelled')">Cancel</button>`;
        } else {
            statusActionHtml = `<span style="color: var(--text-muted); font-size: 12px;">—</span>`;
        }

        return `
            <tr>
                <td><span class="order-id-badge">${orderShortId}</span></td>
                <td>
                    <strong>${escapeHtml(order.student_name || 'Student')}</strong><br>
                    <small style="color:var(--text-muted);">${escapeHtml(order.student_id || '')}</small>
                </td>
                <td><div class="order-items-snippet" title="${escapeHtml(itemsSummary)}">${escapeHtml(itemsSummary) || '1x Meal'}</div></td>
                <td><strong>₹${order.total_amount || 0}</strong></td>
                <td>${escapeHtml(order.pickup_time || 'Immediate')}</td>
                <td><span class="status-badge status-${order.status}">${order.status}</span></td>
                <td>${statusActionHtml}</td>
            </tr>
        `;
    }).join('');
}

async function updateOrderStatus(orderId, newStatus) {
    try {
        const headers = { 'Content-Type': 'application/json' };
        if (authState.token) {
            headers['Authorization'] = `Bearer ${authState.token}`;
        }

        const res = await fetch(`/api/orders/${orderId}`, {
            method: 'PUT',
            headers,
            body: JSON.stringify({ status: newStatus })
        });

        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.error || 'Failed to update status');
        }

        showToast(`Order status updated to ${newStatus}`);
        fetchOrders();
        fetchQueueStatus();
        fetchNotifications();
    } catch (err) {
        showToast(err.message || 'Error updating order status', 'error');
    }
}


// ==============================================================================
// SMART QUEUE KANBAN
// ==============================================================================
async function fetchQueueStatus() {
    try {
        const res = await fetch('/api/queue');
        if (!res.ok) return;
        state.queueData = await res.json();

        // Update sidebar queue widget
        const widgetText = document.getElementById('sidebarQueueText');
        const waitText = document.getElementById('sidebarWaitText');
        const dot = document.getElementById('queueStatusDot');

        if (widgetText) widgetText.textContent = `${state.queueData.queue_status} (${state.queueData.active_orders} Active)`;
        if (waitText) waitText.textContent = state.queueData.estimated_wait;

        if (dot) {
            dot.className = 'queue-status-dot';
            if (state.queueData.queue_status === 'Low') dot.classList.add('pulse-low');
            else if (state.queueData.queue_status === 'Moderate') dot.classList.add('pulse-moderate');
            else dot.classList.add('pulse-high');
        }

        // Live stats in cart drawer
        const cartQTitle = document.getElementById('cartQueueTitle');
        const cartQDesc = document.getElementById('cartQueueDesc');
        if (cartQTitle) cartQTitle.textContent = `Queue: ${state.queueData.queue_status}`;
        if (cartQDesc) cartQDesc.textContent = state.queueData.estimated_wait;

        if (state.currentView === 'delivery') loadSmartQueueKanban();
    } catch (err) {
        console.error('Error fetching queue status:', err);
    }
}

function loadSmartQueueKanban() {
    const placedCol = document.getElementById('cards-placed');
    const prepCol = document.getElementById('cards-preparing');
    const readyCol = document.getElementById('cards-ready');
    const compCol = document.getElementById('cards-completed');

    if (!placedCol || !prepCol || !readyCol) return;

    const ordersList = state.orders || [];
    const placed = ordersList.filter(o => o.status === 'Placed');
    const prep = ordersList.filter(o => o.status === 'Preparing');
    const ready = ordersList.filter(o => o.status === 'Ready');
    const comp = ordersList.filter(o => o.status === 'Completed');

    const cPlaced = document.getElementById('count-placed');
    const cPrep = document.getElementById('count-preparing');
    const cReady = document.getElementById('count-ready');
    const cComp = document.getElementById('count-completed');

    if (cPlaced) cPlaced.textContent = placed.length;
    if (cPrep) cPrep.textContent = prep.length;
    if (cReady) cReady.textContent = ready.length;
    if (cComp) cComp.textContent = comp.length;

    // Update Live Queue Condition Banner
    const activeCount = placed.length + prep.length;
    const activeVal = document.getElementById('queueActiveVal');
    const placedVal = document.getElementById('queuePlacedVal');
    const prepVal = document.getElementById('queuePreparingVal');
    const readyVal = document.getElementById('queueReadyVal');
    const condPill = document.getElementById('queueConditionPill');
    const condTitle = document.getElementById('queueConditionTitle');
    const condDesc = document.getElementById('queueConditionDesc');
    const progBar = document.getElementById('queueProgressBar');

    if (activeVal) activeVal.textContent = state.queueData?.active_orders ?? activeCount;
    if (placedVal) placedVal.textContent = state.queueData?.placed_orders ?? placed.length;
    if (prepVal) prepVal.textContent = state.queueData?.preparing_orders ?? prep.length;
    if (readyVal) readyVal.textContent = state.queueData?.ready_orders ?? ready.length;

    const qStatus = state.queueData?.queue_status || (activeCount > 15 ? 'High' : (activeCount > 5 ? 'Moderate' : 'Low'));
    const estWait = state.queueData?.estimated_wait || (activeCount === 0 ? 'No queue - Ready in 5-10 mins' : `${5 + activeCount * 2} mins`);

    if (condPill) condPill.textContent = `Queue: ${qStatus}`;
    if (condTitle) condTitle.textContent = `${qStatus} Campus Flow (~${estWait})`;
    if (condDesc) {
        if (qStatus === 'Low') condDesc.textContent = 'Kitchen is operating smoothly. Fast order turnaround!';
        else if (qStatus === 'Moderate') condDesc.textContent = 'Moderate campus rush. Orders are being prepped steadily.';
        else condDesc.textContent = 'Peak canteen rush hour. Kitchen is at maximum capacity!';
    }
    if (progBar) {
        const pct = Math.min(100, Math.max(15, (activeCount / (state.queueData?.moderate_threshold || 15)) * 100));
        progBar.style.width = `${pct}%`;
    }

    const renderCard = (order, targetStatus, nextBtnLabel) => {
        const itemsList = (order.items || []).map(i => `${i.quantity}x ${i.name}`).join(', ');
        const shortId = `#GE-${(order._id || '').slice(-6).toUpperCase()}`;

        let nextActionHtml = '';
        if (authState.role === 'admin' && nextBtnLabel) {
            nextActionHtml = `<button class="btn-advance-status" onclick="updateOrderStatus('${order._id}', '${targetStatus}')">${nextBtnLabel} &rarr;</button>`;
        } else if (authState.role === 'student' && order.status === 'Placed') {
            nextActionHtml = `<button class="btn-advance-status" style="background:#ef4444;" onclick="updateOrderStatus('${order._id}', 'Cancelled')">Cancel</button>`;
        } else {
            nextActionHtml = `<span class="badge" style="font-size:11px;">${order.status}</span>`;
        }

        return `
            <div class="kanban-card">
                <div class="kanban-card-head">
                    <strong>${shortId}</strong>
                    <small>${escapeHtml(order.pickup_time || 'Immediate')}</small>
                </div>
                <div class="kanban-student-title">${escapeHtml(order.student_name || 'Student')}</div>
                <div class="kanban-items-list">${escapeHtml(itemsList || '1x Canteen Item')}</div>
                <div class="kanban-card-foot">
                    <strong>₹${order.total_amount || 0}</strong>
                    ${nextActionHtml}
                </div>
            </div>
        `;
    };

    const emptyHtml = (msg) => `<div style="padding: 24px 12px; font-size: 13px; color: var(--text-muted); text-align: center;">${msg}</div>`;

    placedCol.innerHTML = placed.length ? placed.map(o => renderCard(o, 'Preparing', 'Start Cooking')).join('') : emptyHtml('No placed orders');
    prepCol.innerHTML = prep.length ? prep.map(o => renderCard(o, 'Ready', 'Mark Ready')).join('') : emptyHtml('No orders preparing');
    readyCol.innerHTML = ready.length ? ready.map(o => renderCard(o, 'Completed', 'Complete')).join('') : emptyHtml('No orders ready for pickup');
    if (compCol) {
        compCol.innerHTML = comp.length ? comp.slice(0, 10).map(o => renderCard(o, null, null)).join('') : emptyHtml('No completed orders');
    }
}


// ==============================================================================
// DASHBOARD OVERVIEW & ANALYTICS (Admin)
// ==============================================================================
async function loadOverviewDashboard() {
    if (authState.role !== 'admin') return;

    try {
        const headers = { 'Authorization': `Bearer ${authState.token}` };
        const res = await fetch('/api/dashboard/stats', { headers });
        if (!res.ok) return;
        const stats = await res.json();

        document.getElementById('statTotalOrders').textContent = stats.total_orders;
        document.getElementById('statActiveOrders').textContent = stats.active_orders;
        document.getElementById('statReadyOrders').textContent = stats.ready_orders;
        document.getElementById('statTotalRevenue').textContent = `₹${stats.total_revenue}`;
        document.getElementById('statAvailableItems').textContent = stats.available_menu_items;
        document.getElementById('statTotalMenuItems').textContent = `${stats.total_menu_items} total items`;
        document.getElementById('statAvgRating').textContent = `${stats.average_rating} ★`;
        document.getElementById('statTotalReviews').textContent = `${stats.total_reviews} campus reviews`;

        loadOrdersSummaryBars();
        loadPopularItemsList();
    } catch (err) {
        console.error('Error loading dashboard:', err);
    }
}

async function loadOrdersSummaryBars() {
    try {
        const headers = { 'Authorization': `Bearer ${authState.token}` };
        const res = await fetch('/api/dashboard/orders-summary', { headers });
        if (!res.ok) return;
        const summary = await res.json();
        const container = document.getElementById('statusSummaryContainer');
        if (!container) return;

        const total = Object.values(summary).reduce((a, b) => a + b, 0) || 1;
        const statuses = ['Placed', 'Preparing', 'Ready', 'Completed', 'Cancelled'];

        container.innerHTML = statuses.map(s => {
            const count = summary[s] || 0;
            const pct = Math.round((count / total) * 100);
            return `
                <div class="summary-bar-row">
                    <div class="summary-bar-header">
                        <span class="status-badge status-${s}">${s}</span>
                        <span class="summary-count">${count} (${pct}%)</span>
                    </div>
                    <div class="summary-bar-track">
                        <div class="summary-bar-fill fill-${s.toLowerCase()}" style="width: ${pct}%;"></div>
                    </div>
                </div>
            `;
        }).join('');
    } catch (err) {
        console.error('Error loading orders summary:', err);
    }
}

async function loadPopularItemsList() {
    try {
        const headers = { 'Authorization': `Bearer ${authState.token}` };
        const res = await fetch('/api/dashboard/popular-items', { headers });
        if (!res.ok) return;
        const items = await res.json();
        const container = document.getElementById('popularItemsContainer');
        if (!container) return;

        container.innerHTML = items.map((item, idx) => `
            <div class="popular-item-row">
                <span class="rank-num">#${idx + 1}</span>
                <img src="${getMenuItemImage(item)}" alt="${escapeHtml(item.name)}" class="popular-thumb" onerror="this.onerror=null; this.src='${DEFAULT_FOOD_IMG}';">
                <div class="popular-meta">
                    <h4>${item.name}</h4>
                    <span>${item.category} • ₹${item.price}</span>
                </div>
                <div class="popular-stats">
                    <strong>${item.total_quantity} sold</strong>
                    <small>₹${item.total_revenue}</small>
                </div>
            </div>
        `).join('');
    } catch (err) {
        console.error('Error loading popular items:', err);
    }
}

async function loadAnalyticsView() {
    if (authState.role !== 'admin') return;

    try {
        const headers = { 'Authorization': `Bearer ${authState.token}` };
        const res = await fetch('/api/analytics', { headers });
        if (!res.ok) return;
        const data = await res.json();

        // Category breakdown
        const catContainer = document.getElementById('analyticsCategoryBars');
        if (catContainer && data.category_distribution) {
            const max = Math.max(...data.category_distribution.map(c => c.count), 1);
            catContainer.innerHTML = data.category_distribution.map(c => `
                <div class="analytics-bar-item">
                    <div class="analytics-bar-header">
                        <span>${c.category}</span>
                        <strong>${c.count} items</strong>
                    </div>
                    <div class="analytics-track">
                        <div class="analytics-fill fill-category" style="width: ${Math.round((c.count / max) * 100)}%;"></div>
                    </div>
                </div>
            `).join('');
        }

        // Status breakdown
        const statusContainer = document.getElementById('analyticsStatusBars');
        if (statusContainer && data.status_distribution) {
            const maxS = Math.max(...data.status_distribution.map(s => s.count), 1);
            statusContainer.innerHTML = data.status_distribution.map(s => `
                <div class="analytics-bar-item">
                    <div class="analytics-bar-header">
                        <span>${s.status}</span>
                        <strong>${s.count} orders</strong>
                    </div>
                    <div class="analytics-track">
                        <div class="analytics-fill fill-status" style="width: ${Math.round((s.count / maxS) * 100)}%;"></div>
                    </div>
                </div>
            `).join('');
        }

        // Pickup time slots
        const slotsContainer = document.getElementById('analyticsPickupSlots');
        if (slotsContainer && data.peak_pickup_times) {
            slotsContainer.innerHTML = data.peak_pickup_times.map(p => `
                <div class="pickup-slot-chip">
                    <span class="slot-time">${p.time}</span>
                    <span class="slot-count">${p.count} orders</span>
                </div>
            `).join('');
        }
    } catch (err) {
        console.error('Error loading analytics:', err);
    }
}


// ==============================================================================
// RATINGS & REVIEWS
// ==============================================================================
function initReviews() {
    const openBtn = document.getElementById('openAddReviewModalBtn');
    const modal = document.getElementById('reviewModalOverlay');
    const closeBtn = document.getElementById('closeReviewModalBtn');
    const cancelBtn = document.getElementById('cancelReviewModalBtn');
    const reviewForm = document.getElementById('reviewForm');
    const starPicker = document.getElementById('starRatingPicker');

    if (openBtn) {
        openBtn.addEventListener('click', () => {
            modal.classList.add('show');
            if (authState.user) {
                document.getElementById('revStudentName').value = authState.user.name;
                document.getElementById('revStudentId').value = authState.user.register_number || '';
            }
        });
    }

    const closeModal = () => modal.classList.remove('show');
    if (closeBtn) closeBtn.addEventListener('click', closeModal);
    if (cancelBtn) cancelBtn.addEventListener('click', closeModal);

    if (starPicker) {
        const stars = starPicker.querySelectorAll('.star-pick');
        const textVal = document.getElementById('selectedStarValText');
        const hiddenInput = document.getElementById('revRatingVal');
        const labels = { 1: '1.0 / 5.0 (Poor)', 2: '2.0 / 5.0 (Fair)', 3: '3.0 / 5.0 (Good)', 4: '4.0 / 5.0 (Very Good)', 5: '5.0 / 5.0 (Excellent)' };

        stars.forEach(star => {
            star.addEventListener('click', () => {
                const val = parseInt(star.getAttribute('data-val'), 10);
                state.reviewRatingVal = val;
                hiddenInput.value = val;
                textVal.textContent = labels[val];

                stars.forEach(s => {
                    const sVal = parseInt(s.getAttribute('data-val'), 10);
                    s.classList.toggle('active', sVal <= val);
                });
            });
        });
    }

    if (reviewForm) {
        reviewForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const submitBtn = document.getElementById('submitReviewBtn');
            submitBtn.disabled = true;

            const name = document.getElementById('revStudentName').value.trim();
            const sid = document.getElementById('revStudentId').value.trim();
            const item = document.getElementById('revItemName').value.trim();
            const comment = document.getElementById('revComment').value.trim();
            const rating = state.reviewRatingVal;

            try {
                const headers = { 'Content-Type': 'application/json' };
                if (authState.token) {
                    headers['Authorization'] = `Bearer ${authState.token}`;
                }

                const res = await fetch('/api/reviews', {
                    method: 'POST',
                    headers,
                    body: JSON.stringify({
                        student_name: name,
                        student_id: sid,
                        menu_item_name: item,
                        rating,
                        comment
                    })
                });

                if (!res.ok) {
                    const errData = await res.json().catch(() => ({}));
                    throw new Error(errData.error || 'Failed to submit review');
                }

                showToast('Thank you for reviewing! Your feedback helps our canteen.');
                closeModal();
                reviewForm.reset();
                loadReviewsView();
            } catch (err) {
                showToast(err.message || 'Error submitting review', 'error');
            } finally {
                submitBtn.disabled = false;
            }
        });
    }
}

async function loadReviewsView() {
    try {
        const res = await fetch('/api/reviews');
        if (!res.ok) throw new Error('Failed to fetch reviews');
        state.reviewsData = await res.json();

        const avg = Number(state.reviewsData.average_rating || 0);
        const total = Number(state.reviewsData.total_reviews || 0);

        const avgScoreEl = document.getElementById('reviewAvgScore');
        const countSummaryEl = document.getElementById('reviewCountSummary');
        const starsEl = document.getElementById('reviewAvgStars');

        if (avgScoreEl) avgScoreEl.textContent = avg > 0 ? avg.toFixed(1) : '0.0';
        if (countSummaryEl) {
            countSummaryEl.textContent = total === 0
                ? 'No campus reviews yet'
                : (total === 1 ? 'Based on 1 campus review' : `Based on ${total} campus reviews`);
        }
        if (starsEl) {
            const rounded = Math.round(avg);
            starsEl.textContent = '★'.repeat(rounded) + '☆'.repeat(Math.max(0, 5 - rounded));
        }

        const breakdownContainer = document.getElementById('ratingBreakdownContainer');
        if (breakdownContainer) {
            const dist = state.reviewsData.distribution || {};
            const totalForPct = total || 1;

            breakdownContainer.innerHTML = [5, 4, 3, 2, 1].map(stars => {
                const count = dist[stars] || 0;
                const pct = total === 0 ? 0 : Math.round((count / totalForPct) * 100);
                return `
                    <div class="star-break-row">
                        <span style="width:50px;">${stars} Stars</span>
                        <div class="star-break-track">
                            <div class="star-break-fill" style="width: ${pct}%;"></div>
                        </div>
                        <span style="width:30px; text-align:right;">${count}</span>
                    </div>
                `;
            }).join('');
        }

        const grid = document.getElementById('reviewsGrid');
        if (grid) {
            const revList = state.reviewsData.reviews || [];
            if (revList.length === 0) {
                grid.innerHTML = '<p class="empty-state" style="padding: 24px; text-align: center; color: var(--text-muted); width: 100%;">No student reviews yet. Be the first to review a meal!</p>';
                return;
            }

            grid.innerHTML = revList.map(r => `
                <div class="review-card">
                    <div class="review-header">
                        <div class="review-author">
                            <h4>${escapeHtml(r.student_name || 'Gazebo Student')}</h4>
                            <small>${escapeHtml(r.student_id || 'Campus Student')}</small>
                        </div>
                        <div class="rating-stars">${'★'.repeat(r.rating || 5)}${'☆'.repeat(Math.max(0, 5 - (r.rating || 5)))}</div>
                    </div>
                    ${r.menu_item_name ? `<span class="review-item-tag">${escapeHtml(r.menu_item_name)}</span>` : ''}
                    <p class="review-text">${escapeHtml(r.comment || '')}</p>
                </div>
            `).join('');
        }
    } catch (err) {
        console.error('Error loading reviews:', err);
    }
}


// ==============================================================================
// SETTINGS MANAGEMENT (Admin)
// ==============================================================================
function initSettings() {
    const form = document.getElementById('settingsForm');
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = document.getElementById('saveSettingsBtn');
            btn.disabled = true;

            const payload = {
                canteen_name: document.getElementById('settingCanteenName').value.trim(),
                operating_hours: document.getElementById('settingOperatingHours').value.trim(),
                default_pickup_duration: document.getElementById('settingPickupDuration').value.trim(),
                queue_low_threshold: parseInt(document.getElementById('settingLowThreshold').value, 10),
                queue_moderate_threshold: parseInt(document.getElementById('settingModThreshold').value, 10),
                notifications_enabled: document.getElementById('settingNotifications').checked
            };

            try {
                const res = await fetch('/api/settings', {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${authState.token}`
                    },
                    body: JSON.stringify(payload)
                });

                if (!res.ok) throw new Error('Failed to save settings');

                showToast('Settings saved successfully in MongoDB!');
                fetchQueueStatus();
            } catch (err) {
                showToast(err.message || 'Error saving settings', 'error');
            } finally {
                btn.disabled = false;
            }
        });
    }
}

async function loadSettingsView() {
    try {
        const res = await fetch('/api/settings');
        if (!res.ok) throw new Error('Failed to load settings');
        const s = await res.json();

        document.getElementById('settingCanteenName').value = s.canteen_name || 'GazeboExpress';
        document.getElementById('settingOperatingHours').value = s.operating_hours || '08:30 AM - 09:30 PM';
        document.getElementById('settingPickupDuration').value = s.default_pickup_duration || '15 mins';
        document.getElementById('settingLowThreshold').value = s.queue_low_threshold || 5;
        document.getElementById('settingModThreshold').value = s.queue_moderate_threshold || 15;
        document.getElementById('settingNotifications').checked = s.notifications_enabled !== false;
    } catch (err) {
        console.error('Error loading settings:', err);
    }
}


// ==============================================================================
// NOTIFICATIONS & MODALS
// ==============================================================================
function initModals() {
    const notifBtn = document.getElementById('notificationBtn');
    const notifDropdown = document.getElementById('notificationDropdown');
    const clearNotifBtn = document.getElementById('markAllReadBtn');

    if (notifBtn && notifDropdown) {
        notifBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            notifDropdown.classList.toggle('show');
        });

        document.addEventListener('click', (e) => {
            if (!notifDropdown.contains(e.target) && !notifBtn.contains(e.target)) {
                notifDropdown.classList.remove('show');
            }
        });
    }

    if (clearNotifBtn) {
        clearNotifBtn.addEventListener('click', async () => {
            await fetch('/api/notifications/clear', { method: 'POST' });
            fetchNotifications();
        });
    }

    // Add Menu Modal
    const openAddBtn = document.getElementById('openAddMenuModalBtn');
    const menuModal = document.getElementById('menuModalOverlay');
    const closeMenuBtn = document.getElementById('closeMenuModalBtn');
    const cancelMenuBtn = document.getElementById('cancelMenuModalBtn');
    const menuForm = document.getElementById('menuItemForm');
    const imageInput = document.getElementById('itemFormImage');
    const imagePreviewWrap = document.getElementById('imagePreviewWrap');
    const imagePreview = document.getElementById('itemImagePreview');

    if (openAddBtn) {
        openAddBtn.addEventListener('click', () => {
            document.getElementById('menuModalTitle').textContent = 'Add Menu Item';
            document.getElementById('menuItemId').value = '';
            menuForm.reset();
            document.getElementById('itemFormAvailable').checked = true;
            imagePreviewWrap.style.display = 'none';
            menuModal.classList.add('show');
        });
    }

    const closeMenuModal = () => menuModal.classList.remove('show');
    if (closeMenuBtn) closeMenuBtn.addEventListener('click', closeMenuModal);
    if (cancelMenuBtn) cancelMenuBtn.addEventListener('click', closeMenuModal);

    if (imageInput) {
        imageInput.addEventListener('input', (e) => {
            const url = e.target.value.trim();
            if (url) {
                imagePreview.src = url;
                imagePreviewWrap.style.display = 'block';
            } else {
                imagePreviewWrap.style.display = 'none';
            }
        });
    }

    if (menuForm) {
        menuForm.addEventListener('submit', handleSaveMenuItem);
    }

    // Confirm Delete Modal
    const deleteModal = document.getElementById('confirmDeleteModal');
    const cancelDeleteBtn = document.getElementById('cancelDeleteBtn');
    const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');

    if (cancelDeleteBtn) {
        cancelDeleteBtn.addEventListener('click', () => deleteModal.classList.remove('show'));
    }

    if (confirmDeleteBtn) {
        confirmDeleteBtn.addEventListener('click', executeDeleteItem);
    }
}

async function fetchNotifications() {
    try {
        const res = await fetch('/api/notifications');
        if (!res.ok) return;
        const data = await res.json();
        state.notifications = data.notifications || [];
        state.unreadNotifCount = data.unread_count || 0;

        const badge = document.getElementById('notificationBadge');
        if (badge) {
            badge.textContent = state.unreadNotifCount;
            badge.style.display = state.unreadNotifCount > 0 ? 'block' : 'none';
        }

        const list = document.getElementById('notificationList');
        if (list) {
            if (state.notifications.length === 0) {
                list.innerHTML = '<p class="empty-notif">No new notifications</p>';
                return;
            }

            list.innerHTML = state.notifications.map(n => `
                <div class="notif-item ${n.read ? '' : 'unread'}">
                    <h5>${n.title}</h5>
                    <p>${n.message}</p>
                    <small>${n.created_at ? new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Just now'}</small>
                </div>
            `).join('');
        }
    } catch (err) {
        console.error('Error fetching notifications:', err);
    }
}


// ==============================================================================
// ADD, EDIT, DELETE MENU ITEMS (Admin Only with Bearer Token)
// ==============================================================================
async function handleSaveMenuItem(e) {
    e.preventDefault();
    const saveBtn = document.getElementById('saveMenuItemBtn');
    saveBtn.disabled = true;

    const itemId = document.getElementById('menuItemId').value;
    const name = document.getElementById('itemFormName').value.trim();
    const category = document.getElementById('itemFormCategory').value;
    const price = parseFloat(document.getElementById('itemFormPrice').value);
    const description = document.getElementById('itemFormDescription').value.trim();
    const image_url = document.getElementById('itemFormImage').value.trim();
    const available = document.getElementById('itemFormAvailable').checked;
    const bestseller = document.getElementById('itemFormBestseller').checked;

    const payload = {
        name,
        category,
        price,
        description,
        image_url,
        available,
        bestseller
    };

    const isEdit = !!itemId;
    const url = isEdit ? `/api/menu/${itemId}` : '/api/menu';
    const method = isEdit ? 'PUT' : 'POST';

    try {
        const headers = {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${authState.token}`
        };

        const res = await fetch(url, {
            method,
            headers,
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Failed to save menu item');

        showToast(isEdit ? 'Menu item updated successfully!' : 'Menu item created successfully!');
        document.getElementById('menuModalOverlay').classList.remove('show');
        fetchMenu();
    } catch (err) {
        showToast(err.message || 'Error saving menu item', 'error');
    } finally {
        saveBtn.disabled = false;
    }
}

function openEditMenuModal(itemId) {
    const item = state.menuItems.find(m => m._id === itemId);
    if (!item) return;

    document.getElementById('menuModalTitle').textContent = 'Edit Menu Item';
    document.getElementById('menuItemId').value = item._id;
    document.getElementById('itemFormName').value = item.name;
    document.getElementById('itemFormCategory').value = item.category;
    document.getElementById('itemFormPrice').value = item.price;
    document.getElementById('itemFormDescription').value = item.description || '';
    document.getElementById('itemFormImage').value = item.image_url || '';
    document.getElementById('itemFormAvailable').checked = item.available !== false;
    document.getElementById('itemFormBestseller').checked = !!item.bestseller;

    const previewWrap = document.getElementById('imagePreviewWrap');
    const previewImg = document.getElementById('itemImagePreview');
    const displayImg = item.image_url || getMenuItemImage(item);
    if (displayImg) {
        previewImg.src = displayImg;
        previewWrap.style.display = 'block';
    } else {
        previewWrap.style.display = 'none';
    }

    document.getElementById('menuModalOverlay').classList.add('show');
}

async function toggleItemAvailability(itemId, isAvailable) {
    try {
        const headers = {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${authState.token}`
        };

        const res = await fetch(`/api/menu/${itemId}`, {
            method: 'PUT',
            headers,
            body: JSON.stringify({ available: isAvailable })
        });

        if (!res.ok) throw new Error('Failed to update availability');

        const item = state.menuItems.find(m => m._id === itemId);
        if (item) item.available = isAvailable;

        showToast(`Item updated to ${isAvailable ? 'In Stock' : 'Out of Stock'}`);
        renderFoodGrid();
    } catch (err) {
        showToast(err.message || 'Error toggling availability', 'error');
    }
}

function confirmDeleteItem(itemId) {
    const item = state.menuItems.find(m => m._id === itemId);
    if (!item) return;

    state.itemPendingDeleteId = itemId;
    document.getElementById('deleteConfirmText').textContent = `Are you sure you want to permanently remove "${item.name}" from the campus menu?`;
    document.getElementById('confirmDeleteModal').classList.add('show');
}

async function executeDeleteItem() {
    if (!state.itemPendingDeleteId) return;

    const deleteBtn = document.getElementById('confirmDeleteBtn');
    deleteBtn.disabled = true;

    try {
        const headers = {
            'Authorization': `Bearer ${authState.token}`
        };

        const res = await fetch(`/api/menu/${state.itemPendingDeleteId}`, {
            method: 'DELETE',
            headers
        });

        if (!res.ok) throw new Error('Failed to delete item');

        showToast('Menu item removed from MongoDB.');
        document.getElementById('confirmDeleteModal').classList.remove('show');
        state.itemPendingDeleteId = null;
        fetchMenu();
    } catch (err) {
        showToast(err.message || 'Error deleting menu item', 'error');
    } finally {
        deleteBtn.disabled = false;
    }
}


// ==============================================================================
// TOAST NOTIFICATIONS
// ==============================================================================
function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <span>${type === 'success' ? '✓' : '⚠'}</span>
        <span>${message}</span>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}
