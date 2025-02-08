import pandas as pd
from geopy.geocoders import Nominatim
import streamlit as st
from typing import Tuple, Optional
import logging
from geopy.exc import GeocoderUnavailable, GeocoderTimedOut
import time

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Arizona Boundary Constants
AZ_BOUNDS = {
    'lat': (31.332177, 37.004261),    # Latitude bounds for Arizona
    'lon': (-114.818169, -109.045223)   # Longitude bounds for Arizona
}

def create_geocoder():
    """
    Create a fresh geocoder instance with appropriate timeout settings.
    """
    return Nominatim(
        user_agent=f"voter_search_app_{int(time.time())}", 
        timeout=10
    )

def clean_zip_code(zip_code: str) -> str:
    """
    Clean and format zip code:
    - Remove any decimal points and trailing zeros
    - Ensure it's a 5-digit string
    """
    try:
        # Convert to float first to handle scientific notation
        zip_float = float(zip_code)
        # Convert to integer to remove decimal places
        zip_int = int(zip_float)
        # Format as 5-digit string
        return f"{zip_int:05d}"
    except (ValueError, TypeError):
        return ""

def attempt_geocode(address: str, max_retries: int = 5, retry_delay: int = 2) -> Optional[Tuple[float, float]]:
    """
    Attempt to geocode an address with retries on timeout.
    Returns None if all attempts fail.
    """
    geolocator = create_geocoder()
    
    for attempt in range(max_retries):
        if attempt > 0:
            # Exponential backoff
            sleep_time = retry_delay * (2 ** (attempt - 1))
            logger.info(f"Sleeping for {sleep_time} seconds before retry {attempt + 1}")
            time.sleep(sleep_time)
            
        try:
            logger.info(f"Attempting to geocode: '{address}'")
            location = geolocator.geocode(address)
            if location:
                logger.info(f"Successfully geocoded '{address}' -> (lat: {location.latitude}, lon: {location.longitude})")
                return location.latitude, location.longitude
            else:
                logger.info(f"No results found for '{address}'")
                
        except (GeocoderUnavailable, GeocoderTimedOut) as e:
            logger.warning(f"Attempt {attempt + 1}/{max_retries} failed for '{address}': {e}")
            continue
            
    logger.warning(f"All {max_retries} attempts failed for '{address}'")
    return None

def is_in_arizona(coords: Optional[Tuple[float, float]]) -> bool:
    """
    Check whether the given coordinates fall inside Arizona's bounds.
    """
    if not coords or None in coords:
        return False
    lat, lon = coords
    return (AZ_BOUNDS['lat'][0] <= lat <= AZ_BOUNDS['lat'][1] and
            AZ_BOUNDS['lon'][0] <= lon <= AZ_BOUNDS['lon'][1])

def clean_address_component(component) -> str:
    """
    Clean an address component by removing NaN values and standardizing format.
    """
    if pd.isna(component) or str(component).lower() == 'nan':
        return ''
    return str(component).strip()

def get_coords(row: pd.Series) -> Optional[Tuple[float, float]]:
    """
    Build a full address from the row and return its coordinates.
    Returns None if geocoding fails.
    """
    # Clean zip code first
    zip_code = clean_zip_code(str(row['Zip –MyData']))
    if not zip_code:
        logger.warning("Invalid or missing zip code")
        return None

    # Clean other address components
    street = clean_address_component(row['Address -MyData'])
    street2 = clean_address_component(row['Address Line 2 -MyData'])
    city = clean_address_component(row['City -MyData'])
    state = clean_address_component(row['State -MyData.'])

    # Try with full address first
    address_parts = [part for part in [street, street2, city, state, zip_code, 'USA'] if part]
    full_address = ', '.join(address_parts)
    
    coords = attempt_geocode(full_address)
    if coords and is_in_arizona(coords):
        return coords

    # Try with street number, city, state, zip
    if street and city:
        simple_address = f"{street}, {city}, {state}, {zip_code}, USA"
        coords = attempt_geocode(simple_address)
        if coords and is_in_arizona(coords):
            return coords

    # Try with just city, state, zip
    if city:
        city_address = f"{city}, {state}, {zip_code}, USA"
        coords = attempt_geocode(city_address)
        if coords and is_in_arizona(coords):
            return coords
    
    # Try with just zip code
    zip_address = f"{zip_code}, {state}, USA"
    coords = attempt_geocode(zip_address)
    if coords and is_in_arizona(coords):
        return coords
    
    logger.warning(f"Failed to geocode address '{full_address}'")
    return None

def main():
    try:
        df = pd.read_csv("macrodata.csv")
    except FileNotFoundError:
        logger.error("Error: macrodata.csv not found. Please run your data loader first.")
        return

    # Process only the first 20 rows with a deep copy
    df_micro = df.head(20).copy(deep=True)

    # Apply the geocoding with fallback logic
    coords_series = df_micro.apply(get_coords, axis=1)
    
    # Convert the list of tuples into two separate columns, handling None values
    df_micro[['lat', 'lon']] = pd.DataFrame(
        [(coords if coords else (None, None)) for coords in coords_series],
        index=df_micro.index
    )

    # Save the geocoded microdata
    micro_output_csv = "microdata.csv"
    df_micro.to_csv(micro_output_csv, index=False)
    logger.info(f"Microdata with geocoded lat/lon saved as '{micro_output_csv}'.")
    st.write(f"Microdata with geocoded lat/lon saved as '{micro_output_csv}'.")

if __name__ == "__main__":
    main()