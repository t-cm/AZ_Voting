import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from typing import Tuple
from dataclasses import dataclass
import random

from data import generate_data  # This function should load macrodata.csv

@dataclass
class AnalyticsConfig:
    """Configuration for analytics visualization"""
    # Preferred column for voter status (should be boolean or convertible to boolean)
    VOTER_STATUS_COL: str = "Voter Status"  
    # Column for registration date from our new schema
    REGISTRATION_DATE_COL: str = "Registration Date"
    PARTY_COL: str = "Party"
    # Use the state column from the CSV (choose either "State -MyData." or "state")
    STATE_COL: str = "State -MyData."
    DATE_RANGES: dict = None

    def __post_init__(self):
        now = datetime.now()
        self.DATE_RANGES = {
            "month": now - timedelta(days=30),
            "year": now - timedelta(days=365)
        }

def safe_percentage(part: int, whole: int) -> float:
    """Safely calculate percentage"""
    return (part / whole * 100) if whole else 0

def get_registration_metrics(df: pd.DataFrame, config: AnalyticsConfig) -> dict:
    """Calculate registration metrics"""
    return {
        "total": len(df),
        "last_month": df[df[config.REGISTRATION_DATE_COL] >= config.DATE_RANGES["month"]].shape[0],
        "last_year": df[df[config.REGISTRATION_DATE_COL] >= config.DATE_RANGES["year"]].shape[0]
    }

def get_voting_metrics(df: pd.DataFrame, config: AnalyticsConfig) -> Tuple[float, float]:
    """Calculate voting percentage metrics"""
    total_registrants = len(df)
    total_voted = df[config.VOTER_STATUS_COL].sum()  # Sum of True values
    total_voted_pct = safe_percentage(total_voted, total_registrants)

    # Calculate percentage for new registrants (last year)
    new_df = df[df[config.REGISTRATION_DATE_COL] >= config.DATE_RANGES["year"]]
    new_total = len(new_df)
    new_voted = new_df[config.VOTER_STATUS_COL].sum()  # Sum of True values
    new_voted_pct = safe_percentage(new_voted, new_total)

    return total_voted_pct, new_voted_pct

def create_monthly_registrations_chart(df: pd.DataFrame, config: AnalyticsConfig, template: str) -> px.bar:
    """Create monthly registrations bar chart"""
    monthly_counts = (
        df[config.REGISTRATION_DATE_COL]
        .dt.to_period("M")
        .value_counts()
        .sort_index()
    )
    monthly_data = pd.DataFrame({
        "Month": monthly_counts.index.astype(str),
        "Count": monthly_counts.values
    })
    return px.bar(
        monthly_data,
        x="Month",
        y="Count",
        title="Registrations per Month",
        template=template
    )

def create_party_distribution_chart(df: pd.DataFrame, config: AnalyticsConfig, template: str) -> px.pie:
    """Create party distribution pie chart"""
    if config.PARTY_COL not in df.columns:
        return None
    party_data = df[config.PARTY_COL].value_counts()
    party_df = pd.DataFrame({
        "Party": party_data.index,
        "Count": party_data.values
    })
    return px.pie(
        party_df,
        names="Party",
        values="Count",
        title="Party Distribution",
        template=template
    )

def create_cumulative_turnout_chart(df: pd.DataFrame, config: AnalyticsConfig, template: str) -> px.line:
    """Create cumulative turnout line chart"""
    df_sorted = df.sort_values(config.REGISTRATION_DATE_COL)
    df_sorted["cumulative_voted"] = df_sorted[config.VOTER_STATUS_COL].cumsum()  # Cumulative sum of True values
    return px.line(
        df_sorted,
        x=config.REGISTRATION_DATE_COL,
        y="cumulative_voted",
        title="Cumulative Voter Turnout Over Time",
        template=template
    )

def create_voter_percentage_by_year_chart(df: pd.DataFrame, config: AnalyticsConfig, template: str) -> px.line:
    """Create a line chart showing voter percentage by registration year"""
    df = df.copy()  # Avoid modifying the original DataFrame
    df["Year"] = df[config.REGISTRATION_DATE_COL].dt.year
    grouped = df.groupby("Year")[config.VOTER_STATUS_COL].agg(["sum", "count"]).reset_index()
    grouped.rename(columns={"sum": "Voted", "count": "Total"}, inplace=True)
    grouped["Voter_Percentage"] = grouped["Voted"] / grouped["Total"] * 100
    return px.line(
        grouped,
        x="Year",
        y="Voter_Percentage",
        title="Voter Turnout by Registration Year",
        template=template,
        markers=True,
        labels={"Voter_Percentage": "Voter Percentage (%)", "Year": "Registration Year"}
    )

def create_cumulative_registrants_chart(df: pd.DataFrame, config: AnalyticsConfig, template: str) -> px.line:
    """Create cumulative registrants line chart"""
    df_sorted = df.sort_values(config.REGISTRATION_DATE_COL)
    df_sorted["cumulative_registrants"] = range(1, len(df_sorted) + 1)
    return px.line(
        df_sorted,
        x=config.REGISTRATION_DATE_COL,
        y="cumulative_registrants",
        title="Cumulative Registrants Over Time",
        template=template
    )

def app():
    st.title("Voter to Analytics")

    # Initialize configuration.
    config = AnalyticsConfig()

    # Load data from macrodata.csv using the generate_data function.
    df = generate_data()

    # Assert that the expected voter status column is present.
    assert config.VOTER_STATUS_COL in df.columns, (
        f"Expected column '{config.VOTER_STATUS_COL}' not found in data. "
        f"Available columns: {df.columns.tolist()}"
    )

    # --- Ensure the CSV has the fields needed for analytics ---
    # If the CSV does not include a registration date, generate a random one (within the past 5 years).
    if config.REGISTRATION_DATE_COL not in df.columns:
        df[config.REGISTRATION_DATE_COL] = [
            datetime.now() - timedelta(days=random.randint(0, 5 * 365))
            for _ in range(len(df))
        ]
    else:
        # Ensure the registration date column is in datetime format.
        df[config.REGISTRATION_DATE_COL] = pd.to_datetime(df[config.REGISTRATION_DATE_COL])

    # Convert the voter status column to boolean if needed.
    if df[config.VOTER_STATUS_COL].dtype == object:
        df[config.VOTER_STATUS_COL] = df[config.VOTER_STATUS_COL].apply(
            lambda x: True if str(x).strip().lower() == "true" else False
        )

    # Get the Plotly template based on the current theme.
    template = "plotly_dark" if st.get_option("theme.base") == "dark" else "plotly_white"

    # Display registration metrics.
    metrics = get_registration_metrics(df, config)
    cols = st.columns(3)
    cols[0].metric("Registrants (Last Month)", f"{metrics['last_month']:,}")
    cols[1].metric("Registrants (Last Year)", f"{metrics['last_year']:,}")
    cols[2].metric("Total Registrants", f"{metrics['total']:,}")

    st.markdown("---")

    # Display voting metrics.
    total_voted_pct, new_voted_pct = get_voting_metrics(df, config)
    cols = st.columns(2)
    cols[0].metric("All Registrants Voted (%)", f"{total_voted_pct:.1f}%")
    cols[1].metric("New Registrants Voted (%)", f"{new_voted_pct:.1f}%")

    st.markdown("---")

    # Display charts. You can add or remove any of these charts.
    charts = [
        create_voter_percentage_by_year_chart(df, config, template),
        create_monthly_registrations_chart(df, config, template),
    ]

    for chart in charts:
        if chart is not None:
            st.markdown("---")
            st.plotly_chart(chart, use_container_width=True)
