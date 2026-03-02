import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from fredapi import Fred
import yfinance as yf
from datetime import datetime, timedelta

# ============================================================================
# 1. ARCHITETTURA VISIVA (THEME GRAPHITE + NEON)
# ============================================================================
st.set_page_config(page_title="MACRO CORE ENGINE PRO", layout="wide", initial_sidebar_state="expanded")

# CSS Avanzato (Ripristinato da Claude con miglioramenti)
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;700;800&display=swap');
  :root {
    --bg: #070b12; --surface: #0e1420; --border: #1c2a3a;
    --cyan: #00f5c4; --red: #ff4d6d; --amber: #f5a623; --blue: #4da6ff;
    --text: #c8d8e8; --muted: #7a9ab0;
  }
  .stApp { background-color: var(--bg); color: var(--text); font-family: 'Space Mono', monospace; }
  .metric-card {
    background: var(--surface); border: 1px solid var(--border);
    padding: 20px; border-radius: 12px; transition: 0.3s;
  }
  .metric-card:hover { border-color: var(--cyan); box-shadow: 0 0 15px rgba(0,245,196,0.1); }
  .pillar-header {
    font-family: 'Syne', sans-serif; font-weight: 800; font-size: 1.2rem;
    color: var(--cyan); border-bottom: 1px solid var(--border); padding-bottom: 8px; margin-bottom: 15px;
  }
  .z-badge {
    padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: bold;
    background: rgba(255,255,255,0.05); border: 1px solid var(--border);
  }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# 2. MOTORE DATI (Integrazione M2 Velocity + MOVE Index)
# ============================================================================
FRED_API_KEY = '938a76ed726e8351f43e1b0c36365784'

@st.cache_data(ttl=3600)
def load_comprehensive_macro():
    fred = Fred(api_key=FRED_API_KEY)
    lookback = (datetime.now() - timedelta(days=365*10))
    
    # Mappa indicatori (ID_FRED: (Nome, Inverti, Descrizione))
    indicators = {
        'M2SL': ('M2 Real Growth', False, 'Liquidità reale YoY'),
        'MULT': ('M2 Velocity', False, 'Velocità di circolazione moneta'),
        'DFII10': ('Real Yield 10Y', True, 'Tassi reali (Invertiti)'),
        'BAMLH0A0HYM2': ('HY Spread', True, 'Rischio Credito'),
        'INDPRO': ('Ind. Production', False, 'Output Industriale'),
        'UNRATE': ('Unemployment', True, 'Mercato del Lavoro'),
        'TCU': ('Capacity Util.', False, 'Saturazione produttiva')
    }
    
    db = {}
    for code, (name, inv, desc) in indicators.items():
        s = fred.get_series(code, observation_start=lookback).dropna()
        if code in ['M2SL', 'INDPRO']: s = s.pct_change(12) * 100
        
        # Statistiche a 3 anni
        window = s.tail(252*3)
        z = (s.iloc[-1] - window.mean()) / window.std()
        score = max(0, min(100, ((-z if inv else z) + 3) / 6 * 100))
        db[name] = {'val': s.iloc[-1], 'z': z, 'score': score, 'hist': s, 'desc': desc}
        
    # Stress System (MOVE + VIX)
    mkt = yf.download(["^MOVE", "^VIX", "CL=F"], period="5y", progress=False)['Close']
    stress = {'^MOVE': 'Bond Vol (MOVE)', '^VIX': 'Equity Vol (VIX)', 'CL=F': 'Oil WTI'}
    for t, n in stress.items():
        s = mkt[t].dropna()
        z = (s.iloc[-1] - s.mean()) / s.std()
        db[n] = {'val': s.iloc[-1], 'z': z, 'score': max(0, min(100, ((-z) + 3) / 6 * 100)), 'hist': s, 'desc': 'Stress di mercato'}
        
    return db

# ============================================================================
# 3. INTERFACCIA PROFESSIONALE
# ============================================================================
try:
    data = load_comprehensive_macro()
    
    # Sidebar di Claude (Ripristinata)
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/3658/3658104.png", width=60)
        st.markdown("### CONFIGURAZIONE")
        pmi_val = st.slider("ISM Manufacturing PMI", 40.0, 60.0, 51.5)
        st.markdown("---")
        st.info("Logica: Z-Score a 3 anni. Baseline: Media mobile storica.")

    # Radar Chart (Il pezzo forte di Claude)
    st.title("🧭 MACRO CORE ENGINE v3.0")
    
    # Riassunto Pilastri
    p_mon = np.mean([data['M2 Real Growth']['score'], data['Real Yield 10Y']['score'], data['HY Spread']['score']])
    p_eco = np.mean([data['Ind. Production']['score'], data['Unemployment']['score'], (pmi_val-40)/20*100])
    p_str = np.mean([data['Bond Vol (MOVE)']['score'], data['Equity Vol (VIX)']['score']])
    
    c1, c2 = st.columns([1, 1])
    with c1:
        # Radar Chart
        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(
            r=[p_mon, p_eco, p_str, data['M2 Velocity']['score'], data['Capacity Util.']['score']],
            theta=['Monetario', 'Economia', 'Stress', 'Velocità M2', 'Produttività'],
            fill='toself', line_color=var_color := ("#00f5c4" if p_eco > 50 else "#ff4d6d")
        ))
        fig_radar.update_layout(polar=dict(bgcolor=SURF_COL, radialaxis=dict(visible=True, range=[0, 100])), 
                                paper_bgcolor="rgba(0,0,0,0)", showlegend=False, height=350)
        st.plotly_chart(fig_radar, use_container_width=True)

    with c2:
        # Identificazione Regime Didascalica (Logica Claude)
        st.markdown("<div style='height:40px;'></div>", unsafe_allow_html=True)
        regime = "GOLDILOCKS" if p_eco > 55 and p_mon > 50 else "STAGFLATION" if p_eco < 45 and p_mon < 40 else "REFLATION"
        st.subheader(f"REGIME ATTUALE: {regime}")
        st.markdown(f"""
        <div class='metric-card'>
            <b>Asset Allocation Implied:</b><br>
            • Equity: {"Overweight" if regime == "GOLDILOCKS" else "Underweight"}<br>
            • Bonds: {"Neutral" if p_mon > 50 else "Avoid (Stress MOVE)"}<br>
            • Cash: {"Minimal" if regime == "GOLDILOCKS" else "High Priority"}
        </div>
        """, unsafe_allow_html=True)

    # Tabs strutturate
    t1, t2, t3 = st.tabs(["📊 DETTAGLIO PILASTRI", "📈 ANALISI STORICA", "📖 METODOLOGIA"])
    
    with t1:
        cols = st.columns(3)
        for i, (name, info) in enumerate(data.items()):
            with cols[i % 3]:
                st.markdown(f"""
                <div class='metric-card'>
                    <div class='stat-label'>{name}</div>
                    <div class='stat-value'>{info['val']:.2f}</div>
                    <div style='display:flex; justify-content:space-between; margin-top:10px;'>
                        <span class='z-badge'>Z-Score: {info['z']:.2f}</span>
                        <span style='color:{"#00f5c4" if info['score']>50 else "#ff4d6d"}'>Score: {info['score']:.0f}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    with t2:
        sel = st.selectbox("Seleziona Metrica per Trend:", list(data.keys()))
        fig_h = go.Figure()
        fig_h.add_trace(go.Scatter(x=data[sel]['hist'].index, y=data[sel]['hist'].values, line_color=CYAN))
        fig_h.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_h, use_container_width=True)

except Exception as e:
    st.error(f"Errore: {e}")
