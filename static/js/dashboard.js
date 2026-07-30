// static/js/dashboard.js
// Auto-D Kenya - Dashboard JavaScript
// ================================================================

// ─── API Configuration ──────────────────────────────────────────

const API_BASE = 'https://auto-digital.onrender.com/api/v1';

// For local development, uncomment:
// const API_BASE = 'http://localhost:8000/api/v1';

// ─── DOM References ─────────────────────────────────────────────

const DOM = {
    // Stats
    statVehicles: document.getElementById('statVehicles'),
    statServices: document.getElementById('statServices'),
    statPayments: document.getElementById('statPayments'),
    statSpent: document.getElementById('statSpent'),

    // Lists
    servicesList: document.getElementById('servicesList'),
    userServicesList: document.getElementById('userServicesList'),
    paymentsList: document.getElementById('paymentsList'),

    // User
    userName: document.getElementById('userName'),
    userAvatar: document.getElementById('userAvatar'),

    // Payment Modal
    paymentModal: document.getElementById('paymentModal'),
    paymentServiceName: document.getElementById('paymentServiceName'),
    paymentAmount: document.getElementById('paymentAmount'),
    paymentTotal: document.getElementById('paymentTotal'),
    mpesaPhone: document.getElementById('mpesaPhone'),
    payNowBtn: document.getElementById('payNowBtn'),

    // Processing Modal
    processingModal: document.getElementById('processingModal'),
    processingText: document.getElementById('processingText'),
    processingDetail: document.getElementById('processingDetail'),

    // Toast
    toastContainer: document.getElementById('toastContainer'),
};

// ─── State ──────────────────────────────────────────────────────

let services = [];
let userServices = [];
let payments = [];
let selectedService = null;
let pollTimer = null;

// ─── Toast ──────────────────────────────────────────────────────

function showToast(message, type = 'info') {
    if (!DOM.toastContainer) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    DOM.toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100px)';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// ─── Auth Helpers ──────────────────────────────────────────────

function getToken() {
    return localStorage.getItem('token');
}

function isAuthenticated() {
    return !!getToken();
}

function getAuthHeaders() {
    const token = getToken();
    return {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : '',
    };
}

function redirectToLogin() {
    window.location.href = '/login.html';
}

// ─── API Calls ──────────────────────────────────────────────────

async function apiCall(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const headers = getAuthHeaders();

    const response = await fetch(url, {
        ...options,
        headers: {
            ...headers,
            ...options.headers,
        },
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.detail || data.message || `HTTP ${response.status}`);
    }

    return data;
}

async function getServices() {
    return apiCall('/mpesa/services');
}

async function getUserServices() {
    return apiCall('/mpesa/user/services');
}

async function getPayments() {
    return apiCall('/mpesa/payments');
}

async function initiatePayment(phone, serviceId, amount) {
    return apiCall('/mpesa/stkpush', {
        method: 'POST',
        body: JSON.stringify({
            phone: phone,
            service_id: serviceId,
            amount: amount,
            description: 'Auto-D Kenya Service',
        }),
    });
}

async function checkPaymentStatus(checkoutId) {
    return apiCall(`/mpesa/status/${checkoutId}`);
}

async function confirmPayment(checkoutId) {
    return apiCall(`/mpesa/confirm/${checkoutId}`, {
        method: 'POST',
    });
}

async function logout() {
    const token = getToken();
    if (token) {
        try {
            await apiCall('/logout', { method: 'POST' });
        } catch (e) {
            // Ignore
        }
    }
    localStorage.removeItem('token');
    localStorage.removeItem('user');
}

// ─── Render Functions ──────────────────────────────────────────

function renderStats(stats) {
    if (DOM.statVehicles) DOM.statVehicles.textContent = stats.vehicles || 0;
    if (DOM.statServices) DOM.statServices.textContent = stats.active_services || 0;
    if (DOM.statPayments) DOM.statPayments.textContent = stats.total_payments || 0;
    if (DOM.statSpent) DOM.statSpent.textContent = `KES ${(stats.amount_spent || 0).toLocaleString()}`;
}

function renderServices() {
    if (!DOM.servicesList) return;

    if (!services || services.length === 0) {
        DOM.servicesList.innerHTML = `
            <div class="empty-state">
                <div class="icon">⚡</div>
                <h3>No Services Available</h3>
                <p>Please check your connection.</p>
            </div>
        `;
        return;
    }

    DOM.servicesList.innerHTML = services.map(s => {
        const purchased = userServices.some(us =>
            us.service_id === s.id || us.service_id === s.code
        );
        const statusClass = purchased ? 'active' : 'locked';
        const statusText = purchased ? '✅ Purchased' : '🔒 Locked';

        return `
            <div class="service-card">
                <div class="service-icon">${s.icon || '📦'}</div>
                <div class="service-name">${s.name}</div>
                <div class="service-price">KES ${(s.price || 0).toLocaleString()}</div>
                <span class="service-status ${statusClass}">${statusText}</span>
                <div class="service-actions">
                    <button
                        class="btn ${purchased ? 'btn-success' : 'btn-primary'} btn-block btn-sm"
                        onclick="${purchased ? `openService('${s.code || s.id}')` : `openPaymentModal('${s.id}')`}"
                    >
                        ${purchased ? '🚀 Open' : '💰 Buy'}
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

function renderUserServices() {
    if (!DOM.userServicesList) return;

    if (!userServices || userServices.length === 0) {
        DOM.userServicesList.innerHTML = `
            <div class="empty-state">
                <div class="icon">🔓</div>
                <h3>No Purchased Services</h3>
                <p>Buy a service to get started.</p>
            </div>
        `;
        return;
    }

    const purchasedDetails = userServices.map(us => {
        const service = services.find(s => s.id === us.service_id || s.id === us.code);
        return {
            ...us,
            name: service?.name || us.service_id || 'Service',
            icon: service?.icon || '📦',
        };
    });

    DOM.userServicesList.innerHTML = purchasedDetails.map(s => `
        <div class="list-item">
            <div>
                <span style="font-size:18px;margin-right:8px;">${s.icon}</span>
                <strong>${s.name}</strong>
                <span class="badge badge-success" style="margin-left:8px;">Active</span>
            </div>
            <span class="text-muted">${new Date(s.purchased_at).toLocaleDateString()}</span>
        </div>
    `).join('');
}

function renderPayments() {
    if (!DOM.paymentsList) return;

    if (!payments || payments.length === 0) {
        DOM.paymentsList.innerHTML = `
            <div class="empty-state">
                <div class="icon">💳</div>
                <h3>No Payments Yet</h3>
                <p>Your payment history will appear here.</p>
            </div>
        `;
        return;
    }

    DOM.paymentsList.innerHTML = payments.slice(0, 10).map(p => {
        const statusClass = p.status === 'completed' ? 'badge-success' :
                           p.status === 'pending' ? 'badge-pending' : 'badge-failed';
        const statusLabel = p.status === 'completed' ? '✅ Complete' :
                           p.status === 'pending' ? '⏳ Pending' : '❌ Failed';

        return `
            <div class="list-item">
                <div>
                    <div style="font-weight:500;">${p.service_name || 'Payment'}</div>
                    <div class="meta">
                        <span>📅 ${new Date(p.created_at).toLocaleDateString()}</span>
                        <span>📱 ${p.phone || '—'}</span>
                    </div>
                </div>
                <div style="display:flex;align-items:center;gap:12px;">
                    <span style="font-weight:700;">KES ${(p.amount || 0).toLocaleString()}</span>
                    <span class="badge ${statusClass}">${statusLabel}</span>
                </div>
            </div>
        `;
    }).join('');
}

// ─── Load Dashboard ─────────────────────────────────────────────

async function loadDashboard() {
    try {
        // Show loading
        if (DOM.statVehicles) DOM.statVehicles.textContent = '...';
        if (DOM.statServices) DOM.statServices.textContent = '...';
        if (DOM.statPayments) DOM.statPayments.textContent = '...';
        if (DOM.statSpent) DOM.statSpent.textContent = 'KES ...';

        // Load data
        const [servicesData, userServicesData, paymentsData] = await Promise.all([
            getServices(),
            getUserServices(),
            getPayments(),
        ]);

        services = servicesData.services || [];
        userServices = userServicesData.services || [];
        payments = paymentsData.payments || [];

        // Calculate stats
        const stats = {
            vehicles: 0,
            active_services: userServices.filter(s => s.status === 'active').length,
            total_payments: payments.length,
            amount_spent: payments.reduce((sum, p) => sum + (p.amount || 0), 0),
        };

        renderStats(stats);
        renderServices();
        renderUserServices();
        renderPayments();

        showToast('✅ Dashboard loaded', 'success');

    } catch (error) {
        console.error('Dashboard load error:', error);
        showToast('❌ ' + error.message, 'error');
    }
}

// ─── Service Actions ───────────────────────────────────────────

function openService(serviceCode) {
    const routes = {
        'mileage': '/mileage.html',
        'valuation': '/instant-value.html',
        'ownership': '/ownership-cost.html',
    };

    if (routes[serviceCode]) {
        window.open(routes[serviceCode], '_blank');
    } else {
        showToast('🔜 Service opening...', 'info');
    }
}

// ─── Payment Modal ─────────────────────────────────────────────

function openPaymentModal(serviceId) {
    const service = services.find(s => s.id === serviceId);
    if (!service) {
        showToast('Service not found', 'error');
        return;
    }

    selectedService = service;

    if (DOM.paymentServiceName) DOM.paymentServiceName.textContent = service.name;
    if (DOM.paymentAmount) DOM.paymentAmount.textContent = `KES ${(service.price || 0).toLocaleString()}`;
    if (DOM.paymentTotal) DOM.paymentTotal.textContent = `KES ${(service.price || 0).toLocaleString()}`;

    if (DOM.mpesaPhone) DOM.mpesaPhone.value = '';
    if (DOM.paymentModal) DOM.paymentModal.classList.add('open');

    // Reset button
    if (DOM.payNowBtn) {
        DOM.payNowBtn.disabled = false;
        DOM.payNowBtn.textContent = '💳 Pay Now';
    }
}

function closePaymentModal() {
    if (DOM.paymentModal) DOM.paymentModal.classList.remove('open');
    selectedService = null;
    if (pollTimer) {
        clearInterval(pollTimer);
        pollTimer = null;
    }
}

// ─── Process Payment ───────────────────────────────────────────

async function processPayment() {
    if (!DOM.mpesaPhone) return;

    let phone = DOM.mpesaPhone.value.trim().replace(/\D/g, '');

    if (phone.startsWith('254')) phone = phone.slice(3);
    if (phone.startsWith('0')) phone = phone.slice(1);

    if (!/^(7\d{8}|11\d{7})$/.test(phone)) {
        showToast('Enter valid Safaricom number (07X or 011X)', 'error');
        return;
    }

    if (!selectedService) {
        showToast('No service selected', 'error');
        return;
    }

    if (!isAuthenticated()) {
        showToast('Please sign in first', 'error');
        return;
    }

    if (DOM.payNowBtn) {
        DOM.payNowBtn.disabled = true;
        DOM.payNowBtn.textContent = '⏳ Processing...';
    }

    if (DOM.processingModal) {
        DOM.processingModal.classList.add('open');
    }
    if (DOM.processingText) DOM.processingText.textContent = 'Initiating payment...';
    if (DOM.processingDetail) DOM.processingDetail.textContent = 'Please wait...';

    try {
        const result = await initiatePayment(
            phone,
            selectedService.id,
            selectedService.price
        );

        const checkoutId = result.checkout_request_id;

        if (DOM.processingText) DOM.processingText.textContent = '📱 STK Push Sent!';
        if (DOM.processingDetail) DOM.processingDetail.textContent = 'Check your phone and enter PIN.';

        showToast('📱 STK Push sent!', 'info');

        const success = await pollPaymentStatus(checkoutId);

        if (DOM.processingModal) DOM.processingModal.classList.remove('open');

        if (success) {
            showToast('✅ Payment successful! Service unlocked.', 'success');
            closePaymentModal();
            await loadDashboard();
        } else {
            showToast('❌ Payment failed or cancelled.', 'error');
        }

    } catch (error) {
        if (DOM.processingModal) DOM.processingModal.classList.remove('open');
        showToast('❌ ' + error.message, 'error');
    } finally {
        if (DOM.payNowBtn) {
            DOM.payNowBtn.disabled = false;
            DOM.payNowBtn.textContent = '💳 Pay Now';
        }
    }
}

async function pollPaymentStatus(checkoutId, maxAttempts = 60) {
    return new Promise((resolve) => {
        let attempts = 0;

        if (pollTimer) clearInterval(pollTimer);

        pollTimer = setInterval(async () => {
            attempts++;

            try {
                const result = await checkPaymentStatus(checkoutId);
                const status = (result.status || '').toLowerCase();

                if (status === 'completed') {
                    clearInterval(pollTimer);
                    pollTimer = null;
                    await confirmPayment(checkoutId);
                    resolve(true);
                    return;
                }

                if (status === 'failed' || status === 'cancelled') {
                    clearInterval(pollTimer);
                    pollTimer = null;
                    resolve(false);
                    return;
                }

            } catch (e) {
                // Continue polling
            }

            if (attempts >= maxAttempts) {
                clearInterval(pollTimer);
                pollTimer = null;
                resolve(false);
            }
        }, 2000);
    });
}

// ─── Logout ────────────────────────────────────────────────────

async function handleLogout() {
    try {
        await logout();
    } catch (e) {
        // Ignore
    }
    redirectToLogin();
}

// ─── Close Modals ──────────────────────────────────────────────

document.addEventListener('click', function(e) {
    const modals = ['paymentModal', 'processingModal'];
    modals.forEach(id => {
        const modal = document.getElementById(id);
        if (modal && e.target === modal) {
            modal.classList.remove('open');
        }
    });
});

// ─── Init ──────────────────────────────────────────────────────

async function init() {
    // Check authentication
    if (!isAuthenticated()) {
        redirectToLogin();
        return;
    }

    // Set user
    try {
        const user = JSON.parse(localStorage.getItem('user') || '{}');
        if (DOM.userName) DOM.userName.textContent = user.email || 'User';
        if (DOM.userAvatar) DOM.userAvatar.textContent = (user.email || 'U')[0].toUpperCase();
    } catch {
        if (DOM.userName) DOM.userName.textContent = 'User';
        if (DOM.userAvatar) DOM.userAvatar.textContent = 'U';
    }

    // Load dashboard
    await loadDashboard();

    // Auto-refresh every 60 seconds
    setInterval(async () => {
        if (isAuthenticated()) {
            await loadDashboard();
        }
    }, 60000);

    console.log('🚗 Auto-D Kenya Dashboard');
    console.log('🔗 API Base:', API_BASE);
}

// ─── Expose functions to global scope ──────────────────────────

window.openPaymentModal = openPaymentModal;
window.closePaymentModal = closePaymentModal;
window.processPayment = processPayment;
window.openService = openService;
window.handleLogout = handleLogout;

// ─── Start ──────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', init);
