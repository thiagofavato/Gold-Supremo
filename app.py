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
# FASE 2: MOTOR DE EXTRAÇÃO DE DADOS 
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
    if df is None or len(df) < 200: return None 
    df = df.copy()
    
    # 1. Volatilidade e Volume
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    df['ATR_14'] = np.max(pd.concat([high_low, high_close, low_close], axis=1), axis=1).rolling(14).mean()
    df['Vol_MA_20'] = df['Volume'].rolling(window=20).mean()

    # 2. Médias Móveis Institucionais
    df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
    df['EMA_21'] = df['Close'].ewm(span=21, adjust=False).mean()
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    df['SMA_200'] = df['Close'].rolling(window=200).mean()
    
    # 3. MACD Intradiário (8-17-9) e Histograma
    df['MACD_Line'] = df['Close'].ewm(span=8, adjust=False).mean() - df['Close'].ewm(span=17, adjust=False).mean()
    df['MACD_Signal'] = df['MACD_Line'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD_Line'] - df['MACD_Signal'] 

    # 4. RSI Calibrado para Ouro
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss
    df['RSI_14'] = 100 - (100 / (1 + rs))
    
    # 5. Geração de Sinais
    df['Padrao'] = "Nenhum"
    df['Sinal'] = "AGUARDANDO"
    df['Status'] = "-" 
    
    for i in range(200, len(df)):
        v1, v2 = df.iloc[i-2], df.iloc[i-1]
        o1, c1, h1, l1 = v1['Open'], v1['Close'], v1['High'], v1['Low']
        o2, c2, h2, l2 = v2['Open'], v2['Close'], v2['High'], v2['Low']
        
        atr_atual = v2['ATR_14']
        engolfo_alta = (c1 < o1) and (c2 > o2) and (c2 > o1) and (o2 < c1)
        engolfo_baixa = (c1 > o1) and (c2 < o2) and (o2 > c1) and (c2 < o1)
        distancia_stop = atr_atual * 1.5
        
        # Filtros Doutrinários
        tendencia_micro_alta = v2['EMA_9'] > v2['EMA_21']
        tendencia_micro_baixa = v2['EMA_9'] < v2['EMA_21']
        tendencia_macro_alta = c2 > v2['SMA_200'] and v2['SMA_50'] > v2['SMA_200']
        tendencia_macro_baixa = c2 < v2['SMA_200'] and v2['SMA_50'] < v2['SMA_200']

        rsi_compra = 40 <= v2['RSI_14'] <= 75
        rsi_venda = 25 <= v2['RSI_14'] <= 60

        macd_hist_atual = v2['MACD_Hist']
        macd_hist_anterior = v1['MACD_Hist']
        macd_expansao_alta = (macd_hist_atual > 0) and (macd_hist_atual > macd_hist_anterior)
        macd_expansao_baixa = (macd_hist_atual < 0) and (macd_hist_atual < macd_hist_anterior)

        if engolfo_alta and tendencia_micro_alta and tendencia_macro_alta and macd_expansao_alta and v2['Volume'] > v2['Vol_MA_20'] and rsi_compra:
            df.loc[df.index[i], 'Sinal'] = "COMPRA"
            df.loc[df.index[i], 'Padrao'] = "Engolfo de Alta"
            df.loc[df.index[i], 'Entrada'] = c2
            sl = min(l1, l2) - distancia_stop
            df.loc[df.index[i], 'Stop_Loss'] = sl
            df.loc[df.index[i], 'TP1'] = c2 + ((c2 - sl) * 1.5)
            df.loc[df.index[i], 'TP2'] = c2 + ((c2 - sl) * 2.0)
            
        elif engolfo_baixa and tendencia_micro_baixa and tendencia_macro_baixa and macd_expansao_baixa and v2['Volume'] > v2['Vol_MA_20'] and rsi_venda:
            df.loc[df.index[i], 'Sinal'] = "VENDA"
            df.loc[df.index[i], 'Padrao'] = "Engolfo de Baixa"
            df.loc[df.index[i], 'Entrada'] = c2
            sl = max(h1, h2) + distancia_stop
            df.loc[df.index[i], 'Stop_Loss'] = sl
            df.loc[df.index[i], 'TP1'] = c2 - ((sl - c2) * 1.5)
            df.loc[df.index[i], 'TP2'] = c2 - ((sl - c2) * 2.0)

    # Scanner de Desfecho
    sinais_gerados = df[df['Sinal'] != "AGUARDANDO"].index
    for idx in sinais_gerados:
        posicao_atual = df.index.get_loc(idx)
        tipo = df.loc[idx, 'Sinal']
        entrada = df.loc[idx, 'Entrada']
        sl = df.loc[idx, 'Stop_Loss']
        tp1 = df.loc[idx, 'TP1']
        tp2 = df.loc[idx, 'TP2']
        
        status_op = "ATIVA 🟡"
        bateu_tp1 = False
        
        for j in range(posicao_atual + 1, len(df)):
            maxima_futura = df['High'].iloc[j]
            minima_futura = df['Low'].iloc[j]
            
            if tipo == "COMPRA":
                if not bateu_tp1:
                    if minima_futura <= sl:
                        status_op = "LOSS 🔴"
                        break
                    elif maxima_futura >= tp1:
                        bateu_tp1 = True
                        sl = entrada 
                if bateu_tp1:
                    if maxima_futura >= tp2:
                        status_op = "GAIN TOTAL 🚀"
                        break
                    elif minima_futura <= sl:
                        status_op = "SAIU NO ZERO ⚪ (Com TP1)"
                        break
                        
            elif tipo == "VENDA":
                if not bateu_tp1:
                    if maxima_futura >= sl:
                        status_op = "LOSS 🔴"
                        break
                    elif minima_futura <= tp1:
                        bateu_tp1 = True
                        sl = entrada 
                if bateu_tp1:
                    if minima_futura <= tp2:
                        status_op = "GAIN TOTAL 🚀"
                        break
                    elif maxima_futura >= sl:
                        status_op = "SAIU NO ZERO ⚪ (Com TP1)"
                        break
                        
        df.loc[idx, 'Status'] = status_op

    return df

# ==========================================
# PAINEL DE COMANDO (UI)
# ==========================================
st.markdown("<h2 style='text-align: center; color: #B8860B;'>💰 GOLD SUPREMO - PURE ACTION 🤖</h2>", unsafe_allow_html=True)

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    # TRAVA REMOVIDA: Recua 2 dias por padrão para o diário não apagar o histórico na virada da meia-noite
    data_padrao = datetime.date.today() - datetime.timedelta(days=2)
    data_inicio = st.date_input("📅 Exibir histórico a partir de:", data_padrao)

@st.fragment(run_every="20s")
def renderizar_motor():
    df_cru = buscar_dados_ouro("5d", "5m")
    df_tec = calcular_motor_supremo(df_cru)
    
    if df_tec is not None:
        u = df_tec.iloc[-1]
        u_anterior = df_tec.iloc[-2] 
        
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
        
        st.subheader("📊 Radar Supremo M5 (Quad-Check Doutrinário)")
        
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Preço Atual", f"${u['Close']:.2f}")
        c2.metric("Inércia (EMA 9/21)", "ALTA 🟩" if u['EMA_9'] > u['EMA_21'] else "BAIXA 🟥")
        
        macd_estado = "NEUTRO ⬜"
        if u['MACD_Hist'] > 0 and u['MACD_Hist'] > u_anterior['MACD_Hist']:
            macd_estado = "EXPANSÃO 🟩"
        elif u['MACD_Hist'] < 0 and u['MACD_Hist'] < u_anterior['MACD_Hist']:
            macd_estado = "QUEDA 🟥"
        elif u['MACD_Hist'] > 0 and u['MACD_Hist'] < u_anterior['MACD_Hist']:
            macd_estado = "CONTRAÇÃO 🟨" 
        elif u['MACD_Hist'] < 0 and u['MACD_Hist'] > u_anterior['MACD_Hist']:
            macd_estado = "CONTRAÇÃO 🟨" 
            
        c3.metric("MACD (8-17-9)", macd_estado)
        c4.metric("Volume", "PICO 🟢" if u['Volume'] > u['Vol_MA_20'] else "SECO 🔴")
        c5.metric("RSI (14)", f"{u['RSI_14']:.1f}")
        
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
    else:
        st.warning("⏳ Coletando dados institucionais (Processando as 200 velas iniciais necessárias para a SMA 200)...")

renderizar_motor()
