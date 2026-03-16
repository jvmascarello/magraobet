import streamlit as st
import pandas as pd
import requests
import random
import datetime
from itertools import product

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="MagraoBet Sniper", layout="wide", initial_sidebar_state="collapsed")

# --- CSS PROFISSIONAL (MOBILE-PORTRAIT-FIRST) ---
st.markdown("""
    <style>
    /* Reset e Fundo */
    .stApp { background-color: #0b161b; color: #e4e4e4; }
    header { visibility: hidden; }
    .main .block-container { padding-top: 1rem; padding-bottom: 2rem; max-width: 1000px; margin: auto; }

    /* UNIFICAÇÃO DO PAINEL DE CONFIGURAÇÃO */
    .config-card {
        background-color: #121e24;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #1e2d35;
        margin-bottom: 20px;
    }

    /* FORÇAR LAYOUT HORIZONTAL ABSOLUTO NO MOBILE */
    [data-testid="stHorizontalBlock"] {
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
        gap: 2px !important;
    }
    
    [data-testid="column"] {
        width: auto !important;
        flex: 1 1 auto !important;
        min-width: 0px !important;
    }

    /* ESTILIZAÇÃO DOS BOTÕES (FEEDBACK VISUAL PERMANENTE) */
    .stButton > button {
        border-radius: 4px;
        font-weight: bold;
        border: 1px solid #2d3d46;
        background-color: #1e2d35;
        color: #a0a0a0;
        height: 35px !important;
        padding: 0 !important;
        width: 100%;
        font-size: 0.8rem !important;
        transition: 0.3s;
    }

    /* BOTÕES SELECIONADOS (VERDE PARA 1 e 2, LARANJA PARA X) */
    /* Usamos a lógica de 'Primary' do Streamlit para manter o estado visual */
    button[kind="primary"] {
        color: white !important;
        border: none !important;
    }
    
    /* Customizando o Primary Verde (Default) */
    div.win-btn button[kind="primary"] {
        background-color: #00c853 !important;
    }
    
    /* Customizando o Primary Laranja para o Empate */
    div.draw-btn button[kind="primary"] {
        background-color: #ffab00 !important;
    }

    /* TIPOGRAFIA E ELEMENTOS DA LINHA */
    .team-text {
        font-size: 0.75rem;
        font-weight: 700;
        color: #ffffff;
        line-height: 1.1;
        white-space: normal;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    .game-info { font-size: 0.65rem; color: #8a9499; }
    .anchor-active { color: #00ff00 !important; }

    /* HR Customizado */
    hr { margin: 8px 0 !important; border-color: #1e2d35 !important; opacity: 0.5; }

    /* Ajuste de Margens */
    div[data-testid="column"] > div { padding: 0 1px !important; }

    /* Ocultar elementos desnecessários */
    div[data-testid="stMetricValue"] { font-size: 1.2rem; }
    </style>
""", unsafe_allow_html=True)

# --- TRATAMENTO DE ESTADO ---
if 'deleted' not in st.session_state: st.session_state.deleted = set()
if 'selections' not in st.session_state: st.session_state.selections = {} 
if 'anchors' not in st.session_state: st.session_state.anchors = set()
if 'periodo' not in st.session_state: st.session_state.periodo = 3

# --- API COM CACHE AGGRESSIVO ---
@st.cache_data(ttl=3600)
def get_odds(api_key):
    if not api_key: return None, "Chave API ausente"
    # Foco no Brasileirão Série A
    url = f"https://api.the-odds-api.com/v4/sports/soccer_brazil_campeonato/odds/?apiKey={api_key}&regions=eu&markets=h2h&oddsFormat=decimal"
    try:
        res = requests.get(url, timeout=12)
        if res.status_code == 200: return res.json(), None
        return None, f"Erro: {res.status_code}"
    except: return None, "Falha na conexão"

# --- INTERFACE ---
st.markdown("<h2 style='text-align: center; color: white;'>🎯 MagraoBet Sniper</h2>", unsafe_allow_html=True)

# PAINEL DE CONFIGURAÇÃO UNIFICADO
with st.container():
    st.markdown('<div class="config-card">', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1: 
        investimento = st.number_input("Invest. R$", value=50, step=10)
    with c2: 
        n_bilhetes = st.number_input("Bilhetes", value=10, min_value=1)
    with c3:
        st.caption("Período (Próximos Dias)")
        p1, p2, p3 = st.columns(3)
        if p1.button("3 Dias", type="primary" if st.session_state.periodo==3 else "secondary", use_container_width=True):
            st.session_state.periodo = 3; st.rerun()
        if p2.button("4 Dias", type="primary" if st.session_state.periodo==4 else "secondary", use_container_width=True):
            st.session_state.periodo = 4; st.rerun()
        if p3.button("5 Dias", type="primary" if st.session_state.periodo==5 else "secondary", use_container_width=True):
            st.session_state.periodo = 5; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# Key Auth
api_key = st.secrets.get("API_KEY", "")
if not api_key:
    api_key = st.text_input("Chave API Sniper:", type="password")
    if not api_key: st.stop()

# Busca
with st.spinner("Sincronizando..."):
    data, erro = get_odds(api_key)

if erro:
    st.error(erro)
    if st.button("🔄 Recarregar"): st.cache_data.clear(); st.rerun()
    st.stop()

# LISTAGEM
if data:
    agora = datetime.datetime.now(datetime.timezone.utc)
    limite = agora + datetime.timedelta(days=st.session_state.periodo)
    
    jogos = []
    for g in data:
        if g['id'] in st.session_state.deleted: continue
        dt = datetime.datetime.fromisoformat(g['commence_time'].replace('Z', '+00:00'))
        if agora < dt <= limite: jogos.append((g, dt))

    if not jogos:
        st.info("Nenhum jogo disponível para este período.")
    else:
        # Cabeçalho da Tabela
        h_f, h_d, h_j, h_o, h_x = st.columns([0.5, 0.8, 3, 3, 0.5])
        h_f.caption("FIX")
        h_d.caption("DATA")
        h_j.caption("PARTIDA")
        h_o.caption("PALPITE (1 X 2)")
        h_x.caption("OFF")
        st.markdown('<hr>', unsafe_allow_html=True)

        for game, dt in jogos:
            gid = game['id']
            home, away = game['home_team'], game['away_team']
            
            if gid not in st.session_state.selections: st.session_state.selections[gid] = {"1"}

            # LINHA DO JOGO
            c_fix, c_dt, c_name, c_1x2, c_del = st.columns([0.5, 0.8, 3, 3, 0.5])
            
            with c_fix:
                is_anc = gid in st.session_state.anchors
                icon = "⭐" if is_anc else "☆"
                if st.button(icon, key=f"star_{gid}"):
                    if is_anc: st.session_state.anchors.discard(gid)
                    else: 
                        st.session_state.anchors.add(gid)
                        st.session_state.selections[gid] = {list(st.session_state.selections[gid])[0]}
                    st.rerun()
            
            with c_dt:
                st.markdown(f"<div class='game-info'>{dt.astimezone().strftime('%d/%m')}<br>{dt.astimezone().strftime('%H:%M')}</div>", unsafe_allow_html=True)
            
            with c_name:
                active_class = "anchor-active" if gid in st.session_state.anchors else ""
                st.markdown(f"<div class='team-text {active_class}'>{home}<br>{away}</div>", unsafe_allow_html=True)
            
            with c_1x2:
                o1, ox, o2 = st.columns(3)
                def handle_bet(val):
                    if gid in st.session_state.anchors: st.session_state.selections[gid] = {val}
                    else:
                        curr = st.session_state.selections[gid]
                        if val in curr and len(curr) > 1: curr.remove(val)
                        else: curr.add(val)

                with o1:
                    st.markdown('<div class="win-btn">', unsafe_allow_html=True)
                    if st.button("1", key=f"b1_{gid}", type="primary" if "1" in st.session_state.selections[gid] else "secondary"):
                        handle_bet("1"); st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                with ox:
                    st.markdown('<div class="draw-btn">', unsafe_allow_html=True)
                    if st.button("X", key=f"bx_{gid}", type="primary" if "X" in st.session_state.selections[gid] else "secondary"):
                        handle_bet("X"); st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                with o2:
                    st.markdown('<div class="win-btn">', unsafe_allow_html=True)
                    if st.button("2", key=f"b2_{gid}", type="primary" if "2" in st.session_state.selections[gid] else "secondary"):
                        handle_bet("2"); st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
            
            with c_del:
                if st.button("🗑️", key=f"del_{gid}"):
                    st.session_state.deleted.add(gid); st.rerun()
            
            st.markdown('<hr>', unsafe_allow_html=True)

        # GERADOR
        st.write("")
        if st.button("🚀 GERAR MATRIZ SNIPER", use_container_width=True, type="primary"):
            if not st.session_state.anchors:
                st.error("Selecione pelo menos uma Âncora (Estrela).")
            else:
                anc_final, var_final = [], []
                for g_data, _ in jogos:
                    id_g = g_data['id']
                    try:
                        m = g_data['bookmakers'][0]['markets'][0]['outcomes']
                        o_map = {
                            "1": next(o['price'] for o in m if o['name'] == g_data['home_team']),
                            "2": next(o['price'] for o in m if o['name'] == g_data['away_team']),
                            "X": next(o['price'] for o in m if o['name'] == 'Draw')
                        }
                    except: continue

                    sels = st.session_state.selections[id_g]
                    if id_g in st.session_state.anchors:
                        choice = list(sels)[0]
                        anc_final.append({"j": f"{g_data['home_team']} x {g_data['away_team']}", "r": choice, "o": o_map[choice]})
                    else:
                        var_final.append([{"j": f"{g_data['home_team']} x {g_data['away_team']}", "r": s, "o": o_map[s]} for s in sels])

                if var_final:
                    combos = list(product(*var_final))
                    amostra = random.sample(combos, min(len(combos), n_bilhetes))
                    st.success(f"Matriz Gerada com {len(amostra)} bilhetes.")
                    stake_unit = investimento / len(amostra)
                    
                    for i, bilhete in enumerate(amostra):
                        odd_t = 1.0
                        rows = []
                        for a in anc_final:
                            odd_t *= a['o']
                            rows.append([a['j'], f"FIXO: {a['r']}", a['o']])
                        for v in bilhete:
                            odd_t *= v['o']
                            rows.append([v['j'], v['r'], v['o']])
                        
                        with st.expander(f"🎫 Bilhete #{i+1} | Odd: {odd_t:.2f} | Retorno: R$ {stake_unit*odd_t:.2f}"):
                            st.table(pd.DataFrame(rows, columns=["Jogo", "Palpite", "Odd"]))