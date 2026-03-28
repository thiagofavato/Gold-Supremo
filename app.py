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
st.markdown("<style>[data-testid='stMetricValue']{font-size: 1.4rem !important;}[data-testid='stMetricLabel']{font-size: 0.9rem !important;}</style>", unsafe_allow_html=True)

TICKER_OURO = "MGC=F"

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
    except Exception as e:
        return None

# ==========================================
# FASE 6: QUAD-CHECK (ENGOLFO + 9/21 + STORGRAMA + VOLUME)
# ==========================================
def calcular_motor_supremo(df):
    if df is None or len(df) < 50:
        return None
    
    df = df.copy()
    
    # Risco Plástico (ATR 14)
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    df['ATR_14'] = np.max(pd.concat([high_low, high_close, low_close], axis=1), axis=1).rolling(14).mean()
    
    # Inércia Gráfica
    df['MA_9'] = df['Close'].rolling(window=9).mean()
    df['MA_21'] = df['Close'].rolling(window=21).mean()
    
    # Aceleração Institucional (Storgrama)
    fast_ema = df['Close'].ewm(span=9, adjust=False).mean()
    slow_ema = df['Close'].ewm(span=20, adjust=False).mean()
    df['Stor_Line'] = fast_ema - slow_ema
    df['Stor_Signal'] = df['Stor_Line'].ewm(span=18, adjust=False).mean()
    
    # Filtro Institucional Dinâmico (Volume)
    df['Vol_MA_20'] = df['Volume'].rolling(window=20).mean()
    
    df['Padrao'] = "Nenhum"
    df['Sinal'] = "AGUARDANDO"
    df['Entrada'] = np.nan
    df['Stop_Loss'] = np.nan
    df['TP1'] = np.nan
    df['TP2'] = np.nan
    
    for i in range(2, len(df)):
        v1 = df.iloc[i-2] 
        v2 = df.iloc[i-1] 
        
        o1, c1, h1, l1 = v1['Open'], v1['Close'], v1['High'], v1['Low']
        o2, c2, h2, l2 = v2['Open'], v2['Close'], v2['High'], v2['Low']
        
        atr_atual = v2['ATR_14']
        
        # Geometria
        engolfo_alta = (c1 < o1) and (c2 > o2) and (c2 > o1) and (o2 < c1)
        engolfo_baixa = (c1 > o1) and (c2 < o2) and (o2 > c1) and (c2 < o1)
        
        # Alinhamento
        grafico_comprado = v2['MA_9'] > v2['MA_21']
        ind_comprado = v2['Stor_Line'] > v2['Stor_Signal']
        
        grafico_vendido = v2['MA_9'] < v2['MA_21']
        ind_vendido = v2['Stor_Line'] < v2['Stor_Signal']
        
        # Volume
        volume_valido = v2['Volume'] > v2['Vol_MA_20']
        
        distancia_stop = atr_atual * 1.5
        
        # COMPRA
        if engolfo_alta and grafico_comprado and ind_comprado and volume_valido:
            df.loc[df.index[i], 'Sinal'] = "COMPRA"
            df.loc[df.index[i], 'Padrao'] = "Engolfo de Alta"
            df.loc[df.index[i], 'Entrada'] = c2
            sl = min(l1, l2) - distancia_stop
            risco = c2 - sl
            df.loc[df.index[i], 'Stop_Loss'] = sl
            df.loc[df.index[i], 'TP1'] = c2 + (risco * 1.5)
            df.loc[df.index[i], 'TP2'] = c2 + (risco * 2.0)
            
        # VENDA
        elif engolfo_baixa and grafico_vendido and ind_vendido and volume_valido:
            df.loc[df.index[i], 'Sinal'] = "VENDA"
            df.loc[df.index[i], 'Padrao'] = "Engolfo de Baixa"
            df.loc[df.index[i], 'Entrada'] = c2
            sl = max(h1, h2) + distancia_stop
            risco = sl - c2
            df.loc[df.index[i], 'Stop_Loss'] = sl
            df.loc[df.index[i], 'TP1'] = c2 - (risco * 1.5)
            df.loc[df.index[i], 'TP2'] = c2 - (risco * 2.0)

    return df

# ==========================================
# PAINEL DE COMANDO E FORWARD TEST (UI)
# ==========================================
st.markdown("<h2 style='text-align: center; color: #B8860B;'>💰 GOLD SUPREMO - PURE ACTION 🤖</h2>", unsafe_allow_html=True)

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    hoje = datetime.date.today()
    domingo = hoje + datetime.timedelta(days=(6 - hoje.weekday()))
    data_inicio = st.date_input("📅 Data de Início do Forward Test (Diário Limpo)", domingo)

@st.fragment(run_every="20s")
def renderizar_motor():
    df_cru = buscar_dados_ouro("5d", "5m")
    df_tec = calcular_motor_supremo(df_cru)
    
    if df_tec is not None:
        vela_live = df_tec.iloc[-1]
        
        st.subheader("📊 Radar Supremo M5 (Quad-Check)")
        c1, c2, c3, c4 = st.columns(4)
        
        c1.metric("Preço Atual", f"${vela_live['Close']:.2f}")
        c2.metric("Inércia (MA 9/21)", "ALTA 🟩" if vela_live['MA_9'] > vela_live['MA_21'] else "BAIXA 🟥")
        c3.metric("Storgrama (Momentum)", "ALTA 🟩" if vela_live['Stor_Line'] > vela_live['Stor_Signal'] else "BAIXA 🟥")
        c4.metric("Volume Dinâmico", "PICO 🟢" if vela_live['Volume'] > vela_live['Vol_MA_20'] else "SECO 🔴")
        
        st.divider()
        st.subheader("🔬 Diário de Forward Test Real")
        
        sinais_historicos = df_tec[df_tec['Sinal'] != "AGUARDANDO"].copy()
        sinais_historicos = sinais_historicos[sinais_historicos.index.date >= data_inicio]
        
        if not sinais_historicos.empty:
            tabela_exibicao = sinais_historicos[['Sinal', 'Padrao', 'Entrada', 'Stop_Loss', 'TP1', 'TP2']].copy()
            tabela_exibicao.index = tabela_exibicao.index.strftime('%d/%m %H:%M')
            
            for col in ['Entrada', 'Stop_Loss', 'TP1', 'TP2']:
                tabela_exibicao[col] = tabela_exibicao[col].apply(lambda x: round(x, 2) if pd.notnull(x) else x)
                
            st.dataframe(tabela_exibicao.iloc[::-1], use_container_width=True)
            st.warning("⚠️ Lembrete de Batalha: Execute a ordem no preço do BlackArrow, ignore o preço exato do robô devido ao spread do contrato.")
        else:
            st.info(f"🟢 Diário zerado. A máquina aguarda a abertura do mercado a partir de {data_inicio.strftime('%d/%m/%Y')}.")
            
    else:
        st.error("❌ Falha ao processar os dados...")

renderizar_motor()
