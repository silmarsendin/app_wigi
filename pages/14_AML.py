import streamlit as st
import requests
import pandas as pd

from io import BytesIO
from math import ceil
from datetime import date, datetime

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth

from supabase import create_client, Client


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="AML - Anticipated Material List",
    page_icon="📦",
    layout="wide"
)


# =========================================================
# AUTH CHECK
# =========================================================

if not st.session_state.get("authenticated", False):
    st.warning("Please sign in to continue.")
    st.stop()


# =========================================================
# SETTINGS
# =========================================================

NOTION_TOKEN = st.secrets["NOTION_TOKEN"]

NOTION_PROJECTS_DATA_SOURCE_ID = (
    st.secrets.get("NOTION_PROJECTS_DATA_SOURCE_ID")
    or st.secrets.get("PROJECTS_DATA_SOURCE_ID")
    or st.secrets.get("NOTION_PROJECTS_DATABASE_ID")
)

SUPABASE_URL = (
    st.secrets.get("SUPABASE_URL", "")
    or ""
).strip().rstrip("/")

SUPABASE_KEY = (
    st.secrets.get("SUPABASE_SECRET_KEY", "")
    or st.secrets.get("SUPABASE_SERVICE_ROLE_KEY", "")
    or st.secrets.get("SUPABASE_PUBLISHABLE_KEY", "")
    or st.secrets.get("SUPABASE_ANON_KEY", "")
    or st.secrets.get("SUPABASE_KEY", "")
    or ""
).strip()

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2025-09-03",
}


# =========================================================
# SUPABASE CLIENT
# =========================================================

@st.cache_resource
def get_supabase_client() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError(
            "Supabase is not configured. Check SUPABASE_URL "
            "and SUPABASE_SECRET_KEY in Streamlit Secrets."
        )

    return create_client(
        SUPABASE_URL,
        SUPABASE_KEY
    )


supabase = get_supabase_client()


# =========================================================
# SESSION STATE
# =========================================================

if "aml_draft_items" not in st.session_state:
    st.session_state.aml_draft_items = []

if "aml_last_saved_id" not in st.session_state:
    st.session_state.aml_last_saved_id = None


if "aml_pdf_bytes" not in st.session_state:
    st.session_state.aml_pdf_bytes = None

if "aml_pdf_filename" not in st.session_state:
    st.session_state.aml_pdf_filename = None

if "aml_pdf_source_id" not in st.session_state:
    st.session_state.aml_pdf_source_id = None


# =========================================================
# NOTION HELPERS
# =========================================================

def get_property_plain_text(prop):
    if not prop:
        return ""

    prop_type = prop.get("type")

    if prop_type == "title":
        return " ".join(
            item.get("plain_text", "")
            for item in prop.get("title", [])
        ).strip()

    if prop_type == "rich_text":
        return " ".join(
            item.get("plain_text", "")
            for item in prop.get("rich_text", [])
        ).strip()

    if prop_type == "select":
        value = prop.get("select")
        return value.get("name", "") if value else ""

    if prop_type == "status":
        value = prop.get("status")
        return value.get("name", "") if value else ""

    if prop_type == "number":
        value = prop.get("number")
        return "" if value is None else str(value)

    if prop_type == "email":
        return prop.get("email") or ""

    return ""


def query_notion_data_source(data_source_id):
    if not data_source_id:
        return []

    url = (
        "https://api.notion.com/v1/data_sources/"
        f"{data_source_id}/query"
    )

    results = []
    payload = {}

    while True:
        try:
            response = requests.post(
                url,
                headers=NOTION_HEADERS,
                json=payload,
                timeout=20
            )
        except requests.RequestException:
            return []

        if response.status_code != 200:
            return []

        data = response.json()
        results.extend(data.get("results", []))

        if not data.get("has_more"):
            break

        next_cursor = data.get("next_cursor")

        if not next_cursor:
            break

        payload["start_cursor"] = next_cursor

    return results


@st.cache_data(ttl=300)
def get_project_options():
    pages = query_notion_data_source(
        NOTION_PROJECTS_DATA_SOURCE_ID
    )

    projects = []

    for page in pages:
        properties = page.get("properties", {})

        project_number = ""

        for property_name in [
            "Number",
            "Project Number",
            "Project #",
        ]:
            project_number = get_property_plain_text(
                properties.get(property_name, {})
            )

            if project_number:
                break

        if not project_number:
            continue

        project_name = ""

        for property_name in [
            "Project Name",
            "Name",
        ]:
            project_name = get_property_plain_text(
                properties.get(property_name, {})
            )

            if project_name:
                break

        projects.append(
            {
                "number": project_number.strip(),
                "name": project_name.strip(),
            }
        )

    unique_projects = {}

    for project in projects:
        unique_projects[project["number"]] = project

    projects = list(unique_projects.values())

    projects.sort(
        key=lambda item: item["number"].casefold()
    )

    return projects


# =========================================================
# AML / SUPABASE HELPERS
# =========================================================

def get_item_library():
    """
    Reads previously entered AML items and builds:
    Group -> list of Descriptions
    """

    try:
        response = (
            supabase
            .table("aml_item")
            .select("group_name,description")
            .order("group_name")
            .execute()
        )

        rows = response.data or []

    except Exception:
        return {}

    library = {}

    for row in rows:
        group_name = (
            row.get("group_name")
            or ""
        ).strip()

        description = (
            row.get("description")
            or ""
        ).strip()

        if not group_name or not description:
            continue

        library.setdefault(
            group_name,
            set()
        ).add(description)

    return {
        group_name: sorted(
            descriptions,
            key=str.casefold
        )
        for group_name, descriptions
        in sorted(
            library.items(),
            key=lambda item: item[0].casefold()
        )
    }


def get_recent_amls(
    project_number=None,
    limit=100
):
    try:
        query = (
            supabase
            .table("aml")
            .select(
                "id,project_number,building_system,include_with,"
                "approved_by,aml_date,date_required_on_job,"
                "approved_date,special_pricing,special_pricing_n,"
                "branch,created_by,created_at"
            )
        )

        if project_number:
            query = query.eq(
                "project_number",
                project_number
            )

        response = (
            query
            .order("id", desc=True)
            .limit(limit)
            .execute()
        )

        return response.data or []

    except Exception:
        return []


def get_aml_items(aml_id):
    try:
        response = (
            supabase
            .table("aml_item")
            .select(
                "id,aml_id,total,ship,remaining,unit,"
                "group_name,description"
            )
            .eq("aml_id", aml_id)
            .order("id")
            .execute()
        )

        return response.data or []

    except Exception:
        return []


def save_aml(
    project_number,
    building_system,
    include_with,
    approved_by,
    aml_date,
    date_required_on_job,
    approved_date,
    special_pricing,
    special_pricing_n,
    items
):
    created_by = (
        st.session_state.get("user_name")
        or st.session_state.get("user_email")
        or ""
    )

    branch = (
        st.session_state.get("user_branch")
        or ""
    )

    header_payload = {
        "project_number": project_number,
        "building_system": building_system or None,
        "include_with": include_with or None,
        "approved_by": approved_by or None,
        "aml_date": aml_date.isoformat(),
        "date_required_on_job": (
            date_required_on_job.isoformat()
            if date_required_on_job
            else None
        ),
        "approved_date": (
            approved_date.isoformat()
            if approved_date
            else None
        ),
        "special_pricing": special_pricing,
        "special_pricing_n": (
            special_pricing_n.strip()
            if special_pricing
            and special_pricing_n.strip()
            else None
        ),
        "branch": branch or None,
        "created_by": created_by or None,
    }

    created_aml_id = None

    try:
        header_response = (
            supabase
            .table("aml")
            .insert(header_payload)
            .execute()
        )

        if not header_response.data:
            return (
                False,
                None,
                "The AML header could not be created."
            )

        created_aml_id = header_response.data[0]["id"]

        item_payload = []

        for item in items:
            item_payload.append(
                {
                    "aml_id": created_aml_id,
                    "total": item["Total"],
                    "ship": item["Ship"],
                    "unit": item["Unit"],
                    "group_name": item["Group"],
                    "description": item["Description"],
                }
            )

        if item_payload:
            item_response = (
                supabase
                .table("aml_item")
                .insert(item_payload)
                .execute()
            )

            if not item_response.data:
                raise RuntimeError(
                    "The AML items could not be created."
                )

        return (
            True,
            created_aml_id,
            None
        )

    except Exception as exc:
        # Avoid leaving an empty AML header if item insertion fails.
        if created_aml_id is not None:
            try:
                (
                    supabase
                    .table("aml")
                    .delete()
                    .eq("id", created_aml_id)
                    .execute()
                )
            except Exception:
                pass

        return (
            False,
            None,
            str(exc)
        )



def update_existing_aml(
    aml_id,
    building_system,
    include_with,
    approved_by,
    aml_date,
    date_required_on_job,
    approved_date,
    special_pricing,
    special_pricing_n,
    edited_items,
    original_item_ids
):
    header_payload = {
        "building_system": building_system.strip() or None,
        "include_with": include_with.strip() or None,
        "approved_by": approved_by.strip() or None,
        "aml_date": aml_date.isoformat(),
        "date_required_on_job": (
            date_required_on_job.isoformat()
            if date_required_on_job else None
        ),
        "approved_date": (
            approved_date.isoformat()
            if approved_date else None
        ),
        "special_pricing": special_pricing,
        "special_pricing_n": (
            special_pricing_n.strip()
            if special_pricing and special_pricing_n.strip()
            else None
        ),
    }

    try:
        (
            supabase.table("aml")
            .update(header_payload)
            .eq("id", aml_id)
            .execute()
        )

        current_existing_ids = set()
        new_item_payloads = []

        for item in edited_items:
            item_id = item.get("Item ID")

            if pd.isna(item_id):
                item_id = None

            total_value = float(
                item.get("Total")
                if item.get("Total") is not None
                and not pd.isna(item.get("Total"))
                else 0
            )

            ship_value = float(
                item.get("Ship")
                if item.get("Ship") is not None
                and not pd.isna(item.get("Ship"))
                else 0
            )

            if total_value < 0:
                return False, "Total cannot be negative."

            if ship_value < 0:
                return False, "Ship cannot be negative."

            if ship_value > total_value:
                return False, "Ship cannot be greater than Total."

            unit_value = str(
                item.get("Unit") or "Unit"
            ).strip()

            if unit_value not in {
                "Ft",
                "Inc",
                "Unit",
            }:
                return (
                    False,
                    "Unit must be Ft, Inc, or Unit."
                )

            group_value = str(
                item.get("Group") or ""
            ).strip()

            description_value = str(
                item.get("Description") or ""
            ).strip()

            # Ignore a completely blank newly-added row.
            if (
                not item_id
                and not group_value
                and not description_value
                and total_value == 0
                and ship_value == 0
            ):
                continue

            if not group_value:
                return False, "Group cannot be empty."

            if not description_value:
                return False, "Description cannot be empty."

            item_payload = {
                "total": total_value,
                "ship": ship_value,
                "unit": unit_value,
                "group_name": group_value,
                "description": description_value,
            }

            if item_id:
                item_id = int(item_id)

                current_existing_ids.add(
                    item_id
                )

                (
                    supabase
                    .table("aml_item")
                    .update(item_payload)
                    .eq("id", item_id)
                    .eq("aml_id", aml_id)
                    .execute()
                )

            else:
                new_item_payloads.append(
                    {
                        "aml_id": aml_id,
                        **item_payload,
                    }
                )

        # Delete items removed from the editable table.
        deleted_item_ids = (
            set(original_item_ids)
            - current_existing_ids
        )

        for deleted_item_id in deleted_item_ids:
            (
                supabase
                .table("aml_item")
                .delete()
                .eq("id", deleted_item_id)
                .eq("aml_id", aml_id)
                .execute()
            )

        # Insert new rows added in the editable table.
        if new_item_payloads:
            (
                supabase
                .table("aml_item")
                .insert(new_item_payloads)
                .execute()
            )

        return True, None

    except Exception as exc:
        return False, str(exc)


def parse_date_value(value):
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except Exception:
        return None


# =========================================================
# PDF REPORT HELPERS
# =========================================================

def format_us_date(value):
    if not value:
        return ""

    if isinstance(value, date):
        return value.strftime("%m/%d/%Y")

    try:
        parsed = datetime.fromisoformat(
            str(value).replace("Z", "+00:00")
        )
        return parsed.strftime("%m/%d/%Y")
    except Exception:
        try:
            parsed = datetime.strptime(
                str(value),
                "%Y-%m-%d"
            )
            return parsed.strftime("%m/%d/%Y")
        except Exception:
            return str(value)


def format_quantity(value):
    if value is None:
        return ""

    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)

    if number.is_integer():
        return str(int(number))

    return (
        f"{number:.2f}"
        .rstrip("0")
        .rstrip(".")
    )


def format_quantity_with_unit(
    value,
    unit
):
    quantity_text = format_quantity(
        value
    )

    normalized_unit = (
        str(unit or "Unit")
        .strip()
    )

    if normalized_unit == "Unit":
        return quantity_text

    return (
        f"{quantity_text} "
        f"{normalized_unit}"
    ).strip()


def wrap_pdf_text(
    text,
    font_name,
    font_size,
    max_width
):
    text = str(text or "").strip()

    if not text:
        return [""]

    words = text.split()
    lines = []
    current = ""

    for word in words:
        candidate = (
            f"{current} {word}".strip()
        )

        if (
            stringWidth(
                candidate,
                font_name,
                font_size
            )
            <= max_width
        ):
            current = candidate
        else:
            if current:
                lines.append(current)

            current = word

    if current:
        lines.append(current)

    return lines or [""]


def get_project_name_by_number(
    project_number,
    projects
):
    target = str(
        project_number or ""
    ).strip()

    for project in projects:
        if (
            str(project.get("number", "")).strip()
            == target
        ):
            return (
                project.get("name")
                or ""
            ).strip()

    return ""


def build_aml_pdf(
    aml,
    items,
    project_name=""
):
    """
    Creates the final ANTICIPATED MATERIAL LIST PDF.
    The internal AML ID and Group are intentionally not
    displayed in the report.
    """

    buffer = BytesIO()

    page_width, page_height = letter

    pdf = canvas.Canvas(
        buffer,
        pagesize=letter
    )

    left = 22
    right = page_width - 22
    top = page_height - 20

    table_left = left
    table_right = right

    # Compact row height to resemble the supplied AML form.
    base_row_height = 18

    # Leave room for header on every page.
    table_start_y = page_height - 185
    bottom_margin = 28

    # Determine how many rows fit per page.
    available_height = (
        table_start_y
        - bottom_margin
        - base_row_height
    )

    rows_per_page = max(
        1,
        int(
            available_height
            // base_row_height
        )
    )

    # Build the PDF display list with one blank row
    # between each material Group.
    pdf_items = []
    previous_group = None

    for item in items:
        current_group = (
            item.get("group_name")
            or ""
        ).strip()

        if (
            previous_group is not None
            and current_group != previous_group
        ):
            pdf_items.append(None)

        pdf_items.append(item)
        previous_group = current_group

    total_pages = max(
        1,
        ceil(
            len(pdf_items)
            / rows_per_page
        )
    )

    branch = (
        aml.get("branch")
        or st.session_state.get("user_branch")
        or ""
    )

    originator = (
        aml.get("created_by")
        or ""
    )

    include_with = (
        aml.get("include_with")
        or ""
    )

    approved_by = (
        aml.get("approved_by")
        or ""
    )

    special_pricing = bool(
        aml.get("special_pricing")
    )

    special_pricing_n = (
        aml.get("special_pricing_n")
        or ""
    )

    for page_index in range(total_pages):
        page_number = page_index + 1

        # -------------------------------------------------
        # OUTER HEADER BOX
        # -------------------------------------------------
        header_bottom = page_height - 160

        pdf.setLineWidth(0.7)

        pdf.rect(
            left,
            header_bottom,
            right - left,
            top - header_bottom
        )

        # Title
        pdf.setFont(
            "Helvetica-Bold",
            17
        )

        pdf.drawCentredString(
            page_width / 2,
            top - 18,
            "ANTICIPATED MATERIAL LIST"
        )

        # Header columns
        middle_x = page_width * 0.61

        pdf.setFont(
            "Helvetica",
            9
        )

        line1_y = top - 37
        line_gap = 14

        pdf.drawString(
            left + 6,
            line1_y,
            f"Branch: {branch}"
        )

        pdf.drawString(
            left + 210,
            line1_y,
            f"Date: {format_us_date(aml.get('aml_date'))}"
        )

        pdf.drawString(
            middle_x,
            line1_y,
            f"Page: {page_number:02d} of {total_pages:02d}"
        )

        job_name = project_name or ""

        pdf.drawString(
            left + 6,
            line1_y - line_gap,
            f"Job Name: {job_name}"
        )

        pdf.drawString(
            middle_x,
            line1_y - line_gap,
            f"Job #: {aml.get('project_number') or ''}"
        )

        pdf.drawString(
            left + 6,
            line1_y - (2 * line_gap),
            "Building/System: "
            f"{aml.get('building_system') or ''}"
        )

        pdf.drawString(
            left + 6,
            line1_y - (3 * line_gap),
            "Date required on Job: "
            f"{format_us_date(aml.get('date_required_on_job'))}"
        )

        pdf.drawString(
            middle_x,
            line1_y - (3 * line_gap),
            f"Originator: {originator}"
        )

        pdf.drawString(
            left + 6,
            line1_y - (4 * line_gap),
            f"Include with: {include_with}"
        )

        approved_date_text = (
            format_us_date(
                aml.get("approved_date")
            )
        )

        pdf.drawString(
            middle_x,
            line1_y - (4 * line_gap),
            f"Approved by: {approved_by}"
        )

        pdf.drawString(
            middle_x + 125,
            line1_y - (4 * line_gap),
            f"Date: {approved_date_text}"
        )

        pricing_text = (
            "Yes"
            if special_pricing
            else "No"
        )

        copy_text = (
            f"   Special Pricing #: {special_pricing_n}"
            if special_pricing_n
            else ""
        )

        pdf.drawString(
            left + 6,
            line1_y - (5 * line_gap),
            "Does special pricing apply? "
            f"{pricing_text}{copy_text}"
        )

        # -------------------------------------------------
        # TABLE HEADER
        # -------------------------------------------------
        y = table_start_y

        col_total = table_left + 70
        col_ship = col_total + 75
        col_remaining = col_ship + 75

        pdf.setLineWidth(0.65)

        table_header_height = 28

        pdf.rect(
            table_left,
            y - table_header_height,
            table_right - table_left,
            table_header_height
        )

        for x in [
            col_total,
            col_ship,
            col_remaining,
        ]:
            pdf.line(
                x,
                y,
                x,
                y - table_header_height
            )

        pdf.setFont(
            "Helvetica",
            8
        )

        pdf.drawCentredString(
            (table_left + col_total) / 2,
            y - 10,
            "Total"
        )
        pdf.drawCentredString(
            (table_left + col_total) / 2,
            y - 20,
            "Quantity"
        )

        pdf.drawCentredString(
            (col_total + col_ship) / 2,
            y - 10,
            "Quant. to"
        )
        pdf.drawCentredString(
            (col_total + col_ship) / 2,
            y - 20,
            "Ship"
        )

        pdf.drawCentredString(
            (col_ship + col_remaining) / 2,
            y - 10,
            "Quant."
        )
        pdf.drawCentredString(
            (col_ship + col_remaining) / 2,
            y - 20,
            "Remaining"
        )

        pdf.setFont(
            "Helvetica",
            9
        )

        pdf.drawCentredString(
            (col_remaining + table_right) / 2,
            y - 17,
            "Description"
        )

        y -= table_header_height

        start_index = (
            page_index
            * rows_per_page
        )

        end_index = min(
            start_index + rows_per_page,
            len(items)
        )

        page_items = pdf_items[
            start_index:end_index
        ]

        # Always leave some blank rows, similar to the
        # supplied printed AML form.
        minimum_visible_rows = rows_per_page

        for row_index in range(
            minimum_visible_rows
        ):
            item = (
                page_items[row_index]
                if row_index < len(page_items)
                else None
            )

            row_height = base_row_height

            pdf.rect(
                table_left,
                y - row_height,
                table_right - table_left,
                row_height
            )

            for x in [
                col_total,
                col_ship,
                col_remaining,
            ]:
                pdf.line(
                    x,
                    y,
                    x,
                    y - row_height
                )

            if item:
                pdf.setFont(
                    "Helvetica",
                    8.5
                )

                pdf.drawCentredString(
                    (table_left + col_total) / 2,
                    y - 12,
                    format_quantity_with_unit(
                        item.get("total"),
                        item.get("unit")
                    )
                )

                pdf.drawCentredString(
                    (col_total + col_ship) / 2,
                    y - 12,
                    format_quantity_with_unit(
                        item.get("ship"),
                        item.get("unit")
                    )
                )

                pdf.drawCentredString(
                    (col_ship + col_remaining) / 2,
                    y - 12,
                    format_quantity_with_unit(
                        item.get("remaining"),
                        item.get("unit")
                    )
                )

                description = (
                    item.get("description")
                    or ""
                )

                description_lines = (
                    wrap_pdf_text(
                        description,
                        "Helvetica",
                        8.5,
                        table_right
                        - col_remaining
                        - 12
                    )
                )

                # One compact printed row, matching the
                # supplied form. Very long descriptions
                # are clipped to two short lines.
                description_lines = (
                    description_lines[:2]
                )

                if len(description_lines) == 1:
                    pdf.drawString(
                        col_remaining + 6,
                        y - 12,
                        description_lines[0]
                    )
                else:
                    pdf.setFont(
                        "Helvetica",
                        7.5
                    )

                    pdf.drawString(
                        col_remaining + 6,
                        y - 8,
                        description_lines[0]
                    )

                    pdf.drawString(
                        col_remaining + 6,
                        y - 16,
                        description_lines[1]
                    )

            y -= row_height

        pdf.showPage()

    pdf.save()

    buffer.seek(0)
    return buffer.getvalue()


# =========================================================
# PAGE HEADER
# =========================================================

st.title(
    "📦 AML - Anticipated Material List"
)

st.caption(
    "Create an Anticipated Material List and associate "
    "multiple material items with a project."
)

st.divider()


# =========================================================
# PROJECT / AML INFORMATION
# =========================================================

st.subheader(
    "1. AML Information"
)

projects = get_project_options()

if not projects:
    st.error(
        "No projects were found in the Projects database. "
        "Please verify NOTION_PROJECTS_DATA_SOURCE_ID."
    )
    st.stop()


project_label_lookup = {
    (
        f"{project['number']} - {project['name']}"
        if project["name"]
        else project["number"]
    ): project["number"]
    for project in projects
}

project_labels = list(
    project_label_lookup.keys()
)

col1, col2 = st.columns(2)

with col1:
    selected_project_label = st.selectbox(
        "Project",
        options=project_labels,
        index=None,
        placeholder="Select a project...",
        key="aml_project_select"
    )

    building_system = st.text_input(
        "Building/System",
        placeholder="Example: Bldg 100 / Wet System"
    )

    include_with = st.text_input(
        "Include With"
    )

    aml_date = st.date_input(
        "Date",
        value=date.today()
    )

    set_required_date = st.checkbox(
        "Set Date Required on Job"
    )

    date_required_on_job = None

    if set_required_date:
        date_required_on_job = st.date_input(
            "Date Required on Job",
            value=date.today()
        )

with col2:
    approved_by = st.text_input(
        "Approved by"
    )

    set_approved_date = st.checkbox(
        "Set Approved Date"
    )

    approved_date = None

    if set_approved_date:
        approved_date = st.date_input(
            "Approved Date",
            value=date.today()
        )

    special_pricing = st.checkbox(
        "Special Pricing"
    )

    special_pricing_n = ""

    if special_pricing:
        special_pricing_n = st.text_input(
            "Special Pricing #"
        )


st.divider()

# =========================================================
# CLEAR OLD DRAFT WHEN NO PROJECT IS SELECTED
# =========================================================
#
# Streamlit keeps session_state while navigating between pages.
# Without this reset, draft material items from a previous AML can
# reappear when the user comes back to this page.
#
# While no Project is selected, the draft must always be empty.
if not selected_project_label:
    st.session_state.aml_draft_items = []

    # Also clear any pending item-entry reset flag.
    st.session_state.pop(
        "aml_reset_item_entry",
        None
    )


# =========================================================
# ITEM ENTRY
# =========================================================

st.subheader(
    "2. Material Items"
)

# Clear the item-entry fields after a material is successfully
# added to the draft AML. This runs before the widgets are
# instantiated, which avoids Streamlit widget-state conflicts.
if st.session_state.pop(
    "aml_reset_item_entry",
    False
):
    for widget_key in [
        "aml_group_select",
        "aml_new_group",
        "aml_first_group",
        "aml_description_select",
        "aml_new_description",
        "aml_description_text",
        "aml_item_total",
        "aml_item_ship",
        "aml_item_unit",
    ]:
        st.session_state.pop(
            widget_key,
            None
        )

item_library = get_item_library()

existing_groups = list(
    item_library.keys()
)

if existing_groups:
    group_options = (
        existing_groups
        + ["➕ Add New Group"]
    )

    selected_group_option = st.selectbox(
        "Group",
        options=group_options,
        index=None,
        placeholder="Select a Group...",
        key="aml_group_select"
    )

    if selected_group_option == "➕ Add New Group":
        group_name = st.text_input(
            "New Group",
            key="aml_new_group"
        ).strip()
    elif selected_group_option:
        group_name = selected_group_option
    else:
        group_name = ""

else:
    st.info(
        "No previous Groups exist yet. "
        "Create the first Group below."
    )

    group_name = st.text_input(
        "Group",
        key="aml_first_group"
    ).strip()


description = ""

if group_name:
    descriptions = item_library.get(
        group_name,
        []
    )

    if descriptions:
        description_options = (
            descriptions
            + ["➕ Add New Description"]
        )

        selected_description_option = (
            st.selectbox(
                "Description",
                options=description_options,
                key="aml_description_select"
            )
        )

        if (
            selected_description_option
            == "➕ Add New Description"
        ):
            description = st.text_input(
                "New Description",
                key="aml_new_description"
            ).strip()
        else:
            description = (
                selected_description_option
            )

    else:
        description = st.text_input(
            "Description",
            key="aml_description_text"
        ).strip()

else:
    st.caption(
        "Select or create a Group first. "
        "The Description field will then be available."
    )


qty_col1, qty_col2, qty_col3, qty_col4 = (
    st.columns(4)
)

with qty_col1:
    total = st.number_input(
        "Total",
        min_value=0.0,
        value=0.0,
        step=1.0,
        format="%.2f",
        key="aml_item_total"
    )

with qty_col2:
    ship = st.number_input(
        "Ship",
        min_value=0.0,
        value=0.0,
        step=1.0,
        format="%.2f",
        key="aml_item_ship"
    )

with qty_col3:
    remaining = max(
        float(total) - float(ship),
        0.0
    )

    st.metric(
        "Remaining",
        f"{remaining:,.2f}"
    )

with qty_col4:
    unit = st.selectbox(
        "Unit",
        options=[
            "Ft",
            "Inc",
            "Unit",
        ],
        index=2,
        key="aml_item_unit"
    )


if st.button(
    "➕ Add Item",
    use_container_width=True,
    type="secondary"
):
    if not selected_project_label:
        st.warning(
            "Please select a Project before adding materials."
        )

    elif not group_name:
        st.warning(
            "Please select or enter a Group."
        )

    elif not description:
        st.warning(
            "Please select or enter a Description."
        )

    elif total <= 0:
        st.warning(
            "Total must be greater than zero."
        )

    elif ship > total:
        st.warning(
            "Ship cannot be greater than Total."
        )

    else:
        st.session_state.aml_draft_items.append(
            {
                "Total": float(total),
                "Ship": float(ship),
                "Remaining": remaining,
                "Unit": unit,
                "Group": group_name,
                "Description": description,
            }
        )

        st.session_state.aml_reset_item_entry = (
            True
        )

        st.success(
            "Item added to the AML."
        )

        st.rerun()


# =========================================================
# DRAFT ITEMS
# =========================================================

st.markdown(
    "#### AML Items"
)

if not selected_project_label:
    st.info(
        "Select a Project to start a new AML material list."
    )

elif not st.session_state.aml_draft_items:
    st.info(
        "No items have been added yet."
    )

else:
    st.dataframe(
        st.session_state.aml_draft_items,
        use_container_width=True,
        hide_index=True,
        column_order=[
            "Total",
            "Ship",
            "Remaining",
            "Unit",
            "Group",
            "Description",
        ],
        column_config={
            "Total": st.column_config.NumberColumn(
                "Total",
                format="%.2f"
            ),
            "Ship": st.column_config.NumberColumn(
                "Ship",
                format="%.2f"
            ),
            "Remaining": st.column_config.NumberColumn(
                "Remaining",
                format="%.2f"
            ),
            "Unit": st.column_config.TextColumn(
                "Unit",
                width="small"
            ),
            "Group": st.column_config.TextColumn(
                "Group"
            ),
            "Description": st.column_config.TextColumn(
                "Description",
                width="large"
            ),
        }
    )

    st.markdown(
        "##### Remove Item"
    )

    for index, item in enumerate(
        st.session_state.aml_draft_items
    ):
        col_text, col_button = st.columns(
            [8, 1]
        )

        with col_text:
            st.write(
                f"{index + 1}. "
                f"{item['Group']} — "
                f"{item['Description']}"
            )

        with col_button:
            if st.button(
                "🗑️",
                key=f"remove_aml_item_{index}",
                help="Remove item"
            ):
                st.session_state.aml_draft_items.pop(
                    index
                )
                st.rerun()


st.divider()


# =========================================================
# SAVE AML
# =========================================================

st.subheader(
    "3. Save AML"
)

save_col1, save_col2 = st.columns(
    [3, 1]
)

with save_col1:
    save_aml_button = st.button(
        "💾 Save AML",
        use_container_width=True,
        type="primary"
    )

with save_col2:
    clear_button = st.button(
        "Clear Draft",
        use_container_width=True
    )


if clear_button:
    st.session_state.aml_draft_items = []
    st.rerun()


if save_aml_button:
    if not selected_project_label:
        st.warning(
            "Please select a Project."
        )

    elif not building_system.strip():
        st.warning(
            "Please enter Building/System."
        )

    elif not st.session_state.aml_draft_items:
        st.warning(
            "Please add at least one material item."
        )

    elif (
        approved_date
        and approved_date < aml_date
    ):
        st.warning(
            "Approved Date cannot be earlier than Date."
        )

    else:
        project_number = (
            project_label_lookup[
                selected_project_label
            ]
        )

        success, aml_id, error = save_aml(
            project_number=project_number,
            building_system=building_system.strip(),
            include_with=include_with.strip(),
            approved_by=approved_by.strip(),
            aml_date=aml_date,
            date_required_on_job=date_required_on_job,
            approved_date=approved_date,
            special_pricing=special_pricing,
            special_pricing_n=special_pricing_n,
            items=st.session_state.aml_draft_items,
        )

        if success:
            st.session_state.aml_last_saved_id = (
                aml_id
            )

            st.session_state.aml_draft_items = []

            st.success(
                "AML saved successfully."
            )

            st.info(
                "Internal AML reference: "
                f"{aml_id}. "
                "This number is used only to link "
                "the AML to its material items."
            )

            st.cache_data.clear()

        else:
            st.error(
                "Unable to save the AML."
            )

            if error:
                st.caption(error)


st.divider()


# =========================================================
# EXISTING AMLs
# =========================================================

with st.expander(
    "📚 Existing AMLs",
    expanded=False
):
    if not selected_project_label:
        st.info(
            "Select a Project at the top of the page "
            "to view its existing AMLs."
        )

    else:
        selected_project_number = (
            project_label_lookup[
                selected_project_label
            ]
        )

        recent_amls = get_recent_amls(
            project_number=
                selected_project_number
        )

        if not recent_amls:
            st.info(
                "No AML records have been created "
                "for the selected Project."
            )

        else:
            aml_label_lookup = {}

            for aml in recent_amls:
                aml_id = aml["id"]

                building_system_label = (
                    aml.get("building_system")
                    or "No Building/System"
                )

                label = (
                    f"{aml['project_number']} "
                    f"| {building_system_label} "
                    f"| {aml.get('aml_date') or 'No Date'} "
                    f"| AML {aml_id}"
                )

                aml_label_lookup[label] = aml

            selected_aml_label = st.selectbox(
                "Select AML",
                options=list(
                    aml_label_lookup.keys()
                ),
                index=None,
                placeholder="Select an AML..."
            )

            if selected_aml_label:
                selected_aml = (
                    aml_label_lookup[
                        selected_aml_label
                    ]
                )

                st.markdown("#### Edit AML")

                edit_col1, edit_col2, edit_col3 = st.columns(3)

                with edit_col1:
                    st.text_input(
                        "Project Number",
                        value=str(selected_aml["project_number"]),
                        disabled=True,
                        key=f"edit_project_number_{selected_aml['id']}"
                    )

                    edit_building_system = st.text_input(
                        "Building/System",
                        value=selected_aml.get("building_system") or "",
                        key=f"edit_building_system_{selected_aml['id']}"
                    )

                    edit_aml_date = st.date_input(
                        "Date",
                        value=(
                            parse_date_value(selected_aml.get("aml_date"))
                            or date.today()
                        ),
                        key=f"edit_aml_date_{selected_aml['id']}"
                    )

                    current_required_date = parse_date_value(
                        selected_aml.get("date_required_on_job")
                    )

                    edit_has_required_date = st.checkbox(
                        "Set Date Required on Job",
                        value=current_required_date is not None,
                        key=f"edit_has_required_date_{selected_aml['id']}"
                    )

                    edit_required_date = None
                    if edit_has_required_date:
                        edit_required_date = st.date_input(
                            "Date Required on Job",
                            value=current_required_date or date.today(),
                            key=f"edit_required_date_{selected_aml['id']}"
                        )

                with edit_col2:
                    edit_include_with = st.text_input(
                        "Include With",
                        value=selected_aml.get("include_with") or "",
                        key=f"edit_include_with_{selected_aml['id']}"
                    )

                    edit_approved_by = st.text_input(
                        "Approved by",
                        value=selected_aml.get("approved_by") or "",
                        key=f"edit_approved_by_{selected_aml['id']}"
                    )

                    current_approved_date = parse_date_value(
                        selected_aml.get("approved_date")
                    )

                    edit_has_approved_date = st.checkbox(
                        "Set Approved Date",
                        value=current_approved_date is not None,
                        key=f"edit_has_approved_date_{selected_aml['id']}"
                    )

                    edit_approved_date = None
                    if edit_has_approved_date:
                        edit_approved_date = st.date_input(
                            "Approved Date",
                            value=current_approved_date or date.today(),
                            key=f"edit_approved_date_{selected_aml['id']}"
                        )

                with edit_col3:
                    edit_special_pricing = st.checkbox(
                        "Special Pricing",
                        value=bool(selected_aml.get("special_pricing")),
                        key=f"edit_special_pricing_{selected_aml['id']}"
                    )

                    edit_special_pricing_n = ""
                    if edit_special_pricing:
                        edit_special_pricing_n = st.text_input(
                            "Special Pricing #",
                            value=selected_aml.get("special_pricing_n") or "",
                            key=f"edit_special_pricing_n_{selected_aml['id']}"
                        )

                selected_items = get_aml_items(selected_aml["id"])

                original_item_ids = {
                    int(item["id"])
                    for item in selected_items
                    if item.get("id") is not None
                }

                edited_item_rows = []

                if selected_items:
                    item_rows = [
                        {
                            "Item ID": item["id"],
                            "Total": item["total"],
                            "Ship": item["ship"],
                            "Remaining": item["remaining"],
                            "Unit": item.get("unit") or "Unit",
                            "Group": item["group_name"],
                            "Description": item["description"],
                        }
                        for item in selected_items
                    ]

                    item_df = pd.DataFrame(item_rows)

                    edited_item_df = st.data_editor(
                        item_df,
                        use_container_width=True,
                        hide_index=True,
                        num_rows="dynamic",
                        disabled=["Item ID", "Remaining"],
                        column_order=[
                            "Total",
                            "Ship",
                            "Remaining",
                            "Unit",
                            "Group",
                            "Description",
                        ],
                        column_config={
                            "Item ID": None,
                            "Total": st.column_config.NumberColumn(
                                "Total", min_value=0.0, step=1.0, format="%.2f"
                            ),
                            "Ship": st.column_config.NumberColumn(
                                "Ship", min_value=0.0, step=1.0, format="%.2f"
                            ),
                            "Remaining": st.column_config.NumberColumn(
                                "Remaining", format="%.2f"
                            ),
                            "Unit": st.column_config.SelectboxColumn(
                                "Unit",
                                options=["Ft", "Inc", "Unit"],
                                required=True,
                            ),
                            "Group": st.column_config.TextColumn(
                                "Group", required=True
                            ),
                            "Description": st.column_config.TextColumn(
                                "Description", required=True, width="large"
                            ),
                        },
                        key=f"edit_aml_items_{selected_aml['id']}"
                    )

                    edited_item_rows = edited_item_df.to_dict(orient="records")
                else:
                    empty_item_df = pd.DataFrame(
                        columns=[
                            "Item ID",
                            "Total",
                            "Ship",
                            "Remaining",
                            "Unit",
                            "Group",
                            "Description",
                        ]
                    )

                    edited_item_df = st.data_editor(
                        empty_item_df,
                        use_container_width=True,
                        hide_index=True,
                        num_rows="dynamic",
                        disabled=[
                            "Item ID",
                            "Remaining",
                        ],
                        column_order=[
                            "Total",
                            "Ship",
                            "Remaining",
                            "Unit",
                            "Group",
                            "Description",
                        ],
                        column_config={
                            "Item ID": None,
                            "Total":
                                st.column_config.NumberColumn(
                                    "Total",
                                    min_value=0.0,
                                    step=1.0,
                                    format="%.2f",
                                ),
                            "Ship":
                                st.column_config.NumberColumn(
                                    "Ship",
                                    min_value=0.0,
                                    step=1.0,
                                    format="%.2f",
                                ),
                            "Remaining":
                                st.column_config.NumberColumn(
                                    "Remaining",
                                    format="%.2f",
                                ),
                            "Unit":
                                st.column_config.SelectboxColumn(
                                    "Unit",
                                    options=[
                                        "Ft",
                                        "Inc",
                                        "Unit",
                                    ],
                                    default="Unit",
                                    required=True,
                                ),
                            "Group":
                                st.column_config.TextColumn(
                                    "Group",
                                    required=True,
                                ),
                            "Description":
                                st.column_config.TextColumn(
                                    "Description",
                                    required=True,
                                    width="large",
                                ),
                        },
                        key=(
                            "edit_aml_items_"
                            f"{selected_aml['id']}"
                        ),
                    )

                    edited_item_rows = (
                        edited_item_df.to_dict(
                            orient="records"
                        )
                    )

                st.caption(
                    "Use the + row at the bottom to add items. "
                    "Use the row controls to remove items. "
                    "Remaining is calculated automatically "
                    "from Total minus Ship."
                )

                if st.button(
                    "💾 Save Changes",
                    key=f"save_aml_changes_{selected_aml['id']}",
                    use_container_width=True,
                    type="primary"
                ):
                    if not edit_building_system.strip():
                        st.warning("Building/System cannot be empty.")
                    elif edit_approved_date and edit_approved_date < edit_aml_date:
                        st.warning("Approved Date cannot be earlier than Date.")
                    else:
                        update_success, update_error = update_existing_aml(
                            aml_id=selected_aml["id"],
                            building_system=edit_building_system,
                            include_with=edit_include_with,
                            approved_by=edit_approved_by,
                            aml_date=edit_aml_date,
                            date_required_on_job=edit_required_date,
                            approved_date=edit_approved_date,
                            special_pricing=edit_special_pricing,
                            special_pricing_n=edit_special_pricing_n,
                            edited_items=edited_item_rows,
                            original_item_ids=original_item_ids,
                        )

                        if update_success:
                            st.session_state.aml_pdf_bytes = None
                            st.session_state.aml_pdf_filename = None
                            st.session_state.aml_pdf_source_id = None
                            st.success("AML updated successfully.")
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error("Unable to update the AML.")
                            if update_error:
                                st.caption(update_error)


                st.divider()

                st.markdown(
                    "#### 📄 Final AML Report"
                )

                st.caption(
                    "Generate the final Anticipated Material List "
                    "in PDF format."
                )

                project_name = (
                    get_project_name_by_number(
                        selected_aml[
                            "project_number"
                        ],
                        projects
                    )
                )

                if st.button(
                    "📄 Generate PDF",
                    key=(
                        "generate_aml_pdf_"
                        f"{selected_aml['id']}"
                    ),
                    use_container_width=True
                ):
                    if not selected_items:
                        st.warning(
                            "This AML has no material items."
                        )
                    else:
                        try:
                            pdf_bytes = build_aml_pdf(
                                selected_aml,
                                selected_items,
                                project_name=project_name
                            )

                            safe_project_number = (
                                str(
                                    selected_aml[
                                        "project_number"
                                    ]
                                )
                                .replace("/", "-")
                                .replace("\\\\", "-")
                                .replace(" ", "_")
                            )

                            filename = (
                                "AML_"
                                f"{safe_project_number}"
                                ".pdf"
                            )

                            st.session_state.aml_pdf_bytes = (
                                pdf_bytes
                            )
                            st.session_state.aml_pdf_filename = (
                                filename
                            )
                            st.session_state.aml_pdf_source_id = (
                                selected_aml["id"]
                            )

                            st.success(
                                "PDF generated successfully."
                            )

                        except Exception as exc:
                            st.error(
                                "Unable to generate the PDF."
                            )
                            st.exception(exc)

                if (
                    st.session_state.aml_pdf_bytes
                    and st.session_state.aml_pdf_source_id
                    == selected_aml["id"]
                ):
                    st.download_button(
                        "⬇️ Download AML PDF",
                        data=st.session_state.aml_pdf_bytes,
                        file_name=(
                            st.session_state.aml_pdf_filename
                            or "AML.pdf"
                        ),
                        mime="application/pdf",
                        use_container_width=True,
                        type="primary"
                    )


st.divider()

# =========================================================
# AML PROCEDURES / INSTRUCTIONS
# =========================================================

with st.expander(
    "📋 AML Procedures and Material Guidelines",
    expanded=False
):
    st.markdown(
        """
### AML Procedures

- Submit to QFS at least **5 to 6 weeks prior to ship date**.
- All items listed will not be charged to job cost until the stocklist has been processed.
- Do not order any special material without getting it approved by the Owner, Engineer, and/or AHJ.
- QFS will review it and highlight non-inventory materials only.
- The form will then be returned to the designer.
- When non-inventory materials are required to be shipped, include the number of items to ship and attach a copy with the stocklist and submit it to QFS.
- Designer is responsible for keeping track of AML Quantities Shipped and Quantities Remaining.
- For long-term projects, it is recommended to provide multiple AMLs with corresponding required dates (overhead, in-rack, fire pump, risers, etc.). This will help prevent the accumulation of excessive materials and avoid any potential delays in material procurement.
- AMLs sent to QFS less than **1 week before the stocklist due date will not be processed**.

### List the following material

- All non-standard pipe *(note: Schedule 10 & 40 in 21'-0" lengths are standard)*.
- All special-cut lengths of pipe.
- All galvanized products (pipe and fittings).
- Large quantities of sprinkler heads (in excess of 1,000).
- Sprinkler heads with special finishes (i.e., polished chrome, painted, etc.).
- Special Sprinklers.
- All cabinets.
- Pressure regulating and large relief valves (6" and larger).
- All non-stocked or non-inventory products *(note: no part no. available)*.
- Special gaskets for grooved special applications.
- All newly developed products.
- All products 8" or larger.
- All Kunkle relief valves.
- 1-1/2" – 8" S/7, S/10 and S/40 Pipe *(5–6 weeks)*.
- Special-sized hose cabinets & access panels *(2 months)*.

### Notes

Mill runs for special length pipe require a minimum of **500 pieces per order** and have an estimated **8-week lead time**.

Use the **QFS Quell material quote form** given to Sales at the estimating phase when creating an AML for Quell materials.
        """
    )

