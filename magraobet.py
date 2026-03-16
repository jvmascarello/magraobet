import streamlit as st
import pandas as pd
import requests
import random
import datetime
from itertools import product

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="MagraoBet Sniper", layout="wide")

# --- ESTILIZAÇÃO CSS (FLASHCORE STYLE) ---
st.markdown("""
    <style>
    /* Fundo e Cores Base */
    .stApp {
        background-color: #0b161b;
        color: #e4e4e4;
    }
    
    /* Painel de Configurações Superior */
    .config-panel {
        background-color: #121e24;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        border: 1px solid #1e2d35;
    }

    /* Linhas de Jogo */
    .game-row {
        border-bottom: 1px solid #1e2d35;
        padding: 12px 5px;
        transition: 0.2s;
    }
    
    /* Nomes dos Times */
    .team-name {
        font-size: 1.05rem;
        font-weight: 500;
        color: #ffffff;
    }
    .anchor-active {
        color: #00c853 !important;
        font-weight: bold;
    }

    /* Ajuste de Botões Streamlit para parecerem compactos */
    .stButton > button {
        width: 100%;
        padding: 2px 5px !important;
        height: 35px !important;
        font-size: 0.9rem !important;
    }
    
    /* Esconder elementos padrão */
    div[data-testid="stCheckbox"] { margin-bottom: 0px; }
    hr { margin: 10px 0 !important; border-color: #1e2d35 !important; }
    </style>
""", unsafe_allow_html=True)

# --- TRATAMENTO SEGURO DA API KEY ---
def get_api_key():
    try:
        if "API_KEY" in st.secrets:
            return st.secrets["API_KEY"]
    except:
        pass
    return ""

# --- INICIALIZAÇÃO DE ESTADOS ---
if 'deleted_games' not in st.session_state:
    st.session_state.deleted_games = set()
if 'selections' not in st.session_state:
    st.session_state.selections = {} # ID -> set(["1", "X", "2"])
if 'anchors' not in st.session_state:
    st.session_state.anchors = set()
if 'periodo' not in st.session_state:
    st.session_state.periodo = 3

# --- BUSCA DE DADOS (DENTRO DA DOCUMENTAÇÃO THE ODDS API) ---
@st.cache_data(ttl=3600)
def buscar_dados_api(api_key):
    if not api_key: return None, "Chave API não configurada."
    
    # Chave exata para o Brasileirão Série A conforme documentação
    league_key = "soccer_brazil_campeonato"
    
    url = f"https://api.the-odds-api.com/v4/sports/{league_key}/odds/?apiKey={api_key}&regions=eu&markets=h2h&oddsFormat=decimal"
    
    try:
        res = requests.get(url, timeout=15)
        if res.status_code == 200:
            data = res.json()
            if not data: return None, "Nenhum jogo encontrado para esta liga no momento."
            return data, None
        elif res.status_code == 404:
            # Fallback para Série B se a A estiver vazia
            url_fallback = f"https://api.the-odds-api.com/v4/sports/soccer_brazil_campeonato_serie_b/odds/?apiKey={api_key}&regions=eu&markets=h2h&oddsFormat=decimal"
            res_fb = requests.get(url_fallback)
            if res_fb.status_code == 200: return res_fb.json(), None
            return None, "Campeonato não encontrado (404)."
        return None, f"Erro na API: {res.status_code}"
    except Exception as e:
        return None, f"Erro de conexão: {str(e)}"

# --- INTERFACE PRINCIPAL ---

st.title("🎯 MagraoBet Sniper")

# --- PAINEL DE CONTROLE INTEGRADO (TOPO) ---
with st.container():
    st.markdown('<div class="config-panel">', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1.5, 1.5, 3])
    
    with c1:
        investimento = st.number_input("Investimento (R$)", value=50, step=5)
    with c2:
        qtd_bilhetes = st.number_input("Qtd. Bilhetes", value=10, min_value=1)
    with c3:
        st.write("Período de Busca")
        p1, p2, p3 = st.columns(3)
        if p1.button("3 Dias", type="primary" if st.session_state.periodo == 3 else "secondary", use_container_width=True):
            st.session_state.periodo = 3
            st.rerun()
        if p2.button("4 Dias", type="primary" if st.session_state.periodo == 4 else "secondary", use_container_width=True):
            st.session_state.periodo = 4
            st.rerun()
        if p3.button("5 Dias", type="primary" if st.session_state.periodo == 5 else "secondary", use_container_width=True):
            st.session_state.periodo = 5
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# Lógica de Chave API
API_KEY = get_api_key()
if not API_KEY:
    API_KEY = st.text_input("Chave API (Insira aqui se não houver no secrets):", type="password")
    if not API_KEY: st.stop()

# Busca
with st.spinner("Sincronizando odds em tempo real..."):
    data, erro = buscar_dados_api(API_KEY)

if erro:
    st.error(f"❌ {erro}")
    if st.button("🔄 Tentar Novamente"):
        st.cache_data.clear()
        st.rerun()
    st.stop()

# --- LISTAGEM DE JOGOS ---
if data:
    agora = datetime.datetime.now(datetime.timezone.utc)
    limite = agora + datetime.timedelta(days=st.session_state.periodo)
    
    # Cabeçalho da Lista
    h1, h2, h3, h4, h5 = st.columns([0.4, 0.4, 1.2, 4, 3.2])
    h1.write("⭐")
    h2.write("🗑️")
    h3.write("Data")
    h4.write("Partida")
    h5.write("1    X    2")
    st.divider()

    for game in data:
        gid = game['id']
        if gid in st.session_state.deleted_games: continue
        
        dt_utc = datetime.datetime.fromisoformat(game['commence_time'].replace('Z', '+00:00'))
        
        if agora < dt_utc <= limite:
            home, away = game['home_team'], game['away_team']
            
            # Inicializa seleção
            if gid not in st.session_state.selections:
                st.session_state.selections[gid] = {"1"} # Default Casa

            with st.container():
                c_star, c_del, c_date, c_teams, c_odds = st.columns([0.4, 0.4, 1.2, 4, 3.2])
                
                # 1. Estrela (Âncora)
                with c_star:
                    is_anc = gid in st.session_state.anchors
                    label_star = "⭐" if is_anc else "☆"
                    if st.button(label_star, key=f"star_{gid}"):
                        if is_anc: st.session_state.anchors.remove(gid)
                        else: 
                            st.session_state.anchors.add(gid)
                            # Se virou âncora, mantém apenas um palpite
                            st.session_state.selections[gid] = {list(st.session_state.selections[gid])[0]}
                        st.rerun()
                
                # 2. Excluir
                with c_del:
                    if st.button("🗑️", key=f"del_{gid}"):
                        st.session_state.deleted_games.add(gid)
                        st.rerun()

                # 3. Data
                with c_date:
                    st.caption(dt_utc.astimezone().strftime("%d/%m %H:%M"))

                # 4. Confronto
                with c_teams:
                    css_class = "anchor-active" if gid in st.session_state.anchors else "team-name"
                    st.markdown(f'<div class="{css_class}">{home} x {away}</div>', unsafe_allow_html=True)

                # 5. Botões 1X2
                with c_odds:
                    o1, ox, o2 = st.columns(3)
                    
                    def handle_click(game_id, val):
                        is_ancora = game_id in st.session_state.anchors
                        if is_ancora:
                            st.session_state.selections[game_id] = {val}
                        else:
                            curr = st.session_state.selections[game_id]
                            if val in curr:
                                if len(curr) > 1: curr.remove(val)
                            else:
                                curr.add(val)

                    with o1:
                        sel = "1" in st.session_state.selections[gid]
                        if st.button("1", key=f"b1_{gid}", type="primary" if sel else "secondary"):
                            handle_click(gid, "1"); st.rerun()
                    with ox:
                        sel = "X" in st.session_state.selections[gid]
                        if st.button("X", key=f"bx_{gid}", type="primary" if sel else "secondary"):
                            handle_click(gid, "X"); st.rerun()
                    with o2:
                        sel = "2" in st.session_state.selections[gid]
                        if st.button("2", key=f"b2_{gid}", type="primary" if sel else "secondary"):
                            handle_click(gid, "2"); st.rerun()
                
                st.markdown('<hr>', unsafe_allow_html=True)

    # --- FINALIZAÇÃO ---
    if st.button("🚀 GERAR BILHETES SNIPER", type="primary", use_container_width=True):
        if not st.session_state.anchors:
            st.warning("⚠️ Selecione pelo menos uma Âncora (estrela) para fixar os resultados.")
        else:
            # Lógica de Matriz aqui...
            st.success(f"Bilhetes em processamento para o investimento de R$ {investimento:.2f}")

else:
    st.info("Aguardando dados da rodada...")