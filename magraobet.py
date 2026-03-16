import streamlit as st
import pandas as pd
import requests
import random
import datetime
from itertools import product

# --- TRATAMENTO HÍBRIDO DE API KEY ---
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

# --- CACHE DE DADOS (O Segredo para economizar a API) ---
# O 'ttl=3600' significa que o sistema só vai à internet buscar jogos 1 vez por hora.
@st.cache_data(ttl=3600)
def buscar_dados_cached(api_key):
    if not api_key: return None, "Aguardando chave..."
    sport_key = "soccer_brazil_campeonato_serie_a"
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={api_key}&regions=eu&markets=h2h&oddsFormat=decimal"
    try:
        res = requests.get(url)
        if res.status_code == 200:
            return res.json(), None
        elif res.status_code == 401:
            return None, "Chave Inválida"
        elif res.status_code == 429:
            return None, "Limite de Uso Excedido (API esgotada)"
        else:
            return None, f"Erro {res.status_code}"
    except:
        return None, "Erro de Conexão"

# --- ESTILO MOBILE ---
st.markdown("""
    <style>
    div.stButton > button { width: 100%; height: 60px; font-size: 20px !important; border-radius: 12px; }
    .stCheckbox { padding: 12px; border-radius: 12px; background: #262730; margin-bottom: 8px; border: 1px solid #444; }
    </style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ Ajustes")
    
    # Campo de chave manual se não houver nos Secrets
    if not api_key_disponivel:
        API_KEY = st.text_input("Insira a API Key:", type="password")
        if API_KEY: api_key_disponivel = True

    banca = st.number_input("Investimento (R$)", value=50, step=1, format="%d")
    qtd_bilhetes = st.slider("Qtd. Bilhetes", 1, 30, 10)
    
    filtro_tempo = st.radio("Período:", ["Próximos 3 dias", "Próximos 7 dias"])
    dias_limit = 3 if "3" in filtro_tempo else 7
    
    # Botão para forçar atualização se necessário
    if st.button("🔄 Forçar Atualização de Jogos"):
        st.cache_data.clear()
        st.rerun()

st.title("🎯 MagraoBet Sniper")

if not api_key_disponivel:
    st.warning("⚠️ Insira a API Key na barra lateral.")
    st.stop()

# Chama a função com Cache
with st.spinner('A carregar jogos (Economizando API)...'):
    data, erro = buscar_dados_cached(API_KEY)

if erro:
    st.error(f"❌ {erro}")
    if "Limite" in erro:
        st.info("A tua cota de 500 buscas da The Odds API terminou. Terás de esperar o próximo mês ou usar outra chave.")
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
                # Verifica se existem bookmakers e odds
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

        if st.button("🔥 GERAR BILHETES SNIPER", type="primary"):
            if not ancoras_finais:
                st.error("Seleciona pelo menos 1 âncora.")
            else:
                op_jogo = [[{"j": v['jogo'], "r": o, "d": v['odds'][o]} for o in v['opcoes']] for v in vars_config]
                todas_combos = list(product(*op_jogo))
                selecao = random.sample(todas_combos, min(len(todas_combos), qtd_bilhetes))
                
                stake = banca / len(selecao)
                for i, combo in enumerate(selecao):
                    odd_total = 1.0
                    for a in ancoras_finais: odd_total *= a['odd']
                    for v in combo: odd_total *= v['d']
                    with st.expander(f"🎫 Bilhete #{i+1} | Odd: {odd_total:.2f}"):
                        st.write(f"💰 **Retorno: R$ {stake * odd_total:.2f}**")
                        resumo = [[a['jogo'], a['res']] for a in ancoras_finais] + [[v['j'], v['r']] for v in combo]
                        st.table(pd.DataFrame(resumo, columns=["Jogo", "Palpite"]))
    else:
        st.warning("Nenhum jogo encontrado no período.")