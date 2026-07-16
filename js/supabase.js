// ============================================
// AUTO-D KENYA - Supabase Client
// Single source of truth for all Supabase operations
// ============================================

// ─── Configuration ──────────────────────────────────────────────
const SUPABASE_URL = 'https://xgkdbithhlvoqjnqvfmj.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inhna2RiaXRoaGx2b3FqbnF2Zm1qIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODI2NTE4NzQsImV4cCI6MjA5ODIyNzg3NH0.-4P2aQAlDl_4oW0C18gh7cEBzoIKeiLUmMnITz-Nt9Y';

// ─── State ──────────────────────────────────────────────────────
let supabaseClient = null;
let currentUser = null;
let isInitialized = false;

// ─── Initialize Supabase ────────────────────────────────────────
function initSupabase() {
    try {
        if (typeof supabase === 'undefined') {
            console.warn('⚠️ Supabase SDK not loaded');
            return null;
        }
        
        if (!supabaseClient) {
            const { createClient } = supabase;
            supabaseClient = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
            console.log('✅ Supabase client initialized');
            isInitialized = true;
        }
        return supabaseClient;
    } catch (error) {
        console.error('❌ Supabase init error:', error);
        return null;
    }
}

// ─── Get Client Instance ────────────────────────────────────────
function getSupabaseClient() {
    if (!supabaseClient) {
        return initSupabase();
    }
    return supabaseClient;
}

// ─── Get Current User ────────────────────────────────────────────
async function getCurrentUser() {
    try {
        const client = getSupabaseClient();
        if (!client) return null;

        const { data: { session }, error } = await client.auth.getSession();
        if (error) throw error;

        if (session?.user) {
            currentUser = session.user;
            localStorage.setItem('auto_d_user', JSON.stringify(currentUser));
            return currentUser;
        }

        // Check local storage
        const stored = localStorage.getItem('auto_d_user');
        if (stored) {
            try {
                const user = JSON.parse(stored);
                currentUser = user;
                return user;
            } catch (e) {
                // ignore
            }
        }

        return null;
    } catch (error) {
        console.warn('⚠️ Get current user error:', error.message);
        return null;
    }
}

// ─── Auth Functions ──────────────────────────────────────────────

// Sign In
async function signIn(email, password) {
    try {
        const client = getSupabaseClient();
        if (!client) throw new Error('Supabase not initialized');

        const { data, error } = await client.auth.signInWithPassword({
            email: email.toLowerCase().trim(),
            password: password
        });

        if (error) throw error;

        currentUser = data.user;
        localStorage.setItem('auto_d_user', JSON.stringify(currentUser));
        return { success: true, user: data.user };
    } catch (error) {
        console.error('❌ Sign in error:', error);
        return { success: false, error: error.message };
    }
}

// Sign Up
async function signUp(email, password, fullName, phone) {
    try {
        const client = getSupabaseClient();
        if (!client) throw new Error('Supabase not initialized');

        const { data, error } = await client.auth.signUp({
            email: email.toLowerCase().trim(),
            password: password,
            options: {
                data: {
                    full_name: fullName,
                    phone: phone || ''
                }
            }
        });

        if (error) throw error;

        // Add user to users table
        if (data.user) {
            try {
                await client
                    .from('users')
                    .insert({
                        auth_user_id: data.user.id,
                        email: email.toLowerCase().trim(),
                        full_name: fullName,
                        phone: phone || '',
                        created_at: new Date().toISOString()
                    });
            } catch (e) {
                console.warn('Could not add user to users table:', e);
            }
        }

        return { success: true, user: data.user };
    } catch (error) {
        console.error('❌ Sign up error:', error);
        return { success: false, error: error.message };
    }
}

// Sign Out
async function signOut() {
    try {
        const client = getSupabaseClient();
        if (!client) return { success: true };

        await client.auth.signOut();
        currentUser = null;
        localStorage.removeItem('auto_d_user');
        return { success: true };
    } catch (error) {
        console.error('❌ Sign out error:', error);
        return { success: false, error: error.message };
    }
}

// Google Sign In
async function signInWithGoogle() {
    try {
        const client = getSupabaseClient();
        if (!client) throw new Error('Supabase not initialized');

        const { data, error } = await client.auth.signInWithOAuth({
            provider: 'google',
            options: {
                redirectTo: window.location.origin + window.location.pathname
            }
        });

        if (error) throw error;
        return { success: true, data };
    } catch (error) {
        console.error('❌ Google sign in error:', error);
        return { success: false, error: error.message };
    }
}

// ─── Admin Functions ────────────────────────────────────────────

// Check if user is admin
async function isAdmin(userId) {
    try {
        const client = getSupabaseClient();
        if (!client) return false;

        const { data, error } = await client
            .from('admin_users')
            .select('role')
            .eq('user_id', userId || currentUser?.id)
            .single();

        if (error) return false;
        return !!data;
    } catch (error) {
        console.warn('⚠️ Admin check error:', error.message);
        return false;
    }
}

// ─── CRUD Operations ────────────────────────────────────────────

// Generic query helper
async function query(table, select = '*', filters = {}, order = null, limit = null) {
    try {
        const client = getSupabaseClient();
        if (!client) throw new Error('Supabase not initialized');

        let query = client.from(table).select(select);

        // Apply filters
        Object.keys(filters).forEach(key => {
            if (Array.isArray(filters[key])) {
                query = query.in(key, filters[key]);
            } else {
                query = query.eq(key, filters[key]);
            }
        });

        // Apply order
        if (order) {
            query = query.order(order.column, { 
                ascending: order.ascending || false 
            });
        }

        // Apply limit
        if (limit) {
            query = query.limit(limit);
        }

        const { data, error } = await query;
        if (error) throw error;
        return { success: true, data };
    } catch (error) {
        console.error(`❌ Query error (${table}):`, error);
        return { success: false, error: error.message };
    }
}

// Insert
async function insert(table, data) {
    try {
        const client = getSupabaseClient();
        if (!client) throw new Error('Supabase not initialized');

        // Add timestamps
        const now = new Date().toISOString();
        const record = {
            ...data,
            created_at: now,
            updated_at: now
        };

        const { data: result, error } = await client
            .from(table)
            .insert(record)
            .select()
            .single();

        if (error) throw error;
        return { success: true, data: result };
    } catch (error) {
        console.error(`❌ Insert error (${table}):`, error);
        return { success: false, error: error.message };
    }
}

// Update
async function update(table, id, data) {
    try {
        const client = getSupabaseClient();
        if (!client) throw new Error('Supabase not initialized');

        const { data: result, error } = await client
            .from(table)
            .update({
                ...data,
                updated_at: new Date().toISOString()
            })
            .eq('id', id)
            .select()
            .single();

        if (error) throw error;
        return { success: true, data: result };
    } catch (error) {
        console.error(`❌ Update error (${table}):`, error);
        return { success: false, error: error.message };
    }
}

// Delete
async function remove(table, id) {
    try {
        const client = getSupabaseClient();
        if (!client) throw new Error('Supabase not initialized');

        const { error } = await client
            .from(table)
            .delete()
            .eq('id', id);

        if (error) throw error;
        return { success: true };
    } catch (error) {
        console.error(`❌ Delete error (${table}):`, error);
        return { success: false, error: error.message };
    }
}

// Upsert (Insert or Update)
async function upsert(table, data, conflictKey = 'id') {
    try {
        const client = getSupabaseClient();
        if (!client) throw new Error('Supabase not initialized');

        const { data: result, error } = await client
            .from(table)
            .upsert({
                ...data,
                updated_at: new Date().toISOString()
            }, { onConflict: conflictKey })
            .select();

        if (error) throw error;
        return { success: true, data: result };
    } catch (error) {
        console.error(`❌ Upsert error (${table}):`, error);
        return { success: false, error: error.message };
    }
}

// ─── Vehicle Functions ──────────────────────────────────────────

// Get user vehicles
async function getUserVehicles(userId) {
    return await query(
        'vehicles',
        '*',
        { user_id: userId || currentUser?.id },
        { column: 'created_at', ascending: false }
    );
}

// Add vehicle
async function addVehicle(vehicleData) {
    return await insert('vehicles', {
        user_id: currentUser?.id || vehicleData.user_id,
        plate: vehicleData.plate?.toUpperCase(),
        make_model: vehicleData.make_model,
        vin: vehicleData.vin || null,
        year: vehicleData.year || null,
        mileage: vehicleData.mileage || 0,
        value: vehicleData.value || 0,
        running_cost: vehicleData.running_cost || 0,
        tco: vehicleData.tco || 0,
        verified: vehicleData.verified || false,
        next_service: vehicleData.next_service || null,
        insurance_status: vehicleData.insurance_status || null
    });
}

// Update vehicle
async function updateVehicle(id, vehicleData) {
    return await update('vehicles', id, vehicleData);
}

// Delete vehicle
async function deleteVehicle(id) {
    return await remove('vehicles', id);
}

// ─── Service Functions ──────────────────────────────────────────

// Get service prices
async function getServicePrices() {
    const result = await query('service_prices');
    if (result.success && result.data) {
        // Convert to object format
        const prices = {};
        result.data.forEach(item => {
            prices[item.service_type] = item.price;
        });
        return { success: true, data: prices };
    }
    return result;
}

// Update service price
async function updateServicePrice(serviceType, price) {
    return await upsert(
        'service_prices',
        {
            service_type: serviceType,
            price: price,
            currency: 'KES'
        },
        'service_type'
    );
}

// Get user's purchased services
async function getUserServices(userId) {
    const result = await query(
        'service_access',
        '*',
        { 
            user_id: userId || currentUser?.id,
            status: 'active'
        },
        { column: 'created_at', ascending: false }
    );
    
    if (result.success && result.data) {
        // Filter expired services
        const now = new Date();
        const active = result.data.filter(item => {
            return !item.expires_at || new Date(item.expires_at) > now;
        });
        return { success: true, data: active };
    }
    return result;
}

// Purchase service
async function purchaseService(serviceId, paymentRef) {
    return await insert('service_access', {
        user_id: currentUser?.id,
        service_id: serviceId,
        status: 'active',
        expires_at: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
        payment_ref: paymentRef
    });
}

// ─── Report Functions ───────────────────────────────────────────

// Get user reports
async function getUserReports(userId, limit = 10) {
    return await query(
        'reports',
        '*',
        { user_id: userId || currentUser?.id },
        { column: 'created_at', ascending: false },
        limit
    );
}

// Add report
async function addReport(reportData) {
    return await insert('reports', {
        user_id: currentUser?.id || reportData.user_id,
        vehicle_id: reportData.vehicle_id || null,
        vehicle_plate: reportData.vehicle_plate || null,
        title: reportData.title || 'Vehicle Report',
        report_type: reportData.report_type || 'Valuation',
        status: reportData.status || 'completed'
    });
}

// ─── Payment Functions ──────────────────────────────────────────

// Get user payments
async function getUserPayments(userId, limit = 10) {
    return await query(
        'payments',
        '*',
        { user_id: userId || currentUser?.id },
        { column: 'created_at', ascending: false },
        limit
    );
}

// Add payment
async function addPayment(paymentData) {
    return await insert('payments', {
        user_id: currentUser?.id || paymentData.user_id,
        service_name: paymentData.service_name || 'Payment',
        phone: paymentData.phone || null,
        amount: paymentData.amount || 0,
        status: paymentData.status || 'completed',
        transaction_id: paymentData.transaction_id || null,
        receipt_url: paymentData.receipt_url || null
    });
}

// ─── Notification Functions ─────────────────────────────────────

// Get user notifications
async function getUserNotifications(userId, limit = 10) {
    return await query(
        'notifications',
        '*',
        { user_id: userId || currentUser?.id },
        { column: 'created_at', ascending: false },
        limit
    );
}

// Add notification
async function addNotification(notificationData) {
    return await insert('notifications', {
        user_id: currentUser?.id || notificationData.user_id,
        type: notificationData.type || 'info',
        message: notificationData.message,
        read: false
    });
}

// Mark notification as read
async function markNotificationRead(id) {
    return await update('notifications', id, { read: true });
}

// Mark all notifications as read
async function markAllNotificationsRead(userId) {
    try {
        const client = getSupabaseClient();
        if (!client) throw new Error('Supabase not initialized');

        const { error } = await client
            .from('notifications')
            .update({ read: true })
            .eq('user_id', userId || currentUser?.id);

        if (error) throw error;
        return { success: true };
    } catch (error) {
        console.error('❌ Mark all notifications read error:', error);
        return { success: false, error: error.message };
    }
}

// ─── Fuel Price Functions ───────────────────────────────────────

// Get fuel prices
async function getFuelPrices() {
    const result = await query('fuel_prices');
    if (result.success && result.data) {
        // Convert to object format with latest prices
        const prices = {};
        const latest = {};
        result.data.forEach(item => {
            if (!latest[item.fuel_type] || new Date(item.created_at) > new Date(latest[item.fuel_type].created_at)) {
                latest[item.fuel_type] = item;
            }
        });
        Object.keys(latest).forEach(key => {
            prices[key] = {
                price: latest[key].price,
                date: latest[key].created_at,
                currency: latest[key].currency || 'KES'
            };
        });
        return { success: true, data: prices };
    }
    return result;
}

// Update fuel price
async function updateFuelPrice(fuelType, price) {
    return await upsert(
        'fuel_prices',
        {
            fuel_type: fuelType,
            price: price,
            currency: 'KES'
        },
        'fuel_type'
    );
}

// ─── Settings Functions ─────────────────────────────────────────

// Get engine settings
async function getEngineSettings() {
    try {
        const client = getSupabaseClient();
        if (!client) throw new Error('Supabase not initialized');

        const { data, error } = await client
            .from('settings')
            .select('value')
            .eq('key', 'engine_settings')
            .single();

        if (error) {
            // Return defaults if not found
            return { 
                success: true, 
                data: {
                    depreciation_rate: 0.15,
                    insurance_rate: 0.045,
                    annual_mileage: 20000,
                    tyre_lifespan: 45000
                } 
            };
        }

        return { success: true, data: data.value };
    } catch (error) {
        console.warn('⚠️ Get engine settings error:', error.message);
        return { 
            success: true, 
            data: {
                depreciation_rate: 0.15,
                insurance_rate: 0.045,
                annual_mileage: 20000,
                tyre_lifespan: 45000
            } 
        };
    }
}

// Update engine settings
async function updateEngineSettings(settings) {
    return await upsert(
        'settings',
        {
            key: 'engine_settings',
            value: settings
        },
        'key'
    );
}

// ─── Activity Log Functions ─────────────────────────────────────

// Add admin log
async function addAdminLog(action, username = 'system') {
    try {
        const client = getSupabaseClient();
        if (!client) return { success: true };

        const { error } = await client
            .from('admin_logs')
            .insert({
                action: action,
                username: username,
                created_at: new Date().toISOString()
            });

        if (error) throw error;
        return { success: true };
    } catch (error) {
        console.warn('⚠️ Add admin log error:', error.message);
        return { success: false, error: error.message };
    }
}

// Get admin logs
async function getAdminLogs(limit = 50) {
    return await query(
        'admin_logs',
        '*',
        {},
        { column: 'created_at', ascending: false },
        limit
    );
}

// ─── Dashboard Stats ─────────────────────────────────────────────

// Get dashboard stats
async function getDashboardStats() {
    try {
        const client = getSupabaseClient();
        if (!client) throw new Error('Supabase not initialized');

        // Get vehicle count
        const { count: vehicles } = await client
            .from('vehicles')
            .select('*', { count: 'exact', head: true })
            .eq('user_id', currentUser?.id);

        // Get report count
        const { count: reports } = await client
            .from('reports')
            .select('*', { count: 'exact', head: true })
            .eq('user_id', currentUser?.id);

        // Get service count
        const { count: services } = await client
            .from('service_access')
            .select('*', { count: 'exact', head: true })
            .eq('user_id', currentUser?.id)
            .eq('status', 'active');

        // Get total amount spent
        const { data: payments } = await client
            .from('payments')
            .select('amount')
            .eq('user_id', currentUser?.id);
        
        const totalSpent = payments ? payments.reduce((sum, p) => sum + (p.amount || 0), 0) : 0;

        return {
            success: true,
            data: {
                vehicles: vehicles || 0,
                reports: reports || 0,
                active_services: services || 0,
                amount_spent: totalSpent
            }
        };
    } catch (error) {
        console.error('❌ Dashboard stats error:', error);
        return { success: false, error: error.message };
    }
}

// ─── Export ──────────────────────────────────────────────────────

// Create the client object
const AutoDClient = {
    // Core
    init: initSupabase,
    getClient: getSupabaseClient,
    getCurrentUser,
    isAdmin,
    
    // Auth
    signIn,
    signUp,
    signOut,
    signInWithGoogle,
    
    // CRUD
    query,
    insert,
    update,
    remove,
    upsert,
    
    // Vehicles
    getUserVehicles,
    addVehicle,
    updateVehicle,
    deleteVehicle,
    
    // Services
    getServicePrices,
    updateServicePrice,
    getUserServices,
    purchaseService,
    
    // Reports
    getUserReports,
    addReport,
    
    // Payments
    getUserPayments,
    addPayment,
    
    // Notifications
    getUserNotifications,
    addNotification,
    markNotificationRead,
    markAllNotificationsRead,
    
    // Fuel
    getFuelPrices,
    updateFuelPrice,
    
    // Settings
    getEngineSettings,
    updateEngineSettings,
    
    // Admin Logs
    addAdminLog,
    getAdminLogs,
    
    // Dashboard
    getDashboardStats,
    
    // Constants
    SUPABASE_URL,
    SUPABASE_ANON_KEY
};

// ─── Expose to window ──────────────────────────────────────────
window.AutoDClient = AutoDClient;

// ─── ES Module Export ──────────────────────────────────────────
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AutoDClient;
}

console.log('🚗 Auto-D Kenya Supabase Client initialized');
console.log('📡 Connected to:', SUPABASE_URL);
