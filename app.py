import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import datetime
import pytz

# ==========================================
# FASE 1: FUNDAÇÃO GOLD SUPREMO
# ==========================================
st.set_page_config(page_title="💰 GOLD SUPREMO", layout="wide", initial_sidebar_state="collapsed")

st.markdown("<h1 style='text-align: center; color: #B8860B;'>💰 GOLD SUPREMO - PURE ACTION 🤖</h1>", unsafe_allow_html=True)
st.divider()

# ==========================================
# FASE 2: MOTOR DE EXTRAÇÃO DE DADOS (COMEX)
# ==========================================
TICKER_OURO = "MGC=F"

@st.cache_data(ttl=60, show_spinner=False)
def buscar_dados_ouro(periodo="5d", intervalo="5m"):
    try:
        df = yf.download(tickers=[TICKER_OURO, "GC=F"], period=periodo, interval=intervalo, progress=False)
        
        if TICKER_OURO in df['Close']:
            dados = df.xs(TICKER_OURO, level=1, axis=1) if isinstance(df.columns, pd.MultiIndex) else df
        else:
            dados = df.xs("GC=F", level=1, axis=1) if isinstance(df.columns, pd.MultiIndex) else df
            
        dados = dados.dropna()
        if dados.empty: return None
        
        if dados.index.tz is None: dados.index = dados.index.tz_localize('UTC')
        dados.index = dados.index.tz_convert('America/New_York').tz_localize(None)
        
        return dados
    except Exception as e:
        return None

# ==========================================
# FASE 3: MATRIZ DE CONFLUÊNCIA TÉCNICA
# ==========================================
def calcular_indicadores(df):
    if df is None or len(df) < 200:
        return None
    
    df = df.copy()
    
    # 1. Filtro Direcional Imperativo (EMAs)
    df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()
    df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
    
    # 2. Oscilador de Exaustão (RSI 14)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI_14'] = 100 - (100 / (1 + rs))
    
    # 3. Aceleração e Momentum (MACD 12, 26, 9)
    ema_12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema_26 = df['Close'].ewm(span=26, adjust=False).mean()
    macd_line = ema_12 - ema_26
    macd_signal = macd_line.ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = macd_line - macd_signal
    
    # 4. Volatilidade e Proteção (ATR 14)
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR_14'] = tr.rolling(14).mean()
    
    return df

# ==========================================
# PAINEL DE COMANDO (UI)
# ==========================================
dados_ouro = buscar_dados_ouro()
dados_processados = calcular_indicadores(dados_ouro)

if dados_processados is not None:
    vela_atual = dados_processados.iloc[-1]
    
    st.success("⚙️ Matriz de Confluência calculada com sucesso!")
    
    st.subheader("📊 Raio-X Técnico (M5)")
    c1, c2, c3, c4 = st.columns(4)
    
    c1.metric("Preço Atual", f"${vela_atual['Close']:.2f}")
    c2.metric("EMA 200 (Tendência)", f"${vela_atual['EMA_200']:.2f}")
    c3.metric("RSI 14 (Exaustão)", f"{vela_atual['RSI_14']:.1f}")
    c4.metric("ATR 14 (Volatilidade)", f"${vela_atual['ATR_14']:.2f}")
    
    st.divider()
    st.info("🟢 O robô agora enxerga a tendência, o momentum e o risco de forma cristalina. Pronto para a Fase 4: O Reconhecimento de Candlesticks.")
else:
    st.error("❌ Falha ao processar os indicadores técnicos. Aguardando volume de dados suficiente...")
