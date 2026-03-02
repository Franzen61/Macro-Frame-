import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from fredapi import Fred
import yfinance as yf
from datetime import datetime, timedelta

# --- CONFIGURAZIONE ---
ST_STYLE = {"cyan": "#00f5c4", "red": "#ff4d6d", "amber": "#f5a623", "blue": "#4da6ff", "bg": "#070b12"}
FRED_API_KEY = '938a76ed726e8351f43e1b0c36365784' 

st.set_page_config(page_title="MACRO TERMINAL PRO", layout="wide")

# --- ENGINE STATISTICO ---
def get_zscore(series, window=252*3): # 3 anni di lookback
    if len(series) < 60: return 0
    mean = series.rolling(window=window).mean()
    std = series.rolling(window=window).std()
    z = (series - mean) / std
    return z.iloc[-1]

def z_to_score(z, invert=False):
    # Trasforma uno Z-score (-3 a +3) in un punteggio 0-100
    val = -z if invert else z
    score = (val + 3) / 6 * 100
    return max(0, min(100, score))

# --- DATA LOADING ---
@st.cache_data(ttl=3600)
def fetch_data():
    fred = Fred(api_key=FRED_API_KEY)
    # Mapping: Nome -> (ID_FRED, Inverti_Zscore, Descrizione)
    metrics = {
        "M2_Velocity": ("MULT", False, "Velocità della moneta (GDP/M2)"),
        "Real_Yield": ("DFII10", True, "Tassi Reali 10Y (Inverso)"),
        "HY_Spread": ("BAMLH0A0HYM2", True, "Credit Stress (High Yield)"),
        "Ind_Prod": ("INDPRO", False, "Produzione Industriale YoY"),
        "Unemployment": ("UNRATE", True, "Tasso Disoccupazione (Inverso)"),
        "M2_Real": ("M2SL", False, "M2 Deflazionato (CPI)")
    }
    
    results = {}
    for name, (fid, inv, desc) in metrics.items():
        try:
            s = fred.get_series(fid, observation_start='2015-01-01')
            if name == "Ind_Prod" or name == "M2_Real":
                s = s.pct_change(12) * 100 # YoY %
            
            z = get_zscore(s.dropna())
            score = z_to_score(z, invert=inv)
            results[name] = {"val": s.iloc[-1], "z": z, "score": score, "desc": desc, "history": s}
        except:
            continue
            
    # Market Data
    mkt = yf.download(["^MOVE", "^VIX", "CL=F"], period="5y", progress=False)['Close']
    for col in mkt.columns:
        z = get_zscore(mkt[col].dropna())
        results[col] = {"val": mkt[col].iloc[-1], "z": z, "score": z_to_score(z, invert=True), "history": mkt[col]}
        
    return results

data = fetch_data()

# --- UI INTERFACE ---
st.title("🧭 MACRO CORE TERMINAL v2.5")
st.markdown("---")

# 1. TOP ROW: REGIME IDENTIFIER
c1, c2, c3 = st.columns([1, 1, 2])

# Calcolo Macro Quadrant
growth = np.mean([data['Ind_Prod']['score'], data['M2_Velocity']['score']])
inflation_risk = 100 - data['Real_Yield']['score']

with c1:
    st.metric("GROWTH SCORE", f"{growth:.1f}/100")
    st.progress(growth/100)

with c2:
    st.metric("INFLATION RISK", f"{inflation_risk:.1f}/100")
    st.progress(inflation_risk/100)

with c3:
    # Determinazione Regime Didascalico
    if growth > 55 and inflation_risk < 45: 
        regime, desc = "GOLDILOCKS", "Crescita robusta, inflazione bassa. Bullish per Equity e Bond."
    elif growth > 55 and inflation_risk > 55:
        regime, desc = "INFLATIONARY BOOM", "Surriscaldamento. Commodities UP, Bond BEARISH."
    elif growth < 45 and inflation_risk > 55:
        regime, desc = "STAGFLATION", "Il peggior scenario. Cash e Oro sono i rifugi."
    else:
        regime, desc = "DEFLATIONARY BUST", "Recessione. Bond governativi e Difensivi necessari."
        
    st.subheader(f"REGIME: {regime}")
    st.info(desc)

# 2. MIDDLE ROW: ANALISI DETTAGLIATA (Z-SCORES)
st.subheader("📊 Analisi Quantitativa degli Indicatori")
cols = st.columns(len(data))

for i, (name, info) in enumerate(data.items()):
    with st.container():
        color = ST_STYLE["cyan"] if info['score'] > 60 else ST_STYLE["red"] if info['score'] < 40 else ST_STYLE["amber"]
        st.markdown(f"""
        <div style="border-left: 5px solid {color}; padding-left: 10px; margin-bottom: 20px;">
            <p style="font-size: 0.8rem; color: gray; margin-bottom: 0;">{name.replace('_', ' ')}</p>
            <h3 style="margin-top: 0;">{info['val']:.2f}</h3>
            <p style="font-size: 0.85rem;">Z-Score: <b>{info['z']:.2f}</b></p>
        </div>
        """, unsafe_allow_html=True)

# 3. BOTTOM ROW: IL GRAFICO CHE MANCAVA (Visualizzatore di soglie)
st.subheader("📈 Analisi Storica e Soglie Critiche")
target_metric = st.selectbox("Seleziona indicatore da esplorare:", list(data.keys()))
hist_data = data[target_metric]['history'].dropna()

fig = go.Figure()
fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data.values, name="Valore Attuale", line=dict(color=ST_STYLE["cyan"], width=2)))
# Aggiunta medie e deviazioni
mean_val = hist_data.mean()
std_val = hist_data.std()

fig.add_hline(y=mean_val, line_dash="dash", line_color="white", annotation_text="Media")
fig.add_hline(y=mean_val + 2*std_val, line_dash="dot", line_color=ST_STYLE["red"], annotation_text="+2 STD (Extreme)")
fig.add_hline(y=mean_val - 2*std_val, line_dash="dot", line_color=ST_STYLE["red"], annotation_text="-2 STD (Extreme)")

fig.update_layout(
    template="plotly_dark", 
    paper_bgcolor="rgba(0,0,0,0)", 
    plot_bgcolor="rgba(0,0,0,0)",
    height=450,
    xaxis=dict(showgrid=False),
    yaxis=dict(gridcolor="#1c2a3a")
)
st.plotly_chart(fig, use_container_width=True)

st.markdown("""
### 📖 Guida alla lettura
* **Z-Score > 2.0 o < -2.0:** Il dato è in una condizione di eccesso statistico (95% di probabilità di rientro). Segnale di inversione imminente.
* **M2 Velocity:** Se sale, la moneta circola. Se scende sotto lo Z-score di -1.5, il rischio recessione è altissimo.
* **MOVE Index:** Sopra 120 indica instabilità sistemica nei titoli di stato.
""")
