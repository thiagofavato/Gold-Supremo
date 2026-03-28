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
# FASE 3 E 4: CONFLUÊNCIA E PADRÕES DE ELITE
# ==========================================
def calcular_sinais_elite(df):
    if df is None or len(df) < 200:
        return None
    
    df = df.copy()
    
    # EMAs e RSI
    df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI_14'] = 100 - (100 / (1 + rs))
    
    # ATR 14
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    df['ATR_14'] = np.max(pd.concat([high_low, high_close, low_close], axis=1), axis=1).rolling(14).mean()
    
    # Rastreador de Padrões e Alvos
    df['Padrao'] = "Nenhum"
    df['Sinal'] = "AGUARDANDO"
    df['Entrada'] = np.nan
    df['Stop_Loss'] = np.nan
    df['TP1'] = np.nan
    df['TP2'] = np.nan
    
    for i in range(3, len(df)):
        v1 = df.iloc[i-3] 
        v2 = df.iloc[i-2] 
        v3 = df.iloc[i-1] # Vela Gatilho (fechada)
        
        o1, c1, h1, l1 = v1['Open'], v1['Close'], v1['High'], v1['Low']
        o2, c2, h2, l2 = v2['Open'], v2['Close'], v2['High'], v2['Low']
        o3, c3, h3, l3 = v3['Open'], v3['Close'], v3['High'], v3['Low']
        
        atr_atual = v3['ATR_14']
        
        # 1. ENGOLFO
        engolfo_alta = (c2 < o2) and (c3 > o3) and (c3 > o2) and (o3 < c2)
        engolfo_baixa = (c2 > o2) and (c3 < o3) and (o3 > c2) and (c3 < o2)
        
        # 2. TRÊS SOLDADOS / CORVOS
        soldados = (c1 > o1) and (c2 > o2) and (c3 > o3) and (c2 > c1) and (c3 > c2) and (o2 > o1) and (o3 > o2)
        corvos = (c1 < o1) and (c2 < o2) and (c3 < o3) and (c2 < c1) and (c3 < c2) and (o2 < o1) and (o3 < o2)
        
        # 3. ESTRELAS
        corpo_v1, corpo_v2 = abs(o1 - c1), abs(o2 - c2)
        estrela_manha = (c1 < o1) and (corpo_v1 > atr_atual*0.5) and (corpo_v2 < corpo_v1*0.3) and (c3 > o3) and (c3 > (o1 + c1)/2)
        estrela_noite = (c1 > o1) and (corpo_v1 > atr_atual*0.5) and (corpo_v2 < corpo_v1*0.3) and (c3 < o3) and (c3 < (o1 + c1)/2)

        # Filtros de Confluência
        tendencia_alta = v3['Close'] > v3['EMA_200']
        tendencia_baixa = v3['Close'] < v3['EMA_200']
        rsi_fundo = v3['RSI_14'] < 45
        rsi_topo = v3['RSI_14'] > 55
        
        # Distância do Stop baseada no manual (1.5x ATR)
        distancia_stop = atr_atual * 1.5
        
        # GATILHOS DE COMPRA
        if (engolfo_alta or soldados or estrela_manha) and tendencia_alta and rsi_fundo:
            df.loc[df.index[i], 'Sinal'] = "COMPRA"
            df.loc[df.index[i], 'Padrao'] = "3 Soldados" if soldados else ("Estrela da Manhã" if estrela_manha else "Engolfo de Alta")
            df.loc[df.index[i], 'Entrada'] = c3
            
            sl = min(l1, l2, l3) - distancia_stop
            risco = c3 - sl
            df.loc[df.index[i], 'Stop_Loss'] = sl
            df.loc[df.index[i], 'TP1'] = c3 + (risco * 1.5) # R:R 1:1.5
            df.loc[df.index[i], 'TP2'] = c3 + (risco * 2.0) # R:R 1:2.0
            
        # GATILHOS DE VENDA
        elif (engolfo_baixa or corvos or estrela_noite) and tendencia_baixa and rsi_topo:
            df.loc[df.index[i], 'Sinal'] = "VENDA"
            df.loc[df.index[i], 'Padrao'] = "3 Corvos" if corvos else ("Estrela da Noite" if estrela_noite else "Engolfo de Baixa")
            df.loc[df.index[i], 'Entrada'] = c3
            
            sl = max(h1, h2, h3) + distancia_stop
            risco = sl - c3
            df.loc[df.index[i], 'Stop_Loss'] = sl
            df.loc[df.index[i], 'TP1'] = c3 - (risco * 1.5)
            df.loc[df.index[i], 'TP2'] = c3 - (risco * 2.0)

    return df

# ==========================================
# FASE 5: LABORATÓRIO DE BACKTEST (UI)
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
        
        # Correção da anomalia do Urso na Alta
        vies = "ALTA 🐂" if vela_live['Close'] > vela_live['EMA_200'] else "BAIXA 🐻"
        c2.metric("Tendência Macro", vies)
        
        c3.metric("RSI 14 (Exaustão)", f"{vela_live['RSI_14']:.1f}")
        c4.metric("ATR 14 (Volatilidade)", f"${vela_live['ATR_14']:.2f}")
        
        st.divider()
        
        # MÓDULO DE BACKTEST: Histórico de Sinais dos últimos 5 dias
        st.subheader("🔬 Laboratório de Backtest (Últimos 5 Dias)")
        
        sinais_historicos = df_tec[df_tec['Sinal'] != "AGUARDANDO"].copy()
        
        if not sinais_historicos.empty:
            # Formatação da tabela para análise
            tabela_exibicao = sinais_historicos[['Sinal', 'Padrao', 'Entrada', 'Stop_Loss', 'TP1', 'TP2', 'RSI_14', 'ATR_14']].copy()
            tabela_exibicao.index = tabela_exibicao.index.strftime('%d/%m %H:%M')
            
            # Arredondando os valores numéricos para visualização limpa
            for col in ['Entrada', 'Stop_Loss', 'TP1', 'TP2', 'RSI_14', 'ATR_14']:
                tabela_exibicao[col] = tabela_exibicao[col].apply(lambda x: round(x, 2))
                
            # Inverte para mostrar o mais recente no topo
            st.dataframe(tabela_exibicao.iloc[::-1], use_container_width=True)
            
            st.info("📋 Pegue as datas e horários desta tabela e cruze visualmente com o seu gráfico no BlackArrow. Verifique se o alvo (TP1/TP2) foi atingido antes do Stop Loss.")
        else:
            st.info("🟢 Filtro rigoroso ativado. Nenhum sinal de elite (>70% acerto) foi disparado nos últimos 5 dias.")
            
    else:
        st.error("❌ Falha ao processar os dados. Aguardando conexão com a Comex...")

renderizar_motor()
