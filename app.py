import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import datetime
import requests

# ==========================================
# FASE 1: FUNDAÇÃO GOLD SUPREMO
# ==========================================
st.set_page_config(page_title="💰 GOLD SUPREMO", layout="wide", initial_sidebar_state="collapsed")
st.markdown("<style>[data-testid='stMetricValue']{font-size: 1.4rem !important;}[data-testid='stMetricLabel']{font-size: 0.9rem !important;}</style>", unsafe_allow_html=True)

TICKER_OURO = "MGC=F"

# --- FUNÇÃO DE DISPARO TELEGRAM ---
def enviar_telegram(mensagem):
    try:
        if "telegram" not in st.secrets:
            return False
        token = st.secrets["telegram"]["token"]
        chat_id = st.secrets["telegram"]["chat_id"]
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": mensagem, "parse_mode": "Markdown"}
        requests.post(url, data=payload)
        return True
    except:
        return False

# ==========================================
# FASE 2: MOTOR DE EXTRAÇÃO DE DADOS (M5 PURO)
# ==========================================
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
    except:
        return None

# ==========================================
# FASE 6: QUAD-CHECK E TRACKER DE STATUS
# ==========================================
def calcular_motor_supremo(df):
    if df is None or len(df) < 200: return None # Aumentamos para 200 velas para calcular a SMA 200
    df = df.copy()
    
    # 1. Indicadores (Volatilidade e Volume)
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    df['ATR_14'] = np.max(pd.concat([high_low, high_close, low_close], axis=1), axis=1).rolling(14).mean()
    df['Vol_MA_20'] = df['Volume'].rolling(window=20).mean()

    # 2. NOVA ENGENHARIA DE MÉDIAS MÓVEIS (Conforme Doutrina Institucional)
    df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()   # Reatividade Ultrasensível
    df['EMA_21'] = df['Close'].ewm(span=21, adjust=False).mean() # Suporte Dinâmico Ativo
    df['SMA_50'] = df['Close'].rolling(window=50).mean()         # Fronteira Estrutural
    df['SMA_200'] = df['Close'].rolling(window=200).mean()       # Bússola Institucional Macro
    
    # 3. MACD Histograma (Mantido intacto por enquanto)
    fast_ema = df['Close'].ewm(span=9, adjust=False).mean()
    slow_ema = df['Close'].ewm(span=20, adjust=False).mean()
    df['Stor_Line'] = fast_ema - slow_ema
    df['Stor_Signal'] = df['Stor_Line'].ewm(span=18, adjust=False).mean()
    
    # 4. Geração de Sinais
    df['Padrao'] = "Nenhum"
    df['Sinal'] = "AGUARDANDO"
    df['Status'] = "-" 
    
    for i in range(2, len(df)):
        v1, v2 = df.iloc[i-2], df.iloc[i-1]
        o1, c1, h1, l1 = v1['Open'], v1['Close'], v1['High'], v1['Low']
        o2, c2, h2, l2 = v2['Open'], v2['Close'], v2['High'], v2['Low']
        
        atr_atual = v2['ATR_14']
        engolfo_alta = (c1 < o1) and (c2 > o2) and (c2 > o1) and (o2 < c1)
        engolfo_baixa = (c1 > o1) and (c2 < o2) and (o2 > c1) and (c2 < o1)
        distancia_stop = atr_atual * 1.5
        
        # Filtros de Tendência
        tendencia_micro_alta = v2['EMA_9'] > v2['EMA_21']
        tendencia_micro_baixa = v2['EMA_9'] < v2['EMA_21']
        tendencia_macro_alta = c2 > v2['SMA_200'] and v2['SMA_50'] > v2['SMA_200']
        tendencia_macro_baixa = c2 < v2['SMA_200'] and v2['SMA_50'] < v2['SMA_200']

        # GATILHO DE COMPRA (Engolfo + Micro Alta + Macro Alta + MACD + Volume)
        if engolfo_alta and tendencia_micro_alta and tendencia_macro_alta and v2['Stor_Line'] > v2['Stor_Signal'] and v2['Volume'] > v2['Vol_MA_20']:
            df.loc[df.index[i], 'Sinal'] = "COMPRA"
            df.loc[df.index[i], 'Padrao'] = "Engolfo de Alta"
            df.loc[df.index[i], 'Entrada'] = c2
            sl = min(l1, l2) - distancia_stop
            df.loc[df.index[i], 'Stop_Loss'] = sl
            df.loc[df.index[i], 'TP1'] = c2 + ((c2 - sl) * 1.5)
            df.loc[df.index[i], 'TP2'] = c2 + ((c2 - sl) * 2.0)
            
        # GATILHO DE VENDA (Engolfo + Micro Baixa + Macro Baixa + MACD + Volume)
        elif engolfo_baixa and tendencia_micro_baixa and tendencia_macro_baixa and v2['Stor_Line'] < v2['Stor_Signal'] and v2['Volume'] > v2['Vol_MA_20']:
            df.loc[df.index[i], 'Sinal'] = "VENDA"
            df.loc[df.index[i], 'Padrao'] = "Engolfo de Baixa"
            df.loc[df.index[i], 'Entrada'] = c2
            sl = max(h1, h2) + distancia_stop
            df.loc[df.index[i], 'Stop_Loss'] = sl
            df.loc[df.index[i], 'TP1'] = c2 - ((sl - c2) * 1.5)
            df.loc[df.index[i], 'TP2'] = c2 - ((sl - c2) * 2.0)

    # ... (O restante do código do Scanner de Desfecho/Viajante do Tempo continua exatamente igual aqui para baixo) ...
# ==========================================
# PAINEL DE COMANDO (UI)
# ==========================================
st.markdown("<h2 style='text-align: center; color: #B8860B;'>💰 GOLD SUPREMO - PURE ACTION 🤖</h2>", unsafe_allow_html=True)

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    # DATA LIMPA: Travada para hoje (limpa o histórico das semanas anteriores)
    data_inicio = st.date_input("📅 Data de Início do Forward Test", datetime.date.today())

@st.fragment(run_every="20s")
def renderizar_motor():
    df_cru = buscar_dados_ouro("5d", "5m")
    df_tec = calcular_motor_supremo(df_cru)
    
    if df_tec is not None:
        u = df_tec.iloc[-1]
        
        if u['Sinal'] != "AGUARDANDO":
            id_sinal = f"gold_{df_tec.index[-1]}"
            if "last_gold_sid" not in st.session_state or st.session_state.last_gold_sid != id_sinal:
                msg = (f"🟡 *SINAL OURO (MGC)*\n\n"
                       f"🕹 *Ação:* {u['Sinal']}\n"
                       f"💵 *Entrada:* ${u['Entrada']:.2f}\n"
                       f"🛡 *Stop:* ${u['Stop_Loss']:.2f}\n"
                       f"🎯 *Alvo:* ${u['TP1']:.2f}")
                if enviar_telegram(msg):
                    st.session_state.last_gold_sid = id_sinal
        
        st.subheader("📊 Radar Supremo M5 (Quad-Check)")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Preço Atual", f"${u['Close']:.2f}")
        
        # CORREÇÃO AQUI: Mudando de MA_9 e MA_21 para EMA_9 e EMA_21
        c2.metric("Inércia (EMA 9/21)", "ALTA 🟩" if u['EMA_9'] > u['EMA_21'] else "BAIXA 🟥")
        
        c3.metric("Storgrama", "ALTA 🟩" if u['Stor_Line'] > u['Stor_Signal'] else "BAIXA 🟥")
        c4.metric("Volume", "PICO 🟢" if u['Volume'] > u['Vol_MA_20'] else "SECO 🔴")
        
        st.divider()
        st.subheader("🔬 Diário de Forward Test Real")
        sinais = df_tec[df_tec['Sinal'] != "AGUARDANDO"].copy()
        sinais = sinais[sinais.index.date >= data_inicio]
        
        if not sinais.empty:
            tab = sinais[['Status', 'Sinal', 'Padrao', 'Entrada', 'Stop_Loss', 'TP1', 'TP2']].copy()
            tab.index = tab.index.strftime('%d/%m %H:%M')
            format_dict = {'Entrada': '${:.2f}', 'Stop_Loss': '${:.2f}', 'TP1': '${:.2f}', 'TP2': '${:.2f}'}
            st.dataframe(tab.style.format(format_dict), use_container_width=True)
        else:
            st.info(f"🟢 Diário zerado. Aguardando novos sinais a partir de {data_inicio.strftime('%d/%m/%Y')}...")

renderizar_motor()
