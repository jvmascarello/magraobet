import streamlit as st
import pandas as pd
import requests
import random
import datetime
from itertools import product

# --- TRATAMENTO HÍBRIDO DE API KEY ---
# Tenta buscar no Streamlit Cloud; se falhar, abre campo na barra lateral
api_key_disponivel = False
try:
    if "API_KEY" in st.secrets:
        API_KEY = st.secrets["API_KEY"]
        api_key_disponivel = True
except:
    api_key_disponivel = False

st.set_page_config(page_title="MagraoBet Sniper", layout="centered")

# --- ESTILO MOBILE (Botões Grandes) ---
st.markdown("""
    <style>
    div.stButton > button { width: 100%; height: 60px; font-size: 20px !important; border-radius: 12px; }
    .stCheckbox { padding: 12px; border-radius: 12px; background: #262730; margin-bottom: 8px; border: 1px solid #444; }
    </style>
""", unsafe_allow_html=True)

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("⚙️ Ajustes")
    
    # Se não achou a chave nos segredos, pede para digitar
    if not api_key_disponivel:
        API_KEY = st.text_input("Chave de API requerida:", type="password")
        if API_KEY: api_key_disponivel = True
    
    # Investimento: Apenas inteiros, passo de 1
    banca = st.number_input("Investimento (R$)", value=50, step=1, format="%d")
    qtd_bilhetes = st.slider("Qtd. Bilhetes", 1, 30, 10)
    
    filtro_tempo = st.radio("Período da Rodada:", ["Próximos 3 dias", "Próximos 7 dias"])
    dias_limit = 3 if "3" in filtro_tempo else 7

def buscar_dados():
    if not API_KEY: return None, "Aguardando chave..."
    url = f"https://api.the-odds-api.com/v4/sports/soccer_brazil_campeonato_serie_a/odds/?apiKey={API_KEY}&regions=eu&markets=h2h&oddsFormat=decimal"
    try:
        res = requests.get(url)
        return (res.json(), None) if res.status_code == 200 else (None, "Chave Inválida ou Limite Excedido")
    except: return None, "Erro de Conexão"

st.title("🎯 MagraoBet Sniper")

if not api_key_disponivel:
    st.warning("⚠️ Insira a API Key na barra lateral para carregar os jogos.")
    st.stop()

with st.spinner('Sincronizando jogos...'):
    data, erro = buscar_dados()

if erro:
    st.error(f"❌ {erro}")
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
        st.header("📌 1. Defina suas Âncoras")
        ancoras_finais = []
        nomes_ancoras = []
        
        for j in jogos_validos:
            if st.checkbox(f"📍 {j['label']}", key=f"anc_{j['id']}"):
                res = st.radio(f"Resultado fixo para {j['jogo']}:", ["1", "X", "2"], horizontal=True, key=f"res_{j['id']}")
                ancoras_finais.append({"jogo": j['jogo'], "res": res, "odd": j[res]})
                nomes_ancoras.append(j['label'])

        st.divider()
        st.header("🎲 2. Limpeza e Variáveis")
        jogos_v = [j for j in jogos_validos if j["label"] not in nomes_ancoras]
        vars_config = []
        
        for jv in jogos_v:
            with st.container(border=True):
                ativo = st.toggle(f"Incluir {jv['jogo']}", value=True, key=f"tog_{jv['id']}")
                if ativo:
                    palpites = st.multiselect("Variações:", ["1", "X", "2"], default=["1"], key=f"mul_{jv['id']}")
                    if palpites:
                        vars_config.append({"jogo": jv['jogo'], "opcoes": palpites, "odds": jv})

        if st.button("🔥 GERAR MATRIZ SNIPER", type="primary"):
            if not ancoras_finais:
                st.error("Selecione ao menos 1 fixo.")
            else:
                op_jogo = [[{"j": v['jogo'], "r": o, "d": v['odds'][o]} for o in v['opcoes']] for v in vars_config]
                todas_combos = list(product(*op_jogo))
                selecao = random.sample(todas_combos, min(len(todas_combos), qtd_bilhetes))
                
                stake = banca / len(selecao)
                for i, combo in enumerate(selecao):
                    odd_total = 1.0
                    for a in ancoras_finais: odd_total *= a['odd']
                    for v in combo: odd_total *= v['d']
                    with st.expander(f"🎫 Bilhete #{i+1} | Retorno: R$ {stake * odd_total:.2f}"):
                        resumo = [[a['jogo'], a['res']] for a in ancoras_finais] + [[v['j'], v['r']] for v in combo]
                        st.table(pd.DataFrame(resumo, columns=["Jogo", "Palpite"]))
    else:
        st.warning("Nenhum jogo encontrado para este período.")