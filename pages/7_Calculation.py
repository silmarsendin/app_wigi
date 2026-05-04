import streamlit as st
from utils.layout import show_sidebar_branding

st.set_page_config(page_title="Calculation", page_icon="📋", layout="wide")

show_sidebar_branding()

st.title("Calculation")
st.write("This page will be used for calculation.")

# ===== PRESSURE / FLOW / K-FACTOR CALCULATOR =====
st.divider()
st.subheader("Hydraulic Formula Calculator")

# =========================================================
# LINE 1 — CALCULATE PRESSURE
# P = (Q / K)^2
# =========================================================
st.markdown("### Calculate Pressure")

col1, col2, col3 = st.columns(3)

with col1:
    flow_p = st.number_input(
        "Flow (Q)",
        min_value=0.0,
        value=0.0,
        step=1.0,
        format="%.2f",
        key="flow_p"
    )

with col2:
    k_p = st.number_input(
        "K Factor (K)",
        min_value=0.01,
        value=5.6,
        step=0.1,
        format="%.2f",
        key="k_p"
    )

pressure = (flow_p / k_p) ** 2 if k_p > 0 else 0.0

with col3:
    st.metric(
        label="Pressure (P)",
        value=f"{pressure:.2f} psi"
    )

# =========================================================
# LINE 2 — CALCULATE FLOW
# Q = K * sqrt(P)
# =========================================================
st.markdown("### Calculate Flow")

col4, col5, col6 = st.columns(3)

with col4:
    pressure_q = st.number_input(
        "Pressure (P)",
        min_value=0.0,
        value=0.0,
        step=1.0,
        format="%.2f",
        key="pressure_q"
    )

with col5:
    k_q = st.number_input(
        "K Factor (K)",
        min_value=0.01,
        value=5.6,
        step=0.1,
        format="%.2f",
        key="k_q"
    )

flow = k_q * (pressure_q ** 0.5) if pressure_q >= 0 else 0.0

with col6:
    st.metric(
        label="Flow (Q)",
        value=f"{flow:.2f} gpm"
    )

# =========================================================
# LINE 3 — CALCULATE K FACTOR
# K = Q / sqrt(P)
# =========================================================
st.markdown("### Calculate K Factor")

col7, col8, col9 = st.columns(3)

with col7:
    flow_k = st.number_input(
        "Flow (Q)",
        min_value=0.0,
        value=0.0,
        step=1.0,
        format="%.2f",
        key="flow_k"
    )

with col8:
    pressure_k = st.number_input(
        "Pressure (P)",
        min_value=0.01,
        value=1.0,
        step=1.0,
        format="%.2f",
        key="pressure_k"
    )

k_factor = flow_k / (pressure_k ** 0.5) if pressure_k > 0 else 0.0

with col9:
    st.metric(
        label="K Factor (K)",
        value=f"{k_factor:.2f}"
    )

# =========================================================
# LINE 4 — HAZEN-WILLIAMS FRICTION LOSS
# Pft = 4.52 × Q^1.85 / (C^1.85 × D^4.87)
# Total Loss = Pft × L
# =========================================================
st.divider()
st.markdown("### Hazen-Williams Friction Loss Calculator")

col10, col11, col12, col13, col14, col15 = st.columns(6)

with col10:
    hw_flow = st.number_input(
        "Flow (Q) GPM",
        min_value=0.0,
        value=0.0,
        step=1.0,
        format="%.2f",
        key="hw_flow"
    )

with col11:
    hw_c = st.number_input(
        "C Factor (C)",
        min_value=1.0,
        value=120.0,
        step=1.0,
        format="%.2f",
        key="hw_c"
    )

with col12:
    hw_d = st.number_input(
        "Internal Diameter (D) in",
        min_value=0.01,
        value=1.0,
        step=0.01,
        format="%.3f",
        key="hw_d"
    )

# ===== FRICTION LOSS PER FOOT =====
if hw_c > 0 and hw_d > 0:
    pft = 4.52 * (hw_flow ** 1.85) / ((hw_c ** 1.85) * (hw_d ** 4.87))
else:
    pft = 0.0

with col13:
    st.metric(
        label="Pft",
        value=f"{pft:.5f} psi/ft"
    )

with col14:
    hw_length = st.number_input(
        "Length (L) ft",
        min_value=0.0,
        value=0.0,
        step=1.0,
        format="%.2f",
        key="hw_length"
    )

# ===== TOTAL FRICTION LOSS =====
total_loss = pft * hw_length

with col15:
    st.metric(
        label="Total Loss",
        value=f"{total_loss:.2f} psi"
    )