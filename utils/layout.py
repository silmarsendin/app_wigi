import streamlit as st
import base64
from pathlib import Path

# Caminho base do projeto (raiz)
BASE_DIR = Path(__file__).resolve().parent.parent


def get_base64_image(image_path: str) -> str:
    image_file = BASE_DIR / image_path
    with open(image_file, "rb") as f:
        return base64.b64encode(f.read()).decode()


def show_sidebar_branding():
    logo_base64 = get_base64_image("assets/logo.png")

    st.markdown(
        """
        <style>
        [data-testid="stSidebarNav"] {
            margin-top: 170px;
        }

        [data-testid="stSidebar"] .sidebar-brand {
            position: fixed;
            top: 20px;
            width: 220px;
            text-align: center;
            z-index: 999999;
        }

        [data-testid="stSidebar"] .sidebar-brand img {
            max-width: 180px;
            margin-bottom: 10px;
        }

        [data-testid="stSidebar"] .sidebar-brand h2 {
            font-size: 28px;
            font-weight: 700;
            margin: 0;
            padding: 0;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.sidebar.markdown(
        f"""
        <div class="sidebar-brand">
            <img src="data:image/png;base64,{logo_base64}">
            <h2>Wiginton App</h2>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.sidebar.markdown(
        "<p style='font-size:10px; text-align:center; color:gray;'>Developed by Silmar Sendin</p>",
        unsafe_allow_html=True
    )