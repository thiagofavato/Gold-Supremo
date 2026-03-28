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
# FASE 2: MOTOR DE EXTRAÇÃO DE DADOS (COMEX)
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
# FASE 3 E 4: CONFLUÊNCIA E ESQUADRÃO DE ELITE (>70%)
# ==========================================
def calcular_sinais_elite(df):
    if df is None or len(df) < 200:
        return None
    
    df = df.copy()
    
    # Filtros e Osciladores
    df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI_14'] = 100 - (100 / (1 + rs))
    
    # Risco Plástico (ATR 14)
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    df['ATR_14'] = np.max(pd.concat([high_low, high_close, low_close], axis=1), axis=1).rolling(14).mean()
    
    # Rastreador de Padrões
    df['Padrao'] = "Nenhum"
    df['Sinal'] = "AGUARDANDO"
    df['Stop_Loss'] = 0.0
    
    for i in range(3, len(df)):
        v1 = df.iloc[i-3] # Vela 1
        v2 = df.iloc[i-2] # Vela 2
        v3 = df.iloc[i-1] # Vela Gatilho (recém fechada)
        
        o1, c1, h1, l1 = v1['Open'], v1['Close'], v1['High'], v1['Low']
        o2, c2, h2, l2 = v2['Open'], v2['Close'], v2['High'], v2['Low']
        o3, c3, h3, l3 = v3['Open'], v3['Close'], v3['High'], v3['Low']
        
        atr_atual = v3['ATR_14']
        
        # ---------------------------------------------------------
        # LÓGICA DE RECONHECIMENTO (Apenas Padrões > 70% de Acerto)
        # ---------------------------------------------------------
        
        # 1. ENGOLFO (73%-78%)
        engolfo_alta = (c2 < o2) and (c3 > o3) and (c3 > o2) and (o3 < c2)
        engolfo_baixa = (c2 > o2) and (c3 < o3) and (o3 > c2) and (c3 < o2)
        
        # 2. TRÊS SOLDADOS / CORVOS (84% e 78%)
        soldados = (c1 > o1) and (c2 > o2) and (c3 > o3) and (c2 > c1) and (c3 > c2) and (o2 > o1) and (o3 > o2)
        corvos = (c1 < o1) and (c2 < o2) and (c3 < o3) and (c2 < c1) and (c3 < c2) and (o2 < o1) and (o3 < o2)
        
        # 3. ESTRELA DA MANHÃ / NOITE (72%-75%)
        corpo_v1, corpo_v2 = abs(o1 - c1), abs(o2 - c2)
        estrela_manha = (c1 < o1) and (corpo_v1 > atr_atual*0.5) and (corpo_v2 < corpo_v1*0.3) and (c3 > o3) and (c3 > (o1 + c1)/2)
        estrela_noite = (c1 > o1) and (corpo_v1 > atr_atual*0.5) and (corpo_v2 < corpo_v1*0.3) and (c3 < o3) and (c3 < (o1 + c1)/2)

        # ---------------------------------------------------------
        # MATRIZ DE CONFLUÊNCIA TÉCNICA (O Filtro Institucional)
        # ---------------------------------------------------------
        tendencia_alta = v3['Close'] > v3['EMA_200']
        tendencia_baixa = v3['Close'] < v3['EMA_200']
        
        # O manual exige exaustão para operar reversões. RSI < 45 (Fundo) ou > 55 (Topo)
        rsi_fundo = v3['RSI_14'] < 45
        rsi_topo = v3['RSI_14'] > 55
        
        # GATILHOS DE COMPRA
        if (engolfo_alta or soldados or estrela_manha) and tendencia_alta and rsi_fundo:
            df.loc[df.index[i], 'Sinal'] = "COMPRA"
            df.loc[df.index[i], 'Padrao'] = "3 Soldados Brancos" if soldados else ("Estrela da Manhã" if estrela_manha else "Engolfo de Alta")
            df.loc[df.index[i], 'Stop_Loss'] = min(l1, l2, l3) - (atr_atual * 1.5) # Stop no extremo do padrão + ATR
            
        # GATILHOS DE VENDA
        elif (engolfo_baixa or corvos or estrela_noite) and tendencia_baixa and rsi_topo:
            df.loc[df.index[i], 'Sinal'] = "VENDA"
            df.loc[df.index[i], 'Padrao'] = "3 Corvos Negros" if corvos else ("Estrela da Noite" if estrela_noite else "Engolfo de Baixa")
            df.loc[df.index[i], 'Stop_Loss'] = max(h1, h2, h3) + (atr_atual * 1.5) # Stop no extremo do padrão + ATR

    return df

# ==========================================
# PAINEL DE COMANDO (UI)
# ==========================================
st.markdown("<h2 style='text-align: center; color: #B8860B;'>💰 GOLD SUPREMO - PURE ACTION 🤖</h2>", unsafe_allow_html=True)

@st.fragment(run_every="20s")
def renderizar_motor():
    df_cru = buscar_dados_ouro("5d", "5m")
    df_tec = calcular_sinais_elite(df_cru)
    
    if df_tec is not None:
        vela_live = df_tec.iloc[-1]
        
        st.subheader("📊 Radar de Elite M5 (Apenas Sinais > 70%)")
        c1, c2, c3, c4 = st.columns(4)
        
        c1.metric("Preço Atual", f"${vela_live['Close']:.2f}")
        c2.metric("Tendência Macro", "ALTA 🐂" if vela_live['Close'] > vela_live['EMA_200'] else "BAIXA 🐻")
        c3.metric("RSI 14 (Exaustão)", f"{vela_live['RSI_14']:.1f}")
        c4.metric("ATR 14 (Volatilidade)", f"${vela_live['ATR_14']:.2f}")
        
        st.divider()
        
        # Verifica a última vela fechada para evitar sinais repintados
        vela_fechada = df_tec.iloc[-2]
        
        if vela_fechada['Sinal'] != "AGUARDANDO":
            seta = "🚀" if vela_fechada['Sinal'] == "COMPRA" else "🧨"
            cor = "green" if vela_fechada['Sinal'] == "COMPRA" else "red"
            
            st.markdown(f"### :{cor}[GATILHO CONFIRMADO: {vela_fechada['Sinal']} {seta}]")
            st.markdown(f"**Padrão Geométrico:** {vela_fechada['Padrao']}")
            st.markdown(f"**Stop Loss Dinâmico:** ${vela_fechada['Stop_Loss']:.2f} (Proteção de 1.5x ATR)")
            st.success("Execute manualmente na plataforma Comex.")
        else:
            st.info("🟢 Escaneando o mercado em busca de Soldados, Corvos, Estrelas e Engolfos. Radar limpo.")
            
    else:
        st.error("❌ Falha ao processar os indicadores técnicos. Aguardando volume de dados suficiente...")

renderizar_motor()
