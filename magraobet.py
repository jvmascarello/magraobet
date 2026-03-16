import streamlit as st
import pandas as pd
import requests
import random
import datetime
from itertools import product

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="MagraoBet Sniper", layout="wide", initial_sidebar_state="collapsed")

# --- CSS PROFISSIONAL (MOBILE-FIRST & FLASHCORE STYLE) ---
st.markdown("""
    <style>
    /* Reset e Fundo */
    .stApp { background-color: #0b161b; color: #e4e4e4; }
    header { visibility: hidden; }
    .main .block-container { padding-top: 2rem; padding-bottom: 2rem; max-width: 900px; }

    /* Painel de Controle Superior */
    .config-card {
        background-color: #121e24;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #1e2d35;
        margin-bottom: 20px;
    }

    /* Forçar colunas horizontais no Mobile */
    [data-testid="column"] {
        flex-direction: row !important;
        align-items: center !important;
        min-width: 0px !important;
    }
    
    /* Linha do Jogo */
    .game-row {
        background-color: #121e24;
        border-bottom: 1px solid #1e2d35;
        padding: 10px 5px;
        display: flex;
        align-items: center;
        width: 100%;
    }

    /* Estilização dos Botões 1X2 */
    .stButton > button {
        border-radius: 4px;
        font-weight: bold;
        border: 1px solid #2d3d46;
        background-color: #1e2d35;
        color: #a0a0a0;
        height: 35px;
        transition: 0.2s;
        margin: 0 2px;
    }
    
    /* Cores de Seleção */
    .btn-selected { background-color: #00c853 !important; color: white !important; border: 1px solid #00c853 !important; }
    .btn-selected-x { background-color: #ffab00 !important; color: white !important; border: 1px solid #ffab00 !important; }

    /* Estilo da Estrela */
    .star-active { color: #00c853 !important; font-size: 1.2rem; }
    .star-inactive { color: #4b5563 !important; font-size: 1.2rem; }

    /* Tipografia */
    .team-name { font-size: 0.95rem; font-weight: 600; color: #ffffff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .game-time { font-size: 0.75rem; color: #8a9499; }
    
    /* Esconder labels de checkbox */
    div[data-testid="stCheckbox"] label { display: none; }
    </style>
""", unsafe_allow_html=True)

# --- TRATAMENTO DE ESTADO ---
if 'deleted' not in st.session_state: st.session_state.deleted = set()
if 'selections' not in st.session_state: st.session_state.selections = {} # {id: set()}
if 'anchors' not in st.session_state: st.session_state.anchors = set()
if 'periodo' not in st.session_state: st.session_state.periodo = 3

# --- API E OTIMIZAÇÃO ---
@st.cache_data(ttl=3600) # Cache de 1 hora para economizar API
def get_data(api_key):
    if not api_key: return None, "Chave API ausente"
    url = f"https://api.the-odds-api.com/v4/sports/soccer_brazil_campeonato/odds/?apiKey={api_key}&regions=eu&markets=h2h&oddsFormat=decimal"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200: return res.json(), None
        return None, f"Erro API: {res.status_code}"
    except: return None, "Falha de conexão"

# --- INTERFACE PRINCIPAL ---
st.title("🎯 MagraoBet Sniper")

# Painel de Controle Compacto
with st.container():
    st.markdown('<div class="config-card">', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1.5, 1.5, 3])
    with c1: investimento = st.number_input("Investimento R$", value=50, step=5)
    with c2: n_bilhetes = st.number_input("Qtd. Bilhetes", value=10, min_value=1)
    with c3:
        st.write("Período")
        d1, d2, d3 = st.columns(3)
        if d1.button("3 Dias", type="primary" if st.session_state.periodo==3 else "secondary", use_container_width=True):
            st.session_state.periodo = 3; st.rerun()
        if d2.button("4 Dias", type="primary" if st.session_state.periodo==4 else "secondary", use_container_width=True):
            st.session_state.periodo = 4; st.rerun()
        if d3.button("5 Dias", type="primary" if st.session_state.periodo==5 else "secondary", use_container_width=True):
            st.session_state.periodo = 5; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# API Key Check
api_key = st.secrets.get("API_KEY", "")
if not api_key:
    api_key = st.text_input("Chave API:", type="password")
    if not api_key: st.stop()

# Busca de Dados
with st.spinner("Sincronizando..."):
    data, erro = get_data(api_key)

if erro:
    st.error(erro)
    if st.button("🔄 Forçar Recarga"): st.cache_data.clear(); st.rerun()
    st.stop()

# Filtro e Exibição
if data:
    agora = datetime.datetime.now(datetime.timezone.utc)
    limite = agora + datetime.timedelta(days=st.session_state.periodo)
    
    valid_games = []
    for g in data:
        if g['id'] in st.session_state.deleted: continue
        dt = datetime.datetime.fromisoformat(g['commence_time'].replace('Z', '+00:00'))
        if agora < dt <= limite: valid_games.append((g, dt))

    if not valid_games:
        st.info("Nenhum jogo no período selecionado.")
    else:
        # Cabeçalho da Tabela
        st.markdown("""
            <div style="display: flex; padding: 0 10px; opacity: 0.6; font-size: 0.8rem; margin-bottom: 5px;">
                <div style="width: 10%">FIXO</div>
                <div style="width: 15%">DATA</div>
                <div style="width: 40%">CONFRONTO</div>
                <div style="width: 25%; text-align: center;">1 X 2</div>
                <div style="width: 10%; text-align: right;">LIMPAR</div>
            </div>
        """, unsafe_allow_html=True)

        for game, dt in valid_games:
            gid = game['id']
            home, away = game['home_team'], game['away_team']
            if gid not in st.session_state.selections: st.session_state.selections[gid] = {"1"}

            with st.container():
                # Grid customizado para não quebrar no mobile
                c_fix, c_dt, c_name, c_1x2, c_del = st.columns([1, 1.5, 3.5, 3, 1])
                
                with c_fix:
                    is_anc = st.checkbox("", key=f"anc_{gid}", value=(gid in st.session_state.anchors))
                    if is_anc: st.session_state.anchors.add(gid)
                    else: st.session_state.anchors.discard(gid)
                
                with c_dt:
                    st.markdown(f"<div class='game-time'>{dt.astimezone().strftime('%d/%m %H:%M')}</div>", unsafe_allow_html=True)
                
                with c_name:
                    color = "#00c853" if gid in st.session_state.anchors else "#ffffff"
                    st.markdown(f"<div class='team-name' style='color:{color}'>{home} x {away}</div>", unsafe_allow_html=True)
                
                with c_1x2:
                    o1, ox, o2 = st.columns(3)
                    def toggle(val):
                        if gid in st.session_state.anchors: st.session_state.selections[gid] = {val}
                        else:
                            curr = st.session_state.selections[gid]
                            if val in curr and len(curr) > 1: curr.remove(val)
                            else: curr.add(val)

                    with o1:
                        if st.button("1", key=f"b1_{gid}", type="primary" if "1" in st.session_state.selections[gid] else "secondary"):
                            toggle("1"); st.rerun()
                    with ox:
                        if st.button("X", key=f"bx_{gid}", type="primary" if "X" in st.session_state.selections[gid] else "secondary"):
                            toggle("X"); st.rerun()
                    with o2:
                        if st.button("2", key=f"b2_{gid}", type="primary" if "2" in st.session_state.selections[gid] else "secondary"):
                            toggle("2"); st.rerun()
                
                with c_del:
                    if st.button("🗑️", key=f"del_{gid}"):
                        st.session_state.deleted.add(gid); st.rerun()
            
            st.markdown('<hr style="margin: 0; border-color: #1e2d35;">', unsafe_allow_html=True)

        # --- GERADOR DE MATRIZ ---
        st.write("")
        if st.button("🚀 GERAR BILHETES SNIPER", use_container_width=True):
            if not st.session_state.anchors:
                st.error("⚠️ Selecione pelo menos um jogo como Âncora (Estrela).")
            else:
                # Coletar Dados para Matriz
                anc_list = []
                var_list = []
                
                for game, _ in valid_games:
                    gid = game['id']
                    try:
                        outcomes = game['bookmakers'][0]['markets'][0]['outcomes']
                        odds_map = {
                            "1": next(o['price'] for o in outcomes if o['name'] == game['home_team']),
                            "2": next(o['price'] for o in outcomes if o['name'] == game['away_team']),
                            "X": next(o['price'] for o in outcomes if o['name'] == 'Draw')
                        }
                    except: continue

                    sels = st.session_state.selections[gid]
                    if gid in st.session_state.anchors:
                        choice = list(sels)[0]
                        anc_list.append({"jogo": f"{game['home_team']} x {game['away_team']}", "res": choice, "odd": odds_map[choice]})
                    else:
                        ops = [{"j": f"{game['home_team']} x {game['away_team']}", "r": s, "o": odds_map[s]} for s in sels]
                        var_list.append(ops)

                if var_list:
                    combos = list(product(*var_list))
                    final_combos = random.sample(combos, min(len(combos), n_bilhetes))
                    
                    st.subheader(f"📋 {len(final_combos)} Bilhetes Sniper")
                    stake = investimento / len(final_combos)
                    
                    for i, combo in enumerate(final_combos):
                        odd_total = 1.0
                        resumo = []
                        for a in anc_list:
                            odd_total *= a['odd']
                            resumo.append([a['jogo'], f"FIXO: {a['res']}", a['odd']])
                        for v in combo:
                            odd_total *= v['o']
                            resumo.append([v['j'], v['r'], v['o']])
                        
                        with st.expander(f"🎫 Bilhete #{i+1} | Odd: {odd_total:.2f} | Retorno: R$ {stake*odd_total:.2f}"):
                            st.table(pd.DataFrame(resumo, columns=["Jogo", "Palpite", "Odd"]))
                            st.write(f"Investimento: R$ {stake:.2f}")