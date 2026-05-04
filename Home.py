import streamlit as st
from utils.layout import show_sidebar_branding

st.set_page_config(
    page_title="Wiginton Tools",
    page_icon="🧰",
    layout="wide"
)

show_sidebar_branding()

st.title("Wiginton Tools")
st.write("Welcome to the Wiginton internal application.")


# ===== CONTEÚDO =====
st.title("Welcome")
st.write("This application contains the following tools:")

st.markdown("""
- Pipes Sizes  
- Hanger  
- Conections  
- Valves
- Pump
- Calculation
- Workflow  
""")

st.title("Note:")
st.write("The images provided in this app are intended solely as visual aids to support learning and memorization. These illustrations were generated using artificial intelligence and may contain minor technical inaccuracies or inconsistencies. Always refer to the applicable codes, standards, manufacturer data sheets, and official technical documentation as the primary and authoritative sources for design, installation, and compliance decisions.")

