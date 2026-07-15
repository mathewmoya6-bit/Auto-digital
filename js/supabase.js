/******************************************************************************
 * AUTO-D ENTERPRISE PLATFORM
 * File: /js/supabase.js
 * Description: Supabase Client
 ******************************************************************************/

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const SUPABASE_URL =
    "https://xgkdbithhlvoqjnqvfmj.supabase.co";

const SUPABASE_ANON_KEY =
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inhna2RiaXRoaGx2b3FqbnF2Zm1qIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODI2NTE4NzQsImV4cCI6MjA5ODIyNzg3NH0.-4P2aQAlDl_4oW0C18gh7cEBzoIKeiLUmMnITz-Nt9Y";

/**
 * Create Supabase Client
 */

export const supabase = createClient(
    SUPABASE_URL,
    SUPABASE_ANON_KEY,
    {
        auth: {

            persistSession: true,

            autoRefreshToken: true,

            detectSessionInUrl: true,

            flowType: "pkce"

        },

        global: {

            headers: {

                "X-Client-Info": "AUTO-D"

            }

        }

    }
);

/**
 * Test Connection
 */

export async function testConnection() {

    try {

        const { data, error } =
            await supabase.auth.getSession();

        if (error) {

            console.error(error);

            return false;

        }

        console.log("✅ Supabase Connected");

        return true;

    }

    catch (err) {

        console.error(err);

        return false;

    }

}

/**
 * Get Current Session
 */

export async function getSession() {

    const { data } =
        await supabase.auth.getSession();

    return data.session;

}

/**
 * Get Current User
 */

export async function getCurrentUser() {

    const { data } =
        await supabase.auth.getUser();

    return data.user;

}

/**
 * Logout
 */

export async function logout() {

    await supabase.auth.signOut();

    window.location.href = "/login.html";

}
