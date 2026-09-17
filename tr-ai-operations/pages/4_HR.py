import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from modules.hr.placeholder import get_status

st.set_page_config(page_title="HR — TR AI Operations Platform", page_icon="👥", layout="wide")
status = get_status()

st.title("👥 HR")
st.info(f"**{status['status']}**")
st.write(
    "The HR module is not implemented in this version. "
    "No employee data or statistics are simulated here."
)
