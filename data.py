import pandas as pd
import random
import uuid
from faker import Faker
import streamlit as st
import datetime


@st.cache_data
def generate_data():
    try:
        # Read the CSV file containing the voter data.
        df = pd.read_csv("macrodata.csv")
        return df
    except Exception as e:
        st.error(f"Error loading data from macrodata.csv: {e}")
        return pd.DataFrame()

