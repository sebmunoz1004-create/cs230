"""
Name: Sebastian Munoz
Course: CS230
Project: Farmers Markets Directory
URL:

This app uses a Farmers Markets Directory CSV file. The user can choose a state,
search by city, and see markets in a table, charts, and a map.
"""

import streamlit as st
import pandas as pd
import pydeck as pdk


def load_data():
    try:
        return pd.read_csv("farmersmarket_2026.csv", encoding="latin1")
    except FileNotFoundError:
        st.error("The CSV file was not found. Make sure farmersmarket_2026.csv is in the same folder as this app.")
        return pd.DataFrame()


def clean_state(state_value):
    state_names = {
        "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
        "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
        "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
        "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
        "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
        "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
        "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
        "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico",
        "NY": "New York", "NC": "North Carolina", "ND": "North Dakota",
        "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
        "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota",
        "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont",
        "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
        "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia"
    }

    if pd.isna(state_value):
        return None

    state_value = str(state_value).strip()

    if state_value.upper() in state_names:
        return state_names[state_value.upper()]

    state_value = state_value.title()

    if state_value in state_names.values():
        return state_value

    return None


def state_with_most_markets(data):
    state_counts = data["State"].value_counts()
    return state_counts.idxmax(), state_counts.max()


st.set_page_config(page_title="Farmers Market Finder", layout="wide")

st.title("Farmers Market Finder")
st.write("This app helps look through farmers markets by state and city.")

# loading data (PY1)
df = load_data()

if df.empty:
    st.stop()

# cleaning the main columns I need (DA1)
df["State"] = df["Parsed_State"].apply(clean_state)
df["City"] = df["Parsed_City"].astype(str).str.strip().str.title()
df["Market Name"] = df["listing_name"].astype(str).str.strip()
df["Street"] = df["Parsed_Address"].astype(str).str.strip()
df["Zip"] = df["Parsed_Zip"].astype(str).str.strip()

df["lat"] = pd.to_numeric(df["location_y"], errors="coerce")
df["lon"] = pd.to_numeric(df["location_x"], errors="coerce")

# only keeping rows that can actually be used on the site
# this also prevents blank states and broken map points
# (DA2)
df = df.dropna(subset=["State", "City", "lat", "lon"])

# extra columns to make the app easier to read (DA7)
df["City, State"] = df["City"] + ", " + df["State"]
df["Takes SNAP"] = df["FNAP"].fillna("").str.contains("SNAP", case=False)
df["Takes Card"] = df["acceptedpayment"].fillna("").str.contains("Credit|Debit", case=False)

# dictionary for the radio button options (PY5)
market_options = {
    "all": "All markets",
    "snap": "Markets that mention SNAP",
    "card": "Markets that mention credit/debit cards"
}

st.sidebar.header("Filters")

# user input widgets (ST1, ST2, ST3)
states = sorted(df["State"].unique())
state_choice = st.sidebar.selectbox("Choose a state", states)
city_search = st.sidebar.text_input("Search for a city")
market_choice = st.sidebar.radio(
    "Market type",
    list(market_options.keys()),
    format_func=lambda x: market_options[x]
)

# filter by state (DA4)
filtered = df[df["State"] == state_choice]

# filter by city too, if the user types one (DA5)
if city_search.strip() != "":
    filtered = filtered[filtered["City"].str.contains(city_search, case=False, na=False)]

if market_choice == "snap":
    filtered = filtered[filtered["Takes SNAP"] == True]
elif market_choice == "card":
    filtered = filtered[filtered["Takes Card"] == True]

st.subheader("Quick Summary")

most_state, most_count = state_with_most_markets(df)

col1, col2, col3 = st.columns(3)
col1.metric("Markets showing", len(filtered))
col2.metric("Cities showing", filtered["City"].nunique())
col3.metric("Most markets overall", f"{most_state} ({most_count})")

st.write("Selected state:", state_choice)

st.subheader("Farmers Markets Table")

if len(filtered) == 0:
    st.warning("No markets match these filters. Try another city or market type.")
    st.stop()

# sorting the table by city and market name (DA3)
filtered = filtered.sort_values(["City", "Market Name"])

table = filtered[[
    "Market Name",
    "Street",
    "City",
    "State",
    "Zip",
    "Takes SNAP",
    "Takes Card"
]]

st.dataframe(table, use_container_width=True)

st.subheader("Top Cities in the Current Results")
top_cities = filtered["City"].value_counts().head(10)
st.bar_chart(top_cities)

# pivot table for market count by state (DA6)
state_table = pd.pivot_table(
    df,
    index="State",
    values="listing_id",
    aggfunc="count"
)

state_table = state_table.rename(columns={"listing_id": "Number of Markets"})
state_table = state_table.sort_values("Number of Markets", ascending=False)

st.subheader("States With the Most Farmers Markets")
st.bar_chart(state_table.head(20))

st.subheader("Payment Options in Current Results")
payment_table = pd.DataFrame({
    "Payment Type": ["SNAP mentioned", "Card mentioned"],
    "Count": [filtered["Takes SNAP"].sum(), filtered["Takes Card"].sum()]
})
st.bar_chart(payment_table.set_index("Payment Type"))

st.subheader("Map of Markets")

map_layer = pdk.Layer(
    "ScatterplotLayer",
    data=filtered,
    get_position="[lon, lat]",
    get_radius=800,
    get_fill_color=[40, 140, 80, 160],
    pickable=True
)

map_view = pdk.ViewState(
    latitude=filtered["lat"].mean(),
    longitude=filtered["lon"].mean(),
    zoom=6
)

map_tip = {
    "html": "<b>{Market Name}</b><br>{Street}<br>{City}, {State}",
    "style": {"backgroundColor": "white", "color": "black"}
}

st.pydeck_chart(pdk.Deck(layers=[map_layer], initial_view_state=map_view, tooltip=map_tip))

st.subheader("A Few Market Names")

# for loop to show a few market examples (DA8)
market_examples = []
for index, row in filtered.head(5).iterrows():
    market_examples.append(row["Market Name"])

# list comprehension to clean up capitalization a little (PY4)
market_examples = [name.title() for name in market_examples]

for market in market_examples:
    st.write("-", market)
