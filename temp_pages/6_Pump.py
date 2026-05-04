import streamlit as st
from utils.layout import show_sidebar_branding

st.set_page_config(page_title="Pump", page_icon="🚒", layout="wide")

show_sidebar_branding()

st.title("Fire Pump Sizing")

# ===== DATA TABLE =====
pump_data = {
    "250 GPM": {
        "Suction Size": '3-1/2"',
        "Discharge Size": '3"',
        "Test Header Size": '3"',
        "Number of Outlet": "1"
    },
    "500 GPM": {
        "Suction Size": '5"',
        "Discharge Size": '5"',
        "Test Header Size": '4"',
        "Number of Outlet": "2"
    },
    "750 GPM": {
        "Suction Size": '6"',
        "Discharge Size": '6"',
        "Test Header Size": '6"',
        "Number of Outlet": "3"
    },
    "1000 GPM": {
        "Suction Size": '8"',
        "Discharge Size": '6"',
        "Test Header Size": '6"',
        "Number of Outlet": "4"
    },
    "1250 GPM": {
        "Suction Size": '8"',
        "Discharge Size": '8"',
        "Test Header Size": '8"',
        "Number of Outlet": "6"
    },
    "1500 GPM": {
        "Suction Size": '8"',
        "Discharge Size": '8"',
        "Test Header Size": '8"',
        "Number of Outlet": "6"
    },
    "2000 GPM": {
        "Suction Size": '10"',
        "Discharge Size": '10"',
        "Test Header Size": '8"',
        "Number of Outlet": "6"
    },
    "2500 GPM": {
        "Suction Size": '10"',
        "Discharge Size": '10"',
        "Test Header Size": '10"',
        "Number of Outlet": "8"
    },
    "3000 GPM": {
        "Suction Size": '12"',
        "Discharge Size": '12"',
        "Test Header Size": '10"',
        "Number of Outlet": "10"
    }
}

# ===== SELECTBOX =====
pump_flow = st.selectbox(
    "Select Pump Flow:",
    list(pump_data.keys())
)

selected_data = pump_data[pump_flow]

st.subheader("Pump Sizing Information")

# ===== TABLE HEADER =====
col1, col2, col3, col4, col5 = st.columns([2.4, 1, 1, 1, 1])

with col1:
    st.markdown("**Photo**")
with col2:
    st.markdown("**Suction Size**")
with col3:
    st.markdown("**Discharge Size**")
with col4:
    st.markdown("**Test Header Size**")
with col5:
    st.markdown("**Number of Outlet**")

# ===== TABLE ROW =====
col1, col2, col3, col4, col5 = st.columns([2.4, 1, 1, 1, 1])

with col1:
    st.image("assets/pump.png", width=240)

with col2:
    st.text_input(
        "Suction Size",
        value=selected_data["Suction Size"],
        disabled=True,
        label_visibility="collapsed"
    )

with col3:
    st.text_input(
        "Discharge Size",
        value=selected_data["Discharge Size"],
        disabled=True,
        label_visibility="collapsed"
    )

with col4:
    st.text_input(
        "Test Header Size",
        value=selected_data["Test Header Size"],
        disabled=True,
        label_visibility="collapsed"
    )

with col5:
    st.text_input(
        "Number of Outlet",
        value=selected_data["Number of Outlet"],
        disabled=True,
        label_visibility="collapsed"
    )

st.divider()

st.title("Notes")
st.write("Increase test header 1 pipe size if header piping is over 15' in length.")
st.write("BFP shall be located minimum of 10 pipe diameters from pump suction flange.")
st.write("Ells and tees shall be located minimum of 10 pipe diameters from pump suction flange (horizontal split case pumps only).")