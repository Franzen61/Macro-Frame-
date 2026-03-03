import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from pandas_datareader
from pandas_datareader.fred import FredReader
from datetime import datetime
import os

# ==========================================================
# CONFIG
# ==========================================================

st.set_page_config(layout="wide", page_title="Macro Core Engine 2.0")

st.markdown(
    """
    <style>
    body {background-color: #0E1117; color: white;}
    .stMetric {background-color: #1c1f26; padding: 10px; border-radius: 10px;}
    </style>
    """,
    unsafe_allow_html=True
)

# ==========================================================
# FRED API HANDLING
# ==========================================================

def get_fred_key():
    try:
        return st.secrets["FRED_API_KEY"]
    except Exception:
        st.error("FRED API Key missing. Add it to secrets.toml")
        st.stop()

FRED_KEY = get_fred_key()

# ==========================================================
# SAFE DATA LOADING
# ==========================================================

@st.cache_data(ttl=3600)
def load_fred(series):
    try:
        reader = FredReader(
            symbols=series,
            start=datetime(1990, 1, 1),
            api_key=FRED_KEY
        )
        data = reader.read()
        return data
    except Exception as e:
        st.warning(f"Error loading {series}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_yahoo(ticker):
    try:
        data = yf.download(ticker, start="1990-01-01", progress=False)
        return data["Adj Close"]
    except:
        st.warning(f"Error loading {ticker}")
        return pd.Series()

# ==========================================================
# Z-SCORE ENGINE
# ==========================================================

def rolling_z(series, window):
    return (series - series.rolling(window).mean()) / series.rolling(window).std()

def expanding_z(series):
    return (series - series.expanding().mean()) / series.expanding().std()

def percentile_z(series, window):
    return series.rolling(window).apply(
        lambda x: pd.Series(x).rank(pct=True).iloc[-1]
    )

def compute_z(series, mode, window):
    if mode == "Rolling":
        return rolling_z(series, window)
    elif mode == "Expanding":
        return expanding_z(series)
    else:
        return percentile_z(series, window)

# ==========================================================
# SIDEBAR
# ==========================================================

st.sidebar.title("MACRO CORE ENGINE 2.0")

z_mode = st.sidebar.selectbox(
    "Z-Score Mode",
    ["Rolling", "Expanding", "Percentile"]
)

window = st.sidebar.slider("Z Window (months)", 24, 120, 36)

st.sidebar.markdown("---")

# ==========================================================
# DATA DOWNLOAD
# ==========================================================

with st.spinner("Downloading macro data..."):

    # Growth
    ism_mfg = load_fred("NAPM")
    ism_srv = load_fred("ISMNONMAN")

    # Monetary
    real_10y = load_fred("DFII10")
    hy_spread = load_fred("BAMLH0A0HYM2")
    m2 = load_fred("M2SL")
    cpi = load_fred("CPIAUCSL")
    gdp = load_fred("GDP")

    # Fiscal
    deficit = load_fred("FYFSD")

    # Risk
    stlfsi = load_fred("STLFSI4")
    move = load_yahoo("^MOVE")

# ==========================================================
# DATA PREP
# ==========================================================

df = pd.concat([
    ism_mfg,
    ism_srv,
    real_10y,
    hy_spread,
    m2,
    cpi,
    gdp,
    deficit,
    stlfsi
], axis=1)

df.columns = [
    "ISM_MFG",
    "ISM_SRV",
    "Real10Y",
    "HY",
    "M2",
    "CPI",
    "GDP",
    "Deficit",
    "Stress"
]

df = df.resample("M").last()

# MOVE
move = move.resample("M").last()
df["MOVE"] = move

df = df.dropna(how="all")

# ==========================================================
# DERIVED METRICS
# ==========================================================

df["PMI"] = (df["ISM_MFG"] + df["ISM_SRV"]) / 2
df["RealM2"] = df["M2"] / df["CPI"]
df["Velocity"] = df["GDP"] / df["RealM2"]
df["FiscalImpulse"] = df["Deficit"].diff(12)

# ==========================================================
# Z-SCORES
# ==========================================================

df["Growth_Z"] = compute_z(df["PMI"], z_mode, window)
df["Real10Y_Z"] = compute_z(df["Real10Y"], z_mode, window)
df["HY_Z"] = compute_z(df["HY"], z_mode, window)
df["Velocity_Z"] = compute_z(df["Velocity"], z_mode, window)
df["Fiscal_Z"] = compute_z(df["FiscalImpulse"], z_mode, window)
df["MOVE_Z"] = compute_z(df["MOVE"], z_mode, window)
df["Stress_Z"] = compute_z(df["Stress"], z_mode, window)

# ==========================================================
# SCORES
# ==========================================================

df["MonetaryScore"] = -df["Real10Y_Z"] - df["HY_Z"]
df["RiskScore"] = -df["MOVE_Z"] - df["Stress_Z"]

df["Composite"] = (
    df["Growth_Z"] +
    df["MonetaryScore"] +
    df["Velocity_Z"] +
    df["Fiscal_Z"] +
    df["RiskScore"]
) / 5

# ==========================================================
# REGIME
# ==========================================================

def regime(x):
    if x > 1:
        return "Inflationary Boom"
    elif x > 0:
        return "Expansion"
    elif x > -1:
        return "Slowdown"
    else:
        return "Recession / Crisis"

df["Regime"] = df["Composite"].apply(regime)

# ==========================================================
# UI
# ==========================================================

st.title("Macro Core Engine 2.0")

col1, col2, col3 = st.columns(3)
col1.metric("Composite", round(df["Composite"].iloc[-1], 2))
col2.metric("Regime", df["Regime"].iloc[-1])
col3.metric("PMI", round(df["PMI"].iloc[-1], 1))

# ==========================================================
# PLOT FUNCTION
# ==========================================================

def plot_series(series, title):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=series.index, y=series, mode="lines"))
    fig.update_layout(
        title=title,
        template="plotly_dark",
        height=350
    )
    st.plotly_chart(fig, use_container_width=True)

# ==========================================================
# PANELS
# ==========================================================

st.subheader("Composite")
plot_series(df["Composite"], "Macro Composite")

st.subheader("Growth")
plot_series(df["Growth_Z"], "PMI Z")

st.subheader("Monetary")

col1, col2 = st.columns(2)
with col1:
    plot_series(df["Real10Y_Z"], "Real 10Y Z")

with col2:
    plot_series(df["HY_Z"], "HY Spread Z")

st.subheader("Liquidity")
plot_series(df["Velocity_Z"], "Velocity Z")

st.subheader("Risk & Stress")

col1, col2 = st.columns(2)
with col1:
    plot_series(df["MOVE_Z"], "MOVE Z")

with col2:
    plot_series(df["Stress_Z"], "Financial Stress Z")

st.subheader("Fiscal")
plot_series(df["Fiscal_Z"], "Fiscal Impulse Z")
