import streamlit as st
import pandas as pd
import yfinance as yf
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

@st.cache_data(ttl=60, show_spinner=False) # Atualiza a cada 60 segundos
def buscar_dados_ouro(periodo="2d", intervalo="5m"):
    try:
        # Baixa os dados do Micro Ouro (MGC=F) e do Ouro Padrão (GC=F) como redundância
        df = yf.download(tickers=[TICKER_OURO, "GC=F"], period=periodo, interval=intervalo, progress=False)
        
        # Filtra apenas o ativo que retornou dados limpos
        if TICKER_OURO in df['Close']:
            dados = df.xs(TICKER_OURO, level=1, axis=1) if isinstance(df.columns, pd.MultiIndex) else df
        else:
            dados = df.xs("GC=F", level=1, axis=1) if isinstance(df.columns, pd.MultiIndex) else df
            
        dados = dados.dropna()
        if dados.empty: return None
        
        # Ajuste balístico de Fuso Horário para Nova York (Bolsa Comex)
        if dados.index.tz is None: dados.index = dados.index.tz_localize('UTC')
        dados.index = dados.index.tz_convert('America/New_York').tz_localize(None)
        
        return dados
    except Exception as e:
        return None

# ==========================================
# TESTE DE COMUNICAÇÃO NA UI
# ==========================================
dados_ouro = buscar_dados_ouro()

if dados_ouro is not None:
    preco_atual = float(dados_ouro['Close'].iloc[-1])
    hora_atualizacao = dados_ouro.index[-1].strftime("%H:%M:%S")
    
    st.success("📡 Conexão de dados com a Comex estabelecida com sucesso!")
    
    col1, col2, col3 = st.columns(3)
    col1.metric(label=f"Cotação Ouro ({TICKER_OURO})", value=f"${preco_atual:.2f}")
    col2.metric(label="Última Atualização (NY Time)", value=hora_atualizacao)
    col3.metric(label="Status da Tropa", value="Pronto para Análise Técnica")
else:
    st.error("❌ Falha ao estabelecer comunicação com os servidores de cotação.")
