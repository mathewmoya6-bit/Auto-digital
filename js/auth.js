/******************************************************************************
 * AUTO-D
 * Registration
 ******************************************************************************/

import { supabase } from "./supabase.js";

/**
 * Register User
 *
 * accountType:
 * individual
 * corporate
 */

export async function register({

    email,
    password,
    accountType = "individual"

}) {

    try {

        const { data, error } =
            await supabase.auth.signUp({

                email,

                password,

                options: {

                    data: {

                        account_type: accountType

                    }

                }

            });

        if (error)
            throw error;

        return {

            success: true,

            user: data.user,

            session: data.session,

            message:
                "Registration successful. Please verify your email."

        };

    }

    catch (err) {

        return {

            success: false,

            message: err.message

        };

    }

}

/******************************************************************************
 * Register Individual
 ******************************************************************************/

export async function registerIndividual(form) {

    const result =
        await register({

            email: form.email,

            password: form.password,

            accountType: "individual"

        });

    if (!result.success)
        return result;

    const { data: appUser, error } =
        await supabase
            .from("users")
            .select("id")
            .eq("auth_user_id", result.user.id)
            .single();

    if (error)
        return {

            success: false,

            message: error.message

        };

    const { error: profileError } =
        await supabase
            .from("individual_profiles")
            .update({

                first_name: form.firstName,

                last_name: form.lastName,

                phone: form.phone,

                national_id: form.nationalId,

                date_of_birth: form.dateOfBirth

            })
            .eq("user_id", appUser.id);

    if (profileError)
        return {

            success: false,

            message: profileError.message

        };

    return result;

}

/******************************************************************************
 * Register Corporate
 ******************************************************************************/

export async function registerCorporate(form) {

    const result =
        await register({

            email: form.email,

            password: form.password,

            accountType: "corporate"

        });

    if (!result.success)
        return result;

    const { data: appUser, error } =
        await supabase
            .from("users")
            .select("id")
            .eq("auth_user_id", result.user.id)
            .single();

    if (error)
        return {

            success: false,

            message: error.message

        };

    const { error: profileError } =
        await supabase
            .from("corporate_profiles")
            .update({

                company_name: form.companyName,

                registration_number: form.registrationNumber,

                kra_pin: form.kraPin,

                company_phone: form.phone,

                company_email: form.email

            })
            .eq("user_id", appUser.id);

    if (profileError)
        return {

            success: false,

            message: profileError.message

        };

    return result;

}
