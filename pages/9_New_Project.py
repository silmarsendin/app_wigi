import streamlit as st
import requests
import streamlit.components.v1 as components

from datetime import date
from urllib.parse import quote


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="New Project",
    page_icon="➕",
    layout="wide"
)


# =========================================================
# CHECK LOGIN
# =========================================================

if not st.session_state.get("authenticated", False):

    st.error(
        "You must be signed in to access this page."
    )

    st.stop()


logged_user_name = st.session_state.get(
    "user_name"
)

logged_user_email = st.session_state.get(
    "user_email"
)

logged_user_role = st.session_state.get(
    "user_role",
    "User"
)


if not logged_user_name:

    st.error(
        "Unable to identify the logged-in user."
    )

    st.stop()


# =========================================================
# PAGE HEADER
# =========================================================

st.title("➕ New Project")

st.caption(
    "Create a new project directly "
    "in the Notion Projects database"
)


# =========================================================
# NOTION CONFIGURATION
# =========================================================

NOTION_TOKEN = st.secrets[
    "NOTION_TOKEN"
]

PROJECTS_DATA_SOURCE_ID = st.secrets[
    "NOTION_PROJECTS_DATA_SOURCE_ID"
]


NOTION_VERSION = "2026-03-11"


HEADERS = {

    "Authorization":
        f"Bearer {NOTION_TOKEN}",

    "Notion-Version":
        NOTION_VERSION,

    "Content-Type":
        "application/json",
}


DATA_SOURCE_URL = (
    "https://api.notion.com/v1/data_sources/"
    f"{PROJECTS_DATA_SOURCE_ID}"
)


CREATE_PAGE_URL = (
    "https://api.notion.com/v1/pages"
)


# =========================================================
# LOAD DATA SOURCE SCHEMA
# =========================================================

@st.cache_data(ttl=300)
def get_projects_schema():

    response = requests.get(
        DATA_SOURCE_URL,
        headers=HEADERS,
        timeout=30
    )

    if response.status_code != 200:

        raise Exception(
            f"Notion API Error "
            f"{response.status_code}: "
            f"{response.text}"
        )

    return response.json()


# =========================================================
# UPLOAD PNG TO NOTION
# =========================================================

def upload_png_to_notion(
    uploaded_file
):

    # -----------------------------------------------------
    # STEP 1 - CREATE FILE UPLOAD
    # -----------------------------------------------------

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
        timeout=30
    )


    if response.status_code != 200:

        raise Exception(
            "Unable to initialize image upload: "
            f"{response.status_code} - "
            f"{response.text}"
        )


    upload_data = response.json()

    file_upload_id = (
        upload_data["id"]
    )


    # -----------------------------------------------------
    # STEP 2 - SEND PNG FILE
    # -----------------------------------------------------

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


    uploaded_file.seek(0)


    files = {

        "file": (
            uploaded_file.name,
            uploaded_file.getvalue(),
            "image/png"
        )
    }


    response = requests.post(
        send_url,
        headers=upload_headers,
        files=files,
        timeout=60
    )


    if response.status_code != 200:

        raise Exception(
            "Unable to upload image: "
            f"{response.status_code} - "
            f"{response.text}"
        )


    return file_upload_id


# =========================================================
# LOAD NOTION SCHEMA
# =========================================================

try:

    schema = get_projects_schema()

except Exception as error:

    st.error(
        "Unable to retrieve the "
        "Projects database structure."
    )

    st.code(
        str(error)
    )

    st.stop()


# =========================================================
# PROJECT INFORMATION
# =========================================================

st.subheader(
    "Project Information"
)


# ---------------------------------------------------------
# PROJECT NUMBER / PROJECT NAME
# ---------------------------------------------------------

col1, col2 = st.columns(2)


with col1:

    project_number = st.text_input(
        "Project Number *",
        placeholder="Example: 2011193"
    )


with col2:

    project_name = st.text_input(
        "Project Name *",
        placeholder="Example: Sand Lake Industrial"
    )


# ---------------------------------------------------------
# DESIGNER / PLANNED HOURS
# ---------------------------------------------------------

col1, col2 = st.columns(2)


with col1:

    designer = logged_user_name

    st.text_input(
        "Designer",
        value=designer,
        disabled=True,
        help=(
            "The designer is automatically "
            "assigned based on the logged-in user."
        )
    )


with col2:

    planned_hours = st.number_input(
        "Planned Hours",
        min_value=0.0,
        step=1.0,
        value=0.0
    )


# =========================================================
# PROJECT PHOTO
# =========================================================

st.markdown("---")

st.subheader(
    "Project Photo"
)


project_photo = st.file_uploader(
    "Upload Project Photo",
    type=["png"],
    accept_multiple_files=False,
    help="PNG files only."
)


if project_photo is not None:

    st.image(
        project_photo,
        caption="Project Photo Preview",
        width=500
    )


# =========================================================
# PROJECT ADDRESS
# =========================================================

st.markdown("---")

st.subheader(
    "Project Address"
)


place = st.text_input(
    "Place",
    placeholder=(
        "Example: 699 Aero Lane, "
        "Sanford, FL 32771"
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
        f"q={encoded_address}&output=embed"
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
        height=430
    )


else:

    st.info(
        "Enter the project address above "
        "to display it on the map."
    )


# =========================================================
# SCHEDULE
# =========================================================

st.markdown("---")

st.subheader(
    "Schedule"
)


col1, col2 = st.columns(2)


with col1:

    use_start_date = st.checkbox(
        "Set Start Date",
        value=True
    )


    start_date = st.date_input(
        "Start Date",
        value=date.today(),
        disabled=not use_start_date
    )


with col2:

    estimated_end_date = st.date_input(
        "Estimated End Date",
        value=date.today()
    )


# =========================================================
# CREATE PROJECT BUTTON
# =========================================================

st.markdown("---")


submitted = st.button(
    "Create Project",
    type="primary",
    use_container_width=True
)


# =========================================================
# CREATE PROJECT
# =========================================================

if submitted:

    # -----------------------------------------------------
    # VALIDATION
    # -----------------------------------------------------

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
            "Unable to identify the Designer."
        )


    if errors:

        for error in errors:

            st.error(
                error
            )

        st.stop()


    # -----------------------------------------------------
    # BUILD NOTION PROPERTIES
    # -----------------------------------------------------

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


        "Planned Hours": {

            "number":
                planned_hours
        },
    }


    # -----------------------------------------------------
    # DESIGNER
    # -----------------------------------------------------

    properties["Designer"] = {

        "select": {

            "name":
                designer
        }
    }


    # -----------------------------------------------------
    # PLACE
    # -----------------------------------------------------

    if place.strip():

        properties["Place"] = {

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
        }


    # -----------------------------------------------------
    # START DATE
    # -----------------------------------------------------

    if use_start_date:

        properties["Start Date"] = {

            "date": {

                "start":
                    start_date.isoformat()
            }
        }


    # -----------------------------------------------------
    # ESTIMATED END DATE
    # -----------------------------------------------------

    properties["End Date"] = {

        "date": {

            "start":
                estimated_end_date.isoformat()
        }
    }


    # -----------------------------------------------------
    # UPLOAD PROJECT PHOTO
    # -----------------------------------------------------

    if project_photo is not None:

        try:

            with st.spinner(
                "Uploading project photo..."
            ):

                project_photo_id = (
                    upload_png_to_notion(
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
                "The project photo "
                "could not be uploaded."
            )

            st.code(
                str(error)
            )

            st.stop()


    # -----------------------------------------------------
    # CREATE PAGE PAYLOAD
    # -----------------------------------------------------

    payload = {

        "parent": {

            "type":
                "data_source_id",

            "data_source_id":
                PROJECTS_DATA_SOURCE_ID
        },

        "properties":
            properties
    }


    # -----------------------------------------------------
    # SEND TO NOTION
    # -----------------------------------------------------

    with st.spinner(
        "Creating project in Notion..."
    ):

        try:

            response = requests.post(
                CREATE_PAGE_URL,
                headers=HEADERS,
                json=payload,
                timeout=30
            )

        except requests.RequestException as error:

            st.error(
                "Unable to connect to Notion."
            )

            st.code(
                str(error)
            )

            st.stop()


    # -----------------------------------------------------
    # RESULT
    # -----------------------------------------------------

    if response.status_code in [
        200,
        201
    ]:

        new_page = response.json()


        st.success(
            f"Project {project_number} "
            "created successfully!"
        )


        st.info(
            f"Designer assigned: {designer}"
        )


        notion_url = (
            new_page.get(
                "url"
            )
        )


        if notion_url:

            st.link_button(
                "Open Project in Notion",
                notion_url
            )


        st.cache_data.clear()


    else:

        st.error(
            "The project could not be "
            "created in Notion."
        )

        st.write(
            f"Status Code: "
            f"{response.status_code}"
        )

        st.code(
            response.text
        )