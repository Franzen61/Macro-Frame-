"""
MACRO CORE ENGINE v1.0
======================
5-pillar macro regime monitor: Monetary · Real Economy · Fiscal · Productive · Geopolitical
Coerente con Equity Pulse, Bond Monitor, Commodity Supercycle, Settoriale.

Dati automatici: FRED API + yfinance
Dati manuali:    sidebar (PMI, GPR)
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
    page_title="MACRO CORE ENGINE",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================================
# GLOBAL CSS — coerente con Equity Pulse
# ============================================================================
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;700;800&display=swap');

  :root {
    --bg:      #070b12;
    --surface: #0e1420;
    --border:  #1c2a3a;
    --cyan:    #00f5c4;
    --red:     #ff4d6d;
    --amber:   #f5a623;
    --blue:    #4da6ff;
    --text:    #c8d8e8;
    --muted:   #7a9ab0;
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

  [data-testid="stDecoration"] { display: none !important; }
  header[data-testid="stHeader"] {
    background: var(--bg) !important;
    border-bottom: 1px solid var(--border) !important;
  }

  .block-container { padding-top: 4rem; padding-bottom: 2rem; }
  h1,h2,h3 { font-family: 'Syne', sans-serif !important; }

  .main-title {
    font-family: 'Syne', sans-serif;
    font-size: 2.2rem;
    font-weight: 800;
    color: var(--cyan);
    letter-spacing: -1px;
    text-transform: uppercase;
  }
  .sub-title {
    font-size: 0.68rem;
    color: var(--muted);
    letter-spacing: 3px;
    text-transform: uppercase;
    margin-top: 2px;
  }
  .section-label {
    font-family: 'Syne', sans-serif;
    font-size: 0.62rem;
    letter-spacing: 4px;
    text-transform: uppercase;
    color: var(--muted);
    border-bottom: 1px solid var(--border);
    padding-bottom: 4px;
    margin-bottom: 14px;
    margin-top: 24px;
  }
  .metric-tile {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 14px 18px;
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
    font-size: 0.58rem;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: var(--muted);
  }
  .metric-value {
    font-family: 'Syne', sans-serif;
    font-size: 1.7rem;
    font-weight: 700;
    color: #eaf3ff;
    line-height: 1.1;
  }
  .metric-sub {
    font-size: 0.62rem;
    color: var(--muted);
    margin-top: 2px;
  }
  .pill {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 2px;
    font-size: 0.58rem;
    letter-spacing: 2px;
    text-transform: uppercase;
    font-weight: 700;
  }
  .pill-bull { background: rgba(0,245,196,0.12);  color: #00f5c4; border: 1px solid #00f5c4; }
  .pill-bear { background: rgba(255,77,109,0.12); color: #ff4d6d; border: 1px solid #ff4d6d; }
  .pill-neut { background: rgba(245,166,35,0.12); color: #f5a623; border: 1px solid #f5a623; }
  .sidebar-section {
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: var(--amber);
    margin-top: 20px;
    margin-bottom: 4px;
    border-bottom: 1px solid var(--border);
    padding-bottom: 4px;
  }
  [data-testid="stSidebar"] label {
    font-size: 0.7rem !important;
    color: #c8d8e8 !important;
    font-family: 'Space Mono', monospace !important;
  }
  .regime-quad {
    border-radius: 6px;
    padding: 18px 20px;
    text-align: center;
    border: 1px solid;
  }
  div[data-testid="stMetric"] { display: none; }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# CONSTANTS
# ============================================================================
PLOT_BG  = "#070b12"
PAPER_BG = "#0e1420"
GRID_COL = "#1c2a3a"
CYAN     = "#00f5c4"
RED      = "#ff4d6d"
AMBER    = "#f5a623"
BLUE     = "#4da6ff"
TEXT_COL = "#c8d8e8"
MUTED    = "#7a9ab0"

FRED_API_KEY = '938a76ed726e8351f43e1b0c36365784'

# ============================================================================
# HELPERS — LAYOUT
# ============================================================================
def base_layout(title="", height=320):
    return dict(
        height=height,
        title=dict(text=title, font=dict(family="Syne", size=12, color=TEXT_COL), x=0.01),
        paper_bgcolor=PAPER_BG,
        plot_bgcolor=PLOT_BG,
        font=dict(family="Space Mono", color=TEXT_COL, size=10),
        xaxis=dict(gridcolor=GRID_COL, showgrid=True, zeroline=False, tickfont=dict(size=9)),
        yaxis=dict(gridcolor=GRID_COL, showgrid=True, zeroline=False, tickfont=dict(size=9)),
        margin=dict(l=48, r=60, t=40, b=36),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=9)),
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
    """Rolling z-score."""
    m = series.rolling(window, min_periods=window//2).mean()
    s = series.rolling(window, min_periods=window//2).std()
    return ((series - m) / s).replace([np.inf, -np.inf], np.nan)

def zscore_to_score(z, invert=False):
    """Converte z-score in score 0-100 via sigmoid clippato."""
    z_clipped = np.clip(z, -3, 3)
    if invert:
        z_clipped = -z_clipped
    return (z_clipped + 3) / 6 * 100

def score_color(score):
    if score >= 60: return CYAN
    if score >= 40: return AMBER
    return RED

def score_pill(score):
    if score >= 60: return "BULL"
    if score >= 40: return "NEUTRAL"
    return "BEAR"

def add_percentile_bands(fig, series, row=1, col=1, color=BLUE):
    """Aggiunge bande 25°/75° percentile su un grafico."""
    if series is None or len(series) < 20:
        return
    p25 = float(np.percentile(series.dropna(), 25))
    p75 = float(np.percentile(series.dropna(), 75))
    fig.add_hline(y=p75, line_dash="dot", line_color=CYAN, line_width=1,
                  annotation_text=f"75p ({p75:.2f})", annotation_position="right",
                  annotation_font=dict(color=CYAN, size=8), row=row, col=col)
    fig.add_hline(y=p25, line_dash="dot", line_color=RED, line_width=1,
                  annotation_text=f"25p ({p25:.2f})", annotation_position="right",
                  annotation_font=dict(color=RED, size=8), row=row, col=col)

# ============================================================================
# FRED CLIENT
# ============================================================================
@st.cache_resource
def get_fred():
    return Fred(api_key=FRED_API_KEY)

fred = get_fred()

# ============================================================================
# DATA LOADING — FRED
# ============================================================================
@st.cache_data(ttl=3600*6)
def load_fred_series(series_id, years=10):
    start = (datetime.now() - timedelta(days=365*years)).strftime('%Y-%m-%d')
    try:
        s = fred.get_series(series_id, observation_start=start)
        return s.dropna()
    except Exception as e:
        return pd.Series(dtype=float)

@st.cache_data(ttl=3600*6)
def load_all_fred():
    """Carica tutte le serie FRED necessarie."""
    data = {}

    # MONETARIO
    data['M2']         = load_fred_series('M2SL', 15)          # M2 money supply
    data['GDP']        = load_fred_series('GDP', 15)            # GDP nominale (trimestrale)
    data['GDPNOW']     = load_fred_series('GDPC1', 15)          # GDP reale
    data['REALYIELD']  = load_fred_series('DFII10', 10)         # Real yield 10Y
    data['HY_OAS']     = load_fred_series('BAMLH0A0HYM2', 10)  # HY OAS spread
    data['IG_OAS']     = load_fred_series('BAMLC0A0CM', 10)    # IG OAS spread
    data['M2_GROWTH']  = load_fred_series('M2SL', 15)          # per calcolare YoY

    # ECONOMIA REALE
    data['INDPRO']     = load_fred_series('INDPRO', 15)         # Produzione industriale
    data['UNRATE']     = load_fred_series('UNRATE', 15)         # Disoccupazione
    data['PAYEMS']     = load_fred_series('PAYEMS', 15)         # Payrolls
    data['RETAIL']     = load_fred_series('RSXFS', 10)          # Retail sales
    data['CONF']       = load_fred_series('UMCSENT', 10)        # Consumer sentiment

    # FISCALE
    data['DEFICIT']    = load_fred_series('FYFSGDA188S', 30)    # Surplus/Deficit % PIL (annuale)
    data['DEBT_GDP']   = load_fred_series('GFDEGDQ188S', 30)    # Debito/PIL (trim.)
    data['FED_SPEND']  = load_fred_series('FGEXPND', 15)        # Spesa federale

    # PRODUTTIVO
    data['TCU']        = load_fred_series('TCU', 15)            # Capacity utilization
    data['ULC']        = load_fred_series('ULCNFB', 15)         # Unit labor costs
    data['NFCI']       = load_fred_series('NFCI', 10)           # Chicago Fed NFCI
    data['HOUST']      = load_fred_series('HOUST', 15)          # Housing starts

    # INFLAZIONE (per output gap proxy)
    data['CPIAUCSL']   = load_fred_series('CPIAUCSL', 15)
    data['PCEPILFE']   = load_fred_series('PCEPILFE', 10)       # Core PCE

    # TASSI
    data['DGS10']      = load_fred_series('DGS10', 15)
    data['DGS2']       = load_fred_series('DGS2', 15)
    data['DGS3MO']     = load_fred_series('DGS3MO', 15)

    return data

@st.cache_data(ttl=3600*4)
def load_market_data():
    """Carica dati mercato via yfinance per pilastro geopolitico."""
    result = {}
    tickers = {
        'OIL':  'CL=F',
        'GOLD': 'GC=F',
        'EEM':  'EEM',
        'DXY':  'DX-Y.NYB',
        'VIX':  '^VIX',
        'BRENT':'BZ=F',
    }
    for name, ticker in tickers.items():
        try:
            df = yf.download(ticker, period="5y", progress=False, auto_adjust=True)
            if not df.empty:
                close = df['Close']
                if isinstance(close, pd.DataFrame):
                    close = close.iloc[:,0]
                result[name] = close.squeeze().dropna()
        except:
            pass
    return result

# ============================================================================
# CALCOLI DERIVATI
# ============================================================================
def compute_m2_gdp_ratio(m2, gdp):
    """M2/PIL - resample M2 a trimestrale per allinearlo a GDP."""
    if m2.empty or gdp.empty:
        return pd.Series(dtype=float)
    m2_q = m2.resample('Q').last()
    gdp_aligned, m2_aligned = gdp.align(m2_q, join='inner')
    if len(gdp_aligned) == 0:
        return pd.Series(dtype=float)
    ratio = (m2_aligned / gdp_aligned).dropna()
    return ratio

def compute_yoy(series):
    """Variazione % anno su anno."""
    if series.empty:
        return pd.Series(dtype=float)
    if series.index.freq is not None and 'M' in str(series.index.freq):
        return series.pct_change(12) * 100
    # Tentativo generico
    return series.pct_change(12) * 100

def compute_indpro_yoy(indpro):
    return compute_yoy(indpro)

def compute_unrate_3m_change(unrate):
    """Variazione disoccupazione su 3 mesi."""
    if unrate.empty:
        return pd.Series(dtype=float)
    return unrate.diff(3)

def compute_yield_curve(dgs10, dgs2):
    if dgs10.empty or dgs2.empty:
        return pd.Series(dtype=float)
    a, b = dgs10.align(dgs2, join='inner')
    return (a - b).dropna()

def compute_fiscal_impulse(deficit):
    """Impulso fiscale = variazione YoY del deficit/PIL."""
    if deficit.empty:
        return pd.Series(dtype=float)
    return deficit.diff(1)  # Annuale, quindi diff(1) = YoY

def compute_output_gap_proxy(indpro):
    """Proxy output gap: deviazione da trend HP."""
    if indpro.empty or len(indpro) < 24:
        return pd.Series(dtype=float)
    from scipy.signal import savgol_filter
    try:
        trend = pd.Series(
            savgol_filter(indpro.values, window_length=min(len(indpro)-1 if len(indpro)%2==0 else len(indpro), 61), polyorder=2),
            index=indpro.index
        )
        gap = ((indpro - trend) / trend * 100).dropna()
        return gap
    except:
        # Fallback: rolling mean
        trend = indpro.rolling(36, min_periods=12).mean()
        return ((indpro - trend) / trend * 100).dropna()

# ============================================================================
# SCORING ENGINE
# ============================================================================
ZSCORE_WINDOW_MONTHS = 36  # 3 anni

def score_pillar_monetary(data, window=ZSCORE_WINDOW_MONTHS):
    """
    A. MONETARIO
    - M2/PIL: alto = liquido (bull for assets) → score alto se alto
    - Real Yield: basso/negativo = bull → invert
    - HY OAS: basso = no stress → invert
    Ritorna: score 0-100, dict indicatori
    """
    indicators = {}
    scores = []

    # M2/GDP
    m2_gdp = compute_m2_gdp_ratio(data.get('M2', pd.Series()), data.get('GDP', pd.Series()))
    if not m2_gdp.empty and len(m2_gdp) >= 4:
        m2_gdp_m = m2_gdp.resample('M').interpolate()
        z = zscore_series(m2_gdp_m, window)
        if not z.empty and not pd.isna(z.iloc[-1]):
            s = zscore_to_score(z.iloc[-1], invert=False)
            scores.append(s)
            indicators['M2/PIL'] = {
                'value': round(float(m2_gdp.iloc[-1]), 3),
                'z': round(float(z.iloc[-1]), 2),
                'score': round(s, 1),
                'series': m2_gdp,
                'z_series': z,
                'unit': 'ratio',
                'desc': 'Liquidità relativa: alto = eccesso di moneta vs economia'
            }

    # Real Yield
    ry = data.get('REALYIELD', pd.Series())
    if not ry.empty:
        z = zscore_series(ry, window)
        if not z.empty and not pd.isna(z.iloc[-1]):
            s = zscore_to_score(z.iloc[-1], invert=True)  # basso RY = bull
            scores.append(s)
            indicators['Real Yield 10Y'] = {
                'value': round(float(ry.iloc[-1]), 2),
                'z': round(float(z.iloc[-1]), 2),
                'score': round(s, 1),
                'series': ry,
                'z_series': z,
                'unit': '%',
                'desc': 'Tasso reale basso/negativo = favorevole a asset rischiosi'
            }

    # HY OAS
    hy = data.get('HY_OAS', pd.Series())
    if not hy.empty:
        z = zscore_series(hy, window)
        if not z.empty and not pd.isna(z.iloc[-1]):
            s = zscore_to_score(z.iloc[-1], invert=True)  # spread basso = bull
            scores.append(s)
            indicators['HY Credit Spread'] = {
                'value': round(float(hy.iloc[-1]), 0),
                'z': round(float(z.iloc[-1]), 2),
                'score': round(s, 1),
                'series': hy,
                'z_series': z,
                'unit': 'bp',
                'desc': 'Spread HY compressi = no stress sistemico = bull'
            }

    pillar_score = float(np.mean(scores)) if scores else 50.0
    return round(pillar_score, 1), indicators

def score_pillar_real_economy(data, pmi_manual, window=ZSCORE_WINDOW_MONTHS):
    """
    B. ECONOMIA REALE
    - PMI: sopra 50 = bull
    - Produzione industriale YoY: positivo = bull
    - Disoccupazione variazione 3M: negativo (scende) = bull
    """
    indicators = {}
    scores = []

    # PMI (manuale) — score diretto
    if pmi_manual is not None:
        pmi_score = min(100, max(0, (pmi_manual - 30) / (70 - 30) * 100))
        pmi_pill = "BULL" if pmi_manual > 52 else ("NEUTRAL" if pmi_manual > 48 else "BEAR")
        scores.append(pmi_score)
        indicators['PMI Composito'] = {
            'value': pmi_manual,
            'z': round((pmi_manual - 50) / 5, 2),
            'score': round(pmi_score, 1),
            'series': None,
            'z_series': None,
            'unit': '',
            'desc': '>52 espansione · <48 contrazione · 50 = neutro'
        }

    # Produzione industriale YoY
    indpro = data.get('INDPRO', pd.Series())
    if not indpro.empty:
        ip_yoy = compute_indpro_yoy(indpro).dropna()
        if not ip_yoy.empty:
            z = zscore_series(ip_yoy, window)
            if not z.empty and not pd.isna(z.iloc[-1]):
                s = zscore_to_score(z.iloc[-1], invert=False)
                scores.append(s)
                indicators['Produzione Ind. YoY'] = {
                    'value': round(float(ip_yoy.iloc[-1]), 2),
                    'z': round(float(z.iloc[-1]), 2),
                    'score': round(s, 1),
                    'series': ip_yoy,
                    'z_series': z,
                    'unit': '%',
                    'desc': 'Crescita produzione industriale anno su anno'
                }

    # Disoccupazione variazione 3M
    unrate = data.get('UNRATE', pd.Series())
    if not unrate.empty:
        du = compute_unrate_3m_change(unrate).dropna()
        if not du.empty:
            z = zscore_series(du, window)
            if not z.empty and not pd.isna(z.iloc[-1]):
                s = zscore_to_score(z.iloc[-1], invert=True)  # disoc. scende = bull
                scores.append(s)
                indicators['Disoccupazione Δ3M'] = {
                    'value': round(float(du.iloc[-1]), 2),
                    'z': round(float(z.iloc[-1]), 2),
                    'score': round(s, 1),
                    'series': du,
                    'z_series': z,
                    'unit': 'pp',
                    'desc': 'Variazione disoccupazione su 3 mesi · negativo = bull'
                }

    pillar_score = float(np.mean(scores)) if scores else 50.0
    return round(pillar_score, 1), indicators

def score_pillar_fiscal(data, window=ZSCORE_WINDOW_MONTHS):
    """
    C. FISCALE
    - Deficit/PIL: espansione (deficit in crescita) = stimolo = bull breve, rischio LT
    - Impulso fiscale: positivo = espansivo = bull
    - Debito/PIL: alto e crescente = rischio LT
    """
    indicators = {}
    scores = []

    deficit = data.get('DEFICIT', pd.Series())
    debt_gdp = data.get('DEBT_GDP', pd.Series())

    # Deficit/PIL (annuale FYFSGDA188S: surplus se positivo, deficit se negativo)
    if not deficit.empty and len(deficit) >= 3:
        # Nota: la serie FRED è surplus/deficit - negativo = deficit
        impulse = compute_fiscal_impulse(deficit).dropna()
        if not impulse.empty:
            z = zscore_series(impulse, min(window, len(impulse)-1))
            if not z.empty and not pd.isna(z.iloc[-1]):
                # Impulso espansivo (deficit in aumento = più negativo → impulse negativo)
                # Invert: impulso espansivo = bull
                s = zscore_to_score(z.iloc[-1], invert=True)
                scores.append(s)
                indicators['Impulso Fiscale'] = {
                    'value': round(float(impulse.iloc[-1]), 2),
                    'z': round(float(z.iloc[-1]), 2),
                    'score': round(s, 1),
                    'series': impulse,
                    'z_series': z,
                    'unit': '%PIL',
                    'desc': 'Variazione YoY deficit/PIL · positivo = restrittivo · negativo = espansivo'
                }

        # Deficit livello attuale
        if not deficit.empty:
            last_deficit = float(deficit.iloc[-1])
            indicators['Deficit/PIL attuale'] = {
                'value': round(last_deficit, 1),
                'z': None,
                'score': None,
                'series': deficit,
                'z_series': None,
                'unit': '% PIL',
                'desc': 'Saldo primario / PIL · negativo = deficit · fonte: FRED FYFSGDA188S'
            }

    # Debito/PIL
    if not debt_gdp.empty and len(debt_gdp) >= 4:
        z = zscore_series(debt_gdp, min(window*3, len(debt_gdp)-1))
        if not z.empty and not pd.isna(z.iloc[-1]):
            # Debito alto = rischio LT → invert (alto debito = bear segnale)
            s = zscore_to_score(z.iloc[-1], invert=True)
            scores.append(s)
            indicators['Debito/PIL'] = {
                'value': round(float(debt_gdp.iloc[-1]), 1),
                'z': round(float(z.iloc[-1]), 2),
                'score': round(s, 1),
                'series': debt_gdp,
                'z_series': z,
                'unit': '%',
                'desc': 'Debito federale / PIL · alto e crescente = rischio sostenibilità LT'
            }

    pillar_score = float(np.mean(scores)) if scores else 50.0
    return round(pillar_score, 1), indicators

def score_pillar_productive(data, window=ZSCORE_WINDOW_MONTHS):
    """
    D. PRODUTTIVO
    - Capacity utilization: alto = economia tirata = pressione inflattiva
    - ULC YoY: basso = margini sani = bull
    - Output gap proxy: positivo = sopra potenziale
    """
    indicators = {}
    scores = []

    # Capacity utilization
    tcu = data.get('TCU', pd.Series())
    if not tcu.empty:
        z = zscore_series(tcu, window)
        if not z.empty and not pd.isna(z.iloc[-1]):
            s = zscore_to_score(z.iloc[-1], invert=False)
            scores.append(s)
            indicators['Capacity Utilization'] = {
                'value': round(float(tcu.iloc[-1]), 1),
                'z': round(float(z.iloc[-1]), 2),
                'score': round(s, 1),
                'series': tcu,
                'z_series': z,
                'unit': '%',
                'desc': 'Utilizzo capacità produttiva · alto = economia in piena capacità'
            }

    # Unit Labor Costs YoY
    ulc = data.get('ULC', pd.Series())
    if not ulc.empty:
        ulc_yoy = compute_yoy(ulc).dropna()
        if not ulc_yoy.empty:
            z = zscore_series(ulc_yoy, window)
            if not z.empty and not pd.isna(z.iloc[-1]):
                s = zscore_to_score(z.iloc[-1], invert=True)  # ULC basso = bull (meno inflazione)
                scores.append(s)
                indicators['Unit Labor Costs YoY'] = {
                    'value': round(float(ulc_yoy.iloc[-1]), 2),
                    'z': round(float(z.iloc[-1]), 2),
                    'score': round(s, 1),
                    'series': ulc_yoy,
                    'z_series': z,
                    'unit': '%',
                    'desc': 'Costi lavoro per unità prodotta · alto = pressione inflattiva sui margini'
                }

    # Output gap proxy
    indpro = data.get('INDPRO', pd.Series())
    if not indpro.empty and len(indpro) >= 36:
        gap = compute_output_gap_proxy(indpro)
        if not gap.empty:
            z = zscore_series(gap, window)
            if not z.empty and not pd.isna(z.iloc[-1]):
                s = zscore_to_score(z.iloc[-1], invert=False)
                scores.append(s)
                indicators['Output Gap (proxy)'] = {
                    'value': round(float(gap.iloc[-1]), 2),
                    'z': round(float(z.iloc[-1]), 2),
                    'score': round(s, 1),
                    'series': gap,
                    'z_series': z,
                    'unit': '%',
                    'desc': 'Deviazione produzione da trend · positivo = sopra potenziale'
                }

    pillar_score = float(np.mean(scores)) if scores else 50.0
    return round(pillar_score, 1), indicators

def score_pillar_geopolitical(mkt_data, gpr_manual, window_days=756):
    """
    E. GEOPOLITICO
    - GPR Index: basso = tranquillo = bull → invert
    - Oil price z-score: alto = stress = bear → invert
    - EEM performance 3M: positivo = EM stabile = bull
    """
    indicators = {}
    scores = []

    # GPR (manuale)
    if gpr_manual is not None:
        gpr_score = min(100, max(0, 100 - (gpr_manual / 400 * 100)))
        scores.append(gpr_score)
        gpr_level = "BASSO" if gpr_manual < 80 else ("MEDIO" if gpr_manual < 150 else "ALTO")
        indicators['GPR Index'] = {
            'value': gpr_manual,
            'z': round((gpr_manual - 100) / 50, 2),
            'score': round(gpr_score, 1),
            'series': None,
            'z_series': None,
            'unit': '',
            'desc': f'Geopolitical Risk Index · media storica ~100 · attuale: {gpr_level}'
        }

    # Oil price z-score (proxy tensioni geopolitiche)
    oil = mkt_data.get('OIL')
    if oil is not None and len(oil) >= 60:
        window = min(window_days, len(oil)-10)
        z = zscore_series(oil, window)
        if not z.empty and not pd.isna(z.iloc[-1]):
            s = zscore_to_score(z.iloc[-1], invert=True)  # petrolio alto = stress = bear
            scores.append(s)
            indicators['Oil Price (WTI)'] = {
                'value': round(float(oil.iloc[-1]), 1),
                'z': round(float(z.iloc[-1]), 2),
                'score': round(s, 1),
                'series': oil,
                'z_series': z,
                'unit': '$',
                'desc': 'Prezzo petrolio WTI · alto e crescente = rischio geopolitico/inflattivo'
            }

    # EEM performance 3M (proxy stress EM)
    eem = mkt_data.get('EEM')
    if eem is not None and len(eem) >= 63:
        eem_3m = float(eem.iloc[-1] / eem.iloc[-63] - 1) * 100
        eem_score = min(100, max(0, (eem_3m + 20) / 40 * 100))
        scores.append(eem_score)
        indicators['EEM Perf. 3M'] = {
            'value': round(eem_3m, 1),
            'z': round(eem_3m / 10, 2),
            'score': round(eem_score, 1),
            'series': None,
            'z_series': None,
            'unit': '%',
            'desc': 'Performance ETF EM 3 mesi · positivo = mercati EM stabili'
        }

    pillar_score = float(np.mean(scores)) if scores else 50.0
    return round(pillar_score, 1), indicators

def compute_regime(growth_score, inflation_score):
    """
    Mappa 4 regimi macro usando Growth score e Inflation score.
    Growth = media (Real Economy + Productive)
    Inflation = 100 - (Monetary) perché alta liquidità → alta inflazione potenziale
    """
    high_growth    = growth_score >= 50
    high_inflation = inflation_score >= 50

    if high_growth and not high_inflation:
        return "GOLDILOCKS", CYAN, "Crescita senza inflazione — ottimale per equity"
    elif high_growth and high_inflation:
        return "INFLATIONARY BOOM", AMBER, "Crescita con inflazione — favorevole a real assets e commodities"
    elif not high_growth and high_inflation:
        return "STAGFLATION", RED, "Bassa crescita + alta inflazione — peggiore scenario"
    else:
        return "DISINFLATIONARY BUST", BLUE, "Bassa crescita + bassa inflazione — favorevole a bond"

# ============================================================================
# SESSION STATE
# ============================================================================
defaults = {
    'pmi_composite': 51.5,
    'gpr_index': 105,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ============================================================================
# SIDEBAR
# ============================================================================
with st.sidebar:
    st.markdown(
        '<div style="font-family:Syne;font-size:1.1rem;font-weight:800;color:#00f5c4;letter-spacing:-0.5px;">🧭 MACRO CORE ENGINE</div>',
        unsafe_allow_html=True)
    st.markdown(
        '<div style="font-size:0.58rem;letter-spacing:3px;color:#4a6070;text-transform:uppercase;margin-bottom:16px;">Macro Regime Monitor v1.0</div>',
        unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section">📊 PMI Composito</div>', unsafe_allow_html=True)
    st.markdown(
        '<div style="font-size:0.65rem;color:#8ab0c8;line-height:1.8;margin-bottom:6px;">'
        'Fonte: ISM Manufacturing/Services<br>'
        'oppure S&P Global PMI Composite<br>'
        '<b>Aggiorna mensile</b></div>', unsafe_allow_html=True)
    pmi = st.number_input("PMI Composito USA", min_value=20.0, max_value=80.0,
                           value=float(st.session_state['pmi_composite']), step=0.1,
                           key='pmi_composite', format="%.1f")

    st.markdown('<div class="sidebar-section">🌍 GPR Index</div>', unsafe_allow_html=True)
    st.markdown(
        '<div style="font-size:0.65rem;color:#8ab0c8;line-height:1.8;margin-bottom:6px;">'
        'Fonte: geopoliticalrisk.com<br>'
        'Media storica ~100 · Crisi: >200<br>'
        '<b>Aggiorna mensile</b></div>', unsafe_allow_html=True)
    gpr = st.number_input("GPR Index (Geopolitical Risk)", min_value=0, max_value=500,
                           value=int(st.session_state['gpr_index']), step=5,
                           key='gpr_index')

    st.markdown('<div class="sidebar-section">⚙️ Impostazioni</div>', unsafe_allow_html=True)
    zscore_years = st.selectbox("Finestra Z-Score", [2, 3, 5], index=1,
                                 help="Anni di storia per normalizzazione z-score")
    show_zscore = st.checkbox("Mostra z-score nei grafici", value=True)

    if st.button("🔄 Aggiorna Dati FRED", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    st.markdown(
        '<div style="font-size:0.55rem;color:#4a6070;line-height:1.8;">'
        'Auto FRED: M2, GDP, Real Yield, HY OAS, INDPRO, UNRATE, Deficit, Debt/GDP, TCU, ULC<br>'
        'Auto yfinance: OIL, EEM, DXY, VIX<br>'
        'Manuale: PMI, GPR Index<br>'
        'Cache: 6h FRED · 4h market</div>', unsafe_allow_html=True)

# ============================================================================
# LOAD DATA
# ============================================================================
ZSCORE_WINDOW = zscore_years * 12

with st.spinner("Caricamento dati FRED e mercati..."):
    fred_data = load_all_fred()
    mkt_data  = load_market_data()

# ============================================================================
# COMPUTE SCORES
# ============================================================================
score_A, ind_A = score_pillar_monetary(fred_data, ZSCORE_WINDOW)
score_B, ind_B = score_pillar_real_economy(fred_data, pmi, ZSCORE_WINDOW)
score_C, ind_C = score_pillar_fiscal(fred_data, ZSCORE_WINDOW)
score_D, ind_D = score_pillar_productive(fred_data, ZSCORE_WINDOW)
score_E, ind_E = score_pillar_geopolitical(mkt_data, gpr)

# Regime
growth_score    = np.mean([score_B, score_D])
inflation_proxy = 100 - score_A  # alta liquidità → rischio inflazione
regime_name, regime_color, regime_desc = compute_regime(growth_score, inflation_proxy)

composite = np.mean([score_A, score_B, score_C, score_D, score_E])

# ============================================================================
# HEADER
# ============================================================================
st.markdown('<div class="main-title">🧭 Macro Core Engine</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Regime Macro Monitor · 5 Pilastri · FRED API + Manual Input</div>', unsafe_allow_html=True)
now_str = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
st.markdown(
    f'<div style="font-size:0.58rem;color:#4a6070;letter-spacing:2px;text-align:right;margin-bottom:16px;">'
    f'Last update: {now_str} · Z-score window: {zscore_years}Y</div>',
    unsafe_allow_html=True)

# ============================================================================
# TABS
# ============================================================================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🧭 Regime Overview",
    "💰 Monetario",
    "📈 Economia Reale",
    "🏛️ Fiscale + Produttivo",
    "🌍 Geopolitico",
    "📖 Metodologia",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 · REGIME OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown('<div class="section-label">Composite Score & Regime Macro</div>', unsafe_allow_html=True)

    # Top row: regime + composite
    col_reg, col_comp = st.columns([2, 3])

    with col_reg:
        reg_bg = {CYAN: "#0a1a14", AMBER: "#1a150a", RED: "#1a0a0a", BLUE: "#0a0f1a"}[regime_color]
        st.markdown(f"""
        <div style="background:{reg_bg};border:2px solid {regime_color};border-radius:8px;
                    padding:24px;text-align:center;margin-bottom:12px">
          <div style="font-size:0.58rem;letter-spacing:3px;color:{MUTED};text-transform:uppercase;margin-bottom:8px">
            Regime Corrente
          </div>
          <div style="font-family:Syne;font-size:1.5rem;font-weight:800;color:{regime_color};line-height:1.1">
            {regime_name}
          </div>
          <div style="font-size:0.65rem;color:#8ab0c8;margin-top:10px;line-height:1.7">
            {regime_desc}
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Growth vs Inflation quadrant mini-map
        st.markdown(f"""
        <div style="background:#080e14;border:1px solid #1c2a3a;border-radius:6px;padding:12px;margin-top:8px">
          <div style="font-size:0.55rem;letter-spacing:3px;color:#4a6070;text-transform:uppercase;margin-bottom:10px">
            Mappa Quadranti
          </div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;font-size:0.58rem">
            <div style="padding:8px;border-radius:4px;border:1px solid;text-align:center;
                        {'border-color:#00f5c4;background:rgba(0,245,196,0.12);color:#00f5c4' if regime_name=='GOLDILOCKS' else 'border-color:#1c2a3a;color:#4a6070'}">
              🟢 GOLDILOCKS<br><span style="font-size:0.5rem">↑ Crescita · ↓ Inflaz</span>
            </div>
            <div style="padding:8px;border-radius:4px;border:1px solid;text-align:center;
                        {'border-color:#f5a623;background:rgba(245,166,35,0.12);color:#f5a623' if regime_name=='INFLATIONARY BOOM' else 'border-color:#1c2a3a;color:#4a6070'}">
              🟡 INFL. BOOM<br><span style="font-size:0.5rem">↑ Crescita · ↑ Inflaz</span>
            </div>
            <div style="padding:8px;border-radius:4px;border:1px solid;text-align:center;
                        {'border-color:#4da6ff;background:rgba(77,166,255,0.12);color:#4da6ff' if regime_name=='DISINFLATIONARY BUST' else 'border-color:#1c2a3a;color:#4a6070'}">
              🔵 DISINFL. BUST<br><span style="font-size:0.5rem">↓ Crescita · ↓ Inflaz</span>
            </div>
            <div style="padding:8px;border-radius:4px;border:1px solid;text-align:center;
                        {'border-color:#ff4d6d;background:rgba(255,77,109,0.12);color:#ff4d6d' if regime_name=='STAGFLATION' else 'border-color:#1c2a3a;color:#4a6070'}">
              🔴 STAGFLATION<br><span style="font-size:0.5rem">↓ Crescita · ↑ Inflaz</span>
            </div>
          </div>
          <div style="font-size:0.52rem;color:#4a6070;margin-top:8px;text-align:center">
            Growth score: {growth_score:.0f}/100 · Inflation proxy: {inflation_proxy:.0f}/100
          </div>
        </div>
        """, unsafe_allow_html=True)

    with col_comp:
        # 5 pillar scores bar chart
        pillar_names  = ['A · Monetario', 'B · Econ. Reale', 'C · Fiscale', 'D · Produttivo', 'E · Geopolitico']
        pillar_scores = [score_A, score_B, score_C, score_D, score_E]
        bar_colors    = [score_color(s) for s in pillar_scores]

        fig_bars = go.Figure()
        fig_bars.add_trace(go.Bar(
            x=pillar_names,
            y=pillar_scores,
            marker_color=bar_colors,
            text=[f"{s:.0f}" for s in pillar_scores],
            textposition="outside",
            textfont=dict(size=11, color=TEXT_COL),
        ))
        fig_bars.add_hline(y=60, line_dash="dot", line_color=CYAN, line_width=1,
                           annotation_text="Bull", annotation_position="right",
                           annotation_font=dict(color=CYAN, size=9))
        fig_bars.add_hline(y=40, line_dash="dot", line_color=RED, line_width=1,
                           annotation_text="Bear", annotation_position="right",
                           annotation_font=dict(color=RED, size=9))
        fig_bars.add_hline(y=float(composite), line_dash="solid", line_color=AMBER, line_width=2,
                           annotation_text=f"Composite: {composite:.0f}", annotation_position="right",
                           annotation_font=dict(color=AMBER, size=10))
        fig_bars.update_layout(
            **base_layout("Score per Pilastro (0–100)", 320),
            yaxis=dict(range=[0, 110], gridcolor=GRID_COL),
            showlegend=False,
        )
        st.plotly_chart(fig_bars, use_container_width=True, config={"displayModeBar": False})

        # Composite summary tiles
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(tile_html("COMPOSITE SCORE", f"{composite:.0f}/100",
                                   f"Media 5 pilastri", score_pill(composite).lower().replace("neutral","amber"),
                                   score_pill(composite)), unsafe_allow_html=True)
        with c2:
            st.markdown(tile_html("GROWTH SCORE", f"{growth_score:.0f}/100",
                                   "Econ.Reale + Produttivo", "blue"), unsafe_allow_html=True)
        with c3:
            st.markdown(tile_html("INFLATION PROXY", f"{inflation_proxy:.0f}/100",
                                   "100 - Monetario", "amber"), unsafe_allow_html=True)

    # Asset class implications
    st.markdown('<div class="section-label">Implicazioni per Asset Class</div>', unsafe_allow_html=True)

    implications = {
        "GOLDILOCKS": {
            "Equity": ("✅ FAVOREVOLE", CYAN, "Crescita utili senza pressioni tassi"),
            "Bond":   ("⚡ NEUTRALE",   AMBER, "Tassi stabili, carry ok ma non eccezionale"),
            "Commodity": ("⚠️ PRUDENZA", AMBER, "Domanda ok ma niente inflazione"),
            "Cash":   ("❌ EVITARE",    RED,   "Costo opportunità troppo alto"),
        },
        "INFLATIONARY BOOM": {
            "Equity": ("⚡ SELETTIVO",  AMBER, "Favorisce value/energy vs growth"),
            "Bond":   ("❌ NEGATIVO",   RED,   "Tassi in salita = duration under pressure"),
            "Commodity": ("✅ OTTIMALE", CYAN, "Petrolio, metalli, soft commodities"),
            "Cash":   ("⚡ NEUTRALE",   AMBER, "Tassi reali ancora negativi"),
        },
        "STAGFLATION": {
            "Equity": ("❌ NEGATIVO",   RED,   "Margini compressi + multipli sotto pressione"),
            "Bond":   ("❌ NEGATIVO",   RED,   "Inflazione erode valore reale"),
            "Commodity": ("✅ PARZIALE", AMBER, "Commodity energia si difende"),
            "Cash":   ("✅ RELATIVO",   CYAN,  "Tassi nominali alti ma reali negativi"),
        },
        "DISINFLATIONARY BUST": {
            "Equity": ("⚠️ DIFENSIVO",  AMBER, "Preferire settori difensivi e qualità"),
            "Bond":   ("✅ OTTIMALE",   CYAN,  "Duration lunga beneficia di cali tassi"),
            "Commodity": ("❌ NEGATIVO", RED,   "Domanda debole = prezzi sotto pressione"),
            "Cash":   ("⚡ NEUTRALE",   AMBER, "Rendimento reale positivo ma transitorio"),
        },
    }

    impl = implications.get(regime_name, implications["GOLDILOCKS"])
    cc1, cc2, cc3, cc4 = st.columns(4)
    for col, (asset, (label, color, desc)) in zip([cc1, cc2, cc3, cc4], impl.items()):
        with col:
            bg = f"rgba({','.join(str(int(color[i:i+2],16)) for i in (1,3,5))},0.08)"
            col.markdown(f"""
            <div style="background:{bg};border:1px solid {color};border-radius:6px;
                        padding:14px;text-align:center;margin-bottom:8px">
              <div style="font-size:0.58rem;letter-spacing:2px;color:{MUTED};margin-bottom:6px">{asset.upper()}</div>
              <div style="font-family:Syne;font-size:0.85rem;font-weight:700;color:{color}">{label}</div>
              <div style="font-size:0.6rem;color:#8ab0c8;margin-top:6px;line-height:1.6">{desc}</div>
            </div>
            """, unsafe_allow_html=True)

    # Radar chart
    st.markdown('<div class="section-label">Radar — Profilo Macro Corrente</div>', unsafe_allow_html=True)
    fig_radar = go.Figure()
    categories = ['Monetario', 'Econ. Reale', 'Fiscale', 'Produttivo', 'Geopolitico']
    vals = [score_A, score_B, score_C, score_D, score_E]
    vals_closed = vals + [vals[0]]
    cats_closed = categories + [categories[0]]

    fig_radar.add_trace(go.Scatterpolar(
        r=vals_closed, theta=cats_closed,
        fill='toself', fillcolor='rgba(0,245,196,0.08)',
        line=dict(color=CYAN, width=2),
        name='Score Attuale'
    ))
    fig_radar.add_trace(go.Scatterpolar(
        r=[50]*6, theta=cats_closed,
        line=dict(color=AMBER, width=1, dash='dot'),
        name='Neutro (50)'
    ))
    fig_radar.update_layout(
        polar=dict(
            bgcolor=PLOT_BG,
            radialaxis=dict(visible=True, range=[0, 100], gridcolor=GRID_COL,
                           tickfont=dict(size=8, color=MUTED)),
            angularaxis=dict(gridcolor=GRID_COL, tickfont=dict(size=10, color=TEXT_COL)),
        ),
        paper_bgcolor=PAPER_BG,
        plot_bgcolor=PLOT_BG,
        font=dict(family="Space Mono", color=TEXT_COL),
        height=380,
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=9)),
        margin=dict(l=60, r=60, t=40, b=40),
    )
    st.plotly_chart(fig_radar, use_container_width=True, config={"displayModeBar": False})


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 · MONETARIO
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown('<div class="section-label">Pilastro A · Monetario — Liquidità, Costo del Denaro, Credito</div>', unsafe_allow_html=True)

    col_sc, col_det = st.columns([1, 3])
    with col_sc:
        color_a = score_color(score_A)
        st.markdown(f"""
        <div style="background:#080e14;border:2px solid {color_a};border-radius:8px;
                    padding:20px;text-align:center">
          <div style="font-size:0.55rem;letter-spacing:3px;color:{MUTED}">SCORE PILASTRO A</div>
          <div style="font-family:Syne;font-size:3rem;font-weight:800;color:{color_a}">{score_A:.0f}</div>
          <div style="font-size:0.6rem;color:#4a6070">/100</div>
          <div style="margin-top:10px">{signal_pill(score_pill(score_A))}</div>
        </div>
        """, unsafe_allow_html=True)

        for name, ind in ind_A.items():
            z_str = f"z={ind['z']:+.2f}" if ind['z'] is not None else ""
            col = score_color(ind['score']) if ind['score'] else AMBER
            st.markdown(f"""
            <div style="background:#0a0f18;border:1px solid #1c2a3a;border-radius:4px;
                        padding:10px 12px;margin-top:8px">
              <div style="font-size:0.55rem;color:{MUTED};letter-spacing:2px">{name.upper()}</div>
              <div style="font-family:Syne;font-size:1.1rem;color:{col};font-weight:700">
                {ind['value']}{ind['unit']}
              </div>
              <div style="font-size:0.55rem;color:#4a6070">{z_str} · score {ind['score']:.0f}/100</div>
            </div>
            """, unsafe_allow_html=True)

    with col_det:
        n_charts = sum(1 for ind in ind_A.values() if ind['series'] is not None)
        if n_charts > 0:
            fig_mon = make_subplots(rows=n_charts, cols=1, vertical_spacing=0.08,
                                     subplot_titles=[n for n, ind in ind_A.items() if ind['series'] is not None])
            row = 1
            for name, ind in ind_A.items():
                if ind['series'] is None: continue
                s = ind['series']
                fig_mon.add_trace(go.Scatter(x=s.index, y=s.values, name=name,
                                              line=dict(color=score_color(ind['score']), width=1.8)),
                                   row=row, col=1)
                if show_zscore and ind['z_series'] is not None:
                    zs = ind['z_series']
                    # Normalizza z-score all'asse del dato per overlay visivo
                    pass
                add_percentile_bands(fig_mon, s, row=row, col=1)
                row += 1

            fig_mon.update_layout(**base_layout("", 280 * n_charts))
            fig_mon.update_layout(paper_bgcolor=PAPER_BG, plot_bgcolor=PLOT_BG)
            for i in range(1, n_charts + 1):
                fig_mon.update_xaxes(gridcolor=GRID_COL, row=i, col=1)
                fig_mon.update_yaxes(gridcolor=GRID_COL, row=i, col=1)
            st.plotly_chart(fig_mon, use_container_width=True, config={"displayModeBar": False})

    # Z-score panel
    if show_zscore:
        st.markdown('<div class="section-label">Z-Score Panel — Monetario</div>', unsafe_allow_html=True)
        fig_z = go.Figure()
        colors_z = [CYAN, AMBER, RED]
        for i, (name, ind) in enumerate(ind_A.items()):
            if ind['z_series'] is not None:
                fig_z.add_trace(go.Scatter(x=ind['z_series'].index, y=ind['z_series'].values,
                                            name=name, line=dict(color=colors_z[i % 3], width=1.5)))
        fig_z.add_hline(y=0, line_dash="solid", line_color=GRID_COL, line_width=1)
        fig_z.add_hline(y=1.5, line_dash="dot", line_color=CYAN, line_width=1,
                        annotation_text="+1.5σ", annotation_position="right",
                        annotation_font=dict(color=CYAN, size=8))
        fig_z.add_hline(y=-1.5, line_dash="dot", line_color=RED, line_width=1,
                        annotation_text="-1.5σ", annotation_position="right",
                        annotation_font=dict(color=RED, size=8))
        fig_z.update_layout(**base_layout("Z-Score indicatori monetari", 280))
        st.plotly_chart(fig_z, use_container_width=True, config={"displayModeBar": False})

    # Interpretazione
    with st.expander("📖 Interpretazione Pilastro Monetario"):
        st.markdown(f"""
        **M2/PIL:** Misura quanta liquidità c'è in sistema rispetto alla dimensione dell'economia.
        Valori elevati indicano eccesso di moneta — favorevole agli asset nel breve ma potenzialmente inflattivo.
        **Score attuale:** {ind_A.get('M2/PIL', {}).get('score', 'N/A')}

        **Real Yield 10Y (DFII10):** Rendimento reale dei Treasury. Negativo = politica accomodante, 
        favorevole a equity e commodities. Positivo e in salita = pressure sui multipli.
        **Valore attuale:** {ind_A.get('Real Yield 10Y', {}).get('value', 'N/A')}%

        **HY Credit Spread (BAMLH0A0HYM2):** Spread High Yield. Basso = mercato del credito sereno, 
        nessuno stress sistemico. In salita rapida = segnale di risk-off.
        **Valore attuale:** {ind_A.get('HY Credit Spread', {}).get('value', 'N/A')}bp
        """)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 · ECONOMIA REALE
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown('<div class="section-label">Pilastro B · Economia Reale — Ciclo, Occupazione, Domanda</div>', unsafe_allow_html=True)

    col_sc, col_det = st.columns([1, 3])
    with col_sc:
        color_b = score_color(score_B)
        st.markdown(f"""
        <div style="background:#080e14;border:2px solid {color_b};border-radius:8px;
                    padding:20px;text-align:center">
          <div style="font-size:0.55rem;letter-spacing:3px;color:{MUTED}">SCORE PILASTRO B</div>
          <div style="font-family:Syne;font-size:3rem;font-weight:800;color:{color_b}">{score_B:.0f}</div>
          <div style="font-size:0.6rem;color:#4a6070">/100</div>
          <div style="margin-top:10px">{signal_pill(score_pill(score_B))}</div>
        </div>
        """, unsafe_allow_html=True)

        for name, ind in ind_B.items():
            z_str = f"z={ind['z']:+.2f}" if ind['z'] is not None else ""
            col = score_color(ind['score']) if ind['score'] else AMBER
            st.markdown(f"""
            <div style="background:#0a0f18;border:1px solid #1c2a3a;border-radius:4px;
                        padding:10px 12px;margin-top:8px">
              <div style="font-size:0.55rem;color:{MUTED};letter-spacing:2px">{name.upper()}</div>
              <div style="font-family:Syne;font-size:1.1rem;color:{col};font-weight:700">
                {ind['value']}{ind['unit']}
              </div>
              <div style="font-size:0.55rem;color:#4a6070">{z_str} · score {ind['score']:.0f}/100</div>
            </div>
            """, unsafe_allow_html=True)

    with col_det:
        # Charts INDPRO + UNRATE
        indpro = fred_data.get('INDPRO', pd.Series())
        unrate = fred_data.get('UNRATE', pd.Series())

        n_plots = sum([not indpro.empty, not unrate.empty])
        if n_plots > 0:
            subtitles = []
            if not indpro.empty: subtitles.append("Produzione Industriale (indice)")
            if not unrate.empty: subtitles.append("Tasso di Disoccupazione (%)")

            fig_re = make_subplots(rows=max(n_plots,1), cols=1, vertical_spacing=0.10,
                                    subplot_titles=subtitles)
            row = 1
            if not indpro.empty:
                ip_yoy = compute_indpro_yoy(indpro)
                fig_re.add_trace(go.Scatter(x=indpro.index, y=indpro.values,
                                             name="INDPRO", line=dict(color=CYAN, width=1.5)),
                                  row=row, col=1)
                row += 1
            if not unrate.empty:
                fig_re.add_trace(go.Scatter(x=unrate.index, y=unrate.values,
                                             name="UNRATE", line=dict(color=AMBER, width=1.5),
                                             fill='tozeroy', fillcolor='rgba(245,166,35,0.06)'),
                                  row=row, col=1)

            fig_re.update_layout(**base_layout("", 260 * n_plots))
            fig_re.update_layout(paper_bgcolor=PAPER_BG, plot_bgcolor=PLOT_BG)
            for i in range(1, n_plots + 1):
                fig_re.update_xaxes(gridcolor=GRID_COL, row=i, col=1)
                fig_re.update_yaxes(gridcolor=GRID_COL, row=i, col=1)
            st.plotly_chart(fig_re, use_container_width=True, config={"displayModeBar": False})

    # PMI gauge
    st.markdown('<div class="section-label">PMI Composito — Input Manuale</div>', unsafe_allow_html=True)
    pmi_color = CYAN if pmi > 52 else (RED if pmi < 48 else AMBER)
    pmi_label = "ESPANSIONE" if pmi > 52 else ("CONTRAZIONE" if pmi < 48 else "NEUTRO")
    st.markdown(f"""
    <div style="background:#080e14;border:1px solid #1c2a3a;border-radius:6px;padding:16px 20px">
      <div style="display:flex;align-items:center;gap:24px">
        <div style="text-align:center">
          <div style="font-size:0.55rem;letter-spacing:3px;color:{MUTED}">PMI COMPOSITO USA</div>
          <div style="font-family:Syne;font-size:3.5rem;font-weight:800;color:{pmi_color}">{pmi:.1f}</div>
          <div style="font-size:0.7rem;color:{pmi_color};font-weight:700">{pmi_label}</div>
        </div>
        <div style="flex:1;font-size:0.65rem;color:#8ab0c8;line-height:2">
          <b style="color:{TEXT_COL}">Soglie:</b><br>
          <span style="color:{CYAN}">▶ &gt;52: espansione solida</span><br>
          <span style="color:{AMBER}">▶ 48–52: zona neutra / transizione</span><br>
          <span style="color:{RED}">▶ &lt;48: contrazione</span><br><br>
          <span style="color:#4a6070">Fonte: ISM o S&P Global PMI · aggiorna mensile dalla sidebar</span>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # YoY produzione
    if not indpro.empty:
        ip_yoy = compute_indpro_yoy(indpro).dropna()
        if not ip_yoy.empty:
            st.markdown('<div class="section-label">Produzione Industriale YoY%</div>', unsafe_allow_html=True)
            yoy_colors = [CYAN if v > 0 else RED for v in ip_yoy.values]
            fig_yoy = go.Figure()
            fig_yoy.add_trace(go.Bar(x=ip_yoy.index, y=ip_yoy.values,
                                      marker_color=yoy_colors, opacity=0.8, name="IP YoY%"))
            ma = ip_yoy.rolling(6).mean()
            fig_yoy.add_trace(go.Scatter(x=ma.index, y=ma.values, name="MA6M",
                                          line=dict(color=AMBER, width=1.5)))
            fig_yoy.add_hline(y=0, line_dash="solid", line_color=GRID_COL, line_width=1)
            fig_yoy.update_layout(**base_layout("Produzione Industriale — Variazione % Annua", 280))
            st.plotly_chart(fig_yoy, use_container_width=True, config={"displayModeBar": False})


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 · FISCALE + PRODUTTIVO
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    col_fisc, col_prod = st.columns(2)

    with col_fisc:
        st.markdown('<div class="section-label">Pilastro C · Fiscale</div>', unsafe_allow_html=True)
        color_c = score_color(score_C)
        st.markdown(f"""
        <div style="background:#080e14;border:2px solid {color_c};border-radius:6px;
                    padding:16px;text-align:center;margin-bottom:12px">
          <div style="font-size:0.55rem;letter-spacing:3px;color:{MUTED}">SCORE C</div>
          <div style="font-family:Syne;font-size:2.5rem;font-weight:800;color:{color_c}">{score_C:.0f}</div>
          <div style="margin-top:6px">{signal_pill(score_pill(score_C))}</div>
        </div>
        """, unsafe_allow_html=True)

        for name, ind in ind_C.items():
            if ind['score'] is None: continue
            col = score_color(ind['score'])
            st.markdown(f"""
            <div style="background:#0a0f18;border:1px solid #1c2a3a;border-radius:4px;
                        padding:10px 12px;margin-bottom:8px">
              <div style="font-size:0.55rem;color:{MUTED};letter-spacing:2px">{name.upper()}</div>
              <div style="font-family:Syne;font-size:1.1rem;color:{col};font-weight:700">
                {ind['value']}{ind['unit']}
              </div>
              <div style="font-size:0.55rem;color:#4a6070">{ind['desc']}</div>
            </div>
            """, unsafe_allow_html=True)

        # Grafici fiscali
        deficit = fred_data.get('DEFICIT', pd.Series())
        debt_gdp = fred_data.get('DEBT_GDP', pd.Series())

        if not deficit.empty:
            fig_def = go.Figure()
            def_colors = [CYAN if v > 0 else RED for v in deficit.values]
            fig_def.add_trace(go.Bar(x=deficit.index, y=deficit.values,
                                      marker_color=def_colors, name="Surplus/Deficit % PIL"))
            fig_def.add_hline(y=0, line_dash="solid", line_color=GRID_COL)
            fig_def.update_layout(**base_layout("Saldo Fiscale / PIL % (FYFSGDA188S)", 260))
            st.plotly_chart(fig_def, use_container_width=True, config={"displayModeBar": False})

        if not debt_gdp.empty:
            fig_debt = go.Figure()
            fig_debt.add_trace(go.Scatter(x=debt_gdp.index, y=debt_gdp.values,
                                           name="Debito/PIL", line=dict(color=AMBER, width=1.8),
                                           fill='tozeroy', fillcolor='rgba(245,166,35,0.06)'))
            fig_debt.update_layout(**base_layout("Debito Federale / PIL % (GFDEGDQ188S)", 260))
            st.plotly_chart(fig_debt, use_container_width=True, config={"displayModeBar": False})

    with col_prod:
        st.markdown('<div class="section-label">Pilastro D · Produttivo</div>', unsafe_allow_html=True)
        color_d = score_color(score_D)
        st.markdown(f"""
        <div style="background:#080e14;border:2px solid {color_d};border-radius:6px;
                    padding:16px;text-align:center;margin-bottom:12px">
          <div style="font-size:0.55rem;letter-spacing:3px;color:{MUTED}">SCORE D</div>
          <div style="font-family:Syne;font-size:2.5rem;font-weight:800;color:{color_d}">{score_D:.0f}</div>
          <div style="margin-top:6px">{signal_pill(score_pill(score_D))}</div>
        </div>
        """, unsafe_allow_html=True)

        for name, ind in ind_D.items():
            col = score_color(ind['score'])
            st.markdown(f"""
            <div style="background:#0a0f18;border:1px solid #1c2a3a;border-radius:4px;
                        padding:10px 12px;margin-bottom:8px">
              <div style="font-size:0.55rem;color:{MUTED};letter-spacing:2px">{name.upper()}</div>
              <div style="font-family:Syne;font-size:1.1rem;color:{col};font-weight:700">
                {ind['value']}{ind['unit']}
              </div>
              <div style="font-size:0.55rem;color:#4a6070">{ind['desc']}</div>
            </div>
            """, unsafe_allow_html=True)

        tcu = fred_data.get('TCU', pd.Series())
        ulc = fred_data.get('ULC', pd.Series())

        if not tcu.empty:
            fig_tcu = go.Figure()
            fig_tcu.add_trace(go.Scatter(x=tcu.index, y=tcu.values,
                                          name="TCU", line=dict(color=BLUE, width=1.8)))
            add_percentile_bands(fig_tcu, tcu)
            fig_tcu.add_hline(y=80, line_dash="dot", line_color=AMBER, line_width=1,
                              annotation_text="80% soglia alta", annotation_font=dict(color=AMBER, size=8))
            fig_tcu.update_layout(**base_layout("Capacity Utilization % (TCU)", 260))
            st.plotly_chart(fig_tcu, use_container_width=True, config={"displayModeBar": False})

        if not ulc.empty:
            ulc_yoy = compute_yoy(ulc).dropna()
            if not ulc_yoy.empty:
                ulc_colors = [RED if v > 3 else (AMBER if v > 1 else CYAN) for v in ulc_yoy.values]
                fig_ulc = go.Figure()
                fig_ulc.add_trace(go.Bar(x=ulc_yoy.index, y=ulc_yoy.values,
                                          marker_color=ulc_colors, name="ULC YoY%"))
                fig_ulc.add_hline(y=0, line_dash="solid", line_color=GRID_COL)
                fig_ulc.add_hline(y=3, line_dash="dot", line_color=RED, line_width=1,
                                  annotation_text="3% alert", annotation_font=dict(color=RED, size=8))
                fig_ulc.update_layout(**base_layout("Unit Labor Costs YoY% (ULCNFB)", 260))
                st.plotly_chart(fig_ulc, use_container_width=True, config={"displayModeBar": False})


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 · GEOPOLITICO
# ══════════════════════════════════════════════════════════════════════════════
with tab5:
    st.markdown('<div class="section-label">Pilastro E · Geopolitico — Rischio, Energia, Stress EM</div>', unsafe_allow_html=True)

    col_sc, col_det = st.columns([1, 3])
    with col_sc:
        color_e = score_color(score_E)
        st.markdown(f"""
        <div style="background:#080e14;border:2px solid {color_e};border-radius:8px;
                    padding:20px;text-align:center">
          <div style="font-size:0.55rem;letter-spacing:3px;color:{MUTED}">SCORE PILASTRO E</div>
          <div style="font-family:Syne;font-size:3rem;font-weight:800;color:{color_e}">{score_E:.0f}</div>
          <div style="font-size:0.6rem;color:#4a6070">/100</div>
          <div style="margin-top:10px">{signal_pill(score_pill(score_E))}</div>
        </div>
        """, unsafe_allow_html=True)

        for name, ind in ind_E.items():
            z_str = f"z={ind['z']:+.2f}" if ind['z'] is not None else ""
            col = score_color(ind['score'])
            st.markdown(f"""
            <div style="background:#0a0f18;border:1px solid #1c2a3a;border-radius:4px;
                        padding:10px 12px;margin-top:8px">
              <div style="font-size:0.55rem;color:{MUTED};letter-spacing:2px">{name.upper()}</div>
              <div style="font-family:Syne;font-size:1.1rem;color:{col};font-weight:700">
                {ind['value']}{ind['unit']}
              </div>
              <div style="font-size:0.55rem;color:#4a6070">{z_str} · score {ind['score']:.0f}/100</div>
            </div>
            """, unsafe_allow_html=True)

        # GPR panel
        gpr_color = CYAN if gpr < 80 else (AMBER if gpr < 150 else RED)
        gpr_level = "BASSO" if gpr < 80 else ("MEDIO" if gpr < 150 else "ELEVATO")
        st.markdown(f"""
        <div style="background:#0a0f18;border:1px solid {gpr_color};border-radius:4px;
                    padding:12px;margin-top:12px;text-align:center">
          <div style="font-size:0.55rem;color:{MUTED}">GPR INDEX</div>
          <div style="font-family:Syne;font-size:2rem;color:{gpr_color};font-weight:700">{gpr}</div>
          <div style="font-size:0.65rem;color:{gpr_color}">{gpr_level}</div>
          <div style="font-size:0.52rem;color:#4a6070;margin-top:4px">Media storica ~100</div>
        </div>
        """, unsafe_allow_html=True)

    with col_det:
        oil = mkt_data.get('OIL')
        eem = mkt_data.get('EEM')
        dxy = mkt_data.get('DXY')

        n_geo = sum([oil is not None, eem is not None, dxy is not None])
        if n_geo > 0:
            subtitles = []
            if oil is not None: subtitles.append("WTI Crude Oil ($)")
            if eem is not None: subtitles.append("EEM — Emerging Markets ETF")
            if dxy is not None: subtitles.append("DXY — Dollar Index")

            fig_geo = make_subplots(rows=n_geo, cols=1, vertical_spacing=0.08,
                                     subplot_titles=subtitles)
            row = 1
            if oil is not None:
                oil_1y = oil.last('365D')
                fig_geo.add_trace(go.Scatter(x=oil_1y.index, y=oil_1y.values,
                                              name="WTI", line=dict(color=AMBER, width=1.8)),
                                   row=row, col=1)
                add_percentile_bands(fig_geo, oil_1y, row=row, col=1)
                row += 1
            if eem is not None:
                eem_1y = eem.last('365D')
                fig_geo.add_trace(go.Scatter(x=eem_1y.index, y=eem_1y.values,
                                              name="EEM", line=dict(color=BLUE, width=1.8)),
                                   row=row, col=1)
                row += 1
            if dxy is not None:
                dxy_1y = dxy.last('365D')
                fig_geo.add_trace(go.Scatter(x=dxy_1y.index, y=dxy_1y.values,
                                              name="DXY", line=dict(color=CYAN, width=1.8)),
                                   row=row, col=1)

            fig_geo.update_layout(**base_layout("", 240 * n_geo))
            fig_geo.update_layout(paper_bgcolor=PAPER_BG, plot_bgcolor=PLOT_BG)
            for i in range(1, n_geo + 1):
                fig_geo.update_xaxes(gridcolor=GRID_COL, row=i, col=1)
                fig_geo.update_yaxes(gridcolor=GRID_COL, row=i, col=1)
            st.plotly_chart(fig_geo, use_container_width=True, config={"displayModeBar": False})


# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 · METODOLOGIA
# ══════════════════════════════════════════════════════════════════════════════
with tab6:
    st.markdown(f"""
    # 🧭 Macro Core Engine — Metodologia v1.0

    ## 1. Obiettivo
    Identificare il **regime macro corrente** attraverso 5 pilastri fondamentali, 
    con implicazioni operative per equity, bond, commodities e cash.
    Non è un sistema predittivo ma un **bussola diagnostica** per orientare 
    l'allocazione nei monitor di mercato esistenti.

    ## 2. I 5 Pilastri

    | Pilastro | Indicatori | Fonte | Frequenza |
    |----------|-----------|-------|-----------|
    | A · Monetario | M2/PIL, Real Yield 10Y, HY OAS | FRED | Mensile |
    | B · Econ. Reale | PMI, INDPRO YoY, Unemp. Δ3M | FRED + Manuale | Mensile |
    | C · Fiscale | Deficit/PIL, Impulso fiscale, Debito/PIL | FRED | Annuale/Trim. |
    | D · Produttivo | Capacity Utilization, ULC YoY, Output Gap | FRED | Mensile/Trim. |
    | E · Geopolitico | GPR Index, WTI, EEM 3M perf. | yfinance + Manuale | Mensile |

    ## 3. Metodologia Z-Score

    Ogni indicatore viene normalizzato con **z-score rolling** (finestra {zscore_years} anni):

    ```
    Z(t) = (X(t) - Media_rolling(t)) / StdDev_rolling(t)
    ```

    Il z-score viene poi convertito in **score 0-100** via sigmoid clippata:
    ```
    z_clipped = clip(z, -3, +3)
    score = (z_clipped + 3) / 6 × 100
    ```
    Per indicatori dove alto = bear (es. HY spread, ULC), si applica `invert=True`.

    ## 4. Score per Pilastro
    Media aritmetica degli score degli indicatori disponibili nel pilastro.
    - **Score ≥ 60** → BULL (verde)
    - **Score 40–60** → NEUTRAL (ambra)
    - **Score < 40** → BEAR (rosso)

    ## 5. Regime Macro — 4 Quadranti

    | Regime | Growth | Inflation | Favorevole a |
    |--------|--------|-----------|--------------|
    | 🟢 GOLDILOCKS | Alto | Basso | Equity growth |
    | 🟡 INFLATIONARY BOOM | Alto | Alto | Commodities, value |
    | 🔵 DISINFLATIONARY BUST | Basso | Basso | Bond duration |
    | 🔴 STAGFLATION | Basso | Alto | Cash, real assets |

    - **Growth Score** = media (Econ. Reale + Produttivo)
    - **Inflation Proxy** = 100 - Monetario (alta liquidità → rischio inflazione)

    ## 6. Dati Manuali da Aggiornare

    | Variabile | Fonte | Frequenza |
    |-----------|-------|-----------|
    | PMI Composito | ISM o S&P Global | Mensile (primo lun.) |
    | GPR Index | geopoliticalrisk.com | Mensile |

    ## 7. Serie FRED Utilizzate

    | Codice | Descrizione |
    |--------|-------------|
    | M2SL | M2 Money Stock |
    | GDP | GDP Nominale USA |
    | DFII10 | Real Yield 10Y |
    | BAMLH0A0HYM2 | HY OAS Spread |
    | INDPRO | Industrial Production Index |
    | UNRATE | Unemployment Rate |
    | FYFSGDA188S | Deficit/Surplus % PIL (annuale) |
    | GFDEGDQ188S | Debito Federale % PIL (trim.) |
    | TCU | Total Capacity Utilization |
    | ULCNFB | Unit Labor Costs Nonfarm |

    ## 8. Limiti del Modello
    - Dati FRED con lag variabile (1–45 giorni)
    - Il pilastro fiscale usa dati annuali → reattività ridotta
    - Z-score dipende dalla lunghezza della finestra scelta
    - Il regime macro è **lagging**, non leading — usarlo per conferma, non per timing
    - Combinare sempre con i segnali dei 4 monitor di mercato

    ---
    **Versione:** 1.0 · **Data:** {datetime.now().strftime('%d/%m/%Y')} · **FRED Key:** ...784
    
    *Non costituisce consulenza finanziaria.*
    """)

# ============================================================================
# FOOTER
# ============================================================================
st.markdown("---")
st.markdown(f"""
<div style='font-family:Space Mono,monospace;font-size:0.56rem;color:#4a6a80;text-align:center;line-height:2'>
  🧭 MACRO CORE ENGINE v1.0 · 5-Pillar Macro Regime Monitor<br>
  Auto: FRED API (M2, GDP, DFII10, HY OAS, INDPRO, UNRATE, Deficit, Debt, TCU, ULC) · yfinance (OIL, EEM, DXY)<br>
  Manuale: PMI Composito · GPR Index · Z-score window: {zscore_years}Y<br>
  Regime: {regime_name} · Composite: {composite:.0f}/100 · {now_str}
</div>
""", unsafe_allow_html=True)
