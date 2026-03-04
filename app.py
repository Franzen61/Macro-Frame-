"""
MACRO CORE ENGINE v1.4.3
========================
5-Pillar Macro Regime Monitor
Companion: Settoriale · Commodity Supercycle · Bond Monitor · Equity Pulse

v1.4.3 — audit scoring engine:
  - PMI: formula lineare → pct_score expanding su serie ISM storica (confrontabile)
  - Impulso Fiscale: invert corretto (False) — espansivo = bull breve termine
  - HY OAS: pct_score calcolato in bp (uniformità, no ambiguità unità)
  - Output Gap: rimosso Savitzky-Golay (lookforward bias) → rolling causale 36m
  - Oil Geopolitico: livello assoluto → YoY change (distingue shock domanda/offerta)
  - build_historical_composite: allineato con nuovo scoring engine
  - M2/PIL rimosso da score (ridondante con Velocity) — solo grafico informativo
  - EEM: formula lineare → pct_score expanding su rendimento 3M

v1.4.2 — fix:
  - BUG FIX: m2_gdp_ratio e m2_velocity usano resample("QS") per allineamento
    corretto con GDP FRED (fix grafico M2/PIL vuoto e Velocity assente)

v1.4.1 — patch:
  - MOVE Index spostato da Geopolitico → Monetario (misura vol tassi, non geo)
  - GPR Index (Caldara & Iacoviello) integrato nel Pilastro E Geopolitico
  - File uploader CSV GPR in sidebar
  - DXY lookback esteso a 30Y
  - PMI summary card mostra valore numerico (bug fix)

v1.4 — fix + upgrade:
  - HY OAS: unità corretta (×100 → basis points)
  - Serie storica: percentile expanding
  - PMI automatico via FRED
  - STLFSI Financial Stress Index
  - Regime Persistence Metric
  - Tab Backtest rendimenti per regime
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
    page_title="MACRO CORE ENGINE v1.4",
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
    --bg:#070b12; --surface:#0e1420; --surface2:#141c28;
    --border:#1c2a3a; --text:#c8d8e8; --muted:#7a9ab0;
    --cyan:#00f5c4; --lime:#c6ff1a; --orange:#f5a623;
    --blue:#4da6ff; --red:#ff4d6d; --magenta:#ff2bd4;
  }
  html,body,[data-testid="stAppViewContainer"],[data-testid="stApp"],.stApp {
    background-color:var(--bg) !important;
    color:var(--text) !important;
    font-family:'Space Mono',monospace !important;
  }
  [data-testid="stSidebar"] {
    background-color:var(--surface) !important;
    border-right:1px solid var(--border) !important;
  }
  header[data-testid="stHeader"] {
    background:var(--bg) !important;
    border-bottom:1px solid var(--border) !important;
  }
  [data-testid="stDecoration"] { display:none !important; }
  .block-container { padding-top:2.8rem; padding-bottom:2rem; }
  h1,h2,h3 { font-family:'Syne',sans-serif !important; }
  .main-title {
    font-family:'Syne',sans-serif; font-size:2.2rem; font-weight:800;
    color:var(--cyan); letter-spacing:-1px; text-transform:uppercase;
  }
  .sub-title {
    font-size:0.68rem; color:var(--muted);
    letter-spacing:3px; text-transform:uppercase; margin-top:2px;
  }
  .section-label {
    font-family:'Syne',sans-serif; font-size:0.62rem; letter-spacing:4px;
    text-transform:uppercase; color:var(--muted);
    border-bottom:1px solid var(--border);
    padding-bottom:4px; margin-bottom:14px; margin-top:24px;
  }
  .metric-tile {
    background:var(--surface); border:1px solid var(--border);
    border-radius:4px; padding:14px 18px;
    position:relative; overflow:hidden; margin-bottom:10px;
  }
  .metric-tile::before {
    content:''; position:absolute; top:0; left:0;
    width:3px; height:100%; background:var(--cyan);
  }
  .metric-tile.red::before     { background:var(--red); }
  .metric-tile.amber::before   { background:var(--orange); }
  .metric-tile.lime::before    { background:var(--lime); }
  .metric-tile.blue::before    { background:var(--blue); }
  .metric-tile.magenta::before { background:var(--magenta); }
  .metric-label {
    font-size:0.58rem; letter-spacing:3px; text-transform:uppercase; color:var(--muted);
  }
  .metric-value {
    font-family:'Syne',sans-serif; font-size:1.7rem;
    font-weight:700; color:#eaf3ff; line-height:1.1;
  }
  .metric-sub { font-size:0.62rem; color:var(--muted); margin-top:2px; }
  .pill {
    display:inline-block; padding:2px 10px; border-radius:2px;
    font-size:0.58rem; letter-spacing:2px; text-transform:uppercase; font-weight:700;
  }
  .pill-bull { background:rgba(0,245,196,0.12);  color:#00f5c4; border:1px solid #00f5c4; }
  .pill-bear { background:rgba(255,77,109,0.12); color:#ff4d6d; border:1px solid #ff4d6d; }
  .pill-neut { background:rgba(245,166,35,0.12); color:#f5a623; border:1px solid #f5a623; }
  .sidebar-section {
    font-size:0.68rem; font-weight:700; letter-spacing:2px;
    text-transform:uppercase; color:var(--orange);
    margin-top:20px; margin-bottom:4px;
    border-bottom:1px solid var(--border); padding-bottom:4px;
  }
  .summary-cell {
    background:var(--surface2); border:1px solid var(--border);
    border-radius:4px; padding:10px 12px; margin-bottom:6px;
  }
  .summary-cell-label {
    font-size:0.55rem; letter-spacing:2px; text-transform:uppercase; color:var(--muted);
  }
  .summary-cell-value {
    font-family:'Syne',sans-serif; font-size:1.4rem; font-weight:700; line-height:1.1;
  }
  .regime-card {
    background:var(--surface2); border-radius:8px;
    border:2px solid var(--cyan); padding:18px 22px; margin-bottom:10px;
  }
  [data-testid="stTabs"] button {
    font-family:'Space Mono',monospace !important;
    font-size:0.6rem !important; letter-spacing:2px !important;
    text-transform:uppercase !important;
  }
  div[data-testid="stMetric"] { display:none; }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# CONSTANTS
# ============================================================================
PLOT_BG  = "#070b12"
PAPER_BG = "#0e1420"
GRID_COL = "#1c2a3a"
CYAN     = "#00f5c4"
LIME     = "#c6ff1a"
ORANGE   = "#f5a623"
BLUE     = "#4da6ff"
RED      = "#ff4d6d"
MAGENTA  = "#ff2bd4"
TEXT_COL = "#c8d8e8"
MUTED    = "#7a9ab0"
GOLD_COL = "#f7c948"
PURPLE   = "#bb88ff"

FRED_API_KEY = "938a76ed726e8351f43e1b0c36365784"

# ============================================================================
# GPR EVENTS
# ============================================================================
GPR_EVENTS = {
    "1900-07": "Boxer Rebellion",
    "1904-02": "Russia-Jap War",
    "1914-08": "WWI Begins",
    "1939-09": "WWII Begins",
    "1941-12": "Pearl Harbor",
    "1944-06": "D-Day",
    "1950-07": "Korean War",
    "1956-11": "Suez Crisis",
    "1962-10": "Cuban Missile",
    "1973-10": "Yom Kippur",
    "1980-01": "USSR→Afghan.",
    "1982-04": "Falklands",
    "1990-08": "Iraq→Kuwait",
    "1991-01": "Gulf War",
    "2001-09": "September 11",
    "2003-03": "Iraq War",
    "2011-02": "Arab Spring",
    "2014-03": "Crimea",
    "2015-11": "Paris Attacks",
    "2017-08": "US-Korea",
    "2020-03": "COVID-19",
    "2022-02": "Russia→Ukraine",
    "2023-10": "Gaza War",
    "2024-04": "Iran→Israel",
    "2025-01": "Trump 2.0",
}

# ============================================================================
# GPR DATA LOADER
# ============================================================================
def load_gpr_data(uploaded_file=None):
    try:
        if uploaded_file is not None:
            df = pd.read_csv(uploaded_file, sep=",", low_memory=False)
        else:
            return None
        df["month"] = pd.to_datetime(df["month"])
        df = df.sort_values("month")
        df = df[df["month"].dt.year >= 1900].reset_index(drop=True)
        cols = [c for c in ["month","GPR","GPRT","GPRA","GPRH","GPRHT","GPRHA"] if c in df.columns]
        return df[cols].copy()
    except Exception:
        return None

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
        margin=dict(l=52, r=60, t=40, b=36),
        legend=dict(font=dict(size=9, color=TEXT_COL), bgcolor="rgba(0,0,0,0)"),
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
    if s >= 60: return CYAN
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
    if s is None or (isinstance(s, pd.Series) and s.empty):
        return pd.Series(dtype=float)
    if not isinstance(s.index, pd.DatetimeIndex):
        try:
            s = s.copy(); s.index = pd.to_datetime(s.index)
        except Exception:
            return pd.Series(dtype=float)
    return s

def fbd(s, cut):
    s = safe_ts(s)
    if s.empty: return s
    return s[s.index >= cut].dropna()

def add_percentile_bands(fig, series, row=1, col=1, invert=False):
    if series is None or len(series.dropna()) < 20:
        return
    p25 = float(np.percentile(series.dropna(), 25))
    p75 = float(np.percentile(series.dropna(), 75))
    high_col   = RED  if invert else CYAN
    low_col    = CYAN if invert else RED
    high_label = "75p stress" if invert else "75p bull"
    low_label  = "25p bull"   if invert else "25p bear"
    fig.add_hline(y=p75, line_dash="dot", line_color=high_col, line_width=1,
                  annotation_text=f"{high_label} {p75:.2f}",
                  annotation_position="right",
                  annotation_font=dict(color=high_col, size=8), row=row, col=col)
    fig.add_hline(y=p25, line_dash="dot", line_color=low_col, line_width=1,
                  annotation_text=f"{low_label} {p25:.2f}",
                  annotation_position="right",
                  annotation_font=dict(color=low_col, size=8), row=row, col=col)

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
        s = fred_client.get_series(series_id, observation_start=start).dropna()
        # Normalizza indice a DatetimeIndex tz-naive
        if not isinstance(s.index, pd.DatetimeIndex):
            s.index = pd.to_datetime(s.index)
        if hasattr(s.index, "tz") and s.index.tz is not None:
            s.index = s.index.tz_localize(None)
        return s
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
    d["STLFSI"]    = load_fred_series("STLFSI4",      20)
    d["INDPRO"]    = load_fred_series("INDPRO",       20)
    d["UNRATE"]    = load_fred_series("UNRATE",       20)
    d["PAYEMS"]    = load_fred_series("PAYEMS",       20)
    d["PCE"]       = load_fred_series("PCEPILFE",     20)
    d["RETAIL"]    = load_fred_series("RSXFS",        20)
    d["ISM_MFG"]   = load_fred_series("NAPM",         20)
    d["ISM_SVC"]   = load_fred_series("NMFBAI",       20)
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
        "OIL": "CL=F", "EEM": "EEM", "MOVE": "^MOVE",
        "GOLD": "GC=F", "DXY": "DX-Y.NYB",
        "SPY": "SPY", "TLT": "TLT", "GLD": "GLD", "GSG": "GSG",
    }
    periods = {"DXY": "30y", "MOVE": "25y"}
    for name, ticker in tickers.items():
        try:
            period = periods.get(name, "25y")
            df = yf.download(ticker, period=period, progress=False, auto_adjust=True)
            if not df.empty:
                result[name] = df["Close"].squeeze().dropna()
        except Exception:
            pass
    return result

# ============================================================================
# DATA TRANSFORMS — v1.4.2: fix QS resample per allineamento GDP FRED
# ============================================================================
def _to_dti(s):
    """Forza indice a DatetimeIndex tz-naive — robusto a object/string/tz-aware da FRED."""
    s = s.copy()
    if not isinstance(s.index, pd.DatetimeIndex):
        s.index = pd.to_datetime(s.index)
    if hasattr(s.index, "tz") and s.index.tz is not None:
        s.index = s.index.tz_localize(None)
    return s

def m2_gdp_ratio(m2, gdp):
    if m2.empty or gdp.empty: return pd.Series(dtype=float)
    try:
        m2  = _to_dti(m2)
        gdp = _to_dti(gdp)
        m2_q  = m2.resample("QS").last()
        gdp_q = gdp.resample("QS").last().ffill()
        g, m  = gdp_q.align(m2_q, join="inner")
        if len(g) == 0: return pd.Series(dtype=float)
        ratio = (m / g).dropna()
        return ratio
    except Exception:
        return pd.Series(dtype=float)

def m2_real(m2, cpi):
    if m2.empty or cpi.empty: return pd.Series(dtype=float)
    try:
        m2  = _to_dti(m2)
        cpi = _to_dti(cpi)
        m2_m  = m2.resample("M").last()
        cpi_m = cpi.resample("M").last()
        m2_m, cpi_m = m2_m.align(cpi_m, join="inner")
        if len(m2_m) == 0: return pd.Series(dtype=float)
        return (m2_m / (cpi_m / cpi_m.iloc[0]) * 100).dropna()
    except Exception:
        return pd.Series(dtype=float)

def m2_velocity(m2, gdp):
    if m2.empty or gdp.empty: return pd.Series(dtype=float)
    try:
        m2  = _to_dti(m2)
        gdp = _to_dti(gdp)
        m2_q  = m2.resample("QS").last()
        gdp_q = gdp.resample("QS").last().ffill()
        g, m  = gdp_q.align(m2_q, join="inner")
        if len(g) == 0: return pd.Series(dtype=float)
        return (g / m).dropna()
    except Exception:
        return pd.Series(dtype=float)

def yoy(series, periods=12):
    return series.pct_change(periods).mul(100).dropna()

def output_gap_proxy(indpro):
    """
    Output gap proxy causale — nessun lookforward bias.
    Usa rolling mean a 36 mesi (causale) come trend di lungo periodo.
    Savitzky-Golay rimosso in v1.4.3: filtro simmetrico introduce lookforward bias
    che invalida il backtest storico (il trend al mese T usava dati fino a T+N).
    Rolling 36m: ogni punto usa solo dati passati → statisticamente valido.
    """
    if indpro.empty or len(indpro) < 36: return pd.Series(dtype=float)
    trend = indpro.rolling(36, min_periods=24).mean()
    return ((indpro - trend) / trend * 100).dropna()

def pmi_auto_fred(ism_mfg, ism_svc):
    if ism_mfg.empty and ism_svc.empty: return None
    if ism_mfg.empty: return float(ism_svc.iloc[-1]) if not ism_svc.empty else None
    if ism_svc.empty: return float(ism_mfg.iloc[-1]) if not ism_mfg.empty else None
    a, b = ism_mfg.resample("M").last().align(ism_svc.resample("M").last(), join="inner")
    if len(a) == 0: return None
    return float(a.iloc[-1] * 0.60 + b.iloc[-1] * 0.40)

# ============================================================================
# INDICATOR METADATA
# ============================================================================
INDICATOR_META = {
    "M2/PIL":              "C",   # informativo — inverso di Velocity, escluso da score
    "M2 Reale":            "C",
    "Velocity (GDP/M2)":   "C",
    "Real Yield 10Y":      "L",
    "HY OAS Spread":       "L",
    "Stress Finanziario":  "L",
    "MOVE Index":          "L",
    "PMI Composito":       "L",
    "INDPRO YoY":          "LAG",
    "Disoccupazione D3M":  "LAG",
    "NFP D3M":             "LAG",
    "Core PCE YoY":        "LAG",
    "Impulso Fiscale":     "L",
    "Debito/PIL":          "LAG",
    "Capacity Utilization":"C",
    "ULC YoY":             "LAG",
    "Output Gap":          "C",
    "Produttivita' YoY":   "LAG",
    "Oil (WTI)":           "L",
    "EEM 3M":              "L",
    "GPR Index":           "L",
    "DXY":                 "L",
}

# ============================================================================
# SCORING ENGINE
# ============================================================================
def score_monetary(d):
    ind, scores = {}, []

    mg = m2_gdp_ratio(d["M2"], d["GDP"])
    if not mg.empty:
        # M2/PIL è l'inverso esatto di Velocity (GDP/M2) → ridondante nello score
        # Tenuto come grafico informativo, score=None (come Deficit/PIL nel fiscale)
        ind["M2/PIL"] = {"value": fmt(float(mg.iloc[-1]), 3), "score": None,
                         "series": mg, "unit": "", "desc": "M2 / PIL nominale · solo informativo"}

    mr = m2_real(d["M2"], d["CPI"])
    if not mr.empty:
        s = pct_score(mr)
        scores.append(s)
        ind["M2 Reale"] = {"value": fmt(float(mr.iloc[-1]), 1), "score": s,
                            "series": mr, "unit": "idx", "desc": "M2 deflazionato da CPI"}

    vel = m2_velocity(d["M2"], d["GDP"])
    if not vel.empty:
        vel_m = vel.sort_index().resample("MS").last().reindex(
            pd.date_range(vel.index.min(), vel.index.max(), freq="MS")
        ).ffill().bfill()
        # v1.4.3: invert=True — velocity bassa coincide con QE/bull market (post-2008, post-COVID)
        # velocity alta coincide con restrizione monetaria/bear. Evidenza storica: r negativa con SPY.
        # Score calcolato su vel_m mensile, stessa serie usata per il grafico
        s = pct_score(vel_m, invert=True)
        scores.append(s)
        ind["Velocity (GDP/M2)"] = {"value": fmt(float(vel.iloc[-1]), 3), "score": s,
                                     "series": vel_m, "unit": "x",
                                     "desc": "Velocita' moneta · bassa = liquidita' abbondante = bull"}

    ry = d["REALYIELD"].resample("M").last() if not d["REALYIELD"].empty else pd.Series(dtype=float)
    if not ry.empty:
        s = pct_score(ry, invert=True)
        scores.append(s)
        ind["Real Yield 10Y"] = {"value": fmt(float(ry.iloc[-1]), 2), "score": s,
                                  "series": ry, "unit": "%", "desc": "TIPS 10Y · basso = bull"}

    hy = d["HY_OAS"].resample("M").last() if not d["HY_OAS"].empty else pd.Series(dtype=float)
    if not hy.empty:
        # v1.4.3: converte in bp prima del pct_score — uniformità e chiarezza
        hy_bp = hy * 100
        s = pct_score(hy_bp, invert=True)
        scores.append(s)
        ind["HY OAS Spread"] = {"value": fmt(float(hy_bp.iloc[-1]), 0), "score": s,
                                 "series": hy_bp, "unit": "bp", "desc": "Spread HY · basso = no stress"}

    stlfsi = d["STLFSI"].resample("M").last() if not d["STLFSI"].empty else pd.Series(dtype=float)
    if not stlfsi.empty:
        s = pct_score(stlfsi, invert=True)
        scores.append(s)
        ind["Stress Finanziario"] = {"value": fmt(float(stlfsi.iloc[-1]), 2), "score": s,
                                      "series": stlfsi, "unit": "idx",
                                      "desc": "STLFSI · neg = nessuno stress · pos = stress elevato"}

    move = d.get("MOVE")
    if move is not None and not (isinstance(move, pd.Series) and move.empty) and len(move) > 60:
        move_m = move.resample("M").last() if isinstance(move.index, pd.DatetimeIndex) else move
        s = pct_score(move_m, invert=True)
        scores.append(s)
        ind["MOVE Index"] = {"value": fmt(float(move.iloc[-1]), 1), "score": s,
                              "series": move_m, "unit": "idx",
                              "desc": "Bond vol implicita Treasury · basso = stabilita' tassi"}

    return round(float(np.mean(scores)) if scores else 50.0, 1), ind


def score_real_economy(d, pmi_override):
    ind, scores = {}, []

    pmi_auto = pmi_auto_fred(d.get("ISM_MFG", pd.Series()), d.get("ISM_SVC", pd.Series()))
    pmi = pmi_override if pmi_override is not None else pmi_auto
    pmi_source = "manuale" if pmi_override is not None else ("FRED ISM" if pmi_auto is not None else "N/A")

    if pmi is not None:
        # v1.4.3: pct_score su serie ISM storica — confrontabile con altri indicatori
        ism_combined = pd.Series(dtype=float)
        if not d.get("ISM_MFG", pd.Series()).empty and not d.get("ISM_SVC", pd.Series()).empty:
            a = d["ISM_MFG"].resample("M").last()
            b = d["ISM_SVC"].resample("M").last()
            a, b = a.align(b, join="inner")
            if len(a) > 0:
                ism_combined = (a * 0.60 + b * 0.40)
        elif not d.get("ISM_MFG", pd.Series()).empty:
            ism_combined = d["ISM_MFG"].resample("M").last()
        elif not d.get("ISM_SVC", pd.Series()).empty:
            ism_combined = d["ISM_SVC"].resample("M").last()
        if len(ism_combined) >= 20:
            s = pct_score(ism_combined)
        else:
            # fallback: formula lineare solo se serie storica insufficiente
            s = min(100, max(0, (pmi - 30) / (70 - 30) * 100))
        scores.append(s)
        ind["PMI Composito"] = {"value": fmt(pmi, 1), "score": round(s, 1),
                                 "series": ism_combined if not ism_combined.empty else None,
                                 "unit": "",
                                 "desc": f">52 exp · <48 contr · fonte: {pmi_source}"}

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

    return round(float(np.mean(scores)) if scores else 50.0, 1), ind, pmi_source


def score_fiscal(d):
    ind, scores = {}, []
    if not d["DEFICIT"].empty:
        impulse = d["DEFICIT"].diff(1).dropna()
        if not impulse.empty:
            # v1.4.3: invert=False — impulso espansivo (deficit crescente, valore più negativo)
            # è stimolativo → bull per crescita nel breve. Penalizzare solo quando si contrae.
            # Nota: FYFSGDA188S è deficit come % PIL con segno negativo → diff più negativo = più stimolo
            s = pct_score(impulse, invert=False)
            scores.append(s)
            ind["Impulso Fiscale"] = {"value": fmt(float(impulse.iloc[-1]), 2), "score": s,
                                       "series": impulse, "unit": "% PIL",
                                       "desc": "Delta deficit/PIL · espansivo = bull breve termine"}
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


def score_geopolitical(mkt, gpr_df=None):
    ind, scores = {}, []
    oil = mkt.get("OIL")
    if oil is not None and len(oil) > 250:
        # v1.4.3: YoY invece di livello assoluto — distingue shock da domanda (bull) vs
        # shock da offerta/geopolitico (bear). Accelerazione YoY negativa = rischio.
        oil_m = oil.resample("M").last()
        oil_yoy = oil_m.pct_change(12).mul(100).dropna()
        if len(oil_yoy) >= 20:
            s = pct_score(oil_yoy, invert=True)  # spike YoY = rischio inflattivo/geo = bear
            scores.append(s)
            ind["Oil (WTI)"] = {"value": fmt(float(oil.iloc[-1]), 1), "score": s,
                                 "series": oil_yoy, "unit": "$",
                                 "desc": "Petrolio YoY · spike = rischio inflattivo/geo"}
    eem = mkt.get("EEM")
    if eem is not None and len(eem) > 63:
        # v1.4.3: percentile expanding su rendimento 3M — confrontabile con gli altri indicatori
        eem_3m_series = eem.pct_change(63).mul(100).dropna()
        s = pct_score(eem_3m_series, invert=False)  # alto rendimento EM = bull = score alto
        eem_3m_last = float(eem_3m_series.iloc[-1])
        scores.append(s)
        ind["EEM 3M"] = {"value": fmt(eem_3m_last, 1), "score": round(s, 1),
                          "series": eem_3m_series, "unit": "%",
                          "desc": "ETF EM rendimento 3M · percentile expanding · alto = risk appetite"}
    dxy = mkt.get("DXY")
    if dxy is not None and len(dxy) > 60:
        s = pct_score(dxy, invert=True)
        scores.append(s)
        ind["DXY"] = {"value": fmt(float(dxy.iloc[-1]), 1), "score": s,
                       "series": dxy, "unit": "", "desc": "Dollar Index · lookback 30Y · alto = stress EM"}
    if gpr_df is not None and not gpr_df.empty:
        gpr_col = "GPR" if gpr_df["GPR"].notna().sum() > 50 else "GPRH"
        gpr_s   = gpr_df.set_index("month")[gpr_col].dropna()
        if len(gpr_s) > 20:
            s = pct_score(gpr_s, invert=True)
            scores.append(s)
            last_val = float(gpr_s.iloc[-1])
            ind["GPR Index"] = {"value": fmt(last_val, 1), "score": s,
                                 "series": gpr_s, "unit": "idx",
                                 "desc": f"Geopolitical Risk Index · basso = rischio contenuto · ({gpr_col})"}
    return round(float(np.mean(scores)) if scores else 50.0, 1), ind


def compute_regime(growth, inflation):
    if growth >= 50 and inflation < 50:
        return "GOLDILOCKS",           CYAN,   "Crescita solida · inflazione contenuta · ottimale per equity"
    if growth >= 50 and inflation >= 50:
        return "INFLATIONARY BOOM",    ORANGE, "Crescita forte · inflazione elevata · favorevole real assets"
    if growth < 50  and inflation >= 50:
        return "STAGFLATION",          RED,    "Crescita debole · inflazione alta · sfavorevole equity e bond"
    return     "DISINFLATIONARY BUST", BLUE,   "Crescita debole · disinflazione · favorevole bond lunghi"

# ============================================================================
# SERIE STORICA
# ============================================================================
@st.cache_data(ttl=3600*6)
def build_historical_composite():
    try:
        f = Fred(api_key=FRED_API_KEY)
        def gs(sid, y=25):
            start = (datetime.now() - timedelta(days=365*y)).strftime("%Y-%m-%d")
            return f.get_series(sid, observation_start=start).dropna()

        m2    = gs("M2SL").resample("M").last()
        gdp   = gs("GDP").resample("M").last().ffill()
        ry    = gs("DFII10").resample("M").last()
        hy    = gs("BAMLH0A0HYM2").resample("M").last()
        ip    = gs("INDPRO").resample("M").last()
        ur    = gs("UNRATE").resample("M").last()
        nfp   = gs("PAYEMS").resample("M").last()
        pce_s = gs("PCEPILFE").resample("M").last()
        tcu   = gs("TCU").resample("M").last()
        ulc_q = gs("ULCNFB").resample("Q").last().resample("M").ffill()
        def_  = gs("FYFSGDA188S").resample("M").last().ffill()
        debt  = gs("GFDEGDQ188S").resample("M").last().ffill()

        mg_h  = (m2 / gdp).dropna()
        ip_y  = ip.pct_change(12).mul(100)
        ur3   = ur.diff(3)
        nfp3  = (nfp.diff(3) / 1000)
        pce_y = pce_s.pct_change(12).mul(100)
        ulc_y = ulc_q.pct_change(4).mul(100)
        imp_f = def_.diff(1)

        def exp_pct(s, inv=False):
            res = s.expanding(min_periods=24).apply(
                lambda x: float((x[:-1] < x[-1]).mean() * 100) if len(x) > 1 else 50.0,
                raw=True)
            return (100 - res) if inv else res

        # v1.4.3: allineamento con scoring engine aggiornato
        # sA: Monetario — rimosso M2/PIL (ridondante con velocity), aggiunto velocity
        vel_h = (gdp / m2).dropna()
        sA_h = (exp_pct(vel_h, inv=True) + exp_pct(ry, inv=True) + exp_pct(hy, inv=True)) / 3
        # sB: Econ.Reale — invariato
        sB_h = (exp_pct(ip_y) + exp_pct(ur3, inv=True) +
                exp_pct(nfp3) + exp_pct(abs(pce_y - 2.0), inv=True)) / 4
        # sC: Fiscale — impulso fiscale ora invert=False (espansivo = bull breve)
        sC_h = (exp_pct(imp_f, inv=False) + exp_pct(debt, inv=True)) / 2
        # sD: Produttivo — invariato
        sD_h = (exp_pct(tcu) + exp_pct(ulc_y, inv=True)) / 2
        sE_h = pd.Series(50.0, index=sA_h.index)

        df = pd.DataFrame({"sA": sA_h, "sB": sB_h, "sC": sC_h, "sD": sD_h, "sE": sE_h}).dropna()
        df["Composite"]  = df["sA"]*0.20 + df["sB"]*0.30 + df["sC"]*0.15 + df["sD"]*0.15 + df["sE"]*0.20
        df["Monetario"]  = df["sA"]
        df["Econ.Reale"] = df["sB"]
        df["Fiscale"]    = df["sC"]
        df["Produttivo"] = df["sD"]
        return df[["Composite","Monetario","Econ.Reale","Fiscale","Produttivo"]].dropna()
    except Exception:
        return pd.DataFrame()

# ============================================================================
# BACKTESTING
# ============================================================================
@st.cache_data(ttl=3600*6)
def build_regime_backtest(hist_df):
    try:
        hist = hist_df.copy()
        hist["growth"]    = hist["Econ.Reale"]
        hist["inflation"] = 100 - hist["Monetario"]

        def classify(row):
            if row["growth"] >= 50 and row["inflation"] < 50:  return "GOLDILOCKS"
            if row["growth"] >= 50 and row["inflation"] >= 50: return "INFL.BOOM"
            if row["growth"] < 50  and row["inflation"] >= 50: return "STAGFLATION"
            return "DISINFL.BUST"

        hist["regime"] = hist.apply(classify, axis=1)
        assets = {}
        for ticker_name, ticker in [("SPY","SPY"),("TLT","TLT"),("GLD","GLD"),("GSG","GSG")]:
            try:
                df = yf.download(ticker, start="2000-01-01", progress=False, auto_adjust=True)
                if not df.empty:
                    pr = df["Close"].squeeze().dropna()
                    pr_m = pr.resample("M").last()
                    ret_m = pr_m.pct_change().mul(100)
                    assets[ticker_name] = ret_m
            except Exception:
                pass

        if not assets: return None

        asset_df = pd.DataFrame(assets).dropna(how="all")
        merged = hist[["regime"]].join(asset_df, how="inner").dropna()

        results = {}
        for regime in ["GOLDILOCKS","INFL.BOOM","STAGFLATION","DISINFL.BUST"]:
            sub = merged[merged["regime"] == regime]
            if len(sub) < 3:
                results[regime] = {"n_months": 0}
                continue
            row = {"n_months": len(sub)}
            for a in assets:
                if a in sub.columns:
                    row[f"{a}_avg"] = round(float(sub[a].mean()), 2)
                    row[f"{a}_hit"] = round(float((sub[a] > 0).mean() * 100), 0)
            results[regime] = row

        results["_regime_series"] = hist["regime"]
        return results
    except Exception:
        return None

# ============================================================================
# SIDEBAR
# ============================================================================
with st.sidebar:
    st.markdown(
        '<div style="font-family:Syne;font-size:1.1rem;font-weight:800;color:#00f5c4">'
        '🧭 MACRO CORE ENGINE</div>', unsafe_allow_html=True)
    st.markdown(
        '<div style="font-size:0.58rem;letter-spacing:3px;color:#4a6070;'
        'text-transform:uppercase;margin-bottom:14px">v1.4.2 · Regime Monitor</div>',
        unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section">📊 PMI Composito</div>', unsafe_allow_html=True)
    pmi_override_active = st.checkbox("Override PMI manuale", value=False)
    pmi_slider = st.slider("PMI USA/Globale", 35.0, 65.0, 52.0, 0.1,
        disabled=not pmi_override_active)
    pmi_manual = pmi_slider if pmi_override_active else None

    st.markdown('<div class="sidebar-section">🌍 GPR Index — Aggiornamento</div>',
        unsafe_allow_html=True)
    st.markdown(
        f'<div style="font-size:0.55rem;color:{MUTED};line-height:1.7;margin-bottom:6px">'
        'Carica il CSV aggiornato da<br>'
        '<b style="color:#8b9bb0">matteoiacoviello.com/gpr.htm</b><br>'
        'Formato: CSV virgola, colonne GPR/GPRH/GPRHT/GPRHA<br>'
        'Aggiornamento: mensile (~ giorno 10)</div>',
        unsafe_allow_html=True)
    gpr_uploaded = st.file_uploader("CSV GPR Index", type=["csv"],
        label_visibility="collapsed")
    if gpr_uploaded:
        st.markdown(
            f'<div style="font-size:0.58rem;color:{CYAN};margin-top:4px">'
            f'✓ File caricato: {gpr_uploaded.name}</div>', unsafe_allow_html=True)
    else:
        st.markdown(
            f'<div style="font-size:0.55rem;color:{MUTED};margin-top:2px">'
            'Nessun file — grafico GPR non disponibile</div>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section">⚙️ Impostazioni</div>', unsafe_allow_html=True)
    years_display = st.selectbox("Finestra grafici (anni)", [5, 10, 15, 20], index=1)

    if st.button("🔄 Aggiorna Dati FRED + Mercati", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    st.markdown(
        '<div style="font-size:0.55rem;color:#4a6070;line-height:1.9">'
        '<b style="color:#8b9bb0">Auto FRED:</b> M2, PIL, CPI, DFII10,<br>'
        'HY/IG OAS, STLFSI, INDPRO, UNRATE,<br>NFP, PCE, ISM Mfg/Svc,<br>'
        'TCU, ULC, PRODUC, Deficit, Debito<br>'
        '<b style="color:#8b9bb0">Auto yfinance:</b> Oil, EEM, MOVE, Gold, DXY<br>'
        '<b style="color:#8b9bb0">Backtest:</b> SPY, TLT, GLD, GSG<br>'
        '<b style="color:#8b9bb0">Manuale:</b> PMI (override) · GPR CSV (mensile)</div>',
        unsafe_allow_html=True)

# ============================================================================
# LOAD DATA + COMPUTE
# ============================================================================
with st.spinner("Caricamento dati FRED + mercati..."):
    fred_data = load_all_fred()
    mkt_data  = load_market_data()
    gpr_df    = load_gpr_data(gpr_uploaded)

fred_data["MOVE"] = mkt_data.get("MOVE", pd.Series(dtype=float))

sA, indA          = score_monetary(fred_data)
sB, indB, pmi_src = score_real_economy(fred_data, pmi_manual)
sC, indC          = score_fiscal(fred_data)
sD, indD          = score_productive(fred_data)
sE, indE          = score_geopolitical(mkt_data, gpr_df)

pillar_scores = {"A · Monetario": sA, "B · Econ. Reale": sB,
                 "C · Fiscale": sC, "D · Produttivo": sD, "E · Geopolitico": sE}

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
    '<div class="sub-title">5-Pillar Macro Regime Monitor · FRED + yfinance · Percentile Expanding · v1.4.2</div>',
    unsafe_allow_html=True)
st.markdown(
    f'<div style="font-size:0.58rem;color:{MUTED};text-align:right;margin-top:2px;margin-bottom:4px">'
    f'Last fetch: {datetime.utcnow().strftime("%Y-%m-%d %H:%M")} UTC · '
    f'PMI fonte: {pmi_src} · Scoring: percentile expanding</div>',
    unsafe_allow_html=True)
st.markdown(f'<hr style="border:0;border-top:1px solid {GRID_COL};margin-bottom:4px">', unsafe_allow_html=True)

# ============================================================================
# TABS
# ============================================================================
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🧭 Overview", "💰 Monetario", "📈 Econ. Reale",
    "🏛️ Fiscale · Produttivo", "🌍 Geopolitico",
    "📊 Backtest Regime", "ℹ️ Metodologia",
])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — OVERVIEW
# ─────────────────────────────────────────────────────────────────────────────
with tab1:
    rc1, rc2, rc3 = st.columns([1.8, 1, 1])

    with rc1:
        st.markdown(f"""
        <div class="regime-card" style="border-color:{regime_color}">
          <div style="font-size:0.58rem;letter-spacing:3px;text-transform:uppercase;color:{MUTED}">Regime Macro Corrente</div>
          <div style="font-family:Syne;font-size:1.8rem;font-weight:800;color:{regime_color};margin-top:4px">{regime_label}</div>
          <div style="font-size:0.68rem;color:{MUTED};margin-top:6px">{regime_desc}</div>
          <div style="margin-top:10px">{signal_pill(score_pill(composite))}</div>
        </div>""", unsafe_allow_html=True)

    with rc2:
        for label, val, col in [
            ("Composite",       f"{composite:.0f}",       regime_color),
            ("Growth Score",    f"{growth_score:.0f}",    score_color(growth_score)),
            ("Inflation Proxy", f"{inflation_proxy:.0f}", ORANGE),
        ]:
            st.markdown(f"""<div class="summary-cell">
              <div class="summary-cell-label">{label}</div>
              <div class="summary-cell-value" style="color:{col}">{val}</div>
            </div>""", unsafe_allow_html=True)

    with rc3:
        pmi_val_display = indB.get("PMI Composito", {}).get("value", "N/A")
        try:
            pv = float(pmi_val_display)
            pmi_col_rc3 = CYAN if pv > 52 else (RED if pv < 48 else ORANGE)
            pmi_display_rc3 = f"{pv:.1f} ({pmi_src[:4]})"
        except Exception:
            pmi_col_rc3 = MUTED
            pmi_display_rc3 = f"N/A ({pmi_src[:4]})"
        for label, val, col in [
            ("Macro Breadth",     f"{breadth:.0f}%",   BLUE),
            ("Regime Confidence", f"{confidence:.1f}", MAGENTA),
            ("PMI / fonte",       pmi_display_rc3,     pmi_col_rc3),
        ]:
            st.markdown(f"""<div class="summary-cell">
              <div class="summary-cell-label">{label}</div>
              <div class="summary-cell-value" style="color:{col}">{val}</div>
            </div>""", unsafe_allow_html=True)

    chart_col, quad_col = st.columns([1.6, 1])

    with chart_col:
        st.markdown('<div class="section-label">Score per Pilastro (0-100)</div>', unsafe_allow_html=True)
        fig_bar = go.Figure()
        names = list(pillar_scores.keys())
        vals  = list(pillar_scores.values())
        fig_bar.add_bar(x=names, y=vals,
            marker_color=[score_color(v) for v in vals],
            text=[f"{v:.0f}" for v in vals],
            textposition="outside",
            textfont=dict(size=12, color=TEXT_COL))
        fig_bar.add_hline(y=60, line_dash="dot", line_color=CYAN, line_width=1.2,
            annotation_text="Bull 60", annotation_position="right",
            annotation_font=dict(color=CYAN, size=9))
        fig_bar.add_hline(y=40, line_dash="dot", line_color=RED, line_width=1.2,
            annotation_text="Bear 40", annotation_position="right",
            annotation_font=dict(color=RED, size=9))
        fig_bar.add_hline(y=composite, line_dash="solid", line_color=ORANGE, line_width=2,
            annotation_text=f"Composite {composite:.0f}",
            annotation_position="right", annotation_font=dict(color=ORANGE, size=10))
        lb = base_layout("", 300)
        lb["yaxis"] = dict(range=[0, 115], gridcolor=GRID_COL, tickfont=dict(size=9, color=MUTED))
        lb["showlegend"] = False
        fig_bar.update_layout(**lb)
        st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})

    with quad_col:
        st.markdown('<div class="section-label">Mappa Quadranti</div>', unsafe_allow_html=True)
        fig_quad = go.Figure()
        lq = base_layout("", 300)
        lq["xaxis"] = dict(range=[0,100], title="Monetario",
                           gridcolor=GRID_COL, tickfont=dict(size=8, color=MUTED))
        lq["yaxis"] = dict(range=[0,100], title="Crescita",
                           gridcolor=GRID_COL, tickfont=dict(size=8, color=MUTED))
        lq["showlegend"] = False
        lq["shapes"] = [
            dict(type="rect", x0=50, x1=100, y0=50, y1=100, fillcolor="rgba(0,245,196,0.05)", line_width=0),
            dict(type="rect", x0=0,  x1=50,  y0=50, y1=100, fillcolor="rgba(245,166,35,0.05)", line_width=0),
            dict(type="rect", x0=50, x1=100, y0=0,  y1=50,  fillcolor="rgba(77,166,255,0.05)", line_width=0),
            dict(type="rect", x0=0,  x1=50,  y0=0,  y1=50,  fillcolor="rgba(255,77,109,0.05)", line_width=0),
        ]
        fig_quad.update_layout(**lq)
        for qx, qy, ql, qc in [(75,75,"GOLDILOCKS",CYAN),(25,75,"INFL.BOOM",ORANGE),
                                (75,25,"DISINFL.BUST",BLUE),(25,25,"STAGFLATION",RED)]:
            fig_quad.add_annotation(x=qx, y=qy, text=f"<b>{ql}</b>",
                font=dict(family="Syne", size=9, color=qc), showarrow=False)
        fig_quad.add_vline(x=50, line_dash="dash", line_color=GRID_COL, line_width=1)
        fig_quad.add_hline(y=50, line_dash="dash", line_color=GRID_COL, line_width=1)
        fig_quad.add_trace(go.Scatter(x=[sA], y=[growth_score], mode="markers",
            marker=dict(size=16, color=regime_color, line=dict(color="white", width=2)),
            showlegend=False))
        st.plotly_chart(fig_quad, use_container_width=True, config={"displayModeBar": False})

    radar_col, asset_col = st.columns([1, 1])
    with radar_col:
        st.markdown('<div class="section-label">Radar — Profilo Macro</div>', unsafe_allow_html=True)
        cats = ["Monetario", "Econ. Reale", "Fiscale", "Produttivo", "Geopolitico"]
        vr = [sA, sB, sC, sD, sE]
        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(r=vr+[vr[0]], theta=cats+[cats[0]],
            fill="toself", fillcolor="rgba(0,245,196,0.08)",
            line=dict(color=CYAN, width=2), name="Score"))
        fig_radar.add_trace(go.Scatterpolar(r=[50]*6, theta=cats+[cats[0]],
            line=dict(color=ORANGE, width=1, dash="dot"), name="Neutro"))
        fig_radar.update_layout(
            polar=dict(bgcolor=PLOT_BG,
                radialaxis=dict(visible=True, range=[0,100], gridcolor=GRID_COL,
                    tickfont=dict(size=8, color=MUTED)),
                angularaxis=dict(gridcolor=GRID_COL, tickfont=dict(size=9, color=TEXT_COL))),
            paper_bgcolor=PAPER_BG, plot_bgcolor=PLOT_BG,
            font=dict(family="Space Mono", color=TEXT_COL),
            height=300, margin=dict(l=40,r=40,t=20,b=20),
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=9)))
        st.plotly_chart(fig_radar, use_container_width=True, config={"displayModeBar": False})

    with asset_col:
        st.markdown('<div class="section-label">Implicazioni Asset Class</div>', unsafe_allow_html=True)
        IMPL = {
            "GOLDILOCKS":         [("Equity",CYAN,"FAVOREVOLE","Utili crescita, multipli sani"),
                                   ("Bond",ORANGE,"NEUTRALE","Carry ok, duration non premiata"),
                                   ("Commodity",ORANGE,"SELETTIVO","Domanda buona, no spike"),
                                   ("Cash",RED,"SOTTOPESO","Opportunity cost alto")],
            "INFLATIONARY BOOM":  [("Equity",ORANGE,"SELETTIVO","Value/Energy over Growth"),
                                   ("Bond",RED,"NEGATIVO","Duration sotto pressione"),
                                   ("Commodity",CYAN,"OTTIMALE","Oil, metalli, soft commodity"),
                                   ("Cash",ORANGE,"NEUTRALE","Nominali alti, reali compressi")],
            "STAGFLATION":        [("Equity",RED,"NEGATIVO","Margini compressi, multipli giu"),
                                   ("Bond",RED,"NEGATIVO","Inflazione erode reale"),
                                   ("Commodity",CYAN,"PARZIALE","Energia e metalli preziosi"),
                                   ("Cash",CYAN,"RELATIVO","Tassi nominali elevati")],
            "DISINFLATIONARY BUST":[("Equity",ORANGE,"DIFENSIVO","Qualita e dividendi"),
                                    ("Bond",CYAN,"OTTIMALE","Duration lunga, flight to quality"),
                                    ("Commodity",RED,"NEGATIVO","Domanda debole"),
                                    ("Cash",ORANGE,"NEUTRALE","Rendimento reale positivo")],
        }
        impl = IMPL.get(regime_label, IMPL["GOLDILOCKS"])
        for asset, ac, status, desc in impl:
            rgb = tuple(int(ac.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
            st.markdown(f"""
            <div style="background:rgba({rgb[0]},{rgb[1]},{rgb[2]},0.07);
                        border:1px solid {ac};border-radius:4px;
                        padding:8px 12px;margin-bottom:5px;display:flex;align-items:center;gap:10px">
              <div style="font-size:0.58rem;letter-spacing:2px;color:{MUTED};min-width:60px">{asset.upper()}</div>
              <div style="font-family:Syne;font-size:0.75rem;font-weight:700;color:{ac};min-width:80px">{status}</div>
              <div style="font-size:0.58rem;color:#8ab0c8">{desc}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown('<div class="section-label">Serie Storica Composite · Percentile Expanding · Alert Zona</div>',
        unsafe_allow_html=True)
    hist = build_historical_composite()

    if not hist.empty:
        persistence_val = round(float(hist["Composite"].rolling(6).std().iloc[-1]), 1) if len(hist) >= 6 else None
        h = fbd(hist, cutoff_date(max(years_display, 5))).copy()
        fig_h = go.Figure()
        fig_h.add_hrect(y0=60, y1=100, fillcolor="rgba(0,245,196,0.04)", line_width=0,
            annotation_text="BULL", annotation_position="top right",
            annotation_font=dict(color=CYAN, size=8))
        fig_h.add_hrect(y0=0, y1=40, fillcolor="rgba(255,77,109,0.04)", line_width=0,
            annotation_text="BEAR", annotation_position="bottom right",
            annotation_font=dict(color=RED, size=8))
        fig_h.add_hline(y=60, line_dash="dot", line_color=CYAN, line_width=1)
        fig_h.add_hline(y=40, line_dash="dot", line_color=RED, line_width=1)
        fig_h.add_hline(y=50, line_dash="solid", line_color=GRID_COL, line_width=0.8)
        for col_name, col_hex in [("Monetario",BLUE),("Econ.Reale",CYAN),
                                   ("Fiscale",ORANGE),("Produttivo",PURPLE)]:
            if col_name in h.columns:
                fig_h.add_trace(go.Scatter(x=h.index, y=h[col_name], name=col_name,
                    line=dict(color=col_hex, width=0.8, dash="dot"), opacity=0.3))
        fig_h.add_trace(go.Scatter(x=h.index, y=h["Composite"], name="Composite",
            line=dict(color=TEXT_COL, width=2.5)))
        last_c = float(h["Composite"].iloc[-1])
        fig_h.add_trace(go.Scatter(x=[h.index[-1]], y=[last_c], mode="markers",
            marker=dict(size=12, color=score_color(last_c), line=dict(color="white", width=2)),
            showlegend=False))
        lh = base_layout("Composite Score Storico — Percentile Expanding da 2000", 340)
        lh["yaxis"] = dict(range=[0,100], gridcolor=GRID_COL, tickfont=dict(size=9, color=MUTED))
        lh["legend"] = dict(orientation="h", y=-0.22, x=0.5, xanchor="center",
            font=dict(size=9, color=TEXT_COL), bgcolor="rgba(0,0,0,0)")
        fig_h.update_layout(**lh)
        st.plotly_chart(fig_h, use_container_width=True, config={"displayModeBar": False})

        p_left, p_right = st.columns([1, 2])
        with p_left:
            if persistence_val is not None:
                pc = CYAN if persistence_val < 5 else (ORANGE if persistence_val < 10 else RED)
                pl = "STABILE" if persistence_val < 5 else ("TRANSIZIONE" if persistence_val < 10 else "VOLATILE")
                st.markdown(f"""
                <div style="background:{PAPER_BG};border:1px solid {pc};border-radius:4px;
                            padding:10px 14px;text-align:center">
                  <div style="font-size:0.55rem;letter-spacing:2px;color:{MUTED}">REGIME PERSISTENCE</div>
                  <div style="font-family:Syne;font-size:1.3rem;font-weight:700;color:{pc}">{pl}</div>
                  <div style="font-size:0.58rem;color:{MUTED}">std 6M = {persistence_val}</div>
                </div>""", unsafe_allow_html=True)

        with p_right:
            def _zone(s): return "BULL" if s >= 60 else ("BEAR" if s < 40 else "NEUTRAL")
            prev_z = _zone(float(h["Composite"].iloc[-2])) if len(h) >= 2 else _zone(composite)
            curr_z = _zone(composite)
            if prev_z != curr_z:
                ac = CYAN if curr_z == "BULL" else (ORANGE if curr_z == "NEUTRAL" else RED)
                icon = "📈" if curr_z == "BULL" else ("📉" if curr_z == "BEAR" else "⚠️")
                st.markdown(f"""
                <div style="background:rgba(0,0,0,0.3);border:2px solid {ac};
                            border-radius:4px;padding:10px 14px">
                  <div style="font-family:Syne;font-weight:800;color:{ac}">{icon} CAMBIO ZONA</div>
                  <div style="font-size:0.65rem;color:{TEXT_COL};margin-top:4px">
                    {prev_z} → <b style="color:{ac}">{curr_z}</b> ({composite:.0f}/100)
                  </div>
                </div>""", unsafe_allow_html=True)
            else:
                mc = CYAN if curr_z == "BULL" else (RED if curr_z == "BEAR" else ORANGE)
                months = sum(1 for v in reversed(h["Composite"].values) if _zone(v) == curr_z)
                st.markdown(f"""
                <div style="background:{PAPER_BG};border:1px solid {mc};border-radius:4px;
                            padding:10px 14px;display:flex;align-items:center;gap:12px">
                  <div style="font-family:Syne;font-size:1.3rem;font-weight:700;color:{mc}">{curr_z}</div>
                  <div style="font-size:0.6rem;color:{TEXT_COL}">Stabile · {months} periodi ·
                    Composite: {composite:.0f} · Breadth: {breadth:.0f}%</div>
                </div>""", unsafe_allow_html=True)
    else:
        st.info("Serie storica non disponibile.")

    if gpr_df is not None and not gpr_df.empty:
        st.markdown('<div class="section-label">GPR Index — Geopolitical Risk (sottopancia)</div>',
            unsafe_allow_html=True)
        gpr_col_use = "GPR" if gpr_df["GPR"].notna().sum() > 50 else "GPRH"
        gpr_plot = gpr_df.set_index("month")[gpr_col_use].dropna()
        gpr_cut  = gpr_plot[gpr_plot.index >= cutoff_date(max(years_display, 10))]
        fig_gpr_sub = go.Figure()
        fig_gpr_sub.add_hrect(y0=150, y1=gpr_plot.max()*1.1,
            fillcolor="rgba(255,77,109,0.06)", line_width=0)
        fig_gpr_sub.add_hline(y=100, line_dash="dot", line_color=MUTED, line_width=1,
            annotation_text="Media storica 100", annotation_position="right",
            annotation_font=dict(color=MUTED, size=8))
        fig_gpr_sub.add_trace(go.Scatter(x=gpr_cut.index, y=gpr_cut, name=gpr_col_use,
            line=dict(color=ORANGE, width=1.5),
            fill="tozeroy", fillcolor="rgba(245,166,35,0.06)"))
        for ym, label in GPR_EVENTS.items():
            try:
                ev_date = pd.Timestamp(ym + "-01")
                if ev_date >= gpr_cut.index.min() and ev_date <= gpr_cut.index.max():
                    fig_gpr_sub.add_vline(x=ev_date, line_dash="dot",
                        line_color=RED, line_width=0.8,
                        annotation_text=label, annotation_position="top",
                        annotation_font=dict(size=7, color=RED),
                        annotation_textangle=-90)
            except Exception:
                pass
        lg = base_layout(f"GPR Index ({gpr_col_use}) — eventi geopolitici rilevanti", 200)
        lg["yaxis"] = dict(gridcolor=GRID_COL, tickfont=dict(size=8, color=MUTED))
        lg["showlegend"] = False
        fig_gpr_sub.update_layout(**lg)
        st.plotly_chart(fig_gpr_sub, use_container_width=True, config={"displayModeBar": False})

    with st.expander("📋 Dettaglio Score — tutti gli indicatori", expanded=False):
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
                meta   = INDICATOR_META.get(iname, "C")
                meta_col = CYAN if meta == "L" else (ORANGE if meta == "C" else MUTED)
                rows_html += (
                    f'<tr><td style="padding:4px 8px;font-size:0.6rem;color:{pcol}">{pillar_name}</td>'
                    f'<td style="padding:4px 8px;font-size:0.6rem;color:{TEXT_COL}">{iname}</td>'
                    f'<td style="padding:4px 8px;font-size:0.58rem;color:{meta_col};font-weight:700">{meta}</td>'
                    f'<td style="padding:4px 8px;font-size:0.6rem;color:{TEXT_COL}">{idata["value"]} {idata["unit"]}</td>'
                    f'<td style="padding:4px 8px;font-size:0.6rem;color:{sc_col};font-weight:700">{sc:.0f}</td>'
                    f'<td style="padding:4px 8px;min-width:80px">'
                    f'<div style="background:#1c2a3a;border-radius:2px;height:4px">'
                    f'<div style="background:{sc_col};height:4px;width:{bar_w}%;border-radius:2px"></div></div></td>'
                    f'<td style="padding:4px 8px">{signal_pill(score_pill(sc))}</td></tr>'
                )
        st.markdown(
            f'<div style="font-size:0.55rem;color:{MUTED};margin-bottom:4px">L=Leading C=Coincident LAG=Lagging</div>'
            f'<div style="border:1px solid #1c2a3a;border-radius:4px;overflow:hidden">'
            f'<table style="width:100%;border-collapse:collapse;background:#080e14">'
            f'<thead><tr style="background:#0e1420">'
            f'<th style="padding:5px 8px;font-size:0.5rem;color:{MUTED}">PILASTRO</th>'
            f'<th style="padding:5px 8px;font-size:0.5rem;color:{MUTED}">INDICATORE</th>'
            f'<th style="padding:5px 8px;font-size:0.5rem;color:{MUTED}">TIPO</th>'
            f'<th style="padding:5px 8px;font-size:0.5rem;color:{MUTED}">VALORE</th>'
            f'<th style="padding:5px 8px;font-size:0.5rem;color:{MUTED}">SCORE</th>'
            f'<th style="padding:5px 8px;font-size:0.5rem;color:{MUTED}">LIVELLO</th>'
            f'<th style="padding:5px 8px;font-size:0.5rem;color:{MUTED}">SEGNALE</th>'
            f'</tr></thead><tbody>{rows_html}</tbody></table></div>',
            unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — MONETARIO
# ─────────────────────────────────────────────────────────────────────────────
with tab2:
    t2c1, t2c2 = st.columns([1, 2])
    with t2c1:
        st.markdown(tile_html("SCORE PILASTRO A", f"{sA:.0f}/100", "Monetario",
            score_cc(sA), score_pill(sA)), unsafe_allow_html=True)
        for iname, idata in indA.items():
            sc = idata.get("score")
            if sc is None:
                continue
            st.markdown(tile_html(iname.upper(),
                idata["value"] + " " + idata["unit"],
                "Score: " + str(round(sc)) + "/100 · " + idata["desc"],
                score_cc(sc), score_pill(sc)), unsafe_allow_html=True)

    with t2c2:
        cut = cutoff_date(years_display)

        # M2 Reale
        mr = m2_real(fred_data["M2"], fred_data["CPI"])
        if not mr.empty:
            mr_d = fbd(mr, cut)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=mr_d.index, y=mr_d,
                line=dict(color=BLUE, width=2), name="M2 Reale"))
            add_percentile_bands(fig, mr, invert=False)
            fig.update_layout(**base_layout("M2 Reale (CPI deflazionato)", 230))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        # Velocity — v1.4.2: GDP trimestrale → espanso mensile con ffill, poi ratio su M2 mensile
        try:
            _m2v  = fred_data["M2"].copy()
            _gdpv = fred_data["GDP"].copy()
            _m2v.index  = pd.to_datetime(_m2v.index).normalize()
            _gdpv.index = pd.to_datetime(_gdpv.index).normalize()
            # M2: mensile
            _m2v = _m2v.resample("MS").last()
            # GDP: trimestrale → espandi a mensile con ffill
            _gdpv = _gdpv.resample("MS").last().reindex(_m2v.index).ffill().bfill()
            # Calcola ratio solo dove entrambi hanno valori
            _common = _m2v.index.intersection(_gdpv.dropna().index)
            if len(_common) > 4:
                _vel = (_gdpv.loc[_common] / _m2v.loc[_common]).dropna()
                _cutoff_v = pd.Timestamp.now() - pd.DateOffset(years=years_display)
                _vel_d = _vel[_vel.index >= _cutoff_v]
                if len(_vel_d) > 2:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=list(_vel_d.index.strftime("%Y-%m-%d")),
                        y=list(_vel_d.values.astype(float)),
                        line=dict(color=PURPLE, width=2), name="Velocity"))
                    add_percentile_bands(fig, _vel, invert=False)
                    fig.update_layout(**base_layout("Velocity — GDP/M2", 220))
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        except Exception as _e:
            st.caption(f"Velocity errore: {_e}")

        # Real Yield
        ry = fred_data["REALYIELD"]
        if not ry.empty:
            ry_d = fbd(ry, cut)
            fig = go.Figure()
            fig.add_hline(y=0, line_dash="solid", line_color=GRID_COL, line_width=1)
            fig.add_trace(go.Scatter(x=ry_d.index, y=ry_d,
                line=dict(color=ORANGE, width=2), fill="tozeroy",
                fillcolor="rgba(245,166,35,0.07)", name="Real Yield"))
            add_percentile_bands(fig, ry, invert=True)
            fig.update_layout(**base_layout("Real Yield 10Y — TIPS (%)", 230))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        # HY OAS
        hy = fred_data["HY_OAS"]
        if not hy.empty:
            hy_bp = hy * 100
            hy_d  = fbd(hy_bp, cut)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=hy_d.index, y=hy_d,
                line=dict(color=RED, width=2), fill="tozeroy",
                fillcolor="rgba(255,77,109,0.07)", name="HY OAS (bp)"))
            add_percentile_bands(fig, hy_bp, invert=True)
            fig.update_layout(**base_layout("HY OAS Spread (bp)  —  FIX v1.4: BAMLH0A0HYM2 × 100", 230))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        # STLFSI
        stlfsi = fred_data["STLFSI"]
        if not stlfsi.empty:
            st_d = fbd(stlfsi, cut)
            fig = go.Figure()
            fig.add_hrect(y0=-4, y1=0, fillcolor="rgba(0,245,196,0.04)", line_width=0)
            fig.add_hrect(y0=0,  y1=6, fillcolor="rgba(255,77,109,0.04)", line_width=0)
            fig.add_hline(y=0, line_dash="solid", line_color=ORANGE, line_width=1.5,
                annotation_text="Neutro", annotation_font=dict(color=ORANGE, size=9))
            fig.add_trace(go.Scatter(x=st_d.index, y=st_d,
                line=dict(color=MAGENTA, width=2), fill="tozeroy",
                fillcolor="rgba(255,43,212,0.07)", name="STLFSI"))
            fig.update_layout(**base_layout(
                "St. Louis Financial Stress Index (STLFSI)  neg = nessuno stress  pos = stress elevato", 220))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        # MOVE INDEX
        move = mkt_data.get("MOVE")
        if move is not None and not move.empty:
            move_d = fbd(move, cut)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=move_d.index, y=move_d,
                line=dict(color=PURPLE, width=2), fill="tozeroy",
                fillcolor="rgba(187,136,255,0.07)", name="MOVE"))
            add_percentile_bands(fig, move, invert=True)
            fig.update_layout(**base_layout(
                "MOVE Index — Bond Vol implicita Treasury (v1.4.1: da Geo → Monetario)", 230))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        # M2/PIL — v1.4.2: GDP trimestrale → espanso mensile con ffill, poi ratio su M2 mensile
        try:
            _m2r  = fred_data["M2"].copy()
            _gdpr = fred_data["GDP"].copy()
            _m2r.index  = pd.to_datetime(_m2r.index).normalize()
            _gdpr.index = pd.to_datetime(_gdpr.index).normalize()
            _m2r  = _m2r.resample("MS").last()
            _gdpr = _gdpr.resample("MS").last().reindex(_m2r.index).ffill().bfill()
            _common_r = _m2r.index.intersection(_gdpr.dropna().index)
            if len(_common_r) > 4:
                _ratio = (_m2r.loc[_common_r] / _gdpr.loc[_common_r]).dropna()
                _cutoff_r = pd.Timestamp.now() - pd.DateOffset(years=years_display)
                _ratio_d = _ratio[_ratio.index >= _cutoff_r]
                if len(_ratio_d) > 2:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=list(_ratio_d.index.strftime("%Y-%m-%d")),
                        y=list(_ratio_d.values.astype(float)),
                        line=dict(color=CYAN, width=2), name="M2/PIL"))
                    add_percentile_bands(fig, _ratio, invert=False)  # alto M2/PIL = bull
                    fig.update_layout(**base_layout("M2/PIL Ratio", 220))
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        except Exception as _e:
            st.caption(f"M2/PIL errore: {_e}")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — ECONOMIA REALE
# ─────────────────────────────────────────────────────────────────────────────
with tab3:
    t3c1, t3c2 = st.columns([1, 2])
    with t3c1:
        st.markdown(tile_html("SCORE PILASTRO B", f"{sB:.0f}/100", "Economia Reale",
            score_cc(sB), score_pill(sB)), unsafe_allow_html=True)

        pmi_val = indB.get("PMI Composito", {}).get("value", "N/A")
        try:
            pv = float(pmi_val)
            if pv >= 52:   pmi_col, pmi_status = CYAN,   "ESPANSIONE"
            elif pv >= 50: pmi_col, pmi_status = LIME,   "NEUTRO+"
            elif pv >= 48: pmi_col, pmi_status = ORANGE, "NEUTRO-"
            else:          pmi_col, pmi_status = RED,    "CONTRAZIONE"
            pmi_display = f"{pv:.1f}"
        except Exception:
            pmi_col, pmi_status, pmi_display = MUTED, "N/A", "N/A"

        st.markdown(f"""
        <div class="metric-tile" style="text-align:center;padding:20px 12px;border-color:{pmi_col}">
          <div class="metric-label">PMI COMPOSITO — {pmi_src.upper()}</div>
          <div style="font-family:Syne;font-size:3.2rem;font-weight:800;
               color:{pmi_col};line-height:1;margin:10px 0">{pmi_display}</div>
          <div style="font-family:Syne;font-size:0.75rem;font-weight:700;
               color:{pmi_col};letter-spacing:3px">{pmi_status}</div>
          <div style="margin-top:8px;font-size:0.55rem;color:{MUTED}">
            &gt;52 espansione · &lt;48 contrazione · 50 = neutro
          </div>
        </div>""", unsafe_allow_html=True)

        for iname, idata in indB.items():
            if iname == "PMI Composito": continue
            sc = idata.get("score")
            if sc is None: continue
            st.markdown(tile_html(iname.upper(),
                idata["value"] + " " + idata["unit"],
                "Score: " + str(round(sc)) + "/100 · " + idata["desc"],
                score_cc(sc), score_pill(sc)), unsafe_allow_html=True)

    with t3c2:
        cut = cutoff_date(years_display)

        if not fred_data["INDPRO"].empty:
            ip_yoy = yoy(fred_data["INDPRO"])
            ip_d   = fbd(ip_yoy, cut)
            fig = go.Figure()
            fig.add_hline(y=0, line_dash="solid", line_color=GRID_COL, line_width=1)
            fig.add_trace(go.Scatter(x=ip_d.index, y=ip_d,
                line=dict(color=CYAN, width=2), fill="tozeroy",
                fillcolor="rgba(0,245,196,0.07)", name="INDPRO YoY"))
            add_percentile_bands(fig, ip_yoy, invert=False)
            fig.update_layout(**base_layout("Produzione Industriale YoY (%)", 230))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        col_u, col_n = st.columns(2)
        with col_u:
            if not fred_data["UNRATE"].empty:
                ur_d = fbd(fred_data["UNRATE"], cut)
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=ur_d.index, y=ur_d,
                    line=dict(color=ORANGE, width=2), name="UNRATE"))
                add_percentile_bands(fig, fred_data["UNRATE"], invert=True)
                fig.update_layout(**base_layout("Disoccupazione (%)", 220))
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        with col_n:
            if not fred_data["PAYEMS"].empty:
                nfp3 = fred_data["PAYEMS"].diff(3) / 1000
                nfp_d = fbd(nfp3, cut)
                fig = go.Figure()
                fig.add_hline(y=0, line_dash="solid", line_color=GRID_COL, line_width=1)
                fig.add_trace(go.Scatter(x=nfp_d.index, y=nfp_d,
                    line=dict(color=LIME, width=2), fill="tozeroy",
                    fillcolor="rgba(198,255,26,0.07)", name="NFP D3M (K)"))
                fig.update_layout(**base_layout("NFP variazione 3M (K)", 220))
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        if not fred_data["PCE"].empty:
            pce_yoy = yoy(fred_data["PCE"])
            pce_d   = fbd(pce_yoy, cut)
            fig = go.Figure()
            fig.add_hline(y=2.0, line_dash="dot", line_color=CYAN, line_width=1.5,
                annotation_text="Target 2%", annotation_font=dict(color=CYAN, size=9))
            fig.add_trace(go.Scatter(x=pce_d.index, y=pce_d,
                line=dict(color=RED, width=2), fill="tozeroy",
                fillcolor="rgba(255,77,109,0.07)", name="Core PCE YoY"))
            fig.update_layout(**base_layout("Core PCE YoY (%) — ottimale vicino 2%", 230))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        if not fred_data["RETAIL"].empty:
            ret_yoy = yoy(fred_data["RETAIL"])
            ret_d   = fbd(ret_yoy, cut)
            fig = go.Figure()
            fig.add_hline(y=0, line_dash="solid", line_color=GRID_COL, line_width=1)
            fig.add_trace(go.Scatter(x=ret_d.index, y=ret_d,
                line=dict(color=BLUE, width=2), fill="tozeroy",
                fillcolor="rgba(77,166,255,0.07)", name="Retail YoY"))
            fig.update_layout(**base_layout("Retail Sales YoY (%)", 220))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — FISCALE + PRODUTTIVO
# ─────────────────────────────────────────────────────────────────────────────
with tab4:
    st.markdown('<div class="section-label">C · Pilastro Fiscale</div>', unsafe_allow_html=True)
    fc1, fc2 = st.columns([1, 2])
    with fc1:
        st.markdown(tile_html("SCORE PILASTRO C", f"{sC:.0f}/100", "Fiscale",
            score_cc(sC), score_pill(sC)), unsafe_allow_html=True)
        for iname, idata in indC.items():
            sc = idata.get("score")
            if sc is None: continue
            st.markdown(tile_html(iname.upper(),
                idata["value"] + " " + idata["unit"],
                "Score: " + str(round(sc)) + "/100 · " + idata["desc"],
                score_cc(sc), score_pill(sc)), unsafe_allow_html=True)
    with fc2:
        cut = cutoff_date(years_display)
        if not fred_data["DEFICIT"].empty:
            def_d = fbd(fred_data["DEFICIT"], cut)
            fig = go.Figure()
            fig.add_hline(y=0, line_dash="solid", line_color=GRID_COL, line_width=1)
            fig.add_trace(go.Scatter(x=def_d.index, y=def_d,
                line=dict(color=ORANGE, width=2), fill="tozeroy",
                fillcolor="rgba(245,166,35,0.07)", name="Deficit/PIL"))
            fig.update_layout(**base_layout("Deficit Federale / PIL (%)", 240))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        if not fred_data["DEBT_GDP"].empty:
            debt_d = fbd(fred_data["DEBT_GDP"], cut)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=debt_d.index, y=debt_d,
                line=dict(color=RED, width=2), fill="tozeroy",
                fillcolor="rgba(255,77,109,0.07)", name="Debito/PIL"))
            fig.update_layout(**base_layout("Debito Federale / PIL (%)", 230))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.markdown('<div class="section-label">D · Pilastro Produttivo</div>', unsafe_allow_html=True)
    dc1, dc2 = st.columns([1, 2])
    with dc1:
        st.markdown(tile_html("SCORE PILASTRO D", f"{sD:.0f}/100", "Produttivo",
            score_cc(sD), score_pill(sD)), unsafe_allow_html=True)
        for iname, idata in indD.items():
            sc = idata.get("score")
            if sc is None: continue
            st.markdown(tile_html(iname.upper(),
                idata["value"] + " " + idata["unit"],
                "Score: " + str(round(sc)) + "/100 · " + idata["desc"],
                score_cc(sc), score_pill(sc)), unsafe_allow_html=True)
    with dc2:
        cut = cutoff_date(years_display)
        if not fred_data["TCU"].empty:
            tcu_d = fbd(fred_data["TCU"], cut)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=tcu_d.index, y=tcu_d,
                line=dict(color=BLUE, width=2), fill="tozeroy",
                fillcolor="rgba(77,166,255,0.07)", name="TCU"))
            add_percentile_bands(fig, fred_data["TCU"], invert=False)
            fig.update_layout(**base_layout("Capacity Utilization (%) — con bande 25p/75p", 240))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        if not fred_data["ULC"].empty:
            ulc_yoy = yoy(fred_data["ULC"], 4).resample("Q").last()
            ulc_d   = fbd(ulc_yoy, cut)
            fig = go.Figure()
            fig.add_hline(y=0, line_dash="solid", line_color=GRID_COL, line_width=1)
            fig.add_trace(go.Scatter(x=ulc_d.index, y=ulc_d,
                line=dict(color=ORANGE, width=2), fill="tozeroy",
                fillcolor="rgba(245,166,35,0.07)", name="ULC YoY"))
            fig.update_layout(**base_layout("Unit Labor Costs YoY (%)", 220))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        if not fred_data["PRODUC"].empty:
            prod_yoy = yoy(fred_data["PRODUC"], 4).resample("Q").last()
            prod_d   = fbd(prod_yoy, cut)
            fig = go.Figure()
            fig.add_hline(y=0, line_dash="solid", line_color=GRID_COL, line_width=1)
            fig.add_trace(go.Scatter(x=prod_d.index, y=prod_d,
                line=dict(color=PURPLE, width=2), fill="tozeroy",
                fillcolor="rgba(187,136,255,0.07)", name="Produttivita YoY"))
            fig.update_layout(**base_layout("Produttivita YoY (%) — output per ora", 220))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ─────────────────────────────────────────────────────────────────────────────
# TAB 5 — GEOPOLITICO
# ─────────────────────────────────────────────────────────────────────────────
with tab5:
    t5c1, t5c2 = st.columns([1, 2])
    with t5c1:
        st.markdown(tile_html("SCORE PILASTRO E", f"{sE:.0f}/100", "Geopolitico",
            score_cc(sE), score_pill(sE)), unsafe_allow_html=True)
        for iname, idata in indE.items():
            sc = idata.get("score")
            if sc is None: continue
            st.markdown(tile_html(iname.upper(),
                idata["value"] + " " + idata["unit"],
                "Score: " + str(round(sc)) + "/100 · " + idata["desc"],
                score_cc(sc), score_pill(sc)), unsafe_allow_html=True)
        st.markdown(
            f'<div style="font-size:0.55rem;color:{MUTED};border:1px solid {GRID_COL};'
            f'border-radius:4px;padding:8px 10px;margin-top:8px;line-height:1.6">'
            f'<b style="color:{ORANGE}">v1.4.1</b> MOVE Index spostato nel<br>'
            f'Pilastro A Monetario — misura<br>volatilità tassi, non rischio geo.</div>',
            unsafe_allow_html=True)

    with t5c2:
        cut = cutoff_date(years_display)

        if gpr_df is not None and not gpr_df.empty:
            gpr_series  = gpr_df.set_index("month")["GPRH"].dropna()
            gpr_threats = gpr_df.set_index("month")["GPRHT"].dropna() if "GPRHT" in gpr_df.columns else pd.Series(dtype=float)
            gpr_acts    = gpr_df.set_index("month")["GPRHA"].dropna() if "GPRHA" in gpr_df.columns else pd.Series(dtype=float)
            gpr_recent  = gpr_df.set_index("month")["GPR"].dropna()   if "GPR"  in gpr_df.columns else pd.Series(dtype=float)

            last_gpr  = float(gpr_series.iloc[-1])
            last_date = gpr_series.index[-1].strftime("%b %Y")
            gpr_pct   = float((gpr_series < last_gpr).mean() * 100)
            gpr_ma12  = gpr_series.rolling(12).mean()
            gpr_col_v = RED if last_gpr > 150 else (ORANGE if last_gpr > 100 else CYAN)

            # ── KPI bar ──────────────────────────────────────────────────────
            st.markdown(f"""
            <div style="background:{PAPER_BG};border:1px solid {gpr_col_v};border-radius:4px;
                        padding:8px 16px;display:flex;align-items:center;gap:28px;margin-bottom:8px">
              <div>
                <div style="font-size:0.52rem;letter-spacing:2px;color:{MUTED}">GPRH ULTIMO ({last_date})</div>
                <div style="font-family:Syne;font-size:1.6rem;font-weight:700;color:{gpr_col_v}">{last_gpr:.1f}</div>
              </div>
              <div style="font-size:0.6rem;color:{TEXT_COL};line-height:1.9">
                Percentile storico (1900–oggi): <b style="color:{gpr_col_v}">{gpr_pct:.0f}°</b><br>
                Media storica: <b>100</b> &nbsp;·&nbsp; Soglia stress: <b>150</b><br>
                Media mobile 12m: <b style="color:{ORANGE}">{gpr_ma12.iloc[-1]:.1f}</b><br>
                Fonte: Caldara &amp; Iacoviello (2022) · <a href="https://www.matteoiacoviello.com/gpr.htm"
                style="color:{CYAN}">matteoiacoviello.com/gpr.htm</a>
              </div>
            </div>""", unsafe_allow_html=True)

            # ── VISTA PANORAMICA 1900–OGGI ───────────────────────────────────
            st.markdown('<div class="section-label">GPR Index — Panoramica storica 1900–oggi</div>',
                unsafe_allow_html=True)

            fig_full = go.Figure()
            fig_full.add_trace(go.Scatter(
                x=gpr_series.index, y=gpr_series,
                name="GPRH", line=dict(color=CYAN, width=1.2),
                fill="tozeroy", fillcolor="rgba(0,245,196,0.04)"))
            fig_full.add_trace(go.Scatter(
                x=gpr_ma12.index, y=gpr_ma12,
                name="MA 12m", line=dict(color=ORANGE, width=1.5, dash="dot")))
            fig_full.add_hline(y=100, line_dash="dot", line_color=MUTED, line_width=1,
                annotation_text="Media 100", annotation_position="right",
                annotation_font=dict(color=MUTED, size=8))
            fig_full.add_hline(y=150, line_dash="dot", line_color=RED, line_width=1,
                annotation_text="Stress 150", annotation_position="right",
                annotation_font=dict(color=RED, size=8))

            # Raggruppa eventi vicini per evitare label sovrapposti (min 18 mesi distanza)
            ev_sorted = sorted(GPR_EVENTS.items())
            ev_plotted = []
            for ym, label in ev_sorted:
                try:
                    ev_date = pd.Timestamp(ym + "-01")
                    if ev_date < gpr_series.index.min() or ev_date > gpr_series.index.max():
                        continue
                    # Salta se troppo vicino all'ultimo evento plottato
                    if ev_plotted and abs((ev_date - ev_plotted[-1]).days) < 540:
                        continue
                    y_val = float(gpr_series.asof(ev_date)) if ev_date in gpr_series.index or True else 100
                    fig_full.add_vline(x=ev_date, line_dash="dot",
                        line_color="rgba(255,77,109,0.35)", line_width=1)
                    fig_full.add_annotation(
                        x=ev_date, y=gpr_series.max() * 0.97,
                        text=label, showarrow=False,
                        font=dict(size=6, color=RED),
                        textangle=-90, xanchor="left")
                    ev_plotted.append(ev_date)
                except Exception:
                    pass

            fig_full.update_layout(
                height=320, paper_bgcolor=PAPER_BG, plot_bgcolor=PLOT_BG,
                font=dict(family="Space Mono", color=TEXT_COL, size=9),
                margin=dict(l=52, r=90, t=20, b=30),
                hovermode="x unified",
                legend=dict(orientation="h", y=-0.12, x=0.5, xanchor="center",
                    font=dict(size=8, color=TEXT_COL), bgcolor="rgba(0,0,0,0)"),
                xaxis=dict(gridcolor=GRID_COL, tickfont=dict(size=8, color=MUTED)),
                yaxis=dict(gridcolor=GRID_COL, tickfont=dict(size=8, color=MUTED),
                    title=dict(text="GPRH", font=dict(size=8, color=MUTED))),
            )
            st.plotly_chart(fig_full, use_container_width=True, config={"displayModeBar": False})

            # ── VISTA RECENTE con Threats / Acts subplot ─────────────────────
            st.markdown('<div class="section-label">GPR Index — Dettaglio recente (finestra selezionata)</div>',
                unsafe_allow_html=True)

            fig_gpr = make_subplots(rows=2, cols=1, row_heights=[0.65, 0.35],
                shared_xaxes=True, vertical_spacing=0.04)

            cut_gpr = cutoff_date(max(years_display, 5))
            gpr_h_cut = fbd(gpr_series, cut_gpr)
            ma12_cut  = fbd(gpr_ma12,   cut_gpr)

            if not gpr_threats.empty:
                fig_gpr.add_trace(go.Scatter(
                    x=fbd(gpr_threats, cut_gpr).index,
                    y=fbd(gpr_threats, cut_gpr).values,
                    name="Threats", line=dict(color=ORANGE, width=1, dash="dot"), opacity=0.7),
                    row=1, col=1)
            if not gpr_acts.empty:
                fig_gpr.add_trace(go.Scatter(
                    x=fbd(gpr_acts, cut_gpr).index,
                    y=fbd(gpr_acts, cut_gpr).values,
                    name="Acts", line=dict(color=RED, width=1, dash="dot"), opacity=0.7),
                    row=1, col=1)

            fig_gpr.add_trace(go.Scatter(
                x=gpr_h_cut.index, y=gpr_h_cut,
                name="GPRH", line=dict(color=CYAN, width=2),
                fill="tozeroy", fillcolor="rgba(0,245,196,0.05)"), row=1, col=1)
            fig_gpr.add_trace(go.Scatter(
                x=ma12_cut.index, y=ma12_cut,
                name="MA 12m", line=dict(color=ORANGE, width=1.5, dash="dot")), row=1, col=1)
            fig_gpr.add_hline(y=100, line_dash="dot", line_color=MUTED, line_width=1,
                row=1, col=1, annotation_text="100", annotation_position="right",
                annotation_font=dict(color=MUTED, size=8))
            fig_gpr.add_hline(y=150, line_dash="dot", line_color=RED, line_width=1,
                row=1, col=1, annotation_text="150", annotation_position="right",
                annotation_font=dict(color=RED, size=8))

            # Marker eventi nella finestra recente
            ev_added = []
            for ym, label in GPR_EVENTS.items():
                try:
                    ev_date = pd.Timestamp(ym + "-01")
                    if ev_date >= gpr_h_cut.index.min() and ev_date <= gpr_h_cut.index.max():
                        if label not in ev_added:
                            fig_gpr.add_vline(x=ev_date, line_dash="dot",
                                line_color="rgba(255,77,109,0.5)", line_width=1, row=1, col=1)
                            fig_gpr.add_annotation(x=ev_date, y=gpr_h_cut.max() * 0.97,
                                text=label, showarrow=False,
                                font=dict(size=6.5, color=RED),
                                textangle=-90, xanchor="left", row=1, col=1)
                            ev_added.append(label)
                except Exception:
                    pass

            # Subplot inferiore: GPR recente (bar)
            if not gpr_recent.empty:
                gpr_r_cut = fbd(gpr_recent, cut_gpr)
                if not gpr_r_cut.empty:
                    fig_gpr.add_trace(go.Bar(
                        x=gpr_r_cut.index, y=gpr_r_cut,
                        name="GPR recente", marker_color=MAGENTA, opacity=0.5), row=2, col=1)
                    fig_gpr.add_hline(y=100, line_dash="dot", line_color=MUTED,
                        line_width=1, row=2, col=1)

            fig_gpr.update_layout(
                height=400, paper_bgcolor=PAPER_BG, plot_bgcolor=PLOT_BG,
                font=dict(family="Space Mono", color=TEXT_COL, size=9),
                margin=dict(l=52, r=90, t=20, b=30),
                hovermode="x unified",
                legend=dict(orientation="h", y=-0.1, x=0.5, xanchor="center",
                    font=dict(size=8, color=TEXT_COL), bgcolor="rgba(0,0,0,0)"),
                xaxis=dict(gridcolor=GRID_COL, tickfont=dict(size=8, color=MUTED)),
                xaxis2=dict(gridcolor=GRID_COL, tickfont=dict(size=8, color=MUTED)),
                yaxis=dict(gridcolor=GRID_COL, tickfont=dict(size=8, color=MUTED),
                    title=dict(text="GPRH", font=dict(size=8, color=MUTED))),
                yaxis2=dict(gridcolor=GRID_COL, tickfont=dict(size=8, color=MUTED),
                    title=dict(text="GPR", font=dict(size=8, color=MUTED))),
            )
            st.plotly_chart(fig_gpr, use_container_width=True, config={"displayModeBar": False})

            # ── CORRELAZIONI GPR ─────────────────────────────────────────────
            corr_items = []
            for asset_name, asset_key, asset_src in [
                ("Gold", "GOLD", "mkt"), ("Oil WTI", "OIL", "mkt"),
                ("EEM", "EEM", "mkt"), ("HY OAS", "HY_OAS", "fred"),
            ]:
                try:
                    s = (mkt_data.get(asset_key) if asset_src == "mkt" else fred_data.get(asset_key))
                    if s is None or s.empty: continue
                    s.index = pd.to_datetime(s.index).normalize()
                    s_m = s.resample("MS").last()
                    gpr_m = gpr_series.resample("MS").last()
                    combined = pd.concat([gpr_m, s_m], axis=1).dropna()
                    if len(combined) > 24:
                        r = combined.iloc[:,0].corr(combined.iloc[:,1])
                        corr_items.append((asset_name, r))
                except Exception:
                    pass

            if corr_items:
                st.markdown('<div class="section-label">Correlazione GPRH vs Asset (mensile, full history)</div>',
                    unsafe_allow_html=True)
                cols_corr = st.columns(len(corr_items))
                for i, (aname, r) in enumerate(corr_items):
                    col_r = RED if r > 0.3 else (CYAN if r < -0.3 else MUTED)
                    with cols_corr[i]:
                        st.markdown(f"""<div style="background:{PAPER_BG};border:1px solid {col_r};
                            border-radius:4px;padding:6px 10px;text-align:center">
                            <div style="font-size:0.5rem;color:{MUTED};letter-spacing:1px">{aname}</div>
                            <div style="font-family:Syne;font-size:1.1rem;font-weight:700;color:{col_r}">{r:+.2f}</div>
                            </div>""", unsafe_allow_html=True)

        else:
            st.info("GPR Index non disponibile. Carica il CSV dalla sidebar per abilitare il grafico.")


        gold = mkt_data.get("GOLD")
        if gold is not None and not gold.empty:
            gold_d = fbd(gold, cut)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=gold_d.index, y=gold_d,
                line=dict(color=GOLD_COL, width=2.5), name="Gold (USD)"))
            fig.update_layout(**base_layout("Gold USD/oz", 230))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        col_oi, col_eem = st.columns(2)
        with col_oi:
            oil = mkt_data.get("OIL")
            if oil is not None and not oil.empty:
                oil_d = fbd(oil, cut)
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=oil_d.index, y=oil_d,
                    line=dict(color=ORANGE, width=2), fill="tozeroy",
                    fillcolor="rgba(245,166,35,0.07)", name="WTI"))
                add_percentile_bands(fig, oil, invert=True)
                fig.update_layout(**base_layout("Oil WTI (USD/bbl)", 230))
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        with col_eem:
            eem = mkt_data.get("EEM")
            if eem is not None and not eem.empty:
                eem_d = fbd(eem, cut)
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=eem_d.index, y=eem_d,
                    line=dict(color=CYAN, width=2), name="EEM"))
                fig.update_layout(**base_layout("EEM — Emerging Markets ETF", 230))
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        dxy = mkt_data.get("DXY")
        if dxy is not None and not dxy.empty:
            dxy_d = fbd(dxy, cut)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=dxy_d.index, y=dxy_d,
                line=dict(color=BLUE, width=2), name="DXY"))
            add_percentile_bands(fig, dxy, invert=True)
            fig.update_layout(**base_layout("Dollar Index (DXY) — lookback 30Y", 220))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ─────────────────────────────────────────────────────────────────────────────
# TAB 6 — BACKTEST PER REGIME
# ─────────────────────────────────────────────────────────────────────────────
with tab6:
    st.markdown('<div class="section-label">Rendimenti Medi per Regime Macro — SPY · TLT · GLD · GSG</div>',
        unsafe_allow_html=True)
    st.markdown(f"""
    <div style="font-size:0.62rem;color:{MUTED};margin-bottom:14px;line-height:1.8">
      Backtesting semplice: per ogni mese storico dal 2000 viene classificato il regime macro
      usando la serie storica del Composite Score (percentile expanding).
      Si calcolano i rendimenti mensili medi e la hit rate (% mesi positivi) per ciascun asset.
      <b style="color:{ORANGE}">Non e un sistema di trading. Rendimenti passati non garantiscono futuri.</b>
    </div>""", unsafe_allow_html=True)

    with st.spinner("Calcolo backtest per regime..."):
        hist_df_bt = build_historical_composite()
        bt = build_regime_backtest(hist_df_bt) if not hist_df_bt.empty else None

    if bt:
        REGIME_COLS = {"GOLDILOCKS": CYAN, "INFL.BOOM": ORANGE,
                       "STAGFLATION": RED, "DISINFL.BUST": BLUE}
        ASSETS = ["SPY", "TLT", "GLD", "GSG"]
        ASSET_NAMES = {"SPY": "Equity (SPY)", "TLT": "Bond LT (TLT)",
                       "GLD": "Gold (GLD)",   "GSG": "Commodity (GSG)"}

        cols = st.columns(4)
        for i, (regime, rc) in enumerate(REGIME_COLS.items()):
            with cols[i]:
                row = bt.get(regime, {})
                n   = row.get("n_months", 0)
                st.markdown(f"""
                <div style="background:{PAPER_BG};border:2px solid {rc};border-radius:6px;
                            padding:12px;margin-bottom:12px">
                  <div style="font-family:Syne;font-size:0.75rem;font-weight:800;color:{rc}">{regime}</div>
                  <div style="font-size:0.55rem;color:{MUTED};margin-bottom:8px">{n} mesi storici</div>
                  {"".join([
                    f'<div style="display:flex;justify-content:space-between;border-bottom:1px solid {GRID_COL};padding:3px 0">'
                    f'<span style="font-size:0.58rem;color:{MUTED}">{ASSET_NAMES[a]}</span>'
                    f'<span style="font-size:0.62rem;color:{"#00f5c4" if row.get(a+"_avg",0)>0 else "#ff4d6d"};font-weight:700">'
                    f'{row.get(a+"_avg","N/A"):+.2f}% / {row.get(a+"_hit","N/A"):.0f}% hit</span></div>'
                    for a in ASSETS if row.get(a+"_avg") is not None
                  ])}
                </div>""", unsafe_allow_html=True)

        st.markdown('<div class="section-label">Heatmap Rendimenti Medi Mensili per Regime</div>',
            unsafe_allow_html=True)
        heat_data, heat_labels = [], []
        for regime in REGIME_COLS:
            row = bt.get(regime, {})
            heat_data.append([row.get(a + "_avg", 0) for a in ASSETS])
            heat_labels.append(regime)

        fig_heat = go.Figure(data=go.Heatmap(
            z=heat_data, x=[ASSET_NAMES[a] for a in ASSETS], y=heat_labels,
            colorscale=[[0,"#ff4d6d"],[0.5,"#1c2a3a"],[1,"#00f5c4"]],
            zmid=0,
            text=[[f"{v:+.2f}%" for v in row] for row in heat_data],
            texttemplate="%{text}", textfont=dict(size=11, family="Syne"),
            showscale=True,
        ))
        lheat = base_layout("Rendimento Medio Mensile (%) per Regime", 300)
        lheat["xaxis"] = dict(tickfont=dict(size=10, color=TEXT_COL))
        lheat["yaxis"] = dict(tickfont=dict(size=10, color=TEXT_COL))
        fig_heat.update_layout(**lheat)
        st.plotly_chart(fig_heat, use_container_width=True, config={"displayModeBar": False})

        reg_ser = bt.get("_regime_series")
        if reg_ser is not None:
            st.markdown('<div class="section-label">Distribuzione Regime nel Tempo</div>',
                unsafe_allow_html=True)
            reg_cut = fbd(reg_ser, cutoff_date(max(years_display, 10)))
            regime_num = reg_cut.map({"GOLDILOCKS": 3, "INFL.BOOM": 2,
                                      "STAGFLATION": 1, "DISINFL.BUST": 0})
            fig_rt = go.Figure()
            for reg_name, rval, rc in [("GOLDILOCKS",3,CYAN),("INFL.BOOM",2,ORANGE),
                                        ("STAGFLATION",1,RED),("DISINFL.BUST",0,BLUE)]:
                mask = regime_num == rval
                fig_rt.add_trace(go.Bar(x=regime_num[mask].index, y=[1]*mask.sum(),
                    marker_color=rc, name=reg_name, opacity=0.7))
            lrt = base_layout("Regime Storico (barre mensili)", 200)
            lrt["barmode"] = "stack"
            lrt["yaxis"] = dict(visible=False)
            lrt["legend"] = dict(orientation="h", y=-0.3, x=0.5, xanchor="center",
                font=dict(size=9, color=TEXT_COL), bgcolor="rgba(0,0,0,0)")
            fig_rt.update_layout(**lrt)
            st.plotly_chart(fig_rt, use_container_width=True, config={"displayModeBar": False})

        st.markdown(f"""
        <div style="background:{PAPER_BG};border:1px solid {regime_color};border-radius:4px;
                    padding:12px 18px;margin-top:8px">
          <div style="font-size:0.55rem;letter-spacing:2px;color:{MUTED}">REGIME CORRENTE</div>
          <div style="font-family:Syne;font-size:1.2rem;font-weight:800;color:{regime_color}">{regime_label}</div>
          <div style="font-size:0.62rem;color:{TEXT_COL};margin-top:4px">
            Sulla base del backtest storico, in questo regime il posizionamento
            storicamente piu efficace e stato quello indicato nella tabella sopra.
          </div>
        </div>""", unsafe_allow_html=True)
    else:
        st.info("Dati backtest non disponibili. Controlla connessione FRED / yfinance.")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 7 — METODOLOGIA
# ─────────────────────────────────────────────────────────────────────────────
with tab7:
    st.markdown('<div class="section-label">Macro Core Engine v1.4.2 — Note Metodologiche</div>',
        unsafe_allow_html=True)

    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.markdown(f"""
        <div class="metric-tile" style="margin-bottom:12px">
          <div class="metric-label">SCORING — PERCENTILE EXPANDING</div>
          <div style="font-size:0.65rem;color:{TEXT_COL};line-height:1.8;margin-top:8px">
            Ogni indicatore viene trasformato in un percentile da 0 a 100 usando
            l'intera distribuzione storica disponibile dal 2000 (expanding window).<br><br>
            <b style="color:{CYAN}">Percentile 0</b> = valore ai minimi storici<br>
            <b style="color:{ORANGE}">Percentile 50</b> = mediana storica = neutro<br>
            <b style="color:{LIME}">Percentile 100</b> = valore ai massimi storici<br><br>
            Indicatori bearish (Real Yield, Stress, HY OAS) vengono invertiti (100 - p).
          </div>
        </div>""", unsafe_allow_html=True)

        st.markdown(f"""
        <div class="metric-tile">
          <div class="metric-label">ARCHITETTURA DEI PILASTRI</div>
          <div style="font-size:0.65rem;color:{TEXT_COL};line-height:1.8;margin-top:8px">
            <b style="color:{CYAN}">A · Monetario (20%)</b><br>
            M2 Reale · Velocity · Real Yield · HY OAS · STLFSI · MOVE<br>(M2/PIL: solo grafico, inverso esatto di Velocity)<br><br>
            <b style="color:{LIME}">B · Economia Reale (30%)</b><br>
            PMI Composito · INDPRO YoY · Disoccupazione D3M · NFP D3M · Core PCE YoY<br><br>
            <b style="color:{ORANGE}">C · Fiscale (15%)</b><br>
            Impulso Fiscale · Debito/PIL<br><br>
            <b style="color:{BLUE}">D · Produttivo (15%)</b><br>
            Capacity Utilization · ULC YoY · Output Gap · Produttivita YoY<br><br>
            <b style="color:{MAGENTA}">E · Geopolitico (20%)</b><br>
            Oil WTI · EEM 3M · DXY · GPR Index (se CSV caricato)
          </div>
        </div>""", unsafe_allow_html=True)

    with col_m2:
        st.markdown(f"""
        <div class="metric-tile" style="margin-bottom:12px">
          <div class="metric-label">REGIME CLASSIFICATION</div>
          <div style="font-size:0.65rem;color:{TEXT_COL};line-height:1.8;margin-top:8px">
            <b style="color:{CYAN}">Growth Score</b> = media(sB, sD)<br>
            <b style="color:{ORANGE}">Inflation Proxy</b> = 100 - sA<br><br>
            <b style="color:{CYAN}">GOLDILOCKS</b>: growth &ge;50 · infl &lt;50<br>
            <b style="color:{ORANGE}">INFL. BOOM</b>: growth &ge;50 · infl &ge;50<br>
            <b style="color:{RED}">STAGFLATION</b>: growth &lt;50 · infl &ge;50<br>
            <b style="color:{BLUE}">DISINFL. BUST</b>: growth &lt;50 · infl &lt;50
          </div>
        </div>""", unsafe_allow_html=True)

        st.markdown(f"""
        <div class="metric-tile" style="margin-bottom:12px">
          <div class="metric-label">METRICHE SINTETICHE</div>
          <div style="font-size:0.65rem;color:{TEXT_COL};line-height:1.8;margin-top:8px">
            <b style="color:{BLUE}">Macro Breadth</b>: % pilastri con score &gt;50<br>
            <b style="color:{MAGENTA}">Regime Confidence</b>: media |score - 50|<br>
            <b style="color:{CYAN}">Regime Persistence</b>: std dev rolling 6M
          </div>
        </div>""", unsafe_allow_html=True)

        st.markdown(f"""
        <div class="metric-tile">
          <div class="metric-label">CHANGELOG</div>
          <div style="font-size:0.62rem;color:{TEXT_COL};line-height:1.9;margin-top:8px">
            <span style="color:{CYAN}">BUG v1.4.2</span> m2_gdp_ratio: fix QS resample<br>
            <span style="color:{CYAN}">BUG v1.4.2</span> m2_velocity: fix QS resample<br>
            <span style="color:{CYAN}">BUG v1.4.2</span> M2/PIL grafico: sort_index + interpolate<br>
            <span style="color:{LIME}">NEW v1.4.1</span> GPR Index + eventi storici<br>
            <span style="color:{LIME}">NEW v1.4.1</span> GPR subplot sottopancia Tab1<br>
            <span style="color:{LIME}">NEW v1.4.1</span> File uploader CSV GPR sidebar<br>
            <span style="color:{ORANGE}">UX v1.4.1</span> MOVE → Pilastro A Monetario<br>
            <span style="color:{ORANGE}">UX v1.4.1</span> DXY lookback 30Y<br>
            <span style="color:{CYAN}">BUG v1.4</span> HY OAS unita corretta (x100 bp)<br>
            <span style="color:{CYAN}">BUG v1.4</span> Serie storica: percentile expanding<br>
            <span style="color:{LIME}">NEW v1.4</span> STLFSI Financial Stress Index<br>
            <span style="color:{LIME}">NEW v1.4</span> PMI auto-FRED (ISM Mfg + Svc)<br>
            <span style="color:{LIME}">NEW v1.4</span> Regime Persistence Metric<br>
            <span style="color:{LIME}">NEW v1.4</span> Tab Backtest rendimenti per regime
          </div>
        </div>""", unsafe_allow_html=True)
