import streamlit as st
import requests
import bcrypt
import secrets
import hashlib
import resend

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
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

NOTION_USERS_DATA_SOURCE_ID = (
    st.secrets["NOTION_USERS_DATA_SOURCE_ID"]
)

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

resend.api_key = RESEND_API_KEY


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

if "login_view" not in st.session_state:
    st.session_state.login_view = "login"


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

    return query_data_source(
        NOTION_USERS_DATA_SOURCE_ID
    )


def get_users_in_branch(
    branch_name
):

    if not branch_name:
        return []

    pages = get_all_users()

    target_branch = normalize_text(
        branch_name
    )

    users = []

    for page in pages:

        properties = page.get(
            "properties",
            {}
        )

        user_branch = normalize_text(
            get_select(
                properties,
                "Branch",
                ""
            )
        )

        if user_branch != target_branch:
            continue

        user_name = (
            get_title(
                properties,
                "Name"
            )
            or ""
        ).strip()

        user_email = (
            get_email(
                properties,
                "Email"
            )
            or ""
        ).strip()

        identifiers = set()

        # Name
        if user_name:

            identifiers.add(
                normalize_identity(
                    user_name
                )
            )

            # Also accept individual name parts.
            for part in user_name.split():

                normalized_part = (
                    normalize_identity(
                        part
                    )
                )

                if len(normalized_part) >= 3:

                    identifiers.add(
                        normalized_part
                    )

        # Email and email prefix
        if user_email:

            identifiers.add(
                normalize_identity(
                    user_email
                )
            )

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

        # Include all simple text/select values in Users.
        # This supports cases where Projects.Designer uses
        # initials, display names, short names, etc.
        for prop in properties.values():

            prop_type = prop.get(
                "type"
            )

            if prop_type not in {
                "title",
                "rich_text",
                "select",
                "status",
                "email",
                "number",
            }:
                continue

            value = (
                get_property_plain_text(
                    prop
                )
            )

            normalized_value = (
                normalize_identity(
                    value
                )
            )

            if normalized_value:

                identifiers.add(
                    normalized_value
                )

        users.append(
            {
                "id":
                    page.get(
                        "id"
                    )
                    or "",

                "name":
                    user_name,

                "email":
                    user_email,

                "identifiers":
                    identifiers,
            }
        )

    return users


def get_logged_manager_branch():

    user_email = (
        st.session_state.user_email
        or ""
    ).strip().lower()

    if not user_email:
        return ""

    user_page = get_user_by_email(
        user_email
    )

    if not user_page:
        return ""

    properties = user_page.get(
        "properties",
        {}
    )

    return (
        get_select(
            properties,
            "Branch",
            ""
        )
        or ""
    ).strip()


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

    url = (
        "https://api.notion.com/v1/data_sources/"
        f"{NOTION_USERS_DATA_SOURCE_ID}"
    )

    try:

        response = requests.get(
            url,
            headers=NOTION_HEADERS,
            timeout=15
        )

    except requests.RequestException:

        return []

    if response.status_code != 200:

        return []

    properties = (
        response.json()
        .get(
            "properties",
            {}
        )
    )

    branch_property = properties.get(
        "Branch",
        {}
    )

    if (
        branch_property.get(
            "type"
        )
        != "select"
    ):

        return []

    options = (
        branch_property
        .get(
            "select",
            {}
        )
        .get(
            "options",
            []
        )
    )

    return [
        option.get(
            "name",
            ""
        )
        for option in options
        if option.get(
            "name"
        )
    ]


# =========================================================
# GET USER BY EMAIL
# =========================================================

def get_user_by_email(email):

    url = (
        "https://api.notion.com/v1/data_sources/"
        f"{NOTION_USERS_DATA_SOURCE_ID}/query"
    )

    payload = {
        "filter": {
            "property": "Email",
            "email": {
                "equals": email
            }
        }
    }

    try:

        response = requests.post(
            url,
            headers=NOTION_HEADERS,
            json=payload,
            timeout=15
        )

    except requests.RequestException:

        return None

    if response.status_code != 200:

        return None

    results = response.json().get(
        "results",
        []
    )

    if not results:

        return None

    return results[0]


# =========================================================
# UPDATE USER IN NOTION
# =========================================================

def update_user_properties(
    page_id,
    properties
):

    url = (
        "https://api.notion.com/v1/pages/"
        f"{page_id}"
    )

    try:

        response = requests.patch(
            url,
            headers=NOTION_HEADERS,
            json={
                "properties": properties
            },
            timeout=15
        )

    except requests.RequestException:

        return False

    return response.status_code == 200


# =========================================================
# CREATE USER IN NOTION
# =========================================================

def create_user_in_notion(
    name,
    email,
    password,
    branch
):

    existing_user = get_user_by_email(
        email
    )

    if existing_user:

        return (
            False,
            "An account already exists for this email."
        )

    password_hash = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")

    url = (
        "https://api.notion.com/v1/pages"
    )

    payload = {

        "parent": {
            "type": "data_source_id",
            "data_source_id":
                NOTION_USERS_DATA_SOURCE_ID
        },

        "properties": {

            "Name": {
                "title": [
                    {
                        "text": {
                            "content": name
                        }
                    }
                ]
            },

            "Email": {
                "email": email
            },

            "Password Hash": {
                "rich_text": [
                    {
                        "text": {
                            "content":
                                password_hash
                        }
                    }
                ]
            },

            "Active": {
                "checkbox": True
            },

            "Role": {
                "select": {
                    "name": "Designer"
                }
            },

            "Branch": {
                "select": {
                    "name": branch
                }
            }
        }
    }

    try:

        response = requests.post(
            url,
            headers=NOTION_HEADERS,
            json=payload,
            timeout=15
        )

    except requests.RequestException:

        return (
            False,
            "Unable to connect to the user database."
        )

    if response.status_code not in [
        200,
        201
    ]:

        return (
            False,
            "Unable to create account."
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

    user_page = get_user_by_email(
        email
    )

    if not user_page:

        return None

    properties = user_page.get(
        "properties",
        {}
    )

    name = get_title(
        properties,
        "Name"
    )

    notion_email = get_email(
        properties,
        "Email"
    )

    password_hash = get_text(
        properties,
        "Password Hash"
    )

    active = get_checkbox(
        properties,
        "Active",
        True
    )

    role = get_select(
        properties,
        "Role",
        "Designer"
    )

    branch = get_select(
        properties,
        "Branch",
        ""
    )

    if not active:

        return None

    if not password_hash:

        return None

    try:

        password_ok = bcrypt.checkpw(
            password.encode("utf-8"),
            password_hash.encode("utf-8")
        )

    except Exception:

        return None

    if not password_ok:

        return None

    return {
        "id": user_page.get("id"),
        "name": name,
        "email": notion_email,
        "role": role,
        "branch": branch,
    }


# =========================================================
# GENERATE RESET TOKEN
# =========================================================

def generate_reset_token():

    token = secrets.token_urlsafe(32)

    token_hash = hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()

    return token, token_hash


# =========================================================
# CREATE PASSWORD RESET
# =========================================================

def create_password_reset(email):

    user_page = get_user_by_email(
        email
    )

    if not user_page:

        return True, None

    token, token_hash = (
        generate_reset_token()
    )

    expires = (
        datetime.now(
            timezone.utc
        )
        + timedelta(
            minutes=30
        )
    )

    properties = {

        "Reset Token Hash": {
            "rich_text": [
                {
                    "text": {
                        "content":
                            token_hash
                    }
                }
            ]
        },

        "Reset Expires": {
            "date": {
                "start":
                    expires.isoformat()
            }
        }
    }

    success = update_user_properties(
        user_page["id"],
        properties
    )

    if not success:

        return False, None

    return True, token


# =========================================================
# FIND USER BY RESET TOKEN
# =========================================================

def find_user_by_reset_token(token):

    token_hash = hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()

    url = (
        "https://api.notion.com/v1/data_sources/"
        f"{NOTION_USERS_DATA_SOURCE_ID}/query"
    )

    payload = {

        "filter": {

            "property":
                "Reset Token Hash",

            "rich_text": {
                "equals":
                    token_hash
            }
        }
    }

    try:

        response = requests.post(
            url,
            headers=NOTION_HEADERS,
            json=payload,
            timeout=15
        )

    except requests.RequestException:

        return None

    if response.status_code != 200:

        return None

    results = response.json().get(
        "results",
        []
    )

    if not results:

        return None

    return results[0]


# =========================================================
# SEND RESET EMAIL
# =========================================================

def send_reset_email(
    email,
    reset_link
):

    try:

        resend.Emails.send(
            {
                "from": RESET_EMAIL_SENDER,

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

        return True

    except Exception as e:

        st.error(
            "RESEND ERROR:"
        )

        st.exception(
            e
        )

        return False


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

                return

            st.session_state.authenticated = (
                True
            )

            st.session_state.user_id = (
                user["id"]
            )

            st.session_state.user_name = (
                user["name"]
            )

            st.session_state.user_email = (
                user["email"]
            )

            st.session_state.user_role = (
                user["role"]
            )

            st.session_state.user_branch = (
                user.get(
                    "branch"
                )
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

        if not branch_options:

            st.warning(
                "No Branch options are available."
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
                        password,
                        branch
                    )
                )

                if success:

                    st.success(
                        "Account created successfully!"
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
            "Enter your email address "
            "to reset your password."
        )

        with st.form(
            "forgot_password_form"
        ):

            email = st.text_input(
                "Email",
                placeholder=
                    "name@email.com"
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

            success, token = (
                create_password_reset(
                    email
                )
            )

            if not success:

                st.error(
                    "Unable to process "
                    "the password reset."
                )

                return

            if token:

                reset_link = (
                    f"{APP_URL}"
                    f"/?reset_token={token}"
                )

                email_sent = (
                    send_reset_email(
                        email,
                        reset_link
                    )
                )

                if not email_sent:

                    st.error(
                        "Unable to send the "
                        "password reset email."
                    )

                    return

            st.success(
                "If an account exists for that "
                "email address, a password reset "
                "link has been sent."
            )

            st.caption(
                "The reset link is valid "
                "for 30 minutes."
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
    token
):

    user_page = (
        find_user_by_reset_token(
            token
        )
    )

    if not user_page:

        st.error(
            "This password reset link "
            "is invalid or has already "
            "been used."
        )

        return

    properties = user_page.get(
        "properties",
        {}
    )

    expires_prop = (
        properties.get(
            "Reset Expires",
            {}
        )
    )

    date_data = (
        expires_prop.get(
            "date"
        )
    )

    if not date_data:

        st.error(
            "This password reset "
            "link is invalid."
        )

        return

    try:

        expires = (
            datetime.fromisoformat(
                date_data["start"]
            )
        )

    except Exception:

        st.error(
            "This password reset "
            "link is invalid."
        )

        return

    if (
        datetime.now(
            timezone.utc
        )
        > expires
    ):

        st.error(
            "This password reset "
            "link has expired."
        )

        return

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

            if not password:

                st.warning(
                    "Please enter a new password."
                )

                return

            if len(password) < 8:

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

            password_hash = (
                bcrypt.hashpw(
                    password.encode(
                        "utf-8"
                    ),
                    bcrypt.gensalt()
                )
                .decode(
                    "utf-8"
                )
            )

            success = (
                update_user_properties(
                    user_page["id"],
                    {

                        "Password Hash": {
                            "rich_text": [
                                {
                                    "text": {
                                        "content":
                                            password_hash
                                    }
                                }
                            ]
                        },

                        "Reset Token Hash": {
                            "rich_text": []
                        },

                        "Reset Expires": {
                            "date": None
                        }
                    }
                )
            )

            if success:

                st.query_params.clear()

                st.session_state.login_view = (
                    "login"
                )

                st.success(
                    "Password changed successfully."
                )

                if st.button(
                    "Return to Sign In",
                    use_container_width=True
                ):

                    st.rerun()

            else:

                st.error(
                    "Unable to change password."
                )


# =========================================================
# LOGOUT
# =========================================================

def logout():

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

if reset_token:

    reset_password_page(
        reset_token
    )

    st.stop()


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

dashboard = st.Page(
    "pages/14_Dashboard.py",
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