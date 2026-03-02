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

# =============================================================================
# PAGE CONFIG
# =============================================================================
st.set_page_config(
    page_title="MACRO CORE ENGINE v1.1",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# GLOBAL CSS — versione più leggibile
# =============================================================================
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;700;800&display=swap');

  :root {
    --bg:      #05070c;
    --surface: #0d111a;
    --border:  #1b2635;
    --cyan:    #00f5c4;
    --red:     #ff4d6d;
    --amber:   #f5a623;
    --blue:    #4da6ff;
    --text:    #d4e0f0;
    --muted:   #7f93aa;
  }

  html, body,
  [data-testid="stAppViewContainer"],
  [data-testid="stApp"],
  .stApp {
    background-color: var(--bg) !important;
    color: var(--text) !important;
    font-family: 'Space Mono', monospace !important;
  }

  [data-testid="stSidebar"] {
    background-color: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
  }

  header[data-testid="stHeader"] {
    background: var(--bg) !important;
    border-bottom: 1px solid var(--border) !important;
  }

  .block-container { padding-top: 3.5rem; padding-bottom: 2rem; }
  h1,h2,h3 { font-family: 'Syne', sans-serif !important; }

  .main-title {
    font-family: 'Syne', sans-serif;
    font-size: 2.1rem;
    font-weight: 800;
    color: var(--cyan);
    letter-spacing: -0.5px;
    text-transform: uppercase;
  }
  .sub-title {
    font-size: 0.75rem;
    color: var(--muted);
    letter-spacing: 3px;
    text-transform: uppercase;
    margin-top: 4px;
  }
  .section-label {
    font-family: 'Syne', sans-serif;
    font-size: 0.7rem;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: var(--muted);
    border-bottom: 1px solid var(--border);
    padding-bottom: 4px;
    margin-bottom: 12px;
    margin-top: 22px;
  }
  .metric-tile {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 12px 14px;
    position: relative;
    overflow: hidden;
    margin-bottom: 10px;
  }
  .metric-tile::before {
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 3px; height: 100%;
    background: var(--cyan);
  }
  .metric-tile.red::before   { background: var(--red); }
  .metric-tile.amber::before { background: var(--amber); }
  .metric-tile.blue::before  { background: var(--blue); }
  .metric-label {
    font-size: 0.7rem;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: var(--muted);
  }
  .metric-value {
    font-family: 'Syne', sans-serif;
    font-size: 1.6rem;
    font-weight: 700;
    color: #eaf3ff;
    line-height: 1.1;
  }
  .metric-sub {
    font-size: 0.7rem;
    color: var(--muted);
    margin-top: 4px;
  }
  .pill {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 2px;
    font-size: 0.65rem;
    letter-spacing: 2px;
    text-transform: uppercase;
    font-weight: 700;
  }
  .pill-bull { background: rgba(0,245,196,0.12);  color: #00f5c4; border: 1px solid #00f5c4; }
  .pill-bear { background: rgba(255,77,109,0.12); color: #ff4d6d; border: 1px solid #ff4d6d; }
  .pill-neut { background: rgba(245,166,35,0.12); color: #f5a623; border: 1px solid #f5a623; }

  .sidebar-section {
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: var(--amber);
    margin-top: 18px;
    margin-bottom: 4px;
    border-bottom: 1px solid var(--border);
    padding-bottom: 4px;
  }
  [data-testid="stSidebar"] label {
    font-size: 0.75rem !important;
    color: #c8d8e8 !important;
    font-family: 'Space Mono', monospace !important;
  }

  .regime-quad {
    border-radius: 6px;
    padding: 16px 18px;
    text-align: center;
    border: 1px solid;
    font-size: 0.8rem;
  }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# CONSTANTS
# =============================================================================
PLOT_BG  = "#05070c"
PAPER_BG = "#0d111a"
GRID_COL = "#1b2635"
CYAN     = "#00f5c4"
RED      = "#ff4d6d"
AMBER    = "#f5a623"
BLUE     = "#4da6ff"
TEXT_COL = "#d4e0f0"
MUTED    = "#7f93aa"

FRED_API_KEY = "938a76ed726e8351f43e1b0c36365784"

# =============================================================================
# HELPERS — LAYOUT & UTILS
# =============================================================================
def base_layout(title="", height=320):
    return dict(
        height=height,
        title=dict(text=title, font=dict(family="Syne", size=13, color=TEXT_COL), x=0.01),
        paper_bgcolor=PAPER_BG,
        plot_bgcolor=PLOT_BG,
        font=dict(family="Space Mono", color=TEXT_COL, size=11),
        xaxis=dict(gridcolor=GRID_COL, showgrid=True, zeroline=False, tickfont=dict(size=10)),
        yaxis=dict(gridcolor=GRID_COL, showgrid=True, zeroline=False, tickfont=dict(size=10)),
        margin=dict(l=55, r=40, t=40, b=40),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
        hovermode="x unified",
    )

def signal_pill(label):
    cls = {"BULL":"pill-bull","BEAR":"pill-bear","NEUTRAL":"pill-neut"}.get(label,"pill-neut")
    return f'<span class="pill {cls}">{label}</span>'

def tile_html(label, value, sub="", color_class="", pill=None):
    pill_html = f'<div style="margin-top:6px">{signal_pill(pill)}</div>' if pill else ""
    return f"""
    <div class="metric-tile {color_class}">
      <div class="metric-label">{label}</div>
      <div class="metric-value">{value}</div>
      <div class="metric-sub">{sub}</div>
      {pill_html}
    </div>"""

def zscore_series(series, window):
    m = series.rolling(window, min_periods=window//2).mean()
    s = series.rolling(window, min_periods=window//2).std()
    return ((series - m) / s).replace([np.inf, -np.inf], np.nan)

def percentile_score(series, value):
    s = series.dropna()
    if len(s) < 20:
        return 50.0
    pct = (s < value).mean() * 100
    return float(pct)

def score_color(score):
    if score >= 60: return CYAN
    if score >= 40: return AMBER
    return RED

def score_pill(score):
    if score >= 60: return "BULL"
    if score >= 40: return "NEUTRAL"
    return "BEAR"

# =============================================================================
# FRED CLIENT
# =============================================================================
@st.cache_resource
def get_fred():
    return Fred(api_key=FRED_API_KEY)

fred = get_fred()

# =============================================================================
# DATA LOADING — FRED & MARKET
# =============================================================================
@st.cache_data(ttl=3600*6)
def load_fred_series(series_id, years=15):
    start = (datetime.now() - timedelta(days=365*years)).strftime('%Y-%m-%d')
    try:
        s = fred.get_series(series_id, observation_start=start)
        return s.dropna()
    except Exception:
        return pd.Series(dtype=float)

@st.cache_data(ttl=3600*6)
def load_all_fred():
    data = {}
    # MONETARIO
    data["M2"]        = load_fred_series("M2SL", 20)
    data["GDP"]       = load_fred_series("GDP", 20)
    data["CPI"]       = load_fred_series("CPIAUCSL", 20)
    data["REALYIELD"] = load_fred_series("DFII10", 15)
    data["HY_OAS"]    = load_fred_series("BAMLH0A0HYM2", 15)
    data["IG_OAS"]    = load_fred_series("BAMLC0A0CM", 15)

    # ECONOMIA REALE
    data["INDPRO"]    = load_fred_series("INDPRO", 20)
    data["UNRATE"]    = load_fred_series("UNRATE", 20)
    data["PAYEMS"]    = load_fred_series("PAYEMS", 20)

    # FISCALE
    data["DEFICIT"]   = load_fred_series("FYFSGDA188S", 30)
    data["DEBT_GDP"]  = load_fred_series("GFDEGDQ188S", 30)

    # PRODUTTIVO
    data["TCU"]       = load_fred_series("TCU", 20)
    data["ULC"]       = load_fred_series("ULCNFB", 20)

    return data

@st.cache_data(ttl=3600*4)
def load_market_data():
    result = {}
    tickers = {
        "OIL":  "CL=F",
        "EEM":  "EEM",
        "MOVE": "^MOVE",
    }
    for name, ticker in tickers.items():
        try:
            df = yf.download(ticker, period="10y", progress=False, auto_adjust=True)
            if not df.empty:
                close = df["Close"]
                result[name] = close.squeeze().dropna()
        except Exception:
            pass
    return result

# =============================================================================
# DERIVED CALCULATIONS
# =============================================================================
def compute_m2_gdp_ratio(m2, gdp):
    if m2.empty or gdp.empty:
        return pd.Series(dtype=float)
    m2_q = m2.resample("Q").last()
    gdp_aligned, m2_aligned = gdp.align(m2_q, join="inner")
    if len(gdp_aligned) == 0:
        return pd.Series(dtype=float)
    return (m2_aligned / gdp_aligned).dropna()

def compute_m2_real(m2, cpi):
    if m2.empty or cpi.empty:
        return pd.Series(dtype=float)
    cpi_m = cpi.resample("M").last()
    m2_m  = m2.resample("M").last()
    m2_m, cpi_m = m2_m.align(cpi_m, join="inner")
    if len(m2_m) == 0:
        return pd.Series(dtype=float)
    base = cpi_m.iloc[0]
    cpi_indexed = cpi_m / base * 100
    m2_real = (m2_m / cpi_indexed) * 100
    return m2_real.dropna()

def compute_velocity(m2, gdp):
    if m2.empty or gdp.empty:
        return pd.Series(dtype=float)
    m2_q = m2.resample("Q").last()
    gdp_aligned, m2_aligned = gdp.align(m2_q, join="inner")
    if len(gdp_aligned) == 0:
        return pd.Series(dtype=float)
    vel = (gdp_aligned / m2_aligned).dropna()
    return vel

def compute_yoy(series, periods=12):
    if series.empty:
        return pd.Series(dtype=float)
    return series.pct_change(periods) * 100

def compute_unrate_3m_change(unrate):
    if unrate.empty:
        return pd.Series(dtype=float)
    return unrate.diff(3)

def compute_output_gap_proxy(indpro):
    if indpro.empty or len(indpro) < 24:
        return pd.Series(dtype=float)
    from scipy.signal import savgol_filter
    try:
        wl = min(len(indpro) - 1 if len(indpro) % 2 == 0 else len(indpro), 61)
        trend = pd.Series(
            savgol_filter(indpro.values, window_length=wl, polyorder=2),
            index=indpro.index
        )
        gap = ((indpro - trend) / trend * 100).dropna()
        return gap
    except Exception:
        trend = indpro.rolling(36, min_periods=12).mean()
        return ((indpro - trend) / trend * 100).dropna()

def compute_fiscal_impulse(deficit):
    if deficit.empty:
        return pd.Series(dtype=float)
    return deficit.diff(1)
# =============================================================================
# SCORING — 5 PILLARS
# =============================================================================
ZSCORE_WINDOW_MONTHS = 36

def score_pillar_monetary(data):
    indicators = {}
    scores = []

    m2 = data.get("M2", pd.Series())
    gdp = data.get("GDP", pd.Series())
    cpi = data.get("CPI", pd.Series())
    ry  = data.get("REALYIELD", pd.Series())
    hy  = data.get("HY_OAS", pd.Series())

    # M2/PIL
    m2_gdp = compute_m2_gdp_ratio(m2, gdp)
    if not m2_gdp.empty:
        m2_gdp_m = m2_gdp.resample("M").interpolate()
        last_val = float(m2_gdp.iloc[-1])
        score = percentile_score(m2_gdp_m, last_val)
        scores.append(score)
        indicators["M2/PIL"] = {
            "value": round(last_val, 3),
            "score": round(score, 1),
            "series": m2_gdp,
            "unit": "ratio",
            "desc": "Liquidità relativa: M2 / PIL nominale"
        }

    # M2 reale
    m2_real = compute_m2_real(m2, cpi)
    if not m2_real.empty:
        last_val = float(m2_real.iloc[-1])
        score = percentile_score(m2_real, last_val)
        scores.append(score)
        indicators["M2 reale (CPI defl.)"] = {
            "value": round(last_val, 1),
            "score": round(score, 1),
            "series": m2_real,
            "unit": "index",
            "desc": "M2 deflazionato da CPI"
        }

    # Velocity
    vel = compute_velocity(m2, gdp)
    if not vel.empty:
        vel_m = vel.resample("M").interpolate()
        last_val = float(vel.iloc[-1])
        score = percentile_score(vel_m, last_val)
        scores.append(score)
        indicators["Velocity (GDP/M2)"] = {
            "value": round(last_val, 3),
            "score": round(score, 1),
            "series": vel,
            "unit": "x",
            "desc": "Velocità della moneta: PIL nominale / M2"
        }

    # Real Yield (basso = bull)
    if not ry.empty:
        ry_m = ry.resample("M").last()
        last_val = float(ry_m.iloc[-1])
        raw_score = percentile_score(ry_m, last_val)
        score = 100 - raw_score
        scores.append(score)
        indicators["Real Yield 10Y"] = {
            "value": round(last_val, 2),
            "score": round(score, 1),
            "series": ry_m,
            "unit": "%",
            "desc": "Tasso reale 10Y · basso/negativo = favorevole a risk assets"
        }

    # HY OAS (basso = bull)
    if not hy.empty:
        hy_m = hy.resample("M").last()
        last_val = float(hy_m.iloc[-1])
        raw_score = percentile_score(hy_m, last_val)
        score = 100 - raw_score
        scores.append(score)
        indicators["HY Credit Spread"] = {
            "value": round(last_val, 0),
            "score": round(score, 1),
            "series": hy_m,
            "unit": "bp",
            "desc": "Spread HY · basso = poco stress sistemico"
        }

    pillar_score = float(np.mean(scores)) if scores else 50.0
    return round(pillar_score, 1), indicators

def score_pillar_real_economy(data, pmi_manual):
    indicators = {}
    scores = []

    # PMI manuale
    if pmi_manual is not None:
        pmi_score = min(100, max(0, (pmi_manual - 30) / (70 - 30) * 100))
        scores.append(pmi_score)
        indicators["PMI Composito"] = {
            "value": pmi_manual,
            "score": round(pmi_score, 1),
            "series": None,
            "unit": "",
            "desc": ">52 espansione · <48 contrazione"
        }

    # Produzione industriale YoY
    indpro = data.get("INDPRO", pd.Series())
    if not indpro.empty:
        ip_yoy = compute_yoy(indpro, 12).dropna()
        if not ip_yoy.empty:
            last_val = float(ip_yoy.iloc[-1])
            score = percentile_score(ip_yoy, last_val)
            scores.append(score)
            indicators["INDPRO YoY"] = {
                "value": round(last_val, 2),
                "score": round(score, 1),
                "series": ip_yoy,
                "unit": "%",
                "desc": "Produzione industriale · variazione % anno su anno"
            }

    # Disoccupazione Δ3M (scende = bull)
    unrate = data.get("UNRATE", pd.Series())
    if not unrate.empty:
        du = compute_unrate_3m_change(unrate).dropna()
        if not du.empty:
            last_val = float(du.iloc[-1])
            raw_score = percentile_score(du, last_val)
            score = 100 - raw_score
            scores.append(score)
            indicators["Disoccupazione Δ3M"] = {
                "value": round(last_val, 2),
                "score": round(score, 1),
                "series": du,
                "unit": "pp",
                "desc": "Variazione disoccupazione su 3 mesi · negativa = miglioramento"
            }

    pillar_score = float(np.mean(scores)) if scores else 50.0
    return round(pillar_score, 1), indicators

def score_pillar_fiscal(data):
    indicators = {}
    scores = []

    deficit  = data.get("DEFICIT", pd.Series())
    debt_gdp = data.get("DEBT_GDP", pd.Series())

    if not deficit.empty:
        impulse = compute_fiscal_impulse(deficit).dropna()
        if not impulse.empty:
            last_val = float(impulse.iloc[-1])
            raw_score = percentile_score(impulse, last_val)
            score = 100 - raw_score
            scores.append(score)
            indicators["Impulso fiscale"] = {
                "value": round(last_val, 2),
                "score": round(score, 1),
                "series": impulse,
                "unit": "% PIL",
                "desc": "Δ deficit/PIL · negativo = espansivo"
            }

        indicators["Deficit/PIL attuale"] = {
            "value": round(float(deficit.iloc[-1]), 1),
            "score": None,
            "series": deficit,
            "unit": "% PIL",
            "desc": "Saldo pubblico / PIL · negativo = deficit"
        }

    if not debt_gdp.empty:
        last_val = float(debt_gdp.iloc[-1])
        raw_score = percentile_score(debt_gdp, last_val)
        score = 100 - raw_score
        scores.append(score)
        indicators["Debito/PIL"] = {
            "value": round(last_val, 1),
            "score": round(score, 1),
            "series": debt_gdp,
            "unit": "%",
            "desc": "Debito federale / PIL"
        }

    pillar_score = float(np.mean(scores)) if scores else 50.0
    return round(pillar_score, 1), indicators

def score_pillar_productive(data):
    indicators = {}
    scores = []

    tcu = data.get("TCU", pd.Series())
    ulc = data.get("ULC", pd.Series())
    indpro = data.get("INDPRO", pd.Series())

    if not tcu.empty:
        last_val = float(tcu.iloc[-1])
        score = percentile_score(tcu, last_val)
        scores.append(score)
        indicators["Capacity Utilization"] = {
            "value": round(last_val, 1),
            "score": round(score, 1),
            "series": tcu,
            "unit": "%",
            "desc": "Utilizzo capacità produttiva"
        }

    if not ulc.empty:
        ulc_yoy = compute_yoy(ulc, 4).dropna()
        if not ulc_yoy.empty:
            last_val = float(ulc_yoy.iloc[-1])
            raw_score = percentile_score(ulc_yoy, last_val)
            score = 100 - raw_score
            scores.append(score)
            indicators["Unit Labor Costs YoY"] = {
                "value": round(last_val, 2),
                "score": round(score, 1),
                "series": ulc_yoy,
                "unit": "%",
                "desc": "Costi lavoro per unità prodotta"
            }

    if not indpro.empty:
        gap = compute_output_gap_proxy(indpro)
        if not gap.empty:
            last_val = float(gap.iloc[-1])
            score = percentile_score(gap, last_val)
            scores.append(score)
            indicators["Output Gap (proxy)"] = {
                "value": round(last_val, 2),
                "score": round(score, 1),
                "series": gap,
                "unit": "%",
                "desc": "Deviazione produzione da trend"
            }

    pillar_score = float(np.mean(scores)) if scores else 50.0
    return round(pillar_score, 1), indicators

def score_pillar_geopolitical(mkt_data):
    indicators = {}
    scores = []

    oil  = mkt_data.get("OIL")
    eem  = mkt_data.get("EEM")
    move = mkt_data.get("MOVE")

    if oil is not None and len(oil) > 60:
        last_val = float(oil.iloc[-1])
        raw_score = percentile_score(oil, last_val)
        score = 100 - raw_score
        scores.append(score)
        indicators["Oil (WTI)"] = {
            "value": round(last_val, 1),
            "score": round(score, 1),
            "series": oil,
            "unit": "$",
            "desc": "Prezzo petrolio · alto = rischio inflattivo/geopolitico"
        }

    if eem is not None and len(eem) > 63:
        eem_3m = float(eem.iloc[-1] / eem.iloc[-63] - 1) * 100
        score = min(100, max(0, (eem_3m + 20) / 40 * 100))
        scores.append(score)
        indicators["EEM 3M perf."] = {
            "value": round(eem_3m, 1),
            "score": round(score, 1),
            "series": None,
            "unit": "%",
            "desc": "ETF EM · 3 mesi · positivo = EM stabili"
        }

    if move is not None and len(move) > 60:
        last_val = float(move.iloc[-1])
        raw_score = percentile_score(move, last_val)
        score = 100 - raw_score
        scores.append(score)
        indicators["MOVE Index"] = {
            "value": round(last_val, 1),
            "score": round(score, 1),
            "series": move,
            "unit": "index",
            "desc": "Volatilità obbligazionaria globale"
        }

    pillar_score = float(np.mean(scores)) if scores else 50.0
    return round(pillar_score, 1), indicators

def compute_regime(growth_score, inflation_score):
    high_growth    = growth_score >= 50
    high_inflation = inflation_score >= 50

    if high_growth and not high_inflation:
        return "GOLDILOCKS", CYAN, "Crescita senza inflazione — ottimale per equity"
    elif high_growth and high_inflation:
        return "INFLATIONARY BOOM", AMBER, "Crescita con inflazione — favorevole a real assets"
    elif not high_growth and high_inflation:
        return "STAGFLATION", RED, "Bassa crescita + alta inflazione"
    else:
        return "DISINFLATIONARY BUST", BLUE, "Bassa crescita + bassa inflazione — favorevole a bond"

# =============================================================================
# SESSION DEFAULTS
# =============================================================================
defaults = {
    "pmi_composite": 52.0,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# =============================================================================
# SIDEBAR
# =============================================================================
with st.sidebar:
    st.markdown(
        '<div style="font-family:Syne;font-size:1.2rem;font-weight:800;color:#00f5c4;letter-spacing:-0.5px;">🧭 MACRO CORE ENGINE</div>',
        unsafe_allow_html=True)
    st.markdown(
        '<div style="font-size:0.7rem;letter-spacing:3px;color:#4a6070;text-transform:uppercase;margin-bottom:16px;">Macro Regime Monitor v1.1</div>',
        unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section">📊 PMI Composito</div>', unsafe_allow_html=True)
    pmi_val = st.slider(
        "PMI Composito (USA / Globale)",
        min_value=35.0, max_value=65.0, value=float(st.session_state["pmi_composite"]), step=0.1
    )
    st.session_state["pmi_composite"] = pmi_val
    st.markdown(
        '<div style="font-size:0.7rem;color:#8ab0c8;line-height:1.6;margin-bottom:6px;">'
        'Fonte: ISM + ISM Services o S&P Global PMI Composite<br>'
        '<b>Aggiorna mensile</b></div>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section">⚙️ Impostazioni</div>', unsafe_allow_html=True)
    show_monetary_z = st.checkbox("Mostra pannello z-score monetario", value=True)
    st.markdown(
        '<div style="font-size:0.7rem;color:#8ab0c8;line-height:1.4;margin-bottom:6px;">'
        'Z-score usato solo per visualizzazione · scoring basato su percentili</div>',
        unsafe_allow_html=True)

    if st.button("🔄 Aggiorna dati FRED / Mercati"):
        st.cache_data.clear()

# =============================================================================
# LOAD DATA
# =============================================================================
data = load_all_fred()
mkt_data = load_market_data()

# =============================================================================
# SCORING
# =============================================================================
monetary_score, monetary_ind = score_pillar_monetary(data)
real_score, real_ind         = score_pillar_real_economy(data, st.session_state["pmi_composite"])
fiscal_score, fiscal_ind     = score_pillar_fiscal(data)
prod_score, prod_ind         = score_pillar_productive(data)
geo_score, geo_ind           = score_pillar_geopolitical(mkt_data)

pillar_scores = {
    "A · Monetario": monetary_score,
    "B · Econ. Reale": real_score,
    "C · Fiscale": fiscal_score,
    "D · Produttivo": prod_score,
    "E · Geopolitico": geo_score,
}

growth_score    = float(np.mean([real_score, prod_score]))
inflation_proxy = 100 - monetary_score
composite_score = float(np.mean(list(pillar_scores.values())))

regime_label, regime_color, regime_desc = compute_regime(growth_score, inflation_proxy)

# =============================================================================
# MAIN LAYOUT
# =============================================================================
col_main, col_side = st.columns([3, 1.4])

with col_main:
    st.markdown('<div class="main-title">MACRO CORE ENGINE</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-title">Macro Regime Monitor · 5 Pilastri · FRED API + Mercati</div>',
        unsafe_allow_html=True)
    st.markdown(
        f'<div style="font-size:0.75rem;color:{MUTED};margin-top:6px;">'
        f'Last update: {datetime.utcnow().strftime("%Y-%m-%d %H:%M")} UTC · '
        f'Percentile-based scoring</div>',
        unsafe_allow_html=True)

    st.markdown('<div class="section-label">Regime macro</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1.4, 1.2, 1.4])

    with c1:
        st.markdown(
            f'<div class="metric-tile" style="border-color:{regime_color};">'
            f'<div class="metric-label">Regime attuale</div>'
            f'<div class="metric-value" style="color:{regime_color};">{regime_label}</div>'
            f'<div class="metric-sub">{regime_desc}</div>'
            f'</div>', unsafe_allow_html=True)

    with c2:
        st.markdown(tile_html(
            "Composite Score",
            f"{composite_score:.1f}",
            "Media 5 pilastri (0–100)",
            color_class="blue",
            pill=score_pill(composite_score)
        ), unsafe_allow_html=True)

    with c3:
        st.markdown(tile_html(
            "Growth Score",
            f"{growth_score:.1f}",
            "Econ. Reale + Produttivo",
            color_class="blue",
            pill=score_pill(growth_score)
        ), unsafe_allow_html=True)

    st.markdown('<div class="section-label">Score per pilastro</div>', unsafe_allow_html=True)
    fig_bar = go.Figure()
    names = list(pillar_scores.keys())
    vals  = list(pillar_scores.values())
    colors = [score_color(v) for v in vals]

    fig_bar.add_bar(
        x=names,
        y=vals,
        marker_color=colors,
        text=[f"{v:.0f}" for v in vals],
        textposition="outside"
    )
    layout_bar = base_layout("Score per pilastro (0–100)", height=320)
    layout_bar["yaxis"] = dict(range=[0, 100], gridcolor=GRID_COL)
    fig_bar.update_layout(**layout_bar)
    st.plotly_chart(fig_bar, use_container_width=True)

    if show_monetary_z:
        st.markdown('<div class="section-label">Z-Score Panel — Monetario</div>', unsafe_allow_html=True)

        m2 = data.get("M2", pd.Series())
        gdp = data.get("GDP", pd.Series())
        cpi = data.get("CPI", pd.Series())
        ry  = data.get("REALYIELD", pd.Series())
        hy  = data.get("HY_OAS", pd.Series())

        m2_gdp = compute_m2_gdp_ratio(m2, gdp)
        m2_real = compute_m2_real(m2, cpi)
        vel = compute_velocity(m2, gdp)

        def prep_z(s):
            if s is None or s.empty:
                return None
            s_m = s.resample("M").last().dropna()
            s_m = s_m[s_m.index >= (s_m.index.max() - pd.DateOffset(years=8))]
            z = zscore_series(s_m, 24)
            return s_m, z

        series_map = {
            "M2/PIL": m2_gdp,
            "M2 reale": m2_real,
            "Velocity": vel,
            "Real Yield 10Y": ry,
            "HY Spread": hy,
        }
        colors_z = {
            "M2/PIL": CYAN,
            "M2 reale": BLUE,
            "Velocity": "#9b59b6",
            "Real Yield 10Y": RED,
            "HY Spread": AMBER,
        }

        fig_z = go.Figure()
        for name, s in series_map.items():
            prep = prep_z(s)
            if prep is None:
                continue
            s_m, z = prep
            if z is None or z.dropna().empty:
                continue
            fig_z.add_trace(go.Scatter(
                x=z.index,
                y=z,
                mode="lines",
                name=name,
                line=dict(color=colors_z[name], width=2.2),
            ))

        fig_z.add_hline(y=1.5, line_dash="dot", line_color=MUTED, line_width=1,
                        annotation_text="+1.5σ", annotation_position="top right",
                        annotation_font=dict(color=MUTED, size=9))
        fig_z.add_hline(y=-1.5, line_dash="dot", line_color=MUTED, line_width=1,
                        annotation_text="-1.5σ", annotation_position="bottom right",
                        annotation_font=dict(color=MUTED, size=9))

        layout_z = base_layout("Z-Score indicatori monetari (ultimi 8 anni)", height=360)
        layout_z["yaxis"] = dict(gridcolor=GRID_COL, zeroline=False, range=[-4, 4])
        fig_z.update_layout(**layout_z)
        st.plotly_chart(fig_z, use_container_width=True)

with col_side:
    st.markdown('<div class="section-label">Dettaglio pilastri</div>', unsafe_allow_html=True)

    def render_pillar_block(title, score, indicators):
        st.markdown(f"**{title} — {score:.1f}/100**  {signal_pill(score_pill(score))}", unsafe_allow_html=True)
        for name, info in indicators.items():
            val = info["value"]
            unit = info["unit"]
            desc = info["desc"]
            st.markdown(
                f"<div style='font-size:0.8rem;color:{TEXT_COL};margin-top:4px;'><b>{name}</b>: "
                f"{val} {unit}<br><span style='color:{MUTED};font-size:0.75rem;'>{desc}</span></div>",
                unsafe_allow_html=True
            )
        st.markdown("<hr style='border:0;border-top:1px solid #1b2635;margin:10px 0;'>", unsafe_allow_html=True)

    render_pillar_block("A · Monetario", monetary_score, monetary_ind)
    render_pillar_block("B · Economia reale", real_score, real_ind)
    render_pillar_block("C · Fiscale", fiscal_score, fiscal_ind)
    render_pillar_block("D · Produttivo", prod_score, prod_ind)
    render_pillar_block("E · Geopolitico", geo_score, geo_ind)
