import streamlit as st
from utils.layout import show_sidebar_branding

st.set_page_config(page_title="Valve", page_icon="🚰", layout="wide")

show_sidebar_branding()

st.title("Valve")

pipe_size = st.selectbox(
    "Select Pipe Size:",
    [
        "2-1/2 in",
        "3 in",
        "4 in",
        "5 in",
        "6 in",
        "8 in",
        "10 in",
        "12 in",
    ]
)

def readonly_box(value):
    st.markdown(
        f"""
        <div style="
            border: 1px solid #ddd;
            border-radius: 6px;
            padding: 8px;
            min-height: 38px;
            background-color: #f7f7f7;
            text-align: center;
            font-size: 16px;">
            {value}
        </div>
        """,
        unsafe_allow_html=True
    )

# ===== VICTAULIC #717 DATA =====
valve_data = {
    "2-1/2 in": {"OD": "2.875", "A": "3.88", "B": "4.26", "C": "3.57", "E": "—", "J": "—", "K": "—", "P": "—", "R": "—"},
    "3 in": {"OD": "3.500", "A": "4.25", "B": "5.06", "C": "4.17", "E": "—", "J": "—", "K": "—", "P": "—", "R": "—"},
    "4 in": {"OD": "4.500", "A": "9.63", "B": "6.00", "C": "3.88", "E": "3.50", "J": "2.00", "K": "4.50", "P": "3.50", "R": "3.35"},
    "5 in": {"OD": "5.563", "A": "10.50", "B": "6.80", "C": "4.50", "E": "4.17", "J": "2.15", "K": "5.88", "P": "4.08", "R": "3.98"},
    "6 in": {"OD": "6.625", "A": "11.50", "B": "8.00", "C": "5.00", "E": "4.50", "J": "2.38", "K": "6.67", "P": "4.73", "R": "3.89"},
    "8 in": {"OD": "8.625", "A": "14.00", "B": "9.88", "C": "6.06", "E": "5.65", "J": "2.15", "K": "8.85", "P": "5.65", "R": "5.75"},
    "10 in": {"OD": "10.750", "A": "17.00", "B": "12.00", "C": "7.09", "E": "6.69", "J": "2.15", "K": "10.92", "P": "6.73", "R": "—"},
    "12 in": {"OD": "12.750", "A": "19.50", "B": "14.00", "C": "8.06", "E": "7.64", "J": "2.51", "K": "12.81", "P": "7.73", "R": "—"},
}

data = valve_data[pipe_size]

if pipe_size in ["2-1/2 in", "3 in"]:
    valve_image = "assets/cv7172.png"
elif pipe_size in ["4 in", "5 in", "6 in", "8 in"]:
    valve_image = "assets/cv7174.png"
else:
    valve_image = "assets/cv71710.png"

# ===== TABLE 1 =====
st.markdown("## Check Valve Victaulic #717® Grooved")
st.subheader(f"Selected Pipe Size: {pipe_size}")

headers = ["Image", "OD", "A", "B", "C", "E", "J", "K", "P", "R"]
header_cols = st.columns([3, 1.2, 1.2, 1, 1, 1, 1, 1, 1, 1])

for col, header in zip(header_cols, headers):
    with col:
        st.markdown(f"**{header}**")

st.divider()

row_cols = st.columns([3, 1.2, 1.2, 1, 1, 1, 1, 1, 1, 1])

with row_cols[0]:
    st.image(valve_image, width=260)

with row_cols[1]:
    readonly_box(data["OD"])

with row_cols[2]:
    readonly_box(data["A"])

with row_cols[3]:
    readonly_box(data["B"])

with row_cols[4]:
    readonly_box(data["C"])

with row_cols[5]:
    readonly_box(data["E"])

with row_cols[6]:
    readonly_box(data["J"])

with row_cols[7]:
    readonly_box(data["K"])

with row_cols[8]:
    readonly_box(data["P"])

with row_cols[9]:
    readonly_box(data["R"])

st.divider()

# ===== GLR300G DATA =====
glr300g_data = {
    "2-1/2 in": {"A": "3.8", "B": "2.87", "C": "5.04", "D": "5.31", "E": "4.13", "F": "5.31"},
    "3 in": {"A": "3.8", "B": "3.5", "C": "5.04", "D": "5.60", "E": "4.41", "F": "5.31"},
    "4 in": {"A": "4.5", "B": "4.5", "C": "5.04", "D": "6.89", "E": "5.71", "F": "5.31"},
    "5 in": {"A": "—", "B": "—", "C": "—", "D": "—", "E": "—", "F": "—"},
    "6 in": {"A": "5.2", "B": "6.63", "C": "8.66", "D": "8.23", "E": "7.05", "F": "7.60"},
    "8 in": {"A": "5.8", "B": "8.63", "C": "8.66", "D": "9.21", "E": "8.03", "F": "7.60"},
    "10 in": {"A": "—", "B": "—", "C": "—", "D": "—", "E": "—", "F": "—"},
    "12 in": {"A": "—", "B": "—", "C": "—", "D": "—", "E": "—", "F": "—"},
}

glr_data = glr300g_data[pipe_size]

# ===== TABLE 2 =====
st.markdown("## GLR300G Grooved")

glr_headers = ["Image", "A", "B", "C", "D", "E", "F"]
glr_header_cols = st.columns([3, 1, 1, 1, 1, 1, 1])

for col, header in zip(glr_header_cols, glr_headers):
    with col:
        st.markdown(f"**{header}**")

st.divider()

glr_row_cols = st.columns([3, 1, 1, 1, 1, 1, 1])

with glr_row_cols[0]:
    st.image("assets/glr.png", width=260)

with glr_row_cols[1]:
    readonly_box(glr_data["A"])

with glr_row_cols[2]:
    readonly_box(glr_data["B"])

with glr_row_cols[3]:
    readonly_box(glr_data["C"])

with glr_row_cols[4]:
    readonly_box(glr_data["D"])

with glr_row_cols[5]:
    readonly_box(glr_data["E"])

with glr_row_cols[6]:
    readonly_box(glr_data["F"])