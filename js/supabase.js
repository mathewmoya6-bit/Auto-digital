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
            supabaseClient = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
                auth: {
                    persistSession: true,
                    autoRefreshToken: true,
                    detectSessionInUrl: true
                }
            });
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

        // First try to get session from Supabase
        const { data: { session }, error } = await client.auth.getSession();
        if (error) throw error;

        if (session?.user) {
            currentUser = session.user;
            localStorage.setItem('auto_d_user', JSON.stringify(currentUser));
            return currentUser;
        }

        // Fallback to stored user
        const stored = localStorage.getItem('auto_d_user');
        if (stored) {
            try {
                const user = JSON.parse(stored);
                // Verify the stored user is still valid
                const { data: { user: verifiedUser }, error: verifyError } = await client.auth.getUser();
                if (!verifyError && verifiedUser) {
                    currentUser = verifiedUser;
                    localStorage.setItem('auto_d_user', JSON.stringify(verifiedUser));
                    return verifiedUser;
                }
                // If verification fails, stored user is invalid
                localStorage.removeItem('auto_d_user');
                return null;
            } catch (e) {
                localStorage.removeItem('auto_d_user');
                return null;
            }
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

// ─── Sign Up ──────────────────────────────────────────────────────
async function signUp(email, password, fullName = null) {
    try {
        const client = getSupabaseClient();
        if (!client) throw new Error('Supabase not initialized');

        const { data, error } = await client.auth.signUp({
            email: email.toLowerCase().trim(),
            password: password,
            options: {
                data: {
                    full_name: fullName || email.split('@')[0]
                }
            }
        });

        if (error) throw error;

        if (data.user) {
            return { success: true, user: data.user };
        }
        return { success: false, error: 'Registration failed' };
    } catch (error) {
        console.error('❌ Sign up error:', error);
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

        let queryBuilder = client.from(table).select(select);

        // Apply filters
        Object.keys(filters).forEach(key => {
            const value = filters[key];
            if (value === null) {
                queryBuilder = queryBuilder.is(key, null);
            } else if (Array.isArray(value)) {
                queryBuilder = queryBuilder.in(key, value);
            } else if (typeof value === 'object' && value !== null) {
                // Handle operators like { operator: 'gt', value: 100 }
                if (value.operator && value.value !== undefined) {
                    queryBuilder = queryBuilder.filter(key, value.operator, value.value);
                } else {
                    queryBuilder = queryBuilder.eq(key, value);
                }
            } else {
                queryBuilder = queryBuilder.eq(key, value);
            }
        });

        if (order) {
            queryBuilder = queryBuilder.order(order.column, { 
                ascending: order.ascending !== false 
            });
        }

        if (limit) {
            queryBuilder = queryBuilder.limit(limit);
        }

        const { data, error } = await queryBuilder;
        if (error) throw error;
        return { success: true, data };
    } catch (error) {
        console.error(`❌ Query error (${table}):`, error);
        return { success: false, error: error.message };
    }
}

// ─── Insert Helper ──────────────────────────────────────────────────
async function insert(table, data) {
    try {
        const client = getSupabaseClient();
        if (!client) throw new Error('Supabase not initialized');

        const { data: result, error } = await client
            .from(table)
            .insert({
                ...data,
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString()
            })
            .select();

        if (error) throw error;
        return { success: true, data: result };
    } catch (error) {
        console.error(`❌ Insert error (${table}):`, error);
        return { success: false, error: error.message };
    }
}

// ─── Update Helper ──────────────────────────────────────────────────
async function update(table, data, match) {
    try {
        const client = getSupabaseClient();
        if (!client) throw new Error('Supabase not initialized');

        let queryBuilder = client.from(table).update({
            ...data,
            updated_at: new Date().toISOString()
        });

        Object.keys(match).forEach(key => {
            queryBuilder = queryBuilder.eq(key, match[key]);
        });

        const { data: result, error } = await queryBuilder.select();

        if (error) throw error;
        return { success: true, data: result };
    } catch (error) {
        console.error(`❌ Update error (${table}):`, error);
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

// ─── Delete Helper ──────────────────────────────────────────────────
async function remove(table, match) {
    try {
        const client = getSupabaseClient();
        if (!client) throw new Error('Supabase not initialized');

        let queryBuilder = client.from(table).delete();

        Object.keys(match).forEach(key => {
            queryBuilder = queryBuilder.eq(key, match[key]);
        });

        const { data, error } = await queryBuilder.select();

        if (error) throw error;
        return { success: true, data };
    } catch (error) {
        console.error(`❌ Delete error (${table}):`, error);
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
            // Return default settings if not found
            return { 
                success: true, 
                data: {
                    depreciation_rate: 0.15,
                    insurance_rate: 0.045,
                    annual_mileage: 20000,
                    tyre_lifespan: 45000,
                    service_interval: 10000
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
                tyre_lifespan: 45000,
                service_interval: 10000
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

        const { count: vehicles, error: vehiclesError } = await client
            .from('vehicles')
            .select('*', { count: 'exact', head: true })
            .eq('user_id', user.id);

        const { count: reports, error: reportsError } = await client
            .from('reports')
            .select('*', { count: 'exact', head: true })
            .eq('user_id', user.id);

        const { count: services, error: servicesError } = await client
            .from('service_access')
            .select('*', { count: 'exact', head: true })
            .eq('user_id', user.id)
            .eq('status', 'active');

        const { data: payments, error: paymentsError } = await client
            .from('payments')
            .select('amount')
            .eq('user_id', user.id)
            .eq('status', 'completed');
        
        const totalSpent = payments ? payments.reduce((sum, p) => sum + (p.amount || 0), 0) : 0;

        return {
            success: true,
            data: {
                vehicles: vehicles || 0,
                reports: reports || 0,
                active_services: services || 0,
                amount_spent: totalSpent,
                errors: {
                    vehicles: vehiclesError?.message,
                    reports: reportsError?.message,
                    services: servicesError?.message,
                    payments: paymentsError?.message
                }
            }
        };
    } catch (error) {
        console.error('❌ Dashboard stats error:', error);
        return { success: false, error: error.message };
    }
}

// ─── Add Vehicle ──────────────────────────────────────────────────
async function addVehicle(vehicleData) {
    try {
        const user = await getCurrentUser();
        if (!user) throw new Error('User not authenticated');

        const result = await insert('vehicles', {
            user_id: user.id,
            ...vehicleData,
            plate: vehicleData.plate?.toUpperCase().trim(),
            verified: false
        });

        return result;
    } catch (error) {
        console.error('❌ Add vehicle error:', error);
        return { success: false, error: error.message };
    }
}

// ─── Get User Vehicles ──────────────────────────────────────────
async function getUserVehicles() {
    try {
        const user = await getCurrentUser();
        if (!user) throw new Error('User not authenticated');

        return await query(
            'vehicles',
            '*',
            { user_id: user.id },
            { column: 'created_at', ascending: false }
        );
    } catch (error) {
        console.error('❌ Get vehicles error:', error);
        return { success: false, error: error.message };
    }
}

// ─── Delete Vehicle ──────────────────────────────────────────────
async function deleteVehicle(vehicleId) {
    try {
        const user = await getCurrentUser();
        if (!user) throw new Error('User not authenticated');

        return await remove('vehicles', { 
            id: vehicleId, 
            user_id: user.id 
        });
    } catch (error) {
        console.error('❌ Delete vehicle error:', error);
        return { success: false, error: error.message };
    }
}

// ─── Expose to window ──────────────────────────────────────────
const AutoDClient = {
    // Client
    init: initSupabase,
    getClient: getSupabaseClient,
    
    // Auth
    getCurrentUser,
    signIn,
    signOut,
    signUp,
    isAdmin,
    
    // CRUD
    query,
    insert,
    update,
    upsert,
    remove,
    
    // Vehicles
    addVehicle,
    getUserVehicles,
    deleteVehicle,
    
    // Fuel
    getFuelPrices,
    updateFuelPrice,
    
    // Services
    getServicePrices,
    updateServicePrice,
    
    // Settings
    getEngineSettings,
    updateEngineSettings,
    
    // Admin
    addAdminLog,
    getAdminLogs,
    
    // Dashboard
    getDashboardStats,
    
    // Constants
    SUPABASE_URL,
    SUPABASE_ANON_KEY
};

// ─── Browser / Global ──────────────────────────────────────────
if (typeof window !== 'undefined') {
    window.AutoDClient = AutoDClient;
}

// ─── Node / CommonJS ────────────────────────────────────────────
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AutoDClient;
}

console.log('🚗 Auto-D Kenya Supabase Client initialized');
console.log('📦 Version: 2.0.0');
console.log('🔐 Auth: Supabase + JWT');
console.log('📊 Tables: vehicles, reports, services, payments, settings');
