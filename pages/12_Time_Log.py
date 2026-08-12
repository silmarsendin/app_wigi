# ============================================================
# 12_Time_Log.py
# WIGINTON TOOLS
# ============================================================

import streamlit as st
import requests
import time
import io

from datetime import datetime, timedelta

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, KeepTogether
from reportlab.pdfgen import canvas
from zoneinfo import ZoneInfo

from utils.layout import show_sidebar_branding


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Time Log",
    page_icon="⏱️",
    layout="wide"
)


# ============================================================
# SIDEBAR
# ============================================================

show_sidebar_branding()


# ============================================================
# AUTHENTICATION CHECK
# ============================================================

if not st.session_state.get(
    "authenticated",
    False
):

    st.warning(
        "Please log in to access this page."
    )

    st.stop()


# ============================================================
# NOTION CONFIGURATION
# ============================================================

NOTION_TOKEN = st.secrets[
    "NOTION_TOKEN"
]


PROJECTS_DATA_SOURCE_ID = st.secrets[
    "NOTION_PROJECTS_DATA_SOURCE_ID"
]


TIME_LOG_DATA_SOURCE_ID = (
    "3245f88d-03b8-8030-9382-000b086a3ef8"
)


NOTION_VERSION = "2026-03-11"


NOTION_HEADERS = {

    "Authorization":
        f"Bearer {NOTION_TOKEN}",

    "Notion-Version":
        NOTION_VERSION,

    "Content-Type":
        "application/json",
}


TIMEZONE = ZoneInfo(
    "America/New_York"
)


# ============================================================
# SESSION STATE
# ============================================================

DEFAULT_SESSION_VALUES = {

    "time_log_running":
        False,

    "time_log_start":
        None,

    "time_log_project_id":
        None,

    "time_log_project_label":
        None,

    "time_log_task":
        "",

    "time_log_last_end":
        None,

    "time_log_last_hours":
        None,

    # Last Time Log record created.
    "time_log_last_page_id":
        None,

    "time_log_last_project_id":
        None,

    "time_log_last_task":
        "",

    "time_log_last_start":
        None,

    # Hours currently represented by the last Time Log record.
    # This is needed so edited times can update Project hours
    # using only the difference.
    "time_log_last_recorded_hours":
        None,

    # Last confirmed Project hour values written by this page.
    # Used to keep the UI immediately synchronized after a write.
    "time_log_last_project_values":
        None,
}


for key, default_value in (
    DEFAULT_SESSION_VALUES.items()
):

    if key not in st.session_state:

        st.session_state[
            key
        ] = default_value


# ============================================================
# NOTION PROPERTY HELPERS
# ============================================================

def safe_title(
    prop
):

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
    )


def safe_rich_text(
    prop
):

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
    )


def safe_number(
    prop,
    default=0.0
):

    if not prop:
        return default

    value = prop.get(
        "number"
    )

    if value is None:
        return default

    try:

        return float(
            value
        )

    except Exception:

        return default


def safe_select(
    prop
):

    if not prop:
        return ""

    selected = prop.get(
        "select"
    )

    if not selected:
        return ""

    return selected.get(
        "name",
        ""
    )


def property_text(
    prop
):

    if not prop:
        return ""

    prop_type = prop.get(
        "type"
    )


    if prop_type == "title":

        return safe_title(
            prop
        )


    if prop_type == "rich_text":

        return safe_rich_text(
            prop
        )


    if prop_type == "select":

        return safe_select(
            prop
        )


    if prop_type == "status":

        value = prop.get(
            "status"
        )

        if value:

            return value.get(
                "name",
                ""
            )


    if prop_type == "email":

        return (
            prop.get(
                "email",
                ""
            )
            or ""
        )


    if prop_type == "people":

        people = prop.get(
            "people",
            []
        )

        if people:

            return people[0].get(
                "name",
                ""
            )


    if prop_type == "number":

        value = prop.get(
            "number"
        )

        if value is not None:

            return str(
                value
            )


    return ""


# ============================================================
# QUERY NOTION DATA SOURCE
# ============================================================

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
                timeout=30
            )


        except requests.RequestException as error:

            st.error(
                "Unable to connect to the database."
            )

            st.code(
                str(error)
            )

            return []


        if response.status_code != 200:

            st.error(
                f"Database API Error: "
                f"{response.status_code}"
            )

            st.code(
                response.text
            )

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


# ============================================================
# GET NOTION PAGE
# ============================================================

def get_notion_page(
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
            timeout=30
        )


    except requests.RequestException as error:

        st.error(
            "Unable to connect to the database."
        )

        st.code(
            str(error)
        )

        return None


    if response.status_code != 200:

        st.error(
            f"Unable to load record. "
            f"API Error "
            f"{response.status_code}"
        )

        st.code(
            response.text
        )

        return None


    return response.json()


# ============================================================
# UPDATE NOTION PAGE
# ============================================================

def update_notion_page(
    page_id,
    properties,
    error_label="record"
):

    url = (
        "https://api.notion.com/v1/pages/"
        f"{page_id}"
    )


    payload = {

        "properties":
            properties
    }


    try:

        response = requests.patch(
            url,
            headers=NOTION_HEADERS,
            json=payload,
            timeout=30
        )


    except requests.RequestException as error:

        st.error(
            "Unable to connect to the database."
        )

        st.code(
            str(error)
        )

        return False


    if response.status_code != 200:

        st.error(
            f"Unable to update {error_label}. "
            f"API Error "
            f"{response.status_code}"
        )

        st.code(
            response.text
        )

        return False


    return True


# ============================================================
# CREATE TIME LOG PAGE
# ============================================================

def create_time_log_page(
    project_id,
    task,
    start_time,
    end_time
):

    url = (
        "https://api.notion.com/v1/pages"
    )


    properties = {

        "Task": {

            "title": [

                {

                    "type":
                        "text",

                    "text": {

                        "content":
                            task
                    }
                }
            ]
        },


        "Project": {

            "relation": [

                {

                    "id":
                        project_id
                }
            ]
        },


        "Start Time": {

            "date": {

                "start":
                    start_time.isoformat()
            }
        },


        "End Time": {

            "date": {

                "start":
                    end_time.isoformat()
            }
        }
    }


    payload = {

        "parent": {

            "type":
                "data_source_id",

            "data_source_id":
                TIME_LOG_DATA_SOURCE_ID
        },

        "properties":
            properties
    }


    try:

        response = requests.post(
            url,
            headers=NOTION_HEADERS,
            json=payload,
            timeout=30
        )


    except requests.RequestException as error:

        st.error(
            "Unable to connect to the database."
        )

        st.code(
            str(error)
        )

        return None


    if response.status_code not in [
        200,
        201
    ]:

        st.error(
            "Unable to create the "
            "Time Log record."
        )

        st.code(
            response.text
        )

        return None


    return response.json().get(
        "id"
    )


# ============================================================
# UPDATE TIME LOG TIMES
# ============================================================

def update_time_log_times(
    time_log_page_id,
    start_time,
    end_time
):

    return update_notion_page(
        time_log_page_id,
        {

            "Start Time": {

                "date": {

                    "start":
                        start_time.isoformat()
                }
            },

            "End Time": {

                "date": {

                    "start":
                        end_time.isoformat()
                }
            }
        },
        error_label=
            "Time Log"
    )


# ============================================================
# GET LOGGED USER
# ============================================================

def get_logged_user():

    user_name = (
        st.session_state.get(
            "user_name"
        )
    )


    if user_name:

        return str(
            user_name
        ).strip()


    return ""


# ============================================================
# BUILD PROJECT OBJECT FROM NOTION PAGE
# ============================================================

def build_project_object(
    page
):

    if not page:
        return None


    properties = page.get(
        "properties",
        {}
    )


    designer = property_text(
        properties.get(
            "Designer",
            {}
        )
    )


    project_number = property_text(
        properties.get(
            "Number",
            {}
        )
    )


    if not project_number:

        project_number = property_text(
            properties.get(
                "Project Number",
                {}
            )
        )


    project_name = property_text(
        properties.get(
            "Project Name",
            {}
        )
    )


    planned_hours = safe_number(
        properties.get(
            "Planned Hours",
            {}
        ),
        0.0
    )


    # Hours Used Total is the numeric cumulative field in Projects.
    used_hours = safe_number(
        properties.get(
            "Hours Used Total",
            {}
        ),
        0.0
    )


    # These are recalculated from Planned and Used so the UI
    # stays consistent even if old records contain stale values.
    remaining_hours = (
        planned_hours
        -
        used_hours
    )


    if remaining_hours < 0:

        remaining_hours = 0.0


    used_percent = (

        used_hours
        /
        planned_hours
        *
        100

        if planned_hours > 0

        else 0.0
    )


    return {

        "id":
            page.get(
                "id"
            ),

        "project_number":
            project_number,

        "project_name":
            project_name,

        "designer":
            designer,

        "planned_hours":
            planned_hours,

        "used_hours":
            used_hours,

        "remaining_hours":
            remaining_hours,

        "used_percent":
            used_percent,
    }


# ============================================================
# LOAD PROJECTS FOR DESIGNER
# ============================================================

def load_projects_for_designer(
    designer_name
):

    pages = query_data_source(
        PROJECTS_DATA_SOURCE_ID
    )


    projects = []


    for page in pages:

        project = build_project_object(
            page
        )


        if not project:

            continue


        if (
            project[
                "designer"
            ]
            .strip()
            .lower()
            !=
            designer_name
            .strip()
            .lower()
        ):

            continue


        projects.append(
            project
        )


    projects.sort(

        key=lambda project: (

            project[
                "project_number"
            ],

            project[
                "project_name"
            ]
        )
    )


    return projects


# ============================================================
# GET CURRENT PROJECT VALUES DIRECTLY FROM DATABASE
# ============================================================

def get_current_project(
    project_id
):

    page = get_notion_page(
        project_id
    )


    if not page:

        return None


    return build_project_object(
        page
    )


# ============================================================
# UPDATE PROJECT HOURS BY DELTA
# ============================================================

def update_project_hours_by_delta(
    project_id,
    hours_delta
):

    # --------------------------------------------------------
    # READ CURRENT VALUES DIRECTLY FROM PROJECT
    # --------------------------------------------------------

    current_project = (
        get_current_project(
            project_id
        )
    )


    if not current_project:

        return None


    planned_hours = (
        current_project[
            "planned_hours"
        ]
    )


    current_used_hours = (
        current_project[
            "used_hours"
        ]
    )


    # --------------------------------------------------------
    # CALCULATE NEW VALUES
    # --------------------------------------------------------

    new_used_hours = (

        current_used_hours
        +
        hours_delta
    )


    if new_used_hours < 0:

        new_used_hours = 0.0


    remaining_hours = (

        planned_hours
        -
        new_used_hours
    )


    if remaining_hours < 0:

        remaining_hours = 0.0


    used_percent = (

        new_used_hours
        /
        planned_hours
        *
        100

        if planned_hours > 0

        else 0.0
    )


    # --------------------------------------------------------
    # UPDATE PROJECT
    # --------------------------------------------------------

    properties = {

        "Hours Used Total": {

            "number":
                round(
                    new_used_hours,
                    4
                )
        },


        "Remaining Hours": {

            "number":
                round(
                    remaining_hours,
                    4
                )
        },


        "Used Hours (%)": {

            "number":
                round(
                    used_percent,
                    4
                )
        }
    }


    success = update_notion_page(
        project_id,
        properties,
        error_label=
            "Project Hours"
    )


    if not success:

        return None


    # --------------------------------------------------------
    # VERIFY THE VALUES WERE ACTUALLY WRITTEN
    # --------------------------------------------------------
    #
    # The data service can take a short moment before a GET
    # reflects a PATCH. Retry briefly so the UI does not reload
    # with the previous values.
    # --------------------------------------------------------

    verified_project = None


    for _ in range(4):

        time.sleep(
            0.35
        )


        refreshed_project = (
            get_current_project(
                project_id
            )
        )


        if not refreshed_project:

            continue


        if abs(
            refreshed_project[
                "used_hours"
            ]
            -
            new_used_hours
        ) < 0.01:

            verified_project = (
                refreshed_project
            )

            break


    # --------------------------------------------------------
    # RETURN THE VALUES WE JUST WROTE
    # --------------------------------------------------------

    result = {

        "used_hours":
            new_used_hours,

        "remaining_hours":
            remaining_hours,

        "used_percent":
            used_percent,

        "planned_hours":
            planned_hours,

        "verified":
            verified_project
            is not None,
    }


    if verified_project:

        result[
            "used_hours"
        ] = verified_project[
            "used_hours"
        ]

        result[
            "remaining_hours"
        ] = verified_project[
            "remaining_hours"
        ]

        result[
            "used_percent"
        ] = verified_project[
            "used_percent"
        ]

        result[
            "planned_hours"
        ] = verified_project[
            "planned_hours"
        ]


    return result


# ============================================================
# DATETIME EDITOR HELPER
# ============================================================

def combine_date_and_time(
    selected_date,
    selected_time
):

    return datetime.combine(
        selected_date,
        selected_time,
        tzinfo=TIMEZONE
    )


# ============================================================
# TIME LOG HISTORY / REPORT HELPERS
# ============================================================

def get_time_log_relation_ids(
    properties
):

    for property_name in [
        "Project",
        "Projects",
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

            return {
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

    return set()


def get_time_log_datetime(
    properties,
    property_name
):

    prop = properties.get(
        property_name,
        {}
    )

    date_data = prop.get(
        "date"
    )

    if not date_data:
        return None

    value = date_data.get(
        "start"
    )

    if not value:
        return None

    try:

        parsed = datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00"
            )
        )

        if parsed.tzinfo is None:

            parsed = parsed.replace(
                tzinfo=TIMEZONE
            )

        else:

            parsed = parsed.astimezone(
                TIMEZONE
            )

        return parsed

    except Exception:

        return None


def build_time_log_record(
    page,
    project_lookup=None
):

    properties = page.get(
        "properties",
        {}
    )

    start_time = (
        get_time_log_datetime(
            properties,
            "Start Time"
        )
    )

    end_time = (
        get_time_log_datetime(
            properties,
            "End Time"
        )
    )

    worked_hours = 0.0

    if (
        start_time
        and end_time
        and end_time > start_time
    ):

        worked_hours = (
            end_time
            -
            start_time
        ).total_seconds() / 3600


    relation_ids = (
        get_time_log_relation_ids(
            properties
        )
    )


    project_id = None

    if relation_ids:

        project_id = next(
            iter(
                relation_ids
            )
        )


    project_label = ""

    if (
        project_lookup
        and project_id
        and project_id in project_lookup
    ):

        project = project_lookup[
            project_id
        ]

        number = (
            project.get(
                "project_number"
            )
            or ""
        )

        name = (
            project.get(
                "project_name"
            )
            or ""
        )

        if number and name:

            project_label = (
                f"{number} - {name}"
            )

        else:

            project_label = (
                number
                or name
            )


    return {

        "page_id":
            page.get(
                "id"
            ),

        "project_id":
            project_id,

        "project":
            project_label,

        "task":
            property_text(
                properties.get(
                    "Task",
                    {}
                )
            ),

        "start":
            start_time,

        "end":
            end_time,

        "hours":
            worked_hours,
    }


def load_time_logs_for_project(
    project_id
):

    payload = {

        "page_size":
            100,

        "filter": {

            "property":
                "Project",

            "relation": {

                "contains":
                    project_id
            }
        },

        "sorts": [

            {

                "property":
                    "Start Time",

                "direction":
                    "descending"
            }
        ]
    }


    pages = query_data_source(
        TIME_LOG_DATA_SOURCE_ID,
        payload
    )


    records = []


    for page in pages:

        record = (
            build_time_log_record(
                page
            )
        )


        if record[
            "project_id"
        ] != project_id:

            continue


        records.append(
            record
        )


    records.sort(
        key=lambda record:
            record[
                "start"
            ]
            or datetime.min.replace(
                tzinfo=TIMEZONE
            ),
        reverse=True
    )


    return records


def get_previous_week_range():

    today = datetime.now(
        TIMEZONE
    ).date()


    current_week_monday = (
        today
        -
        timedelta(
            days=today.weekday()
        )
    )


    previous_monday = (
        current_week_monday
        -
        timedelta(
            days=7
        )
    )


    previous_sunday = (
        previous_monday
        +
        timedelta(
            days=6
        )
    )


    return (
        previous_monday,
        previous_sunday
    )


def load_previous_week_time_logs(
    user_projects
):

    previous_monday, previous_sunday = (
        get_previous_week_range()
    )


    user_project_ids = {
        project[
            "id"
        ]
        for project in user_projects
        if project.get(
            "id"
        )
    }


    project_lookup = {
        project[
            "id"
        ]:
            project
        for project in user_projects
        if project.get(
            "id"
        )
    }


    # Fetch the complete Time Log and filter locally.
    # This is safer because the current Time Log table does not
    # contain a separate User property; the user's own Projects
    # define which records belong to this designer.
    pages = query_data_source(
        TIME_LOG_DATA_SOURCE_ID,
        {
            "page_size":
                100,

            "sorts": [

                {

                    "property":
                        "Start Time",

                    "direction":
                        "ascending"
                }
            ]
        }
    )


    records = []


    for page in pages:

        record = (
            build_time_log_record(
                page,
                project_lookup
            )
        )


        if (
            record[
                "project_id"
            ]
            not in user_project_ids
        ):

            continue


        start_time = (
            record[
                "start"
            ]
        )


        if not start_time:

            continue


        work_date = (
            start_time.date()
        )


        if (
            work_date
            < previous_monday
            or work_date
            > previous_sunday
        ):

            continue


        records.append(
            record
        )


    records.sort(
        key=lambda record:
            record[
                "start"
            ]
            or datetime.min.replace(
                tzinfo=TIMEZONE
            )
    )


    return (
        previous_monday,
        previous_sunday,
        records
    )


def format_pdf_time(
    value
):

    if not value:
        return ""

    return value.strftime(
        "%I:%M %p"
    )


def build_weekly_timesheet_pdf(
    designer_name,
    week_start,
    week_end,
    records
):

    # ========================================================
    # LAYOUT
    # ========================================================
    #
    # The layout intentionally follows the appearance of the
    # Design Department time sheet used as reference:
    #
    # - centered blue TIME SHEET / DESIGN DEPARTMENT heading
    # - employee and week-ending information
    # - Job # / Job Name / M T W T F S S / RT / OT grid
    # - separate RT and OT rows for each job
    # - TOTAL RT / TOTAL OT
    # - Travel Report and Expense Report sections
    # - Employee and Supervisor signature lines
    #
    # The PDF is generated programmatically from the previous
    # Monday-through-Sunday Time Log records.
    # ========================================================

    buffer = io.BytesIO()

    pdf = canvas.Canvas(
        buffer,
        pagesize=letter
    )

    page_width, page_height = (
        letter
    )


    # --------------------------------------------------------
    # COLORS / FONTS
    # --------------------------------------------------------

    blue = colors.HexColor(
        "#3333CC"
    )

    light_yellow = colors.HexColor(
        "#FFFDA3"
    )

    light_gray = colors.HexColor(
        "#F2F2F2"
    )

    grid_color = colors.HexColor(
        "#222222"
    )


    # --------------------------------------------------------
    # PDF HOURS RULE
    # --------------------------------------------------------
    #
    # The printed time sheet uses whole hours only:
    # - decimal portions are discarded (never rounded up)
    # - a displayed daily value can never exceed 8 hours
    #
    # Examples:
    # 2.95 -> 2
    # 7.99 -> 7
    # 8.00 -> 8
    # 9.50 -> 8
    # --------------------------------------------------------

    def pdf_daily_hours(
        value
    ):

        try:

            numeric_value = float(
                value
                or 0
            )

        except Exception:

            numeric_value = 0.0


        if numeric_value <= 0:

            return 0


        whole_hours = int(
            numeric_value
        )


        return min(
            whole_hours,
            8
        )


    # --------------------------------------------------------
    # GENERAL DRAWING HELPERS
    # --------------------------------------------------------

    def draw_centered(
        value,
        x_center,
        y,
        font="Helvetica",
        size=8,
        color=colors.black
    ):

        pdf.setFont(
            font,
            size
        )

        pdf.setFillColor(
            color
        )

        pdf.drawCentredString(
            x_center,
            y,
            str(
                value
            )
        )


    def draw_left(
        value,
        x,
        y,
        font="Helvetica",
        size=8,
        color=colors.black
    ):

        pdf.setFont(
            font,
            size
        )

        pdf.setFillColor(
            color
        )

        pdf.drawString(
            x,
            y,
            str(
                value
            )
        )


    def draw_right(
        value,
        x,
        y,
        font="Helvetica",
        size=8,
        color=colors.black
    ):

        pdf.setFont(
            font,
            size
        )

        pdf.setFillColor(
            color
        )

        pdf.drawRightString(
            x,
            y,
            str(
                value
            )
        )


    def draw_cell_text(
        value,
        x,
        y,
        width,
        height,
        align="center",
        font="Helvetica",
        size=7
    ):

        text_value = (
            ""
            if value is None
            else str(
                value
            )
        )


        max_width = (
            width
            -
            4
        )


        current_size = (
            size
        )


        while (
            current_size > 5
            and pdf.stringWidth(
                text_value,
                font,
                current_size
            )
            >
            max_width
        ):

            current_size -= 0.5


        pdf.setFont(
            font,
            current_size
        )

        pdf.setFillColor(
            colors.black
        )


        text_y = (
            y
            +
            (
                height
                -
                current_size
            )
            / 2
            +
            1
        )


        if align == "left":

            pdf.drawString(
                x + 2,
                text_y,
                text_value
            )


        elif align == "right":

            pdf.drawRightString(
                x
                +
                width
                -
                2,
                text_y,
                text_value
            )


        else:

            pdf.drawCentredString(
                x
                +
                width
                /
                2,
                text_y,
                text_value
            )


    def draw_grid(
        x,
        y_top,
        column_widths,
        row_heights,
        fills=None,
        line_width=0.6
    ):

        total_width = sum(
            column_widths
        )

        total_height = sum(
            row_heights
        )


        if fills:

            row_y = (
                y_top
            )


            for row_index, row_height in enumerate(
                row_heights
            ):

                row_y -= (
                    row_height
                )


                for column_index, column_width in enumerate(
                    column_widths
                ):

                    fill_color = fills.get(
                        (
                            row_index,
                            column_index
                        )
                    )


                    if fill_color:

                        cell_x = (
                            x
                            +
                            sum(
                                column_widths[
                                    :column_index
                                ]
                            )
                        )


                        pdf.setFillColor(
                            fill_color
                        )


                        pdf.rect(
                            cell_x,
                            row_y,
                            column_width,
                            row_height,
                            stroke=0,
                            fill=1
                        )


        pdf.setStrokeColor(
            grid_color
        )

        pdf.setLineWidth(
            line_width
        )


        # Outer rectangle
        pdf.rect(
            x,
            y_top
            -
            total_height,
            total_width,
            total_height,
            stroke=1,
            fill=0
        )


        # Vertical lines
        running_x = (
            x
        )


        for column_width in (
            column_widths[:-1]
        ):

            running_x += (
                column_width
            )


            pdf.line(
                running_x,
                y_top,
                running_x,
                y_top
                -
                total_height
            )


        # Horizontal lines
        running_y = (
            y_top
        )


        for row_height in (
            row_heights[:-1]
        ):

            running_y -= (
                row_height
            )


            pdf.line(
                x,
                running_y,
                x
                +
                total_width,
                running_y
            )


    # --------------------------------------------------------
    # HEADER
    # --------------------------------------------------------

    draw_centered(
        "TIME SHEET",
        page_width / 2,
        760,
        font="Helvetica",
        size=14,
        color=blue
    )


    draw_centered(
        "DESIGN DEPARTMENT",
        page_width / 2,
        742,
        font="Helvetica",
        size=14,
        color=blue
    )


    # Employee / week data
    draw_left(
        "Emp Name:",
        52,
        693,
        font="Helvetica-Bold",
        size=8
    )


    draw_left(
        designer_name,
        128,
        693,
        font="Helvetica-Bold",
        size=8
    )


    pdf.setLineWidth(
        0.5
    )


    pdf.line(
        128,
        690,
        275,
        690
    )


    draw_left(
        "Employee No:",
        418,
        719,
        font="Helvetica-Bold",
        size=8
    )


    # Employee number is not presently stored in the Time Log page.
    # Leave the field blank while preserving the reference layout.
    draw_centered(
        "",
        552,
        719,
        font="Helvetica-Bold",
        size=8
    )


    draw_left(
        "Week Ending:",
        418,
        693,
        font="Helvetica-Bold",
        size=8
    )


    draw_right(
        week_end.strftime(
            "%m/%d/%y"
        ),
        575,
        693,
        font="Helvetica-Bold",
        size=8
    )


    # --------------------------------------------------------
    # AGGREGATE WEEKLY RECORDS BY PROJECT
    # --------------------------------------------------------

    project_rows = {}


    for record in records:

        project_label = (
            record.get(
                "project"
            )
            or ""
        )


        if " - " in project_label:

            project_number, project_name = (
                project_label.split(
                    " - ",
                    1
                )
            )

        else:

            project_number = (
                project_label
            )

            project_name = ""


        key = (
            project_number,
            project_name
        )


        if key not in project_rows:

            project_rows[
                key
            ] = {

                "project_number":
                    project_number,

                "project_name":
                    project_name,

                "daily":
                    [
                        0.0
                    ]
                    *
                    7,

                "total":
                    0.0,
            }


        start_time = (
            record.get(
                "start"
            )
        )


        if not start_time:

            continue


        day_index = (
            start_time.date()
            -
            week_start
        ).days


        if (
            day_index
            <
            0
            or day_index
            >
            6
        ):

            continue


        worked_hours = float(
            record.get(
                "hours"
            )
            or 0.0
        )


        project_rows[
            key
        ][
            "daily"
        ][
            day_index
        ] += (
            worked_hours
        )


        project_rows[
            key
        ][
            "total"
        ] += (
            worked_hours
        )


    project_rows = list(
        project_rows.values()
    )


    # Convert raw decimal hours into the values that will
    # actually appear in the PDF.
    for project_row in project_rows:

        project_row[
            "printed_daily"
        ] = [
            pdf_daily_hours(
                day_hours
            )
            for day_hours in project_row[
                "daily"
            ]
        ]


        project_row[
            "printed_total"
        ] = sum(
            project_row[
                "printed_daily"
            ]
        )


    project_rows.sort(
        key=lambda row: (
            row[
                "project_number"
            ],
            row[
                "project_name"
            ]
        )
    )


    # Reference form has space for 9 jobs.
    # If there are more, first 9 are shown on this page.
    max_project_rows = 9


    visible_projects = (
        project_rows[
            :max_project_rows
        ]
    )


    # --------------------------------------------------------
    # MAIN TIME GRID
    # --------------------------------------------------------

    grid_x = (
        51
    )


    grid_top = (
        676
    )


    header_height = (
        16
    )


    rt_height = (
        14
    )


    ot_height = (
        13
    )


    column_widths = [
        75,   # Job #
        155,  # Job Name
        20,   # RT / OT
        32,   # Mon
        32,   # Tue
        32,   # Wed
        32,   # Thu
        32,   # Fri
        32,   # Sat
        32,   # Sun
        34,   # RT
        34,   # OT
    ]


    row_heights = [
        header_height
    ]


    for _ in range(
        max_project_rows
    ):

        row_heights.extend(
            [
                rt_height,
                ot_height,
            ]
        )


    fills = {}


    # Header fill is white just like reference.
    for project_index in range(
        max_project_rows
    ):

        rt_row = (
            1
            +
            project_index
            *
            2
        )


        ot_row = (
            rt_row
            +
            1
        )


        # OT row yellow from RT/OT marker through OT total.
        for column_index in range(
            2,
            len(
                column_widths
            )
        ):

            fills[
                (
                    ot_row,
                    column_index
                )
            ] = (
                light_yellow
            )


    draw_grid(
        grid_x,
        grid_top,
        column_widths,
        row_heights,
        fills=fills,
        line_width=0.65
    )


    # Header labels
    headers = [
        "Job #",
        "Job Name",
        "",
        "M",
        "T",
        "W",
        "T",
        "F",
        "S",
        "S",
        "RT",
        "OT",
    ]


    running_x = (
        grid_x
    )


    for column_index, (
        column_width,
        header
    ) in enumerate(
        zip(
            column_widths,
            headers
        )
    ):

        draw_cell_text(
            header,
            running_x,
            grid_top
            -
            header_height,
            column_width,
            header_height,
            align="center",
            font="Helvetica-Bold",
            size=8
        )


        running_x += (
            column_width
        )


    # Data rows
    data_y_top = (
        grid_top
        -
        header_height
    )


    for project_index in range(
        max_project_rows
    ):

        rt_top = (
            data_y_top
            -
            project_index
            *
            (
                rt_height
                +
                ot_height
            )
        )


        rt_y = (
            rt_top
            -
            rt_height
        )


        ot_y = (
            rt_y
            -
            ot_height
        )


        if (
            project_index
            <
            len(
                visible_projects
            )
        ):

            project = (
                visible_projects[
                    project_index
                ]
            )


            # Job # spans RT/OT visually through repeated empty OT line.
            draw_cell_text(
                project[
                    "project_number"
                ],
                grid_x,
                rt_y,
                column_widths[
                    0
                ],
                rt_height,
                align="center",
                font="Helvetica",
                size=7
            )


            draw_cell_text(
                project[
                    "project_name"
                ],
                grid_x
                +
                column_widths[
                    0
                ],
                rt_y,
                column_widths[
                    1
                ],
                rt_height,
                align="center",
                font="Helvetica",
                size=7
            )


            # RT / OT labels
            rt_x = (
                grid_x
                +
                column_widths[
                    0
                ]
                +
                column_widths[
                    1
                ]
            )


            draw_cell_text(
                "RT",
                rt_x,
                rt_y,
                column_widths[
                    2
                ],
                rt_height,
                font="Helvetica",
                size=7
            )


            draw_cell_text(
                "OT",
                rt_x,
                ot_y,
                column_widths[
                    2
                ],
                ot_height,
                font="Helvetica",
                size=7
            )


            day_x = (
                rt_x
                +
                column_widths[
                    2
                ]
            )


            for day_index in range(
                7
            ):

                hours_value = (
                    project[
                        "printed_daily"
                    ][
                        day_index
                    ]
                )


                display_hours = (
                    ""
                    if hours_value <= 0
                    else str(
                        hours_value
                    )
                )


                draw_cell_text(
                    display_hours,
                    day_x,
                    rt_y,
                    column_widths[
                        3
                        +
                        day_index
                    ],
                    rt_height,
                    font="Helvetica",
                    size=7
                )


                day_x += (
                    column_widths[
                        3
                        +
                        day_index
                    ]
                )


            # RT total
            draw_cell_text(
                str(
                    project[
                        "printed_total"
                    ]
                )
                if project[
                    "printed_total"
                ] > 0
                else "",
                day_x,
                rt_y,
                column_widths[
                    10
                ],
                rt_height,
                font="Helvetica",
                size=7
            )


            # OT total intentionally blank.
            day_x += (
                column_widths[
                    10
                ]
            )


            draw_cell_text(
                "",
                day_x,
                ot_y,
                column_widths[
                    11
                ],
                ot_height,
                font="Helvetica",
                size=7
            )


        else:

            rt_x = (
                grid_x
                +
                column_widths[
                    0
                ]
                +
                column_widths[
                    1
                ]
            )


            draw_cell_text(
                "RT",
                rt_x,
                rt_y,
                column_widths[
                    2
                ],
                rt_height,
                font="Helvetica",
                size=7
            )


            draw_cell_text(
                "OT",
                rt_x,
                ot_y,
                column_widths[
                    2
                ],
                ot_height,
                font="Helvetica",
                size=7
            )


    grid_bottom = (
        grid_top
        -
        sum(
            row_heights
        )
    )


    # --------------------------------------------------------
    # HOLIDAY / PTO MINI TABLE
    # --------------------------------------------------------

    mini_top = (
        grid_bottom
        -
        12
    )


    mini_column_widths = [
        75,
        155,
        20,
        32,
        32,
        32,
        32,
        32,
        32,
        32,
    ]


    mini_row_heights = [
        14,
        14,
    ]


    mini_fills = {}


    draw_grid(
        grid_x,
        mini_top,
        mini_column_widths,
        mini_row_heights,
        fills=mini_fills,
        line_width=0.6
    )


    mini_rows = [
        (
            "100.1.2445",
            "Holiday"
        ),
        (
            "130.1.2442",
            "PTO"
        ),
    ]


    mini_y = (
        mini_top
    )


    for row_index, (
        job_number,
        description
    ) in enumerate(
        mini_rows
    ):

        row_y = (
            mini_y
            -
            (
                row_index
                +
                1
            )
            *
            mini_row_heights[
                row_index
            ]
        )


        draw_cell_text(
            job_number,
            grid_x,
            row_y,
            mini_column_widths[
                0
            ],
            mini_row_heights[
                row_index
            ],
            size=6.5
        )


        draw_cell_text(
            description,
            grid_x
            +
            mini_column_widths[
                0
            ],
            row_y,
            mini_column_widths[
                1
            ],
            mini_row_heights[
                row_index
            ],
            align="left",
            size=6.5
        )


        rt_x = (
            grid_x
            +
            mini_column_widths[
                0
            ]
            +
            mini_column_widths[
                1
            ]
        )


        draw_cell_text(
            "RT",
            rt_x,
            row_y,
            mini_column_widths[
                2
            ],
            mini_row_heights[
                row_index
            ],
            size=6.5
        )


    total_rt = sum(
        project[
            "printed_total"
        ]
        for project in project_rows
    )


    totals_y = (
        mini_top
        -
        sum(
            mini_row_heights
        )
        -
        19
    )


    draw_right(
        "TOTAL RT",
        493,
        totals_y,
        font="Helvetica",
        size=8
    )


    pdf.rect(
        522,
        totals_y
        -
        3,
        33,
        14,
        stroke=1,
        fill=0
    )


    draw_centered(
        str(
            int(
                total_rt
            )
        ),
        538.5,
        totals_y
        +
        1,
        size=7
    )


    draw_right(
        "TOTAL OT",
        493,
        totals_y
        -
        15,
        font="Helvetica",
        size=8
    )


    pdf.setFillColor(
        light_yellow
    )


    pdf.rect(
        555,
        totals_y
        -
        18,
        33,
        14,
        stroke=1,
        fill=1
    )


    # --------------------------------------------------------
    # TRAVEL REPORT
    # --------------------------------------------------------

    travel_title_y = (
        totals_y
        -
        39
    )


    draw_left(
        "TRAVEL REPORT",
        grid_x,
        travel_title_y,
        font="Helvetica",
        size=8
    )


    travel_top = (
        travel_title_y
        -
        5
    )


    travel_widths = [
        75,
        210,
        30,
        78,
        145,
    ]


    travel_heights = [
        14,
        14,
        14,
        14,
        14,
        14,
    ]


    travel_fills = {}


    # Miles cells in detail rows and blank extended amount
    # cells are lightly highlighted to resemble the form.
    for row_index in range(
        1,
        len(
            travel_heights
        )
    ):

        travel_fills[
            (
                row_index,
                2
            )
        ] = (
            light_yellow
        )


    draw_grid(
        grid_x,
        travel_top,
        travel_widths,
        travel_heights,
        fills=travel_fills,
        line_width=0.6
    )


    travel_headers = [
        "JOB #",
        "DESCRIPTION & DATE",
        "Miles",
        "",
        "EXTENDED AMOUNT",
    ]


    running_x = (
        grid_x
    )


    for width, header in zip(
        travel_widths,
        travel_headers
    ):

        draw_cell_text(
            header,
            running_x,
            travel_top
            -
            travel_heights[
                0
            ],
            width,
            travel_heights[
                0
            ],
            font="Helvetica",
            size=7
        )


        running_x += (
            width
        )


    # Formula label rows like reference
    for row_index in range(
        1,
        5
    ):

        formula_x = (
            grid_x
            +
            sum(
                travel_widths[
                    :3
                ]
            )
        )


        row_y = (
            travel_top
            -
            sum(
                travel_heights[
                    :row_index
                    +
                    1
                ]
            )
        )


        draw_cell_text(
            "(Miles x .725)",
            formula_x,
            row_y,
            travel_widths[
                3
            ],
            travel_heights[
                row_index
            ],
            size=6.5
        )


    # Total row
    total_travel_y = (
        travel_top
        -
        sum(
            travel_heights
        )
    )


    draw_cell_text(
        "TOTAL",
        grid_x
        +
        sum(
            travel_widths[
                :3
            ]
        ),
        total_travel_y,
        travel_widths[
            3
        ],
        travel_heights[
            -1
        ],
        align="right",
        font="Helvetica",
        size=7
    )


    # --------------------------------------------------------
    # EXPENSE REPORT
    # --------------------------------------------------------

    expense_title_y = (
        total_travel_y
        -
        20
    )


    draw_left(
        "EXPENSE REPORT (ATTACH ALL RECEIPTS)",
        grid_x,
        expense_title_y,
        font="Helvetica",
        size=8
    )


    expense_top = (
        expense_title_y
        -
        5
    )


    expense_widths = [
        75,
        330,
        133,
    ]


    expense_heights = [
        14,
        14,
        14,
        14,
        14,
    ]


    expense_fills = {}


    for row_index in range(
        1,
        4
    ):

        expense_fills[
            (
                row_index,
                2
            )
        ] = (
            light_yellow
        )


    draw_grid(
        grid_x,
        expense_top,
        expense_widths,
        expense_heights,
        fills=expense_fills,
        line_width=0.6
    )


    expense_headers = [
        "JOB #",
        "DESCRIPTION & DATE OF EXPENSE",
        "AMOUNT",
    ]


    running_x = (
        grid_x
    )


    for width, header in zip(
        expense_widths,
        expense_headers
    ):

        draw_cell_text(
            header,
            running_x,
            expense_top
            -
            expense_heights[
                0
            ],
            width,
            expense_heights[
                0
            ],
            font="Helvetica",
            size=7
        )


        running_x += (
            width
        )


    expense_total_y = (
        expense_top
        -
        sum(
            expense_heights
        )
    )


    draw_cell_text(
        "TOTAL",
        grid_x
        +
        expense_widths[
            0
        ],
        expense_total_y,
        expense_widths[
            1
        ],
        expense_heights[
            -1
        ],
        align="right",
        size=7
    )


    # --------------------------------------------------------
    # SIGNATURES
    # --------------------------------------------------------

    signature_y = (
        expense_total_y
        -
        31
    )


    draw_left(
        "Emp. Signature",
        grid_x,
        signature_y,
        size=8
    )


    pdf.line(
        124,
        signature_y
        -
        3,
        302,
        signature_y
        -
        3
    )


    draw_left(
        "Date",
        309,
        signature_y,
        size=8
    )


    pdf.line(
        338,
        signature_y
        -
        3,
        385,
        signature_y
        -
        3
    )


    draw_centered(
        week_end.strftime(
            "%m/%d/%y"
        ),
        361.5,
        signature_y
        +
        1,
        size=6.5
    )


    draw_left(
        "Super. Signature",
        396,
        signature_y,
        size=8
    )


    pdf.line(
        481,
        signature_y
        -
        3,
        588,
        signature_y
        -
        3
    )


    # --------------------------------------------------------
    # FOOTNOTE
    # --------------------------------------------------------

    if (
        len(
            project_rows
        )
        >
        max_project_rows
    ):

        draw_left(
            (
                f"Note: {len(project_rows) - max_project_rows} "
                "additional project(s) are not shown in the main grid."
            ),
            grid_x,
            18,
            font="Helvetica-Oblique",
            size=6,
            color=colors.grey
        )


    pdf.showPage()

    pdf.save()


    pdf_bytes = (
        buffer.getvalue()
    )


    buffer.close()


    return pdf_bytes


# ============================================================
# PAGE HEADER
# ============================================================

st.title(
    "⏱️ Time Log"
)


st.caption(
    "Record the time worked on your projects."
)


# ============================================================
# LOGGED DESIGNER
# ============================================================

logged_user = (
    get_logged_user()
)


if not logged_user:

    st.error(
        "The logged-in designer "
        "could not be identified."
    )

    st.stop()


st.write(
    f"👤 Designer: "
    f"{logged_user}"
)


st.divider()


# ============================================================
# LOAD PROJECTS
# ============================================================

with st.spinner(
    "Loading your projects..."
):

    projects = (
        load_projects_for_designer(
            logged_user
        )
    )


if not projects:

    st.info(
        "No projects were found "
        "for the logged-in designer."
    )

    st.stop()


# ============================================================
# PROJECT LOOKUP
# ============================================================

project_by_id = {

    project[
        "id"
    ]:
        project

    for project in projects
}


project_options = {}


for project in projects:

    project_number = (
        project[
            "project_number"
        ]
    )

    project_name = (
        project[
            "project_name"
        ]
    )


    if (
        project_number
        and project_name
    ):

        label = (
            f"{project_number} - "
            f"{project_name}"
        )


    elif project_number:

        label = project_number


    elif project_name:

        label = project_name


    else:

        label = (
            "Unnamed Project"
        )


    project_options[
        label
    ] = project


# ============================================================
# ACTIVE PROJECT DEFAULT INDEX
# ============================================================

default_index = 0


if (
    st.session_state
    .time_log_running
):

    active_project_id = (
        st.session_state
        .time_log_project_id
    )


    for index, (
        label,
        project
    ) in enumerate(
        project_options.items()
    ):

        if (
            project[
                "id"
            ]
            ==
            active_project_id
        ):

            default_index = (
                index
            )

            break


# ============================================================
# PROJECT SELECTION
# ============================================================

st.subheader(
    "Project"
)


selected_label = (
    st.selectbox(

        "Select Project",

        options=list(
            project_options.keys()
        ),

        index=default_index,

        disabled=(
            st.session_state
            .time_log_running
        )
    )
)


selected_project = (
    project_options[
        selected_label
    ]
)


# ============================================================
# KEEP PROJECT HOURS IMMEDIATELY SYNCHRONIZED AFTER A WRITE
# ============================================================

last_project_values = (
    st.session_state
    .time_log_last_project_values
)


if (
    last_project_values
    and selected_project[
        "id"
    ]
    ==
    st.session_state
    .time_log_last_project_id
):

    selected_project = (
        selected_project.copy()
    )

    selected_project[
        "planned_hours"
    ] = last_project_values[
        "planned_hours"
    ]

    selected_project[
        "used_hours"
    ] = last_project_values[
        "used_hours"
    ]

    selected_project[
        "remaining_hours"
    ] = last_project_values[
        "remaining_hours"
    ]

    selected_project[
        "used_percent"
    ] = last_project_values[
        "used_percent"
    ]


# ============================================================
# TASK
# ============================================================

if (
    st.session_state
    .time_log_running
):

    task_default = (
        st.session_state
        .time_log_task
    )

else:

    task_default = ""


task_value = (
    st.text_input(

        "Task",

        value=
            task_default,

        placeholder=(
            "Example: Submittal, Stocklist, "
            "Foreman's Package..."
        ),

        disabled=(
            st.session_state
            .time_log_running
        )
    )
)


# ============================================================
# PROJECT HOURS
# ============================================================

st.subheader(
    "Project Hours"
)


col1, col2, col3, col4 = (
    st.columns(4)
)


with col1:

    st.metric(
        "Planned Hours",
        f"{selected_project['planned_hours']:.2f}"
    )


with col2:

    st.metric(
        "Hours Used Total",
        f"{selected_project['used_hours']:.2f}"
    )


with col3:

    st.metric(
        "Remaining Hours",
        f"{selected_project['remaining_hours']:.2f}"
    )


with col4:

    st.metric(
        "Used Hours (%)",
        f"{selected_project['used_percent']:.1f}%"
    )


st.divider()


# ============================================================
# TIMER
# ============================================================

st.subheader(
    "Time Control"
)


button_col1, button_col2 = (
    st.columns(2)
)


with button_col1:

    start_clicked = st.button(
        "▶ Start",
        type="primary",
        use_container_width=True,
        disabled=(
            st.session_state
            .time_log_running
        )
    )


with button_col2:

    pause_clicked = st.button(
        "⏸ Pause",
        use_container_width=True,
        disabled=(
            not st.session_state
            .time_log_running
        )
    )


# ============================================================
# START ACTION
# ============================================================

if start_clicked:

    if not task_value.strip():

        st.warning(
            "Please enter a Task "
            "before starting."
        )

        st.stop()


    start_time = datetime.now(
        TIMEZONE
    )


    st.session_state.time_log_running = (
        True
    )

    st.session_state.time_log_start = (
        start_time
    )

    st.session_state.time_log_project_id = (
        selected_project[
            "id"
        ]
    )

    st.session_state.time_log_project_label = (
        selected_label
    )

    st.session_state.time_log_task = (
        task_value.strip()
    )

    # Clear previous completed-session editor.
    st.session_state.time_log_last_end = (
        None
    )

    st.session_state.time_log_last_hours = (
        None
    )

    st.session_state.time_log_last_page_id = (
        None
    )

    st.session_state.time_log_last_project_id = (
        None
    )

    st.session_state.time_log_last_task = (
        ""
    )

    st.session_state.time_log_last_start = (
        None
    )

    st.session_state.time_log_last_recorded_hours = (
        None
    )

    st.session_state.time_log_last_project_values = (
        None
    )


    st.rerun()


# ============================================================
# EDITABLE START TIME WHILE TIMER IS RUNNING
# ============================================================

if (
    st.session_state
    .time_log_running
    and st.session_state
    .time_log_start
):

    st.markdown(
        "#### Current Session Time"
    )


    current_start = (
        st.session_state
        .time_log_start
    )


    start_date_col, start_time_col = (
        st.columns(2)
    )


    with start_date_col:

        edited_start_date = (
            st.date_input(
                "Start Date",
                value=
                    current_start.date(),
                key=
                    "running_start_date"
            )
        )


    with start_time_col:

        edited_start_clock = (
            st.time_input(
                "Start Time",
                value=
                    current_start.time()
                    .replace(
                        microsecond=0
                    ),
                step=60,
                key=
                    "running_start_clock"
            )
        )


    edited_running_start = (
        combine_date_and_time(
            edited_start_date,
            edited_start_clock
        )
    )


    # Update session immediately if user changes the Start time.
    if (
        edited_running_start
        !=
        st.session_state
        .time_log_start
    ):

        st.session_state.time_log_start = (
            edited_running_start
        )


# ============================================================
# PAUSE ACTION
# ============================================================

if pause_clicked:

    end_time = datetime.now(
        TIMEZONE
    )


    start_time = (
        st.session_state
        .time_log_start
    )


    active_project_id = (
        st.session_state
        .time_log_project_id
    )


    active_task = (
        st.session_state
        .time_log_task
    )


    if not start_time:

        st.error(
            "Start Time was not found."
        )

        st.stop()


    if not active_project_id:

        st.error(
            "The active project "
            "could not be found."
        )

        st.stop()


    elapsed_seconds = (

        end_time
        -
        start_time

    ).total_seconds()


    worked_hours = (

        elapsed_seconds
        /
        3600
    )


    if worked_hours <= 0:

        st.error(
            "Invalid time interval. "
            "End Time must be after Start Time."
        )

        st.stop()


    # --------------------------------------------------------
    # CREATE TIME LOG
    # --------------------------------------------------------

    time_log_page_id = (
        create_time_log_page(

            project_id=
                active_project_id,

            task=
                active_task,

            start_time=
                start_time,

            end_time=
                end_time
        )
    )


    if not time_log_page_id:

        st.error(
            "The Time Log was not created. "
            "Project hours were not changed."
        )

        st.stop()


    # --------------------------------------------------------
    # UPDATE PROJECT HOURS
    # --------------------------------------------------------
    #
    # update_project_hours_by_delta reads the Project again
    # first, then adds worked_hours to the Used Hours that is
    # CURRENTLY stored in the Projects table.
    # --------------------------------------------------------

    project_updated = (
        update_project_hours_by_delta(

            active_project_id,

            worked_hours
        )
    )


    if not project_updated:

        st.error(
            "The Time Log was created, "
            "but the Project Hours "
            "could not be updated."
        )

        st.stop()


    st.session_state.time_log_last_project_values = (
        project_updated
    )


    if not project_updated.get(
        "verified",
        False
    ):

        st.warning(
            "Project Hours were sent successfully, "
            "but the updated values were not yet returned "
            "by the database. The values shown below use "
            "the confirmed calculation from this session."
        )


    # --------------------------------------------------------
    # SAVE LAST SESSION FOR EDITING
    # --------------------------------------------------------

    st.session_state.time_log_last_page_id = (
        time_log_page_id
    )

    st.session_state.time_log_last_project_id = (
        active_project_id
    )

    st.session_state.time_log_last_task = (
        active_task
    )

    st.session_state.time_log_last_start = (
        start_time
    )

    st.session_state.time_log_last_end = (
        end_time
    )

    st.session_state.time_log_last_hours = (
        worked_hours
    )

    st.session_state.time_log_last_recorded_hours = (
        worked_hours
    )


    # --------------------------------------------------------
    # RESET ACTIVE TIMER
    # --------------------------------------------------------

    st.session_state.time_log_running = (
        False
    )

    st.session_state.time_log_start = (
        None
    )

    st.session_state.time_log_project_id = (
        None
    )

    st.session_state.time_log_project_label = (
        None
    )

    st.session_state.time_log_task = (
        ""
    )


    st.rerun()


# ============================================================
# TIMER STATUS
# ============================================================

st.divider()


if (
    st.session_state
    .time_log_running
):

    st.success(
        "Timer is running."
    )


    st.write(
        f"Project: "
        f"{st.session_state.time_log_project_label}"
    )


    st.write(
        f"Task: "
        f"{st.session_state.time_log_task}"
    )


    current_time = datetime.now(
        TIMEZONE
    )


    elapsed_seconds = (

        current_time
        -
        st.session_state
        .time_log_start

    ).total_seconds()


    elapsed_seconds = max(
        elapsed_seconds,
        0
    )


    elapsed_hours = (
        elapsed_seconds
        /
        3600
    )


    total_minutes = int(
        elapsed_seconds
        /
        60
    )


    hours = (
        total_minutes
        //
        60
    )


    minutes = (
        total_minutes
        %
        60
    )


    col1, col2 = (
        st.columns(2)
    )


    with col1:

        st.metric(
            "Current Session",
            f"{hours:02d}:{minutes:02d}"
        )


    with col2:

        st.metric(
            "Decimal Hours",
            f"{elapsed_hours:.2f}"
        )


# ============================================================
# LAST RECORDED SESSION - EDITABLE START / END
# ============================================================

elif (
    st.session_state
    .time_log_last_page_id
    and
    st.session_state
    .time_log_last_start
    and
    st.session_state
    .time_log_last_end
):

    st.success(
        "Time recorded successfully."
    )


    last_hours = (
        st.session_state
        .time_log_last_recorded_hours
        or 0.0
    )


    last_minutes = int(
        round(
            last_hours
            *
            60
        )
    )


    hours = (
        last_minutes
        //
        60
    )


    minutes = (
        last_minutes
        %
        60
    )


    col1, col2 = (
        st.columns(2)
    )


    with col1:

        st.metric(
            "Last Session",
            f"{hours:02d}:{minutes:02d}"
        )


    with col2:

        st.metric(
            "Hours Recorded",
            f"{last_hours:.2f}"
        )


    st.markdown(
        "#### Edit Recorded Time"
    )


    st.caption(
        "If you change the Start or End time, "
        "the Time Log and the Project Used Hours, "
        "Remaining Hours and Used Hours (%) "
        "will be recalculated automatically when you save."
    )


    last_start = (
        st.session_state
        .time_log_last_start
    )


    last_end = (
        st.session_state
        .time_log_last_end
    )


    start_col1, start_col2, end_col1, end_col2 = (
        st.columns(4)
    )


    with start_col1:

        edited_last_start_date = (
            st.date_input(
                "Start Date",
                value=
                    last_start.date(),
                key=
                    "last_start_date"
            )
        )


    with start_col2:

        edited_last_start_clock = (
            st.time_input(
                "Start Time",
                value=
                    last_start.time()
                    .replace(
                        microsecond=0
                    ),
                step=60,
                key=
                    "last_start_clock"
            )
        )


    with end_col1:

        edited_last_end_date = (
            st.date_input(
                "End Date",
                value=
                    last_end.date(),
                key=
                    "last_end_date"
            )
        )


    with end_col2:

        edited_last_end_clock = (
            st.time_input(
                "End Time",
                value=
                    last_end.time()
                    .replace(
                        microsecond=0
                    ),
                step=60,
                key=
                    "last_end_clock"
            )
        )


    edited_last_start = (
        combine_date_and_time(
            edited_last_start_date,
            edited_last_start_clock
        )
    )


    edited_last_end = (
        combine_date_and_time(
            edited_last_end_date,
            edited_last_end_clock
        )
    )


    edited_seconds = (

        edited_last_end
        -
        edited_last_start

    ).total_seconds()


    edited_hours = (

        edited_seconds
        /
        3600

        if edited_seconds > 0

        else 0.0
    )


    st.metric(
        "Adjusted Hours",
        f"{edited_hours:.2f}"
    )


    save_adjustment = (
        st.button(
            "💾 Update Recorded Time",
            type="primary",
            use_container_width=True
        )
    )


    if save_adjustment:

        if edited_seconds <= 0:

            st.error(
                "End Time must be after Start Time."
            )

            st.stop()


        last_time_log_page_id = (
            st.session_state
            .time_log_last_page_id
        )


        last_project_id = (
            st.session_state
            .time_log_last_project_id
        )


        previous_recorded_hours = (
            st.session_state
            .time_log_last_recorded_hours
            or 0.0
        )


        hours_delta = (

            edited_hours
            -
            previous_recorded_hours
        )


        # ----------------------------------------------------
        # UPDATE TIME LOG RECORD
        # ----------------------------------------------------

        time_log_updated = (
            update_time_log_times(

                last_time_log_page_id,

                edited_last_start,

                edited_last_end
            )
        )


        if not time_log_updated:

            st.stop()


        # ----------------------------------------------------
        # UPDATE PROJECT USING ONLY THE DIFFERENCE
        # ----------------------------------------------------
        #
        # Example:
        # Original record = 2.00 h
        # Edited record   = 2.50 h
        # Project receives +0.50 h
        #
        # If reduced from 2.00 h to 1.50 h,
        # Project receives -0.50 h.
        # ----------------------------------------------------

        project_updated = (
            update_project_hours_by_delta(

                last_project_id,

                hours_delta
            )
        )


        if not project_updated:

            st.error(
                "The Time Log was updated, "
                "but the Project Hours "
                "could not be updated."
            )

            st.stop()


        st.session_state.time_log_last_project_values = (
            project_updated
        )


        # ----------------------------------------------------
        # SAVE ADJUSTED VALUES IN SESSION
        # ----------------------------------------------------

        st.session_state.time_log_last_start = (
            edited_last_start
        )

        st.session_state.time_log_last_end = (
            edited_last_end
        )

        st.session_state.time_log_last_hours = (
            edited_hours
        )

        st.session_state.time_log_last_recorded_hours = (
            edited_hours
        )


        st.success(
            "Recorded time and Project Hours "
            "updated successfully."
        )


        st.rerun()

# ============================================================
# SELECTED PROJECT - TIME LOG HISTORY
# ============================================================

st.divider()


st.subheader(
    "Worked Time History"
)


st.caption(
    "All recorded work periods for the Project selected above."
)


with st.spinner(
    "Loading worked time history..."
):

    selected_project_logs = (
        load_time_logs_for_project(
            selected_project[
                "id"
            ]
        )
    )


if not selected_project_logs:

    st.info(
        "No worked time records were found "
        "for the selected Project."
    )


else:

    history_rows = []


    for record in (
        selected_project_logs
    ):

        start_time = (
            record[
                "start"
            ]
        )


        end_time = (
            record[
                "end"
            ]
        )


        history_rows.append(
            {
                "Date":
                    (
                        start_time.strftime(
                            "%m/%d/%Y"
                        )
                        if start_time
                        else ""
                    ),

                "Task":
                    record[
                        "task"
                    ],

                "Start Time":
                    (
                        start_time.strftime(
                            "%I:%M %p"
                        )
                        if start_time
                        else ""
                    ),

                "End Time":
                    (
                        end_time.strftime(
                            "%I:%M %p"
                        )
                        if end_time
                        else ""
                    ),

                "Hours":
                    round(
                        record[
                            "hours"
                        ],
                        2
                    ),
            }
        )


    st.dataframe(
        history_rows,
        use_container_width=True,
        hide_index=True,

        column_order=[
            "Date",
            "Task",
            "Start Time",
            "End Time",
            "Hours",
        ],

        column_config={

            "Date":
                st.column_config.TextColumn(
                    "Date"
                ),

            "Task":
                st.column_config.TextColumn(
                    "Task",
                    width="large"
                ),

            "Start Time":
                st.column_config.TextColumn(
                    "Start Time"
                ),

            "End Time":
                st.column_config.TextColumn(
                    "End Time"
                ),

            "Hours":
                st.column_config.NumberColumn(
                    "Hours",
                    format="%.2f"
                ),
        },
    )


    total_selected_project_hours = sum(
        record[
            "hours"
        ]
        for record in selected_project_logs
    )


    st.metric(
        "Total Recorded Time for Selected Project",
        f"{total_selected_project_hours:.2f} hours"
    )


# ============================================================
# PREVIOUS WEEK PDF
# ============================================================

st.divider()


st.subheader(
    "Weekly Time Sheet"
)


previous_monday, previous_sunday, previous_week_records = (
    load_previous_week_time_logs(
        projects
    )
)


previous_week_total = sum(
    record[
        "hours"
    ]
    for record in previous_week_records
)


week_col1, week_col2, week_col3 = (
    st.columns(3)
)


with week_col1:

    st.metric(
        "Week Start",
        previous_monday.strftime(
            "%m/%d/%Y"
        )
    )


with week_col2:

    st.metric(
        "Week End",
        previous_sunday.strftime(
            "%m/%d/%Y"
        )
    )


with week_col3:

    st.metric(
        "Total Hours",
        f"{previous_week_total:.2f}"
    )


weekly_pdf_bytes = (
    build_weekly_timesheet_pdf(

        designer_name=
            logged_user,

        week_start=
            previous_monday,

        week_end=
            previous_sunday,

        records=
            previous_week_records,
    )
)


pdf_file_name = (
    "Weekly_Time_Sheet_"
    f"{previous_monday.strftime('%Y%m%d')}_"
    f"{previous_sunday.strftime('%Y%m%d')}.pdf"
)


st.download_button(
    "📄 Generate Previous Week PDF",
    data=
        weekly_pdf_bytes,
    file_name=
        pdf_file_name,
    mime=
        "application/pdf",
    type=
        "primary",
    use_container_width=True,
)


st.caption(
    "The report covers the previous completed week, "
    "Monday through Sunday. The employee signature date "
    "is set to the final Sunday of that week."
)

