"""
MACRO CORE ENGINE v2.0
======================
Merge definitivo: Interfaccia Claude (Tabs, Radar) + Logica Copilot (M2 Real, Velocity, MOVE, Sparklines).
5 Pilastri: Monetario, Econ. Reale, Fiscale, Produttivo, Rischio & Stress
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from fredapi import Fred
import yfinance as yf
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings("ignore")

# ============================================================================
# PAGE CONFIG & CSS
# ============================================================================
st.set_page_config(page_title="MACRO CORE ENGINE", page_icon="🧭", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;700;800&display=swap');
  :root {
    --bg: #070b12; --surface: #0e1420; --border: #1c2a3a;
    --cyan: #00f5c4; --red: #ff4d6d; --amber: #f5a623; --blue: #4da6ff;
    --text: #c8d8e8; --muted: #7a9ab0;
  }
  html, body, [data-testid="stAppViewContainer"], .stApp {
    background-color: var(--bg) !important; color: var(--text) !important; font-family: 'Space Mono', monospace !important;
  }
  [data-testid="stSidebar"] { background-color: var(--surface) !important; border-right: 1px solid var(--border) !important; }
  header[data-testid="stHeader"] { background: var(--bg) !important; border-bottom: 1px solid var(--border) !important; }
  .block-container { padding-top: 3rem; padding-bottom: 2rem; }
  h1,h2,h3 { font-family: 'Syne', sans-serif !important; }
  .main-title { font-family: 'Syne', sans-serif; font-size: 2.2rem; font-weight: 800; color: var(--cyan); letter-spacing: -1px; }
  .section-label { font-family: 'Syne', sans-serif; font-size: 0.65rem; letter-spacing: 4px; text-transform: uppercase; color: var(--muted); border-bottom: 1px solid var(--border); padding-bottom: 4px; margin-bottom: 14px; margin-top: 24px; }
  .pill { display: inline-block; padding: 2px 10px; border-radius: 2px; font-size: 0.58rem; letter-spacing: 2px; text-transform: uppercase; font-weight: 700; }
  .pill-bull { background: rgba(0,245,196,0.12); color: #00f5c4; border: 1px solid #00f5c4; }
  .pill-bear { background: rgba(255,77,109,0.12); color: #ff4d6d; border: 1px solid #ff4d6d; }
  .pill-neut { background: rgba(245,166,35,0.12); color: #f5a623; border: 1px solid #f5a623; }
</style>
""", unsafe_allow_html=True)

# CONSTANTS
PLOT_BG, PAPER_BG, GRID_COL = "#070b12", "#0e1420", "#1c2a3a"
CYAN, RED, AMBER, BLUE, TEXT_COL, MUTED = "#00f5c4", "#ff4d6d", "#f5a623", "#4da6ff", "#c8d8e8", "#7a9ab0"
FRED_API_KEY = '938a76ed726e8351f43e1b0c36365784'

# ============================================================================
# UTILS & MATH
# ============================================================================
def base_layout(title="", height=320):
    return dict(height=height, title=dict(text=title, font=dict(family="Syne", size=12, color=TEXT_COL), x=0.01),
                paper_bgcolor=PAPER_BG, plot_bgcolor=PLOT_BG, font=dict(family="Space Mono", color=TEXT_COL, size=10),
                xaxis=dict(gridcolor=GRID_COL, showgrid=True), yaxis=dict(gridcolor=GRID_COL, showgrid=True),
                margin=dict(l=40, r=40, t=40, b=30), hovermode="x unified")

def zscore_series(series, window):
    m = series.rolling(window, min_periods=window//2).mean()
    s = series.rolling(window, min_periods=window//2).std()
    return ((series - m) / s).replace([np.inf, -np.inf], np.nan)

def zscore_to_score(z, invert=False):
    z_clipped = np.clip(z, -3, 3)
    if invert: z_clipped = -z_clipped
    return (z_clipped + 3) / 6 * 100

def score_color(score): return CYAN if score >= 60 else AMBER if score >= 40 else RED
def score_pill(score): return "BULL" if score >= 60 else "NEUTRAL" if score >= 40 else "BEAR"

# ============================================================================
# DATA LOADERS
# ============================================================================
@st.cache_resource
def get_fred(): return Fred(api_key=FRED_API_KEY)
fred = get_fred()

@st.cache_data(ttl=3600*6)
def load_fred_series(series_id, years=15):
    start = (datetime.now() - timedelta(days=365*years)).strftime('%Y-%m-%d')
    try: return fred.get_series(series_id, observation_start=start).dropna()
    except: return pd.Series(dtype=float)

@st.cache_data(ttl=3600*6)
def load_all_fred():
    return {
        'M2': load_fred_series('M2SL', 15), 'GDP': load_fred_series('GDP', 15), 
        'CPI': load_fred_series('CPIAUCSL', 15), 'REALYIELD': load_fred_series('DFII10', 10),
        'HY_OAS': load_fred_series('BAMLH0A0HYM2', 10), 'INDPRO': load_fred_series('INDPRO', 15),
        'UNRATE': load_fred_series('UNRATE', 15), 'DEFICIT': load_fred_series('FYFSGDA188S', 30),
        'DEBT_GDP': load_fred_series('GFDEGDQ188S', 30), 'TCU': load_fred_series('TCU', 15),
        'ULC': load_fred_series('ULCNFB', 15)
    }

@st.cache_data(ttl=3600*2)
def load_market_data():
    tickers = {'OIL': 'CL=F', 'MOVE': '^MOVE', 'VIX': '^VIX', 'DXY': 'DX-Y.NYB'}
    res = {}
    for name, ticker in tickers.items():
        try:
            df = yf.download(ticker, period="5y", progress=False)
            if not df.empty: res[name] = df['Close'].squeeze().dropna()
        except: pass
    return res

# ============================================================================
# MACRO FUNCTIONS (Copilot logic)
# ============================================================================
def compute_m2_real(m2, cpi):
    if m2.empty or cpi.empty: return pd.Series(dtype=float)
    m2_m, cpi_m = m2.resample("M").last().align(cpi.resample("M").last(), join="inner")
    if len(m2_m) == 0: return pd.Series(dtype=float)
    return ((m2_m / (cpi_m / cpi_m.iloc[0] * 100)) * 100).dropna()

def compute_velocity(m2, gdp):
    if m2.empty or gdp.empty: return pd.Series(dtype=float)
    gdp_a, m2_a = gdp.align(m2.resample("Q").last(), join="inner")
    return (gdp_a / m2_a).dropna()

def compute_yoy(series): return series.pct_change(12) * 100 if not series.empty else pd.Series(dtype=float)
def compute_unrate_3m_change(unrate): return unrate.diff(3) if not unrate.empty else pd.Series(dtype=float)

# ============================================================================
# SCORING ENGINE
# ============================================================================
ZW = 36 # Z-score window months

def score_pillar_monetary(data):
    scores, ind = [], {}
    # 1. Real Yield
    ry = data.get('REALYIELD', pd.Series())
    if not ry.empty:
        z = zscore_series(ry, ZW)
        s = zscore_to_score(z.iloc[-1], invert=True)
        scores.append(s)
        ind['Real Yield 10Y'] = {'val': round(ry.iloc[-1], 2), 'z': z.iloc[-1], 'score': s, 'series': ry, 'unit': '%', 'desc': "Tasso reale: basso = bull"}
    # 2. HY OAS
    hy = data.get('HY_OAS', pd.Series())
    if not hy.empty:
        z = zscore_series(hy, ZW)
        s = zscore_to_score(z.iloc[-1], invert=True)
        scores.append(s)
        ind['HY Spread'] = {'val': round(hy.iloc[-1], 0), 'z': z.iloc[-1], 'score': s, 'series': hy, 'unit': 'bp', 'desc': "Spread credito: basso = bull"}
    # 3. M2 Reale YoY (Copilot logic)
    m2r = compute_m2_real(data.get('M2', pd.Series()), data.get('CPI', pd.Series()))
    m2r_yoy = m2r.pct_change(12)*100
    if not m2r_yoy.empty:
        z = zscore_series(m2r_yoy, ZW)
        s = zscore_to_score(z.iloc[-1], invert=False)
        scores.append(s)
        ind['M2 Reale YoY'] = {'val': round(m2r_yoy.iloc[-1], 2), 'z': z.iloc[-1], 'score': s, 'series': m2r_yoy, 'unit': '%', 'desc': "Liquidità depurata da inflazione"}
    return np.mean(scores) if scores else 50.0, ind

def score_pillar_real_economy(data, pmi_manual):
    scores, ind = [], {}
    if pmi_manual:
        s = min(100, max(0, (pmi_manual - 30) / 40 * 100))
        scores.append(s)
        ind['PMI Composito'] = {'val': pmi_manual, 'z': (pmi_manual-50)/5, 'score': s, 'series': None, 'unit': '', 'desc': ">50 Espansione"}
    
    ip_yoy = compute_yoy(data.get('INDPRO', pd.Series())).dropna()
    if not ip_yoy.empty:
        z = zscore_series(ip_yoy, ZW)
        s = zscore_to_score(z.iloc[-1], invert=False)
        scores.append(s)
        ind['IndPro YoY'] = {'val': round(ip_yoy.iloc[-1], 2), 'z': z.iloc[-1], 'score': s, 'series': ip_yoy, 'unit': '%', 'desc': "Crescita produzione industriale"}
        
    du = compute_unrate_3m_change(data.get('UNRATE', pd.Series())).dropna()
    if not du.empty:
        z = zscore_series(du, ZW)
        s = zscore_to_score(z.iloc[-1], invert=True) # disoccupazione scende = bull
        scores.append(s)
        ind['Disoccupazione Δ3M'] = {'val': round(du.iloc[-1], 2), 'z': z.iloc[-1], 'score': s, 'series': du, 'unit': 'pp', 'desc': "Variazione su 3 mesi (negativo=bull)"}
    return np.mean(scores) if scores else 50.0, ind

def score_pillar_fiscal_prod(data):
    # Combinato per brevità di codice, ma separato nella logica
    fc_scores, pr_scores = [], []
    ind_c, ind_d = {}, {}
    
    # FISCAL (C)
    deficit = data.get('DEFICIT', pd.Series())
    if not deficit.empty and len(deficit)>2:
        impulse = deficit.diff(1).dropna()
        if not impulse.empty:
            z = zscore_series(impulse, min(ZW, len(impulse)-1))
            s = zscore_to_score(z.iloc[-1], invert=True) # Più spesa = bull breve termine
            fc_scores.append(s)
            ind_c['Impulso Fiscale'] = {'val': round(impulse.iloc[-1], 2), 'z': z.iloc[-1], 'score': s, 'series': impulse, 'unit': '%PIL', 'desc': "Variazione deficit (negativo=espansivo)"}
            
    # PROD (D)
    tcu = data.get('TCU', pd.Series())
    if not tcu.empty:
        z = zscore_series(tcu, ZW)
        s = zscore_to_score(z.iloc[-1], invert=False)
        pr_scores.append(s)
        ind_d['Capacity Util.'] = {'val': round(tcu.iloc[-1], 1), 'z': z.iloc[-1], 'score': s, 'series': tcu, 'unit': '%', 'desc': "Utilizzo capacità"}
        
    return (np.mean(fc_scores) if fc_scores else 50.0, ind_c), (np.mean(pr_scores) if pr_scores else 50.0, ind_d)

def score_pillar_risk(mkt):
    scores, ind = [], {}
    
    # MOVE (Bond Volatility)
    move = mkt.get('MOVE')
    if move is not None and len(move)>60:
        z = zscore_series(move, min(756, len(move)-10))
        s = zscore_to_score(z.iloc[-1], invert=True) # High vol = Bear
        scores.append(s)
        ind['MOVE Index'] = {'val': round(move.iloc[-1], 1), 'z': z.iloc[-1], 'score': s, 'series': move, 'unit': 'pt', 'desc': "Volatilità Treasury (Stress obbligazionario)"}

    # VIX (Equity Volatility)
    vix = mkt.get('VIX')
    if vix is not None and len(vix)>60:
        z = zscore_series(vix, min(756, len(vix)-10))
        s = zscore_to_score(z.iloc[-1], invert=True)
        scores.append(s)
        ind['VIX Index'] = {'val': round(vix.iloc[-1], 1), 'z': z.iloc[-1], 'score': s, 'series': vix, 'unit': 'pt', 'desc': "Volatilità Azionaria"}

    # OIL
    oil = mkt.get('OIL')
    if oil is not None and len(oil)>60:
        z = zscore_series(oil, min(756, len(oil)-10))
        s = zscore_to_score(z.iloc[-1], invert=True) # Oil alto = shock
        scores.append(s)
        ind['Oil WTI'] = {'val': round(oil.iloc[-1], 1), 'z': z.iloc[-1], 'score': s, 'series': oil, 'unit': '$', 'desc': "Proxy shock materie prime/geopolitica"}

    return np.mean(scores) if scores else 50.0, ind

# ============================================================================
# UI & RENDERING
# ============================================================================
def render_sparkline(series, color):
    if series is None or series.empty or len(series) < 5: return
    s = series.dropna().iloc[-60:] # Ultimi 60 data point
    fig = go.Figure(go.Scatter(x=s.index, y=s.values, mode="lines", line=dict(color=color, width=2), hoverinfo="skip"))
    fig.update_layout(height=40, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", xaxis=dict(visible=False), yaxis=dict(visible=False))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

if 'pmi_composite' not in st.session_state: st.session_state['pmi_composite'] = 51.5

with st.sidebar:
    st.markdown('<div style="font-family:Syne;font-size:1.1rem;font-weight:800;color:#00f5c4;">🧭 MACRO CORE v2</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-label" style="margin-top:10px;">📊 Input Manuale</div>', unsafe_allow_html=True)
    pmi = st.number_input("PMI Composito USA", min_value=20.0, max_value=80.0, value=float(st.session_state['pmi_composite']), step=0.1)
    if st.button("🔄 Aggiorna Dati"): st.cache_data.clear(); st.rerun()

with st.spinner("Caricamento dati FRED e mercati..."):
    fred_data = load_all_fred()
    mkt_data = load_market_data()

sc_A, ind_A = score_pillar_monetary(fred_data)
sc_B, ind_B = score_pillar_real_economy(fred_data, pmi)
(sc_C, ind_C), (sc_D, ind_D) = score_pillar_fiscal_prod(fred_data)
sc_E, ind_E = score_pillar_risk(mkt_data)

composite = np.mean([sc_A, sc_B, sc_C, sc_D, sc_E])
growth_score = np.mean([sc_B, sc_D])
inflation_proxy = 100 - sc_A

# Regime Logic
if growth_score >= 50 and inflation_proxy < 50: reg_name, reg_col = "GOLDILOCKS", CYAN
elif growth_score >= 50 and inflation_proxy >= 50: reg_name, reg_col = "INFLATIONARY BOOM", AMBER
elif growth_score < 50 and inflation_proxy >= 50: reg_name, reg_col = "STAGFLATION", RED
else: reg_name, reg_col = "DISINFLATIONARY BUST", BLUE

# HEADER
st.markdown('<div class="main-title">🧭 Macro Core Engine v2.0</div>', unsafe_allow_html=True)
st.markdown(f'<div style="font-size:0.6rem;color:#7a9ab0;letter-spacing:2px;margin-bottom:16px;">Regime Corrente: <span style="color:{reg_col};font-weight:bold;">{reg_name}</span></div>', unsafe_allow_html=True)

# TABS
tabs = st.tabs(["🧭 Overview", "💰 A: Monetario", "📈 B: Reale", "🏛️ C/D: Fiscale+Prod", "⚠️ E: Rischio & Stress"])

with tabs[0]:
    c1, c2 = st.columns([2, 3])
    with c1:
        st.markdown(f"""
        <div style="background:#0a1a14;border:2px solid {reg_col};border-radius:8px;padding:24px;text-align:center;">
          <div style="font-size:0.6rem;color:{MUTED};letter-spacing:2px">REGIME MACRO</div>
          <div style="font-family:Syne;font-size:1.6rem;font-weight:800;color:{reg_col}">{reg_name}</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        fig_bars = go.Figure(go.Bar(
            x=['A: Monetario', 'B: Reale', 'C: Fiscale', 'D: Produttivo', 'E: Rischio'],
            y=[sc_A, sc_B, sc_C, sc_D, sc_E],
            marker_color=[score_color(s) for s in [sc_A, sc_B, sc_C, sc_D, sc_E]]
        ))
        fig_bars.add_hline(y=50, line_dash="dot", line_color=MUTED)
        fig_bars.update_layout(**base_layout("Scores (0-100)", 200), margin=dict(t=30, b=0, l=30, r=10))
        st.plotly_chart(fig_bars, use_container_width=True, config={"displayModeBar": False})

def render_pillar_tab(title, score, indicators, color_theme):
    st.markdown(f'<div class="section-label">{title}</div>', unsafe_allow_html=True)
    for name, data in indicators.items():
        col1, col2 = st.columns([2, 1])
        c = score_color(data['score'])
        with col1:
            st.markdown(f"""
            <div style="background:#0a0f18;border:1px solid #1c2a3a;border-radius:4px;padding:12px;margin-bottom:10px;">
              <div style="font-size:0.6rem;color:{MUTED};letter-spacing:2px">{name.upper()}</div>
              <div style="font-family:Syne;font-size:1.2rem;color:{c};font-weight:700">{data['val']} {data['unit']}</div>
              <div style="font-size:0.55rem;color:#4a6070">{data['desc']} · Score: {data['score']:.0f}/100</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
            render_sparkline(data['series'], c)

with tabs[1]: render_pillar_tab("Pilastro A: Condizioni Monetarie", sc_A, ind_A, CYAN)
with tabs[2]: render_pillar_tab("Pilastro B: Economia Reale", sc_B, ind_B, BLUE)
with tabs[3]: 
    render_pillar_tab("Pilastro C: Politica Fiscale", sc_C, ind_C, AMBER)
    render_pillar_tab("Pilastro D: Capacità Produttiva", sc_D, ind_D, AMBER)
with tabs[4]: render_pillar_tab("Pilastro E: Rischio e Stress Sistemico", sc_E, ind_E, RED)
