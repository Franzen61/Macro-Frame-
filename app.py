import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from fredapi import Fred
import yfinance as yf
from datetime import datetime, timedelta

# =============================================================================
# 1. SETUP & STYLING (Stile Claude "Graphite & Neon")
# =============================================================================
st.set_page_config(page_title="MACRO CORE TERMINAL", layout="wide", initial_sidebar_state="collapsed")

# Palette colori istituzionale
CYAN, RED, AMBER, BLUE = "#00f5c4", "#ff4d6d", "#f5a623", "#4da6ff"
BG_COL, SURF_COL, BORDER_COL = "#070b12", "#0e1420", "#1c2a3a"

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Mono&family=Syne:wght@700;800&display=swap');
    .stApp {{ background-color: {BG_COL}; color: #c8d8e8; font-family: 'Space Mono', monospace; }}
    .macro-card {{ background: {SURF_COL}; border: 1px solid {BORDER_COL}; border-radius: 8px; padding: 20px; margin-bottom: 15px; }}
    .stat-label {{ font-size: 0.7rem; color: #7a9ab0; letter-spacing: 2px; text-transform: uppercase; }}
    .stat-value {{ font-family: 'Syne', sans-serif; font-size: 1.8rem; font-weight: 800; color: {CYAN}; }}
    .z-score {{ font-size: 0.85rem; font-weight: bold; }}
    h1, h2, h3 {{ font-family: 'Syne', sans-serif; color: white; }}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# 2. CORE ENGINE (Logica Statistica & Data Fetching)
# =============================================================================
FRED_API_KEY = '938a76ed726e8351f43e1b0c36365784'

@st.cache_data(ttl=3600)
def get_macro_data():
    fred = Fred(api_key=FRED_API_KEY)
    start_date = (datetime.now() - timedelta(days=365*5))
    
    # Configurazioni: (Inverti_Zscore, Descrizione)
    config = {
        "M2SL": (False, "M2 Real Growth (YoY)"),
        "MULT": (False, "M2 Velocity (GDP/M2)"),
        "DFII10": (True, "Real Yield 10Y (Cost of Capital)"),
        "BAMLH0A0HYM2": (True, "HY Credit Spreads"),
        "INDPRO": (False, "Industrial Production YoY"),
        "UNRATE": (True, "Unemployment Rate (Inverted)")
    }
    
    db = {}
    for code, (invert, label) in config.items():
        s = fred.get_series(code, observation_start=start_date).dropna()
        if code in ["M2SL", "INDPRO"]: s = s.pct_change(12) * 100
        
        # Calcolo Z-Score (rolling 3 anni approx)
        mean, std = s.mean(), s.std()
        current_val = s.iloc[-1]
        z = (current_val - mean) / std
        score = max(0, min(100, ((-z if invert else z) + 3) / 6 * 100))
        
        db[label] = {"val": current_val, "z": z, "score": score, "history": s}
    
    # Stress Market Data (Yahoo Finance)
    mkt = yf.download(["^MOVE", "^VIX", "CL=F"], period="5y", progress=False)['Close']
    stress_map = {"^MOVE": "Bond Vol (MOVE)", "^VIX": "Equity Vol (VIX)", "CL=F": "Oil Shock (WTI)"}
    for ticker, name in stress_map.items():
        s = mkt[ticker].dropna()
        z = (s.iloc[-1] - s.mean()) / s.std()
        db[name] = {"val": s.iloc[-1], "z": z, "score": max(0, min(100, ((-z) + 3) / 6 * 100)), "history": s}
        
    return db

# =============================================================================
# 3. DASHBOARD RENDERING
# =============================================================================
try:
    data = get_macro_data()
    
    # HEADER & REGIME CALCULATION
    growth_idx = (data["Industrial Production YoY"]["score"] + data["M2 Velocity (GDP/M2)"]["score"]) / 2
    liquidity_idx = data["M2 Real Growth (YoY)"]["score"]
    
    st.markdown(f"<h1>🧭 MACRO CORE TERMINAL <span style='color:{CYAN};font-size:1rem;'>v2.5 PRO</span></h1>", unsafe_allow_html=True)
    
    col_reg1, col_reg2 = st.columns([1, 2])
    
    with col_reg1:
        # Logica Quadrante
        if growth_idx > 50 and liquidity_idx > 50: reg, col, desc = "GOLDILOCKS", CYAN, "Espansione non inflattiva. Bullish Risk Assets."
        elif growth_idx > 50 and liquidity_idx <= 50: reg, col, desc = "OVERHEATING", AMBER, "Crescita alta ma liquidità in calo. Prudenza."
        elif growth_idx <= 50 and liquidity_idx > 50: reg, col, desc = "REFLATION", BLUE, "Supporto monetario in rallentamento economico."
        else: reg, col, desc = "STAGFLATION/BUST", RED, "Contrazione e stress. Defensive mode ON."
        
        st.markdown(f"""
            <div style="border: 2px solid {col}; padding: 20px; border-radius: 10px; background: {SURF_COL};">
                <div class="stat-label">Current Regime</div>
                <div style="color:{col}; font-family:'Syne'; font-size:2rem; font-weight:800;">{reg}</div>
                <p style="font-size:0.8rem; margin-top:10px; color:#abbbc9;">{desc}</p>
            </div>
        """, unsafe_allow_html=True)

    with col_reg2:
        # Radar-style Summary Bar
        fig_summary = go.Figure(go.Bar(
            x=[k for k in data.keys()],
            y=[v['score'] for v in data.values()],
            marker_color=[CYAN if v['score']>60 else RED if v['score']<40 else AMBER for v in data.values()]
        ))
        fig_summary.update_layout(height=180, margin=dict(t=20, b=20, l=0, r=0), paper_bgcolor="rgba(0,0,0,0)", 
                                  plot_bgcolor="rgba(0,0,0,0)", font=dict(color="white", size=9),
                                  yaxis=dict(range=[0, 100], showgrid=False, zeroline=False))
        st.plotly_chart(fig_summary, use_container_width=True, config={'displayModeBar': False})

    # INDICATOR GRID
    st.markdown("### 📊 Pillars Deep-Dive")
    cols = st.columns(3)
    for i, (name, info) in enumerate(data.items()):
        target_col = cols[i % 3]
        with target_col:
            z_color = CYAN if abs(info['z']) < 1.5 else AMBER if abs(info['z']) < 2.5 else RED
            st.markdown(f"""
                <div class="macro-card">
                    <div class="stat-label">{name}</div>
                    <div class="stat-value">{info['val']:.2f}</div>
                    <div class="z-score" style="color:{z_color}">Z-Score: {info['z']:.2f}</div>
                </div>
            """, unsafe_allow_html=True)
            
    # HISTORICAL ANALYSIS SECTION
    st.markdown("### 📈 Historical Context & Thresholds")
    selected = st.selectbox("Analizza serie storica:", list(data.keys()))
    h_data = data[selected]['history']
    
    fig_hist = go.Figure()
    fig_hist.add_trace(go.Scatter(x=h_data.index, y=h_data.values, line=dict(color=CYAN, width=2)))
    
    # Aggiunta soglie statistiche
    mean = h_data.mean()
    std = h_data.std()
    for n in [-2, 0, 2]:
        fig_hist.add_hline(y=mean + n*std, line_dash="dot", line_color="#3a4a5a", 
                           annotation_text=f"{n} STD" if n != 0 else "MEAN")
    
    fig_hist.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=400)
    st.plotly_chart(fig_hist, use_container_width=True)

except Exception as e:
    st.error(f"Errore nel caricamento dati: {e}")
    st.info("Verifica la tua chiave API FRED o la connessione internet.")
