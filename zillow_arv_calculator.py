import streamlit as st
import requests
from bs4 import BeautifulSoup
from geopy.geocoders import Nominatim
import pandas as pd
from urllib.parse import quote
import time
import re
from typing import Dict, Any

# Zillow Scraping Configuration
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]
geolocator = Nominatim(user_agent="arv_calculator")

@st.cache_data(ttl=3600)
def geocode_address(address: str) -> tuple:
    """Geocode address to lat/lon using free Nominatim."""
    try:
        location = geolocator.geocode(address)
        if location:
            return location.latitude, location.longitude
        st.error("Could not geocode address.")
        return None, None
    except:
        return None, None

def fetch_zillow_page(url: str) -> str:
    """Fetch Zillow page with random user agent and delay."""
    headers = {"User-Agent": USER_AGENTS[hash(url) % len(USER_AGENTS)]}
    proxies = {}  # Add {'http': 'http://proxy:port'} if needed
    time.sleep(2)  # Rate limiting
    response = requests.get(url, headers=headers, proxies=proxies)
    if response.status_code == 200:
        return response.text
    st.error(f"Failed to fetch {url} (status: {response.status_code}). Try again or check connection.")
    return ""

@st.cache_data(ttl=3600)
def get_property_details(address: str) -> Dict[str, Any]:
    """Scrape target property details from Zillow."""
    encoded_address = quote(address)
    url = f"https://www.zillow.com/homedetails/{encoded_address.replace(' ', '-')}"
    html = fetch_zillow_page(url)
    if not html:
        return {}
    
    soup = BeautifulSoup(html, 'lxml')
    
    # Extract details using resilient selectors
    beds = int(re.search(r'(\d+(?:\.\d+)?)\s*bd', html).group(1)) if re.search(r'(\d+(?:\.\d+)?)\s*bd', html) else 0
    baths = int(re.search(r'(\d+(?:\.\d+)?)\s*ba', html).group(1)) if re.search(r'(\d+(?:\.\d+)?)\s*ba', html) else 0
    sq_ft = int(re.search(r'(\d+(?:,\d{3})*)\s*sqft', html).group(1).replace(',', '')) if re.search(r'(\d+(?:,\d{3})*)\s*sqft', html) else 0
    lot_size = int(re.search(r'lot:\s*(\d+(?:,\d{3})*)', html).group(1).replace(',', '')) if re.search(r'lot:\s*(\d+(?:,\d{3})*)', html) else 0
    year_built = int(re.search(r'built\s*(\d{4})', html).group(1)) if re.search(r'built\s*(\d{4})', html) else 0
    
    lat_match = re.search(r'"latitude":\s*([\d.-]+)', html)
    lon_match = re.search(r'"longitude":\s*([\d.-]+)', html)
    lat = float(lat_match.group(1)) if lat_match else None
    lon = float(lon_match.group(1)) if lon_match else None
    
    if not all([beds, baths, sq_ft]):
        st.warning("Partial details fetched; some fields may be missing.")
    
    return {
        "address": address,
        "beds": beds,
        "baths": baths,
        "sq_ft": sq_ft,
        "lot_size": lot_size,
        "year_built": year_built,
        "latitude": lat,
        "longitude": lon
    }

@st.cache_data(ttl=3600)
def get_comps(lat: float, lon: float, beds: int, baths: int, sq_ft: int, lot_size: int, year_built: int) -> pd.DataFrame:
    """Scrape recently sold comps from Zillow search."""
    # Build search URL for recently sold in radius (Zillow uses ~0.5-1 mile via map bounds approx)
    search_url = f"https://www.zillow.com/homes/{lat},{lon}_rb/?searchQueryState={{%22pagination%22%3A{{}}%2C%22isMapVisible%22%3Atrue%2C%22filterState%22%3A{{%22sort%22%3A{{%22value%22%3A%22globalrelevanceex%22}}%2C%22ah%22%3A{{%22value%22%3Atrue}}%2C%22sold%22%3A{{%22value%22%3Atrue}}%2C%22rs%22%3A{{%22value%22%3Atrue}}%2C%22mf%22%3A{{%22value%22%3Afalse}}%2C%22fsba%22%3A{{%22value%22%3Afalse}}%2C%22fsbo%22%3A{{%22value%22%3Afalse}}%2C%22nc%22%3A{{%22value%22%3Afalse}}%2C%22cmsn%22%3A{{%22value%22%3Afalse}}%2C%22auc%22%3A{{%22value%22%3Afalse}}%2C%22fore%22%3A{{%22value%22%3Afalse}}%2C%22pmf%22%3A{{%22value%22%3Afalse}}%2C%22pf%22%3A{{%22value%22%3Afalse}}%2C%22mp%22%3A{{%22value%22%3Afalse}}%2C%22con%22%3A{{%22value%22%3Afalse}}%2C%22land%22%3A{{%22value%22%3Afalse}}%2C%22tow%22%3A{{%22value%22%3Afalse}}%2C%22apa%22%3A{{%22value%22%3Afalse}}%2C%22apco%22%3A{{%22value%22%3Afalse}}%2C%22manu%22%3A{{%22value%22%3Afalse}}%2C%22house%22%3A{{%22value%22%3Atrue}}%2C%22town%22%3A{{%22value%22%3Atrue}}%2C%22cond%22%3A{{%22value%22%3Atrue}}%2C%22aprt%22%3A{{%22value%22%3Atrue}}%2C%22mlt%22%3A{{%22value%22%3Afalse}}%2C%22man%22%3A{{%22value%22%3Afalse}}%2C%22lot%22%3A{{%22value%22%3Afalse}}%2C%22room%22%3A{{%22value%22%3Afalse}}%2C%22sf%22%3A{{%22value%22%3Afalse}}%2C%22ha%22%3A{{%22value%22%3Afalse}}%2C%22bd%22%3A{{%22value%22%3A%22{0}%22}}%2C%22ba%22%3A{{%22value%22%3A%22{1}%22}}%2C%22sqft%22%3A{{%22value%22%3A%22{2}%22}}%2C%22lot%22%3A{{%22value%22%3A%22{3}%22}}%2C%22yb%22%3A{{%22value%22%3A%22{4}%22}}%2C%22fr%22%3A{{%22value%22%3Atrue}}%2C%22fs%22%3A{{%22value%22%3A30}}%2C%22fsbo%22%3A{{%22value%22%3Afalse}}%2C%22cmsn%22%3A{{%22value%22%3Afalse}}%2C%22auc%22%3A{{%22value%22%3Afalse}}%2C%22fore%22%3A{{%22value%22%3Afalse}}%2C%22pmf%22%3A{{%22value%22%3Afalse}}%2C%22pf%22%3A{{%22value%22%3Afalse}}%2C%22mp%22%3A{{%22value%22%3Afalse}}%2C%22fr%22%3A{{%22value%22%3Atrue}}%2C%22rh%22%3A{{%22value%22%3Atrue}}}}%2C%22isListVisible%22%3Atrue%2C%22mapBounds%22%3A{{%22west%22%3A{5}%2C%22east%22%3A{6}%2C%22south%22%3A{7}%2C%22north%22%3A{8}}}}%2C%22usersSearchTerm%22%3A%22{9}%22}}".format(
        beds, baths, f"{sq_ft*0.8}-{sq_ft*1.2}", f"{lot_size*0.8}-{lot_size*1.2}", year_built-10, year_built+10,
        lon-0.01, lon+0.01, lat-0.01, lat+0.01, address  # Approx 0.5-mile radius
    )
    html = fetch_zillow_page(search_url)
    if not html:
        return pd.DataFrame()
    
    soup = BeautifulSoup(html, 'lxml')
    comps = []
    
    # Parse search results (up to 20 comps)
    for card in soup.find_all('article', {'id': re.compile(r'zpid_\d+')}):  # Listing cards
        addr = card.find('address')
        address_comp = addr.text.strip() if addr else ""
        
        beds_comp = int(card.find('span', {'data-test': 'property-beds'}).text.split()[0]) if card.find('span', {'data-test': 'property-beds'}) else 0
        baths_comp = float(card.find('span', {'data-test': 'property-baths'}).text.split()[0]) if card.find('span', {'data-test': 'property-baths'}) else 0
        sq_ft_comp = int(re.search(r'(\d+) sqft', card.text).group(1).replace(',', '')) if re.search(r'(\d+) sqft', card.text) else 0
        sold_price = int(re.search(r'Sold:\s*\$([\d,]+)', card.text).group(1).replace(',', '')) if re.search(r'Sold:\s*\$([\d,]+)', card.text) else 0
        sold_date = card.find('span', {'data-test': 'listing-card-sold-date'}).text if card.find('span', {'data-test': 'listing-card-sold-date'}) else ""
        
        # Filter for similarity and recent (last 6 months)
        if (abs(beds_comp - beds) <= 1 and abs(baths_comp - baths) <= 1 and
            0.8 * sq_ft <= sq_ft_comp <= 1.2 * sq_ft and sold_date and "2025" in sold_date):  # Approx recent
            comps.append({
                "Address": address_comp,
                "Beds": beds_comp,
                "Baths": baths_comp,
                "Sq Ft": sq_ft_comp,
                "Sold Date": sold_date,
                "Sold Price": sold_price
            })
    
    return pd.DataFrame(comps)

def calculate_arv(comps_df: pd.DataFrame) -> float:
    """Median sold price as ARV."""
    if not comps_df.empty and "Sold Price" in comps_df.columns:
        return comps_df["Sold Price"].median()
    return 0

# Streamlit UI
st.title("🏠 Zillow ARV Calculator for Wholesaling")
st.markdown("Enter a property address to estimate ARV from similar recently sold comps (scraped from Zillow).")

address = st.text_input("Property Address (e.g., 123 Main St, Anytown, CA 12345):", key="address")

if st.button("Calculate ARV") and address:
    with st.spinner("Geocoding and fetching property details..."):
        lat, lon = geocode_address(address)
        if not lat or not lon:
            st.error("Geocoding failed. Check address.")
            st.stop()
        
        prop_details = get_property_details(address)
    
    if prop_details:
        st.subheader("Target Property Details")
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Address:** {prop_details['address']}")
            st.write(f"**Beds:** {prop_details['beds']}")
            st.write(f"**Baths:** {prop_details['baths']}")
        with col2:
            st.write(f"**Sq Ft:** {prop_details['sq_ft']:,}")
            st.write(f"**Lot Size:** {prop_details['lot_size']:,} sq ft")
            st.write(f"**Year Built:** {prop_details['year_built']}")

        with st.spinner("Fetching comparable sold properties..."):
            comps_df = get_comps(
                prop_details["latitude"], prop_details["longitude"],
                prop_details["beds"], prop_details["baths"],
                prop_details["sq_ft"], prop_details["lot_size"],
                prop_details["year_built"]
            )
        
        if not comps_df.empty:
            st.subheader("Comparable Recently Sold Properties")
            st.dataframe(comps_df, use_container_width=True)
            
            arv = calculate_arv(comps_df)
            st.metric("Estimated ARV (Median Sold Price)", f"${arv:,.0f}")
            
            st.info(f"Based on {len(comps_df)} comps. Recent sales approximate renovated flips. Adjust filters in code if needed.")
        else:
            st.warning("No matching comps found. Try a broader area or check for blocks.")
    else:
        st.stop()

st.markdown("---")
st.caption("Built with Streamlit & Zillow scraping. For blocks, add proxies. Legal note: For personal use only; respect Zillow TOS.")
