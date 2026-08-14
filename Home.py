import streamlit as st
import requests
import bcrypt
import secrets
import hashlib
import hmac
import base64
import json
import resend

from supabase import create_client

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from streamlit_cookies_controller import CookieController
from utils.layout import show_sidebar_branding


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Wiginton Tools",
    page_icon="🧰",
    layout="wide"
)


# =========================================================
# SETTINGS
# =========================================================

NOTION_TOKEN = st.secrets["NOTION_TOKEN"]

# Forecast data source.
# The code accepts either of the secret names below so the Home page
# can use the same Forecast table already configured in the app.
NOTION_FORECAST_DATA_SOURCE_ID = (
    st.secrets.get("NOTION_FORECAST_DATA_SOURCE_ID")
    or st.secrets.get("FORECAST_DATA_SOURCE_ID")
    or st.secrets.get("NOTION_FORECAST_DATABASE_ID")
)

# Projects data source.
NOTION_PROJECTS_DATA_SOURCE_ID = (
    st.secrets.get("NOTION_PROJECTS_DATA_SOURCE_ID")
    or st.secrets.get("PROJECTS_DATA_SOURCE_ID")
    or st.secrets.get("NOTION_PROJECTS_DATABASE_ID")
)

APP_URL = st.secrets["APP_URL"].rstrip("/")

RESEND_API_KEY = st.secrets["RESEND_API_KEY"]

RESET_EMAIL_SENDER = st.secrets["RESET_EMAIL_SENDER"]

# Secret used only to sign persistent login tokens.
# Add AUTH_SECRET to .streamlit/secrets.toml and Streamlit Cloud secrets.
AUTH_SECRET = st.secrets["AUTH_SECRET"]

# =========================================================
# SUPABASE / AUTH / PROFILES
# =========================================================
# Authentication is handled by Supabase Auth.
# public.profiles stores only application user data:
# id, created_at, name, email, employee_number, role,
# branch and active.
#
# Projects and Forecast remain in Notion.
SUPABASE_URL = (
    st.secrets.get("SUPABASE_URL", "")
    or ""
).strip().rstrip("/")

SUPABASE_SECRET_KEY = (
    st.secrets.get("SUPABASE_SECRET_KEY", "")
    or st.secrets.get("SUPABASE_SERVICE_ROLE_KEY", "")
    or st.secrets.get("SUPABASE_KEY", "")
    or ""
).strip()

# A publishable/anon key is optional in this server-side
# Streamlit implementation. If it does not exist, the secret
# key is also used for the password sign-in request.
SUPABASE_PUBLIC_KEY = (
    st.secrets.get("SUPABASE_PUBLISHABLE_KEY", "")
    or st.secrets.get("SUPABASE_ANON_KEY", "")
    or ""
).strip()

PROFILES_TABLE_NAME = "profiles"

# =========================================================
# FIXED BRANCH OPTIONS
# =========================================================
# Branches are part of the company structure and therefore
# should not depend on which users already exist in profiles.
BRANCH_OPTIONS = [
    "ATLANTA",
    "CHARLOTTE",
    "FORT MYERS",
    "GAINESVILLE",
    "JACKSONVILLE",
    "MELBOURNE",
    "MIAMI",
    "ORLANDO",
    "PENSACOLA",
    "TAMPA",
    "WEST PALM BEACH",
]


def create_supabase_admin_client():

    if (
        not SUPABASE_URL
        or not SUPABASE_SECRET_KEY
    ):
        raise RuntimeError(
            "Supabase is not configured. "
            "Check SUPABASE_URL and SUPABASE_SECRET_KEY."
        )

    # Use the standard client initialization for compatibility
    # across supabase-py versions. Admin Auth operations are
    # available because this client uses the server-side secret key.
    return create_client(
        SUPABASE_URL,
        SUPABASE_SECRET_KEY,
    )


supabase_admin = (
    create_supabase_admin_client()
)

# Persistent login settings.
# The login remains valid for up to 10 hours, but never past midnight
# in the app's local timezone.
AUTH_COOKIE_NAME = "wiginton_auth"
AUTH_DURATION_HOURS = 10
AUTH_COOKIE_SECURE = APP_URL.lower().startswith("https://")

resend.api_key = RESEND_API_KEY

# Browser cookie controller used to restore the user after a new
# Streamlit session is created in the same browser/profile.
cookie_controller = CookieController(key="wiginton_auth_cookies")


NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2025-09-03",
}


# Database reads are intentionally not time-cached.
# Each Streamlit rerun requests the current data so changes
# such as passwords, users, projects and forecast are reflected
# immediately.


# =========================================================
# SESSION STATE
# =========================================================

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "user_id" not in st.session_state:
    st.session_state.user_id = None

if "user_name" not in st.session_state:
    st.session_state.user_name = None

if "user_email" not in st.session_state:
    st.session_state.user_email = None

if "user_role" not in st.session_state:
    st.session_state.user_role = None

if "user_branch" not in st.session_state:
    st.session_state.user_branch = None

if "user_employee_number" not in st.session_state:
    st.session_state.user_employee_number = None

if "login_view" not in st.session_state:
    st.session_state.login_view = "login"


if "login_error_detail" not in st.session_state:
    st.session_state.login_error_detail = None


if "password_reset_detail" not in st.session_state:
    st.session_state.password_reset_detail = None

if "supabase_profile_error" not in st.session_state:
    st.session_state.supabase_profile_error = None


# =========================================================
# NOTION PROPERTY HELPERS
# =========================================================

def get_title(properties, property_name):

    prop = properties.get(
        property_name,
        {}
    )

    values = prop.get(
        "title",
        []
    )

    if values:
        return values[0].get(
            "plain_text",
            ""
        )

    return ""


def get_email(properties, property_name):

    prop = properties.get(
        property_name,
        {}
    )

    return prop.get(
        "email",
        ""
    ) or ""


def get_text(properties, property_name):

    prop = properties.get(
        property_name,
        {}
    )

    values = prop.get(
        "rich_text",
        []
    )

    if values:
        return values[0].get(
            "plain_text",
            ""
        )

    return ""


def get_checkbox(
    properties,
    property_name,
    default=True
):

    prop = properties.get(
        property_name,
        {}
    )

    if "checkbox" not in prop:
        return default

    return prop.get(
        "checkbox",
        default
    )


def get_select(
    properties,
    property_name,
    default=""
):

    prop = properties.get(
        property_name,
        {}
    )

    select_value = prop.get(
        "select"
    )

    if not select_value:
        return default

    return select_value.get(
        "name",
        default
    )




# =========================================================
# SUPABASE PROFILE HELPERS
# =========================================================

def normalize_profile(
    row
):

    if not row:
        return None

    return {
        "id":
            row.get(
                "id"
            ),

        "created_at":
            row.get(
                "created_at"
            ),

        "name":
            (
                row.get(
                    "name"
                )
                or ""
            ).strip(),

        "email":
            (
                row.get(
                    "email"
                )
                or ""
            )
            .strip()
            .lower(),

        "employee_number":
            (
                row.get(
                    "employee_number"
                )
                or ""
            ).strip(),

        "role":
            (
                row.get(
                    "role"
                )
                or "Designer"
            ).strip(),

        "branch":
            (
                row.get(
                    "branch"
                )
                or ""
            ).strip(),

        "active":
            bool(
                row.get(
                    "active",
                    True
                )
            ),
    }


def load_profiles():

    try:

        response = (
            supabase_admin
            .table(
                PROFILES_TABLE_NAME
            )
            .select(
                "id,created_at,name,email,"
                "employee_number,role,branch,active"
            )
            .order(
                "name"
            )
            .execute()
        )

    except Exception:

        return []

    return [
        normalize_profile(
            row
        )
        for row in (
            response.data
            or []
        )
    ]


def get_profile_by_email(
    email
):

    target_email = (
        email
        or ""
    ).strip().lower()

    if not target_email:
        return None

    st.session_state[
        "supabase_profile_error"
    ] = None

    try:

        response = (
            supabase_admin
            .table(
                PROFILES_TABLE_NAME
            )
            .select(
                "id,created_at,name,email,"
                "employee_number,role,branch,active"
            )
            .execute()
        )

    except Exception as error:

        st.session_state[
            "supabase_profile_error"
        ] = str(
            error
        )

        return None

    for row in (
        response.data
        or []
    ):

        profile = (
            normalize_profile(
                row
            )
        )

        if (
            profile
            and profile.get(
                "email",
                ""
            )
            .strip()
            .lower()
            == target_email
        ):

            return profile

    return None



def get_profile_by_id(
    profile_id
):

    if not profile_id:
        return None

    try:

        response = (
            supabase_admin
            .table(
                PROFILES_TABLE_NAME
            )
            .select(
                "id,created_at,name,email,"
                "employee_number,role,branch,active"
            )
            .eq(
                "id",
                str(
                    profile_id
                )
            )
            .limit(
                1
            )
            .execute()
        )

    except Exception:

        return None

    rows = (
        response.data
        or []
    )

    if not rows:
        return None

    return normalize_profile(
        rows[0]
    )


def update_profile(
    profile_id,
    values
):

    if not profile_id:
        return False

    allowed_fields = {
        "name",
        "email",
        "employee_number",
        "role",
        "branch",
        "active",
    }

    payload = {
        key: value
        for key, value
        in values.items()
        if key in allowed_fields
    }

    if not payload:
        return True

    try:

        (
            supabase_admin
            .table(
                PROFILES_TABLE_NAME
            )
            .update(
                payload
            )
            .eq(
                "id",
                str(
                    profile_id
                )
            )
            .execute()
        )

        return True

    except Exception:

        return False


def insert_profile(
    user_id,
    name,
    email,
    employee_number,
    role,
    branch,
    active=True
):

    payload = {
        "id":
            str(
                user_id
            ),

        "name":
            name.strip(),

        "email":
            email.strip().lower(),

        "employee_number":
            employee_number.strip(),

        "role":
            role.strip()
            or "Designer",

        "branch":
            branch.strip(),

        "active":
            bool(
                active
            ),
    }

    try:

        (
            supabase_admin
            .table(
                PROFILES_TABLE_NAME
            )
            .insert(
                payload
            )
            .execute()
        )

        return True, None

    except Exception as error:

        return (
            False,
            str(
                error
            ),
        )


def authenticate_with_supabase_auth(
    email,
    password
):
    """
    Authenticate an end user with Supabase Auth.

    IMPORTANT:
    User sign-in must use the Publishable/anon key.
    The Secret key is reserved for server-side admin operations.
    """

    if not SUPABASE_URL:
        return {
            "error":
                "SUPABASE_URL is not configured."
        }

    if not SUPABASE_PUBLIC_KEY:
        return {
            "error":
                (
                    "SUPABASE_PUBLISHABLE_KEY is not configured. "
                    "Add the Supabase Publishable Key to "
                    ".streamlit/secrets.toml."
                )
        }

    try:

        response = requests.post(
            (
                f"{SUPABASE_URL}/auth/v1/token"
                "?grant_type=password"
            ),
            headers={
                "apikey":
                    SUPABASE_PUBLIC_KEY,

                "Content-Type":
                    "application/json",
            },
            json={
                "email":
                    email.strip().lower(),

                "password":
                    password,
            },
            timeout=20,
        )

    except requests.RequestException as error:

        return {
            "error":
                (
                    "Unable to connect to Supabase Auth. "
                    f"{error}"
                )
        }

    if response.status_code != 200:

        try:
            response_data = (
                response.json()
            )

            error_message = (
                response_data.get(
                    "msg"
                )
                or response_data.get(
                    "message"
                )
                or response_data.get(
                    "error_description"
                )
                or response_data.get(
                    "error"
                )
                or "Authentication failed."
            )

        except Exception:

            error_message = (
                "Authentication failed."
            )

        return {
            "error":
                error_message,

            "status_code":
                response.status_code,
        }

    data = response.json()

    auth_user = (
        data.get(
            "user"
        )
        or {}
    )

    user_id = (
        auth_user.get(
            "id"
        )
    )

    if not user_id:

        return {
            "error":
                (
                    "Supabase authenticated the request, "
                    "but no User ID was returned."
                )
        }

    return {
        "id":
            user_id,

        "email":
            (
                auth_user.get(
                    "email"
                )
                or email
            )
            .strip()
            .lower(),

        "access_token":
            data.get(
                "access_token"
            ),

        "refresh_token":
            data.get(
                "refresh_token"
            ),

        "error":
            None,
    }



def create_auth_user(
    email,
    password,
    name
):

    try:

        response = (
            supabase_admin
            .auth
            .admin
            .create_user(
                {
                    "email":
                        email.strip().lower(),

                    "password":
                        password,

                    "email_confirm":
                        True,

                    "user_metadata": {
                        "name":
                            name.strip(),
                    },
                }
            )
        )

    except Exception as error:

        return (
            None,
            str(
                error
            ),
        )

    auth_user = (
        getattr(
            response,
            "user",
            None
        )
    )

    if not auth_user:
        return (
            None,
            "Unable to create the authentication user."
        )

    return (
        auth_user,
        None,
    )


def delete_auth_user(
    user_id
):

    if not user_id:
        return

    try:

        (
            supabase_admin
            .auth
            .admin
            .delete_user(
                str(
                    user_id
                )
            )
        )

    except Exception:

        pass


# =========================================================
# FORECAST DASHBOARD HELPERS
# =========================================================

LOCAL_TIMEZONE = ZoneInfo("America/New_York")


def query_data_source(
    data_source_id,
    payload=None
):

    if not data_source_id:
        return []

    url = (
        "https://api.notion.com/v1/data_sources/"
        f"{data_source_id}/query"
    )

    query_payload = dict(
        payload or {}
    )

    results = []

    while True:

        try:

            response = requests.post(
                url,
                headers=NOTION_HEADERS,
                json=query_payload,
                timeout=20
            )

        except requests.RequestException:

            return []

        if response.status_code != 200:

            return []

        data = response.json()

        results.extend(
            data.get(
                "results",
                []
            )
        )

        if not data.get(
            "has_more"
        ):

            break

        next_cursor = data.get(
            "next_cursor"
        )

        if not next_cursor:

            break

        query_payload[
            "start_cursor"
        ] = next_cursor

    return results


def get_property_plain_text(
    prop
):

    if not prop:
        return ""

    prop_type = prop.get(
        "type"
    )

    if prop_type == "title":

        values = prop.get(
            "title",
            []
        )

        return " ".join(
            item.get(
                "plain_text",
                ""
            )
            for item in values
        ).strip()

    if prop_type == "rich_text":

        values = prop.get(
            "rich_text",
            []
        )

        return " ".join(
            item.get(
                "plain_text",
                ""
            )
            for item in values
        ).strip()

    if prop_type == "select":

        value = prop.get(
            "select"
        )

        return (
            value.get(
                "name",
                ""
            )
            if value
            else ""
        )

    if prop_type == "status":

        value = prop.get(
            "status"
        )

        return (
            value.get(
                "name",
                ""
            )
            if value
            else ""
        )

    if prop_type == "email":

        return (
            prop.get(
                "email"
            )
            or ""
        )

    if prop_type == "number":

        value = prop.get(
            "number"
        )

        if value is None:
            return ""

        return str(
            value
        )

    return ""


def normalize_text(
    value
):

    return (
        str(
            value or ""
        )
        .strip()
        .casefold()
    )


def property_matches_logged_user(
    prop
):

    if not prop:
        return False

    prop_type = prop.get(
        "type"
    )

    user_name = normalize_text(
        st.session_state.user_name
    )

    user_email = normalize_text(
        st.session_state.user_email
    )

    user_id = (
        st.session_state.user_id
        or ""
    )

    if prop_type in {
        "title",
        "rich_text",
        "select",
        "status",
        "email",
        "number",
    }:

        value = normalize_text(
            get_property_plain_text(
                prop
            )
        )

        return value in {
            user_name,
            user_email,
        }

    if prop_type == "people":

        for person in prop.get(
            "people",
            []
        ):

            person_name = normalize_text(
                person.get(
                    "name"
                )
            )

            person_email = normalize_text(
                (
                    person.get(
                        "person"
                    )
                    or {}
                ).get(
                    "email"
                )
            )

            person_id = (
                person.get(
                    "id"
                )
                or ""
            )

            if (
                person_name == user_name
                or person_email == user_email
                or (
                    user_id
                    and person_id == user_id
                )
            ):

                return True

        return False

    if prop_type == "relation":

        relation_ids = {
            item.get(
                "id"
            )
            for item in prop.get(
                "relation",
                []
            )
            if item.get(
                "id"
            )
        }

        return bool(
            user_id
            and user_id in relation_ids
        )

    return False


def normalize_identity(
    value
):

    value = normalize_text(
        value
    )

    if not value:
        return ""

    # Keep only letters and numbers so small differences
    # such as dots, hyphens and extra spaces do not prevent
    # a Designer/User match.
    return "".join(
        character
        for character in value
        if character.isalnum()
    )


def get_all_users():

    return load_profiles()


def get_users_in_branch(
    branch_name
):

    if not branch_name:
        return []

    target_branch = (
        normalize_text(
            branch_name
        )
    )

    users = []

    for profile in load_profiles():

        if not profile.get(
            "active",
            True
        ):
            continue

        if (
            normalize_text(
                profile.get(
                    "branch",
                    ""
                )
            )
            != target_branch
        ):
            continue

        user_name = (
            profile.get(
                "name",
                ""
            )
            or ""
        ).strip()

        user_email = (
            profile.get(
                "email",
                ""
            )
            or ""
        ).strip()

        employee_number = (
            profile.get(
                "employee_number",
                ""
            )
            or ""
        ).strip()

        identifiers = set()

        for value in [
            user_name,
            user_email,
            employee_number,
        ]:

            normalized_value = (
                normalize_identity(
                    value
                )
            )

            if normalized_value:

                identifiers.add(
                    normalized_value
                )

        if user_name:

            for part in (
                user_name.split()
            ):

                normalized_part = (
                    normalize_identity(
                        part
                    )
                )

                if (
                    len(
                        normalized_part
                    )
                    >= 3
                ):

                    identifiers.add(
                        normalized_part
                    )

        if user_email:

            email_prefix = (
                user_email
                .split(
                    "@",
                    1
                )[0]
            )

            identifiers.add(
                normalize_identity(
                    email_prefix
                )
            )

        users.append(
            {
                "id":
                    profile.get(
                        "id"
                    )
                    or "",

                "name":
                    user_name,

                "email":
                    user_email,

                "employee_number":
                    employee_number,

                "role":
                    profile.get(
                        "role",
                        "Designer"
                    ),

                "branch":
                    profile.get(
                        "branch",
                        ""
                    ),

                "identifiers":
                    identifiers,
            }
        )

    return users


def get_logged_manager_branch():

    branch = (
        st.session_state.user_branch
        or ""
    ).strip()

    if branch:
        return branch

    profile = get_profile_by_email(
        (
            st.session_state.user_email
            or ""
        )
    )

    if not profile:
        return ""

    branch = (
        profile.get(
            "branch",
            ""
        )
        or ""
    ).strip()

    st.session_state.user_branch = (
        branch
    )

    return branch



def identity_matches_user(
    designer_value,
    identifiers
):

    designer_identity = (
        normalize_identity(
            designer_value
        )
    )

    if not designer_identity:
        return False

    # Exact normalized match.
    if designer_identity in identifiers:
        return True

    # Controlled fallback for values such as:
    # "Silmar" vs "Silmar Sendin" or an email prefix.
    # Require at least 4 characters to avoid broad matches.
    if len(designer_identity) >= 4:

        for identifier in identifiers:

            if len(identifier) < 4:
                continue

            if (
                designer_identity
                in identifier
                or identifier
                in designer_identity
            ):

                return True

    return False


def user_can_see_designer_property(
    designer_prop
):

    is_manager = (
        normalize_text(
            st.session_state.user_role
        )
        == "manager"
    )

    # -----------------------------------------------------
    # STANDARD USER
    # -----------------------------------------------------

    if not is_manager:

        return property_matches_logged_user(
            designer_prop
        )

    # -----------------------------------------------------
    # MANAGER
    # -----------------------------------------------------

    manager_branch = (
        get_logged_manager_branch()
    )

    if not manager_branch:
        return False

    st.session_state.user_branch = (
        manager_branch
    )

    branch_users = (
        get_users_in_branch(
            manager_branch
        )
    )

    if not branch_users:
        return False

    allowed_ids = {
        user[
            "id"
        ]
        for user in branch_users
        if user[
            "id"
        ]
    }

    prop_type = designer_prop.get(
        "type"
    )

    # -----------------------------------------------------
    # DESIGNER AS SELECT / TEXT / EMAIL / STATUS
    # -----------------------------------------------------

    if prop_type in {
        "select",
        "status",
        "title",
        "rich_text",
        "email",
        "number",
    }:

        designer_value = (
            get_property_plain_text(
                designer_prop
            )
        )

        for user in branch_users:

            if identity_matches_user(
                designer_value,
                user[
                    "identifiers"
                ]
            ):

                return True

        return False

    # -----------------------------------------------------
    # DESIGNER AS PEOPLE
    # -----------------------------------------------------

    if prop_type == "people":

        for person in designer_prop.get(
            "people",
            []
        ):

            person_id = (
                person.get(
                    "id"
                )
                or ""
            )

            if (
                person_id
                and person_id
                in allowed_ids
            ):

                return True

            person_name = (
                person.get(
                    "name"
                )
                or ""
            )

            person_email = (
                (
                    person.get(
                        "person"
                    )
                    or {}
                ).get(
                    "email"
                )
                or ""
            )

            for user in branch_users:

                if (
                    identity_matches_user(
                        person_name,
                        user[
                            "identifiers"
                        ]
                    )
                    or identity_matches_user(
                        person_email,
                        user[
                            "identifiers"
                        ]
                    )
                ):

                    return True

        return False

    # -----------------------------------------------------
    # DESIGNER AS RELATION
    # -----------------------------------------------------

    if prop_type == "relation":

        relation_ids = {
            item.get(
                "id"
            )
            for item in designer_prop.get(
                "relation",
                []
            )
            if item.get(
                "id"
            )
        }

        return bool(
            relation_ids
            & allowed_ids
        )

    return False


def get_forecast_date_property(
    properties
):

    preferred_names = [
        "Date",
        "Forecast Date",
        "Start Date",
        "Due Date",
        "Schedule",
        "End Date",
    ]

    for property_name in preferred_names:

        prop = properties.get(
            property_name,
            {}
        )

        if (
            prop.get(
                "type"
            )
            == "date"
            and prop.get(
                "date"
            )
        ):

            return (
                property_name,
                prop.get(
                    "date"
                )
            )

    for property_name, prop in (
        properties.items()
    ):

        if (
            prop.get(
                "type"
            )
            == "date"
            and prop.get(
                "date"
            )
        ):

            return (
                property_name,
                prop.get(
                    "date"
                )
            )

    return (
        None,
        None
    )


def parse_notion_datetime(
    value
):

    if not value:
        return None

    try:

        parsed = datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00"
            )
        )

    except ValueError:

        return None

    if parsed.tzinfo is None:

        parsed = parsed.replace(
            tzinfo=LOCAL_TIMEZONE
        )

    else:

        parsed = parsed.astimezone(
            LOCAL_TIMEZONE
        )

    return parsed


def get_forecast_task(
    properties
):

    preferred_names = [
        "Task",
        "Activity",
        "Forecast",
        "Name",
        "Title",
    ]

    for property_name in preferred_names:

        prop = properties.get(
            property_name,
            {}
        )

        value = get_property_plain_text(
            prop
        )

        if value:
            return value

    for prop in properties.values():

        if prop.get(
            "type"
        ) == "title":

            value = get_property_plain_text(
                prop
            )

            if value:
                return value

    return "Forecast Activity"


def get_related_page_info(
    page_id
):

    url = (
        "https://api.notion.com/v1/pages/"
        f"{page_id}"
    )

    try:

        response = requests.get(
            url,
            headers=NOTION_HEADERS,
            timeout=15
        )

    except requests.RequestException:

        return {}

    if response.status_code != 200:

        return {}

    return response.json().get(
        "properties",
        {}
    )


def build_project_label_from_properties(
    properties
):

    project_number = ""

    for property_name in [
        "Number",
        "Project Number",
    ]:

        project_number = (
            get_property_plain_text(
                properties.get(
                    property_name,
                    {}
                )
            )
        )

        if project_number:
            break

    project_name = ""

    for property_name in [
        "Project Name",
        "Name",
    ]:

        project_name = (
            get_property_plain_text(
                properties.get(
                    property_name,
                    {}
                )
            )
        )

        if project_name:
            break

    if (
        project_number
        and project_name
    ):

        return (
            f"{project_number} - "
            f"{project_name}"
        )

    if project_number:
        return project_number

    if project_name:
        return project_name

    for prop in properties.values():

        value = get_property_plain_text(
            prop
        )

        if value:
            return value

    return ""


def get_project_label_lookup():

    lookup = {}

    for page in get_all_projects():

        page_id = page.get(
            "id"
        )

        if not page_id:
            continue

        properties = page.get(
            "properties",
            {}
        )

        lookup[
            page_id
        ] = (
            build_project_label_from_properties(
                properties
            )
        )

    return lookup


def get_forecast_project(
    properties
):

    preferred_names = [
        "Project",
        "Projects",
        "Project Number",
        "Project Name",
    ]

    for property_name in preferred_names:

        prop = properties.get(
            property_name,
            {}
        )

        if not prop:
            continue

        if prop.get(
            "type"
        ) == "relation":

            relation = prop.get(
                "relation",
                []
            )

            if relation:

                related_page_id = (
                    relation[0].get(
                        "id"
                    )
                )

                if related_page_id:

                    project_lookup = (
                        get_project_label_lookup()
                    )

                    label = (
                        project_lookup.get(
                            related_page_id,
                            ""
                        )
                    )

                    if label:
                        return label

                    # Fallback for a relation not present in the
                    # cached Projects query.
                    related_properties = (
                        get_related_page_info(
                            related_page_id
                        )
                    )

                    label = (
                        build_project_label_from_properties(
                            related_properties
                        )
                    )

                    if label:
                        return label

        value = get_property_plain_text(
            prop
        )

        if value:
            return value

    return ""


def get_all_forecast_records():

    if not NOTION_FORECAST_DATA_SOURCE_ID:
        return []

    return query_data_source(
        NOTION_FORECAST_DATA_SOURCE_ID
    )


def get_upcoming_forecasts_for_logged_user():

    if not NOTION_FORECAST_DATA_SOURCE_ID:
        return []

    pages = get_all_forecast_records()

    upcoming = []

    today = datetime.now(
        LOCAL_TIMEZONE
    ).date()

    is_manager = (
        normalize_text(
            st.session_state.user_role
        )
        == "manager"
    )

    manager_branch_users = []

    if is_manager:

        manager_branch = (
            get_logged_manager_branch()
        )

        if manager_branch:

            st.session_state.user_branch = (
                manager_branch
            )

            manager_branch_users = (
                get_users_in_branch(
                    manager_branch
                )
            )

    for page in pages:

        properties = page.get(
            "properties",
            {}
        )

        done = get_checkbox(
            properties,
            "Done",
            False
        )

        if done:
            continue

        designer_prop = properties.get(
            "Designer",
            {}
        )

        # Standard users see only their own activities.
        # Managers see activities assigned to users in
        # the same Branch as the logged-in Manager.
        if is_manager:

            if not manager_branch_users:
                continue

            prop_type = designer_prop.get(
                "type"
            )

            visible_to_manager = False

            allowed_ids = {
                user.get(
                    "id"
                )
                for user in manager_branch_users
                if user.get(
                    "id"
                )
            }

            if prop_type in {
                "select",
                "status",
                "title",
                "rich_text",
                "email",
                "number",
            }:

                designer_value = (
                    get_property_plain_text(
                        designer_prop
                    )
                )

                visible_to_manager = any(
                    identity_matches_user(
                        designer_value,
                        user[
                            "identifiers"
                        ]
                    )
                    for user in manager_branch_users
                )

            elif prop_type == "people":

                for person in designer_prop.get(
                    "people",
                    []
                ):

                    person_id = (
                        person.get(
                            "id"
                        )
                        or ""
                    )

                    person_name = (
                        person.get(
                            "name"
                        )
                        or ""
                    )

                    person_email = (
                        (
                            person.get(
                                "person"
                            )
                            or {}
                        ).get(
                            "email"
                        )
                        or ""
                    )

                    if (
                        person_id in allowed_ids
                        or any(
                            identity_matches_user(
                                person_name,
                                user[
                                    "identifiers"
                                ]
                            )
                            or identity_matches_user(
                                person_email,
                                user[
                                    "identifiers"
                                ]
                            )
                            for user in manager_branch_users
                        )
                    ):

                        visible_to_manager = True
                        break

            elif prop_type == "relation":

                relation_ids = {
                    item.get(
                        "id"
                    )
                    for item in designer_prop.get(
                        "relation",
                        []
                    )
                    if item.get(
                        "id"
                    )
                }

                visible_to_manager = bool(
                    relation_ids
                    & allowed_ids
                )

            if not visible_to_manager:
                continue

        else:

            if not property_matches_logged_user(
                designer_prop
            ):
                continue

        _, date_data = (
            get_forecast_date_property(
                properties
            )
        )

        if not date_data:
            continue

        start_value = date_data.get(
            "start"
        )

        event_datetime = (
            parse_notion_datetime(
                start_value
            )
        )

        if not event_datetime:
            continue

        if event_datetime.date() < today:
            continue

        days_until_event = (
            event_datetime.date()
            - today
        ).days

        # Show only Forecast activities occurring
        # from today through the next 7 days.
        if days_until_event > 7:
            continue

        upcoming.append(
            {
                "date":
                    event_datetime,

                "project":
                    get_forecast_project(
                        properties
                    ),

                "task":
                    get_forecast_task(
                        properties
                    ),
            }
        )

    upcoming.sort(
        key=lambda item:
            item["date"]
    )

    return upcoming


def render_forecast_dashboard():

    st.subheader(
        "📅 Upcoming Forecast"
    )

    if not NOTION_FORECAST_DATA_SOURCE_ID:

        st.warning(
            "Forecast dashboard is not configured. "
            "Add NOTION_FORECAST_DATA_SOURCE_ID "
            "to Streamlit secrets."
        )

        return

    with st.spinner(
        "Loading upcoming activities..."
    ):

        forecasts = (
            get_upcoming_forecasts_for_logged_user()
        )

    today = datetime.now(
        LOCAL_TIMEZONE
    ).date()

    today_count = sum(
        1
        for item in forecasts
        if item["date"].date()
        == today
    )

    next_7_days = sum(
        1
        for item in forecasts
        if 0
        <= (
            item["date"].date()
            - today
        ).days
        <= 7
    )

    col1, col2, col3 = (
        st.columns(3)
    )

    with col1:

        st.metric(
            "Open Activities",
            len(
                forecasts
            )
        )

    with col2:

        st.metric(
            "Due Today",
            today_count
        )

    with col3:

        st.metric(
            "Next 7 Days",
            next_7_days
        )

    if not forecasts:

        st.success(
            "You have no upcoming "
            "open forecast activities."
        )

        return

    st.markdown(
        "#### Next Activities"
    )

    rows = []

    for item in forecasts[:15]:

        event_datetime = (
            item["date"]
        )

        if (
            event_datetime.hour == 0
            and event_datetime.minute == 0
        ):

            date_text = (
                event_datetime
                .strftime(
                    "%m/%d/%Y"
                )
            )

        else:

            date_text = (
                event_datetime
                .strftime(
                    "%m/%d/%Y %I:%M %p"
                )
            )

        rows.append(
            {
                "Date":
                    date_text,

                "Project":
                    item["project"]
                    or "—",

                "Activity":
                    item["task"],
            }
        )

    st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True
    )

    if len(forecasts) > 15:

        st.caption(
            f"Showing the next 15 of "
            f"{len(forecasts)} open activities. "
            "Open Forecast to see the complete schedule."
        )



# =========================================================
# ACTIVE PROJECT PROGRESS
# =========================================================

def get_projects_schema():

    if not NOTION_PROJECTS_DATA_SOURCE_ID:
        return {}

    url = (
        "https://api.notion.com/v1/data_sources/"
        f"{NOTION_PROJECTS_DATA_SOURCE_ID}"
    )

    try:

        response = requests.get(
            url,
            headers=NOTION_HEADERS,
            timeout=20
        )

    except requests.RequestException:

        return {}

    if response.status_code != 200:

        return {}

    return response.json()


def get_all_projects():

    if not NOTION_PROJECTS_DATA_SOURCE_ID:
        return []

    return query_data_source(
        NOTION_PROJECTS_DATA_SOURCE_ID
    )


def get_project_checkbox_fields():

    schema = get_projects_schema()

    properties = schema.get(
        "properties",
        {}
    )

    checkbox_fields = []

    for (
        property_name,
        property_data
    ) in properties.items():

        if (
            property_data.get("type")
            == "checkbox"
        ):

            checkbox_fields.append(
                property_name
            )

    return checkbox_fields


def get_active_projects_for_logged_user():

    pages = get_all_projects()

    projects = []

    checkbox_fields = (
        get_project_checkbox_fields()
    )

    is_manager = (
        normalize_text(
            st.session_state.user_role
        )
        == "manager"
    )

    manager_branch_users = []

    if is_manager:

        manager_branch = (
            get_logged_manager_branch()
        )

        if manager_branch:

            st.session_state.user_branch = (
                manager_branch
            )

            manager_branch_users = (
                get_users_in_branch(
                    manager_branch
                )
            )

    for page in pages:

        properties = page.get(
            "properties",
            {}
        )

        # -------------------------------------------------
        # USER FILTER
        # -------------------------------------------------

        designer_prop = properties.get(
            "Designer",
            {}
        )

        # Standard users see only Projects assigned to them.
        # Managers see Projects assigned to users in
        # the same Branch as the logged-in Manager.
        if is_manager:

            if not manager_branch_users:
                continue

            prop_type = designer_prop.get(
                "type"
            )

            visible_to_manager = False

            allowed_ids = {
                user.get(
                    "id"
                )
                for user in manager_branch_users
                if user.get(
                    "id"
                )
            }

            if prop_type in {
                "select",
                "status",
                "title",
                "rich_text",
                "email",
                "number",
            }:

                designer_value = (
                    get_property_plain_text(
                        designer_prop
                    )
                )

                visible_to_manager = any(
                    identity_matches_user(
                        designer_value,
                        user[
                            "identifiers"
                        ]
                    )
                    for user in manager_branch_users
                )

            elif prop_type == "people":

                for person in designer_prop.get(
                    "people",
                    []
                ):

                    person_id = (
                        person.get(
                            "id"
                        )
                        or ""
                    )

                    person_name = (
                        person.get(
                            "name"
                        )
                        or ""
                    )

                    person_email = (
                        (
                            person.get(
                                "person"
                            )
                            or {}
                        ).get(
                            "email"
                        )
                        or ""
                    )

                    if (
                        person_id in allowed_ids
                        or any(
                            identity_matches_user(
                                person_name,
                                user[
                                    "identifiers"
                                ]
                            )
                            or identity_matches_user(
                                person_email,
                                user[
                                    "identifiers"
                                ]
                            )
                            for user in manager_branch_users
                        )
                    ):

                        visible_to_manager = True
                        break

            elif prop_type == "relation":

                relation_ids = {
                    item.get(
                        "id"
                    )
                    for item in designer_prop.get(
                        "relation",
                        []
                    )
                    if item.get(
                        "id"
                    )
                }

                visible_to_manager = bool(
                    relation_ids
                    & allowed_ids
                )

            if not visible_to_manager:
                continue

        else:

            if not property_matches_logged_user(
                designer_prop
            ):
                continue

        # -------------------------------------------------
        # INSTALLED FILTER
        # -------------------------------------------------

        installed = get_checkbox(
            properties,
            "Installed",
            False
        )

        if installed:

            continue

        # -------------------------------------------------
        # PROJECT NUMBER
        # -------------------------------------------------

        project_number = (
            get_property_plain_text(
                properties.get(
                    "Number",
                    {}
                )
            )
        )

        if not project_number:

            project_number = (
                get_property_plain_text(
                    properties.get(
                        "Project Number",
                        {}
                    )
                )
            )

        # -------------------------------------------------
        # PROJECT NAME
        # -------------------------------------------------

        project_name = (
            get_property_plain_text(
                properties.get(
                    "Project Name",
                    {}
                )
            )
        )

        if not project_name:

            project_name = (
                get_property_plain_text(
                    properties.get(
                        "Name",
                        {}
                    )
                )
            )

        # -------------------------------------------------
        # CHECKBOX VALUES
        # -------------------------------------------------

        milestones = {}

        for field_name in checkbox_fields:

            milestones[
                field_name
            ] = get_checkbox(
                properties,
                field_name,
                False
            )

        projects.append(
            {
                "number":
                    project_number,

                "name":
                    project_name,

                "milestones":
                    milestones,
            }
        )

    projects.sort(
        key=lambda item:
            str(
                item["number"]
            ).casefold()
    )

    return (
        projects,
        checkbox_fields
    )


def render_active_project_progress():

    st.subheader(
        "📋 Active Project Progress"
    )

    st.caption(
        "Current progress for your active projects."
    )

    if (
        normalize_text(
            st.session_state.user_role
        )
        == "manager"
    ):

        manager_branch = (
            get_logged_manager_branch()
        )

        if manager_branch:

            branch_users = (
                get_users_in_branch(
                    manager_branch
                )
            )

            branch_user_names = [
                user.get(
                    "name"
                )
                or user.get(
                    "email"
                )
                or "Unknown"
                for user in branch_users
            ]

            st.caption(
                f"Manager Branch: {manager_branch} | "
                f"Users in Branch: {len(branch_users)} | "
                f"{', '.join(branch_user_names)}"
            )

    if not NOTION_PROJECTS_DATA_SOURCE_ID:

        st.warning(
            "Project progress information "
            "is not configured."
        )

        return

    with st.spinner(
        "Loading project progress..."
    ):

        (
            projects,
            checkbox_fields
        ) = (
            get_active_projects_for_logged_user()
        )

    if not projects:

        st.success(
            "You have no active projects."
        )

        return

    # =====================================================
    # FIXED MILESTONE ORDER
    # =====================================================

    milestone_config = [
        {
            "display_name": "Predesign Meeting",
            "aliases": [
                "Predesign Meeting",
                "Predesgin Meeting",
            ],
        },
        {
            "display_name": "Sales Review Meeting",
            "aliases": [
                "Sales Review Meeting",
            ],
        },
        {
            "display_name": "Design Review Meeting",
            "aliases": [
                "Design Review Meeting",
                "Design Reviewm Meeting",
            ],
        },
        {
            "display_name": "AML sent to QFS",
            "aliases": [
                "AML sent to QFS",
                "AML Sent to QFS",
            ],
        },
        {
            "display_name": "Submittal",
            "aliases": [
                "Submittal",
            ],
        },
        {
            "display_name": "Stocklist sent to QFS",
            "aliases": [
                "Stocklist sent to QFS",
                "Stocklist Sent to QFS",
            ],
        },
        {
            "display_name": "Foreman Package",
            "aliases": [
                "Foreman Package",
                "Foreman's Package",
                "Foreman Package Sent",
            ],
        },
    ]

    normalized_checkbox_lookup = {
        normalize_text(field_name):
            field_name
        for field_name in checkbox_fields
    }

    resolved_milestones = []

    for milestone in milestone_config:

        actual_field_name = None

        for alias in milestone["aliases"]:

            normalized_alias = normalize_text(
                alias
            )

            if (
                normalized_alias
                in normalized_checkbox_lookup
            ):

                actual_field_name = (
                    normalized_checkbox_lookup[
                        normalized_alias
                    ]
                )

                break

        resolved_milestones.append(
            {
                "display_name":
                    milestone[
                        "display_name"
                    ],

                "field_name":
                    actual_field_name,
            }
        )

    # =====================================================
    # SUMMARY METRICS
    # =====================================================

    total_projects = len(
        projects
    )

    total_completed_steps = 0

    total_possible_steps = (
        total_projects
        * len(
            resolved_milestones
        )
    )

    for project in projects:

        for milestone in resolved_milestones:

            field_name = milestone[
                "field_name"
            ]

            if not field_name:
                continue

            if project[
                "milestones"
            ].get(
                field_name,
                False
            ):

                total_completed_steps += 1

    if total_possible_steps > 0:

        overall_progress = (
            total_completed_steps
            / total_possible_steps
            * 100
        )

    else:

        overall_progress = 0.0

    col1, col2, col3 = (
        st.columns(3)
    )

    with col1:

        st.metric(
            "Active Projects",
            total_projects
        )

    with col2:

        st.metric(
            "Completed Steps",
            total_completed_steps
        )

    with col3:

        st.metric(
            "Overall Progress",
            f"{overall_progress:.0f}%"
        )

    # =====================================================
    # BUILD TABLE
    # =====================================================

    rows = []

    for project in projects:

        row = {
            "Project":
                project[
                    "number"
                ]
                or "—",

            "Project Name":
                project[
                    "name"
                ]
                or "—",
        }

        completed_steps = 0

        for milestone in resolved_milestones:

            display_name = milestone[
                "display_name"
            ]

            field_name = milestone[
                "field_name"
            ]

            completed = False

            if field_name:

                completed = (
                    project[
                        "milestones"
                    ].get(
                        field_name,
                        False
                    )
                )

            row[
                display_name
            ] = (
                "✅"
                if completed
                else "⬜"
            )

            if completed:

                completed_steps += 1

        progress = (
            completed_steps
            / len(
                resolved_milestones
            )
            * 100
            if resolved_milestones
            else 0
        )

        row[
            "Progress"
        ] = (
            f"{progress:.0f}%"
        )

        rows.append(
            row
        )

    # =====================================================
    # EXACT COLUMN ORDER
    # =====================================================

    fixed_column_order = [
        "Project",
        "Project Name",
        "Predesign Meeting",
        "Sales Review Meeting",
        "Design Review Meeting",
        "AML sent to QFS",
        "Submittal",
        "Stocklist sent to QFS",
        "Foreman Package",
        "Progress",
    ]

    st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True,
        column_order=fixed_column_order,

        column_config={
            "Project":
                st.column_config.TextColumn(
                    "Project",
                    width="small"
                ),

            "Project Name":
                st.column_config.TextColumn(
                    "Project Name",
                    width="medium"
                ),

            "Predesign Meeting":
                st.column_config.TextColumn(
                    "Predesign Meeting",
                    width="small"
                ),

            "Sales Review Meeting":
                st.column_config.TextColumn(
                    "Sales Review Meeting",
                    width="small"
                ),

            "Design Review Meeting":
                st.column_config.TextColumn(
                    "Design Review Meeting",
                    width="small"
                ),

            "AML sent to QFS":
                st.column_config.TextColumn(
                    "AML sent to QFS",
                    width="small"
                ),

            "Submittal":
                st.column_config.TextColumn(
                    "Submittal",
                    width="small"
                ),

            "Stocklist sent to QFS":
                st.column_config.TextColumn(
                    "Stocklist sent to QFS",
                    width="small"
                ),

            "Foreman Package":
                st.column_config.TextColumn(
                    "Foreman Package",
                    width="small"
                ),

            "Progress":
                st.column_config.TextColumn(
                    "Progress",
                    width="small"
                ),
        },
    )

    st.caption(
        "✅ Completed   |   ⬜ Pending"
    )


# =========================================================
# USERS / BRANCH OPTIONS
# =========================================================

def get_user_branch_options():

    return BRANCH_OPTIONS.copy()


# =========================================================
# GET USER BY EMAIL
# =========================================================

def get_user_by_email(
    email
):

    return get_profile_by_email(
        email
    )


# =========================================================
# SUPABASE AUTH USER LOOKUP
# =========================================================

def get_auth_user_by_email(
    email
):

    target_email = (
        email
        or ""
    ).strip().lower()

    if not target_email:
        return None

    try:

        response = requests.get(
            (
                f"{SUPABASE_URL}"
                "/auth/v1/admin/users"
            ),
            headers={
                "apikey":
                    SUPABASE_SECRET_KEY,

                "Authorization":
                    (
                        "Bearer "
                        f"{SUPABASE_SECRET_KEY}"
                    ),
            },
            params={
                "page": 1,
                "per_page": 1000,
            },
            timeout=20,
        )

    except requests.RequestException:

        return None

    if response.status_code != 200:
        return None

    data = response.json()

    users = (
        data.get(
            "users",
            []
        )
        if isinstance(
            data,
            dict
        )
        else []
    )

    for user in users:

        user_email = (
            user.get(
                "email",
                ""
            )
            or ""
        ).strip().lower()

        if user_email == target_email:
            return user

    return None


def update_existing_auth_user_for_account(
    user_id,
    email,
    password,
    name
):

    if not user_id:
        return False, "Authentication User ID was not found."

    try:

        response = requests.put(
            (
                f"{SUPABASE_URL}"
                "/auth/v1/admin/users/"
                f"{user_id}"
            ),
            headers={
                "apikey":
                    SUPABASE_SECRET_KEY,

                "Authorization":
                    (
                        "Bearer "
                        f"{SUPABASE_SECRET_KEY}"
                    ),

                "Content-Type":
                    "application/json",
            },
            json={
                "email":
                    email.strip().lower(),

                "password":
                    password,

                "email_confirm":
                    True,

                "user_metadata": {
                    "name":
                        name.strip(),
                },
            },
            timeout=20,
        )

    except requests.RequestException as error:

        return (
            False,
            str(
                error
            ),
        )

    if response.status_code not in {
        200,
        201,
    }:

        try:

            detail = (
                response.json()
            )

        except Exception:

            detail = (
                response.text
            )

        return (
            False,
            str(
                detail
            ),
        )

    return True, None


# =========================================================
# CREATE USER
# =========================================================

def create_user_in_notion(
    name,
    email,
    employee_number,
    password,
    branch
):
    """
    Create/complete a Wiginton Tools account using:
      1. Supabase Authentication
      2. public.profiles

    If an Authentication user already exists but no profile
    exists yet, the account is completed instead of rejected.
    """

    email = (
        email
        .strip()
        .lower()
    )

    # -----------------------------------------------------
    # 1. PROFILE ALREADY EXISTS
    # -----------------------------------------------------

    existing_profile = (
        get_profile_by_email(
            email
        )
    )

    if existing_profile:

        return (
            False,
            (
                "An account already exists for this email "
                "in the current Supabase profiles table."
            )
        )

    # -----------------------------------------------------
    # 2. CHECK SUPABASE AUTH
    # -----------------------------------------------------

    existing_auth_user = (
        get_auth_user_by_email(
            email
        )
    )

    if existing_auth_user:

        user_id = (
            existing_auth_user.get(
                "id"
            )
        )

        # The Auth user exists but profiles does not.
        # Complete/migrate the account and set the password
        # entered in the Create Account screen.
        auth_updated, auth_error = (
            update_existing_auth_user_for_account(
                user_id=
                    user_id,

                email=
                    email,

                password=
                    password,

                name=
                    name,
            )
        )

        if not auth_updated:

            return (
                False,
                (
                    "The email already exists in Supabase "
                    "Authentication, but the account could "
                    "not be completed. "
                    f"{auth_error or ''}"
                ).strip()
            )

        success, profile_error = (
            insert_profile(
                user_id=
                    user_id,

                name=
                    name,

                email=
                    email,

                employee_number=
                    employee_number,

                role=
                    "Designer",

                branch=
                    branch,

                active=
                    True,
            )
        )

        if not success:

            return (
                False,
                (
                    "The Authentication user exists, but "
                    "the profile could not be created. "
                    f"{profile_error or ''}"
                ).strip()
            )

        return (
            True,
            (
                "Account completed successfully. "
                "The existing Supabase Authentication user "
                "has now been linked to a new profile."
            )
        )

    # -----------------------------------------------------
    # 3. CREATE BRAND-NEW AUTH USER
    # -----------------------------------------------------

    auth_user, auth_error = (
        create_auth_user(
            email,
            password,
            name
        )
    )

    if not auth_user:

        return (
            False,
            auth_error
            or "Unable to create account."
        )

    user_id = getattr(
        auth_user,
        "id",
        None
    )

    # -----------------------------------------------------
    # 4. CREATE PROFILE
    # -----------------------------------------------------

    success, profile_error = (
        insert_profile(
            user_id=
                user_id,

            name=
                name,

            email=
                email,

            employee_number=
                employee_number,

            role=
                "Designer",

            branch=
                branch,

            active=
                True,
        )
    )

    if not success:

        # Roll back Auth creation when profile creation fails.
        delete_auth_user(
            user_id
        )

        return (
            False,
            (
                "Authentication user was created, "
                "but the profile could not be saved. "
                f"{profile_error or ''}"
            ).strip()
        )

    return (
        True,
        "Account created successfully."
    )


# =========================================================
# AUTHENTICATE USER
# =========================================================

def authenticate_user(
    email,
    password
):

    st.session_state[
        "login_error_detail"
    ] = None

    auth_result = (
        authenticate_with_supabase_auth(
            email,
            password
        )
    )

    if not auth_result:

        st.session_state[
            "login_error_detail"
        ] = (
            "Supabase Auth returned no response."
        )

        return None

    if auth_result.get(
        "error"
    ):

        st.session_state[
            "login_error_detail"
        ] = (
            auth_result.get(
                "error"
            )
        )

        return None

    user_id = (
        auth_result.get(
            "id"
        )
    )

    profile = get_profile_by_id(
        user_id
    )

    if not profile:

        profile_error = (
            st.session_state.get(
                "supabase_profile_error"
            )
        )

        if profile_error:

            st.session_state[
                "login_error_detail"
            ] = (
                "Authentication succeeded, but "
                "public.profiles could not be read: "
                f"{profile_error}"
            )

        else:

            st.session_state[
                "login_error_detail"
            ] = (
                "Authentication succeeded, but no matching "
                "record was found in public.profiles."
            )

        return None

    if not profile.get(
        "active",
        True
    ):

        st.session_state[
            "login_error_detail"
        ] = (
            "This user profile is inactive."
        )

        return None

    return {
        "id":
            profile.get(
                "id"
            ),

        "name":
            profile.get(
                "name",
                ""
            ),

        "email":
            profile.get(
                "email",
                auth_result.get(
                    "email",
                    ""
                )
            ),

        "employee_number":
            profile.get(
                "employee_number",
                ""
            ),

        "role":
            profile.get(
                "role",
                "Designer"
            ),

        "branch":
            profile.get(
                "branch",
                ""
            ),
    }



# =========================================================
# PASSWORD RESET TOKEN
# =========================================================

def generate_reset_token(
    profile
):

    now_timestamp = int(
        datetime.now(
            timezone.utc
        ).timestamp()
    )

    expiration_timestamp = int(
        (
            datetime.now(
                timezone.utc
            )
            + timedelta(
                minutes=30
            )
        ).timestamp()
    )

    nonce = (
        secrets.token_urlsafe(
            24
        )
    )

    payload = {
        "purpose":
            "password_reset",

        "id":
            str(
                profile.get(
                    "id"
                )
            ),

        "email":
            profile.get(
                "email",
                ""
            ),

        "nonce":
            nonce,

        "iat":
            now_timestamp,

        "exp":
            expiration_timestamp,
    }

    encoded_payload = (
        base64.urlsafe_b64encode(
            json.dumps(
                payload,
                separators=(
                    ",",
                    ":"
                ),
                sort_keys=True
            )
            .encode(
                "utf-8"
            )
        )
        .decode(
            "utf-8"
        )
        .rstrip(
            "="
        )
    )

    signature = hmac.new(
        AUTH_SECRET.encode(
            "utf-8"
        ),
        encoded_payload.encode(
            "utf-8"
        ),
        hashlib.sha256
    ).hexdigest()

    # Store the reset nonce in Supabase Auth metadata so the
    # reset link becomes one-time-use without adding columns
    # to public.profiles.
    try:

        (
            supabase_admin
            .auth
            .admin
            .update_user_by_id(
                str(
                    profile[
                        "id"
                    ]
                ),
                {
                    "user_metadata": {
                        "password_reset_nonce":
                            nonce,
                    }
                }
            )
        )

    except Exception:

        return None

    return (
        f"{encoded_payload}."
        f"{signature}"
    )


def decode_reset_token(
    token
):

    if not token:
        return None

    try:

        encoded_payload, signature = (
            token.split(
                ".",
                1
            )
        )

        expected_signature = hmac.new(
            AUTH_SECRET.encode(
                "utf-8"
            ),
            encoded_payload.encode(
                "utf-8"
            ),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(
            signature,
            expected_signature
        ):
            return None

        padding = (
            "="
            * (
                -len(
                    encoded_payload
                )
                % 4
            )
        )

        payload = json.loads(
            base64.urlsafe_b64decode(
                (
                    encoded_payload
                    + padding
                ).encode(
                    "utf-8"
                )
            )
            .decode(
                "utf-8"
            )
        )

        if (
            payload.get(
                "purpose"
            )
            != "password_reset"
        ):
            return None

        now_timestamp = int(
            datetime.now(
                timezone.utc
            ).timestamp()
        )

        if (
            now_timestamp
            >= int(
                payload.get(
                    "exp",
                    0
                )
            )
        ):
            return None

        return payload

    except Exception:

        return None


def get_auth_user_by_id(
    user_id
):

    try:

        response = (
            supabase_admin
            .auth
            .admin
            .get_user_by_id(
                str(
                    user_id
                )
            )
        )

    except Exception:

        return None

    return getattr(
        response,
        "user",
        None
    )


def create_password_reset(
    email
):

    email = (
        email
        or ""
    ).strip().lower()

    st.session_state[
        "password_reset_detail"
    ] = None

    profile = (
        get_profile_by_email(
            email
        )
    )

    if not profile:

        profile_error = (
            st.session_state.get(
                "supabase_profile_error"
            )
        )

        if profile_error:

            st.session_state[
                "password_reset_detail"
            ] = (
                "Unable to read public.profiles: "
                f"{profile_error}"
            )

            return {
                "success": False,
                "account_found": False,
                "token": None,
            }

        st.session_state[
            "password_reset_detail"
        ] = (
            "No matching profile was found for this email."
        )

        return {
            "success": True,
            "account_found": False,
            "token": None,
        }

    if not profile.get(
        "active",
        True
    ):

        st.session_state[
            "password_reset_detail"
        ] = (
            "The matching profile is inactive."
        )

        return {
            "success": True,
            "account_found": False,
            "token": None,
        }

    auth_user = (
        get_auth_user_by_id(
            profile.get(
                "id"
            )
        )
    )

    if not auth_user:

        st.session_state[
            "password_reset_detail"
        ] = (
            "Profile found, but the matching "
            "Supabase Authentication user was not found."
        )

        return {
            "success": False,
            "account_found": True,
            "token": None,
        }

    token = (
        generate_reset_token(
            profile
        )
    )

    if not token:

        st.session_state[
            "password_reset_detail"
        ] = (
            "The reset token could not be generated."
        )

        return {
            "success": False,
            "account_found": True,
            "token": None,
        }

    st.session_state[
        "password_reset_detail"
    ] = (
        "Profile and Authentication user found. "
        "Reset token created."
    )

    return {
        "success": True,
        "account_found": True,
        "token": token,
    }



def find_user_by_reset_token(
    token
):

    payload = decode_reset_token(
        token
    )

    if not payload:
        return None

    profile = get_profile_by_id(
        payload.get(
            "id"
        )
    )

    if not profile:
        return None

    if (
        normalize_text(
            profile.get(
                "email"
            )
        )
        != normalize_text(
            payload.get(
                "email"
            )
        )
    ):

        return None

    auth_user = get_auth_user_by_id(
        profile[
            "id"
        ]
    )

    if not auth_user:
        return None

    user_metadata = (
        getattr(
            auth_user,
            "user_metadata",
            None
        )
        or {}
    )

    if (
        user_metadata.get(
            "password_reset_nonce"
        )
        != payload.get(
            "nonce"
        )
    ):

        return None

    return profile



# =========================================================
# SEND RESET EMAIL
# =========================================================

def send_reset_email(
    email,
    reset_link
):

    if not RESEND_API_KEY:

        return (
            False,
            "RESEND_API_KEY is not configured."
        )

    if not RESET_EMAIL_SENDER:

        return (
            False,
            "RESET_EMAIL_SENDER is not configured."
        )

    try:

        result = (
            resend.Emails.send(
                {
                    "from":
                        RESET_EMAIL_SENDER,

                    "to": [
                        email
                    ],

                    "subject":
                        "Wiginton Tools - Password Reset",

                    "html": f"""
                    <div style="
                        font-family: Arial, Helvetica, sans-serif;
                        max-width: 600px;
                        margin: auto;
                        padding: 30px;
                        color: #222222;
                    ">

                        <h2>
                            Wiginton Tools
                        </h2>

                        <p>
                            We received a request to reset
                            your Wiginton Tools password.
                        </p>

                        <p>
                            Click the button below to create
                            a new password.
                        </p>

                        <p style="
                            margin: 30px 0;
                        ">

                            <a
                                href="{reset_link}"
                                style="
                                    background: #0068c9;
                                    color: white;
                                    padding: 12px 22px;
                                    text-decoration: none;
                                    border-radius: 6px;
                                    display: inline-block;
                                "
                            >
                                Reset Password
                            </a>

                        </p>

                        <p>
                            This link is valid for 30 minutes.
                        </p>

                        <p>
                            If you did not request this password
                            reset, you can ignore this email.
                        </p>

                        <hr>

                        <p style="
                            font-size: 12px;
                            color: #777777;
                        ">
                            Wiginton Tools
                        </p>

                    </div>
                    """
                }
            )
        )

        email_id = None

        if isinstance(
            result,
            dict
        ):

            email_id = (
                result.get(
                    "id"
                )
            )

        else:

            email_id = getattr(
                result,
                "id",
                None
            )

        return (
            True,
            email_id
            or "Accepted by Resend."
        )

    except Exception as error:

        return (
            False,
            str(
                error
            )
        )



# =========================================================
# PERSISTENT LOGIN HELPERS
# =========================================================

def get_auth_expiration():

    now = datetime.now(
        LOCAL_TIMEZONE
    )

    ten_hours_later = (
        now
        + timedelta(
            hours=AUTH_DURATION_HOURS
        )
    )

    next_midnight = (
        now.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )
        + timedelta(
            days=1
        )
    )

    return min(
        ten_hours_later,
        next_midnight
    )


def encode_auth_payload(payload):

    payload_json = json.dumps(
        payload,
        separators=(",", ":"),
        sort_keys=True
    )

    return (
        base64.urlsafe_b64encode(
            payload_json.encode(
                "utf-8"
            )
        )
        .decode(
            "utf-8"
        )
    )


def decode_auth_payload(encoded_payload):

    padding = (
        "="
        * (-len(encoded_payload) % 4)
    )

    payload_json = (
        base64.urlsafe_b64decode(
            (
                encoded_payload
                + padding
            ).encode(
                "utf-8"
            )
        )
        .decode(
            "utf-8"
        )
    )

    return json.loads(
        payload_json
    )


def create_auth_token(user):

    expires = get_auth_expiration()

    payload = {
        "id": user.get("id") or "",
        "email": (
            user.get("email")
            or ""
        ).strip().lower(),
        "exp": int(
            expires.timestamp()
        ),
    }

    encoded_payload = (
        encode_auth_payload(
            payload
        )
    )

    signature = hmac.new(
        AUTH_SECRET.encode(
            "utf-8"
        ),
        encoded_payload.encode(
            "utf-8"
        ),
        hashlib.sha256
    ).hexdigest()

    token = (
        f"{encoded_payload}."
        f"{signature}"
    )

    return token, expires


def validate_auth_token(
    token
):

    if not token:
        return None

    try:

        encoded_payload, signature = (
            token.split(
                ".",
                1
            )
        )

        expected_signature = hmac.new(
            AUTH_SECRET.encode(
                "utf-8"
            ),
            encoded_payload.encode(
                "utf-8"
            ),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(
            signature,
            expected_signature
        ):
            return None

        payload = decode_auth_payload(
            encoded_payload
        )

        expiration_timestamp = int(
            payload.get(
                "exp",
                0
            )
        )

        now_timestamp = int(
            datetime.now(
                timezone.utc
            ).timestamp()
        )

        if (
            now_timestamp
            >= expiration_timestamp
        ):
            return None

        user_id = (
            payload.get(
                "id"
            )
        )

        email = (
            payload.get(
                "email",
                ""
            )
            .strip()
            .lower()
        )

        if not user_id:
            return None

        profile = get_profile_by_id(
            user_id
        )

        if not profile:
            return None

        if not profile.get(
            "active",
            True
        ):
            return None

        if (
            email
            and normalize_text(
                profile.get(
                    "email"
                )
            )
            != normalize_text(
                email
            )
        ):
            return None

        return {
            "id":
                profile.get(
                    "id"
                ),

            "name":
                profile.get(
                    "name",
                    ""
                ),

            "email":
                profile.get(
                    "email",
                    ""
                ),

            "employee_number":
                profile.get(
                    "employee_number",
                    ""
                ),

            "role":
                profile.get(
                    "role",
                    "Designer"
                ),

            "branch":
                profile.get(
                    "branch",
                    ""
                ),
        }

    except Exception:

        return None



def set_authenticated_user(user):

    st.session_state.authenticated = True

    st.session_state.user_id = (
        user.get("id")
    )

    st.session_state.user_name = (
        user.get("name")
    )

    st.session_state.user_email = (
        user.get("email")
    )

    st.session_state.user_role = (
        user.get("role")
    )

    st.session_state.user_branch = (
        user.get("branch")
    )


def save_persistent_login(user):

    token, expires = (
        create_auth_token(
            user
        )
    )

    cookie_controller.set(
        AUTH_COOKIE_NAME,
        token,
        path="/",
        expires=expires,
        secure=AUTH_COOKIE_SECURE,
        same_site="strict"
    )


def clear_persistent_login():

    try:

        if cookie_controller.get(
            AUTH_COOKIE_NAME
        ) is not None:

            cookie_controller.remove(
                AUTH_COOKIE_NAME,
                path="/",
                secure=AUTH_COOKIE_SECURE,
                same_site="strict"
            )

    except Exception:
        pass


def restore_persistent_login():

    if st.session_state.authenticated:
        return True

    try:
        token = cookie_controller.get(
            AUTH_COOKIE_NAME
        )
    except Exception:
        token = None

    if not token:
        return False

    user = validate_auth_token(
        token
    )

    if not user:
        clear_persistent_login()
        return False

    set_authenticated_user(
        user
    )

    return True


# =========================================================
# LOGIN PAGE
# =========================================================

def login_page():

    st.markdown(
        "<br><br>",
        unsafe_allow_html=True
    )

    left, center, right = (
        st.columns(
            [1.4, 1, 1.4]
        )
    )

    with center:

        st.title(
            "🧰 Wiginton Tools"
        )

        st.write(
            "Please sign in to continue."
        )

        with st.form(
            "login_form"
        ):

            email = st.text_input(
                "Email",
                placeholder=
                    "name@wiginton.net"
            )

            password = st.text_input(
                "Password",
                type="password"
            )

            submit = (
                st.form_submit_button(
                    "Sign In",
                    use_container_width=True
                )
            )

        if submit:

            if (
                not email
                or not password
            ):

                st.warning(
                    "Please enter your email "
                    "and password."
                )

                return

            user = authenticate_user(
                email
                .strip()
                .lower(),
                password
            )

            if not user:

                st.error(
                    "Invalid email or password."
                )

                login_error_detail = (
                    st.session_state.get(
                        "login_error_detail"
                    )
                )

                if login_error_detail:

                    st.caption(
                        "Login details: "
                        f"{login_error_detail}"
                    )

                return

            set_authenticated_user(
                user
            )

            save_persistent_login(
                user
            )

            st.rerun()

        st.markdown("")

        col_create, col_forgot = (
            st.columns(2)
        )

        with col_create:

            if st.button(
                "Create Account",
                use_container_width=True
            ):

                st.session_state.login_view = (
                    "create"
                )

                st.rerun()

        with col_forgot:

            if st.button(
                "Forgot Password?",
                use_container_width=True
            ):

                st.session_state.login_view = (
                    "forgot"
                )

                st.rerun()


# =========================================================
# CREATE ACCOUNT PAGE
# =========================================================

def create_account_page():

    branch_options = (
        get_user_branch_options()
    )

    st.markdown(
        "<br><br>",
        unsafe_allow_html=True
    )

    left, center, right = (
        st.columns(
            [1.4, 1, 1.4]
        )
    )

    with center:

        st.title(
            "🧰 Create Account"
        )

        st.write(
            "Create your Wiginton Tools account."
        )

        with st.form(
            "create_account_form"
        ):

            name = st.text_input(
                "Name"
            )

            email = st.text_input(
                "Email",
                placeholder=
                    "name@wiginton.net"
            )

            employee_number = (
                st.text_input(
                    "Employee Number"
                )
            )

            branch = st.selectbox(
                "Branch",
                options=[
                    "Select a branch..."
                ]
                + branch_options,
                index=0
            )

            password = st.text_input(
                "Password",
                type="password"
            )

            confirm_password = (
                st.text_input(
                    "Confirm Password",
                    type="password"
                )
            )

            create = (
                st.form_submit_button(
                    "Create Account",
                    use_container_width=True
                )
            )

        if create:

            name = (
                name.strip()
            )

            email = (
                email
                .strip()
                .lower()
            )

            if (
                not name
                or not email
                or not employee_number.strip()
                or not branch.strip()
                or branch
                == "Select a branch..."
                or not password
                or not confirm_password
            ):

                st.warning(
                    "Please complete all fields."
                )

            elif not email.endswith(
                "@wiginton.net"
            ):

                st.error(
                    "Please use a Wiginton "
                    "email address."
                )

            elif (
                password
                != confirm_password
            ):

                st.error(
                    "Passwords do not match."
                )

            elif len(password) < 8:

                st.error(
                    "Password must contain "
                    "at least 8 characters."
                )

            else:

                success, message = (
                    create_user_in_notion(
                        name,
                        email,
                        employee_number,
                        password,
                        branch
                    )
                )

                if success:

                    st.success(
                        message
                        or "Account created successfully!"
                    )

                    st.info(
                        "You can now return "
                        "to Sign In."
                    )

                else:

                    st.error(
                        message
                    )

        if st.button(
            "← Back to Sign In",
            use_container_width=True
        ):

            st.session_state.login_view = (
                "login"
            )

            st.rerun()


# =========================================================
# FORGOT PASSWORD PAGE
# =========================================================

def forgot_password_page():

    st.markdown(
        "<br><br>",
        unsafe_allow_html=True
    )

    left, center, right = (
        st.columns(
            [1.4, 1, 1.4]
        )
    )

    with center:

        st.title(
            "🔑 Reset Password"
        )

        st.write(
            "Enter your Wiginton email address "
            "to reset your password."
        )

        with st.form(
            "forgot_password_form"
        ):

            email = (
                st.text_input(
                    "Email",
                    placeholder=
                        "name@wiginton.net"
                )
            )

            reset = (
                st.form_submit_button(
                    "Send Reset Link",
                    use_container_width=True
                )
            )

        if reset:

            email = (
                email
                .strip()
                .lower()
            )

            if not email:

                st.warning(
                    "Please enter your email address."
                )

                return

            if not email.endswith(
                "@wiginton.net"
            ):

                st.warning(
                    "Please use your Wiginton email address."
                )

                return

            try:

                # Supabase Auth now sends the recovery email.
                # redirect_to points back to this Streamlit app.
                auth_key = (
                    SUPABASE_PUBLIC_KEY
                    or SUPABASE_SECRET_KEY
                )

                response = requests.post(
                    (
                        f"{SUPABASE_URL}/auth/v1/recover"
                    ),
                    headers={
                        "apikey":
                            auth_key,

                        "Content-Type":
                            "application/json",
                    },
                    json={
                        "email":
                            email,

                        "redirect_to":
                            APP_URL,
                    },
                    timeout=20,
                )

                if response.status_code not in (
                    200,
                    201,
                    202,
                    204,
                ):

                    try:

                        error_data = (
                            response.json()
                        )

                        error_message = (
                            error_data.get(
                                "msg"
                            )
                            or error_data.get(
                                "message"
                            )
                            or error_data.get(
                                "error_description"
                            )
                            or error_data.get(
                                "error"
                            )
                            or "Unable to send the recovery email."
                        )

                    except Exception:

                        error_message = (
                            "Unable to send the recovery email."
                        )

                    st.error(
                        "Unable to send the password reset email."
                    )

                    st.caption(
                        f"Supabase details: {error_message}"
                    )

                    return

                st.success(
                    "Password recovery request sent."
                )

                st.caption(
                    "Check your Wiginton email inbox "
                    "and follow the link sent by Supabase."
                )

                st.caption(
                    "If you do not see the message, "
                    "check your Junk or Spam folder."
                )

            except requests.RequestException as error:

                st.error(
                    "Unable to connect to Supabase Auth."
                )

                st.caption(
                    f"Connection details: {error}"
                )

        if st.button(
            "← Back to Sign In",
            use_container_width=True
        ):

            st.session_state.login_view = (
                "login"
            )

            st.rerun()



# =========================================================
# RESET PASSWORD PAGE
# =========================================================

def reset_password_page(
    token=None
):

    st.markdown(
        "<br><br>",
        unsafe_allow_html=True
    )

    left, center, right = (
        st.columns(
            [1.4, 1, 1.4]
        )
    )

    with center:

        st.title(
            "🔑 Create New Password"
        )

        query_params = (
            st.query_params
        )

        token_hash = (
            query_params.get(
                "token_hash"
            )
            or token
        )

        recovery_type = (
            query_params.get(
                "type"
            )
            or "recovery"
        )

        if (
            not token_hash
            or recovery_type
            != "recovery"
        ):

            st.warning(
                "Open this page using the password "
                "recovery link sent to your email."
            )

            if st.button(
                "← Back to Sign In",
                use_container_width=True
            ):

                st.query_params.clear()

                st.session_state.login_view = (
                    "login"
                )

                st.rerun()

            return

        st.write(
            "Enter your new password below."
        )

        with st.form(
            "new_password_form"
        ):

            password = (
                st.text_input(
                    "New Password",
                    type="password"
                )
            )

            confirm = (
                st.text_input(
                    "Confirm Password",
                    type="password"
                )
            )

            submit = (
                st.form_submit_button(
                    "Change Password",
                    use_container_width=True
                )
            )

        if submit:

            if len(
                password
            ) < 8:

                st.error(
                    "Password must contain "
                    "at least 8 characters."
                )

                return

            if (
                password
                != confirm
            ):

                st.error(
                    "Passwords do not match."
                )

                return

            if not SUPABASE_PUBLIC_KEY:

                st.error(
                    "SUPABASE_PUBLISHABLE_KEY "
                    "is not configured."
                )

                return

            try:

                # -------------------------------------------------
                # STEP 1
                # Verify the recovery token_hash.
                # Supabase returns a temporary authenticated session.
                # -------------------------------------------------

                verify_response = (
                    requests.post(
                        (
                            f"{SUPABASE_URL}"
                            "/auth/v1/verify"
                        ),
                        headers={
                            "apikey":
                                SUPABASE_PUBLIC_KEY,

                            "Content-Type":
                                "application/json",
                        },
                        json={
                            "token_hash":
                                token_hash,

                            "type":
                                "recovery",
                        },
                        timeout=20,
                    )
                )

                if (
                    verify_response.status_code
                    not in (
                        200,
                        201,
                    )
                ):

                    try:

                        verify_error = (
                            verify_response.json()
                        )

                        verify_message = (
                            verify_error.get(
                                "msg"
                            )
                            or verify_error.get(
                                "message"
                            )
                            or verify_error.get(
                                "error_description"
                            )
                            or verify_error.get(
                                "error"
                            )
                            or (
                                "The recovery link is "
                                "invalid or expired."
                            )
                        )

                    except Exception:

                        verify_message = (
                            "The recovery link is "
                            "invalid or expired."
                        )

                    st.error(
                        verify_message
                    )

                    return

                verify_data = (
                    verify_response.json()
                )

                access_token = (
                    verify_data.get(
                        "access_token"
                    )
                )

                if not access_token:

                    session_data = (
                        verify_data.get(
                            "session"
                        )
                        or {}
                    )

                    access_token = (
                        session_data.get(
                            "access_token"
                        )
                    )

                if not access_token:

                    st.error(
                        "Supabase verified the recovery "
                        "link but did not return a session."
                    )

                    return

                # -------------------------------------------------
                # STEP 2
                # Update password using the recovery session.
                # -------------------------------------------------

                update_response = (
                    requests.put(
                        (
                            f"{SUPABASE_URL}"
                            "/auth/v1/user"
                        ),
                        headers={
                            "apikey":
                                SUPABASE_PUBLIC_KEY,

                            "Authorization":
                                (
                                    "Bearer "
                                    f"{access_token}"
                                ),

                            "Content-Type":
                                "application/json",
                        },
                        json={
                            "password":
                                password,
                        },
                        timeout=20,
                    )
                )

                if (
                    update_response.status_code
                    not in (
                        200,
                        201,
                    )
                ):

                    try:

                        update_error = (
                            update_response.json()
                        )

                        update_message = (
                            update_error.get(
                                "msg"
                            )
                            or update_error.get(
                                "message"
                            )
                            or update_error.get(
                                "error_description"
                            )
                            or update_error.get(
                                "error"
                            )
                            or (
                                "Unable to update "
                                "the password."
                            )
                        )

                    except Exception:

                        update_message = (
                            "Unable to update "
                            "the password."
                        )

                    st.error(
                        update_message
                    )

                    return

                # Clear recovery parameters after success.
                st.query_params.clear()

                st.session_state.login_view = (
                    "login"
                )

                st.success(
                    "Password changed successfully."
                )

                st.info(
                    "Return to Sign In and use "
                    "your new password."
                )

                if st.button(
                    "Return to Sign In",
                    use_container_width=True,
                    type="primary"
                ):

                    st.rerun()

            except requests.RequestException as error:

                st.error(
                    "Unable to connect to Supabase Auth."
                )

                st.caption(
                    "Connection details: "
                    f"{error}"
                )



# =========================================================
# LOGOUT
# =========================================================

def logout():

    clear_persistent_login()

    st.session_state.authenticated = (
        False
    )

    st.session_state.user_id = None
    st.session_state.user_name = None
    st.session_state.user_email = None
    st.session_state.user_role = None
    st.session_state.user_branch = None

    st.session_state.login_view = (
        "login"
    )

    st.rerun()


# =========================================================
# RESET TOKEN URL CHECK
# =========================================================

reset_token = (
    st.query_params.get(
        "reset_token"
    )
)

recovery_token_hash = (
    st.query_params.get(
        "token_hash"
    )
)

recovery_type = (
    st.query_params.get(
        "type"
    )
)

if (
    reset_token
    or (
        recovery_token_hash
        and recovery_type
        == "recovery"
    )
):

    reset_password_page(
        reset_token
    )

    st.stop()


# =========================================================
# RESTORE PERSISTENT LOGIN
# =========================================================

if not st.session_state.authenticated:
    restore_persistent_login()


# =========================================================
# LOGIN CHECK
# =========================================================

if not st.session_state.authenticated:

    if (
        st.session_state.login_view
        == "create"
    ):

        create_account_page()

    elif (
        st.session_state.login_view
        == "forgot"
    ):

        forgot_password_page()

    else:

        login_page()

    st.stop()


# =========================================================
# HOME PAGE
# =========================================================

def home_page():

    st.title(
        "🧰 Wiginton Tools"
    )

    if st.session_state.user_name:

        st.caption(
            f"Signed in as "
            f"{st.session_state.user_name}"
        )

    st.divider()

    render_forecast_dashboard()

    st.divider()

    render_active_project_progress()

    st.divider()

    with st.expander(
        "ℹ️ Technical Information"
    ):

        st.write(
            "The images provided in this app are intended "
            "solely as visual aids to support learning and "
            "memorization. These illustrations may contain "
            "minor technical inaccuracies or inconsistencies. "
            "Always refer to the applicable codes, standards, "
            "manufacturer data sheets, and official technical "
            "documentation as the primary and authoritative "
            "sources for design, installation, and compliance "
            "decisions."
        )


# =========================================================
# ENGINEERING TOOL PAGES
# =========================================================

home = st.Page(
    home_page,
    title="Home",
    icon="🏠",
    default=True
)

pipes_sizes = st.Page(
    "pages/1_Pipes_Sizes.py",
    title="Pipes Sizes",
    icon="📏"
)

hanger = st.Page(
    "pages/2_Hanger.py",
    title="Hanger",
    icon="🔩"
)

trapeze = st.Page(
    "pages/3_Trapeze.py",
    title="Trapeze",
    icon="📐"
)

connections = st.Page(
    "pages/4_Connections.py",
    title="Connections",
    icon="🔗"
)

valves = st.Page(
    "pages/5_Valves.py",
    title="Valves",
    icon="🚰"
)

pump = st.Page(
    "pages/6_Pump.py",
    title="Pump",
    icon="⚙️"
)

calculation = st.Page(
    "pages/7_Calculation.py",
    title="Calculation",
    icon="🧮"
)


# =========================================================
# PROJECT MANAGEMENT PAGES
# =========================================================

new_project = st.Page(
    "pages/9_New_Project.py",
    title="New Project",
    icon="➕"
)

update_project = st.Page(
    "pages/10_Update_Project.py",
    title="Update Project",
    icon="✏️"
)

forecast = st.Page(
    "pages/11_Forecast.py",
    title="Forecast",
    icon="📅"
)

time_log = st.Page(
    "pages/12_Time_Log.py",
    title="Time Log",
    icon="⏱️"
)

permit = st.Page(
    "pages/13_Permit.py",
    title="Permit",
    icon="📋"
)

aml = st.Page(
    "pages/14_AML.py",
    title="AML",
    icon="📦"
)

dashboard = st.Page(
    "pages/15_Dashboard.py",
    title="Dashboard",
    icon="📊"
)

workflow = st.Page(
    "pages/8_Workflow.py",
    title="Workflow",
    icon="🔄"
)


# =========================================================
# SIDEBAR BRANDING
# =========================================================

show_sidebar_branding()


# =========================================================
# USER INFORMATION
# =========================================================

with st.sidebar:

    st.divider()

    if st.session_state.user_name:

        st.caption(
            "Signed in as"
        )

        st.write(
            f"👤 "
            f"{st.session_state.user_name}"
        )

    if st.session_state.user_email:

        st.caption(
            st.session_state.user_email
        )

    if st.session_state.user_role:

        st.caption(
            f"Role: "
            f"{st.session_state.user_role}"
        )

    if st.session_state.user_branch:

        st.caption(
            f"Branch: "
            f"{st.session_state.user_branch}"
        )

    if st.button(
        "🚪 Sign Out",
        use_container_width=True
    ):

        logout()


# =========================================================
# NAVIGATION
# =========================================================

project_management_pages = [
    new_project,
    update_project,
    forecast,
    time_log,
    permit,
    aml,
]

# Dashboard is available only to Managers.
if (
    normalize_text(
        st.session_state.user_role
    )
    == "manager"
):
    project_management_pages.append(
        dashboard
    )

project_management_pages.append(
    workflow
)

pg = st.navigation(
    {
        "Engineering Tools": [
            home,
            pipes_sizes,
            hanger,
            trapeze,
            connections,
            valves,
            pump,
            calculation,
        ],

        "Project Management":
            project_management_pages,
    }
)


# =========================================================
# RUN SELECTED PAGE
# =========================================================

pg.run()