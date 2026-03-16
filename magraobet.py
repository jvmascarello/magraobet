import streamlit as st
import pandas as pd
import requests
import random
import datetime
from itertools import product

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="MagraoBet Sniper", layout="wide", initial_sidebar_state="collapsed")

# --- CSS AVANÇADO (ANTI-STACKING MOBILE & FLASHCORE) ---
st.markdown("""
    <style>
    /* Fundo e Container Principal */
    .stApp { background-color: #0b161b; color: #e4e4e4; }
    header { visibility: hidden; }
    .main .block-container { padding-top: 1rem; padding-bottom: 2rem; max-width: 1000px; }

    /* FORÇAR LAYOUT HORIZONTAL NO CELULAR (CRÍTICO) */
    div[data-testid="stHorizontalBlock"] {
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
        gap: 0px !important;
    }
    
    /* Impedir que colunas individuais quebrem ou fiquem verticais */
    [data-testid="column"] {
        width: auto !important;
        flex: 1 1 auto !important;
        min-width: 0px !important;
    }

    /* Painel de Controle Superior */
    .config-card {
        background-color: #121e24;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #1e2d35;
        margin-bottom: 15px;
    }

    /* Estilização dos Botões 1X2 Compactos */
    .stButton > button {
        border-radius: 3px;
        font-weight: bold;
        border: 1px solid #2d3d46;
        background-color: #1e2d35;
        color: #a0a0a0;
        height: 32px !important;
        line-height: 1 !important;
        padding: 0px !important;
        margin: 0px !important;
        width: 100%;
        font-size: 0.8rem !important;
    }
    
    /* Cores de Seleção */
    .stButton > button:active, .stButton > button:focus { outline: none !important; }
    
    /* Estrela e Lixeira Custom (Ajuste de visibilidade) */
    .icon-btn button {
        background: transparent !important;
        border: none !important;
        font-size: 1.2rem !important;
        color: #4b5563 !important;
    }

    /* Tipografia Profissional */
    .team-name { font-size: 0.85rem; font-weight: 600; color: #ffffff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .game-time { font-size: 0.7rem; color: #8a9499; margin-right: 5px; }
    
    /* Divisores */
    hr { margin: 5px 0 !important; border-color: #1e2d35 !important; opacity: 0.5; }
    
    /* Ajuste de Margens das Colunas */
    div[data-testid="column"] > div { padding: 0 2px !important; }
    </style>
""", unsafe_allow_html=True)

# --- TRATAMENTO DE ESTADO ---
if 'deleted' not in st.session_state: st.session_state.deleted = set()
if 'selections' not in st.session_state: st.session_state.selections = {} 
if 'anchors' not in st.session_state: st.session_state.anchors = set()
if 'periodo' not in st.session_state: st.session_state.periodo = 3

# --- API OTIMIZADA COM CACHE ---
@st.cache_data(ttl=3600)
def get_data(api_key):
    if not api_key: return None, "Chave API ausente"
    # Endpoints para Brasileirão Série A
    url = f"https://api.the-odds-api.com/v4/sports/soccer_brazil_campeonato/odds/?apiKey={api_key}&regions=eu&markets=h2h&oddsFormat=decimal"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200: return res.json(), None
        return None, f"Erro API: {res.status_code}"
    except: return None, "Falha de conexão"

# --- TÍTULO ---
st.title("🎯 MagraoBet Sniper")

# --- PAINEL DE CONTROLE (PC E CELULAR) ---
with st.container():
    st.markdown('<div class="config-card">', unsafe_allow_html=True)
    c_inv, c_bil, c_dias = st.columns([1, 1, 2])
    with c_inv: investimento = st.number_input("Invest. R$", value=50, step=5)
    with c_bil: n_bilhetes = st.number_input("Bilhetes", value=10, min_value=1)
    with c_dias:
        st.write("Período (Próximos Dias)")
        d1, d2, d3 = st.columns(3)
        if d1.button("3D", type="primary" if st.session_state.periodo==3 else "secondary", use_container_width=True):
            st.session_state.periodo = 3; st.rerun()
        if d2.button("4D", type="primary" if st.session_state.periodo==4 else "secondary", use_container_width=True):
            st.session_state.periodo = 4; st.rerun()
        if d3.button("5D", type="primary" if st.session_state.periodo==5 else "secondary", use_container_width=True):
            st.session_state.periodo = 5; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# API Key Check
api_key = st.secrets.get("API_KEY", "")
if not api_key:
    api_key = st.text_input("Cole sua Chave API aqui:", type="password")
    if not api_key: st.stop()

# Busca de Dados
with st.spinner("Sincronizando..."):
    data, erro = get_data(api_key)

if erro:
    st.error(erro)
    if st.button("🔄 Recarregar Dados"): st.cache_data.clear(); st.rerun()
    st.stop()

# --- LISTAGEM DE JOGOS ---
if data:
    agora = datetime.datetime.now(datetime.timezone.utc)
    limite = agora + datetime.timedelta(days=st.session_state.periodo)
    
    valid_games = []
    for g in data:
        if g['id'] in st.session_state.deleted: continue
        dt = datetime.datetime.fromisoformat(g['commence_time'].replace('Z', '+00:00'))
        if agora < dt <= limite: valid_games.append((g, dt))

    if not valid_games:
        st.info("Nenhum jogo encontrado.")
    else:
        # Tabela Header
        h_fix, h_dt, h_name, h_1x2, h_del = st.columns([0.6, 1.2, 3.5, 3, 0.6])
        h_fix.caption("FIX")
        h_dt.caption("DATA")
        h_name.caption("JOGO")
        h_1x2.caption("1  X  2")
        h_del.caption("OFF")
        st.markdown('<hr>', unsafe_allow_html=True)

        for game, dt in valid_games:
            gid = game['id']
            home, away = game['home_team'], game['away_team']
            
            # Estado inicial
            if gid not in st.session_state.selections: st.session_state.selections[gid] = {"1"}

            # LINHA DO JOGO
            c_fix, c_dt, c_name, c_1x2, c_del = st.columns([0.6, 1.2, 3.5, 3, 0.6])
            
            with c_fix:
                is_anc = gid in st.session_state.anchors
                icon = "⭐" if is_anc else "☆"
                if st.button(icon, key=f"anc_btn_{gid}"):
                    if is_anc: st.session_state.anchors.discard(gid)
                    else: 
                        st.session_state.anchors.add(gid)
                        st.session_state.selections[gid] = {list(st.session_state.selections[gid])[0]}
                    st.rerun()
            
            with c_dt:
                st.markdown(f"<div class='game-time'>{dt.astimezone().strftime('%d/%m')}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='game-time' style='font-size:0.6rem'>{dt.astimezone().strftime('%H:%M')}</div>", unsafe_allow_html=True)
            
            with c_name:
                color = "#00c853" if gid in st.session_state.anchors else "#ffffff"
                st.markdown(f"<div class='team-name' style='color:{color}'>{home} <br> {away}</div>", unsafe_allow_html=True)
            
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
            
            st.markdown('<hr>', unsafe_allow_html=True)

        # --- GERADOR DE MATRIZ CORRIGIDO ---
        st.write("")
        if st.button("🚀 GERAR BILHETES SNIPER", use_container_width=True, type="primary"):
            if not st.session_state.anchors:
                st.error("Selecione pelo menos um jogo como Âncora (Estrela).")
            else:
                anc_list, var_list = [], []
                
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
                    amostra = random.sample(combos, min(len(combos), n_bilhetes))
                    
                    st.success(f"Matriz Gerada: {len(amostra)} bilhetes.")
                    stake_fixa = investimento / len(amostra)
                    
                    for idx, combo in enumerate(amostra):
                        odd_total = 1.0
                        detalhes = []
                        for a in anc_list:
                            odd_total *= a['odd']
                            detalhes.append({"Jogo": a['jogo'], "Palpite": f"FIXO: {a['res']}", "Odd": a['odd']})
                        for v in combo:
                            odd_total *= v['o']
                            detalhes.append({"Jogo": v['j'], "Palpite": v['r'], "Odd": v['o']})
                        
                        with st.expander(f"🎫 Bilhete #{idx+1} | Odd: {odd_total:.2f} | Retorno: R$ {stake_fixa*odd_total:.2f}"):
                            st.table(pd.DataFrame(detalhes))
                            st.caption(f"Valor da Aposta: R$ {stake_fixa:.2f}")
                else:
                    st.info("Apenas jogos âncoras selecionados. Matriz de 1 bilhete único.")
                    odd_total = 1.0
                    detalhes = []
                    for a in anc_list:
                        odd_total *= a['odd']
                        detalhes.append({"Jogo": a['jogo'], "Palpite": f"FIXO: {a['res']}", "Odd": a['odd']})
                    st.table(pd.DataFrame(detalhes))
                    st.write(f"Odd: {odd_total:.2f} | Retorno: R$ {investimento*odd_total:.2f}")