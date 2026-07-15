/******************************************************************************
 * AUTO-D ENTERPRISE PLATFORM
 * File: /js/auth.js
 * Part 1 - Registration
 ******************************************************************************/

import { supabase } from "./supabase.js";

/******************************************************************************
 * Register User
 ******************************************************************************/

export async function registerUser(formData) {

    try {

        const {
            email,
            password,
            phone,
            accountType,
            firstName,
            lastName,
            companyName
        } = formData;

        // ----------------------------------------------------
        // 1. Create Auth User
        // ----------------------------------------------------

        const { data: authData, error: authError } =
            await supabase.auth.signUp({

                email,

                password,

                options: {

                    data: {

                        account_type: accountType

                    }

                }

            });

        if (authError)
            throw authError;

        if (!authData.user)
            throw new Error("Registration failed.");

        // ----------------------------------------------------
        // 2. Create users table record
        // ----------------------------------------------------

        const { data: userRow, error: userError } =
            await supabase
                .from("users")
                .insert({

                    auth_user_id: authData.user.id,

                    email,

                    phone,

                    account_type: accountType,

                    account_status: "active"

                })
                .select()
                .single();

        if (userError)
            throw userError;

        // ----------------------------------------------------
        // 3. Create Profile
        // ----------------------------------------------------

        if (accountType === "individual") {

            const { error } =
                await supabase
                    .from("individual_profiles")
                    .insert({

                        user_id: userRow.id,

                        first_name: firstName,

                        last_name: lastName,

                        preferred_currency: "KES",

                        default_annual_mileage: 20000

                    });

            if (error)
                throw error;

        }

        else if (accountType === "corporate") {

            const { error } =
                await supabase
                    .from("corporate_profiles")
                    .insert({

                        user_id: userRow.id,

                        company_name: companyName,

                        fleet_size: 0,

                        employee_count: 1,

                        verified: false

                    });

            if (error)
                throw error;

        }

        return {

            success: true,

            user: authData.user,

            message:
                "Registration successful. Please verify your email."

        };

    }

    catch (error) {

        console.error(error);

        return {

            success: false,

            message: error.message

        };

    }

}

/******************************************************************************
 * Register Individual
 ******************************************************************************/

export async function registerIndividual({

    firstName,

    lastName,

    phone,

    email,

    password

}) {

    return registerUser({

        firstName,

        lastName,

        phone,

        email,

        password,

        accountType: "individual"

    });

}

/******************************************************************************
 * Register Corporate
 ******************************************************************************/

export async function registerCorporate({

    companyName,

    phone,

    email,

    password

}) {

    return registerUser({

        companyName,

        phone,

        email,

        password,

        accountType: "corporate"

    });

}
