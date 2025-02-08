import streamlit as st
import pandas as pd
import pydeck as pdk
from dataclasses import dataclass

@dataclass
class MapConfig:
    """Configuration for map visualization"""
    LARGE_DATASET_THRESHOLD: int = 999
    DEFAULT_ZOOM: int = 6
    DEFAULT_PITCH: int = 0
    SCATTER_RADIUS_M: int = 500
    SCATTER_MIN_PIXELS: int = 10
    SCATTER_MAX_PIXELS: int = 50
    HEXAGON_RADIUS: int = 1000
    ELEVATION_SCALE: int = 50
    DOT_COLOR: tuple = (200, 30, 0, 160)
    
    # Map style configurations
    DEFAULT_STYLE: str = None  # Default PyDeck style
    SATELLITE_STYLE: str = 'mapbox://styles/mapbox/satellite-v9'
    STREET_STYLE: str = 'mapbox://styles/mapbox/light-v9'

@st.cache_data
def load_microdata() -> pd.DataFrame:
    """Load voter data from microdata.csv."""
    df = pd.read_csv("microdata.csv")
    return df

@st.cache_data
def create_layer(df: pd.DataFrame, config: MapConfig) -> pdk.Layer:
    """Create and cache visualization layer."""
    if len(df) > config.LARGE_DATASET_THRESHOLD:
        return pdk.Layer(
            "HexagonLayer",
            data=df,
            get_position='[lon, lat]',
            radius=config.HEXAGON_RADIUS,
            elevation_scale=config.ELEVATION_SCALE,
            extruded=True,
            pickable=True
        )
    return pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position='[lon, lat]',
        get_fill_color=list(config.DOT_COLOR),
        get_radius=config.SCATTER_RADIUS_M,
        radius_min_pixels=config.SCATTER_MIN_PIXELS,
        radius_max_pixels=config.SCATTER_MAX_PIXELS,
        pickable=True
    )

@st.cache_data
def create_deck(df: pd.DataFrame, config: MapConfig, map_style: str = None) -> pdk.Deck:
    """Create and cache the deck configuration."""
    deck_args = {
        "initial_view_state": pdk.ViewState(
            latitude=df['lat'].mean(),
            longitude=df['lon'].mean(),
            zoom=config.DEFAULT_ZOOM,
            pitch=config.DEFAULT_PITCH
        ),
        "layers": [create_layer(df, config)],
        "tooltip": {
            "html": (
                "<b>{First Name -MyData} {Last Name -MyData}</b><br/>"
                "Address: {Address -MyData} {Address Line 2 -MyData}, {City -MyData}, {State -MyData.} {Zip –MyData}<br/>"
                "Phone: {Phone}<br/>"
                "Email: {Email -MyData}<br/>"
                "Registration Date: {Registration Date}<br/>"
                "Voter Status: {Voter Status}<br/>"
            ),
            "style": {"color": "white"}
        }
    }
    if map_style:
        deck_args["map_style"] = map_style
    return pdk.Deck(**deck_args)

def app():
    st.title("Scaled Registrant Map")
    
    config = MapConfig()
    
    # Map style selector
    map_style = st.selectbox(
        "Select Map Style",
        options=["Default", "Street View", "Satellite"],
        index=0
    )
    selected_style = None
    if map_style == "Street View":
        selected_style = config.STREET_STYLE
    elif map_style == "Satellite":
        selected_style = config.SATELLITE_STYLE
    
    with st.spinner("Loading voter data from microdata.csv..."):
        df = load_microdata()
        if df.empty:
            st.error("No data available in microdata.csv.")
            return
        deck = create_deck(df, config, selected_style)
        st.pydeck_chart(deck)

if __name__ == "__main__":
    app()
