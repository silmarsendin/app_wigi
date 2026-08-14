import streamlit as st
import requests

from datetime import date, datetime
from streamlit_calendar import calendar


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Forecast",
    page_icon="📅",
    layout="wide",
)


# =========================================================
# PAGE HEADER
# =========================================================

st.title("📅 Forecast")

st.caption(
    "Project forecast and milestone schedule"
)


# =========================================================
# LOGGED USER
# =========================================================

logged_user_name = (
    st.session_state.get("user_name")
    or ""
).strip()

logged_user_role = (
    st.session_state.get("user_role")
    or "Designer"
).strip()

logged_user_branch = (
    st.session_state.get("user_branch")
    or ""
).strip()

logged_user_email = (
    st.session_state.get("user_email")
    or ""
).strip()

is_manager = (
    logged_user_role.casefold()
    == "manager"
)

if not logged_user_name:

    st.error(
        "Unable to identify the logged-in user."
    )

    st.stop()


# =========================================================
# CONFIGURATION
# =========================================================

NOTION_TOKEN = st.secrets["NOTION_TOKEN"]

NOTION_USERS_DATA_SOURCE_ID = (
    st.secrets.get("NOTION_USERS_DATA_SOURCE_ID")
    or st.secrets.get("USERS_DATA_SOURCE_ID")
    or st.secrets.get("NOTION_USERS_DATABASE_ID")
)

FORECAST_DATA_SOURCE_ID = (
    st.secrets["NOTION_FORECAST_DATA_SOURCE_ID"]
)

NOTION_PERMIT_ID = (
    st.secrets.get("NOTION_PERMIT_DATA_SOURCE_ID")
    or st.secrets.get("NOTION_PERMIT_DATABASE_ID")
    or st.secrets.get("PERMIT_DATA_SOURCE_ID")
    or st.secrets.get("PERMIT_DATABASE_ID")
)


HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2025-09-03",
    "Content-Type": "application/json",
}


FORECAST_URL = (
    "https://api.notion.com/v1/data_sources/"
    f"{FORECAST_DATA_SOURCE_ID}/query"
)


# =========================================================
# TEXT NORMALIZATION
# =========================================================

def normalize_text(value):

    return (
        str(value or "")
        .strip()
        .casefold()
    )


# =========================================================
# PROPERTY HELPERS
# =========================================================

def get_title(prop):

    if not prop:
        return ""

    values = prop.get(
        "title",
        []
    )

    return "".join(
        item.get(
            "plain_text",
            ""
        )
        for item in values
    ).strip()


def get_rich_text(prop):

    if not prop:
        return ""

    values = prop.get(
        "rich_text",
        []
    )

    return "".join(
        item.get(
            "plain_text",
            ""
        )
        for item in values
    ).strip()


def get_select(prop):

    if not prop:
        return ""

    value = prop.get(
        "select"
    )

    if value:

        return value.get(
            "name",
            ""
        ).strip()

    return ""


def get_status(prop):

    if not prop:
        return ""

    value = prop.get(
        "status"
    )

    if value:

        return value.get(
            "name",
            ""
        ).strip()

    return ""


def get_date(prop):

    if not prop:
        return None

    value = prop.get(
        "date"
    )

    if not value:
        return None

    return value.get(
        "start"
    )


def get_checkbox(prop):

    if not prop:
        return False

    return bool(
        prop.get(
            "checkbox",
            False
        )
    )


def get_formula_value(prop):

    if not prop:
        return ""

    formula = prop.get(
        "formula"
    )

    if not formula:
        return ""

    formula_type = formula.get(
        "type"
    )


    if formula_type == "string":

        return (
            formula.get(
                "string"
            )
            or ""
        )


    if formula_type == "number":

        value = formula.get(
            "number"
        )

        return (
            ""
            if value is None
            else str(value)
        )


    if formula_type == "boolean":

        return (
            "Yes"
            if formula.get(
                "boolean"
            )
            else "No"
        )


    if formula_type == "date":

        value = formula.get(
            "date"
        )

        if value:

            return value.get(
                "start",
                ""
            )


    return ""


def get_rollup_text(prop):

    if not prop:
        return ""

    rollup = prop.get(
        "rollup"
    )

    if not rollup:
        return ""

    rollup_type = rollup.get(
        "type"
    )


    if rollup_type == "array":

        values = []

        for item in rollup.get(
            "array",
            []
        ):

            item_type = item.get(
                "type"
            )


            if item_type == "title":

                values.extend(
                    value.get(
                        "plain_text",
                        ""
                    )
                    for value in item.get(
                        "title",
                        []
                    )
                )


            elif item_type == "rich_text":

                values.extend(
                    value.get(
                        "plain_text",
                        ""
                    )
                    for value in item.get(
                        "rich_text",
                        []
                    )
                )


            elif item_type == "select":

                selected = item.get(
                    "select"
                )

                if selected:

                    values.append(
                        selected.get(
                            "name",
                            ""
                        )
                    )


            elif item_type == "status":

                selected_status = item.get(
                    "status"
                )

                if selected_status:

                    values.append(
                        selected_status.get(
                            "name",
                            ""
                        )
                    )


            elif item_type == "number":

                number = item.get(
                    "number"
                )

                if number is not None:

                    values.append(
                        str(number)
                    )


            elif item_type == "formula":

                formula = item.get(
                    "formula",
                    {}
                )

                if (
                    formula.get("type")
                    == "string"
                ):

                    values.append(
                        formula.get(
                            "string",
                            ""
                        )
                    )


        return ", ".join(
            value
            for value in values
            if value
        )


    if rollup_type == "number":

        value = rollup.get(
            "number"
        )

        return (
            ""
            if value is None
            else str(value)
        )


    return ""


def get_property_text(prop):

    if not prop:
        return ""

    prop_type = prop.get(
        "type"
    )


    if prop_type == "title":
        return get_title(prop)


    if prop_type == "rich_text":
        return get_rich_text(prop)


    if prop_type == "select":
        return get_select(prop)


    if prop_type == "status":
        return get_status(prop)


    if prop_type == "formula":
        return get_formula_value(prop)


    if prop_type == "rollup":
        return get_rollup_text(prop)


    if prop_type == "number":

        value = prop.get(
            "number"
        )

        if value is None:
            return ""

        if (
            isinstance(value, float)
            and value.is_integer()
        ):
            return str(
                int(value)
            )

        return str(value)


    if prop_type == "email":

        return (
            prop.get(
                "email"
            )
            or ""
        )


    return ""


# =========================================================
# DATE HELPERS
# =========================================================

def parse_event_date(value):

    if not value:
        return None


    try:

        return datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00"
            )
        ).date()

    except (
        ValueError,
        TypeError
    ):

        try:

            return date.fromisoformat(
                value[:10]
            )

        except (
            ValueError,
            TypeError
        ):

            return None


def format_date(value):

    parsed = (
        parse_event_date(
            value
        )
    )

    if not parsed:
        return ""

    return parsed.strftime(
        "%m/%d/%Y"
    )


def add_months(
    original_date,
    months
):

    month_index = (
        original_date.month
        - 1
        + months
    )

    year = (
        original_date.year
        + month_index // 12
    )

    month = (
        month_index % 12
        + 1
    )


    days_in_month = [

        31,

        29
        if (
            year % 4 == 0
            and (
                year % 100 != 0
                or year % 400 == 0
            )
        )
        else 28,

        31,
        30,
        31,
        30,
        31,
        31,
        30,
        31,
        30,
        31,
    ]


    day = min(
        original_date.day,
        days_in_month[
            month - 1
        ]
    )


    return date(
        year,
        month,
        day
    )


# =========================================================
# RELATED PROJECT
# =========================================================

@st.cache_data(
    ttl=300,
    show_spinner=False
)
def get_related_project(
    page_id
):

    if not page_id:
        return {}


    url = (
        "https://api.notion.com/v1/pages/"
        f"{page_id}"
    )


    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=20,
        )

    except requests.RequestException:

        return {}


    if response.status_code != 200:
        return {}


    return response.json().get(
        "properties",
        {}
    )


def get_project_number_from_relation(
    relation_items
):

    if not relation_items:
        return ""


    project_page_id = (
        relation_items[0].get(
            "id"
        )
    )


    if not project_page_id:
        return ""


    properties = (
        get_related_project(
            project_page_id
        )
    )


    for property_name in [
        "Number",
        "Project Number",
        "Project",
    ]:

        value = (
            get_property_text(
                properties.get(
                    property_name
                )
            )
        )

        if value:
            return value


    return ""


# =========================================================
# USERS / BRANCH DESIGNERS
# =========================================================

@st.cache_data(
    ttl=300,
    show_spinner=False
)
def load_users():

    if not NOTION_USERS_DATA_SOURCE_ID:
        return []

    url = (
        "https://api.notion.com/v1/data_sources/"
        f"{NOTION_USERS_DATA_SOURCE_ID}/query"
    )

    records = []
    payload = {
        "page_size": 100
    }

    while True:

        try:
            response = requests.post(
                url,
                headers=HEADERS,
                json=payload,
                timeout=30,
            )

        except requests.RequestException:
            return []

        if response.status_code != 200:
            return []

        data = response.json()

        records.extend(
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

        payload[
            "start_cursor"
        ] = next_cursor

    return records


def get_users_for_branch(
    branch_name
):

    if not branch_name:
        return []

    target_branch = normalize_text(
        branch_name
    )

    users = []

    for page in load_users():

        properties = page.get(
            "properties",
            {}
        )

        branch = get_property_text(
            properties.get(
                "Branch"
            )
        )

        if (
            normalize_text(branch)
            != target_branch
        ):
            continue

        active_prop = properties.get(
            "Active",
            {}
        )

        if (
            active_prop
            and active_prop.get("type")
            == "checkbox"
            and not get_checkbox(active_prop)
        ):
            continue

        name = get_property_text(
            properties.get(
                "Name"
            )
        ).strip()

        if not name:
            # Fallback to the first title property.
            for prop in properties.values():
                if prop.get("type") == "title":
                    name = get_property_text(
                        prop
                    ).strip()

                    if name:
                        break

        role = get_property_text(
            properties.get(
                "Role"
            )
        ).strip()

        email = get_property_text(
            properties.get(
                "Email"
            )
        ).strip()

        if name:
            users.append(
                {
                    "name": name,
                    "role": role,
                    "email": email,
                    "branch": branch,
                }
            )

    # Remove duplicates while preserving a predictable order.
    unique = {}

    for user in users:
        unique[
            normalize_text(
                user["name"]
            )
        ] = user

    return sorted(
        unique.values(),
        key=lambda user:
            user["name"].casefold()
    )


def get_manager_designer_names():

    branch_users = (
        get_users_for_branch(
            logged_user_branch
        )
    )

    # We include users whose Role is Designer.
    # If the Users table has no Role filled in, keep the user
    # available so a valid Forecast Designer is not hidden.
    designer_names = []

    for user in branch_users:

        role = normalize_text(
            user.get("role")
        )

        if (
            not role
            or role == "designer"
        ):
            designer_names.append(
                user["name"]
            )

    # Also include designers actually present in Forecast records
    # when they match someone in the same branch.
    branch_name_lookup = {
        normalize_text(
            user["name"]
        ): user["name"]
        for user in branch_users
    }

    for event in all_events:
        designer = (
            event.get(
                "extendedProps",
                {}
            ).get(
                "designer",
                ""
            )
            or ""
        ).strip()

        normalized_designer = (
            normalize_text(
                designer
            )
        )

        if (
            normalized_designer
            in branch_name_lookup
        ):
            designer_names.append(
                branch_name_lookup[
                    normalized_designer
                ]
            )

    return sorted(
        set(designer_names),
        key=str.casefold
    )


# =========================================================
# FORECAST DATA
# =========================================================

@st.cache_data(
    ttl=300,
    show_spinner=False
)
def load_forecast():

    records = []

    payload = {
        "page_size": 100
    }


    while True:

        try:

            response = requests.post(
                FORECAST_URL,
                headers=HEADERS,
                json=payload,
                timeout=30,
            )

        except requests.RequestException as error:

            raise Exception(
                "Unable to connect to the schedule database."
            ) from error


        if response.status_code != 200:

            raise Exception(
                "Unable to load schedule data."
            )


        data = response.json()


        records.extend(
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


        payload[
            "start_cursor"
        ] = next_cursor


    return records


# =========================================================
# EVENT COLORS
# =========================================================

EVENT_COLORS = {

    "AML":
        "#7C3AED",

    "Stocklist":
        "#2563EB",

    "Foreman's":
        "#D97706",

    "Permit Submittal":
        "#DB2777",

    "Boots on the Ground":
        "#DC2626",

    "Boot on the Ground":
        "#DC2626",

    "Design Review":
        "#0891B2",

    "Submittal":
        "#4F46E5",

    "Installation":
        "#EA580C",

    "Approved":
        "#16A34A",
}


DEFAULT_EVENT_COLOR = (
    "#64748B"
)

DONE_COLOR = (
    "#16A34A"
)


# =========================================================
# BUILD EVENTS
# =========================================================

def build_events(records):

    events = []


    for page in records:

        properties = page.get(
            "properties",
            {}
        )


        # -------------------------------------------------
        # BUILDING
        # -------------------------------------------------

        building = (
            get_property_text(
                properties.get(
                    "Building"
                )
            )
        )


        # -------------------------------------------------
        # DATE
        # -------------------------------------------------

        event_date = (
            get_date(
                properties.get(
                    "Date of event"
                )
            )
        )


        # -------------------------------------------------
        # DESIGNER
        # -------------------------------------------------

        designer = (
            get_property_text(
                properties.get(
                    "Designer"
                )
            )
        )


        # -------------------------------------------------
        # TYPE
        # -------------------------------------------------

        event_type = (
            get_property_text(
                properties.get(
                    "Type of Event"
                )
            )
        )


        # -------------------------------------------------
        # DONE
        # -------------------------------------------------

        done = (
            get_checkbox(
                properties.get(
                    "Done"
                )
            )
        )


        # -------------------------------------------------
        # PROJECT RELATION
        # -------------------------------------------------

        project_relation = (
            properties.get(
                "Projects",
                {}
            )
        )


        relation_items = (
            project_relation.get(
                "relation",
                []
            )
        )


        project_page_id = (
            relation_items[0].get(
                "id"
            )
            if relation_items
            else None
        )


        # -------------------------------------------------
        # PROJECT NUMBER
        # -------------------------------------------------

        project_number = (
            get_property_text(
                properties.get(
                    "Project Number"
                )
            )
        )


        if not project_number:

            project_number = (
                get_property_text(
                    properties.get(
                        "Project"
                    )
                )
            )


        if not project_number:

            project_number = (
                get_project_number_from_relation(
                    relation_items
                )
            )


        # -------------------------------------------------
        # DATE REQUIRED
        # -------------------------------------------------

        if not event_date:
            continue


        # -------------------------------------------------
        # TITLE
        # -------------------------------------------------

        title_parts = []


        if project_number:

            title_parts.append(
                project_number
            )


        if building:

            title_parts.append(
                building
            )


        if event_type:

            title_parts.append(
                event_type
            )


        title = " | ".join(
            title_parts
        )


        if not title:

            title = (
                "Forecast Event"
            )


        # -------------------------------------------------
        # COLOR
        # -------------------------------------------------

        if done:

            color = (
                DONE_COLOR
            )

        else:

            color = (
                EVENT_COLORS.get(
                    event_type,
                    DEFAULT_EVENT_COLOR
                )
            )


        # -------------------------------------------------
        # EVENT
        # -------------------------------------------------

        events.append(
            {
                "id":
                    page.get(
                        "id"
                    ),

                "title":
                    title,

                "start":
                    event_date,

                "allDay":
                    True,

                "backgroundColor":
                    color,

                "borderColor":
                    color,

                "extendedProps": {

                    "project_number":
                        project_number,

                    "project_page_id":
                        project_page_id,

                    "building":
                        building,

                    "designer":
                        designer,

                    "event_type":
                        event_type,

                    "done":
                        done,
                }
            }
        )


    return events


# =========================================================
# RESOLVE PERMIT DATA SOURCE
# =========================================================

@st.cache_data(
    ttl=600,
    show_spinner=False
)
def resolve_data_source_id(
    notion_id
):

    if not notion_id:
        return None


    # -----------------------------------------------------
    # TRY AS DATA SOURCE
    # -----------------------------------------------------

    url = (
        "https://api.notion.com/v1/data_sources/"
        f"{notion_id}"
    )


    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=20,
        )


        if response.status_code == 200:
            return notion_id


    except requests.RequestException:
        pass


    # -----------------------------------------------------
    # TRY AS DATABASE
    # -----------------------------------------------------

    url = (
        "https://api.notion.com/v1/databases/"
        f"{notion_id}"
    )


    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=20,
        )

    except requests.RequestException:

        return None


    if response.status_code != 200:
        return None


    data_sources = (
        response.json().get(
            "data_sources",
            []
        )
    )


    if not data_sources:
        return None


    return data_sources[0].get(
        "id"
    )


# =========================================================
# PERMIT DATA
# =========================================================

@st.cache_data(
    ttl=300,
    show_spinner=False
)
def load_permits(
    permit_data_source_id
):

    if not permit_data_source_id:
        return []


    url = (
        "https://api.notion.com/v1/data_sources/"
        f"{permit_data_source_id}/query"
    )


    records = []

    payload = {
        "page_size": 100
    }


    while True:

        try:

            response = requests.post(
                url,
                headers=HEADERS,
                json=payload,
                timeout=30,
            )

        except requests.RequestException:

            return []


        if response.status_code != 200:
            return []


        data = response.json()


        records.extend(
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


        payload[
            "start_cursor"
        ] = next_cursor


    return records


# =========================================================
# PERMIT RELATION
# =========================================================

def get_permit_project_relation(
    properties
):

    for property_name in [
        "Projects",
        "Project",
    ]:

        prop = properties.get(
            property_name,
            {}
        )


        if (
            prop.get(
                "type"
            )
            == "relation"
        ):

            return prop.get(
                "relation",
                []
            )


    # -----------------------------------------------------
    # BACKUP:
    # FIRST RELATION PROPERTY
    # -----------------------------------------------------

    for prop in properties.values():

        if (
            prop.get(
                "type"
            )
            == "relation"
        ):

            return prop.get(
                "relation",
                []
            )


    return []


# =========================================================
# PERMIT STATUS
# =========================================================

def get_permit_status(
    submitted_date,
    approved_date
):

    if approved_date:

        return (
            "Approved"
        )


    if submitted_date:

        return (
            "Submitted - Awaiting Approval"
        )


    return (
        "Not Submitted"
    )


# =========================================================
# LOAD FORECAST DATA
# =========================================================

try:

    forecast_records = (
        load_forecast()
    )

except Exception:

    st.error(
        "Unable to load Forecast data."
    )

    st.caption(
        "Please try again later."
    )

    st.stop()


all_events = (
    build_events(
        forecast_records
    )
)


# =========================================================
# DESIGNER / MANAGER VISIBILITY FILTER
# =========================================================
#
# Designer:
#   - sees only their own Forecast records.
#
# Manager:
#   - sees Forecast records assigned to Designers in the
#     Manager's Branch.
#   - can later select one Designer or All.
# =========================================================

if is_manager:

    manager_designer_names = (
        get_manager_designer_names()
    )

    allowed_designer_names = {
        normalize_text(name)
        for name in manager_designer_names
    }

    events = [
        event
        for event in all_events
        if normalize_text(
            event.get(
                "extendedProps",
                {}
            ).get(
                "designer",
                ""
            )
        )
        in allowed_designer_names
    ]

else:

    manager_designer_names = []

    events = [
        event
        for event in all_events
        if normalize_text(
            event.get(
                "extendedProps",
                {}
            ).get(
                "designer",
                ""
            )
        )
        == normalize_text(
            logged_user_name
        )
    ]


visible_forecast_page_ids = {
    event.get("id")
    for event in events
    if event.get("id")
}

forecast_records = [
    page
    for page in forecast_records
    if page.get("id")
    in visible_forecast_page_ids
]


if is_manager and not logged_user_branch:

    st.warning(
        "Your Manager account does not have a Branch assigned. "
        "Designer filtering by Branch is unavailable."
    )

elif (
    is_manager
    and not NOTION_USERS_DATA_SOURCE_ID
):

    st.warning(
        "Users data source is not configured. "
        "Add NOTION_USERS_DATA_SOURCE_ID to Streamlit Secrets."
    )


# =========================================================
# FILTER VALUES
# =========================================================

designers = sorted(
    {
        event[
            "extendedProps"
        ][
            "designer"
        ]

        for event in events

        if event[
            "extendedProps"
        ][
            "designer"
        ]
    }
)


event_types = sorted(
    {
        event[
            "extendedProps"
        ][
            "event_type"
        ]

        for event in events

        if event[
            "extendedProps"
        ][
            "event_type"
        ]
    }
)


projects = sorted(
    {
        event[
            "extendedProps"
        ][
            "project_number"
        ]

        for event in events

        if event[
            "extendedProps"
        ][
            "project_number"
        ]
    }
)


# =========================================================
# FILTER BAR
# =========================================================

if is_manager:

    st.caption(
        "Manager view: select one Designer or All Designers "
        f"in Branch {logged_user_branch or '—'}."
    )

else:

    st.caption(
        f"Showing only Projects assigned to "
        f"{logged_user_name} as Designer."
    )

col1, col2, col3, col4 = (
    st.columns(
        [
            1.2,
            1.2,
            1.5,
            1,
        ]
    )
)


with col1:

    if is_manager:

        selected_designer = (
            st.selectbox(
                "Designer",
                [
                    "All"
                ]
                + manager_designer_names,
                index=0,
            )
        )

    else:

        selected_designer = (
            st.selectbox(
                "Designer",
                [logged_user_name],
                disabled=True,
            )
        )


with col2:

    selected_project = (
        st.selectbox(
            "Project",
            [
                "All"
            ]
            + projects
        )
    )


with col3:

    selected_event_types = (
        st.multiselect(
            "Type of Event",
            event_types,
            default=
                event_types,
        )
    )


with col4:

    selected_done = (
        st.selectbox(
            "Done",
            [
                "All",
                "No",
                "Yes",
            ]
        )
    )


# =========================================================
# APPLY FILTERS
# =========================================================

filtered_events = []


for event in events:

    props = event[
        "extendedProps"
    ]


    if (
        selected_designer
        != "All"
        and normalize_text(
            props[
                "designer"
            ]
        )
        != normalize_text(
            selected_designer
        )
    ):

        continue


    if (
        selected_project
        != "All"
        and props[
            "project_number"
        ]
        != selected_project
    ):

        continue


    if (
        props[
            "event_type"
        ]
        not in selected_event_types
    ):

        continue


    if (
        selected_done
        == "Yes"
        and not props[
            "done"
        ]
    ):

        continue


    if (
        selected_done
        == "No"
        and props[
            "done"
        ]
    ):

        continue


    filtered_events.append(
        event
    )


# =========================================================
# METRICS
# =========================================================

metric1, metric2, metric3 = (
    st.columns(3)
)


filtered_event_ids = {
    event.get("id")
    for event in filtered_events
    if event.get("id")
}

filtered_forecast_records = [
    page
    for page in forecast_records
    if page.get("id")
    in filtered_event_ids
]

metric1.metric(
    "Forecast Records",
    len(
        filtered_forecast_records
    )
)


metric2.metric(
    "Events Displayed",
    len(
        filtered_events
    )
)


completed_count = sum(
    1
    for event in filtered_events
    if event[
        "extendedProps"
    ][
        "done"
    ]
)


metric3.metric(
    "Completed",
    completed_count
)


st.divider()


# =========================================================
# LEGEND
# =========================================================

st.markdown(
    """
    🟢 **Done**
    &nbsp;&nbsp;&nbsp;
    🟣 **AML**
    &nbsp;&nbsp;&nbsp;
    🔵 **Stocklist**
    &nbsp;&nbsp;&nbsp;
    🟠 **Foreman's**
    &nbsp;&nbsp;&nbsp;
    🔴 **Boots on the Ground**
    """
)


# =========================================================
# CALENDAR OPTIONS
# =========================================================

calendar_options = {

    "initialView":
        "dayGridMonth",

    "headerToolbar": {

        "left":
            "prev,next today",

        "center":
            "title",

        "right":
            "dayGridMonth,timeGridWeek,listMonth",
    },

    "height":
        780,

    "firstDay":
        1,

    "navLinks":
        True,

    "editable":
        False,

    "selectable":
        False,

    "dayMaxEvents":
        5,

    "eventDisplay":
        "block",

    "displayEventTime":
        False,
}


# =========================================================
# CALENDAR CSS
# =========================================================

calendar_css = """

.fc-event {
    font-size: 11px;
    font-weight: 500;
    cursor: pointer;
}

.fc-daygrid-event {
    border-radius: 4px;
    padding: 2px 4px;
}

.fc-toolbar-title {
    font-size: 22px !important;
    font-weight: 600;
}

.fc-list-event-title {
    font-weight: 500;
}

.fc-list-event-time {
    width: 80px;
}

"""


# =========================================================
# DISPLAY CALENDAR
# =========================================================

calendar_result = calendar(

    events=
        filtered_events,

    options=
        calendar_options,

    custom_css=
        calendar_css,

    key=
        "forecast_calendar",
)


# =========================================================
# EVENT DETAILS
# =========================================================

if calendar_result:

    event_click = (
        calendar_result.get(
            "eventClick"
        )
    )


    if event_click:

        clicked_event = (
            event_click.get(
                "event",
                {}
            )
        )


        properties = (
            clicked_event.get(
                "extendedProps",
                {}
            )
        )


        st.divider()


        st.subheader(
            "Event Details"
        )


        detail_col1, detail_col2 = (
            st.columns(2)
        )


        with detail_col1:

            st.write(
                "**Project:**",
                properties.get(
                    "project_number",
                    ""
                )
                or "—"
            )


            st.write(
                "**Building / System:**",
                properties.get(
                    "building",
                    ""
                )
                or "—"
            )


            st.write(
                "**Designer:**",
                properties.get(
                    "designer",
                    ""
                )
                or "—"
            )


        with detail_col2:

            st.write(
                "**Type of Event:**",
                properties.get(
                    "event_type",
                    ""
                )
                or "—"
            )


            done = (
                properties.get(
                    "done",
                    False
                )
            )


            st.write(
                "**Done:**",
                (
                    "Yes"
                    if done
                    else "No"
                )
            )


# =========================================================
# UPCOMING INSTALLATION STARTS
# =========================================================

st.divider()


st.subheader(
    "🚧 Upcoming Installation Starts"
)


st.info(
    "These are the upcoming installation starts over "
    "the next three months. Please verify that they have "
    "already been submitted for approval."
)


today = (
    date.today()
)

three_months_from_today = (
    add_months(
        today,
        3
    )
)


boots_events = []


for event in filtered_events:

    properties = event[
        "extendedProps"
    ]


    event_type = (
        properties.get(
            "event_type",
            ""
        )
    )


    # -----------------------------------------------------
    # ONLY BOOTS ON THE GROUND
    # -----------------------------------------------------

    if normalize_text(
        event_type
    ) not in {
        "boot on the ground",
        "boots on the ground",
    }:

        continue


    event_date = (
        parse_event_date(
            event.get(
                "start"
            )
        )
    )


    if not event_date:
        continue


    # -----------------------------------------------------
    # TODAY THROUGH NEXT 3 MONTHS
    # -----------------------------------------------------

    if event_date < today:
        continue


    if (
        event_date
        > three_months_from_today
    ):
        continue


    boots_events.append(
        {
            "date":
                event_date,

            "project":
                properties.get(
                    "project_number",
                    ""
                )
                or "—",

            "project_page_id":
                properties.get(
                    "project_page_id"
                ),

            "building":
                properties.get(
                    "building",
                    ""
                )
                or "—",

            "designer":
                properties.get(
                    "designer",
                    ""
                )
                or "—",

            "done":
                properties.get(
                    "done",
                    False
                ),
        }
    )


# =========================================================
# SORT UPCOMING INSTALLATIONS
# =========================================================

boots_events.sort(
    key=lambda item:
        item["date"]
)


# =========================================================
# DISPLAY UPCOMING INSTALLATIONS
# =========================================================

if not boots_events:

    st.success(
        "There are no Boots on the Ground events "
        "scheduled within the next three months."
    )


else:

    upcoming_rows = []


    for item in boots_events:

        days_until_start = (
            item["date"]
            - today
        ).days


        upcoming_rows.append(
            {
                "Start Date":
                    item[
                        "date"
                    ].strftime(
                        "%m/%d/%Y"
                    ),

                "Project":
                    item[
                        "project"
                    ],

                "Building / System":
                    item[
                        "building"
                    ],

                "Designer":
                    item[
                        "designer"
                    ],

                "Days Until Start":
                    days_until_start,

                "Done":
                    (
                        "Yes"
                        if item[
                            "done"
                        ]
                        else "No"
                    ),
            }
        )


    st.dataframe(
        upcoming_rows,
        use_container_width=True,
        hide_index=True,

        column_config={

            "Start Date":
                st.column_config.TextColumn(
                    "Start Date"
                ),

            "Project":
                st.column_config.TextColumn(
                    "Project"
                ),

            "Building / System":
                st.column_config.TextColumn(
                    "Building / System"
                ),

            "Designer":
                st.column_config.TextColumn(
                    "Designer"
                ),

            "Days Until Start":
                st.column_config.NumberColumn(
                    "Days Until Start",
                    format="%d days",
                ),

            "Done":
                st.column_config.TextColumn(
                    "Done"
                ),
        },
    )


    st.caption(
        f"{len(boots_events)} installation start"
        f"{'s' if len(boots_events) != 1 else ''} "
        f"scheduled through "
        f"{three_months_from_today.strftime('%m/%d/%Y')}."
    )


# =========================================================
# PERMIT STATUS FOR UPCOMING INSTALLATIONS
# =========================================================

st.divider()


st.subheader(
    "📝 Permit Status for Upcoming Installations"
)


st.caption(
    "Permit information for projects with an installation "
    "start scheduled within the next three months."
)


# =========================================================
# PROJECTS INCLUDED IN UPCOMING INSTALLATIONS
# =========================================================

upcoming_project_ids = {
    item[
        "project_page_id"
    ]
    for item in boots_events
    if item.get(
        "project_page_id"
    )
}


project_number_lookup = {
    item[
        "project_page_id"
    ]:
        item[
            "project"
        ]

    for item in boots_events

    if item.get(
        "project_page_id"
    )
}


project_start_lookup = {}


for item in boots_events:

    project_page_id = (
        item.get(
            "project_page_id"
        )
    )


    if not project_page_id:
        continue


    existing_date = (
        project_start_lookup.get(
            project_page_id
        )
    )


    if (
        existing_date is None
        or item["date"]
        < existing_date
    ):

        project_start_lookup[
            project_page_id
        ] = item[
            "date"
        ]


# =========================================================
# LOAD PERMITS
# =========================================================

if not upcoming_project_ids:

    st.info(
        "There are no upcoming installation projects "
        "to check for permit information."
    )


elif not NOTION_PERMIT_ID:

    st.warning(
        "Permit information is not configured."
    )


else:

    permit_data_source_id = (
        resolve_data_source_id(
            NOTION_PERMIT_ID
        )
    )


    if not permit_data_source_id:

        st.warning(
            "Permit information is currently unavailable."
        )


    else:

        permit_records = (
            load_permits(
                permit_data_source_id
            )
        )


        permit_rows = []

        projects_with_permit = set()


        # =================================================
        # FILTER PERMIT RECORDS BY UPCOMING PROJECTS
        # =================================================

        for page in permit_records:

            properties = page.get(
                "properties",
                {}
            )


            relation_items = (
                get_permit_project_relation(
                    properties
                )
            )


            related_project_ids = {
                item.get(
                    "id"
                )
                for item in relation_items
                if item.get(
                    "id"
                )
            }


            matching_project_ids = (
                related_project_ids
                & upcoming_project_ids
            )


            if not matching_project_ids:
                continue


            for project_page_id in (
                matching_project_ids
            ):

                projects_with_permit.add(
                    project_page_id
                )


                project_number = (
                    project_number_lookup.get(
                        project_page_id,
                        "—"
                    )
                )


                installation_start = (
                    project_start_lookup.get(
                        project_page_id
                    )
                )


                building = (
                    get_property_text(
                        properties.get(
                            "Building"
                        )
                    )
                    or "—"
                )


                permit_type = (
                    get_property_text(
                        properties.get(
                            "Type"
                        )
                    )
                    or "—"
                )


                ahj = (
                    get_property_text(
                        properties.get(
                            "AHJ"
                        )
                    )
                    or "—"
                )


                submitted_date = (
                    get_date(
                        properties.get(
                            "Submitted Date"
                        )
                    )
                )


                approved_date = (
                    get_date(
                        properties.get(
                            "Approved Date"
                        )
                    )
                )


                status = (
                    get_permit_status(
                        submitted_date,
                        approved_date
                    )
                )


                permit_rows.append(
                    {
                        "_project_page_id":
                            project_page_id,

                        "_status":
                            status,

                        "Installation Start":
                            (
                                installation_start.strftime(
                                    "%m/%d/%Y"
                                )
                                if installation_start
                                else ""
                            ),

                        "Project":
                            project_number,

                        "Building":
                            building,

                        "Permit Type":
                            permit_type,

                        "AHJ":
                            ahj,

                        "Submitted Date":
                            format_date(
                                submitted_date
                            ),

                        "Approved Date":
                            format_date(
                                approved_date
                            ),

                        "Status":
                            status,
                    }
                )


        # =================================================
        # PROJECTS WITHOUT PERMIT RECORD
        # =================================================

        for project_page_id in (
            upcoming_project_ids
        ):

            if (
                project_page_id
                in projects_with_permit
            ):

                continue


            project_number = (
                project_number_lookup.get(
                    project_page_id,
                    "—"
                )
            )


            installation_start = (
                project_start_lookup.get(
                    project_page_id
                )
            )


            permit_rows.append(
                {
                    "_project_page_id":
                        project_page_id,

                    "_status":
                        "No Permit Record",

                    "Installation Start":
                        (
                            installation_start.strftime(
                                "%m/%d/%Y"
                            )
                            if installation_start
                            else ""
                        ),

                    "Project":
                        project_number,

                    "Building":
                        "—",

                    "Permit Type":
                        "—",

                    "AHJ":
                        "—",

                    "Submitted Date":
                        "",

                    "Approved Date":
                        "",

                    "Status":
                        "No Permit Record",
                }
            )


        # =================================================
        # SORT
        # =================================================

        permit_rows.sort(
            key=lambda row: (
                parse_event_date(
                    row[
                        "Installation Start"
                    ]
                )
                or date.max,

                str(
                    row[
                        "Project"
                    ]
                ).lower(),

                str(
                    row[
                        "Permit Type"
                    ]
                ).lower(),
            )
        )


        # =================================================
        # SUMMARY BY PROJECT
        # =================================================

        project_status = {}


        for project_page_id in (
            upcoming_project_ids
        ):

            project_rows = [
                row
                for row in permit_rows
                if row[
                    "_project_page_id"
                ]
                == project_page_id
            ]


            statuses = {
                row[
                    "_status"
                ]
                for row in project_rows
            }


            if (
                not project_rows
                or "No Permit Record"
                in statuses
            ):

                project_status[
                    project_page_id
                ] = (
                    "No Permit Record"
                )


            elif (
                "Not Submitted"
                in statuses
            ):

                project_status[
                    project_page_id
                ] = (
                    "Not Submitted"
                )


            elif (
                "Submitted - Awaiting Approval"
                in statuses
            ):

                project_status[
                    project_page_id
                ] = (
                    "Awaiting Approval"
                )


            else:

                project_status[
                    project_page_id
                ] = (
                    "Approved"
                )


        approved_projects = sum(
            1
            for value in (
                project_status.values()
            )
            if value == "Approved"
        )


        awaiting_projects = sum(
            1
            for value in (
                project_status.values()
            )
            if value
            == "Awaiting Approval"
        )


        not_ready_projects = sum(
            1
            for value in (
                project_status.values()
            )
            if value in {
                "Not Submitted",
                "No Permit Record",
            }
        )


        metric_col1, metric_col2, metric_col3 = (
            st.columns(3)
        )


        with metric_col1:

            st.metric(
                "Projects Approved",
                approved_projects
            )


        with metric_col2:

            st.metric(
                "Projects Awaiting Approval",
                awaiting_projects
            )


        with metric_col3:

            st.metric(
                "Not Submitted / No Record",
                not_ready_projects
            )


        # =================================================
        # ALERT
        # =================================================

        if not_ready_projects > 0:

            st.warning(
                f"{not_ready_projects} upcoming project"
                f"{'s' if not_ready_projects != 1 else ''} "
                "have a Permit that has not been submitted "
                "or do not have a Permit record."
            )


        elif awaiting_projects > 0:

            st.info(
                f"{awaiting_projects} upcoming project"
                f"{'s are' if awaiting_projects != 1 else ' is'} "
                "still awaiting Permit approval."
            )


        else:

            st.success(
                "All upcoming installation projects have "
                "their registered Permits approved."
            )


        # =================================================
        # DISPLAY TABLE
        # =================================================

        display_permit_rows = []


        for row in permit_rows:

            display_permit_rows.append(
                {
                    "Installation Start":
                        row[
                            "Installation Start"
                        ],

                    "Project":
                        row[
                            "Project"
                        ],

                    "Building":
                        row[
                            "Building"
                        ],

                    "Permit Type":
                        row[
                            "Permit Type"
                        ],

                    "AHJ":
                        row[
                            "AHJ"
                        ],

                    "Submitted Date":
                        row[
                            "Submitted Date"
                        ],

                    "Approved Date":
                        row[
                            "Approved Date"
                        ],

                    "Status":
                        row[
                            "Status"
                        ],
                }
            )


        st.dataframe(
            display_permit_rows,
            use_container_width=True,
            hide_index=True,

            column_config={

                "Installation Start":
                    st.column_config.TextColumn(
                        "Installation Start"
                    ),

                "Project":
                    st.column_config.TextColumn(
                        "Project"
                    ),

                "Building":
                    st.column_config.TextColumn(
                        "Building"
                    ),

                "Permit Type":
                    st.column_config.TextColumn(
                        "Permit Type"
                    ),

                "AHJ":
                    st.column_config.TextColumn(
                        "AHJ"
                    ),

                "Submitted Date":
                    st.column_config.TextColumn(
                        "Submitted Date"
                    ),

                "Approved Date":
                    st.column_config.TextColumn(
                        "Approved Date"
                    ),

                "Status":
                    st.column_config.TextColumn(
                        "Status"
                    ),
            },
        )