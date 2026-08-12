import streamlit as st
import requests
import pandas as pd
import plotly.express as px

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


CACHE_TTL = 300


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


@st.cache_data(
    ttl=CACHE_TTL,
    show_spinner=False
)
def load_projects():

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
# BUILD BRANCH PROJECT DATA
# =========================================================

def build_branch_projects(
    project_pages,
    branch_users
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


        installed = (
            get_checkbox(
                properties,
                "Installed",
                False
            )
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


    project_pages = (
        load_projects()
    )


    branch_projects = (
        build_branch_projects(
            project_pages,
            branch_users
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
