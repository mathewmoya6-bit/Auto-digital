/**
 * Auto-D Kenya — Auth helper (Supabase-backed)
 * ─────────────────────────────────────────────────────────────
 * Wraps Supabase Auth so pages can call simple async functions
 * instead of touching the SDK directly. Requires the Supabase
 * UMD script to be loaded BEFORE this file:
 *
 *   <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
 *   <script src="assets/auth.js"></script>
 *
 * The anon key below is Supabase's public, client-side key — it's
 * designed to be shipped in front-end code and is safe to expose.
 * Row Level Security (RLS) policies on your Supabase tables are what
 * actually control access, not secrecy of this key.
 * ─────────────────────────────────────────────────────────────
 */

(function (global) {
    'use strict';

    var SUPABASE_URL = 'https://xgkdbithhlvoqjnqvfmj.supabase.co';
    var SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inhna2RiaXRoaGx2b3FqbnF2Zm1qIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODI2NTE4NzQsImV4cCI6MjA5ODIyNzg3NH0.-4P2aQAlDl_4oW0C18gh7cEBzoIKeiLUmMnITz-Nt9Y';

    if (!global.supabase) {
        console.error('Supabase SDK not found. Load the supabase-js <script> tag before assets/auth.js.');
    }

    var client = global.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

    function getSession() {
        return client.auth.getSession().then(function (res) {
            if (res.error) {
                console.error(res.error);
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
            if (res.error) return { ok: false, error: res.error.message };
            // If your Supabase project has email confirmation ON (the default),
            // signUp succeeds but returns no session until the user confirms.
            var needsConfirmation = !res.data.session;
            return { ok: true, needsConfirmation: needsConfirmation };
        });
    }

    function logIn(email, password) {
        if (!email || !password) {
            return Promise.resolve({ ok: false, error: 'Please enter your email and password.' });
        }

        return client.auth.signInWithPassword({ email: email, password: password }).then(function (res) {
            if (res.error) return { ok: false, error: res.error.message };
            return { ok: true };
        });
    }

    function logOut() {
        return client.auth.signOut();
    }

    /**
     * Call at the top of any page that requires a logged-in user.
     * Redirects to login.html (preserving the destination) if there's
     * no active Supabase session. Resolves with the session (or null
     * right before redirecting).
     */
    function requireAuth() {
        return getSession().then(function (session) {
            if (!session) {
                var dest = encodeURIComponent(location.pathname.split('/').pop() || 'dashboard.html');
                location.href = 'login.html?redirect=' + dest;
            }
            return session;
        });
    }

    global.AutoDAuth = {
        client: client,
        getSession: getSession,
        isLoggedIn: isLoggedIn,
        signUp: signUp,
        logIn: logIn,
        logOut: logOut,
        requireAuth: requireAuth
    };
})(window);
