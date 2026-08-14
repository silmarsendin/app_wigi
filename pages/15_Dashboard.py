import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import pydeck as pdk
import time

from datetime import date, datetime


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Dashboard",
    page_icon="📊",
    layout="wide",
)


# =========================================================
# ACCESS CONTROL
# =========================================================

if not st.session_state.get(
    "authenticated",
    False,
):

    st.error(
        "You must be signed in to access this page."
    )

    st.stop()


logged_user_role = (
    st.session_state.get(
        "user_role"
    )
    or ""
)


if (
    str(
        logged_user_role
    )
    .strip()
    .casefold()
    != "manager"
):

    st.error(
        "This page is available only to Managers."
    )

    st.stop()


logged_user_email = (
    st.session_state.get(
        "user_email"
    )
    or ""
).strip().lower()


# =========================================================
# SETTINGS
# =========================================================

NOTION_TOKEN = (
    st.secrets[
        "NOTION_TOKEN"
    ]
)


NOTION_USERS_DATA_SOURCE_ID = (
    st.secrets[
        "NOTION_USERS_DATA_SOURCE_ID"
    ]
)


NOTION_PROJECTS_DATA_SOURCE_ID = (
    st.secrets.get(
        "NOTION_PROJECTS_DATA_SOURCE_ID"
    )
    or st.secrets.get(
        "PROJECTS_DATA_SOURCE_ID"
    )
    or st.secrets.get(
        "NOTION_PROJECTS_DATABASE_ID"
    )
)


NOTION_PERMIT_ID = (
    st.secrets.get(
        "NOTION_PERMIT_DATA_SOURCE_ID"
    )
    or st.secrets.get(
        "NOTION_PERMIT_DATABASE_ID"
    )
    or st.secrets.get(
        "PERMIT_DATA_SOURCE_ID"
    )
    or st.secrets.get(
        "PERMIT_DATABASE_ID"
    )
)


NOTION_HEADERS = {
    "Authorization":
        f"Bearer {NOTION_TOKEN}",

    "Content-Type":
        "application/json",

    "Notion-Version":
        "2025-09-03",
}


CACHE_TTL = 30


# =========================================================
# GENERAL HELPERS
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


def normalize_identity(
    value
):

    value = normalize_text(
        value
    )

    if not value:
        return ""

    return "".join(
        character
        for character in value
        if character.isalnum()
    )


def parse_date(
    value
):

    if not value:
        return None

    try:

        return datetime.fromisoformat(
            str(
                value
            )
            .replace(
                "Z",
                "+00:00"
            )
        ).date()

    except Exception:

        try:

            return date.fromisoformat(
                str(
                    value
                )[:10]
            )

        except Exception:

            return None


def format_date(
    value
):

    parsed = parse_date(
        value
    )

    if not parsed:
        return ""

    return parsed.strftime(
        "%m/%d/%Y"
    )


# =========================================================
# NOTION PROPERTY HELPERS
# =========================================================

def get_property_plain_text(
    prop
):

    if not prop:
        return ""


    prop_type = prop.get(
        "type"
    )


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

        if (
            isinstance(
                value,
                float
            )
            and value.is_integer()
        ):

            return str(
                int(
                    value
                )
            )

        return str(
            value
        )


    if prop_type == "formula":

        formula = prop.get(
            "formula",
            {}
        )

        formula_type = formula.get(
            "type"
        )

        value = formula.get(
            formula_type
        )

        if value is None:
            return ""

        if (
            formula_type == "date"
            and isinstance(
                value,
                dict
            )
        ):

            return (
                value.get(
                    "start"
                )
                or ""
            )

        return str(
            value
        )


    if prop_type == "rollup":

        rollup = prop.get(
            "rollup",
            {}
        )

        rollup_type = rollup.get(
            "type"
        )

        if rollup_type == "number":

            value = rollup.get(
                "number"
            )

            return (
                ""
                if value is None
                else str(
                    value
                )
            )

        if rollup_type == "array":

            values = []

            for item in rollup.get(
                "array",
                []
            ):

                value = (
                    get_property_plain_text(
                        item
                    )
                )

                if value:

                    values.append(
                        value
                    )

            return ", ".join(
                values
            )


    return ""


def get_checkbox(
    properties,
    property_name,
    default=False
):

    prop = properties.get(
        property_name,
        {}
    )

    if prop.get(
        "type"
    ) != "checkbox":

        return default

    return bool(
        prop.get(
            "checkbox",
            default
        )
    )


def get_number(
    properties,
    property_name,
    default=0.0
):

    prop = properties.get(
        property_name,
        {}
    )

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


def get_date_value(
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

    return date_data.get(
        "start"
    )


# =========================================================
# QUERY HELPERS
# =========================================================

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
                "Unable to connect to the application database."
            ) from error


        if response.status_code != 200:

            raise Exception(
                "Unable to retrieve dashboard data."
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


@st.cache_data(
    ttl=CACHE_TTL,
    show_spinner=False
)
def resolve_data_source_id(
    notion_id
):

    if not notion_id:
        return None


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

    except requests.RequestException:

        return None


    if response.status_code != 200:
        return None


    data_sources = (
        response.json()
        .get(
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
# CACHED TABLE LOADERS
# =========================================================

@st.cache_data(
    ttl=CACHE_TTL,
    show_spinner=False
)
def load_users():

    return query_data_source(
        NOTION_USERS_DATA_SOURCE_ID
    )


def load_projects():

    # Projects are intentionally loaded without Streamlit cache so that
    # recently edited Notion fields are read on every dashboard refresh.
    return query_data_source(
        NOTION_PROJECTS_DATA_SOURCE_ID
    )


@st.cache_data(
    ttl=CACHE_TTL,
    show_spinner=False
)
def load_permits(
    permit_data_source_id
):

    if not permit_data_source_id:
        return []

    return query_data_source(
        permit_data_source_id
    )


# =========================================================
# USER / BRANCH HELPERS
# =========================================================

def get_user_record_by_email(
    users,
    email
):

    target_email = normalize_text(
        email
    )

    for page in users:

        properties = page.get(
            "properties",
            {}
        )

        user_email = normalize_text(
            get_property_plain_text(
                properties.get(
                    "Email",
                    {}
                )
            )
        )

        if user_email == target_email:

            return page


    return None


def get_branch_users(
    users,
    branch_name
):

    target_branch = normalize_text(
        branch_name
    )

    branch_users = []

    for page in users:

        properties = page.get(
            "properties",
            {}
        )


        branch = normalize_text(
            get_property_plain_text(
                properties.get(
                    "Branch",
                    {}
                )
            )
        )


        if branch != target_branch:
            continue


        name = (
            get_property_plain_text(
                properties.get(
                    "Name",
                    {}
                )
            )
            or ""
        ).strip()


        email = (
            get_property_plain_text(
                properties.get(
                    "Email",
                    {}
                )
            )
            or ""
        ).strip()


        identifiers = set()


        if name:

            identifiers.add(
                normalize_identity(
                    name
                )
            )

            for part in name.split():

                part_value = (
                    normalize_identity(
                        part
                    )
                )

                if len(
                    part_value
                ) >= 3:

                    identifiers.add(
                        part_value
                    )


        if email:

            identifiers.add(
                normalize_identity(
                    email
                )
            )

            email_prefix = (
                email
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


        branch_users.append(
            {
                "id":
                    page.get(
                        "id"
                    )
                    or "",

                "name":
                    name,

                "email":
                    email,

                "identifiers":
                    identifiers,
            }
        )


    return branch_users


def match_designer_to_user(
    designer_prop,
    branch_users
):

    if not designer_prop:
        return None


    prop_type = designer_prop.get(
        "type"
    )


    allowed_ids = {
        user[
            "id"
        ]:
            user

        for user in branch_users

        if user[
            "id"
        ]
    }


    # -----------------------------------------------------
    # SIMPLE FIELD
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


        designer_identity = (
            normalize_identity(
                designer_value
            )
        )


        if not designer_identity:
            return None


        for user in branch_users:

            identifiers = (
                user[
                    "identifiers"
                ]
            )


            if designer_identity in identifiers:

                return user


            if len(
                designer_identity
            ) >= 4:

                for identifier in identifiers:

                    if len(
                        identifier
                    ) < 4:

                        continue


                    if (
                        designer_identity
                        in identifier
                        or identifier
                        in designer_identity
                    ):

                        return user


        return None


    # -----------------------------------------------------
    # PEOPLE
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


            if person_id in allowed_ids:

                return allowed_ids[
                    person_id
                ]


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


            for compare_value in [
                person_name,
                person_email,
            ]:

                compare_identity = (
                    normalize_identity(
                        compare_value
                    )
                )


                if not compare_identity:
                    continue


                for user in branch_users:

                    if (
                        compare_identity
                        in user[
                            "identifiers"
                        ]
                    ):

                        return user


        return None


    # -----------------------------------------------------
    # RELATION
    # -----------------------------------------------------

    if prop_type == "relation":

        for item in designer_prop.get(
            "relation",
            []
        ):

            relation_id = (
                item.get(
                    "id"
                )
                or ""
            )


            if relation_id in allowed_ids:

                return allowed_ids[
                    relation_id
                ]


    return None


# =========================================================
# PROJECT MILESTONE CONFIG
# =========================================================

MILESTONE_CONFIG = [
    {
        "display_name":
            "Predesign Meeting",

        "aliases": [
            "Predesign Meeting",
            "Predesgin Meeting",
        ],
    },
    {
        "display_name":
            "Sales Review Meeting",

        "aliases": [
            "Sales Review Meeting",
        ],
    },
    {
        "display_name":
            "Design Review Meeting",

        "aliases": [
            "Design Review Meeting",
            "Design Reviewm Meeting",
        ],
    },
    {
        "display_name":
            "AML sent to QFS",

        "aliases": [
            "AML sent to QFS",
            "AML Sent to QFS",
        ],
    },
    {
        "display_name":
            "Submittal",

        "aliases": [
            "Submittal",
        ],
    },
    {
        "display_name":
            "Stocklist sent to QFS",

        "aliases": [
            "Stocklist sent to QFS",
            "Stocklist Sent to QFS",
        ],
    },
    {
        "display_name":
            "Foreman Package",

        "aliases": [
            "Foreman Package",
            "Foreman's Package",
            "Foreman Package Sent",
        ],
    },
]


def find_checkbox_field(
    properties,
    aliases
):

    normalized_properties = {
        normalize_text(
            property_name
        ):
            property_name

        for property_name, prop
        in properties.items()

        if prop.get(
            "type"
        )
        == "checkbox"
    }


    for alias in aliases:

        normalized_alias = (
            normalize_text(
                alias
            )
        )


        if (
            normalized_alias
            in normalized_properties
        ):

            return (
                normalized_properties[
                    normalized_alias
                ]
            )


    return None


# =========================================================
# PROJECT / MAP HELPERS
# =========================================================

def get_property_by_aliases(
    properties,
    aliases
):

    normalized_properties = {
        normalize_text(name): prop
        for name, prop in properties.items()
    }

    for alias in aliases:

        prop = normalized_properties.get(
            normalize_text(alias)
        )

        if prop is not None:
            return prop

    return {}


def get_text_by_aliases(
    properties,
    aliases,
    default=""
):

    prop = get_property_by_aliases(
        properties,
        aliases
    )

    value = get_property_plain_text(
        prop
    )

    return (
        str(value).strip()
        if value not in (None, "")
        else default
    )


def to_float(
    value
):

    if value is None:
        return None

    if isinstance(value, str):
        value = value.strip().replace(",", ".")

    if value == "":
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def get_number_by_aliases(
    properties,
    aliases
):

    prop = get_property_by_aliases(
        properties,
        aliases
    )

    if not prop:
        return None

    prop_type = prop.get(
        "type"
    )

    if prop_type == "number":
        return to_float(
            prop.get("number")
        )

    # Also accepts formula / rollup / rich text values if coordinates
    # were created in Notion using one of those property types.
    return to_float(
        get_property_plain_text(prop)
    )


@st.cache_data(
    ttl=3600,
    show_spinner=False
)
def geocode_project_address(
    address
):

    import re

    original_address = str(address or "").strip()

    if not original_address:
        return None, None, "No address", ""

    # Nominatim can have difficulty with suite/unit information.
    # Try the original address first, followed by progressively
    # simplified versions.
    candidates = []

    def add_candidate(value):
        value = re.sub(r"\s+", " ", str(value or "")).strip(" ,")
        if value and value not in candidates:
            candidates.append(value)

    add_candidate(original_address)

    # Remove common suite/unit designators while keeping the street address.
    without_suite = re.sub(
        r"(?i)(?:,?\s+|\s+)(?:suite|ste\.?|unit|#)\s*[A-Za-z0-9-]+(?=,|$)",
        "",
        original_address,
    )
    add_candidate(without_suite)

    # Add commas before a US state abbreviation and ZIP when the address
    # was entered as plain text without separators.
    formatted = re.sub(
        r"\s+([A-Z]{2})\s+(\d{5}(?:-\d{4})?)$",
        r", \1 \2",
        without_suite,
    )
    add_candidate(formatted)

    last_status = "Not found"

    for candidate in candidates:
        try:
            response = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={
                    "q": candidate,
                    "format": "jsonv2",
                    "limit": 1,
                    "addressdetails": 1,
                    "countrycodes": "us",
                },
                headers={
                    "User-Agent":
                        "WigintonToolsProjectDashboard/1.1 (project-map-geocoder)"
                },
                timeout=20,
            )

            if response.status_code != 200:
                last_status = f"HTTP {response.status_code}"
                continue

            results = response.json()

            if not results:
                last_status = "Not found"
                continue

            latitude = to_float(results[0].get("lat"))
            longitude = to_float(results[0].get("lon"))

            if latitude is not None and longitude is not None:
                return latitude, longitude, "Located", candidate

        except requests.RequestException as error:
            last_status = f"Request error: {type(error).__name__}"
        except (ValueError, TypeError):
            last_status = "Invalid response"

    return None, None, last_status, " | ".join(candidates)


def build_project_map_dataframe(
    projects_dataframe
):

    map_rows = []
    missing_rows = []
    geocoding_used = False

    for _, row in projects_dataframe.iterrows():

        address = str(row.get("Address", "") or "").strip()
        latitude = to_float(row.get("Latitude"))
        longitude = to_float(row.get("Longitude"))

        geocoding_status = "Stored coordinates"
        geocoding_query = ""

        if (latitude is None or longitude is None) and address:
            if geocoding_used:
                time.sleep(1.05)

            latitude, longitude, geocoding_status, geocoding_query = (
                geocode_project_address(address)
            )
            geocoding_used = True

        elif not address and (latitude is None or longitude is None):
            geocoding_status = "No address"

        valid_coordinates = (
            latitude is not None
            and longitude is not None
            and -90 <= latitude <= 90
            and -180 <= longitude <= 180
        )

        common = {
            "Project": row.get("Project", "—"),
            "Project Name": row.get("Project Name", "—"),
            "Designer": row.get("Designer", "—"),
            "Status": row.get("Status", "—"),
            "Address": address or "No address",
            "Address Source": row.get("Address Source", "Empty"),
            "Address Direct Result": row.get("Address Direct Result", ""),
            "Geocoding Status": geocoding_status,
            "Geocoding Query": geocoding_query,
            "Latitude": latitude,
            "Longitude": longitude,
        }

        if valid_coordinates:
            map_rows.append({
                **common,
                "lat": latitude,
                "lon": longitude,
            })
        else:
            missing_rows.append(common)

    return pd.DataFrame(map_rows), pd.DataFrame(missing_rows)


# =========================================================
# NOTION DATA SOURCE / PROPERTY HELPERS
# =========================================================

def retrieve_data_source_schema(
    data_source_id
):

    if not data_source_id:
        return {}

    try:
        response = requests.get(
            f"https://api.notion.com/v1/data_sources/{data_source_id}",
            headers=NOTION_HEADERS,
            timeout=20,
        )
    except requests.RequestException:
        return {}

    if response.status_code != 200:
        return {}

    try:
        return response.json()
    except ValueError:
        return {}


def get_data_source_property_info(
    data_source_schema,
    property_name
):

    properties = (
        data_source_schema.get(
            "properties",
            {}
        )
        if data_source_schema
        else {}
    )

    target = normalize_text(
        property_name
    )

    for name, prop in properties.items():

        if normalize_text(name) != target:
            continue

        return {
            "name": name,
            "id": prop.get("id") or "",
            "type": prop.get("type") or "",
        }

    return {
        "name": property_name,
        "id": "",
        "type": "",
    }


def extract_text_from_property_item_response(
    data
):

    if not data:
        return ""

    # Rich text/title properties can be returned as a paginated list of
    # property_item objects. Each result contains the rich_text/title object.
    if data.get("object") == "list":

        parts = []

        for item in data.get("results", []):
            item_type = item.get("type")

            if item_type in {"rich_text", "title"}:
                content = item.get(item_type) or {}
                plain_text = content.get("plain_text") or ""
                if plain_text:
                    parts.append(plain_text)

            elif item_type == "formula":
                formula = item.get("formula") or {}
                formula_type = formula.get("type")
                value = formula.get(formula_type)
                if value not in (None, ""):
                    parts.append(str(value))

        return "".join(parts).strip()

    # Some property types are returned as a single property_item object.
    item_type = data.get("type")

    if item_type in {"rich_text", "title"}:
        content = data.get(item_type) or {}
        return str(
            content.get("plain_text") or ""
        ).strip()

    if item_type == "number":
        value = data.get("number")
        return "" if value is None else str(value)

    if item_type == "select":
        value = data.get("select") or {}
        return str(value.get("name") or "").strip()

    if item_type == "status":
        value = data.get("status") or {}
        return str(value.get("name") or "").strip()

    if item_type == "email":
        return str(data.get("email") or "").strip()

    if item_type == "url":
        return str(data.get("url") or "").strip()

    if item_type == "phone_number":
        return str(data.get("phone_number") or "").strip()

    if item_type == "formula":
        formula = data.get("formula") or {}
        formula_type = formula.get("type")
        value = formula.get(formula_type)
        return "" if value is None else str(value).strip()

    return ""


def load_page_property_direct(
    page_id,
    property_id
):

    if not page_id or not property_id:
        return {}, "Missing page/property ID"

    try:
        response = requests.get(
            f"https://api.notion.com/v1/pages/{page_id}/properties/{property_id}",
            headers=NOTION_HEADERS,
            timeout=20,
        )
    except requests.RequestException as error:
        return {}, f"Request error: {error}"

    if response.status_code != 200:
        return {}, f"HTTP {response.status_code}"

    try:
        return response.json(), "OK"
    except ValueError:
        return {}, "Invalid JSON"


def get_page_property_text_direct(
    page_id,
    property_id
):

    data, result = load_page_property_direct(
        page_id,
        property_id
    )

    if result != "OK":
        return "", result

    value = extract_text_from_property_item_response(
        data
    )

    return value, "OK" if value else "Empty value"


# =========================================================
# DIRECT NOTION PAGE FALLBACK
# =========================================================

def load_project_page_direct(page_id):

    if not page_id:
        return {}

    try:
        response = requests.get(
            f"https://api.notion.com/v1/pages/{page_id}",
            headers=NOTION_HEADERS,
            timeout=20,
        )
    except requests.RequestException:
        return {}

    if response.status_code != 200:
        return {}

    try:
        return response.json()
    except ValueError:
        return {}


def get_direct_project_properties(page_id):

    return load_project_page_direct(
        page_id
    ).get(
        "properties",
        {}
    )


# =========================================================
# BUILD BRANCH PROJECT DATA
# =========================================================

def build_branch_projects(
    project_pages,
    branch_users,
    place_property_info=None
):

    rows = []


    for page in project_pages:

        properties = page.get(
            "properties",
            {}
        )


        designer_prop = (
            properties.get(
                "Designer",
                {}
            )
        )


        matched_user = (
            match_designer_to_user(
                designer_prop,
                branch_users
            )
        )


        if not matched_user:
            continue


        project_number = (
            get_property_plain_text(
                properties.get(
                    "Number",
                    {}
                )
            )
            or get_property_plain_text(
                properties.get(
                    "Project Number",
                    {}
                )
            )
            or "—"
        )


        project_name = (
            get_property_plain_text(
                properties.get(
                    "Project Name",
                    {}
                )
            )
            or get_property_plain_text(
                properties.get(
                    "Name",
                    {}
                )
            )
            or "—"
        )


        # IMPORTANT:
        # 10_Update_Project.py stores the project address in the Notion
        # property named "Place" as rich_text. Therefore Place must be the
        # primary source used by the Dashboard map.
        #
        # "Address" is kept only as a fallback for older records that may
        # still use the previous field name.
        project_address = get_text_by_aliases(
            properties,
            ["Place", "Address"],
            ""
        )

        if project_address:
            place_from_query = get_text_by_aliases(
                properties,
                ["Place"],
                ""
            )
            address_source = (
                "Query - Place"
                if place_from_query
                else "Query - Address fallback"
            )
        else:
            address_source = ""

        address_direct_result = (
            "Not needed"
            if project_address
            else "Not attempted"
        )

        direct_properties = None

        place_property_id = (
            (place_property_info or {}).get("id")
            or ""
        )

        # If Place was not included / populated in the normal query result,
        # retrieve the exact Place property directly from the Notion page.
        if not project_address and place_property_id:
            project_address, address_direct_result = (
                get_page_property_text_direct(
                    page.get("id") or "",
                    place_property_id
                )
            )

            if project_address:
                address_source = "Direct Property - Place"

        # Final fallback: retrieve the whole page and inspect Place first,
        # then Address for compatibility with older Projects.
        if not project_address:
            direct_properties = get_direct_project_properties(
                page.get("id") or ""
            )

            project_address = get_text_by_aliases(
                direct_properties,
                ["Place", "Address"],
                ""
            )

            if project_address:
                direct_place = get_text_by_aliases(
                    direct_properties,
                    ["Place"],
                    ""
                )

                address_source = (
                    "Direct Page - Place"
                    if direct_place
                    else "Direct Page - Address fallback"
                )

        if not address_source:
            address_source = "Empty"


        project_status = (
            get_text_by_aliases(
                properties,
                [
                    "Status",
                    "Project Status",
                    "Project Phase",
                    "Phase",
                ],
                ""
            )
        )


        project_latitude = (
            get_number_by_aliases(
                properties,
                [
                    "Latitude",
                    "Lat",
                    "Project Latitude",
                ]
            )
        )


        project_longitude = (
            get_number_by_aliases(
                properties,
                [
                    "Longitude",
                    "Lon",
                    "Lng",
                    "Project Longitude",
                ]
            )
        )

        if project_latitude is None or project_longitude is None:
            if direct_properties is None:
                direct_properties = get_direct_project_properties(
                    page.get("id") or ""
                )

            if project_latitude is None:
                project_latitude = get_number_by_aliases(
                    direct_properties,
                    ["Latitude", "Lat", "Project Latitude"]
                )

            if project_longitude is None:
                project_longitude = get_number_by_aliases(
                    direct_properties,
                    ["Longitude", "Lon", "Lng", "Project Longitude"]
                )


        installed = (
            get_checkbox(
                properties,
                "Installed",
                False
            )
        )


        if not project_status:
            project_status = (
                "Installed"
                if installed
                else "Active"
            )


        milestone_values = {}


        for milestone in (
            MILESTONE_CONFIG
        ):

            field_name = (
                find_checkbox_field(
                    properties,
                    milestone[
                        "aliases"
                    ]
                )
            )


            milestone_values[
                milestone[
                    "display_name"
                ]
            ] = (
                get_checkbox(
                    properties,
                    field_name,
                    False
                )
                if field_name
                else False
            )


        completed_steps = sum(
            1
            for value in (
                milestone_values.values()
            )
            if value
        )


        progress_percent = (
            completed_steps
            / len(
                MILESTONE_CONFIG
            )
            * 100
        )


        rows.append(
            {
                "page_id":
                    page.get(
                        "id"
                    )
                    or "",

                "Project":
                    project_number,

                "Project Name":
                    project_name,

                "Designer":
                    matched_user[
                        "name"
                    ]
                    or matched_user[
                        "email"
                    ]
                    or "—",

                "Designer Email":
                    matched_user[
                        "email"
                    ],

                "Address":
                    project_address,

                "Address Source":
                    address_source,

                "Address Direct Result":
                    address_direct_result,

                "Status":
                    project_status,

                "Latitude":
                    project_latitude,

                "Longitude":
                    project_longitude,

                "Installed":
                    installed,

                "Planned Hours":
                    get_number(
                        properties,
                        "Planned Hours",
                        0.0
                    ),

                "Used Hours":
                    get_number(
                        properties,
                        "Used Hours",
                        0.0
                    ),

                "Remaining Hours":
                    get_number(
                        properties,
                        "Remaining Hours",
                        0.0
                    ),

                "Used Hours (%)":
                    get_number(
                        properties,
                        "Used Hours (%)",
                        0.0
                    ),

                "Progress (%)":
                    progress_percent,

                **milestone_values,
            }
        )


    return rows


# =========================================================
# PERMIT HELPERS
# =========================================================

def get_project_relation_ids(
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


        if prop.get(
            "type"
        ) == "relation":

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


    for prop in properties.values():

        if prop.get(
            "type"
        ) == "relation":

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


def build_branch_permit_rows(
    permit_pages,
    project_lookup
):

    rows = []


    for page in permit_pages:

        properties = page.get(
            "properties",
            {}
        )


        relation_ids = (
            get_project_relation_ids(
                properties
            )
        )


        matching_project_id = None


        for project_id in relation_ids:

            if project_id in project_lookup:

                matching_project_id = (
                    project_id
                )

                break


        if not matching_project_id:
            continue


        project = project_lookup[
            matching_project_id
        ]


        submitted_date = (
            parse_date(
                get_date_value(
                    properties,
                    "Submitted Date"
                )
            )
        )


        approved_date = (
            parse_date(
                get_date_value(
                    properties,
                    "Approved Date"
                )
            )
        )


        approval_days = None


        if (
            submitted_date
            and approved_date
        ):

            calculated_days = (
                approved_date
                - submitted_date
            ).days


            if calculated_days >= 0:

                approval_days = (
                    calculated_days
                )


        rows.append(
            {
                "Project":
                    project[
                        "Project"
                    ],

                "Project Name":
                    project[
                        "Project Name"
                    ],

                "Designer":
                    project[
                        "Designer"
                    ],

                "Building":
                    get_property_plain_text(
                        properties.get(
                            "Building",
                            {}
                        )
                    )
                    or "—",

                "Permit Type":
                    get_property_plain_text(
                        properties.get(
                            "Type",
                            {}
                        )
                    )
                    or "—",

                "AHJ":
                    get_property_plain_text(
                        properties.get(
                            "AHJ",
                            {}
                        )
                    )
                    or "—",

                "Submitted Date":
                    submitted_date,

                "Approved Date":
                    approved_date,

                "Approval Days":
                    approval_days,
            }
        )


    return rows


# =========================================================
# LOAD DASHBOARD DATA
# =========================================================

st.title(
    "📊 Branch Dashboard"
)

refresh_col1, refresh_col2 = st.columns([1, 5])

with refresh_col1:
    if st.button(
        "🔄 Refresh Data",
        use_container_width=True,
    ):
        st.cache_data.clear()
        st.rerun()



st.caption(
    "Branch-wide project, productivity, milestone and permit performance."
)


if not NOTION_PROJECTS_DATA_SOURCE_ID:

    st.error(
        "Projects data source is not configured."
    )

    st.stop()


with st.spinner(
    "Loading dashboard..."
):

    users = (
        load_users()
    )


    manager_record = (
        get_user_record_by_email(
            users,
            logged_user_email
        )
    )


    if not manager_record:

        st.error(
            "Unable to identify the logged-in Manager."
        )

        st.stop()


    manager_properties = (
        manager_record.get(
            "properties",
            {}
        )
    )


    manager_branch = (
        get_property_plain_text(
            manager_properties.get(
                "Branch",
                {}
            )
        )
        or ""
    ).strip()


    if not manager_branch:

        st.error(
            "The logged-in Manager does not have a Branch assigned."
        )

        st.stop()


    branch_users = (
        get_branch_users(
            users,
            manager_branch
        )
    )


    projects_data_source_schema = (
        retrieve_data_source_schema(
            NOTION_PROJECTS_DATA_SOURCE_ID
        )
    )


    # 10_Update_Project.py uses the Projects property named "Place".
    # Read the same property here so the Dashboard and Update Project page
    # use one consistent source of truth for project location.
    place_property_info = (
        get_data_source_property_info(
            projects_data_source_schema,
            "Place"
        )
    )


    project_pages = (
        load_projects()
    )


    branch_projects = (
        build_branch_projects(
            project_pages,
            branch_users,
            place_property_info
        )
    )


    permit_data_source_id = (
        resolve_data_source_id(
            NOTION_PERMIT_ID
        )
    )


    permit_pages = (
        load_permits(
            permit_data_source_id
        )
        if permit_data_source_id
        else []
    )


# =========================================================
# BRANCH SUMMARY
# =========================================================

st.info(
    f"Branch: {manager_branch} | "
    f"Users: {len(branch_users)} | "
    f"Projects: {len(branch_projects)}"
)


if not branch_projects:

    st.warning(
        "No Projects were found for users in this Branch."
    )

    st.stop()


projects_df = pd.DataFrame(
    branch_projects
)


active_projects_df = (
    projects_df[
        projects_df[
            "Installed"
        ]
        == False
    ]
    .copy()
)


installed_projects_df = (
    projects_df[
        projects_df[
            "Installed"
        ]
        == True
    ]
    .copy()
)


# =========================================================
# TOP METRICS
# =========================================================

st.divider()


st.subheader(
    "Branch Summary"
)


metric1, metric2, metric3, metric4 = (
    st.columns(4)
)


with metric1:

    st.metric(
        "Active Projects",
        len(
            active_projects_df
        )
    )


with metric2:

    st.metric(
        "Installed Projects",
        len(
            installed_projects_df
        )
    )


with metric3:

    st.metric(
        "Designers",
        active_projects_df[
            "Designer"
        ].nunique()
        if not active_projects_df.empty
        else 0
    )


with metric4:

    avg_progress = (
        active_projects_df[
            "Progress (%)"
        ].mean()
        if not active_projects_df.empty
        else 0.0
    )

    st.metric(
        "Average Project Progress",
        f"{avg_progress:.1f}%"
    )


# =========================================================
# PROJECTS BY DESIGNER
# =========================================================

st.divider()


st.subheader(
    "Projects by Designer"
)


project_count_df = (
    projects_df
    .groupby(
        "Designer",
        as_index=False
    )
    .agg(
        Total_Projects=(
            "Project",
            "count"
        ),
        Active_Projects=(
            "Installed",
            lambda values:
                int(
                    (~values).sum()
                )
        ),
        Installed_Projects=(
            "Installed",
            lambda values:
                int(
                    values.sum()
                )
        ),
    )
    .sort_values(
        "Total_Projects",
        ascending=False
    )
)


st.dataframe(
    project_count_df.rename(
        columns={
            "Total_Projects":
                "Total Projects",

            "Active_Projects":
                "Active Projects",

            "Installed_Projects":
                "Installed Projects",
        }
    ),
    use_container_width=True,
    hide_index=True,
)


count_chart = px.bar(
    project_count_df,
    x="Designer",
    y=[
        "Active_Projects",
        "Installed_Projects",
    ],
    barmode="group",
    labels={
        "value":
            "Projects",

        "variable":
            "Status",
    },
    title=
        "Project Count by Designer",
)


st.plotly_chart(
    count_chart,
    use_container_width=True,
)


# =========================================================
# ACTIVE PROJECT DISTRIBUTION - PIE CHART
# =========================================================

st.divider()


st.subheader(
    "Active Project Distribution"
)


st.caption(
    "Percentage of active Projects by Designer. "
    "Projects with Installed = True are excluded."
)


if active_projects_df.empty:

    st.info(
        "There are no active Projects to display."
    )


else:

    active_distribution_df = (
        active_projects_df
        .groupby(
            "Designer",
            as_index=False
        )
        .agg(
            Projects=(
                "Project",
                "count"
            )
        )
        .sort_values(
            "Projects",
            ascending=False
        )
    )


    pie_chart = px.pie(
        active_distribution_df,
        names="Designer",
        values="Projects",
        hole=0.35,
        title=
            "Percentage of Active Projects by Designer",
    )


    pie_chart.update_traces(
        textposition="inside",
        textinfo="percent+label",
    )


    st.plotly_chart(
        pie_chart,
        use_container_width=True,
    )


# =========================================================
# PRODUCTIVITY BY DESIGNER
# =========================================================

st.divider()


st.subheader(
    "Designer Productivity"
)


st.caption(
    "Productivity indicators based on Planned Hours, "
    "Used Hours and active Project milestone progress."
)


productivity_df = (
    projects_df
    .groupby(
        "Designer",
        as_index=False
    )
    .agg(
        Planned_Hours=(
            "Planned Hours",
            "sum"
        ),
        Used_Hours=(
            "Used Hours",
            "sum"
        ),
        Remaining_Hours=(
            "Remaining Hours",
            "sum"
        ),
        Average_Project_Progress=(
            "Progress (%)",
            "mean"
        ),
        Project_Count=(
            "Project",
            "count"
        ),
    )
)


productivity_df[
    "Hours Used (%)"
] = productivity_df.apply(
    lambda row:
        (
            row[
                "Used_Hours"
            ]
            / row[
                "Planned_Hours"
            ]
            * 100
        )
        if row[
            "Planned_Hours"
        ] > 0
        else 0.0,
    axis=1,
)


productivity_display_df = (
    productivity_df
    .rename(
        columns={
            "Planned_Hours":
                "Planned Hours",

            "Used_Hours":
                "Used Hours",

            "Remaining_Hours":
                "Remaining Hours",

            "Average_Project_Progress":
                "Average Project Progress (%)",

            "Project_Count":
                "Projects",
        }
    )
)


productivity_display_df[
    "Average Project Progress (%)"
] = (
    productivity_display_df[
        "Average Project Progress (%)"
    ]
    .round(1)
)


productivity_display_df[
    "Hours Used (%)"
] = (
    productivity_display_df[
        "Hours Used (%)"
    ]
    .round(1)
)


st.dataframe(
    productivity_display_df,
    use_container_width=True,
    hide_index=True,
)


hours_chart = px.bar(
    productivity_df,
    x="Designer",
    y=[
        "Planned_Hours",
        "Used_Hours",
    ],
    barmode="group",
    labels={
        "value":
            "Hours",

        "variable":
            "Hours",
    },
    title=
        "Planned Hours vs Used Hours by Designer",
)


st.plotly_chart(
    hours_chart,
    use_container_width=True,
)


progress_chart = px.bar(
    productivity_df,
    x="Designer",
    y="Average_Project_Progress",
    labels={
        "Average_Project_Progress":
            "Average Project Progress (%)",
    },
    title=
        "Average Project Progress by Designer",
)


st.plotly_chart(
    progress_chart,
    use_container_width=True,
)


# =========================================================
# PROJECT MILESTONES BY DESIGNER
# =========================================================

st.divider()


st.subheader(
    "Project Milestones by Designer"
)


st.caption(
    "Summary of completed project stages grouped by Designer."
)


milestone_names = [
    item[
        "display_name"
    ]
    for item in MILESTONE_CONFIG
]


milestone_rows = []


for designer, designer_df in (
    active_projects_df.groupby(
        "Designer"
    )
):

    row = {
        "Designer":
            designer,

        "Active Projects":
            len(
                designer_df
            ),
    }


    for milestone in milestone_names:

        completed = int(
            designer_df[
                milestone
            ].sum()
        )


        total = len(
            designer_df
        )


        percentage = (
            completed
            / total
            * 100
            if total
            else 0
        )


        row[
            milestone
        ] = (
            f"{completed}/{total} "
            f"({percentage:.0f}%)"
        )


    milestone_rows.append(
        row
    )


milestone_summary_df = (
    pd.DataFrame(
        milestone_rows
    )
)


fixed_milestone_columns = [
    "Designer",
    "Active Projects",
    "Predesign Meeting",
    "Sales Review Meeting",
    "Design Review Meeting",
    "AML sent to QFS",
    "Submittal",
    "Stocklist sent to QFS",
    "Foreman Package",
]


st.dataframe(
    milestone_summary_df,
    use_container_width=True,
    hide_index=True,
    column_order=
        fixed_milestone_columns,
)


# =========================================================
# PROJECT DETAIL
# =========================================================

with st.expander(
    "View Project Stage Details",
    expanded=False,
):

    detail_rows = []


    for _, row in (
        active_projects_df.iterrows()
    ):

        detail_row = {
            "Designer":
                row[
                    "Designer"
                ],

            "Project":
                row[
                    "Project"
                ],

            "Project Name":
                row[
                    "Project Name"
                ],
        }


        for milestone in milestone_names:

            detail_row[
                milestone
            ] = (
                "✅"
                if row[
                    milestone
                ]
                else "⬜"
            )


        detail_row[
            "Progress"
        ] = (
            f"{row['Progress (%)']:.0f}%"
        )


        detail_rows.append(
            detail_row
        )


    project_detail_columns = [
        "Designer",
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
        detail_rows,
        use_container_width=True,
        hide_index=True,
        column_order=
            project_detail_columns,
    )


# =========================================================
# PERMIT APPROVAL PERFORMANCE
# =========================================================

st.divider()


st.subheader(
    "Permit Approval Performance"
)


st.caption(
    "Approval time includes only Permit records that have "
    "both Submitted Date and Approved Date."
)


project_lookup = {
    project[
        "page_id"
    ]:
        project

    for project in branch_projects

    if project[
        "page_id"
    ]
}


permit_rows = (
    build_branch_permit_rows(
        permit_pages,
        project_lookup
    )
)


permit_df = pd.DataFrame(
    permit_rows
)


if permit_df.empty:

    st.info(
        "No Permit records were found for Projects in this Branch."
    )


else:

    completed_permit_df = (
        permit_df[
            permit_df[
                "Approval Days"
            ].notna()
        ]
        .copy()
    )


    if completed_permit_df.empty:

        st.info(
            "No Permit records with both Submitted Date "
            "and Approved Date were found."
        )


    else:

        overall_avg_days = (
            completed_permit_df[
                "Approval Days"
            ].mean()
        )


        permit_metric1, permit_metric2, permit_metric3 = (
            st.columns(3)
        )


        with permit_metric1:

            st.metric(
                "Approved Permit Records",
                len(
                    completed_permit_df
                )
            )


        with permit_metric2:

            st.metric(
                "Average Approval Time",
                f"{overall_avg_days:.1f} days"
            )


        with permit_metric3:

            fastest_value = (
                completed_permit_df[
                    "Approval Days"
                ].min()
            )

            st.metric(
                "Fastest Approval",
                f"{fastest_value:.0f} days"
            )


        ahj_summary_df = (
            completed_permit_df
            .groupby(
                "AHJ",
                as_index=False
            )
            .agg(
                Average_Days=(
                    "Approval Days",
                    "mean"
                ),
                Permit_Records=(
                    "Approval Days",
                    "count"
                ),
            )
            .sort_values(
                "Average_Days",
                ascending=False
            )
        )


        ahj_summary_df[
            "Average_Days"
        ] = (
            ahj_summary_df[
                "Average_Days"
            ]
            .round(1)
        )


        approval_chart = px.bar(
            ahj_summary_df,
            x="AHJ",
            y="Average_Days",
            labels={
                "Average_Days":
                    "Average Approval Time (Days)",
            },
            title=
                "Average Permit Approval Time by AHJ",
        )


        st.plotly_chart(
            approval_chart,
            use_container_width=True,
        )


        designer_permit_df = (
            completed_permit_df
            .groupby(
                "Designer",
                as_index=False
            )
            .agg(
                Average_Approval_Days=(
                    "Approval Days",
                    "mean"
                ),
                Approved_Permits=(
                    "Approval Days",
                    "count"
                ),
            )
            .sort_values(
                "Average_Approval_Days",
                ascending=False
            )
        )


        designer_permit_df[
            "Average_Approval_Days"
        ] = (
            designer_permit_df[
                "Average_Approval_Days"
            ]
            .round(1)
        )


        st.dataframe(
            designer_permit_df.rename(
                columns={
                    "Average_Approval_Days":
                        "Average Approval Days",

                    "Approved_Permits":
                        "Approved Permit Records",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )


# =========================================================
# ACTIVE PROJECT LIST
# =========================================================

st.divider()


st.subheader(
    "Active Projects"
)


active_project_rows = (
    active_projects_df[
        [
            "Designer",
            "Project",
            "Project Name",
            "Planned Hours",
            "Used Hours",
            "Remaining Hours",
            "Progress (%)",
        ]
    ]
    .copy()
)


active_project_rows[
    "Progress (%)"
] = (
    active_project_rows[
        "Progress (%)"
    ]
    .round(1)
)


st.dataframe(
    active_project_rows.sort_values(
        [
            "Designer",
            "Project",
        ]
    ),
    use_container_width=True,
    hide_index=True,
)

# =========================================================
# PROJECT MAP
# =========================================================

st.divider()

st.subheader(
    "Project Map"
)

st.caption(
    "All projects in this Branch with a valid project address or "
    "Latitude/Longitude are displayed on the map. Hover over a marker "
    "to view the project information."
)


with st.spinner(
    "Locating project addresses..."
):

    map_df, missing_map_df = (
        build_project_map_dataframe(
            projects_df
        )
    )


if map_df.empty:

    st.warning(
        "No projects could be displayed on the map. "
        "Verify that the Projects database contains a valid "
        "Place for each project."
    )

else:

    st.success(
        f"{len(map_df)} project(s) displayed on the map."
    )

    # -----------------------------------------------------
    # CREATE PYDECK-SAFE FIELD NAMES
    # -----------------------------------------------------

    map_deck_df = map_df.copy()

    map_deck_df["project_number"] = (
        map_deck_df["Project"]
        .fillna("")
        .astype(str)
    )

    map_deck_df["project_name"] = (
        map_deck_df["Project Name"]
        .fillna("")
        .astype(str)
    )

    map_deck_df["designer_name"] = (
        map_deck_df["Designer"]
        .fillna("")
        .astype(str)
    )

    map_deck_df["project_status"] = (
        map_deck_df["Status"]
        .fillna("")
        .astype(str)
    )

    map_deck_df["project_address"] = (
        map_deck_df["Address"]
        .fillna("")
        .astype(str)
    )

    map_deck_df["lat"] = pd.to_numeric(
        map_deck_df["lat"],
        errors="coerce",
    )

    map_deck_df["lon"] = pd.to_numeric(
        map_deck_df["lon"],
        errors="coerce",
    )

    map_deck_df = (
        map_deck_df[
            map_deck_df["lat"].notna()
            & map_deck_df["lon"].notna()
        ]
        .copy()
    )


    if map_deck_df.empty:

        st.warning(
            "The project addresses were located, but no valid "
            "Latitude/Longitude values are available for the map."
        )

    else:

        # -------------------------------------------------
        # MAP CENTER / ZOOM
        # -------------------------------------------------

        center_lat = float(
            map_deck_df["lat"].mean()
        )

        center_lon = float(
            map_deck_df["lon"].mean()
        )

        if len(map_deck_df) == 1:
            map_zoom = 11.5

        else:
            lat_span = float(
                map_deck_df["lat"].max()
                - map_deck_df["lat"].min()
            )

            lon_span = float(
                map_deck_df["lon"].max()
                - map_deck_df["lon"].min()
            )

            max_span = max(
                lat_span,
                lon_span,
            )

            if max_span < 0.03:
                map_zoom = 12.0
            elif max_span < 0.08:
                map_zoom = 10.5
            elif max_span < 0.20:
                map_zoom = 9.0
            elif max_span < 0.50:
                map_zoom = 8.0
            elif max_span < 1.00:
                map_zoom = 7.0
            elif max_span < 3.00:
                map_zoom = 5.5
            elif max_span < 8.00:
                map_zoom = 4.5
            else:
                map_zoom = 3.5


        # -------------------------------------------------
        # INTERACTIVE PROJECT MARKERS
        # -------------------------------------------------

        project_layer = pdk.Layer(
            "ScatterplotLayer",
            data=map_deck_df,
            get_position="[lon, lat]",
            get_radius=120,
            radius_min_pixels=8,
            radius_max_pixels=18,
            pickable=True,
            auto_highlight=True,
            stroked=True,
            filled=True,
            get_fill_color=[220, 70, 55, 210],
            get_line_color=[255, 255, 255, 255],
            line_width_min_pixels=2,
        )


        view_state = pdk.ViewState(
            latitude=center_lat,
            longitude=center_lon,
            zoom=map_zoom,
            pitch=0,
            bearing=0,
        )


        tooltip = {
            "html": """
                <div style="font-family: Arial, sans-serif; min-width: 280px;">
                    <div style="font-size: 16px; font-weight: 700; margin-bottom: 8px;">
                        {project_name}
                    </div>
                    <div><b>Project:</b> {project_number}</div>
                    <div><b>Designer:</b> {designer_name}</div>
                    <div><b>Status:</b> {project_status}</div>
                    <div style="margin-top: 6px;">
                        <b>Address:</b> {project_address}
                    </div>
                </div>
            """,
            "style": {
                "backgroundColor": "#222222",
                "color": "white",
                "fontSize": "13px",
                "padding": "10px",
                "borderRadius": "8px",
            },
        }


        deck = pdk.Deck(
            layers=[
                project_layer
            ],
            initial_view_state=view_state,
            tooltip=tooltip,
        )


        st.pydeck_chart(
            deck,
            use_container_width=True,
            height=650,
        )


        st.caption(
            "Move the mouse directly over a project marker to display "
            "Project Number, Project Name, Designer, Status and Address."
        )


        with st.expander(
            "View mapped project details",
            expanded=False,
        ):

            mapped_columns = [
                "Project",
                "Project Name",
                "Designer",
                "Status",
                "Address",
            ]

            st.dataframe(
                map_df[
                    mapped_columns
                ].sort_values(
                    [
                        "Designer",
                        "Project",
                    ]
                ),
                use_container_width=True,
                hide_index=True,
            )

