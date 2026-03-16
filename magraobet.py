import streamlit as st
import pandas as pd
import requests
import random
import datetime
from itertools import product

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="MagraoBet Sniper", layout="wide", initial_sidebar_state="expanded")

# --- ESTILIZAÇÃO CUSTOMIZADA (FLASHCORE STYLE) ---
st.markdown("""
    <style>
    /* Fundo Geral */
    .stApp {
        background-color: #0b161b;
        color: #e4e4e4;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #121e24;
        border-right: 1px solid #1e2d35;
    }

    /* Card do Jogo (Linha) */
    .game-row {
        background-color: #121e24;
        border-bottom: 1px solid #1e2d35;
        padding: 8px 15px;
        display: flex;
        align-items: center;
        transition: background 0.2s;
    }
    .game-row:hover {
        background-color: #18272f;
    }

    /* Estilização das Estrelas (Checkboxes escondidos) */
    div[data-testid="stCheckbox"] {
        margin-bottom: 0px;
    }
    
    /* Botões 1 X 2 customizados */
    .stButton > button {
        border-radius: 4px;
        padding: 5px 10px;
        background-color: #1e2d35;
        border: 1px solid #2d3d46;
        color: #a0a0a0;
        font-weight: bold;
        transition: 0.2s;
        width: 100%;
    }
    
    /* Cores Ativas */
    .active-btn > div > button {
        background-color: #00c853 !important;
        color: white !important;
        border: 1px solid #00c853 !important;
    }
    
    .active-btn-x > div > button {
        background-color: #ffab00 !important;
        color: white !important;
        border: 1px solid #ffab00 !important;
    }

    /* Badge de Retorno */
    .ticket-card {
        background-color: #1a2a33;
        border-left: 5px solid #00c853;
        padding: 15px;
        margin-bottom: 10px;
        border-radius: 5px;
    }

    /* Títulos e Textos */
    h1, h2, h3 { color: #ffffff !important; }
    p, span, label { font-family: 'Roboto', sans-serif; }
    
    /* Esconder elementos desnecessários do Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- TRATAMENTO SEGURO DE SECRETS ---
def get_api_key_safe():
    try:
        # Tenta acessar os secrets apenas se eles existirem
        if "API_KEY" in st.secrets:
            return st.secrets["API_KEY"]
    except Exception:
        # Se falhar (localmente sem o arquivo), retorna vazio para preenchimento manual
        return ""
    return ""

# --- INICIALIZAÇÃO DO ESTADO ---
if 'deleted_games' not in st.session_state:
    st.session_state.deleted_games = set()
if 'selections' not in st.session_state:
    st.session_state.selections = {} # ID: set("1", "X", "2")
if 'anchors' not in st.session_state:
    st.session_state.anchors = set() # ID

# --- FUNÇÕES DE DADOS ---
@st.cache_data(ttl=3600)
def buscar_dados(api_key):
    try:
        url = f"https://api.the-odds-api.com/v4/sports/soccer_brazil_campeonato_serie_a/odds/?apiKey={api_key}&regions=eu&markets=h2h&oddsFormat=decimal"
        res = requests.get(url)
        if res.status_code == 200:
            return res.json(), None
        elif res.status_code == 401:
            return None, "Chave API Inválida ou Expirada."
        return None, f"Erro na API: {res.status_code}"
    except Exception as e:
        return None, "Falha na conexão com a API."

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/5323/5323497.png", width=50)
    st.title("Sniper Control")
    
    # Busca a chave inicial de forma segura
    key_inicial = get_api_key_safe()
    api_key = st.text_input("Chave API (The Odds API):", type="password", value=key_inicial)
    
    if not api_key:
        st.warning("⚠️ Insira sua chave acima.")
    
    st.divider()
    banca = st.number_input("Investimento Total (R$)", value=50.0, step=5.0)
    qtd_bilhetes = st.slider("Quantidade de Bilhetes", 1, 100, 10)
    op_data = st.radio("Período de busca:", ["3 Dias", "7 Dias"])
    dias_lim = 3 if "3" in op_data else 7
    
    if st.button("🔄 Sincronizar Jogos", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# --- CONTEÚDO PRINCIPAL ---
st.title("🎯 MagraoBet Sniper")

if not api_key:
    st.info("💡 Por favor, insira sua Chave API na barra lateral para carregar os jogos.")
    st.stop()

with st.spinner("Buscando odds em tempo real..."):
    data, erro = buscar_dados(api_key)

if erro:
    st.error(f"❌ {erro}")
    st.stop()

if data:
    agora = datetime.datetime.now(datetime.timezone.utc)
    limite = agora + datetime.timedelta(days=dias_lim)
    
    jogos_filtrados = []
    for game in data:
        gid = game['id']
        if gid in st.session_state.deleted_games: continue
        
        dt_utc = datetime.datetime.fromisoformat(game['commence_time'].replace('Z', '+00:00'))
        if agora < dt_utc <= limite:
            jogos_filtrados.append((game, dt_utc))

    if not jogos_filtrados:
        st.warning("Nenhum jogo encontrado para o período selecionado.")
    else:
        # Cabeçalho da Tabela
        h_col1, h_col2, h_col3, h_col4, h_col5 = st.columns([0.5, 0.5, 1.5, 4, 3])
        h_col1.write("⭐")
        h_col2.write("🗑️")
        h_col3.write("Data/Hora")
        h_col4.write("Confronto")
        h_col5.write("Palpites (1 X 2)")
        st.divider()

        for game, dt_utc in jogos_filtrados:
            gid = game['id']
            home = game['home_team']
            away = game['away_team']
            
            if gid not in st.session_state.selections:
                st.session_state.selections[gid] = {"1"}

            with st.container():
                c_star, c_del, c_date, c_teams, c_odds = st.columns([0.5, 0.5, 1.5, 4, 3])
                
                with c_star:
                    is_anc = st.checkbox("", key=f"anc_{gid}", value=(gid in st.session_state.anchors), label_visibility="collapsed")
                    if is_anc: st.session_state.anchors.add(gid)
                    else: st.session_state.anchors.discard(gid)
                
                with c_del:
                    if st.button("🗑️", key=f"del_btn_{gid}"):
                        st.session_state.deleted_games.add(gid)
                        st.rerun()

                with c_date:
                    st.caption(dt_utc.astimezone().strftime("%d.%m %H:%M"))

                with c_teams:
                    label = f"**{home} vs {away}**" if gid in st.session_state.anchors else f"{home} vs {away}"
                    st.markdown(label)

                with c_odds:
                    o1, ox, o2 = st.columns(3)
                    
                    def toggle_selection(game_id, val):
                        is_ancora = game_id in st.session_state.anchors
                        current = st.session_state.selections[game_id]
                        if is_ancora:
                            st.session_state.selections[game_id] = {val}
                        else:
                            if val in current:
                                if len(current) > 1: current.remove(val)
                            else:
                                current.add(val)
                    
                    with o1:
                        style = "active-btn" if "1" in st.session_state.selections[gid] else ""
                        if st.button("1", key=f"b1_{gid}", css_class=style):
                            toggle_selection(gid, "1")
                            st.rerun()
                    
                    with ox:
                        style = "active-btn-x" if "X" in st.session_state.selections[gid] else ""
                        if st.button("X", key=f"bx_{gid}", css_class=style):
                            toggle_selection(gid, "X")
                            st.rerun()
                            
                    with o2:
                        style = "active-btn" if "2" in st.session_state.selections[gid] else ""
                        if st.button("2", key=f"b2_{gid}", css_class=style):
                            toggle_selection(gid, "2")
                            st.rerun()
                
                st.markdown('<div style="margin-bottom: 10px; border-bottom: 1px solid #1e2d35;"></div>', unsafe_allow_html=True)

        st.divider()
        if st.button("🚀 GERAR MATRIZ DE BILHETES", type="primary", use_container_width=True):
            if not st.session_state.anchors:
                st.error("⚠️ Selecione pelo menos uma Âncora (estrela) para fixar o resultado.")
            else:
                ancoras_data = []
                variantes_data = []
                
                for game, _ in jogos_filtrados:
                    gid = game['id']
                    home, away = game['home_team'], game['away_team']
                    try:
                        outcomes = game['bookmakers'][0]['markets'][0]['outcomes']
                        o_map = {
                            "1": next(o['price'] for o in outcomes if o['name'] == home),
                            "2": next(o['price'] for o in outcomes if o['name'] == away),
                            "X": next(o['price'] for o in outcomes if o['name'] == 'Draw')
                        }
                    except: continue

                    selecionados = st.session_state.selections[gid]
                    if gid in st.session_state.anchors:
                        res = list(selecionados)[0]
                        ancoras_data.append({"jogo": f"{home} x {away}", "res": res, "odd": o_map[res]})
                    else:
                        opcoes = [{"jogo": f"{home} x {away}", "res": s, "odd": o_map[s]} for s in selecionados]
                        variantes_data.append(opcoes)

                if variantes_data:
                    combos_possiveis = list(product(*variantes_data))
                    final_tickets = random.sample(combos_possiveis, min(len(combos_possiveis), qtd_bilhetes))
                else:
                    final_tickets = [[]]

                st.subheader(f"📋 Matriz Gerada ({len(final_tickets)} bilhetes)")
                stake_por_bilhete = banca / len(final_tickets)
                
                for i, variant in enumerate(final_tickets):
                    odd_total = 1.0
                    resumo = []
                    for a in ancoras_data:
                        odd_total *= a['odd']
                        resumo.append([a['jogo'], f"FIXO: {a['res']}", a['odd']])
                    for v in variant:
                        odd_total *= v['odd']
                        resumo.append([v['jogo'], v['res'], v['odd']])
                    
                    with st.expander(f"🎫 Bilhete #{i+1} | Odd: {odd_total:.2f} | Retorno: R$ {stake_por_bilhete * odd_total:.2f}"):
                        st.table(pd.DataFrame(resumo, columns=["Confronto", "Palpite", "Odd"]))
                        st.info(f"Aposta sugerida: R$ {stake_por_bilhete:.2f}")