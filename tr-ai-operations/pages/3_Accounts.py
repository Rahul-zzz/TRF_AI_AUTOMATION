import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from modules.accounts.placeholder import get_status

st.set_page_config(page_title="Accounts — TR AI Operations Platform", page_icon="💰", layout="wide")
status = get_status()

st.title("💰 Accounts")
st.info(f"**{status['status']}**")
st.write(
    "The Accounts module is not implemented in this version. "
    "No financial data or statistics are simulated here."
)
