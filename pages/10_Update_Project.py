import streamlit as st
import requests
import streamlit.components.v1 as components

from urllib.parse import quote
from datetime import date, datetime


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Update Project",
    page_icon="✏️",
    layout="wide",
)


# =========================================================
# LOGIN CHECK
# =========================================================

if not st.session_state.get(
    "authenticated",
    False,
):

    st.error(
        "You must be signed in to access this page."
    )

    st.stop()


logged_user_name = (
    st.session_state.get(
        "user_name"
    )
)

logged_user_role = (
    st.session_state.get(
        "user_role",
        "User",
    )
)


if not logged_user_name:

    st.error(
        "Unable to identify the logged-in user."
    )

    st.stop()


# =========================================================
# PAGE HEADER
# =========================================================

st.title(
    "✏️ Update Project"
)

st.caption(
    "Update project information and manage "
    "its forecast schedule."
)


# =========================================================
# CONFIGURATION
# =========================================================

NOTION_TOKEN = (
    st.secrets[
        "NOTION_TOKEN"
    ]
)

PROJECTS_DATA_SOURCE_ID = (
    st.secrets[
        "NOTION_PROJECTS_DATA_SOURCE_ID"
    ]
)

FORECAST_DATA_SOURCE_ID = (
    st.secrets[
        "NOTION_FORECAST_DATA_SOURCE_ID"
    ]
)


NOTION_VERSION = (
    "2026-03-11"
)


HEADERS = {
    "Authorization":
        f"Bearer {NOTION_TOKEN}",

    "Notion-Version":
        NOTION_VERSION,

    "Content-Type":
        "application/json",
}


PROJECTS_DATA_SOURCE_URL = (
    "https://api.notion.com/v1/data_sources/"
    f"{PROJECTS_DATA_SOURCE_ID}"
)


PROJECTS_QUERY_URL = (
    "https://api.notion.com/v1/data_sources/"
    f"{PROJECTS_DATA_SOURCE_ID}/query"
)


FORECAST_DATA_SOURCE_URL = (
    "https://api.notion.com/v1/data_sources/"
    f"{FORECAST_DATA_SOURCE_ID}"
)


FORECAST_QUERY_URL = (
    "https://api.notion.com/v1/data_sources/"
    f"{FORECAST_DATA_SOURCE_ID}/query"
)


# =========================================================
# GENERAL HELPERS
# =========================================================

def normalize_text(value):

    return (
        str(
            value or ""
        )
        .strip()
        .casefold()
    )


def safe_request_error(
    response,
    action,
):

    raise Exception(
        f"{action}\n\n"
        f"Status: {response.status_code}\n"
        f"Response: {response.text}"
    )


# =========================================================
# SCHEMA HELPERS
# =========================================================

@st.cache_data(
    ttl=300,
    show_spinner=False,
)
def get_projects_schema():

    response = requests.get(
        PROJECTS_DATA_SOURCE_URL,
        headers=HEADERS,
        timeout=30,
    )


    if response.status_code != 200:

        safe_request_error(
            response,
            "Unable to retrieve the Projects structure.",
        )


    return response.json()


@st.cache_data(
    ttl=300,
    show_spinner=False,
)
def get_forecast_schema():

    response = requests.get(
        FORECAST_DATA_SOURCE_URL,
        headers=HEADERS,
        timeout=30,
    )


    if response.status_code != 200:

        safe_request_error(
            response,
            "Unable to retrieve the Forecast structure.",
        )


    return response.json()


# =========================================================
# PROPERTY READ HELPERS
# =========================================================

def get_title(
    properties,
    property_name,
):

    prop = properties.get(
        property_name,
        {},
    )


    values = prop.get(
        "title",
        [],
    )


    return "".join(
        item.get(
            "plain_text",
            "",
        )
        for item in values
    ).strip()


def get_text(
    properties,
    property_name,
):

    prop = properties.get(
        property_name,
        {},
    )


    values = prop.get(
        "rich_text",
        [],
    )


    return "".join(
        item.get(
            "plain_text",
            "",
        )
        for item in values
    ).strip()


def get_number(
    properties,
    property_name,
    default=0.0,
):

    prop = properties.get(
        property_name,
        {},
    )


    value = prop.get(
        "number"
    )


    if value is None:
        return default


    return float(
        value
    )


def get_select(
    properties,
    property_name,
    default="",
):

    prop = properties.get(
        property_name,
        {},
    )


    value = prop.get(
        "select"
    )


    if not value:
        return default


    return value.get(
        "name",
        default,
    )


def get_status(
    properties,
    property_name,
    default="",
):

    prop = properties.get(
        property_name,
        {},
    )


    value = prop.get(
        "status"
    )


    if not value:
        return default


    return value.get(
        "name",
        default,
    )


def get_checkbox(
    properties,
    property_name,
    default=False,
):

    prop = properties.get(
        property_name,
        {},
    )


    return bool(
        prop.get(
            "checkbox",
            default,
        )
    )


def get_date_value(
    properties,
    property_name,
):

    prop = properties.get(
        property_name,
        {},
    )


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


def get_formula_value(prop):

    if not prop:
        return ""


    formula = prop.get(
        "formula"
    )


    if not formula:
        return ""


    formula_type = (
        formula.get(
            "type"
        )
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

        if value is None:
            return ""

        return str(
            value
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
                "",
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


    rollup_type = (
        rollup.get(
            "type"
        )
    )


    if rollup_type == "array":

        values = []


        for item in rollup.get(
            "array",
            [],
        ):

            item_type = item.get(
                "type"
            )


            if item_type == "title":

                values.extend(
                    value.get(
                        "plain_text",
                        "",
                    )
                    for value in item.get(
                        "title",
                        [],
                    )
                )


            elif item_type == "rich_text":

                values.extend(
                    value.get(
                        "plain_text",
                        "",
                    )
                    for value in item.get(
                        "rich_text",
                        [],
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
                            "",
                        )
                    )


            elif item_type == "status":

                selected = item.get(
                    "status"
                )

                if selected:

                    values.append(
                        selected.get(
                            "name",
                            "",
                        )
                    )


            elif item_type == "number":

                value = item.get(
                    "number"
                )

                if value is not None:

                    values.append(
                        str(
                            value
                        )
                    )


            elif item_type == "formula":

                value = (
                    get_formula_value(
                        item
                    )
                )

                if value:

                    values.append(
                        value
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


        if value is None:
            return ""


        return str(
            value
        )


    return ""


def get_property_plain_text(prop):

    if not prop:
        return ""


    prop_type = prop.get(
        "type"
    )


    if prop_type == "title":

        return "".join(
            item.get(
                "plain_text",
                "",
            )
            for item in prop.get(
                "title",
                [],
            )
        ).strip()


    if prop_type == "rich_text":

        return "".join(
            item.get(
                "plain_text",
                "",
            )
            for item in prop.get(
                "rich_text",
                [],
            )
        ).strip()


    if prop_type == "select":

        value = prop.get(
            "select"
        )

        if value:

            return value.get(
                "name",
                "",
            )


    if prop_type == "status":

        value = prop.get(
            "status"
        )

        if value:

            return value.get(
                "name",
                "",
            )


    if prop_type == "formula":

        return (
            get_formula_value(
                prop
            )
        )


    if prop_type == "rollup":

        return (
            get_rollup_text(
                prop
            )
        )


    if prop_type == "number":

        value = prop.get(
            "number"
        )

        if value is None:
            return ""


        if (
            isinstance(
                value,
                float,
            )
            and value.is_integer()
        ):

            return str(
                int(value)
            )


        return str(
            value
        )


    return ""


# =========================================================
# SCHEMA PROPERTY HELPERS
# =========================================================

def get_select_options(
    schema,
    property_name,
):

    prop = (
        schema
        .get(
            "properties",
            {},
        )
        .get(
            property_name
        )
    )


    if not prop:
        return []


    if (
        prop.get(
            "type"
        )
        != "select"
    ):

        return []


    return [
        option.get(
            "name",
            "",
        )
        for option in (
            prop.get(
                "select",
                {},
            )
            .get(
                "options",
                [],
            )
        )
        if option.get(
            "name"
        )
    ]


def get_status_options(
    schema,
    property_name,
):

    prop = (
        schema
        .get(
            "properties",
            {},
        )
        .get(
            property_name
        )
    )


    if not prop:

        return []


    if (
        prop.get(
            "type"
        )
        != "status"
    ):

        return []


    return [
        option.get(
            "name",
            "",
        )
        for option in (
            prop.get(
                "status",
                {},
            )
            .get(
                "options",
                [],
            )
        )
        if option.get(
            "name"
        )
    ]


def get_checkbox_properties(
    schema
):

    properties = schema.get(
        "properties",
        {},
    )


    checkbox_fields = []


    for (
        property_name,
        property_data,
    ) in properties.items():

        if (
            property_data.get(
                "type"
            )
            == "checkbox"
        ):

            checkbox_fields.append(
                property_name
            )


    return sorted(
        checkbox_fields
    )


def get_property_type(
    schema,
    property_name,
):

    return (
        schema
        .get(
            "properties",
            {},
        )
        .get(
            property_name,
            {},
        )
        .get(
            "type"
        )
    )


# =========================================================
# LOAD PROJECTS
# =========================================================

@st.cache_data(
    ttl=60,
    show_spinner=False,
)
def load_projects(
    user_name,
    user_role,
):

    # =====================================================
    # ONLY PROJECTS ASSIGNED TO THE LOGGED-IN USER
    # =====================================================
    #
    # This filter applies to every role, including Manager.
    # The first Project selector therefore always shows only
    # projects whose Designer matches the active user.
    # =====================================================

    payload = {
        "page_size":
            100,

        "filter": {

            "property":
                "Designer",

            "select": {

                "equals":
                    user_name,
            }
        }
    }


    projects = []

    next_cursor = None


    while True:

        current_payload = (
            payload.copy()
        )


        if next_cursor:

            current_payload[
                "start_cursor"
            ] = next_cursor


        response = requests.post(
            PROJECTS_QUERY_URL,
            headers=HEADERS,
            json=current_payload,
            timeout=30,
        )


        if response.status_code != 200:

            safe_request_error(
                response,
                "Unable to retrieve Projects.",
            )


        data = (
            response.json()
        )


        projects.extend(
            data.get(
                "results",
                [],
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


    return projects


# =========================================================
# PROJECT PHOTO UPLOAD
# =========================================================

def upload_png(
    uploaded_file
):

    create_upload_url = (
        "https://api.notion.com/v1/file_uploads"
    )


    upload_payload = {

        "mode":
            "single_part",

        "filename":
            uploaded_file.name,

        "content_type":
            "image/png",
    }


    response = requests.post(
        create_upload_url,
        headers=HEADERS,
        json=upload_payload,
        timeout=30,
    )


    if response.status_code != 200:

        safe_request_error(
            response,
            "Unable to initialize the image upload.",
        )


    file_upload_id = (
        response.json()[
            "id"
        ]
    )


    send_url = (
        "https://api.notion.com/v1/file_uploads/"
        f"{file_upload_id}/send"
    )


    upload_headers = {

        "Authorization":
            f"Bearer {NOTION_TOKEN}",

        "Notion-Version":
            NOTION_VERSION,
    }


    uploaded_file.seek(
        0
    )


    files = {

        "file": (
            uploaded_file.name,
            uploaded_file.getvalue(),
            "image/png",
        )
    }


    response = requests.post(
        send_url,
        headers=upload_headers,
        files=files,
        timeout=60,
    )


    if response.status_code != 200:

        safe_request_error(
            response,
            "Unable to upload the project image.",
        )


    return (
        file_upload_id
    )


# =========================================================
# LOAD SCHEMAS
# =========================================================

try:

    projects_schema = (
        get_projects_schema()
    )

    forecast_schema = (
        get_forecast_schema()
    )


except Exception as error:

    st.error(
        "Unable to retrieve the application data structure."
    )

    with st.expander(
        "Technical details"
    ):

        st.code(
            str(error)
        )


    st.stop()


# =========================================================
# PROJECT FIELD OPTIONS
# =========================================================

designer_options = (
    get_select_options(
        projects_schema,
        "Designer",
    )
)


checkbox_fields = (
    get_checkbox_properties(
        projects_schema
    )
)


# =========================================================
# PROJECT STATUS CHECKBOX ORDER
# =========================================================
#
# The Project Status section uses the same milestone order
# as the Home page, with Installed added as the final item.
#
# Aliases allow small spelling differences in the actual
# Projects table property names.
# =========================================================

PROJECT_STATUS_CHECKBOX_CONFIG = [
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
    {
        "display_name": "Installed",
        "aliases": [
            "Installed",
        ],
    },
]


def resolve_project_status_checkboxes(
    available_checkbox_fields
):

    normalized_lookup = {
        normalize_text(field_name):
            field_name
        for field_name in available_checkbox_fields
    }

    resolved_fields = []

    for config in (
        PROJECT_STATUS_CHECKBOX_CONFIG
    ):

        actual_field_name = None

        for alias in config[
            "aliases"
        ]:

            normalized_alias = (
                normalize_text(
                    alias
                )
            )

            if (
                normalized_alias
                in normalized_lookup
            ):

                actual_field_name = (
                    normalized_lookup[
                        normalized_alias
                    ]
                )

                break

        if actual_field_name:

            resolved_fields.append(
                {
                    "display_name":
                        config[
                            "display_name"
                        ],

                    "field_name":
                        actual_field_name,
                }
            )

    return resolved_fields


project_status_checkbox_fields = (
    resolve_project_status_checkboxes(
        checkbox_fields
    )
)


# =========================================================
# FORECAST FIELD CONFIGURATION
# =========================================================

FORECAST_PROJECT_PROPERTY = None


for possible_name in [
    "Projects",
    "Project",
]:

    if (
        get_property_type(
            forecast_schema,
            possible_name,
        )
        == "relation"
    ):

        FORECAST_PROJECT_PROPERTY = (
            possible_name
        )

        break


if not FORECAST_PROJECT_PROPERTY:

    for (
        property_name,
        property_data,
    ) in (
        forecast_schema
        .get(
            "properties",
            {},
        )
        .items()
    ):

        if (
            property_data.get(
                "type"
            )
            == "relation"
        ):

            FORECAST_PROJECT_PROPERTY = (
                property_name
            )

            break


if not FORECAST_PROJECT_PROPERTY:

    st.error(
        "The Forecast table does not contain "
        "a Project relation field."
    )

    st.stop()


FORECAST_TYPE_OPTIONS = (
    get_select_options(
        forecast_schema,
        "Type of Event",
    )
)


# =========================================================
# LOAD PROJECTS
# =========================================================

try:

    projects = (
        load_projects(
            logged_user_name,
            logged_user_role,
        )
    )


except Exception as error:

    st.error(
        "Unable to retrieve Projects."
    )

    with st.expander(
        "Technical details"
    ):

        st.code(
            str(error)
        )


    st.stop()


if not projects:

    st.info(
        "No projects are available "
        "for the current user."
    )

    st.stop()


# =========================================================
# BUILD PROJECT LOOKUP
# =========================================================

project_lookup = {}


for project in projects:

    properties = (
        project.get(
            "properties",
            {},
        )
    )


    number = get_title(
        properties,
        "Number",
    )


    name = get_text(
        properties,
        "Project Name",
    )


    designer_name = get_select(
        properties,
        "Designer",
    )


    label = (
        f"{number} - {name}"
    )


    project_lookup[
        label
    ] = project


# =========================================================
# PROJECT SELECTION
# =========================================================

st.subheader(
    "Select Project"
)


selected_label = (
    st.selectbox(
        "Project",
        options=list(
            project_lookup.keys()
        ),
        index=None,
        placeholder=
            "Select a project to edit",
    )
)


if not selected_label:

    st.info(
        "Select a project above to load "
        "its information and schedule."
    )

    st.stop()


selected_project = (
    project_lookup[
        selected_label
    ]
)


project_page_id = (
    selected_project[
        "id"
    ]
)


current_properties = (
    selected_project.get(
        "properties",
        {},
    )
)


# =========================================================
# CURRENT PROJECT VALUES
# =========================================================

current_number = (
    get_title(
        current_properties,
        "Number",
    )
)


current_name = (
    get_text(
        current_properties,
        "Project Name",
    )
)


current_designer = (
    get_select(
        current_properties,
        "Designer",
    )
)


current_planned_hours = (
    get_number(
        current_properties,
        "Planned Hours",
    )
)


current_used_hours = (
    get_number(
        current_properties,
        "Used Hours",
    )
)


current_remaining_hours = (
    get_number(
        current_properties,
        "Remaining Hours",
    )
)


current_used_hours_percent = (
    get_number(
        current_properties,
        "Used Hours (%)",
    )
)


current_place = (
    get_text(
        current_properties,
        "Place",
    )
)


# =========================================================
# SECTION 1
# PROJECT INFORMATION
# =========================================================

st.divider()


st.subheader(
    "Project Information"
)


col1, col2 = (
    st.columns(2)
)


with col1:

    project_number = (
        st.text_input(
            "Project Number *",
            value=
                current_number,
        )
    )


with col2:

    project_name = (
        st.text_input(
            "Project Name *",
            value=
                current_name,
        )
    )


# =========================================================
# DESIGNER / PLANNED HOURS
# =========================================================

col1, col2 = (
    st.columns(2)
)


with col1:

    if (
        logged_user_role
        == "Manager"
    ):

        available_designers = (
            designer_options.copy()
        )


        if (
            current_designer
            and current_designer
            not in available_designers
        ):

            available_designers.append(
                current_designer
            )


        if available_designers:

            try:

                designer_index = (
                    available_designers.index(
                        current_designer
                    )
                )

            except ValueError:

                designer_index = 0


            designer = (
                st.selectbox(
                    "Designer",
                    options=
                        available_designers,
                    index=
                        designer_index,
                )
            )


        else:

            designer = (
                st.text_input(
                    "Designer",
                    value=
                        current_designer,
                )
            )


    else:

        designer = (
            current_designer
            or logged_user_name
        )


        st.text_input(
            "Designer",
            value=
                designer,
            disabled=True,
        )


with col2:

    planned_hours = (
        st.number_input(
            "Planned Hours",
            min_value=0.0,
            step=1.0,
            value=
                current_planned_hours,
        )
    )


# =========================================================
# HOURS
# =========================================================

col1, col2, col3 = (
    st.columns(3)
)


with col1:

    used_hours = (
        st.number_input(
            "Used Hours",
            min_value=0.0,
            step=0.5,
            value=
                current_used_hours,
        )
    )


with col2:

    remaining_hours = (
        st.number_input(
            "Remaining Hours",
            min_value=0.0,
            step=0.5,
            value=
                current_remaining_hours,
        )
    )


with col3:

    used_hours_percent = (
        st.number_input(
            "Used Hours (%)",
            min_value=0.0,
            max_value=100.0,
            step=1.0,
            value=
                current_used_hours_percent,
        )
    )


# =========================================================
# ADDRESS
# =========================================================

st.divider()


st.subheader(
    "Project Address"
)


place = (
    st.text_input(
        "Place",
        value=
            current_place,
        placeholder=(
            "Example: 699 Aero Lane, "
            "Sanford, FL 32771"
        ),
    )
)


# =========================================================
# MAP
# =========================================================

if place.strip():

    encoded_address = quote(
        place.strip()
    )


    map_url = (
        "https://www.google.com/maps?"
        f"q={encoded_address}"
        "&output=embed"
    )


    components.html(
        f"""
        <iframe
            width="100%"
            height="420"
            style="
                border:0;
                border-radius:8px;
            "
            loading="lazy"
            allowfullscreen
            referrerpolicy="no-referrer-when-downgrade"
            src="{map_url}">
        </iframe>
        """,
        height=430,
    )


# =========================================================
# PROJECT PHOTO
# =========================================================

st.divider()


st.subheader(
    "Project Photo"
)


st.caption(
    "Leave this field empty to keep "
    "the current project photo."
)


project_photo = (
    st.file_uploader(
        "Upload New Project Photo",
        type=[
            "png"
        ],
        accept_multiple_files=False,
        help=
            "PNG files only.",
    )
)


if project_photo is not None:

    st.image(
        project_photo,
        caption=
            "New Project Photo Preview",
        width=500,
    )


# =========================================================
# PROJECT STATUS CHECKBOXES
# =========================================================

checkbox_values = {}


if project_status_checkbox_fields:

    st.divider()


    st.subheader(
        "Project Status"
    )


    st.caption(
        "Update the project status fields below."
    )


    checkbox_columns = (
        st.columns(2)
    )


    for (
        index,
        checkbox_config,
    ) in enumerate(
        project_status_checkbox_fields
    ):

        display_name = (
            checkbox_config[
                "display_name"
            ]
        )

        field_name = (
            checkbox_config[
                "field_name"
            ]
        )

        current_value = (
            get_checkbox(
                current_properties,
                field_name,
                False,
            )
        )


        with checkbox_columns[
            index % 2
        ]:

            checkbox_values[
                field_name
            ] = st.checkbox(
                display_name,
                value=
                    current_value,
                key=(
                    f"project_checkbox_"
                    f"{project_page_id}_"
                    f"{field_name}"
                ),
            )


# =========================================================
# UPDATE PROJECT BUTTON
# =========================================================

st.divider()


update_project_button = (
    st.button(
        "💾 Update Project",
        type="primary",
        use_container_width=True,
    )
)


# =========================================================
# UPDATE PROJECT
# =========================================================

if update_project_button:

    errors = []


    if not project_number.strip():

        errors.append(
            "Project Number is required."
        )


    if not project_name.strip():

        errors.append(
            "Project Name is required."
        )


    if not designer:

        errors.append(
            "Designer is required."
        )


    if errors:

        for error in errors:

            st.error(
                error
            )


    else:

        properties = {

            "Number": {

                "title": [
                    {
                        "type":
                            "text",

                        "text": {
                            "content":
                                project_number.strip()
                        }
                    }
                ]
            },

            "Project Name": {

                "rich_text": [
                    {
                        "type":
                            "text",

                        "text": {
                            "content":
                                project_name.strip()
                        }
                    }
                ]
            },

            "Designer": {

                "select": {
                    "name":
                        designer
                }
            },

            "Planned Hours": {

                "number":
                    planned_hours
            },

            "Used Hours": {

                "number":
                    used_hours
            },

            "Remaining Hours": {

                "number":
                    remaining_hours
            },

            "Used Hours (%)": {

                "number":
                    used_hours_percent
            },

            "Place": {

                "rich_text": [
                    {
                        "type":
                            "text",

                        "text": {
                            "content":
                                place.strip()
                        }
                    }
                ]
            },
        }


        # -------------------------------------------------
        # CHECKBOXES
        # -------------------------------------------------

        for (
            field_name,
            value,
        ) in checkbox_values.items():

            properties[
                field_name
            ] = {

                "checkbox":
                    value
            }


        # -------------------------------------------------
        # PHOTO
        # -------------------------------------------------

        if (
            project_photo
            is not None
        ):

            try:

                with st.spinner(
                    "Uploading project photo..."
                ):

                    project_photo_id = (
                        upload_png(
                            project_photo
                        )
                    )


                properties[
                    "Project Photo"
                ] = {

                    "files": [
                        {
                            "type":
                                "file_upload",

                            "file_upload": {
                                "id":
                                    project_photo_id
                            },

                            "name":
                                project_photo.name
                        }
                    ]
                }


            except Exception as error:

                st.error(
                    "The project photo could not be uploaded."
                )

                with st.expander(
                    "Technical details"
                ):

                    st.code(
                        str(error)
                    )

                st.stop()


        # -------------------------------------------------
        # UPDATE PROJECT
        # -------------------------------------------------

        update_url = (
            "https://api.notion.com/v1/pages/"
            f"{project_page_id}"
        )


        try:

            with st.spinner(
                "Updating project..."
            ):

                response = requests.patch(
                    update_url,
                    headers=HEADERS,
                    json={
                        "properties":
                            properties
                    },
                    timeout=30,
                )


        except requests.RequestException as error:

            st.error(
                "Unable to update the project."
            )

            with st.expander(
                "Technical details"
            ):

                st.code(
                    str(error)
                )


        else:

            if (
                response.status_code
                == 200
            ):

                st.success(
                    f"Project {project_number.strip()} "
                    "updated successfully!"
                )


                st.cache_data.clear()


            else:

                st.error(
                    "The project could not be updated."
                )

                with st.expander(
                    "Technical details"
                ):

                    st.code(
                        response.text
                    )


# =========================================================
# FORECAST HELPERS
# =========================================================

def build_select_property(
    schema,
    property_name,
    value,
):

    if not value:
        return None


    property_type = (
        get_property_type(
            schema,
            property_name,
        )
    )


    if property_type == "select":

        return {

            "select": {
                "name":
                    value
            }
        }


    if property_type == "status":

        return {

            "status": {
                "name":
                    value
            }
        }


    if property_type == "rich_text":

        return {

            "rich_text": [
                {
                    "text": {
                        "content":
                            value
                    }
                }
            ]
        }


    if property_type == "title":

        return {

            "title": [
                {
                    "text": {
                        "content":
                            value
                    }
                }
            ]
        }


    return None


def build_forecast_designer_property(
    designer_name,
):

    if not designer_name:

        return None


    if (
        "Designer"
        not in forecast_schema.get(
            "properties",
            {},
        )
    ):

        return None


    return (
        build_select_property(
            forecast_schema,
            "Designer",
            designer_name,
        )
    )


# =========================================================
# LOAD FORECAST EVENTS FOR SELECTED PROJECT
# =========================================================

@st.cache_data(
    ttl=60,
    show_spinner=False,
)
def load_project_forecast_events(
    selected_project_page_id,
):

    records = []

    payload = {

        "page_size":
            100,

        "filter": {

            "property":
                FORECAST_PROJECT_PROPERTY,

            "relation": {

                "contains":
                    selected_project_page_id
            }
        }
    }


    next_cursor = None


    while True:

        current_payload = (
            payload.copy()
        )


        if next_cursor:

            current_payload[
                "start_cursor"
            ] = next_cursor


        response = requests.post(
            FORECAST_QUERY_URL,
            headers=HEADERS,
            json=current_payload,
            timeout=30,
        )


        if response.status_code != 200:

            safe_request_error(
                response,
                "Unable to retrieve Forecast events.",
            )


        data = (
            response.json()
        )


        records.extend(
            data.get(
                "results",
                [],
            )
        )


        if not data.get(
            "has_more"
        ):
            break


        next_cursor = (
            data.get(
                "next_cursor"
            )
        )


        if not next_cursor:
            break


    return records


# =========================================================
# FORECAST EVENT DISPLAY NAME
# =========================================================

def get_forecast_event_label(
    event,
):

    properties = (
        event.get(
            "properties",
            {},
        )
    )


    building = (
        get_property_plain_text(
            properties.get(
                "Building",
                {},
            )
        )
    )


    event_type = (
        get_property_plain_text(
            properties.get(
                "Type of Event",
                {},
            )
        )
    )


    event_date = (
        get_date_value(
            properties,
            "Date of event",
        )
    )


    parts = []


    if event_date:

        parts.append(
            event_date.strftime(
                "%m/%d/%Y"
            )
        )


    if building:

        parts.append(
            building
        )


    if event_type:

        parts.append(
            event_type
        )


    if not parts:

        return (
            "Forecast Event"
        )


    return " | ".join(
        parts
    )


# =========================================================
# SECTION 2
# ADD FORECAST EVENT
# =========================================================

st.divider()


st.subheader(
    "📅 Add Forecast Event"
)


st.caption(
    f"Add a schedule event for Project "
    f"{current_number} - {current_name}."
)


with st.form(
    "add_forecast_event_form",
    clear_on_submit=True,
):

    forecast_col1, forecast_col2 = (
        st.columns(2)
    )


    with forecast_col1:

        new_forecast_building = (
            st.text_input(
                "Building / System",
                placeholder=(
                    "Example: Building 100 or Total"
                ),
                key=
                    "new_forecast_building",
            )
        )


    with forecast_col2:

        if FORECAST_TYPE_OPTIONS:

            new_forecast_type = (
                st.selectbox(
                    "Type of Event",
                    options=
                        FORECAST_TYPE_OPTIONS,
                    index=None,
                    placeholder=
                        "Select event type...",
                    key=
                        "new_forecast_type",
                )
            )

        else:

            new_forecast_type = (
                st.text_input(
                    "Type of Event",
                    key=
                        "new_forecast_type_text",
                )
            )


    forecast_col3, forecast_col4 = (
        st.columns(2)
    )


    with forecast_col3:

        new_forecast_date = (
            st.date_input(
                "Date of Event",
                value=
                    date.today(),
                key=
                    "new_forecast_date",
            )
        )


    with forecast_col4:

        new_forecast_done = (
            st.checkbox(
                "Done",
                value=False,
                key=
                    "new_forecast_done",
            )
        )


    st.write("")


    add_forecast_button = (
        st.form_submit_button(
            "➕ Add Forecast Event",
            type="primary",
            use_container_width=True,
        )
    )


# =========================================================
# CREATE FORECAST EVENT
# =========================================================

if add_forecast_button:

    forecast_errors = []


    if not new_forecast_building.strip():

        forecast_errors.append(
            "Building / System is required."
        )


    if not new_forecast_type:

        forecast_errors.append(
            "Type of Event is required."
        )


    if forecast_errors:

        for error in forecast_errors:

            st.error(
                error
            )


    else:

        forecast_properties = {

            FORECAST_PROJECT_PROPERTY: {

                "relation": [
                    {
                        "id":
                            project_page_id
                    }
                ]
            },

            "Date of event": {

                "date": {
                    "start":
                        new_forecast_date.isoformat()
                }
            },

            "Done": {

                "checkbox":
                    new_forecast_done
            },
        }


        # -------------------------------------------------
        # BUILDING
        # -------------------------------------------------

        building_property = (
            build_select_property(
                forecast_schema,
                "Building",
                new_forecast_building.strip(),
            )
        )


        if building_property:

            forecast_properties[
                "Building"
            ] = building_property


        # -------------------------------------------------
        # TYPE OF EVENT
        # -------------------------------------------------

        type_property = (
            build_select_property(
                forecast_schema,
                "Type of Event",
                new_forecast_type,
            )
        )


        if type_property:

            forecast_properties[
                "Type of Event"
            ] = type_property


        # -------------------------------------------------
        # DESIGNER
        # -------------------------------------------------

        designer_property = (
            build_forecast_designer_property(
                designer
            )
        )


        if designer_property:

            forecast_properties[
                "Designer"
            ] = designer_property


        # -------------------------------------------------
        # CREATE PAGE
        # -------------------------------------------------

        payload = {

            "parent": {

                "type":
                    "data_source_id",

                "data_source_id":
                    FORECAST_DATA_SOURCE_ID,
            },

            "properties":
                forecast_properties,
        }


        try:

            with st.spinner(
                "Adding Forecast event..."
            ):

                response = requests.post(
                    "https://api.notion.com/v1/pages",
                    headers=HEADERS,
                    json=payload,
                    timeout=30,
                )


        except requests.RequestException as error:

            st.error(
                "Unable to add the Forecast event."
            )

            with st.expander(
                "Technical details"
            ):

                st.code(
                    str(error)
                )


        else:

            if response.status_code in [
                200,
                201,
            ]:

                st.success(
                    "Forecast event added successfully!"
                )


                st.cache_data.clear()

                st.rerun()


            else:

                st.error(
                    "The Forecast event could not be added."
                )

                with st.expander(
                    "Technical details"
                ):

                    st.code(
                        response.text
                    )


# =========================================================
# SECTION 3
# UPDATE FORECAST EVENT
# =========================================================

st.divider()


st.subheader(
    "📝 Update Forecast Event"
)


st.caption(
    "Only Forecast events related to the "
    "selected Project are shown below."
)


# =========================================================
# LOAD RELATED EVENTS
# =========================================================

try:

    related_forecast_events = (
        load_project_forecast_events(
            project_page_id
        )
    )


except Exception as error:

    st.error(
        "Unable to load Forecast events "
        "for this Project."
    )

    with st.expander(
        "Technical details"
    ):

        st.code(
            str(error)
        )


    related_forecast_events = []


# =========================================================
# SHOW EXISTING EVENTS
# =========================================================

if not related_forecast_events:

    st.info(
        "There are no Forecast events "
        "registered for this Project."
    )


else:

    forecast_event_lookup = {}


    for index, event in enumerate(
        related_forecast_events,
        start=1,
    ):

        label = (
            get_forecast_event_label(
                event
            )
        )


        # Avoid duplicate selectbox labels
        unique_label = (
            f"{label} | #{index}"
        )


        forecast_event_lookup[
            unique_label
        ] = event


    selected_forecast_label = (
        st.selectbox(
            "Forecast Event",
            options=list(
                forecast_event_lookup.keys()
            ),
            index=None,
            placeholder=
                "Select an event to edit...",
            key=
                "forecast_event_to_update",
        )
    )


    if selected_forecast_label:

        selected_forecast_event = (
            forecast_event_lookup[
                selected_forecast_label
            ]
        )


        forecast_page_id = (
            selected_forecast_event[
                "id"
            ]
        )


        forecast_properties = (
            selected_forecast_event.get(
                "properties",
                {},
            )
        )


        current_forecast_building = (
            get_property_plain_text(
                forecast_properties.get(
                    "Building",
                    {},
                )
            )
        )


        current_forecast_type = (
            get_property_plain_text(
                forecast_properties.get(
                    "Type of Event",
                    {},
                )
            )
        )


        current_forecast_date = (
            get_date_value(
                forecast_properties,
                "Date of event",
            )
        )


        current_forecast_done = (
            get_checkbox(
                forecast_properties,
                "Done",
                False,
            )
        )


        # =================================================
        # CURRENT EVENT SUMMARY
        # =================================================

        current_event_data = [
            {
                "Project":
                    current_number,

                "Building / System":
                    current_forecast_building
                    or "—",

                "Type of Event":
                    current_forecast_type
                    or "—",

                "Date":
                    (
                        current_forecast_date.strftime(
                            "%m/%d/%Y"
                        )
                        if current_forecast_date
                        else ""
                    ),

                "Done":
                    (
                        "Yes"
                        if current_forecast_done
                        else "No"
                    ),
            }
        ]


        st.dataframe(
            current_event_data,
            use_container_width=True,
            hide_index=True,
        )


        # =================================================
        # EDIT EVENT FORM
        # =================================================

        with st.form(
            "update_forecast_event_form"
        ):

            edit_col1, edit_col2 = (
                st.columns(2)
            )


            with edit_col1:

                edit_forecast_building = (
                    st.text_input(
                        "Building / System",
                        value=
                            current_forecast_building,
                        placeholder=(
                            "Example: Building 100 or Total"
                        ),
                        key=
                            "edit_forecast_building",
                    )
                )


            with edit_col2:

                available_event_types = (
                    FORECAST_TYPE_OPTIONS.copy()
                )


                if (
                    current_forecast_type
                    and current_forecast_type
                    not in available_event_types
                ):

                    available_event_types.append(
                        current_forecast_type
                    )


                if available_event_types:

                    try:

                        event_type_index = (
                            available_event_types.index(
                                current_forecast_type
                            )
                        )

                    except ValueError:

                        event_type_index = 0


                    edit_forecast_type = (
                        st.selectbox(
                            "Type of Event",
                            options=
                                available_event_types,
                            index=
                                event_type_index,
                            key=
                                "edit_forecast_type",
                        )
                    )


                else:

                    edit_forecast_type = (
                        st.text_input(
                            "Type of Event",
                            value=
                                current_forecast_type,
                            key=
                                "edit_forecast_type_text",
                        )
                    )


            edit_col3, edit_col4 = (
                st.columns(2)
            )


            with edit_col3:

                edit_forecast_date = (
                    st.date_input(
                        "Date of Event",
                        value=(
                            current_forecast_date
                            or date.today()
                        ),
                        key=
                            "edit_forecast_date",
                    )
                )


            with edit_col4:

                edit_forecast_done = (
                    st.checkbox(
                        "Done",
                        value=
                            current_forecast_done,
                        key=
                            "edit_forecast_done",
                    )
                )


            st.write("")


            update_forecast_button = (
                st.form_submit_button(
                    "💾 Update Forecast Event",
                    type="primary",
                    use_container_width=True,
                )
            )


        # =================================================
        # UPDATE FORECAST EVENT
        # =================================================

        if update_forecast_button:

            update_errors = []


            if not edit_forecast_building.strip():

                update_errors.append(
                    "Building / System is required."
                )


            if not edit_forecast_type:

                update_errors.append(
                    "Type of Event is required."
                )


            if update_errors:

                for error in update_errors:

                    st.error(
                        error
                    )


            else:

                updated_properties = {

                    # -------------------------------------
                    # KEEP RELATION WITH SELECTED PROJECT
                    # -------------------------------------

                    FORECAST_PROJECT_PROPERTY: {

                        "relation": [
                            {
                                "id":
                                    project_page_id
                            }
                        ]
                    },

                    "Date of event": {

                        "date": {
                            "start":
                                edit_forecast_date.isoformat()
                        }
                    },

                    "Done": {

                        "checkbox":
                            edit_forecast_done
                    },
                }


                # -----------------------------------------
                # BUILDING
                # -----------------------------------------

                building_property = (
                    build_select_property(
                        forecast_schema,
                        "Building",
                        edit_forecast_building.strip(),
                    )
                )


                if building_property:

                    updated_properties[
                        "Building"
                    ] = building_property


                # -----------------------------------------
                # EVENT TYPE
                # -----------------------------------------

                type_property = (
                    build_select_property(
                        forecast_schema,
                        "Type of Event",
                        edit_forecast_type,
                    )
                )


                if type_property:

                    updated_properties[
                        "Type of Event"
                    ] = type_property


                # -----------------------------------------
                # DESIGNER
                # -----------------------------------------

                designer_property = (
                    build_forecast_designer_property(
                        designer
                    )
                )


                if designer_property:

                    updated_properties[
                        "Designer"
                    ] = designer_property


                # -----------------------------------------
                # UPDATE
                # -----------------------------------------

                update_forecast_url = (
                    "https://api.notion.com/v1/pages/"
                    f"{forecast_page_id}"
                )


                try:

                    with st.spinner(
                        "Updating Forecast event..."
                    ):

                        response = requests.patch(
                            update_forecast_url,
                            headers=HEADERS,
                            json={
                                "properties":
                                    updated_properties
                            },
                            timeout=30,
                        )


                except requests.RequestException as error:

                    st.error(
                        "Unable to update the Forecast event."
                    )

                    with st.expander(
                        "Technical details"
                    ):

                        st.code(
                            str(error)
                        )


                else:

                    if response.status_code == 200:

                        st.success(
                            "Forecast event updated successfully!"
                        )


                        st.cache_data.clear()

                        st.rerun()


                    else:

                        st.error(
                            "The Forecast event could not be updated."
                        )

                        with st.expander(
                            "Technical details"
                        ):

                            st.code(
                                response.text
                            )