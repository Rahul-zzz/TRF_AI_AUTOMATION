import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from modules.pod.placeholder import get_status

st.set_page_config(page_title="POD — TR AI Operations Platform", page_icon="📦", layout="wide")
status = get_status()

st.title("📦 POD")
st.info(f"**{status['status']}**")
st.write(
    "The Proof of Delivery module is not implemented in this version. "
    "No POD data, statistics, or workflows are simulated here."
)
