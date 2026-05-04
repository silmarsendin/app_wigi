import streamlit as st
from utils.layout import show_sidebar_branding

st.set_page_config(page_title="Pipes Sizes", page_icon="📏", layout="wide")

show_sidebar_branding()

st.title("Pipes Sizes")

# ===== SELEÇÃO DE DIÂMETRO =====
pipe_size = st.selectbox(
    "Select a pipe size:",
    ["1 in", "1-1/4 in", "1-1/2 in", "2 in", "2-1/2 in", "3 in", "4 in", "6 in", "8 in", "10 in"]
)

# ===== VALORES ASSOCIADOS =====
pipe_data = {
    "1 in": {
        "I.D.Sch-07": "NA",
        "I.D.Sch-10": "NA",
        "I.D.Sch-40": "1.049 in",
        "Outside Diameter": "1.315 in",
        "Capacity Sch-07": "0.050 gal/ft",
        "Capacity Sch-10": "0.049 gal/ft",
        "Capacity Sch-40": "0.045 gal/ft",
    },
    "1-1/4 in": {
        "I.D.Sch-07": "1.536 in",
        "I.D.Sch-10": "1.442 in",
        "I.D.Sch-40": "1.380 in",
        "Outside Diameter": "1.660 in",
        "Capacity Sch-07": "0.087 gal/ft",
        "Capacity Sch-10": "0.085 gal/ft",
        "Capacity Sch-40": "0.078 gal/ft",
    },
    "1-1/2 in": {
        "I.D.Sch-07": "1.728 in",
        "I.D.Sch-10": "1.682 in",
        "I.D.Sch-40": "1.610 in",
        "Outside Diameter": "1.900 in",
        "Capacity Sch-07": "0.118 gal/ft",
        "Capacity Sch-10": "0.115 gal/ft",
        "Capacity Sch-40": "0.106 gal/ft",
    },
    "2 in": {
        "I.D.Sch-07": "2.203 in",
        "I.D.Sch-10": "2.157 in",
        "I.D.Sch-40": "2.067 in",
        "Outside Diameter": "2.375 in",
        "Capacity Sch-07": "0.195 gal/ft",
        "Capacity Sch-10": "0.190 gal/ft",
        "Capacity Sch-40": "0.174 gal/ft",
    },
    "2-1/2 in": {
        "I.D.Sch-07": "2.703 in",
        "I.D.Sch-10": "2.635 in",
        "I.D.Sch-40": "2.469 in",
        "Outside Diameter": "2.875 in",
        "Capacity Sch-07": "0.291 gal/ft",
        "Capacity Sch-10": "0.283 gal/ft",
        "Capacity Sch-40": "0.248 gal/ft",
    },
    "3 in": {
        "I.D.Sch-07": "3.314 in",
        "I.D.Sch-10": "3.260 in",
        "I.D.Sch-40": "3.068 in",
        "Outside Diameter": "3.500 in",
        "Capacity Sch-07": "0.445 gal/ft",
        "Capacity Sch-10": "0.433 gal/ft",
        "Capacity Sch-40": "0.383 gal/ft",
    },
    "4 in": {
        "I.D.Sch-07": "4.310 in",
        "I.D.Sch-10": "4.260 in",
        "I.D.Sch-40": "4.026 in",
        "Outside Diameter": "4.500 in",
        "Capacity Sch-07": "0.760 gal/ft",
        "Capacity Sch-10": "0.740 gal/ft",
        "Capacity Sch-40": "0.660 gal/ft",
    },
    "6 in": {
        "I.D.Sch-07": "NA",
        "I.D.Sch-10": "6.357 in",
        "I.D.Sch-40": "6.065 in",
        "Outside Diameter": "6.625 in",
        "Capacity Sch-07": "1.695 gal/ft",
        "Capacity Sch-10": "1.649 gal/ft",
        "Capacity Sch-40": "1.501 gal/ft",
    },
    "8 in": {
        "I.D.Sch-07": "NA",
        "I.D.Sch-10": "8.249 in",
        "I.D.Sch-40": "NA",
        "Outside Diameter": "8.625 in",
        "Capacity Sch-07": "2.855 gal/ft",
        "Capacity Sch-10": "2.776 gal/ft",
        "Capacity Sch-40": "2.660 gal/ft",
    },
    "10 in": {
        "I.D.Sch-07": "NA",
        "I.D.Sch-10": "NA",
        "I.D.Sch-40": "10.020 in",
        "Outside Diameter": "10.750 in",
        "Capacity Sch-07": "NA",
        "Capacity Sch-10": "NA",
        "Capacity Sch-40": "4.170 gal/ft",
    },
}

data = pipe_data[pipe_size]

st.subheader(f"Selected Pipe: {pipe_size}")

# ===== PRIMEIRA TABELA =====
col1, col2, col3 = st.columns(3)

with col1:
    st.text_input("I.D.Sch-07", value=data["I.D.Sch-07"], disabled=True)
    st.text_input("I.D.Sch-10", value=data["I.D.Sch-10"], disabled=True)
    st.text_input("I.D.Sch-40", value=data["I.D.Sch-40"], disabled=True)

with col2:
    st.text_input("Capacity Sch-07", value=data["Capacity Sch-07"], disabled=True)
    st.text_input("Capacity Sch-10", value=data["Capacity Sch-10"], disabled=True)
    st.text_input("Capacity Sch-40", value=data["Capacity Sch-40"], disabled=True)

with col3:
    st.text_input("Outside Diameter", value=data["Outside Diameter"], disabled=True)

st.divider()

# ===== SELEÇÃO DO RISER =====
riser_size = st.selectbox(
    "Select Riser Size:",
    ["1/2 in", "3/4 in", "1 in", "1-1/4 in", "1-1/2 in", "2 in", "2-1/2 in", "3 in", "4 in", "6 in", "8 in"]
)

st.subheader(f"Selected Riser: {riser_size}")

# ===== TABELAS RISER =====
tol_table = {
    "1-1/4 in": {"1/2 in": "1 in", "3/4 in": "1 in", "1 in": "1 in"},
    "1-1/2 in": {"1/2 in": "1-1/4 in", "3/4 in": "1-1/4 in", "1 in": "1-1/4 in", "1-1/4 in": "1-1/4 in"},
    "2 in": {"1/2 in": "1-1/2 in", "3/4 in": "1-1/2 in", "1 in": "1-1/2 in", "1-1/4 in": "1-1/2 in"},
    "2-1/2 in": {"1/2 in": "1-3/4 in", "3/4 in": "1-3/4 in", "1 in": "1-3/4 in", "1-1/4 in": "2 in", "1-1/2 in": "2 in", "2 in": "2 in"},
    "3 in": {"1/2 in": "2 in", "3/4 in": "2 in", "1 in": "2 in", "1-1/4 in": "2 in", "1-1/2 in": "2-1/2 in", "2 in": "2-1/2 in", "2-1/2 in": "2-1/2 in"},
    "4 in": {"1/2 in": "2-1/2 in", "3/4 in": "2-1/2 in", "1 in": "2-1/2 in", "1-1/4 in": "2-1/2 in", "1-1/2 in": "2-3/4 in", "2 in": "3 in", "2-1/2 in": "3 in", "3 in": "3-1/2 in"},
    "6 in": {"1/2 in": "3-1/2 in", "3/4 in": "3-1/2 in", "1 in": "3-1/2 in", "1-1/4 in": "3-1/2 in", "1-1/2 in": "3-3/4 in", "2 in": "4 in", "2-1/2 in": "4 in", "3 in": "4-1/2 in", "4 in": "4-3/4 in"},
    "8 in": {"1/2 in": "4-1/2 in", "3/4 in": "4-1/2 in", "1 in": "4-1/2 in", "1-1/4 in": "4-1/2 in", "1-1/2 in": "4-3/4 in", "2 in": "5 in", "2-1/2 in": "5 in", "3 in": "5-1/2 in", "4 in": "4-3/4 in"},
}

stubby_table = {
    "1-1/4 in": {"1 in": "3-3/4 in", "1-1/4 in": "3-3/4 in"},
    "1-1/2 in": {"1 in": "4 in", "1-1/4 in": "4 in", "1-1/2 in": "4 in"},
    "2 in": {"1 in": "4-1/4 in", "1-1/4 in": "4-1/4 in", "1-1/2 in": "4-1/4 in", "2 in": "4-1/4 in"},
    "2-1/2 in": {"1 in": "4-1/2 in", "1-1/4 in": "4-1/2 in", "1-1/2 in": "4-1/2 in", "2 in": "4-1/2 in", "2-1/2 in": "4-1/2 in"},
    "3 in": {"1 in": "4-3/4 in", "1-1/4 in": "4-3/4 in", "1-1/2 in": "4-3/4 in", "2 in": "4-3/4 in", "2-1/2 in": "4-3/4 in", "3 in": "4-3/4 in"},
    "4 in": {"1 in": "5-1/4 in", "1-1/4 in": "5-1/4 in", "1-1/2 in": "5-1/4 in", "2 in": "5-1/4 in", "2-1/2 in": "5-1/4 in", "3 in": "5-1/4 in", "4 in": "6-1/4 in"},
    "6 in": {"1 in": "6-1/4 in", "1-1/4 in": "6-1/4 in", "1-1/2 in": "6-1/4 in", "2 in": "6-1/4 in", "2-1/2 in": "6-1/4 in", "3 in": "6-1/4 in", "4 in": "7-1/4 in", "6 in": "7-1/4 in"},
    "8 in": {"1 in": "7-1/4 in", "1-1/4 in": "7-1/4 in", "1-1/2 in": "7-1/4 in", "2 in": "7-1/4 in", "2-1/2 in": "7-1/4 in", "3 in": "7-1/4 in", "4 in": "8-1/4 in", "6 in": "8-1/4 in", "8 in": "8-1/4 in"},
}

riser_data = {}

for main_pipe in tol_table:
    all_risers = set(tol_table.get(main_pipe, {}).keys()) | set(stubby_table.get(main_pipe, {}).keys())

    for riser in all_risers:
        riser_data[(main_pipe, riser)] = {
            "T_O_L_Riser": tol_table.get(main_pipe, {}).get(riser, "NA"),
            "Stubby_Riser": stubby_table.get(main_pipe, {}).get(riser, "NA"),
        }

result = riser_data.get((pipe_size, riser_size), {"T_O_L_Riser": "NA", "Stubby_Riser": "NA"})

st.subheader("Riser Results")

col4, col5 = st.columns(2)

with col4:
    st.image("assets/tol.png", use_container_width=True)
    st.text_input("T_O_L_Riser (X)", value=result["T_O_L_Riser"], disabled=True)

with col5:
    st.image("assets/stubby.png", use_container_width=True)
    st.text_input("Stubby_Riser (X)", value=result["Stubby_Riser"], disabled=True)

# ===== C-FACTOR TABLE =====
st.divider()
st.subheader("C-Factor Reference Table")

c_factor_data = [
    ["WET & DELUGE", "SCH-10/40", "120"],
    ["WET & DELUGE", "SCH-5/7", "120"],
    ["DRY/PRE-ACT", "SCH-10/40", "100"],
    ["DRY/PRE-ACT", "SCH-5/7", "100"],
    ["ALL USES", "GALVANIZED", "120"],
    ["ALL USES", "DUCT. IRON", "140"],
    ["ALL USES", "PLASTIC", "150"],
]

col_a, col_b, col_c = st.columns([2, 2, 1])

with col_a:
    st.markdown("**System Type**")
with col_b:
    st.markdown("**Pipe**")
with col_c:
    st.markdown("**C-Factor**")

for i, row in enumerate(c_factor_data):
    col_a, col_b, col_c = st.columns([2, 2, 1])

    with col_a:
        st.text_input(
            "",
            value=row[0],
            disabled=True,
            label_visibility="collapsed",
            key=f"system_{i}"
        )

    with col_b:
        st.text_input(
            "",
            value=row[1],
            disabled=True,
            label_visibility="collapsed",
            key=f"pipe_{i}"
        )

    with col_c:
        st.text_input(
            "",
            value=row[2],
            disabled=True,
            label_visibility="collapsed",
            key=f"cfactor_{i}"
        )

st.divider()

st.write("Values:")

st.write({
    "Selected Pipe": pipe_size,
    "I.D.Sch-07": data["I.D.Sch-07"],
    "I.D.Sch-10": data["I.D.Sch-10"],
    "I.D.Sch-40": data["I.D.Sch-40"],
    "Capacity Sch-07": data["Capacity Sch-07"],
    "Capacity Sch-10": data["Capacity Sch-10"],
    "Capacity Sch-40": data["Capacity Sch-40"],
    "Outside Diameter": data["Outside Diameter"],
    "Selected Riser": riser_size,
    "T_O_L_Riser (X)": result["T_O_L_Riser"],
    "Stubby_Riser (X)": result["Stubby_Riser"],
})