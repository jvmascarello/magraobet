import streamlit as st
import pandas as pd
import requests
import random
import datetime
from itertools import product

# --- SISTEMA DE CHAVE HÍBRIDA ---
api_key_disponivel = False
try:
    if "API_KEY" in st.secrets:
        API_KEY = st.secrets["API_KEY"]
        api_key_disponivel = True
    else:
        api_key_disponivel = False
except:
    api_key_disponivel = False

st.set_page_config(page_title="MagraoBet Sniper", layout="centered")

# --- CSS MOBILE ---
st.markdown("""
    <style>
    div.stButton > button { width: 100%; height: 60px; font-size: 20px !important; border-radius: 12px; background-color: #ff4b4b; color: white; }
    .stCheckbox { padding: 12px; border-radius: 12px; background: #262730; margin-bottom: 8px; border: 1px solid #444; }
    </style>
""", unsafe_allow_html=True)

# --- FUNÇÕES COM CACHE (ECONOMIA DE API) ---
@st.cache_data(ttl=3600)
def obter_liga_correta(api_key):
    """Descobre o ID atual do Brasileirão para evitar Erro 404"""
    url = f"https://api.the-odds-api.com/v4/sports/?apiKey={api_key}"
    try:
        res = requests.get(url)
        if res.status_code == 200:
            esportes = res.json()
            # Procura por ligas brasileiras ativas
            brasileiras = [s['key'] for s in esportes if 'brazil' in s['key'].lower() and 'soccer' in s['key'].lower()]
            return brasileiras[0] if brasileiras else "soccer_brazil_campeonato_serie_a"
        return "soccer_brazil_campeonato_serie_a"
    except:
        return "soccer_brazil_campeonato_serie_a"

@st.cache_data(ttl=3600)
def buscar_odds_cached(api_key, sport_key):
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={api_key}&regions=eu&markets=h2h&oddsFormat=decimal"
    try:
        res = requests.get(url)
        if res.status_code == 200: return res.json(), None
        return None, f"Erro {res.status_code}: {res.text}"
    except Exception as e: return None, str(e)

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Ajustes")
    if not api_key_disponivel:
        API_KEY = st.text_input("Insira a API Key:", type="password")
        if API_KEY: api_key_disponivel = True

    banca = st.number_input("Investimento (R$)", value=50, step=1, format="%d")
    qtd_bilhetes = st.slider("Qtd. Bilhetes", 1, 30, 10)
    
    filtro_tempo = st.radio("Período:", ["Próximos 3 dias", "Próximos 7 dias"])
    dias_limit = 3 if "3" in filtro_tempo else 7
    
    if st.button("🔄 Atualizar Jogos (Gasta 1 uso API)"):
        st.cache_data.clear()
        st.rerun()

st.title("🎯 MagraoBet Sniper")

if not api_key_disponivel:
    st.warning("⚠️ Insira a API Key na barra lateral.")
    st.stop()

# Execução principal
with st.spinner('A localizar liga e odds...'):
    liga_id = obter_liga_correta(API_KEY)
    data, erro = buscar_odds_cached(API_KEY, liga_id)

if erro:
    st.error(f"❌ Erro na API: {erro}")
    st.stop()

if data:
    agora = datetime.datetime.now(datetime.timezone.utc)
    limite = agora + datetime.timedelta(days=dias_limit)
    jogos_validos = []

    for game in data:
        try:
            dt_utc = datetime.datetime.fromisoformat(game['commence_time'].replace('Z', '+00:00'))
            if agora < dt_utc <= limite:
                home, away = game['home_team'], game['away_team']
                if not game['bookmakers']: continue
                odds = game['bookmakers'][0]['markets'][0]['outcomes']
                o1 = next(o['price'] for o in odds if o['name'] == home)
                o2 = next(o['price'] for o in odds if o['name'] == away)
                ox = next(o['price'] for o in odds if o['name'] == 'Draw')
                
                jogos_validos.append({
                    "id": game['id'],
                    "label": f"{dt_utc.astimezone().strftime('%d/%m %H:%M')} | {home} x {away}",
                    "jogo": f"{home} x {away}", "1": o1, "X": ox, "2": o2
                })
        except: continue

    if jogos_validos:
        st.header("📌 1. Definir Âncoras")
        ancoras_finais = []
        nomes_ancoras = []
        
        for j in jogos_validos:
            if st.checkbox(f"📍 {j['label']}", key=f"anc_{j['id']}"):
                res = st.radio(f"Vencerá:", ["1", "X", "2"], horizontal=True, key=f"res_{j['id']}")
                ancoras_finais.append({"jogo": j['jogo'], "res": res, "odd": j[res]})
                nomes_ancoras.append(j['label'])

        st.divider()
        st.header("🎲 2. Variáveis")
        jogos_v = [j for j in jogos_validos if j["label"] not in nomes_ancoras]
        vars_config = []
        
        for jv in jogos_v:
            with st.container(border=True):
                ativo = st.toggle(f"Incluir {jv['jogo']}", value=True, key=f"tog_{jv['id']}")
                if ativo:
                    palpites = st.multiselect("Variações:", ["1", "X", "2"], default=["1"], key=f"mul_{jv['id']}")
                    if palpites:
                        vars_config.append({"jogo": jv['jogo'], "opcoes": palpites, "odds": jv})

        if st.button("🔥 GERAR BILHETES SNIPER"):
            if not ancoras_finais:
                st.error("Seleciona pelo menos 1 âncora.")
            else:
                op_jogo = [[{"j": v['jogo'], "r": o, "d": v['odds'][o]} for o in v['opcoes']] for v in vars_config]
                combos = list(product(*op_jogo))
                selecao = random.sample(combos, min(len(combos), qtd_bilhetes))
                
                stake = banca / len(selecao)
                for i, combo in enumerate(selecao):
                    odd_total = 1.0
                    for a in ancoras_finais: odd_total *= a['odd']
                    for v in combo: odd_total *= v['d']
                    with st.expander(f"🎫 Bilhete #{i+1} | Odd: {odd_total:.2f}"):
                        st.write(f"💰 **Aposta: R$ {stake:.2f} | Retorno: R$ {stake * odd_total:.2f}**")
                        resumo = [[a['jogo'], a['res']] for a in ancoras_finais] + [[v['j'], v['r']] for v in combo]
                        st.table(pd.DataFrame(resumo, columns=["Jogo", "Palpite"]))
    else:
        st.warning("Nenhum jogo encontrado no período.")