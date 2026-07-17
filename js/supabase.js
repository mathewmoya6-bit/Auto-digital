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

        const stored = localStorage.getItem('auto_d_user');
        if (stored) {
            try {
                const user = JSON.parse(stored);
                currentUser = user;
                return user;
            } catch (e) { /* ignore */ }
        }

        return null;
    } catch (error) {
        console.warn('⚠️ Get current user error:', error.message);
        return null;
    }
}

// ─── Sign In ──────────────────────────────────────────────────────
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

// ─── Sign Out ──────────────────────────────────────────────────────
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

// ─── Check if user is admin ──────────────────────────────────────
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

// ─── Query Helper ──────────────────────────────────────────────────
async function query(table, select = '*', filters = {}, order = null, limit = null) {
    try {
        const client = getSupabaseClient();
        if (!client) throw new Error('Supabase not initialized');

        let query = client.from(table).select(select);

        Object.keys(filters).forEach(key => {
            if (Array.isArray(filters[key])) {
                query = query.in(key, filters[key]);
            } else {
                query = query.eq(key, filters[key]);
            }
        });

        if (order) {
            query = query.order(order.column, { ascending: order.ascending || false });
        }

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

// ─── Upsert Helper ──────────────────────────────────────────────────
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

// ─── Update Fuel Price ──────────────────────────────────────────────
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

// ─── Get Fuel Prices ──────────────────────────────────────────────
async function getFuelPrices() {
    const result = await query('fuel_prices');
    if (result.success && result.data) {
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

// ─── Update Service Price ──────────────────────────────────────────
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

// ─── Get Service Prices ──────────────────────────────────────────
async function getServicePrices() {
    const result = await query('service_prices');
    if (result.success && result.data) {
        const prices = {};
        const latest = {};
        result.data.forEach(item => {
            if (!latest[item.service_type] || new Date(item.created_at) > new Date(latest[item.service_type].created_at)) {
                latest[item.service_type] = item;
            }
        });
        Object.keys(latest).forEach(key => {
            prices[key] = latest[key].price;
        });
        return { success: true, data: prices };
    }
    return result;
}

// ─── Get Engine Settings ──────────────────────────────────────────
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

// ─── Update Engine Settings ──────────────────────────────────────
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

// ─── Add Admin Log ──────────────────────────────────────────────────
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

// ─── Get Admin Logs ──────────────────────────────────────────────────
async function getAdminLogs(limit = 50) {
    return await query(
        'admin_logs',
        '*',
        {},
        { column: 'created_at', ascending: false },
        limit
    );
}

// ─── Get Dashboard Stats ──────────────────────────────────────────
async function getDashboardStats() {
    try {
        const client = getSupabaseClient();
        if (!client) throw new Error('Supabase not initialized');

        const user = await getCurrentUser();
        if (!user) throw new Error('User not authenticated');

        const { count: vehicles } = await client
            .from('vehicles')
            .select('*', { count: 'exact', head: true })
            .eq('user_id', user.id);

        const { count: reports } = await client
            .from('reports')
            .select('*', { count: 'exact', head: true })
            .eq('user_id', user.id);

        const { count: services } = await client
            .from('service_access')
            .select('*', { count: 'exact', head: true })
            .eq('user_id', user.id)
            .eq('status', 'active');

        const { data: payments } = await client
            .from('payments')
            .select('amount')
            .eq('user_id', user.id);
        
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

// ─── Expose to window ──────────────────────────────────────────
const AutoDClient = {
    init: initSupabase,
    getClient: getSupabaseClient,
    getCurrentUser,
    signIn,
    signOut,
    isAdmin,
    query,
    upsert,
    getFuelPrices,
    updateFuelPrice,
    getServicePrices,
    updateServicePrice,
    getEngineSettings,
    updateEngineSettings,
    addAdminLog,
    getAdminLogs,
    getDashboardStats,
    SUPABASE_URL,
    SUPABASE_ANON_KEY
};

window.AutoDClient = AutoDClient;

if (typeof module !== 'undefined' && module.exports) {
    module.exports = AutoDClient;
}

console.log('🚗 Auto-D Kenya Supabase Client initialized');
