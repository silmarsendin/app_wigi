import streamlit as st
import requests
import pandas as pd
from datetime import date

from utils.layout import show_sidebar_branding


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Permit",
    page_icon="📋",
    layout="wide",
)


# =========================================================
# NOTION CONFIG
# =========================================================

NOTION_TOKEN = st.secrets["NOTION_TOKEN"]

NOTION_PROJECTS_ID = (
    st.secrets.get("NOTION_PROJECTS_DATA_SOURCE_ID")
    or st.secrets.get("NOTION_PROJECT_DATA_SOURCE_ID")
    or st.secrets.get("NOTION_PROJECTS_DATABASE_ID")
    or st.secrets.get("NOTION_PROJECT_DATABASE_ID")
    or st.secrets.get("PROJECTS_DATA_SOURCE_ID")
    or st.secrets.get("PROJECTS_DATABASE_ID")
)

NOTION_PERMIT_ID = (
    st.secrets.get("NOTION_PERMIT_DATA_SOURCE_ID")
    or st.secrets.get("NOTION_PERMIT_DATABASE_ID")
    or st.secrets.get("PERMIT_DATA_SOURCE_ID")
    or st.secrets.get("PERMIT_DATABASE_ID")
)

NOTION_VERSION = "2025-09-03"

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": NOTION_VERSION,
}


# =========================================================
# VALIDATE CONFIGURATION
# =========================================================

if not NOTION_PROJECTS_ID:
    st.error(
        "Projects table was not found in Streamlit secrets."
    )
    st.stop()


if not NOTION_PERMIT_ID:
    st.error(
        "Permit table was not found in Streamlit secrets."
    )
    st.stop()


# =========================================================
# SIDEBAR BRANDING
# =========================================================

show_sidebar_branding()


# =========================================================
# RESOLVE DATA SOURCE ID
# =========================================================

@st.cache_data(
    ttl=600,
    show_spinner=False
)
def resolve_data_source_id(notion_id):

    # -----------------------------------------------------
    # TRY AS DATA SOURCE ID
    # -----------------------------------------------------

    url = (
        "https://api.notion.com/v1/data_sources/"
        f"{notion_id}"
    )

    try:

        response = requests.get(
            url,
            headers=NOTION_HEADERS,
            timeout=20,
        )

        if response.status_code == 200:
            return notion_id

    except requests.RequestException:
        pass


    # -----------------------------------------------------
    # TRY AS DATABASE ID
    # -----------------------------------------------------

    url = (
        "https://api.notion.com/v1/databases/"
        f"{notion_id}"
    )

    try:

        response = requests.get(
            url,
            headers=NOTION_HEADERS,
            timeout=20,
        )

    except requests.RequestException as error:

        raise Exception(
            "Unable to connect to Notion."
        ) from error


    if response.status_code != 200:

        raise Exception(
            "Unable to identify the Notion database/data source.\n\n"
            f"Status: {response.status_code}\n"
            f"Response: {response.text}"
        )


    data_sources = (
        response.json().get(
            "data_sources",
            []
        )
    )


    if not data_sources:

        raise Exception(
            "No Data Source was found inside "
            "this Notion database."
        )


    return data_sources[0]["id"]


# =========================================================
# RESOLVE DATABASES
# =========================================================

try:

    PROJECTS_DATA_SOURCE_ID = (
        resolve_data_source_id(
            NOTION_PROJECTS_ID
        )
    )

    PERMIT_DATA_SOURCE_ID = (
        resolve_data_source_id(
            NOTION_PERMIT_ID
        )
    )

except Exception as error:

    st.error(
        "Unable to connect to the Notion databases."
    )

    with st.expander(
        "Technical details"
    ):
        st.code(str(error))

    st.stop()


# =========================================================
# QUERY DATA SOURCE
# =========================================================

def query_data_source(
    data_source_id,
    payload=None
):

    url = (
        "https://api.notion.com/v1/data_sources/"
        f"{data_source_id}/query"
    )

    query_payload = dict(
        payload or {}
    )

    query_payload.setdefault(
        "page_size",
        100
    )

    results = []


    while True:

        try:

            response = requests.post(
                url,
                headers=NOTION_HEADERS,
                json=query_payload,
                timeout=30,
            )

        except requests.RequestException as error:

            raise Exception(
                "Unable to connect to Notion."
            ) from error


        if response.status_code != 200:

            raise Exception(
                "Unable to query Notion.\n\n"
                f"Status: {response.status_code}\n"
                f"Response: {response.text}"
            )


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


# =========================================================
# DATA SOURCE SCHEMA
# =========================================================

def get_data_source_schema(
    data_source_id
):

    url = (
        "https://api.notion.com/v1/data_sources/"
        f"{data_source_id}"
    )

    try:

        response = requests.get(
            url,
            headers=NOTION_HEADERS,
            timeout=20,
        )

    except requests.RequestException:

        return {}


    if response.status_code != 200:
        return {}


    return response.json()


# =========================================================
# PROPERTY HELPERS
# =========================================================

def get_property_plain_text(prop):

    if not prop:
        return ""


    prop_type = prop.get(
        "type"
    )


    # -----------------------------------------------------
    # TITLE
    # -----------------------------------------------------

    if prop_type == "title":

        return " ".join(
            item.get(
                "plain_text",
                ""
            )
            for item in prop.get(
                "title",
                []
            )
        ).strip()


    # -----------------------------------------------------
    # RICH TEXT
    # -----------------------------------------------------

    if prop_type == "rich_text":

        return " ".join(
            item.get(
                "plain_text",
                ""
            )
            for item in prop.get(
                "rich_text",
                []
            )
        ).strip()


    # -----------------------------------------------------
    # NUMBER
    # -----------------------------------------------------

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

        return str(
            value
        )


    # -----------------------------------------------------
    # SELECT
    # -----------------------------------------------------

    if prop_type == "select":

        value = prop.get(
            "select"
        )

        if value:

            return value.get(
                "name",
                ""
            )

        return ""


    # -----------------------------------------------------
    # STATUS
    # -----------------------------------------------------

    if prop_type == "status":

        value = prop.get(
            "status"
        )

        if value:

            return value.get(
                "name",
                ""
            )

        return ""


    return ""


# =========================================================
# DATE PROPERTY
# =========================================================

def get_date_property(prop):

    if not prop:
        return None


    date_data = prop.get(
        "date"
    )


    if not date_data:
        return None


    start = date_data.get(
        "start"
    )


    if not start:
        return None


    try:

        return date.fromisoformat(
            start[:10]
        )

    except ValueError:

        return None


# =========================================================
# PROJECT HELPERS
# =========================================================

def get_project_number(page):

    properties = page.get(
        "properties",
        {}
    )


    for property_name in [
        "Number",
        "Project Number",
        "Project",
        "Name",
    ]:

        prop = properties.get(
            property_name
        )


        if not prop:
            continue


        value = (
            get_property_plain_text(
                prop
            )
        )


        if value:
            return value


    return ""


def get_project_name(page):

    properties = page.get(
        "properties",
        {}
    )


    for property_name in [
        "Project Name",
        "Name",
    ]:

        prop = properties.get(
            property_name
        )


        if not prop:
            continue


        value = (
            get_property_plain_text(
                prop
            )
        )


        if value:
            return value


    return ""


# =========================================================
# LOAD PROJECTS
# =========================================================

def load_projects():

    pages = query_data_source(
        PROJECTS_DATA_SOURCE_ID
    )

    projects = []


    for page in pages:

        project_number = (
            get_project_number(
                page
            )
        )


        if not project_number:
            continue


        project_name = (
            get_project_name(
                page
            )
        )


        properties = page.get(
            "properties",
            {}
        )


        designer = (
            get_property_plain_text(
                properties.get(
                    "Designer",
                    {}
                )
            )
            or ""
        ).strip()


        if project_name:

            label = (
                f"{project_number} - "
                f"{project_name}"
            )

        else:

            label = (
                project_number
            )


        projects.append(
            {
                "page_id":
                    page["id"],

                "number":
                    project_number,

                "name":
                    project_name,

                "designer":
                    designer,

                "label":
                    label,
            }
        )


    # -----------------------------------------------------
    # SORT PROJECTS
    # -----------------------------------------------------

    def sort_key(item):

        value = item[
            "number"
        ]

        try:

            return (
                0,
                int(value)
            )

        except (
            ValueError,
            TypeError
        ):

            return (
                1,
                str(value).lower()
            )


    projects.sort(
        key=sort_key
    )


    return projects


# =========================================================
# LOGGED USER PROJECT FILTER
# =========================================================

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


def get_projects_for_logged_designer(
    projects
):

    logged_designer = normalize_text(
        st.session_state.get(
            "user_name"
        )
    )


    if not logged_designer:

        return []


    return [
        project
        for project in projects
        if normalize_text(
            project.get(
                "designer"
            )
        )
        ==
        logged_designer
    ]


# =========================================================
# SELECT OPTIONS
# =========================================================

def get_select_options(
    property_name
):

    schema = get_data_source_schema(
        PERMIT_DATA_SOURCE_ID
    )

    properties = schema.get(
        "properties",
        {}
    )

    prop = properties.get(
        property_name,
        {}
    )


    if prop.get(
        "type"
    ) != "select":

        return []


    options = (
        prop.get(
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
# PROJECT RELATION PROPERTY
# =========================================================

def get_project_relation_property():

    schema = get_data_source_schema(
        PERMIT_DATA_SOURCE_ID
    )

    properties = schema.get(
        "properties",
        {}
    )


    for property_name in [
        "Project",
        "Projects",
    ]:

        prop = properties.get(
            property_name,
            {}
        )

        if prop.get(
            "type"
        ) == "relation":

            return property_name


    for property_name, prop in (
        properties.items()
    ):

        if prop.get(
            "type"
        ) == "relation":

            return property_name


    return None


PROJECT_RELATION_PROPERTY = (
    get_project_relation_property()
)


if not PROJECT_RELATION_PROPERTY:

    st.error(
        "A Project relation property was not found "
        "in the Permit table."
    )

    st.stop()


# =========================================================
# CREATE PERMIT
# =========================================================

def create_permit(
    project_page_id,
    building,
    submitted_date,
    approved_date,
    ahj,
    permit_type,
):

    properties = {

        "Building": {
            "title": [
                {
                    "text": {
                        "content":
                            building
                    }
                }
            ]
        },

        PROJECT_RELATION_PROPERTY: {
            "relation": [
                {
                    "id":
                        project_page_id
                }
            ]
        },

        "AHJ": {
            "select": {
                "name":
                    ahj
            }
        },

        "Type": {
            "select": {
                "name":
                    permit_type
            }
        },
    }


    if submitted_date:

        properties[
            "Submitted Date"
        ] = {
            "date": {
                "start":
                    submitted_date.isoformat()
            }
        }


    if approved_date:

        properties[
            "Approved Date"
        ] = {
            "date": {
                "start":
                    approved_date.isoformat()
            }
        }


    payload = {

        "parent": {
            "type":
                "data_source_id",

            "data_source_id":
                PERMIT_DATA_SOURCE_ID,
        },

        "properties":
            properties,
    }


    url = (
        "https://api.notion.com/v1/pages"
    )


    try:

        response = requests.post(
            url,
            headers=NOTION_HEADERS,
            json=payload,
            timeout=30,
        )

    except requests.RequestException as error:

        raise Exception(
            "Unable to connect to Notion."
        ) from error


    if response.status_code not in [
        200,
        201,
    ]:

        raise Exception(
            "Unable to create Permit.\n\n"
            f"Status: {response.status_code}\n"
            f"Response: {response.text}"
        )


    return response.json()


# =========================================================
# UPDATE PERMIT
# =========================================================

def update_permit(
    page_id,
    project_page_id,
    building,
    submitted_date,
    approved_date,
    ahj,
    permit_type,
):

    properties = {

        "Building": {
            "title": [
                {
                    "text": {
                        "content":
                            building
                    }
                }
            ]
        },

        PROJECT_RELATION_PROPERTY: {
            "relation": [
                {
                    "id":
                        project_page_id
                }
            ]
        },

        "AHJ": {
            "select": {
                "name":
                    ahj
            }
        },

        "Type": {
            "select": {
                "name":
                    permit_type
            }
        },

        "Submitted Date": {
            "date": (
                {
                    "start":
                        submitted_date.isoformat()
                }
                if submitted_date
                else None
            )
        },

        "Approved Date": {
            "date": (
                {
                    "start":
                        approved_date.isoformat()
                }
                if approved_date
                else None
            )
        },
    }


    url = (
        "https://api.notion.com/v1/pages/"
        f"{page_id}"
    )


    try:

        response = requests.patch(
            url,
            headers=NOTION_HEADERS,
            json={
                "properties":
                    properties
            },
            timeout=30,
        )

    except requests.RequestException as error:

        raise Exception(
            "Unable to connect to Notion."
        ) from error


    if response.status_code != 200:

        raise Exception(
            "Unable to update Permit.\n\n"
            f"Status: {response.status_code}\n"
            f"Response: {response.text}"
        )


    return response.json()


# =========================================================
# LOAD PERMITS
# =========================================================

def load_permits(
    project_lookup_by_id
):

    pages = query_data_source(
        PERMIT_DATA_SOURCE_ID
    )

    permits = []


    for page in pages:

        properties = page.get(
            "properties",
            {}
        )


        # -------------------------------------------------
        # BUILDING
        # -------------------------------------------------

        building = (
            get_property_plain_text(
                properties.get(
                    "Building",
                    {}
                )
            )
        )


        # -------------------------------------------------
        # AHJ
        # -------------------------------------------------

        ahj = (
            get_property_plain_text(
                properties.get(
                    "AHJ",
                    {}
                )
            )
        )


        # -------------------------------------------------
        # TYPE
        # -------------------------------------------------

        permit_type = (
            get_property_plain_text(
                properties.get(
                    "Type",
                    {}
                )
            )
        )


        # -------------------------------------------------
        # DATES
        # -------------------------------------------------

        submitted_date = (
            get_date_property(
                properties.get(
                    "Submitted Date",
                    {}
                )
            )
        )

        approved_date = (
            get_date_property(
                properties.get(
                    "Approved Date",
                    {}
                )
            )
        )


        # -------------------------------------------------
        # PROJECT RELATION
        # -------------------------------------------------

        relation = (
            properties.get(
                PROJECT_RELATION_PROPERTY,
                {}
            )
            .get(
                "relation",
                []
            )
        )


        project_page_id = (
            relation[0]["id"]
            if relation
            else None
        )


        project = (
            project_lookup_by_id.get(
                project_page_id
            )
        )


        project_label = (
            project["label"]
            if project
            else "Unknown Project"
        )


        # -------------------------------------------------
        # DISPLAY LABEL
        # -------------------------------------------------

        label_parts = [
            project_label
        ]


        if building:

            label_parts.append(
                building
            )


        if permit_type:

            label_parts.append(
                permit_type
            )


        permits.append(
            {
                "page_id":
                    page["id"],

                "project_page_id":
                    project_page_id,

                "project_label":
                    project_label,

                "building":
                    building,

                "ahj":
                    ahj,

                "type":
                    permit_type,

                "submitted_date":
                    submitted_date,

                "approved_date":
                    approved_date,

                "label":
                    " | ".join(
                        label_parts
                    ),
            }
        )


    permits.sort(
        key=lambda item:
            item["label"].lower()
    )


    return permits


# =========================================================
# SELECT WITH ADD NEW
# =========================================================

def select_with_add_new(
    label,
    options,
    key,
    current_value=None,
):

    options = list(
        options
    )


    if (
        current_value
        and current_value not in options
    ):

        options.append(
            current_value
        )


    add_new_option = (
        "➕ Add new..."
    )


    display_options = (
        options
        + [
            add_new_option
        ]
    )


    index = None


    if (
        current_value
        and current_value
        in display_options
    ):

        index = (
            display_options.index(
                current_value
            )
        )


    selection = st.selectbox(
        label,
        options=
            display_options,
        index=
            index,
        placeholder=
            f"Select {label}...",
        key=
            key,
    )


    if selection == add_new_option:

        new_value = st.text_input(
            f"New {label}",
            placeholder=
                f"Enter a new {label}...",
            key=
                f"{key}_new",
        )

        return (
            new_value.strip()
        )


    return selection


# =========================================================
# APPROVAL TIME CHART
# =========================================================

def render_approval_time_chart(
    permits
):

    st.subheader(
        "📊 Average Permit Approval Time by AHJ"
    )

    st.caption(
        "Average number of days between Submitted Date "
        "and Approved Date. Only Permits with both dates "
        "are included."
    )


    completed_permits = []


    # -----------------------------------------------------
    # FILTER VALID RECORDS
    # -----------------------------------------------------

    for permit in permits:

        submitted_date = (
            permit.get(
                "submitted_date"
            )
        )

        approved_date = (
            permit.get(
                "approved_date"
            )
        )

        ahj = (
            permit.get(
                "ahj"
            )
            or ""
        ).strip()


        # Only permits with both dates and AHJ
        if (
            not submitted_date
            or not approved_date
            or not ahj
        ):

            continue


        approval_days = (
            approved_date
            - submitted_date
        ).days


        # Ignore invalid records
        if approval_days < 0:

            continue


        completed_permits.append(
            {
                "AHJ":
                    ahj,

                "Approval Days":
                    approval_days,
            }
        )


    # -----------------------------------------------------
    # NO DATA
    # -----------------------------------------------------

    if not completed_permits:

        st.info(
            "There are no Permits with both "
            "Submitted Date and Approved Date yet."
        )

        return


    # -----------------------------------------------------
    # CREATE DATAFRAME
    # -----------------------------------------------------

    df = pd.DataFrame(
        completed_permits
    )


    # -----------------------------------------------------
    # CALCULATE AVERAGE
    # -----------------------------------------------------

    average_df = (
        df
        .groupby(
            "AHJ",
            as_index=False
        )
        .agg(
            Average_Days=(
                "Approval Days",
                "mean"
            ),
            Permits=(
                "Approval Days",
                "count"
            ),
        )
    )


    average_df[
        "Average_Days"
    ] = (
        average_df[
            "Average_Days"
        ]
        .round(1)
    )


    # -----------------------------------------------------
    # SORT FROM LONGEST TO SHORTEST
    # -----------------------------------------------------

    average_df = (
        average_df
        .sort_values(
            "Average_Days",
            ascending=False
        )
        .reset_index(
            drop=True
        )
    )


    # -----------------------------------------------------
    # OVERALL STATISTICS
    # -----------------------------------------------------

    total_completed = (
        len(
            completed_permits
        )
    )

    overall_average = (
        df[
            "Approval Days"
        ]
        .mean()
    )


    fastest_ahj = (
        average_df
        .sort_values(
            "Average_Days",
            ascending=True
        )
        .iloc[0]
    )


    col1, col2, col3 = (
        st.columns(3)
    )


    with col1:

        st.metric(
            "Approved Permits",
            total_completed
        )


    with col2:

        st.metric(
            "Overall Average",
            f"{overall_average:.1f} days"
        )


    with col3:

        st.metric(
            "Fastest AHJ",
            fastest_ahj[
                "AHJ"
            ],
            f"{fastest_ahj['Average_Days']:.1f} days"
        )


    # -----------------------------------------------------
    # BAR CHART
    # -----------------------------------------------------

    chart_df = (
        average_df[
            [
                "AHJ",
                "Average_Days"
            ]
        ]
        .rename(
            columns={
                "Average_Days":
                    "Average Approval Time"
            }
        )
        .set_index(
            "AHJ"
        )
    )


    st.bar_chart(
        chart_df,
        use_container_width=True,
        x_label="AHJ",
        y_label="Average Approval Time (Days)",
    )


    # -----------------------------------------------------
    # DETAILS TABLE
    # -----------------------------------------------------

    with st.expander(
        "View Approval Statistics",
        expanded=False,
    ):

        display_df = (
            average_df.rename(
                columns={
                    "Average_Days":
                        "Average Days",

                    "Permits":
                        "Approved Permits",
                }
            )
        )


        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
        )


# =========================================================
# PAGE HEADER
# =========================================================

st.title(
    "📋 Permit"
)

st.write(
    "Register and manage permit information."
)

st.divider()


# =========================================================
# LOAD PROJECTS
# =========================================================

try:

    projects = (
        load_projects()
    )

except Exception as error:

    st.error(
        "Unable to load Projects from Notion."
    )

    with st.expander(
        "Technical details"
    ):

        st.code(
            str(error)
        )

    st.stop()


if not projects:

    st.warning(
        "No Projects were found."
    )

    st.stop()


# =========================================================
# PROJECT LOOKUPS
# =========================================================

# All Projects remain available for existing Permit records
# and for the global approval-time statistics.
project_lookup = {
    project[
        "label"
    ]:
        project

    for project in projects
}


project_lookup_by_id = {
    project[
        "page_id"
    ]:
        project

    for project in projects
}


# Only the logged user's own Designer Projects are available
# in the first Project selector under New Permit.
logged_designer_projects = (
    get_projects_for_logged_designer(
        projects
    )
)


new_permit_project_lookup = {
    project[
        "label"
    ]:
        project

    for project in logged_designer_projects
}


# =========================================================
# LOAD SELECT OPTIONS
# =========================================================

ahj_options = (
    get_select_options(
        "AHJ"
    )
)


type_options = (
    get_select_options(
        "Type"
    )
)


# =========================================================
# LOAD EXISTING PERMITS ONCE
# =========================================================

try:

    permits = (
        load_permits(
            project_lookup_by_id
        )
    )

except Exception as error:

    permits = []

    st.warning(
        "Unable to load existing Permits."
    )

    with st.expander(
        "Technical details"
    ):

        st.code(
            str(error)
        )


# =========================================================
# NEW PERMIT
# =========================================================

st.subheader(
    "New Permit"
)


if not new_permit_project_lookup:

    st.info(
        "No Projects were found where you are assigned as Designer."
    )


with st.form(
    "new_permit_form",
    clear_on_submit=True,
):

    # -----------------------------------------------------
    # PROJECT / BUILDING
    # -----------------------------------------------------

    col1, col2 = (
        st.columns(2)
    )


    with col1:

        selected_project_label = (
            st.selectbox(
                "Project",
                options=list(
                    new_permit_project_lookup.keys()
                ),
                index=None,
                placeholder=
                    "Select a project...",
            )
        )


    with col2:

        building = (
            st.text_input(
                "Building",
                placeholder=
                    "Example: Building 100 or Total",
            )
        )


    # -----------------------------------------------------
    # TYPE / AHJ
    # -----------------------------------------------------

    col3, col4 = (
        st.columns(2)
    )


    with col3:

        permit_type = (
            select_with_add_new(
                "Type",
                type_options,
                "new_permit_type",
            )
        )


    with col4:

        ahj = (
            select_with_add_new(
                "AHJ",
                ahj_options,
                "new_permit_ahj",
            )
        )


    # -----------------------------------------------------
    # DATES
    # -----------------------------------------------------

    col5, col6 = (
        st.columns(2)
    )


    with col5:

        has_submitted_date = (
            st.checkbox(
                "Permit has been submitted",
                value=True,
            )
        )


        submitted_date = None


        if has_submitted_date:

            submitted_date = (
                st.date_input(
                    "Submitted Date",
                    value=date.today(),
                )
            )


    with col6:

        has_approved_date = (
            st.checkbox(
                "Permit has been approved",
                value=False,
            )
        )


        approved_date = None


        if has_approved_date:

            approved_date = (
                st.date_input(
                    "Approved Date",
                    value=date.today(),
                )
            )


    st.write("")


    save_new = (
        st.form_submit_button(
            "💾 Save Permit",
            type="primary",
            use_container_width=True,
        )
    )


# =========================================================
# SAVE NEW PERMIT
# =========================================================

if save_new:

    errors = []


    if not selected_project_label:

        errors.append(
            "Please select a Project."
        )


    if not building.strip():

        errors.append(
            "Please enter the Building."
        )


    if not permit_type:

        errors.append(
            "Please select or enter the Type."
        )


    if not ahj:

        errors.append(
            "Please select or enter the AHJ."
        )


    if (
        submitted_date
        and approved_date
        and approved_date < submitted_date
    ):

        errors.append(
            "Approved Date cannot be before "
            "Submitted Date."
        )


    if errors:

        for error in errors:

            st.error(
                error
            )


    else:

        selected_project = (
            new_permit_project_lookup[
                selected_project_label
            ]
        )


        try:

            with st.spinner(
                "Saving Permit..."
            ):

                create_permit(
                    project_page_id=
                        selected_project[
                            "page_id"
                        ],

                    building=
                        building.strip(),

                    submitted_date=
                        submitted_date,

                    approved_date=
                        approved_date,

                    ahj=
                        ahj.strip(),

                    permit_type=
                        permit_type.strip(),
                )


            st.success(
                "Permit successfully saved!"
            )


            st.cache_data.clear()

            st.rerun()


        except Exception as error:

            st.error(
                "Unable to save Permit to Notion."
            )


            with st.expander(
                "Technical details"
            ):

                st.code(
                    str(error)
                )


# =========================================================
# RESET EDIT PERMIT STATE
# =========================================================

def reset_edit_permit_fields(
    clear_selection=False
):

    keys_to_clear = [
        "edit_project",
        "edit_building",
        "edit_type",
        "edit_type_new",
        "edit_ahj",
        "edit_ahj_new",
        "edit_has_submitted",
        "edit_submitted_date",
        "edit_has_approved",
        "edit_approved_date",
        "update_permit_button",
    ]

    for key in keys_to_clear:

        st.session_state.pop(
            key,
            None
        )

    if clear_selection:

        st.session_state.pop(
            "edit_permit_selection",
            None
        )


# =========================================================
# EXISTING PERMITS / UPDATE
# =========================================================

st.divider()


with st.expander(
    "📋 Existing Permits / Update Permit",
    expanded=False,
):

    st.caption(
        "View an existing Permit and update its information."
    )


    if not permits:

        st.info(
            "No Permits have been registered yet."
        )


    else:

        # Existing Permits / Update Permit:
        # show only permits related to Projects where the
        # logged-in user is the assigned Designer.
        allowed_project_ids = {
            project[
                "page_id"
            ]
            for project in logged_designer_projects
        }


        filtered_permits = [
            permit
            for permit in permits
            if permit.get(
                "project_page_id"
            )
            in allowed_project_ids
        ]


        permit_lookup = {
            permit[
                "label"
            ]:
                permit

            for permit in filtered_permits
        }


        if not permit_lookup:

            st.info(
                "No existing Permits were found for Projects "
                "where you are assigned as Designer."
            )


        selected_permit_label = (
            st.selectbox(
                "Select Permit to Edit",
                options=list(
                    permit_lookup.keys()
                ),
                index=None,
                placeholder=
                    "Select an existing Permit...",
                key=
                    "edit_permit_selection",
                on_change=
                    reset_edit_permit_fields,
            )
        )


        if selected_permit_label:

            permit = (
                permit_lookup[
                    selected_permit_label
                ]
            )


            # =============================================
            # CURRENT INFORMATION
            # =============================================

            st.markdown(
                "#### Current Information"
            )


            current_data = [
                {
                    "Project":
                        permit[
                            "project_label"
                        ],

                    "Building":
                        permit[
                            "building"
                        ],

                    "Type":
                        permit[
                            "type"
                        ],

                    "AHJ":
                        permit[
                            "ahj"
                        ],

                    "Submitted":
                        (
                            permit[
                                "submitted_date"
                            ].strftime(
                                "%m/%d/%Y"
                            )
                            if permit[
                                "submitted_date"
                            ]
                            else ""
                        ),

                    "Approved":
                        (
                            permit[
                                "approved_date"
                            ].strftime(
                                "%m/%d/%Y"
                            )
                            if permit[
                                "approved_date"
                            ]
                            else ""
                        ),
                }
            ]


            st.dataframe(
                current_data,
                use_container_width=True,
                hide_index=True,
            )


            st.markdown(
                "#### Update Permit"
            )


            # =============================================
            # CURRENT PROJECT
            # =============================================

            project_labels = list(
                project_lookup.keys()
            )


            current_project_index = 0


            if (
                permit["project_label"]
                in project_labels
            ):

                current_project_index = (
                    project_labels.index(
                        permit[
                            "project_label"
                        ]
                    )
                )


            # =============================================
            # EDIT PERMIT
            # =============================================
            # This section intentionally does NOT use st.form().
            # Streamlit forms batch widget changes and do not
            # rerun immediately, which prevented Approved Date
            # from appearing as soon as the Approved checkbox
            # was selected.

            with st.container(
                border=True
            ):

                edit_col1, edit_col2 = (
                    st.columns(2)
                )

                with edit_col1:

                    edit_project_label = (
                        st.selectbox(
                            "Project",
                            options=
                                project_labels,
                            index=
                                current_project_index,
                            key=
                                "edit_project",
                        )
                    )

                with edit_col2:

                    edit_building = (
                        st.text_input(
                            "Building",
                            value=
                                permit[
                                    "building"
                                ],
                            placeholder=
                                "Example: Building 100 or Total",
                            key=
                                "edit_building",
                        )
                    )

                edit_col3, edit_col4 = (
                    st.columns(2)
                )

                with edit_col3:

                    edit_type = (
                        select_with_add_new(
                            "Type",
                            type_options,
                            "edit_type",
                            permit["type"],
                        )
                    )

                with edit_col4:

                    edit_ahj = (
                        select_with_add_new(
                            "AHJ",
                            ahj_options,
                            "edit_ahj",
                            permit["ahj"],
                        )
                    )

                edit_col5, edit_col6 = (
                    st.columns(2)
                )

                with edit_col5:

                    edit_has_submitted = (
                        st.checkbox(
                            "Permit has been submitted",
                            value=(
                                permit[
                                    "submitted_date"
                                ]
                                is not None
                            ),
                            key=
                                "edit_has_submitted",
                        )
                    )

                    edit_submitted_date = None

                    if edit_has_submitted:

                        edit_submitted_date = (
                            st.date_input(
                                "Submitted Date",
                                value=(
                                    permit[
                                        "submitted_date"
                                    ]
                                    or date.today()
                                ),
                                key=
                                    "edit_submitted_date",
                            )
                        )

                with edit_col6:

                    edit_has_approved = (
                        st.checkbox(
                            "Permit has been approved",
                            value=(
                                permit[
                                    "approved_date"
                                ]
                                is not None
                            ),
                            key=
                                "edit_has_approved",
                        )
                    )

                    edit_approved_date = None

                    if edit_has_approved:

                        edit_approved_date = (
                            st.date_input(
                                "Approved Date",
                                value=(
                                    permit[
                                        "approved_date"
                                    ]
                                    or date.today()
                                ),
                                key=
                                    "edit_approved_date",
                            )
                        )

                st.write("")

                update_button = (
                    st.button(
                        "💾 Update Permit",
                        type="primary",
                        use_container_width=True,
                        key=
                            "update_permit_button",
                    )
                )


            # =============================================
            # UPDATE
            # =============================================

            if update_button:

                update_errors = []


                if not edit_building.strip():

                    update_errors.append(
                        "Please enter the Building."
                    )


                if not edit_type:

                    update_errors.append(
                        "Please select or enter the Type."
                    )


                if not edit_ahj:

                    update_errors.append(
                        "Please select or enter the AHJ."
                    )


                if (
                    edit_submitted_date
                    and edit_approved_date
                    and edit_approved_date
                    < edit_submitted_date
                ):

                    update_errors.append(
                        "Approved Date cannot be before "
                        "Submitted Date."
                    )


                if update_errors:

                    for error in update_errors:

                        st.error(
                            error
                        )


                else:

                    selected_project = (
                        project_lookup[
                            edit_project_label
                        ]
                    )


                    try:

                        with st.spinner(
                            "Updating Permit..."
                        ):

                            update_permit(
                                page_id=
                                    permit[
                                        "page_id"
                                    ],

                                project_page_id=
                                    selected_project[
                                        "page_id"
                                    ],

                                building=
                                    edit_building.strip(),

                                submitted_date=
                                    edit_submitted_date,

                                approved_date=
                                    edit_approved_date,

                                ahj=
                                    edit_ahj.strip(),

                                permit_type=
                                    edit_type.strip(),
                            )


                        st.success(
                            "Permit successfully updated!"
                        )

                        st.cache_data.clear()

                        # Return the Update Permit section to its
                        # initial state so the user must choose
                        # another Permit before editing again.
                        reset_edit_permit_fields(
                            clear_selection=True
                        )

                        st.rerun()


                    except Exception as error:

                        st.error(
                            "Unable to update Permit."
                        )


                        with st.expander(
                            "Technical details"
                        ):

                            st.code(
                                str(error)
                            )


# =========================================================
# APPROVAL STATISTICS
# ALWAYS VISIBLE AT THE BOTTOM OF THE PAGE
# =========================================================

st.divider()


render_approval_time_chart(
    permits
)