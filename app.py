import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import datetime
import pytz

# ==========================================
# FASE 1: FUNDAÇÃO GOLD SUPREMO
# ==========================================
st.set_page_config(page_title="💰 GOLD SUPREMO - MTFA", layout="wide", initial_sidebar_state="collapsed")
st.markdown("<style>[data-testid='stMetricValue']{font-size: 1.4rem !important;}[data-testid='stMetricLabel']{font-size: 0.9rem !important;}</style>", unsafe_allow_html=True)

TICKER_OURO = "MGC=F"

# ==========================================
# FASE 2: MOTOR DE EXTRAÇÃO DE DADOS (M5 e M15)
# ==========================================
@st.cache_data(ttl=60, show_spinner=False)
def buscar_dados_ouro(periodo="5d"):
    try:
        # Baixa M5
        df_m5_raw = yf.download(tickers=[TICKER_OURO, "GC=F"], period=periodo, interval="5m", progress=False)
        # Baixa M15
        df_m15_raw = yf.download(tickers=[TICKER_OURO, "GC=F"], period=periodo, interval="15m", progress=False)
        
        def extrair_ativo(df_in):
            if TICKER_OURO in df_in['Close']: return df_in.xs(TICKER_OURO, level=1, axis=1) if isinstance(df_in.columns, pd.MultiIndex) else df_in
            else: return df_in.xs("GC=F", level=1, axis=1) if isinstance(df_in.columns, pd.MultiIndex) else df_in

        df_m5 = extrair_ativo(df_m5_raw).dropna()
        df_m15 = extrair_ativo(df_m15_raw).dropna()
        
        if df_m5.empty or df_m15.empty: return None, None
        
        # Ajuste de Fuso
        for df in [df_m5, df_m15]:
            if df.index.tz is None: df.index = df.index.tz_localize('UTC')
            df.index = df.index.tz_convert('America/New_York').tz_localize(None)
            
        return df_m5, df_m15
    except Exception as e:
        return None, None

# ==========================================
# FASE 6: PENTA-CHECK (ENGOLFO + 9/21 M5 + STOR M5 + VOL + M15 MACRO)
# ==========================================
def calcular_motor_supremo(df_m5, df_m15):
    if df_m5 is None or len(df_m5) < 50: return None
    
    # --- PROCESSAMENTO DO GENERAL (M15) ---
    df_m15 = df_m15.copy()
    df_m15['MA_9_15m'] = df_m15['Close'].rolling(window=9).mean()
    df_m15['MA_21_15m'] = df_m15['Close'].rolling(window=21).mean()
    fast_ema_15 = df_m15['Close'].ewm(span=9, adjust=False).mean()
    slow_ema_15 = df_m15['Close'].ewm(span=20, adjust=False).mean()
    df_m15['Stor_Line_15m'] = fast_ema_15 - slow_ema_15
    df_m15['Stor_Signal_15m'] = df_m15['Stor_Line_15m'].ewm(span=18, adjust=False).mean()
    
    # Sincroniza o M15 com as velas de M5 (Forward Fill)
    m15_sync = df_m15[['MA_9_15m', 'MA_21_15m', 'Stor_Line_15m', 'Stor_Signal_15m']].reindex(df_m5.index, method='ffill')
    
    # --- PROCESSAMENTO DO ATIRADOR (M5) ---
    df = df_m5.join(m15_sync).copy()
    
    # Risco Plástico (ATR 14)
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    df['ATR_14'] = np.max(pd.concat([high_low, high_close, low_close], axis=1), axis=1).rolling(14).mean()
    
    # Inércia Gráfica M5
    df['MA_9'] = df['Close'].rolling(window=9).mean()
    df['MA_21'] = df['Close'].rolling(window=21).mean()
    
    # Aceleração Institucional M5
    fast_ema = df['Close'].ewm(span=9, adjust=False).mean()
    slow_ema = df['Close'].ewm(span=20, adjust=False).mean()
    df['Stor_Line'] = fast_ema - slow_ema
    df['Stor_Signal'] = df['Stor_Line'].ewm(span=18, adjust=False).mean()
    
    # Volume M5
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
        
        # Geometria (Engolfos M5)
        engolfo_alta = (c1 < o1) and (c2 > o2) and (c2 > o1) and (o2 < c1)
        engolfo_baixa = (c1 > o1) and (c2 < o2) and (o2 > c1) and (c2 < o1)
        
        # Alinhamento M5
        grafico_comprado = v2['MA_9'] > v2['MA_21']
        ind_comprado = v2['Stor_Line'] > v2['Stor_Signal']
        
        grafico_vendido = v2['MA_9'] < v2['MA_21']
        ind_vendido = v2['Stor_Line'] < v2['Stor_Signal']
        
        # Volume M5
        volume_valido = v2['Volume'] > v2['Vol_MA_20']
        
        # Alinhamento MACRO (M15) - A Nova Trava
        macro_comprado = (v2['MA_9_15m'] > v2['MA_21_15m']) and (v2['Stor_Line_15m'] > v2['Stor_Signal_15m'])
        macro_vendido = (v2['MA_9_15m'] < v2['MA_21_15m']) and (v2['Stor_Line_15m'] < v2['Stor_Signal_15m'])
        
        distancia_stop = atr_atual * 1.5
        
        # COMPRA PENTA-CHECK
        if engolfo_alta and grafico_comprado and ind_comprado and volume_valido and macro_comprado:
            df.loc[df.index[i], 'Sinal'] = "COMPRA"
            df.loc[df.index[i], 'Padrao'] = "Engolfo + M15"
            df.loc[df.index[i], 'Entrada'] = c2
            sl = min(l1, l2) - distancia_stop
            risco = c2 - sl
            df.loc[df.index[i], 'Stop_Loss'] = sl
            df.loc[df.index[i], 'TP1'] = c2 + (risco * 1.5)
            df.loc[df.index[i], 'TP2'] = c2 + (risco * 2.0)
            
        # VENDA PENTA-CHECK
        elif engolfo_baixa and grafico_vendido and ind_vendido and volume_valido and macro_vendido:
            df.loc[df.index[i], 'Sinal'] = "VENDA"
            df.loc[df.index[i], 'Padrao'] = "Engolfo + M15"
            df.loc[df.index[i], 'Entrada'] = c2
            sl = max(h1, h2) + distancia_stop
            risco = sl - c2
            df.loc[df.index[i], 'Stop_Loss'] = sl
            df.loc[df.index[i], 'TP1'] = c2 - (risco * 1.5)
            df.loc[df.index[i], 'TP2'] = c2 - (risco * 2.0)

    return df

# ==========================================
# PAINEL DE COMANDO E AUDITORIA (UI)
# ==========================================
st.markdown("<h2 style='text-align: center; color: #B8860B;'>💰 GOLD SUPREMO - PENTA CHECK 🤖</h2>", unsafe_allow_html=True)

@st.fragment(run_every="20s")
def renderizar_motor():
    df_m5, df_m15 = buscar_dados_ouro("5d")
    df_tec = calcular_motor_supremo(df_m5, df_m15)
    
    if df_tec is not None:
        vela_live = df_tec.iloc[-1]
        
        st.subheader("📊 Radar Supremo M5/M15 (Penta-Check)")
        c1, c2, c3, c4, c5 = st.columns(5)
        
        c1.metric("Preço Atual", f"${vela_live['Close']:.2f}")
        c2.metric("M5 Inércia", "ALTA 🟩" if vela_live['MA_9'] > vela_live['MA_21'] else "BAIXA 🟥")
        c3.metric("M5 Storgrama", "ALTA 🟩" if vela_live['Stor_Line'] > vela_live['Stor_Signal'] else "BAIXA 🟥")
        c4.metric("M5 Volume", "PICO 🟢" if vela_live['Volume'] > vela_live['Vol_MA_20'] else "SECO 🔴")
        
        macro_status = "ALTA 🟩" if (vela_live['MA_9_15m'] > vela_live['MA_21_15m'] and vela_live['Stor_Line_15m'] > vela_live['Stor_Signal_15m']) else ("BAIXA 🟥" if (vela_live['MA_9_15m'] < vela_live['MA_21_15m'] and vela_live['Stor_Line_15m'] < vela_live['Stor_Signal_15m']) else "MISTO 🟨")
        c5.metric("M15 MACRO", macro_status)
        
        st.divider()
        
        # MÓDULO DE BACKTEST RESTAURADO (Últimos 5 Dias)
        st.subheader("🔬 Laboratório de Backtest (Penta-Check M5 + M15)")
        
        sinais_historicos = df_tec[df_tec['Sinal'] != "AGUARDANDO"].copy()
        
        if not sinais_historicos.empty:
            tabela_exibicao = sinais_historicos[['Sinal', 'Padrao', 'Entrada', 'Stop_Loss', 'TP1', 'TP2']].copy()
            tabela_exibicao.index = tabela_exibicao.index.strftime('%d/%m %H:%M')
            
            for col in ['Entrada', 'Stop_Loss', 'TP1', 'TP2']:
                tabela_exibicao[col] = tabela_exibicao[col].apply(lambda x: round(x, 2) if pd.notnull(x) else x)
                
            st.dataframe(tabela_exibicao.iloc[::-1], use_container_width=True)
            st.warning("⚠️ Nota: Sinais drasticamente reduzidos. O robô só atirou quando o M15 autorizou o M5.")
        else:
            st.info("🟢 Penta-Check ativo. Nenhum sinal sobreviveu ao filtro do M15 nos últimos 5 dias. O mercado esteve altamente ruidoso ou sem tendência macro definida.")
            
    else:
        st.error("❌ Falha ao processar os dados. Aguardando conexão com a Comex...")

renderizar_motor()
