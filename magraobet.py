import streamlit as st
import pandas as pd
import requests
import random
import datetime
from itertools import product

# =========================================================
# CONFIGURAÇÃO PRIVADA
API_KEY = '382e534fa4dfaa17600726e74b847a4e'
# =========================================================

st.set_page_config(page_title="MagraoBet v13.0", layout="wide")

def buscar_liga_ativa(api_key):
    url = f"https://api.the-odds-api.com/v4/sports/?apiKey={api_key}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            esportes = response.json()
            brasileiras = [s['key'] for s in esportes if 'brazil' in s['key'].lower() and 'soccer' in s['key'].lower()]
            return brasileiras[0] if brasileiras else "soccer_brazil_campeonato_serie_a"
        return "soccer_brazil_campeonato_serie_a"
    except: return "soccer_brazil_campeonato_serie_a"

def buscar_odds(api_key, sport_key):
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={api_key}&regions=eu&markets=h2h&oddsFormat=decimal"
    try:
        response = requests.get(url)
        if response.status_code == 200: return response.json(), None
        return None, f"Erro {response.status_code}"
    except Exception as e: return None, str(e)

st.title("🎯 MagraoBet: Sniper v13.0")
# Adicione isso logo após o st.title
with st.sidebar.expander("📖 Manual do Usuário", expanded=True):
    st.write("""
    1. Ajuste a **Data** da rodada.
    2. Escolha os **Fixos** (Âncoras).
    3. Desmarque os jogos ruins.
    4. Clique no **Botão de Fogo** 🔥.
    """)
st.sidebar.header("💰 Gestão Financeira")
banca_total = st.sidebar.number_input("Investimento Total (R$)", value=50.0)
num_bilhetes_desejados = st.sidebar.slider("Quantidade de Bilhetes Únicos", 1, 30, 10)

st.sidebar.subheader("📅 Período da Rodada")
hoje = datetime.date.today()
data_inicio = st.sidebar.date_input("Jogos a partir de:", value=hoje)
data_fim = st.sidebar.date_input("Jogos até:", value=data_inicio + datetime.timedelta(days=4))

with st.spinner('Sincronizando jogos da rodada...'):
    liga_ativa = buscar_liga_ativa(API_KEY)
    data, erro = buscar_odds(API_KEY, liga_ativa)

if data:
    jogos_brutos = []
    dt_inicio_comp = datetime.datetime.combine(data_inicio, datetime.time(0, 0, 0))
    dt_fim_comp = datetime.datetime.combine(data_fim, datetime.time(23, 59, 59))

    for game in data:
        try:
            dt_utc = datetime.datetime.fromisoformat(game['commence_time'].replace('Z', '+00:00'))
            dt_local = dt_utc.astimezone().replace(tzinfo=None)
            if dt_inicio_comp <= dt_local <= dt_fim_comp:
                home, away = game['home_team'], game['away_team']
                odds_raw = game['bookmakers'][0]['markets'][0]['outcomes']
                o1 = next(o['price'] for o in odds_raw if o['name'] == home)
                o2 = next(o['price'] for o in odds_raw if o['name'] == away)
                ox = next(o['price'] for o in odds_raw if o['name'] == 'Draw')
                jogos_brutos.append({
                    "id": game['id'], "exibicao": f"[{dt_local.strftime('%d/%m %H:%M')}] {home} x {away}",
                    "jogo": f"{home} x {away}", "data": dt_local, "1": o1, "X": ox, "2": o2
                })
        except: continue
    
    jogos_brutos = sorted(jogos_brutos, key=lambda x: x['data'])

    if jogos_brutos:
        # --- ETAPA 1: ÂNCORAS ---
        st.header("📌 1. Escolha das Âncoras")
        sel_anc = st.multiselect("Selecione seus fixos da rodada:", [j["exibicao"] for j in jogos_brutos])
        
        if sel_anc:
            ancoras_final, nomes_anc_exib = [], []
            cols_anc = st.columns(len(sel_anc))
            for i, item in enumerate(sel_anc):
                obj = next(j for j in jogos_brutos if j["exibicao"] == item)
                with cols_anc[i]:
                    res = st.selectbox(f"{obj['jogo']}", ["1", "X", "2"], key=f"anc_{obj['id']}")
                    ancoras_final.append({"jogo": obj['jogo'], "res": res, "odd": obj[res]})
                    nomes_anc_exib.append(obj['exibicao'])

            # --- ETAPA 2: LIMPEZA E VARIÁVEIS ---
            st.header("🎲 2. Limpeza e Configuração de Variáveis")
            st.caption("Desmarque os jogos que não quer nos bilhetes e defina seus palpites para os demais.")
            
            jogos_restantes = [j for j in jogos_brutos if j["exibicao"] not in nomes_anc_exib]
            vars_config = []
            
            cv = st.columns(3)
            for i, jogo in enumerate(jogos_restantes):
                with cv[i % 3]:
                    with st.container(border=True):
                        # Checkbox para inclusão/limpeza
                        manter = st.checkbox(f"Incluir: {jogo['jogo']}", value=True, key=f"check_{jogo['id']}")
                        if manter:
                            res_v = st.multiselect(f"Palpites para {jogo['jogo']}:", ["1", "X", "2"], default=["1"], key=f"var_{jogo['id']}")
                            if res_v:
                                vars_config.append({"jogo": jogo["jogo"], "opcoes": res_v, "odds": jogo})

            if st.button("🚀 GERAR MATRIZ SNIPER ÚNICA"):
                # Lógica de Produto Cartesiano para evitar duplicatas
                # Criamos listas de palpites para cada jogo variável
                opcoes_por_jogo = []
                for v in vars_config:
                    palpites_jogo = []
                    for opt in v['opcoes']:
                        palpites_jogo.append({"jogo": v['jogo'], "res": opt, "odd": v['odds'][opt]})
                    opcoes_por_jogo.append(palpites_jogo)

                if not opcoes_por_jogo:
                    st.error("Selecione pelo menos um jogo variável com palpites.")
                else:
                    # Gera todas as combinações possíveis (ÚNICAS)
                    todas_combos = list(product(*opcoes_por_jogo))
                    
                    # Se houver mais combinações do que o desejado, sorteamos uma amostra sem repetição
                    if len(todas_combos) > num_bilhetes_desejados:
                        combos_selecionados = random.sample(todas_combos, num_bilhetes_desejados)
                    else:
                        combos_selecionados = todas_combos
                        if len(todas_combos) < num_bilhetes_desejados:
                            st.warning(f"Sua configuração permitiu apenas {len(todas_combos)} combinações únicas.")

                    stake = banca_total / len(combos_selecionados)
                    
                    st.markdown(f"### 📋 Plano: {len(combos_selecionados)} Bilhetes Únicos | R$ {stake:.2f} cada")
                    grid = st.columns(2)
                    
                    for idx, combo in enumerate(combos_selecionados):
                        odd_t = 1.0
                        for a in ancoras_final: odd_t *= a['odd']
                        for v in combo: odd_t *= v['odd']
                        
                        with grid[idx % 2]:
                            with st.expander(f"🎫 BILHETE #{idx+1} - ODD: {odd_t:.2f}"):
                                st.write(f"💰 Retorno: **R$ {stake * odd_t:.2f}**")
                                resumo = [[a['jogo'], a['res'], f"{a['odd']:.2f}"] for a in ancoras_final] + \
                                         [[v['jogo'], v['res'], f"{v['odd']:.2f}"] for v in combo]
                                st.table(pd.DataFrame(resumo, columns=["Jogo", "Palpite", "Odd"]))
        else:
            st.info("Aguardando seleção de âncoras...")
    else:
        st.warning("Nenhum jogo encontrado para o período.")