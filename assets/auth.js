/**
 * Auto-D Kenya — Auth helper (Supabase-backed)
 * ─────────────────────────────────────────────────────────────
 * Wraps Supabase Auth so pages can call simple async functions
 * instead of touching the SDK directly. Requires the Supabase
 * UMD script to be loaded BEFORE this file.
 */

(function (global) {
    'use strict';

    var SUPABASE_URL = 'https://xgkdbithhlvoqjnqvfmj.supabase.co';
    var SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inhna2RiaXRoaGx2b3FqbnF2Zm1qIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODI2NTE4NzQsImV4cCI6MjA5ODIyNzg3NH0.-4P2aQAlDl_4oW0C18gh7cEBzoIKeiLUmMnITz-Nt9Y';

    if (!global.supabase) {
        console.error('Supabase SDK not found. Load the supabase-js <script> tag before assets/auth.js.');
        // Create a mock client to prevent crashes
        global.supabase = {
            createClient: function() {
                return {
                    auth: {
                        getSession: function() { return Promise.resolve({ data: { session: null }, error: null }); },
                        signInWithPassword: function() { return Promise.resolve({ data: null, error: { message: 'Supabase not loaded' } }); },
                        signUp: function() { return Promise.resolve({ data: null, error: { message: 'Supabase not loaded' } }); },
                        signOut: function() { return Promise.resolve(); }
                    }
                };
            }
        };
    }

    var client = global.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

    function getSession() {
        return client.auth.getSession().then(function (res) {
            if (res.error) {
                console.error('Session error:', res.error);
                return null;
            }
            return res.data.session;
        });
    }

    function isLoggedIn() {
        return getSession().then(function (session) { return !!session; });
    }

    function signUp(name, email, password) {
        if (!name || !email || !password) {
            return Promise.resolve({ ok: false, error: 'Please fill in every field.' });
        }
        if (password.length < 8) {
            return Promise.resolve({ ok: false, error: 'Password must be at least 8 characters.' });
        }

        return client.auth.signUp({
            email: email,
            password: password,
            options: { data: { full_name: name } }
        }).then(function (res) {
            if (res.error) {
                return { ok: false, error: res.error.message };
            }
            var needsConfirmation = !res.data.session;
            return { ok: true, needsConfirmation: needsConfirmation, user: res.data.user };
        }).catch(function(err) {
            return { ok: false, error: err.message || 'Sign up failed' };
        });
    }

    function logIn(email, password) {
        if (!email || !password) {
            return Promise.resolve({ ok: false, error: 'Please enter your email and password.' });
        }

        return client.auth.signInWithPassword({
            email: email,
            password: password
        }).then(function (res) {
            if (res.error) {
                return { ok: false, error: res.error.message };
            }
            return { ok: true, session: res.data.session };
        }).catch(function(err) {
            return { ok: false, error: err.message || 'Login failed' };
        });
    }

    function logOut() {
        return client.auth.signOut().then(function() {
            return { ok: true };
        }).catch(function(err) {
            return { ok: false, error: err.message };
        });
    }

    function requireAuth() {
        return getSession().then(function (session) {
            if (!session) {
                var dest = encodeURIComponent(location.pathname.split('/').pop() || 'dashboard.html');
                location.href = 'login.html?redirect=' + dest;
                return null;
            }
            return session;
        });
    }

    // Expose the auth API globally
    global.AutoDAuth = {
        client: client,
        getSession: getSession,
        isLoggedIn: isLoggedIn,
        signUp: signUp,
        logIn: logIn,
        logOut: logOut,
        requireAuth: requireAuth
    };

    console.log('[Auto-D Auth] Initialized successfully');
})(window);
