"""Shared visible product branding for Streamlit pages."""
import streamlit as st


PRODUCT_NAME = "Leak Probe Water Leak Detection System"


def render_product_header() -> None:
    """Show the product name as the main page's large, left-aligned heading."""
    st.title(PRODUCT_NAME)
