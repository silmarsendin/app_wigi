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
# ================================================================
# HANGER ROD CALCULATOR — SLOPED ROOF / BUILDING
# Logic based on the Hanger Rod Calculator spreadsheet.
# All elevations are entered as feet + inches and converted to decimal feet.
# ================================================================
st.divider()
st.header("Hanger Rod Calculator")
st.caption(
    "Calculates the roof elevation at the pipe location by linear interpolation, "
    "then determines the vertical distance from the pipe centerline to the roof."
)
st.image("assets/rod.png", use_container_width=True)

# Takeout values from the spreadsheet (inches)
hanger_takeout_table = {
    "1 in": 1.75,
    "1-1/4 in": 2.00,
    "1-1/2 in": 2.25,
    "2 in": 2.25,
    "2-1/2 in": 2.75,
    "3 in": 3.00,
    "3-1/2 in": 3.50,
    "4 in": 3.75,
    "5 in": 4.50,
    "6 in": 5.50,
    "8 in": 7.00,
}


def feet_and_inches_input(label, default_ft=0.0, default_in=0.0, key_prefix=""):
    """Display feet and inches fields and return the value in decimal feet."""
    ft_col, in_col = st.columns(2)
    with ft_col:
        feet = st.number_input(
            f"{label} — ft",
            min_value=0.0,
            value=float(default_ft),
            step=1.0,
            format="%.2f",
            key=f"{key_prefix}_ft",
        )
    with in_col:
        inches = st.number_input(
            f"{label} — in",
            min_value=0.0,
            value=float(default_in),
            step=0.125,
            format="%.3f",
            key=f"{key_prefix}_in",
        )
    return feet + inches / 12.0


hanger_pipe_size = st.selectbox(
    "Pipe Size:",
    list(hanger_takeout_table.keys()),
    index=2,
    key="hanger_pipe_size",
)

input_col1, input_col2 = st.columns(2)

with input_col1:
    low_side_tos = feet_and_inches_input(
        "Low Side TOS", default_ft=26, default_in=6, key_prefix="low_side_tos"
    )
    high_side_tos = feet_and_inches_input(
        "High Side TOS", default_ft=28, default_in=9.5, key_prefix="high_side_tos"
    )
    building_length = feet_and_inches_input(
        "Building Length", default_ft=109, default_in=0, key_prefix="building_length"
    )

with input_col2:
    distance_from_low_side = feet_and_inches_input(
        "Distance From Low Side",
        default_ft=84,
        default_in=10.5,
        key_prefix="distance_from_low_side",
    )
    pipe_elevation = feet_and_inches_input(
        "Pipe Centerline Elevation",
        default_ft=11,
        default_in=0,
        key_prefix="pipe_elevation",
    )

# ===== SLOPED ROOF CALCULATIONS =====
takeout_in = hanger_takeout_table[hanger_pipe_size]

if building_length <= 0:
    st.error("Building Length must be greater than zero.")
else:
    # Same logic as the spreadsheet:
    # Slope (in/ft) = ((High TOS - Low TOS) * 12) / Building Length
    slope_in_per_ft = ((high_side_tos - low_side_tos) * 12.0) / building_length

    # Linear interpolation from the low side to the selected location.
    tos_at_location = low_side_tos + (
        distance_from_low_side * slope_in_per_ft / 12.0
    )

    # Vertical distance from pipe centerline to roof at that location.
    pipe_to_roof_ft = tos_at_location - pipe_elevation
    pipe_to_roof_in = pipe_to_roof_ft * 12.0

    # Rod length deducts the hanger takeout, matching the spreadsheet logic.
    rod_length_in = pipe_to_roof_in - takeout_in
    rounded_rod_in = round(rod_length_in * 2.0) / 2.0

    if distance_from_low_side > building_length:
        st.warning(
            "Distance From Low Side is greater than Building Length. "
            "The result is an extrapolation beyond the entered building length."
        )

    if pipe_to_roof_ft < 0:
        st.error(
            "The pipe centerline elevation is above the calculated roof elevation "
            "at this location. Please review the inputs."
        )

    st.markdown("### Results")
    result_col1, result_col2, result_col3 = st.columns(3)

    with result_col1:
        st.metric("Slope", f"{slope_in_per_ft:.3f} in/ft")
        st.metric("Takeout", f"{takeout_in:.2f} in")

    with result_col2:
        st.metric("TOS at Location", f"{tos_at_location:.3f} ft")
        st.metric("Pipe-to-Roof Distance", f"{pipe_to_roof_in:.2f} in")

    with result_col3:
        st.metric("Rod Length", f"{rod_length_in:.2f} in")
        st.metric("Rounded Rod", f"{rounded_rod_in:.2f} in")

    st.caption(
        "TOS at Location = Low Side TOS + "
        "(Distance From Low Side × roof slope). "
        "Rod Length = Pipe-to-Roof Distance − Takeout."
    )