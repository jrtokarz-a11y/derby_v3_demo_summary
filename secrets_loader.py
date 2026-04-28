from __future__ import annotations

import os

def load_streamlit_secrets_into_env() -> None:
    """
    Streamlit Community Cloud stores secrets in st.secrets.
    The app code reads os.getenv(...), so this bridges Streamlit secrets into environment variables.
    Local runs still work with .env.
    """
    try:
        import streamlit as st
        for key, value in st.secrets.items():
            if isinstance(value, (str, int, float, bool)) and key not in os.environ:
                os.environ[key] = str(value)
    except Exception:
        # Local runs without secrets are fine.
        pass
