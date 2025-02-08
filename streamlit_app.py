import streamlit as st
import tab1
import tab2
import tab3
st.cache_data.clear()

# Create two tabs with titles "1" and "2"
tabs = st.tabs(["Query", "Map", "Analyze"])

with tabs[0]:
    tab1.app()  # Call the function from tab1.py

with tabs[1]:
    tab2.app()  # Call the function from tab2.py

with tabs[2]:
    tab3.app()  # Call the function from tab2.py

