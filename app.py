"""
MACRO CORE ENGINE v1.3
======================
5-Pillar Macro Regime Monitor
Companion: Settoriale · Commodity Supercycle · Bond Monitor · Equity Pulse

v1.3 — ibrido Claude + Copilot:
  - Percentile scoring (vs z-score) — piu' robusto, non dipende dalla finestra
  - MOVE Index sostituisce GPR manuale — tutto automatico via yfinance
  - Macro Breadth + Regime Confidence — nuove metriche sintetiche
  - M2 Reale (CPI defl.) + Velocity (GDP/M2) — piu' indicatori monetari
  - Mantenuto: layout tab, serie storica composite, alert cambio zona,
    implicazioni asset class per regime
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
# PAGE CONFIG
# ============================================================================
st.set_page_config(
    page_title="MACRO CORE ENGINE v1.3",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================================
# CSS
# ============================================================================
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;700;800&display=swap');
  :root {
    --bg:#111418; --surface:#1a1f24; --surface2:#20262d;
    --border:#2a323a; --text:#e6edf3; --muted:#8b9bb0;
    --cyan:#00f7ff; --lime:#c6ff1a; --orange:#ff8f1f;
    --blue:#3f8cff; --red:#ff4d6d; --magenta:#ff2bd4;
  }
  html,body,[data-testid="stAppViewContainer"],[data-testid="stApp"],.stApp {
    background-color:var(--bg) !important;
    color:var(--text) !important;
    font-family:'Space Mono',monospace !important;
  }
  [data-testid="stSidebar"] {
    background-color:#14181d !important;
    border-right:1px solid var(--border) !important;
  }
  header[data-testid="stHeader"] {
    background:#101318 !important;
    border-bottom:1px solid var(--border) !important;
  }
  [data-testid="stDecoration"] { display:none !important; }
  .block-container { padding-top:2.8rem; padding-bottom:2rem; }
  h1,h2,h3 { font-family:'Syne',sans-serif !important; }
  .main-title {
    font-family:'Syne',sans-serif; font-size:2.2rem; font-weight:800;
    color:var(--cyan); letter-spacing:-0.5px; text-transform:uppercase;
  }
  .sub-title {
    font-size:0.72rem; color:var(--muted);
    letter-spacing:3px; text-transform:uppercase; margin-top:4px;
  }
  .section-label {
    font-family:'Syne',sans-serif; font-size:0.65rem; letter-spacing:3px;
    text-transform:uppercase; color:var(--muted);
    border-bottom:1px solid var(--border);
    padding-bottom:4px; margin-bottom:10px; margin-top:20px;
  }
  .metric-tile {
    background:var(--surface); border:1px solid var(--border);
    border-radius:6px; padding:12px 14px;
    position:relative; overflow:hidden; margin-bottom:8px;
  }
  .metric-tile::before {
    content:''; position:absolute; top:0; left:0;
    width:3px; height:100%; background:var(--blue);
  }
  .metric-tile.red::before     { background:var(--red); }
  .metric-tile.amber::before   { background:var(--orange); }
  .metric-tile.cyan::before    { background:var(--cyan); }
  .metric-tile.lime::before    { background:var(--lime); }
  .metric-tile.magenta::before { background:var(--magenta); }
  .metric-label {
    font-size:0.62rem; letter-spacing:2px; text-transform:uppercase; color:var(--muted);
  }
  .metric-value {
    font-family:'Syne',sans-serif; font-size:1.7rem;
    font-weight:700; color:#f5f7fb; line-height:1.1;
  }
  .metric-sub { font-size:0.65rem; color:var(--muted); margin-top:4px; }
  .pill {
    display:inline-block; padding:2px 10px; border-radius:999px;
    font-size:0.6rem; letter-spacing:2px; text-transform:uppercase; font-weight:700;
  }
  .pill-bull { background:rgba(198,255,26,0.12); color:#c6ff1a; border:1px solid #c6ff1a; }
  .pill-bear { background:rgba(255,77,109,0.12); color:#ff4d6d; border:1px solid #ff4d6d; }
  .pill-neut { background:rgba(255,143,31,0.12); color:#ff8f1f; border:1px solid #ff8f1f; }
  .regime-card {
    background:var(--surface2); border-radius:8px;
    border:2px solid var(--cyan); padding:14px 18px; margin-bottom:10px;
  }
  .sidebar-section {
    font-size:0.7rem; font-weight:700; letter-spacing:2px;
    text-transform:uppercase; color:var(--orange);
    margin-top:18px; margin-bottom:4px;
    border-bottom:1px solid var(--border); padding-bottom:4px;
  }
  .summary-cell {
    background:var(--surface2); border:1px solid var(--border);
    border-radius:4px; padding:10px 12px; margin-bottom:6px;
  }
  .summary-cell-label {
    font-size:0.58rem; letter-spacing:2px; text-transform:uppercase; color:var(--muted);
  }
  .summary-cell-value {
    font-family:'Syne',sans-serif; font-size:1.4rem; font-weight:700; line-height:1.1;
  }
  [data-testid="stTabs"] button {
    font-family:'Space Mono',monospace !important;
    font-size:0.62rem !important; letter-spacing:2px !important;
    text-transform:uppercase !important;
  }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# CONSTANTS
# ============================================================================
PLOT_BG  = "#111418"
PAPER_BG = "#111418"
GRID_COL = "#2a323a"
CYAN     = "#00f7ff"
LIME     = "#c6ff1a"
ORANGE   = "#ff8f1f"
BLUE     = "#3f8cff"
RED      = "#ff4d6d"
MAGENTA  = "#ff2bd4"
TEXT_COL = "#e6edf3"
MUTED    = "#8b9bb0"
GOLD_COL = "#f7c948"

FRED_API_KEY = "938a76ed726e8351f43e1b0c36365784"

# ============================================================================
# HELPERS
# ============================================================================
def base_layout(title="", height=320):
    return dict(
        height=height,
        title=dict(text=title, font=dict(family="Syne", size=12, color=TEXT_COL), x=0.01),
        paper_bgcolor=PAPER_BG, plot_bgcolor=PLOT_BG,
        font=dict(family="Space Mono", color=TEXT_COL, size=10),
        xaxis=dict(gridcolor=GRID_COL, showgrid=True, zeroline=False,
                   tickfont=dict(size=9, color=MUTED)),
        yaxis=dict(gridcolor=GRID_COL, showgrid=True, zeroline=False,
                   tickfont=dict(size=9, color=MUTED)),
        margin=dict(l=52, r=48, t=40, b=40),
        legend=dict(font=dict(size=10, color=TEXT_COL), bgcolor="rgba(0,0,0,0)"),
        hovermode="x unified",
    )

def signal_pill(label):
    cls = {"BULL":"pill-bull","BEAR":"pill-bear","NEUTRAL":"pill-neut"}.get(label,"pill-neut")
    return f'<span class="pill {cls}">{label}</span>'

def tile_html(label, value, sub="", color_class="", pill=None):
    p = f'<div style="margin-top:6px">{signal_pill(pill)}</div>' if pill else ""
    return f"""<div class="metric-tile {color_class}">
      <div class="metric-label">{label}</div>
      <div class="metric-value">{value}</div>
      <div class="metric-sub">{sub}</div>{p}
    </div>"""

def score_color(s):
    if s >= 60: return LIME
    if s >= 40: return ORANGE
    return RED

def score_pill(s):
    if s >= 60: return "BULL"
    if s >= 40: return "NEUTRAL"
    return "BEAR"

def score_cc(s):
    if s >= 60: return "lime"
    if s >= 40: return "amber"
    return "red"

def pct_score(series, invert=False):
    s = series.dropna()
    if len(s) < 20: return 50.0
    val = float(s.iloc[-1])
    score = float((s < val).mean() * 100)
    return 100 - score if invert else score

def fmt(v, dec=2, suffix=""):
    if v is None or (isinstance(v, float) and np.isnan(v)): return "N/A"
    return f"{v:.{dec}f}{suffix}"

def cutoff_date(years):
    return pd.Timestamp.now() - pd.DateOffset(years=years)

def safe_ts(s):
    """Garantisce DatetimeIndex. Se impossibile, ritorna Series vuota."""
    if s is None or (isinstance(s, pd.Series) and s.empty):
        return pd.Series(dtype=float)
    if not isinstance(s.index, pd.DatetimeIndex):
        try:
            s = s.copy()
            s.index = pd.to_datetime(s.index)
        except Exception:
            return pd.Series(dtype=float)
    return s

def fbd(s, cut):
    """Filter by date — sicuro contro RangeIndex e None."""
    s = safe_ts(s)
    if s.empty:
        return s
    return s[s.index >= cut].dropna()

# ============================================================================
# FRED CLIENT
# ============================================================================
@st.cache_resource
def get_fred():
    return Fred(api_key=FRED_API_KEY)

fred_client = get_fred()

# ============================================================================
# DATA LOADERS
# ============================================================================
@st.cache_data(ttl=3600*6)
def load_fred_series(series_id, years=20):
    start = (datetime.now() - timedelta(days=365*years)).strftime("%Y-%m-%d")
    try:
        return fred_client.get_series(series_id, observation_start=start).dropna()
    except Exception:
        return pd.Series(dtype=float)

@st.cache_data(ttl=3600*6)
def load_all_fred():
    d = {}
    d["M2"]        = load_fred_series("M2SL",        25)
    d["GDP"]       = load_fred_series("GDP",          25)
    d["CPI"]       = load_fred_series("CPIAUCSL",     25)
    d["REALYIELD"] = load_fred_series("DFII10",       20)
    d["HY_OAS"]    = load_fred_series("BAMLH0A0HYM2", 20)
    d["IG_OAS"]    = load_fred_series("BAMLC0A0CM",   20)
    d["INDPRO"]    = load_fred_series("INDPRO",       20)
    d["UNRATE"]    = load_fred_series("UNRATE",       20)
    d["PAYEMS"]    = load_fred_series("PAYEMS",       20)
    d["PCE"]       = load_fred_series("PCEPILFE",     20)
    d["RETAIL"]    = load_fred_series("RSXFS",        20)
    d["DEFICIT"]   = load_fred_series("FYFSGDA188S",  30)
    d["DEBT_GDP"]  = load_fred_series("GFDEGDQ188S",  30)
    d["TCU"]       = load_fred_series("TCU",          20)
    d["ULC"]       = load_fred_series("ULCNFB",       20)
    d["PRODUC"]    = load_fred_series("OPHNFB",       20)
    return d

@st.cache_data(ttl=3600*4)
def load_market_data():
    result = {}
    tickers = {
        "OIL":  "CL=F",
        "EEM":  "EEM",
        "MOVE": "^MOVE",
        "GOLD": "GC=F",
        "DXY":  "DX-Y.NYB",
    }
    for name, ticker in tickers.items():
        try:
            df = yf.download(ticker, period="10y", progress=False, auto_adjust=True)
            if not df.empty:
                result[name] = df["Close"].squeeze().dropna()
        except Exception:
            pass
    return result

# ============================================================================
# DERIVED SERIES
# ============================================================================
def m2_gdp_ratio(m2, gdp):
    if m2.empty or gdp.empty: return pd.Series(dtype=float)
    m2_q = m2.resample("Q").last()
    g, m = gdp.align(m2_q, join="inner")
    return (m / g).dropna() if len(g) > 0 else pd.Series(dtype=float)

def m2_real(m2, cpi):
    if m2.empty or cpi.empty: return pd.Series(dtype=float)
    m2_m  = m2.resample("M").last()
    cpi_m = cpi.resample("M").last()
    m2_m, cpi_m = m2_m.align(cpi_m, join="inner")
    if len(m2_m) == 0: return pd.Series(dtype=float)
    return (m2_m / (cpi_m / cpi_m.iloc[0]) * 100).dropna()

def m2_velocity(m2, gdp):
    if m2.empty or gdp.empty: return pd.Series(dtype=float)
    m2_q = m2.resample("Q").last()
    g, m = gdp.align(m2_q, join="inner")
    return (g / m).dropna() if len(g) > 0 else pd.Series(dtype=float)

def yoy(series, periods=12):
    return series.pct_change(periods).mul(100).dropna()

def output_gap_proxy(indpro):
    if indpro.empty or len(indpro) < 36: return pd.Series(dtype=float)
    try:
        from scipy.signal import savgol_filter
        wl = min(61, len(indpro) - (1 if len(indpro) % 2 == 0 else 0))
        if wl < 5: raise ValueError
        trend = pd.Series(savgol_filter(indpro.values, wl, 2), index=indpro.index)
    except Exception:
        trend = indpro.rolling(36, min_periods=12).mean()
    return ((indpro - trend) / trend * 100).dropna()

# ============================================================================
# SCORING ENGINE
# ============================================================================
def score_monetary(d):
    ind, scores = {}, []
    mg = m2_gdp_ratio(d["M2"], d["GDP"])
    if not mg.empty:
        s = pct_score(mg.resample("M").interpolate())
        scores.append(s)
        ind["M2/PIL"] = {"value": fmt(float(mg.iloc[-1]), 3), "score": s,
                         "series": mg, "unit": "", "desc": "M2 / PIL nominale"}
    mr = m2_real(d["M2"], d["CPI"])
    if not mr.empty:
        s = pct_score(mr)
        scores.append(s)
        ind["M2 Reale"] = {"value": fmt(float(mr.iloc[-1]), 1), "score": s,
                            "series": mr, "unit": "idx", "desc": "M2 deflazionato da CPI"}
    vel = m2_velocity(d["M2"], d["GDP"])
    if not vel.empty:
        s = pct_score(vel.resample("M").interpolate())
        scores.append(s)
        ind["Velocity (GDP/M2)"] = {"value": fmt(float(vel.iloc[-1]), 3), "score": s,
                                     "series": vel, "unit": "x", "desc": "Velocita' moneta"}
    ry = d["REALYIELD"].resample("M").last() if not d["REALYIELD"].empty else pd.Series(dtype=float)
    if not ry.empty:
        s = pct_score(ry, invert=True)
        scores.append(s)
        ind["Real Yield 10Y"] = {"value": fmt(float(ry.iloc[-1]), 2), "score": s,
                                  "series": ry, "unit": "%", "desc": "TIPS 10Y · basso = bull"}
    hy = d["HY_OAS"].resample("M").last() if not d["HY_OAS"].empty else pd.Series(dtype=float)
    if not hy.empty:
        s = pct_score(hy, invert=True)
        scores.append(s)
        ind["HY OAS Spread"] = {"value": fmt(float(hy.iloc[-1]), 0), "score": s,
                                 "series": hy, "unit": "bp", "desc": "Spread HY · basso = no stress"}
    return round(float(np.mean(scores)) if scores else 50.0, 1), ind

def score_real_economy(d, pmi):
    ind, scores = {}, []
    if pmi is not None:
        s = min(100, max(0, (pmi - 30) / (70 - 30) * 100))
        scores.append(s)
        ind["PMI Composito"] = {"value": fmt(pmi, 1), "score": round(s, 1),
                                 "series": None, "unit": "", "desc": ">52 exp · <48 contr · manuale"}
    if not d["INDPRO"].empty:
        ip_yoy = yoy(d["INDPRO"]).resample("M").last()
        if not ip_yoy.empty:
            s = pct_score(ip_yoy)
            scores.append(s)
            ind["INDPRO YoY"] = {"value": fmt(float(ip_yoy.iloc[-1]), 1), "score": s,
                                  "series": ip_yoy, "unit": "%", "desc": "Produzione industriale YoY"}
    if not d["UNRATE"].empty:
        du = d["UNRATE"].diff(3).dropna().resample("M").last()
        if not du.empty:
            s = pct_score(du, invert=True)
            scores.append(s)
            ind["Disoccupazione D3M"] = {"value": fmt(float(du.iloc[-1]), 2), "score": s,
                                          "series": du, "unit": "pp", "desc": "Var 3M · neg = miglioramento"}
    if not d["PAYEMS"].empty:
        nfp3 = (d["PAYEMS"].diff(3) / 1000).dropna().resample("M").last()
        if not nfp3.empty:
            s = pct_score(nfp3)
            scores.append(s)
            ind["NFP D3M"] = {"value": fmt(float(nfp3.iloc[-1]), 0), "score": s,
                               "series": nfp3, "unit": "K", "desc": "Occupazione non-agricola 3M"}
    if not d["PCE"].empty:
        pce_yoy = yoy(d["PCE"]).resample("M").last()
        if not pce_yoy.empty:
            s = pct_score(abs(pce_yoy - 2.0), invert=True)
            scores.append(s)
            ind["Core PCE YoY"] = {"value": fmt(float(pce_yoy.iloc[-1]), 2), "score": s,
                                    "series": pce_yoy, "unit": "%", "desc": "PCE core · ottimale vicino 2%"}
    return round(float(np.mean(scores)) if scores else 50.0, 1), ind

def score_fiscal(d):
    ind, scores = {}, []
    if not d["DEFICIT"].empty:
        impulse = d["DEFICIT"].diff(1).dropna()
        if not impulse.empty:
            s = pct_score(impulse, invert=True)
            scores.append(s)
            ind["Impulso Fiscale"] = {"value": fmt(float(impulse.iloc[-1]), 2), "score": s,
                                       "series": impulse, "unit": "% PIL", "desc": "Delta deficit/PIL"}
        ind["Deficit/PIL"] = {"value": fmt(float(d["DEFICIT"].iloc[-1]), 1), "score": None,
                               "series": d["DEFICIT"], "unit": "% PIL", "desc": "Solo informativo"}
    if not d["DEBT_GDP"].empty:
        s = pct_score(d["DEBT_GDP"], invert=True)
        scores.append(s)
        ind["Debito/PIL"] = {"value": fmt(float(d["DEBT_GDP"].iloc[-1]), 1), "score": s,
                              "series": d["DEBT_GDP"], "unit": "%", "desc": "Debito federale / PIL"}
    return round(float(np.mean(scores)) if scores else 50.0, 1), ind

def score_productive(d):
    ind, scores = {}, []
    if not d["TCU"].empty:
        s = pct_score(d["TCU"])
        scores.append(s)
        ind["Capacity Utilization"] = {"value": fmt(float(d["TCU"].iloc[-1]), 1), "score": s,
                                        "series": d["TCU"], "unit": "%", "desc": "Utilizzo capacita' produttiva"}
    if not d["ULC"].empty:
        ulc_yoy = yoy(d["ULC"], 4).resample("Q").last()
        if not ulc_yoy.empty:
            s = pct_score(ulc_yoy, invert=True)
            scores.append(s)
            ind["ULC YoY"] = {"value": fmt(float(ulc_yoy.iloc[-1]), 2), "score": s,
                               "series": ulc_yoy, "unit": "%", "desc": "Unit labor costs YoY"}
    if not d["INDPRO"].empty:
        gap = output_gap_proxy(d["INDPRO"].resample("M").last())
        if not gap.empty:
            s = pct_score(gap)
            scores.append(s)
            ind["Output Gap"] = {"value": fmt(float(gap.iloc[-1]), 2), "score": s,
                                  "series": gap, "unit": "%", "desc": "Deviazione INDPRO da trend"}
    if not d["PRODUC"].empty:
        prod_yoy = yoy(d["PRODUC"], 4).resample("Q").last()
        if not prod_yoy.empty:
            s = pct_score(prod_yoy)
            scores.append(s)
            ind["Produttivita' YoY"] = {"value": fmt(float(prod_yoy.iloc[-1]), 2), "score": s,
                                         "series": prod_yoy, "unit": "%", "desc": "Output per ora lavorata"}
    return round(float(np.mean(scores)) if scores else 50.0, 1), ind

def score_geopolitical(mkt):
    ind, scores = {}, []
    oil = mkt.get("OIL")
    if oil is not None and len(oil) > 60:
        s = pct_score(oil, invert=True)
        scores.append(s)
        ind["Oil (WTI)"] = {"value": fmt(float(oil.iloc[-1]), 1), "score": s,
                             "series": oil, "unit": "$", "desc": "Petrolio · alto = rischio inflattivo"}
    eem = mkt.get("EEM")
    if eem is not None and len(eem) > 63:
        eem_3m = float(eem.iloc[-1] / eem.iloc[-63] - 1) * 100
        s = min(100, max(0, (eem_3m + 20) / 40 * 100))
        scores.append(s)
        ind["EEM 3M"] = {"value": fmt(eem_3m, 1), "score": round(s, 1),
                          "series": eem, "unit": "%", "desc": "ETF EM 3 mesi · positivo = risk appetite"}
    move = mkt.get("MOVE")
    if move is not None and len(move) > 60:
        s = pct_score(move, invert=True)
        scores.append(s)
        ind["MOVE Index"] = {"value": fmt(float(move.iloc[-1]), 1), "score": s,
                              "series": move, "unit": "idx", "desc": "Bond vol globale · basso = stabilita'"}
    dxy = mkt.get("DXY")
    if dxy is not None and len(dxy) > 60:
        s = pct_score(dxy, invert=True)
        scores.append(s)
        ind["DXY"] = {"value": fmt(float(dxy.iloc[-1]), 1), "score": s,
                       "series": dxy, "unit": "", "desc": "Dollar Index · alto = stress EM"}
    return round(float(np.mean(scores)) if scores else 50.0, 1), ind

def compute_regime(growth, inflation):
    if growth >= 50 and inflation < 50:
        return "GOLDILOCKS",           LIME,   "Crescita solida · inflazione contenuta · ottimale per equity"
    if growth >= 50 and inflation >= 50:
        return "INFLATIONARY BOOM",    ORANGE, "Crescita forte · inflazione elevata · favorevole real assets"
    if growth < 50  and inflation >= 50:
        return "STAGFLATION",          RED,    "Crescita debole · inflazione alta · sfavorevole equity e bond"
    return     "DISINFLATIONARY BUST", BLUE,   "Crescita debole · disinflazione · favorevole bond lunghi"

# ============================================================================
# SIDEBAR
# ============================================================================
with st.sidebar:
    st.markdown(
        '<div style="font-family:Syne;font-size:1.15rem;font-weight:800;color:#00f7ff">'
        '🧭 MACRO CORE ENGINE</div>', unsafe_allow_html=True)
    st.markdown(
        '<div style="font-size:0.62rem;letter-spacing:3px;color:#4a6070;'
        'text-transform:uppercase;margin-bottom:14px">v1.3 · Regime Monitor</div>',
        unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section">📊 PMI Composito</div>', unsafe_allow_html=True)
    pmi = st.slider("PMI USA/Globale", 35.0, 65.0, 52.0, 0.1,
                    help=">52 espansione · <48 contrazione · 50 = neutro")
    st.markdown(
        '<div style="font-size:0.65rem;color:#8ab0c8;line-height:1.7;margin-bottom:4px">'
        'Fonte: ISM Manufacturing + Services<br>oppure S&P Global PMI Composite<br>'
        '<b>Aggiorna mensile</b></div>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section">⚙️ Impostazioni</div>', unsafe_allow_html=True)
    years_display = st.selectbox("Finestra grafici (anni)", [5, 10, 15, 20], index=1)

    if st.button("🔄 Aggiorna Dati FRED + Mercati", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    st.markdown(
        '<div style="font-size:0.55rem;color:#4a6070;line-height:1.9">'
        '<b style="color:#8b9bb0">Auto FRED:</b> M2, PIL, CPI, DFII10,<br>'
        'HY/IG OAS, INDPRO, UNRATE, NFP,<br>PCE, RETAIL, TCU, ULC, PRODUC,<br>'
        'Deficit/PIL, Debito/PIL<br>'
        '<b style="color:#8b9bb0">Auto yfinance:</b> Oil, EEM, MOVE, Gold, DXY<br>'
        '<b style="color:#8b9bb0">Manuale:</b> PMI Composito (slider)</div>',
        unsafe_allow_html=True)

# ============================================================================
# LOAD DATA
# ============================================================================
with st.spinner("Caricamento dati FRED + mercati..."):
    fred_data = load_all_fred()
    mkt_data  = load_market_data()

# ============================================================================
# COMPUTE SCORES
# ============================================================================
sA, indA = score_monetary(fred_data)
sB, indB = score_real_economy(fred_data, pmi)
sC, indC = score_fiscal(fred_data)
sD, indD = score_productive(fred_data)
sE, indE = score_geopolitical(mkt_data)

pillar_scores = {
    "A · Monetario":   sA,
    "B · Econ. Reale": sB,
    "C · Fiscale":     sC,
    "D · Produttivo":  sD,
    "E · Geopolitico": sE,
}

growth_score    = float(np.mean([sB, sD]))
inflation_proxy = 100 - sA
composite       = float(np.mean(list(pillar_scores.values())))
breadth         = float(np.mean([s > 50 for s in pillar_scores.values()]) * 100)
confidence      = float(np.mean([abs(s - 50) for s in pillar_scores.values()]))
regime_label, regime_color, regime_desc = compute_regime(growth_score, inflation_proxy)

# ============================================================================
# HEADER
# ============================================================================
st.markdown('<div class="main-title">🧭 Macro Core Engine</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">5-Pillar Macro Regime Monitor · FRED + yfinance + Manual · Percentile Scoring</div>',
    unsafe_allow_html=True)
st.markdown(
    f'<div style="font-size:0.6rem;color:{MUTED};text-align:right;margin-top:2px;margin-bottom:4px">'
    f'Last fetch: {datetime.utcnow().strftime("%Y-%m-%d %H:%M")} UTC · '
    f'PMI: {pmi:.1f} (manuale) · Scoring: percentile storico · v1.3</div>',
    unsafe_allow_html=True)
st.markdown(f'<hr style="border:0;border-top:1px solid {GRID_COL};margin-bottom:4px">',
            unsafe_allow_html=True)

# ============================================================================
# TABS
# ============================================================================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🧭 Overview Regime",
    "💰 Monetario",
    "📈 Economia Reale",
    "🏛️ Fiscale · Produttivo",
    "🌍 Geopolitico",
    "ℹ️ Metodologia",
])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — OVERVIEW
# ─────────────────────────────────────────────────────────────────────────────
with tab1:

    rc1, rc2, rc3 = st.columns([1.8, 1, 1])

    with rc1:
        st.markdown(f"""
        <div class="regime-card" style="border-color:{regime_color}">
          <div style="font-size:0.62rem;letter-spacing:3px;text-transform:uppercase;color:{MUTED}">Regime Macro Corrente</div>
          <div style="font-family:Syne;font-size:1.8rem;font-weight:800;color:{regime_color};margin-top:4px">{regime_label}</div>
          <div style="font-size:0.7rem;color:{MUTED};margin-top:6px">{regime_desc}</div>
          <div style="margin-top:10px">{signal_pill(score_pill(composite))}</div>
        </div>""", unsafe_allow_html=True)

    with rc2:
        for label, val, col in [
            ("Composite",      f"{composite:.0f}",      regime_color),
            ("Growth Score",   f"{growth_score:.0f}",   score_color(growth_score)),
            ("Inflation Proxy",f"{inflation_proxy:.0f}", ORANGE),
        ]:
            st.markdown(f"""<div class="summary-cell">
              <div class="summary-cell-label">{label}</div>
              <div class="summary-cell-value" style="color:{col}">{val}</div>
            </div>""", unsafe_allow_html=True)

    with rc3:
        for label, val, col in [
            ("Macro Breadth",     f"{breadth:.0f}%",   BLUE),
            ("Regime Confidence", f"{confidence:.1f}", MAGENTA),
            ("PMI (manuale)",     f"{pmi:.1f}",
             LIME if pmi > 52 else (RED if pmi < 48 else ORANGE)),
        ]:
            st.markdown(f"""<div class="summary-cell">
              <div class="summary-cell-label">{label}</div>
              <div class="summary-cell-value" style="color:{col}">{val}</div>
            </div>""", unsafe_allow_html=True)

    chart_col, quad_col = st.columns([1.6, 1])

    with chart_col:
        st.markdown('<div class="section-label">Score per Pilastro (0–100 · percentile storico)</div>',
                    unsafe_allow_html=True)
        fig_bar = go.Figure()
        names = list(pillar_scores.keys())
        vals  = list(pillar_scores.values())
        fig_bar.add_bar(x=names, y=vals,
                        marker_color=[score_color(v) for v in vals],
                        text=[f"{v:.0f}" for v in vals],
                        textposition="outside",
                        textfont=dict(size=12, color=TEXT_COL))
        fig_bar.add_hline(y=60, line_dash="dot", line_color=LIME, line_width=1.2,
                          annotation_text="Bull 60", annotation_position="right",
                          annotation_font=dict(color=LIME, size=9))
        fig_bar.add_hline(y=40, line_dash="dot", line_color=RED, line_width=1.2,
                          annotation_text="Bear 40", annotation_position="right",
                          annotation_font=dict(color=RED, size=9))
        fig_bar.add_hline(y=composite, line_dash="solid", line_color=ORANGE, line_width=2,
                          annotation_text=f"Composite {composite:.0f}",
                          annotation_position="right",
                          annotation_font=dict(color=ORANGE, size=10))
        lb = base_layout("", 320)
        lb["yaxis"] = dict(range=[0, 110], gridcolor=GRID_COL, tickfont=dict(size=9, color=MUTED))
        lb["showlegend"] = False
        fig_bar.update_layout(**lb)
        st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})

    with quad_col:
        st.markdown('<div class="section-label">Mappa Quadranti</div>', unsafe_allow_html=True)
        fig_quad = go.Figure()
        lq = base_layout("", 320)
        lq["xaxis"] = dict(range=[0, 100], title="Liquidita' / Monetario",
                           gridcolor=GRID_COL, tickfont=dict(size=8, color=MUTED))
        lq["yaxis"] = dict(range=[0, 100], title="Crescita",
                           gridcolor=GRID_COL, tickfont=dict(size=8, color=MUTED))
        lq["showlegend"] = False
        lq["shapes"] = [
            dict(type="rect", x0=50, x1=100, y0=50, y1=100, fillcolor="rgba(198,255,26,0.05)", line_width=0),
            dict(type="rect", x0=0,  x1=50,  y0=50, y1=100, fillcolor="rgba(255,143,31,0.05)", line_width=0),
            dict(type="rect", x0=50, x1=100, y0=0,  y1=50,  fillcolor="rgba(63,140,255,0.05)", line_width=0),
            dict(type="rect", x0=0,  x1=50,  y0=0,  y1=50,  fillcolor="rgba(255,77,109,0.05)", line_width=0),
        ]
        fig_quad.update_layout(**lq)
        for qx, qy, ql, qc in [
            (75, 75, "GOLDILOCKS",   LIME),
            (25, 75, "INFL.BOOM",    ORANGE),
            (75, 25, "DISINFL.BUST", BLUE),
            (25, 25, "STAGFLATION",  RED),
        ]:
            fig_quad.add_annotation(x=qx, y=qy, text=f"<b>{ql}</b>",
                font=dict(family="Syne", size=9, color=qc), showarrow=False)
        fig_quad.add_vline(x=50, line_dash="dash", line_color=GRID_COL, line_width=1)
        fig_quad.add_hline(y=50, line_dash="dash", line_color=GRID_COL, line_width=1)
        fig_quad.add_trace(go.Scatter(
            x=[sA], y=[growth_score], mode="markers",
            marker=dict(size=16, color=regime_color, line=dict(color="white", width=2)),
            showlegend=False))
        st.plotly_chart(fig_quad, use_container_width=True, config={"displayModeBar": False})

    # Indicator table
    st.markdown('<div class="section-label">Dettaglio Score — tutti gli indicatori</div>',
                unsafe_allow_html=True)
    rows_html = ""
    for pillar_name, pcol, ind_dict in [
        ("Monetario",   CYAN,    indA),
        ("Econ. Reale", LIME,    indB),
        ("Fiscale",     ORANGE,  indC),
        ("Produttivo",  BLUE,    indD),
        ("Geopolitico", MAGENTA, indE),
    ]:
        for iname, idata in ind_dict.items():
            sc = idata.get("score")
            if sc is None: continue
            sc_col = score_color(sc)
            bar_w  = int(np.clip(sc, 0, 100))
            rows_html += f"""
            <tr>
              <td style="padding:5px 10px;font-size:0.62rem;color:{pcol}">{pillar_name}</td>
              <td style="padding:5px 10px;font-size:0.62rem;color:{TEXT_COL}">{iname}</td>
              <td style="padding:5px 10px;font-size:0.62rem;color:{TEXT_COL}">{idata['value']} {idata['unit']}</td>
              <td style="padding:5px 10px;font-size:0.62rem;color:{sc_col};font-weight:700">{sc:.0f}</td>
              <td style="padding:5px 10px;min-width:100px">
                <div style="background:#2a323a;border-radius:2px;height:5px">
                  <div style="background:{sc_col};height:5px;width:{bar_w}%;border-radius:2px"></div>
                </div>
              </td>
              <td style="padding:5px 10px">{signal_pill(score_pill(sc))}</td>
            </tr>"""
    st.markdown(f"""
    <div style="border:1px solid #2a323a;border-radius:6px;overflow:hidden">
      <table style="width:100%;border-collapse:collapse;background:#0e1318">
        <thead><tr style="background:#1a1f24">
          <th style="padding:6px 10px;text-align:left;font-size:0.55rem;letter-spacing:2px;color:{MUTED}">PILASTRO</th>
          <th style="padding:6px 10px;text-align:left;font-size:0.55rem;letter-spacing:2px;color:{MUTED}">INDICATORE</th>
          <th style="padding:6px 10px;text-align:left;font-size:0.55rem;letter-spacing:2px;color:{MUTED}">VALORE</th>
          <th style="padding:6px 10px;text-align:left;font-size:0.55rem;letter-spacing:2px;color:{MUTED}">SCORE</th>
          <th style="padding:6px 10px;text-align:left;font-size:0.55rem;letter-spacing:2px;color:{MUTED}">LIVELLO</th>
          <th style="padding:6px 10px;text-align:left;font-size:0.55rem;letter-spacing:2px;color:{MUTED}">SEGNALE</th>
        </tr></thead>
        <tbody>{rows_html}</tbody>
      </table>
    </div>""", unsafe_allow_html=True)

    # Historical composite
    st.markdown('<div class="section-label">Serie Storica Composite Score · Alert Cambio Zona</div>',
                unsafe_allow_html=True)

    @st.cache_data(ttl=3600*6)
    def build_historical_composite():
        try:
            f = Fred(api_key=FRED_API_KEY)
            def gs(sid, y=25):
                start = (datetime.now() - timedelta(days=365*y)).strftime("%Y-%m-%d")
                return f.get_series(sid, observation_start=start).dropna()
            m2   = gs("M2SL").resample("M").last()
            gdp  = gs("GDP").resample("M").last().ffill()
            ry   = gs("DFII10").resample("M").last()
            hy   = gs("BAMLH0A0HYM2").resample("M").last()
            ip   = gs("INDPRO").resample("M").last()
            ur   = gs("UNRATE").resample("M").last()
            tcu  = gs("TCU").resample("M").last()
            def_ = gs("FYFSGDA188S").resample("M").last().ffill()
            mg_h = (m2 / gdp).dropna()
            ip_y = ip.pct_change(12).mul(100)
            ur3  = ur.diff(3)

            def pct_roll(s, w=120, inv=False):
                res = s.rolling(w, min_periods=w//2).apply(
                    lambda x: float((x[:-1] < x[-1]).mean() * 100) if len(x) > 1 else 50.0,
                    raw=True)
                return 100 - res if inv else res

            sA_h = (pct_roll(mg_h) + pct_roll(ry, inv=True) + pct_roll(hy, inv=True)) / 3
            sB_h = (pct_roll(ip_y) + pct_roll(ur3, inv=True)) / 2
            sC_h = pct_roll(def_, inv=True)
            sD_h = pct_roll(tcu)
            sE_h = pd.Series(50.0, index=sA_h.index)
            comp = (sA_h*0.20 + sB_h*0.30 + sC_h*0.15 + sD_h*0.15 + sE_h*0.20).dropna()
            return pd.DataFrame({
                "Composite":  comp, "Monetario": sA_h,
                "Econ.Reale": sB_h, "Fiscale":   sC_h, "Produttivo": sD_h,
            }).dropna()
        except Exception:
            return pd.DataFrame()

    hist = build_historical_composite()

    if not hist.empty:
        h = fbd(hist, cutoff_date(max(years_display, 5))).copy()
        fig_h = go.Figure()
        fig_h.add_hrect(y0=60, y1=100, fillcolor="rgba(198,255,26,0.04)", line_width=0,
                        annotation_text="BULL ZONE", annotation_position="top right",
                        annotation_font=dict(color=LIME, size=8))
        fig_h.add_hrect(y0=0,  y1=40,  fillcolor="rgba(255,77,109,0.04)", line_width=0,
                        annotation_text="BEAR ZONE", annotation_position="bottom right",
                        annotation_font=dict(color=RED, size=8))
        fig_h.add_hline(y=60, line_dash="dot",   line_color=LIME,     line_width=1)
        fig_h.add_hline(y=40, line_dash="dot",   line_color=RED,      line_width=1)
        fig_h.add_hline(y=50, line_dash="solid", line_color=GRID_COL, line_width=0.8)
        for col_name, col_hex in [("Monetario", CYAN), ("Econ.Reale", LIME),
                                   ("Fiscale", ORANGE), ("Produttivo", BLUE)]:
            if col_name in h.columns:
                fig_h.add_trace(go.Scatter(x=h.index, y=h[col_name], name=col_name,
                    line=dict(color=col_hex, width=0.9, dash="dot"), opacity=0.3))
        fig_h.add_trace(go.Scatter(x=h.index, y=h["Composite"], name="Composite",
            line=dict(color=TEXT_COL, width=2.5)))
        last_c = float(h["Composite"].iloc[-1])
        fig_h.add_trace(go.Scatter(x=[h.index[-1]], y=[last_c], mode="markers",
            marker=dict(size=12, color=score_color(last_c), line=dict(color="white", width=2)),
            showlegend=False))
        lh = base_layout("Composite Score storico · Percentile rolling 10 anni", 320)
        lh["yaxis"] = dict(range=[0, 100], gridcolor=GRID_COL, tickfont=dict(size=9, color=MUTED))
        lh["legend"] = dict(orientation="h", y=-0.2, x=0.5, xanchor="center",
                             font=dict(size=10, color=TEXT_COL), bgcolor="rgba(0,0,0,0)")
        fig_h.update_layout(**lh)
        st.plotly_chart(fig_h, use_container_width=True, config={"displayModeBar": False})

        def _zone(s): return "BULL" if s >= 60 else ("BEAR" if s < 40 else "NEUTRAL")
        prev_z = _zone(float(h["Composite"].iloc[-2])) if len(h) >= 2 else _zone(composite)
        curr_z = _zone(composite)
        if prev_z != curr_z:
            ac   = LIME if curr_z == "BULL" else (ORANGE if curr_z == "NEUTRAL" else RED)
            icon = "📈" if curr_z == "BULL" else ("📉" if curr_z == "BEAR" else "⚠️")
            st.markdown(f"""
            <div style="background:rgba(0,0,0,0.3);border:2px solid {ac};
                        border-radius:6px;padding:14px 18px;margin-top:6px">
              <div style="font-family:Syne;font-size:1rem;font-weight:800;color:{ac}">
                {icon} CAMBIO DI ZONA RILEVATO</div>
              <div style="font-size:0.7rem;color:{TEXT_COL};margin-top:6px">
                Composite passato da <b>{prev_z}</b> a
                <b style="color:{ac}">{curr_z}</b> ({composite:.0f}/100)
              </div>
            </div>""", unsafe_allow_html=True)
        else:
            mc     = LIME if curr_z == "BULL" else (RED if curr_z == "BEAR" else ORANGE)
            months = sum(1 for v in reversed(h["Composite"].values) if _zone(v) == curr_z)
            st.markdown(f"""
            <div style="background:#1a1f24;border:1px solid {mc};border-radius:6px;
                        padding:10px 16px;margin-top:6px;display:flex;align-items:center;gap:16px">
              <div style="font-family:Syne;font-size:1.4rem;font-weight:800;color:{mc}">{curr_z}</div>
              <div>
                <div style="font-size:0.65rem;color:{TEXT_COL};font-weight:700">
                  Zona stabile · nessun cambio regime</div>
                <div style="font-size:0.6rem;color:{MUTED};margin-top:2px">
                  {months} periodi consecutivi · Composite: {composite:.0f} ·
                  Breadth: {breadth:.0f}% · Confidence: {confidence:.1f}
                </div>
              </div>
            </div>""", unsafe_allow_html=True)
    else:
        st.info("Serie storica non disponibile — controlla connessione FRED.")

    # Asset class implications
    st.markdown('<div class="section-label">Implicazioni Operative per Asset Class</div>',
                unsafe_allow_html=True)
    IMPL = {
        "GOLDILOCKS": [
            ("Equity",    LIME,   "FAVOREVOLE", "Utili in crescita · multipli sostenibili"),
            ("Bond",      ORANGE, "NEUTRALE",   "Carry ok · duration non premiata"),
            ("Commodity", ORANGE, "SELETTIVO",  "Domanda buona · no spike inflattivi"),
            ("Cash",      RED,    "SOTTOPESO",  "Opportunity cost elevato"),
        ],
        "INFLATIONARY BOOM": [
            ("Equity",    ORANGE, "SELETTIVO",  "Value/Energy over Growth"),
            ("Bond",      RED,    "NEGATIVO",   "Duration sotto pressione"),
            ("Commodity", LIME,   "OTTIMALE",   "Oil · metalli · soft commodity"),
            ("Cash",      ORANGE, "NEUTRALE",   "Nominali alti · reali compressi"),
        ],
        "STAGFLATION": [
            ("Equity",    RED,    "NEGATIVO",   "Margini compressi · multipli deflazionati"),
            ("Bond",      RED,    "NEGATIVO",   "Inflazione erode rendimento reale"),
            ("Commodity", LIME,   "PARZIALE",   "Energia e metalli preziosi"),
            ("Cash",      LIME,   "RELATIVO",   "Tassi nominali elevati"),
        ],
        "DISINFLATIONARY BUST": [
            ("Equity",    ORANGE, "DIFENSIVO",  "Qualita' e dividendi"),
            ("Bond",      LIME,   "OTTIMALE",   "Duration lunga · flight to quality"),
            ("Commodity", RED,    "NEGATIVO",   "Domanda debole · prezzi giu'"),
            ("Cash",      ORANGE, "NEUTRALE",   "Rendimento reale positivo"),
        ],
    }
    impl = IMPL.get(regime_label, IMPL["GOLDILOCKS"])
    c1, c2, c3, c4 = st.columns(4)
    for col, (asset, ac, status, desc) in zip([c1, c2, c3, c4], impl):
        rgb = tuple(int(ac.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
        col.markdown(f"""
        <div style="background:rgba({rgb[0]},{rgb[1]},{rgb[2]},0.07);
                    border:1px solid {ac};border-radius:6px;
                    padding:14px;text-align:center">
          <div style="font-size:0.6rem;letter-spacing:2px;color:{MUTED};margin-bottom:6px">
            {asset.upper()}</div>
          <div style="font-family:Syne;font-size:0.85rem;font-weight:700;color:{ac}">
            {status}</div>
          <div style="font-size:0.62rem;color:#8ab0c8;margin-top:6px;line-height:1.6">
            {desc}</div>
        </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — MONETARIO
# ─────────────────────────────────────────────────────────────────────────────
with tab2:
    st.markdown(
        "<div class='section-label'>Pilastro A · Monetario — Liquidita' · Costo Denaro · Credito</div>",
        unsafe_allow_html=True)
    cut = cutoff_date(years_display)
    sc_col, det_col = st.columns([1, 3])

    with sc_col:
        st.markdown(tile_html("SCORE PILASTRO A", f"{sA:.0f}/100",
                               "Monetario", score_cc(sA), score_pill(sA)),
                    unsafe_allow_html=True)
        for name, idata in indA.items():
            sc = idata.get("score")
            if sc is None: continue
            st.markdown(tile_html(name, f"{idata['value']} {idata['unit']}",
                                   f"Score: {sc:.0f}/100 · {idata['desc']}",
                                   score_cc(sc)), unsafe_allow_html=True)

    with det_col:
        mg_s  = m2_gdp_ratio(fred_data["M2"], fred_data["GDP"])
        mr_s  = m2_real(fred_data["M2"], fred_data["CPI"])
        vel_s = m2_velocity(fred_data["M2"], fred_data["GDP"])

        fig_m2 = make_subplots(rows=3, cols=1, shared_xaxes=True,
            subplot_titles=("M2/PIL Ratio", "M2 Reale (CPI defl.)", "Velocity (GDP/M2)"),
            vertical_spacing=0.07)
        for s, row, col_hex, name in [
            (mg_s,  1, CYAN,    "M2/PIL"),
            (mr_s,  2, BLUE,    "M2 Real"),
            (vel_s, 3, MAGENTA, "Velocity"),
        ]:
            sc2 = fbd(s, cut)
            if not sc2.empty:
                fig_m2.add_trace(go.Scatter(x=sc2.index, y=sc2.values,
                    line=dict(color=col_hex, width=1.8), name=name), row=row, col=1)
                fig_m2.add_hline(y=float(sc2.iloc[-1]), line_dash="dot",
                    line_color=col_hex, line_width=0.7, opacity=0.5, row=row, col=1,
                    annotation_text=f"{sc2.iloc[-1]:.3f}", annotation_position="right",
                    annotation_font=dict(color=col_hex, size=8))
        lm2 = base_layout("", 500)
        for i in range(2, 4):
            lm2[f"xaxis{i}"] = dict(gridcolor=GRID_COL)
            lm2[f"yaxis{i}"] = dict(gridcolor=GRID_COL)
        fig_m2.update_layout(**lm2)
        st.plotly_chart(fig_m2, use_container_width=True, config={"displayModeBar": False})

        ry_s = fred_data["REALYIELD"].resample("M").last()
        hy_s = fred_data["HY_OAS"].resample("M").last()
        fig_ry = make_subplots(rows=2, cols=1, shared_xaxes=True,
            subplot_titles=("Real Yield 10Y (%)", "HY OAS Spread (bp)"),
            vertical_spacing=0.08)
        for s, row, col_hex in [(ry_s, 1, ORANGE), (hy_s, 2, RED)]:
            sc2 = fbd(s, cut)
            if not sc2.empty:
                fig_ry.add_trace(go.Scatter(x=sc2.index, y=sc2.values,
                    line=dict(color=col_hex, width=1.8), showlegend=False), row=row, col=1)
                fig_ry.add_hline(y=float(sc2.iloc[-1]), line_dash="dot",
                    line_color=col_hex, line_width=0.7, opacity=0.5, row=row, col=1,
                    annotation_text=f"{sc2.iloc[-1]:.2f}", annotation_position="right",
                    annotation_font=dict(color=col_hex, size=8))
        if not ry_s.empty:
            fig_ry.add_hline(y=0, line_color=GRID_COL, line_width=1, row=1, col=1)
        lry = base_layout("", 360)
        lry["xaxis2"] = dict(gridcolor=GRID_COL)
        lry["yaxis2"] = dict(gridcolor=GRID_COL)
        fig_ry.update_layout(**lry)
        st.plotly_chart(fig_ry, use_container_width=True, config={"displayModeBar": False})

# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — ECONOMIA REALE
# ─────────────────────────────────────────────────────────────────────────────
with tab3:
    st.markdown(
        "<div class='section-label'>Pilastro B · Economia Reale — Ciclo · Occupazione · Domanda</div>",
        unsafe_allow_html=True)
    cut = cutoff_date(years_display)
    sc_col, det_col = st.columns([1, 3])

    with sc_col:
        st.markdown(tile_html("SCORE PILASTRO B", f"{sB:.0f}/100",
                               "Economia Reale", score_cc(sB), score_pill(sB)),
                    unsafe_allow_html=True)
        for name, idata in indB.items():
            sc = idata.get("score")
            if sc is None: continue
            st.markdown(tile_html(name, f"{idata['value']} {idata['unit']}",
                                   f"Score: {sc:.0f}/100", score_cc(sc)),
                        unsafe_allow_html=True)

    with det_col:
        ip_yoy  = yoy(fred_data["INDPRO"]).resample("M").last()
        pce_yoy = yoy(fred_data["PCE"]).resample("M").last()
        du      = fred_data["UNRATE"].diff(3).resample("M").last()
        nfp3    = (fred_data["PAYEMS"].diff(3) / 1000).resample("M").last()

        fig_eco = make_subplots(rows=2, cols=2,
            subplot_titles=("INDPRO YoY %", "Disoccupazione D3M (pp)",
                            "NFP D3M (000)", "Core PCE YoY %"),
            vertical_spacing=0.12, horizontal_spacing=0.08)
        for s, row, col, col_hex, name, use_bar in [
            (ip_yoy,  1, 1, CYAN,   "IP YoY",  False),
            (du,      1, 2, RED,    "UR D3M",  False),
            (nfp3,    2, 1, LIME,   "NFP D3M", True),
            (pce_yoy, 2, 2, ORANGE, "PCE YoY", False),
        ]:
            sc2 = fbd(s, cut)
            if not sc2.empty:
                if use_bar:
                    bc = [LIME if v > 0 else RED for v in sc2.values]
                    fig_eco.add_trace(go.Bar(x=sc2.index, y=sc2.values,
                        marker_color=bc, name=name), row=row, col=col)
                else:
                    fig_eco.add_trace(go.Scatter(x=sc2.index, y=sc2.values,
                        line=dict(color=col_hex, width=1.8), name=name), row=row, col=col)
                if any(v < 0 for v in sc2.values):
                    fig_eco.add_hline(y=0, line_color=GRID_COL,
                                      line_width=0.8, row=row, col=col)
        if not pce_yoy.empty:
            fig_eco.add_hline(y=2.0, line_dash="dot", line_color=LIME, line_width=1.2,
                row=2, col=2, annotation_text="Fed 2%",
                annotation_font=dict(color=LIME, size=8))
        le = base_layout("", 480)
        for ax in ["xaxis2","xaxis3","xaxis4","yaxis2","yaxis3","yaxis4"]:
            le[ax] = dict(gridcolor=GRID_COL)
        fig_eco.update_layout(**le)
        st.plotly_chart(fig_eco, use_container_width=True, config={"displayModeBar": False})

# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — FISCALE · PRODUTTIVO
# ─────────────────────────────────────────────────────────────────────────────
with tab4:
    col_fis, col_pro = st.columns(2)
    cut = cutoff_date(years_display)

    with col_fis:
        st.markdown("<div class='section-label'>Pilastro C · Fiscale</div>",
                    unsafe_allow_html=True)
        st.markdown(tile_html("SCORE PILASTRO C", f"{sC:.0f}/100",
                               "Fiscale", score_cc(sC), score_pill(sC)),
                    unsafe_allow_html=True)
        def_s  = fbd(fred_data["DEFICIT"], cut)
        imp_s  = fred_data["DEFICIT"].diff(1).dropna()
        imp_s  = fbd(imp_s, cut)
        debt_s = fbd(fred_data["DEBT_GDP"], cut)

        fig_fis = make_subplots(rows=3, cols=1, shared_xaxes=True,
            subplot_titles=("Deficit/PIL %", "Impulso Fiscale", "Debito/PIL %"),
            vertical_spacing=0.08)
        if not def_s.empty:
            bc = [LIME if v > 0 else RED for v in def_s.values]
            fig_fis.add_trace(go.Bar(x=def_s.index, y=def_s.values,
                marker_color=bc, name="Deficit/PIL"), row=1, col=1)
        if not imp_s.empty:
            bc2 = [LIME if v < 0 else RED for v in imp_s.values]
            fig_fis.add_trace(go.Bar(x=imp_s.index, y=imp_s.values,
                marker_color=bc2, name="Impulso"), row=2, col=1)
            fig_fis.add_hline(y=0, line_color=GRID_COL, line_width=0.8, row=2, col=1)
        if not debt_s.empty:
            fig_fis.add_trace(go.Scatter(x=debt_s.index, y=debt_s.values,
                line=dict(color=RED, width=2), name="Debito/PIL"), row=3, col=1)
        lfi = base_layout("", 500)
        for i in range(2, 4):
            lfi[f"xaxis{i}"] = dict(gridcolor=GRID_COL)
            lfi[f"yaxis{i}"] = dict(gridcolor=GRID_COL)
        fig_fis.update_layout(**lfi)
        st.plotly_chart(fig_fis, use_container_width=True, config={"displayModeBar": False})

    with col_pro:
        st.markdown("<div class='section-label'>Pilastro D · Produttivo</div>",
                    unsafe_allow_html=True)
        st.markdown(tile_html("SCORE PILASTRO D", f"{sD:.0f}/100",
                               "Produttivo", score_cc(sD), score_pill(sD)),
                    unsafe_allow_html=True)
        tcu_s   = fbd(fred_data["TCU"], cut)
        ulc_yoy = yoy(fred_data["ULC"], 4).resample("Q").last()
        ulc_s   = fbd(ulc_yoy, cut)
        gap_s   = output_gap_proxy(fred_data["INDPRO"].resample("M").last())
        gap_s   = fbd(gap_s, cut)
        prod_y  = yoy(fred_data["PRODUC"], 4).resample("Q").last()
        prod_s  = fbd(prod_y, cut)

        fig_pro = make_subplots(rows=4, cols=1, shared_xaxes=True,
            subplot_titles=("Capacity Util. %", "ULC YoY %",
                            "Output Gap %", "Produttivita' YoY %"),
            vertical_spacing=0.06)
        if not tcu_s.empty:
            fig_pro.add_trace(go.Scatter(x=tcu_s.index, y=tcu_s.values,
                line=dict(color=CYAN, width=1.8), name="TCU"), row=1, col=1)
            fig_pro.add_hline(y=80, line_dash="dot", line_color=ORANGE, line_width=0.8,
                row=1, col=1, annotation_text="80%",
                annotation_font=dict(color=ORANGE, size=8))
        for s, row, col_hex, name, use_bar in [
            (ulc_s,  2, RED,  "ULC",  True),
            (gap_s,  3, BLUE, "Gap",  True),
            (prod_s, 4, LIME, "Prod", False),
        ]:
            sc2 = s.dropna()
            if not sc2.empty:
                if use_bar:
                    bc = ([RED  if v > 0 else LIME for v in sc2.values] if row == 2
                          else [LIME if v > 0 else RED  for v in sc2.values])
                    fig_pro.add_trace(go.Bar(x=sc2.index, y=sc2.values,
                        marker_color=bc, name=name), row=row, col=1)
                else:
                    fig_pro.add_trace(go.Scatter(x=sc2.index, y=sc2.values,
                        line=dict(color=col_hex, width=1.8), name=name), row=row, col=1)
                fig_pro.add_hline(y=0, line_color=GRID_COL, line_width=0.8, row=row, col=1)
        lpr = base_layout("", 560)
        for i in range(2, 5):
            lpr[f"xaxis{i}"] = dict(gridcolor=GRID_COL)
            lpr[f"yaxis{i}"] = dict(gridcolor=GRID_COL)
        fig_pro.update_layout(**lpr)
        st.plotly_chart(fig_pro, use_container_width=True, config={"displayModeBar": False})

# ─────────────────────────────────────────────────────────────────────────────
# TAB 5 — GEOPOLITICO
# ─────────────────────────────────────────────────────────────────────────────
with tab5:
    st.markdown(
        "<div class='section-label'>Pilastro E · Geopolitico — Energia · EM · Bond Vol · Dollar</div>",
        unsafe_allow_html=True)
    cut = cutoff_date(years_display)
    sc_col, det_col = st.columns([1, 3])

    with sc_col:
        st.markdown(tile_html("SCORE PILASTRO E", f"{sE:.0f}/100",
                               "Geopolitico", score_cc(sE), score_pill(sE)),
                    unsafe_allow_html=True)
        for name, idata in indE.items():
            sc = idata.get("score")
            if sc is None: continue
            st.markdown(tile_html(name, f"{idata['value']} {idata['unit']}",
                                   f"Score: {sc:.0f}/100", score_cc(sc)),
                        unsafe_allow_html=True)
        st.markdown(f"""
        <div style="background:#1a1f24;border:1px solid {GRID_COL};
                    border-radius:4px;padding:10px 12px;margin-top:8px">
          <div style="font-size:0.58rem;letter-spacing:2px;color:{MUTED};margin-bottom:4px">NOTE v1.3</div>
          <div style="font-size:0.62rem;color:#8ab0c8;line-height:1.8">
            GPR Index rimosso (manuale difficile).<br>
            Sostituito con <b>MOVE Index</b> (^MOVE)<br>
            automatico via yfinance, daily.
          </div>
        </div>""", unsafe_allow_html=True)

    with det_col:
        oil  = mkt_data.get("OIL",  pd.Series())
        eem  = mkt_data.get("EEM",  pd.Series())
        move = mkt_data.get("MOVE", pd.Series())
        dxy  = mkt_data.get("DXY",  pd.Series())
        gold = mkt_data.get("GOLD", pd.Series())

        fig_geo = make_subplots(rows=2, cols=2,
            subplot_titles=("Oil WTI ($)", "MOVE Index (bond vol)",
                            "EEM ETF ($)", "DXY Dollar Index"),
            vertical_spacing=0.12, horizontal_spacing=0.08)
        for s, row, col, col_hex, name in [
            (oil,  1, 1, ORANGE,   "Oil"),
            (move, 1, 2, RED,      "MOVE"),
            (eem,  2, 1, BLUE,     "EEM"),
            (dxy,  2, 2, TEXT_COL, "DXY"),
        ]:
            if s is not None and not s.empty:
                sc2 = fbd(s, cut)
                if not sc2.empty:
                    fig_geo.add_trace(go.Scatter(x=sc2.index, y=sc2.values,
                        line=dict(color=col_hex, width=1.8), name=name), row=row, col=col)
        lge = base_layout("", 440)
        for ax in ["xaxis2","xaxis3","xaxis4","yaxis2","yaxis3","yaxis4"]:
            lge[ax] = dict(gridcolor=GRID_COL)
        fig_geo.update_layout(**lge)
        st.plotly_chart(fig_geo, use_container_width=True, config={"displayModeBar": False})

        if gold is not None and not gold.empty:
            gc = fbd(gold, cut)
            if not gc.empty:
                fig_gold = go.Figure()
                fig_gold.add_trace(go.Scatter(x=gc.index, y=gc.values,
                    line=dict(color=GOLD_COL, width=2),
                    fill="tozeroy", fillcolor="rgba(247,201,72,0.05)", name="Gold XAU"))
                fig_gold.update_layout(**base_layout("Gold XAU/USD — Safe Haven", 220))
                st.plotly_chart(fig_gold, use_container_width=True,
                                config={"displayModeBar": False})

# ─────────────────────────────────────────────────────────────────────────────
# TAB 6 — METODOLOGIA
# ─────────────────────────────────────────────────────────────────────────────
with tab6:
    st.markdown(f"""
<div style="background:#1a1f24;border:1px solid #2a323a;border-radius:6px;
            padding:24px 28px;font-size:0.68rem;line-height:2;color:#c8d8e8">
<h3 style="font-family:Syne;color:{CYAN};margin-top:0">🧭 Macro Core Engine v1.3 — Metodologia</h3>
<h4 style="color:{ORANGE}">1. Scoring — Percentile Storico</h4>
Ogni indicatore e' normalizzato tramite percentile sulla distribuzione storica completa.<br>
<code>Score = (osservazioni storiche minori del valore corrente) / n * 100</code><br>
Il 50 significa esattamente "a meta' della storia". Per indicatori bear (spread, debito,
volatilita') il punteggio e' invertito (100 - percentile).
<h4 style="color:{ORANGE}">2. Pilastri</h4>
<b style="color:{CYAN}">A · Monetario (20%)</b> — M2/PIL · M2 Reale · Velocity · Real Yield 10Y · HY OAS<br>
<b style="color:{LIME}">B · Economia Reale (30%)</b> — PMI · INDPRO YoY · Unemp D3M · NFP D3M · Core PCE<br>
<b style="color:{ORANGE}">C · Fiscale (15%)</b> — Impulso Fiscale · Debito/PIL<br>
<b style="color:{BLUE}">D · Produttivo (15%)</b> — Capacity Util. · ULC YoY · Output Gap · Produttivita'<br>
<b style="color:{MAGENTA}">E · Geopolitico (20%)</b> — Oil · EEM 3M · MOVE Index · DXY
<h4 style="color:{ORANGE}">3. Metriche Sintetiche (novita' v1.3)</h4>
<b>Macro Breadth</b>: % pilastri con score &gt; 50<br>
<b>Regime Confidence</b>: distanza media dei pilastri da 50<br>
<b>M2 Reale</b>: M2 deflazionato da CPI<br>
<b>Velocity</b>: GDP/M2 — trasmissione monetaria
<h4 style="color:{ORANGE}">4. Regime Macro — 4 Quadranti</h4>
<table style="font-size:0.62rem;border-collapse:collapse;width:100%">
  <tr style="background:#111418">
    <td style="padding:5px 10px;color:{LIME};font-weight:bold">GOLDILOCKS</td>
    <td style="padding:5px 10px">Growth &ge; 50 · Inflation proxy &lt; 50</td>
  </tr>
  <tr style="background:#1a1f24">
    <td style="padding:5px 10px;color:{ORANGE};font-weight:bold">INFLATIONARY BOOM</td>
    <td style="padding:5px 10px">Growth &ge; 50 · Inflation proxy &ge; 50</td>
  </tr>
  <tr style="background:#111418">
    <td style="padding:5px 10px;color:{BLUE};font-weight:bold">DISINFLATIONARY BUST</td>
    <td style="padding:5px 10px">Growth &lt; 50 · Inflation proxy &lt; 50</td>
  </tr>
  <tr style="background:#1a1f24">
    <td style="padding:5px 10px;color:{RED};font-weight:bold">STAGFLATION</td>
    <td style="padding:5px 10px">Growth &lt; 50 · Inflation proxy &ge; 50</td>
  </tr>
</table>
<h4 style="color:{ORANGE}">5. Fonti Dati</h4>
FRED: tutti gli indicatori macro USA — automatico, cache 6h<br>
yfinance: Oil, EEM, MOVE, Gold, DXY — automatico, cache 4h<br>
Manuale: PMI Composito — aggiorna mensile (ISM o S&P Global)
<h4 style="color:{ORANGE}">6. Changelog</h4>
v1.0: z-score, GPR manuale · v1.2 (Copilot): percentile, MOVE, M2 real, Velocity<br>
v1.3 (ibrido): mantiene tab + serie storica + alert zona + implicazioni asset class
<br><div style="font-size:0.55rem;color:#4a6070">
Companion: Settoriale · Commodity Supercycle · Bond Monitor · Equity Pulse<br>
Solo scopo informativo. Non costituisce consulenza finanziaria.</div>
</div>
""", unsafe_allow_html=True)

# ============================================================================
# FOOTER
# ============================================================================
st.markdown(f"""
<hr style="border:0;border-top:1px solid {GRID_COL};margin-top:24px">
<div style="font-size:0.55rem;color:#4a6070;text-align:center;line-height:2;padding-bottom:12px">
  🧭 MACRO CORE ENGINE v1.3 · 5 Pilastri · Percentile Scoring · FRED + yfinance<br>
  Auto FRED: M2, PIL, CPI, DFII10, HY/IG OAS, INDPRO, UNRATE, NFP, PCE, RETAIL, TCU, ULC, PRODUC, Deficit/PIL, Debito/PIL<br>
  Auto yfinance: Oil (CL=F) · EEM · MOVE (^MOVE) · Gold (GC=F) · DXY (DX-Y.NYB)<br>
  Manuale: PMI Composito · Regime: Goldilocks · Infl.Boom · Stagflation · Disinfl.Bust
</div>
""", unsafe_allow_html=True)
