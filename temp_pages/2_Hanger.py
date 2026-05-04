import streamlit as st
from utils.layout import show_sidebar_branding

st.set_page_config(page_title="Hanger", page_icon="🔩", layout="wide")

show_sidebar_branding()

st.title("Hanger")

# ===== SELEÇÃO DE DIÂMETRO =====
pipe_size = st.selectbox(
    "Select Pipe Size:",
    ["1 in", "1-1/4 in", "1-1/2 in", "2 in", "2-1/2 in", "3 in", "3-1/2 in", "4 in", "5 in", "6 in", "8 in"]
)

# ===== SELEÇÃO DE TIPO DE TUBO =====
pipe_type = st.selectbox(
    "Select Pipe Type:",
    [
        "Steel pipe except threaded lightwall",
        "Threaded lightwall steel pipe",
        "Copper tube",
        "CPVC",
        "Ductile-iron pipe"
    ]
)

# ===== DADOS DO HANGER =====
hanger_data = {
    "1 in":     {"A": '3/8"', "B": '1-3/4"', "M": '2-3/8"', "N": '3-1/4"', "E": '1"'},
    "1-1/4 in": {"A": '3/8"', "B": '2"', "M": '2-3/8"', "N": '3-3/4"', "E": '1"'},
    "1-1/2 in": {"A": '3/8"', "B": '2-1/4"', "M": '3"', "N": '4-1/4"', "E": '1-1/4"'},
    "2 in":     {"A": '3/8"', "B": '2-1/2"', "M": '3-1/4"', "N": '4-1/2"', "E": '1-1/4"'},
    "2-1/2 in": {"A": '3/8"', "B": '2-3/4"', "M": '3-7/8"', "N": '5-3/8"', "E": '1-3/8"'},
    "3 in":     {"A": '3/8"', "B": '3"', "M": '4-1/4"', "N": '6-1/8"', "E": '1-3/8"'},
    "3-1/2 in": {"A": '3/8"', "B": '3-1/2"', "M": '4-5/8"', "N": '5-5/8"', "E": '1-1/2"'},
    "4 in":     {"A": '3/8"', "B": '3-3/4"', "M": '5"', "N": '7-1/4"', "E": '1-1/2"'},
    "5 in":     {"A": '1/2"', "B": '4-1/2"', "M": '5-1/2"', "N": '8-1/2"', "E": '1-5/8"'},
    "6 in":     {"A": '1/2"', "B": '5-1/2"', "M": '6-1/8"', "N": '10-1/4"', "E": '2-1/4"'},
    "8 in":     {"A": '1/2"', "B": '7"', "M": '8-7/8"', "N": '12-7/8"', "E": '2-3/4"'},
}

# ===== TABELA DE DISTÂNCIA MÁXIMA =====
max_hanger_distance = {
    "Steel pipe except threaded lightwall": {
        "1 in": "12'-0\"", "1-1/4 in": "12'-0\"", "1-1/2 in": "15'-0\"", "2 in": "15'-0\"",
        "2-1/2 in": "15'-0\"", "3 in": "15'-0\"", "3-1/2 in": "15'-0\"", "4 in": "15'-0\"",
        "5 in": "15'-0\"", "6 in": "15'-0\"", "8 in": "15'-0\"",
    },
    "Threaded lightwall steel pipe": {
        "1 in": "12'-0\"", "1-1/4 in": "12'-0\"", "1-1/2 in": "12'-0\"", "2 in": "12'-0\"",
        "2-1/2 in": "12'-0\"", "3 in": "12'-0\"", "3-1/2 in": "NA", "4 in": "NA",
        "5 in": "NA", "6 in": "NA", "8 in": "NA",
    },
    "Copper tube": {
        "1 in": "8'-0\"", "1-1/4 in": "10'-0\"", "1-1/2 in": "12'-0\"", "2 in": "12'-0\"",
        "2-1/2 in": "12'-0\"", "3 in": "12'-0\"", "3-1/2 in": "15'-0\"", "4 in": "15'-0\"",
        "5 in": "15'-0\"", "6 in": "15'-0\"", "8 in": "15'-0\"",
    },
    "CPVC": {
        "1 in": "6'-0\"", "1-1/4 in": "6'-6\"", "1-1/2 in": "7'-0\"", "2 in": "8'-0\"",
        "2-1/2 in": "9'-0\"", "3 in": "10'-0\"", "3-1/2 in": "NA", "4 in": "NA",
        "5 in": "NA", "6 in": "NA", "8 in": "NA",
    },
    "Ductile-iron pipe": {
        "1 in": "NA", "1-1/4 in": "NA", "1-1/2 in": "NA", "2 in": "NA",
        "2-1/2 in": "NA", "3 in": "15'-0\"", "3-1/2 in": "NA", "4 in": "15'-0\"",
        "5 in": "NA", "6 in": "15'-0\"", "8 in": "15'-0\"",
    }
}

# ===== RESULTADOS =====
data = hanger_data[pipe_size]
max_distance = max_hanger_distance[pipe_type][pipe_size]

st.subheader(f"Selected Pipe Size: {pipe_size}")



# ===== LAYOUT =====
left_col, right_col = st.columns([1, 2])

with left_col:
    st.image("assets/hanger.png", use_container_width=True)

with right_col:
    st.text_input("A", value=data["A"], disabled=True)
    st.text_input("B", value=data["B"], disabled=True)
    st.text_input("M", value=data["M"], disabled=True)
    st.text_input("N", value=data["N"], disabled=True)
    st.text_input("E", value=data["E"], disabled=True)

st.divider()

st.image("assets/hangerd.png", use_container_width=True)
st.subheader(f"Pipe Type: {pipe_type}")
st.success(f"Maximum Distance Between Hangers: {max_distance}")

st.divider()

st.write("Hanger Dimensions:")
st.write(data)