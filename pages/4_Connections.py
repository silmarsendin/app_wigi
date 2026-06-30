import streamlit as st
from utils.layout import show_sidebar_branding

st.set_page_config(page_title="Connections", page_icon="🔗", layout="wide")

show_sidebar_branding()

st.title("Connections - Vitaulic")

# ===== PIPE SIZE =====
pipe_size = st.selectbox(
    "Select Pipe Size:",
    [
        "1 in",
        "1-1/4 in",
        "1-1/2 in",
        "2 in",
        "2-1/2 in",
        "3 in",
        "3-1/2 in",
        "4 in",
        "5 in",
        "6 in",
        "8 in",
        "10 in",
        "12 in",
    ]
)

# ===== DIMENSIONS DATA =====
dimensions_data = {
    "1 in": {
        "tee": 'C to E = 2.25"',
        "elbow_90": 'C to E = 2.25"',
        "elbow_45": 'C to E = 1.75"',
        "reducer": 'Not shown in the provided reducer table',
    },
    "1-1/4 in": {
        "tee": 'C to E = 2.75"',
        "elbow_90": 'C to E = 2.75"',
        "elbow_45": 'C to E = 1.75"',
        "reducer": 'Reducers from 1-1/4" to 1": E to E = 2.50"',
    },
    "1-1/2 in": {
        "tee": 'C to E = 2.75"',
        "elbow_90": 'C to E = 2.75"',
        "elbow_45": 'C to E = 1.75"',
        "reducer": 'Reducers from 1-1/2" to 1", or 1-1/4": E to E = 2.50"',
    },
    "2 in": {
        "tee": 'C to E = 3.25"',
        "elbow_90": 'C to E = 3.25"',
        "elbow_45": 'C to E = 2.00"',
        "reducer": 'Reducers from 2" to 3/4", 1", 1-1/4", or 1-1/2": E to E = 2.50"',
    },
    "2-1/2 in": {
        "tee": 'C to E = 3.75"',
        "elbow_90": 'C to E = 3.75"',
        "elbow_45": 'C to E = 2.25"',
        "reducer": 'Reducers from 2-1/2" to 1", 1-1/4", 1-1/2", or 2": E to E = 2.50"',
    },
    "3 in": {
        "tee": 'C to E = 4.25"',
        "elbow_90": 'C to E = 4.25"',
        "elbow_45": 'C to E = 2.50"',
        "reducer": 'Reducers from 3" to 1", 1-1/4", 1-1/2", 2", or 2-1/2": E to E = 2.50"',
    },
    "3-1/2 in": {
        "tee": 'C to E = 4.50"',
        "elbow_90": 'C to E = 4.50"',
        "elbow_45": 'C to E = 2.75"',
        "reducer": 'Reducer from 3-1/2" to 3": E to E = 2.50"',
    },
    "4 in": {
        "tee": 'C to E = 5.00"',
        "elbow_90": 'C to E = 5.00"',
        "elbow_45": 'C to E = 3.00"',
        "reducer": 'Reducers from 4" to 1", 1-1/4", 1-1/2", 2", 2-1/2", 3", or 3-1/2": E to E = 3.00"',
    },
    "5 in": {
        "tee": 'C to E = 5.50"',
        "elbow_90": 'C to E = 5.50"',
        "elbow_45": 'C to E = 3.25"',
        "reducer": 'Reducer from 5" to 2-1/2", or 3": E to E = 4.50"',
    },
    "6 in": {
        "tee": 'C to E = 6.50"',
        "elbow_90": 'C to E = 6.50"',
        "elbow_45": 'C to E = 3.50"',
        "reducer": 'Reducer from 6" to 1", 1-1/2", 2", 2-1/2", 3", 4",  or 5": E to E = 4.00"',
    },
    "8 in": {
        "tee": 'C to E = 7.75"',
        "elbow_90": 'C to E = 7.75"',
        "elbow_45": 'C to E = 4.25"',
        "reducer": 'Reducer from 8" to 3", 4", 5", or 6": E to E = 5.00"',
    },
    "10 in": {
        "tee": 'C to E = 9.00"',
        "elbow_90": 'C to E = 9.00"',
        "elbow_45": 'C to E = 4.75"',
        "reducer": 'Reducer from 10" to 6", or 8": E to E = 6.00"',
    },
    "12 in": {
        "tee": 'C to E = 10.00"',
        "elbow_90": 'C to E = 10.00"',
        "elbow_45": 'C to E = 5.25"',
        "reducer": 'Reducer from 12" to 6", 8", or 10": E to E = 7.00"',
    },
}

data = dimensions_data[pipe_size]

st.subheader(f"Selected Pipe Size: {pipe_size}")

# ===== TABLE HEADER =====
header_col1, header_col2, header_col3 = st.columns([1, 2, 4])

with header_col1:
    st.markdown("**Image**")

with header_col2:
    st.markdown("**Connection**")

with header_col3:
    st.markdown("**Dimensions**")

st.divider()

# ===== FUNCTION TO CREATE ROWS =====
def connection_row(image_path, connection_name, dimension_text):
    col1, col2, col3 = st.columns([1, 2, 4])

    with col1:
        st.image(image_path, width=120)

    with col2:
        st.markdown(f"**{connection_name}**")

    with col3:
        st.text_input(
            label=f"{connection_name} Dimensions",
            value=dimension_text,
            disabled=True,
            label_visibility="collapsed"
        )

    st.divider()


# ===== ROWS =====
connection_row(
    "assets/tee.png",
    "Tee Grooved",
    data["tee"]
)

connection_row(
    "assets/90.png",
    "Elbow 90°",
    data["elbow_90"]
)

connection_row(
    "assets/45.png",
    "Elbow 45°",
    data["elbow_45"]
)

connection_row(
    "assets/red.png",
    "Concentric Reducer",
    data["reducer"]
)
