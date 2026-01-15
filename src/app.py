import json
import pandas as pd
import requests
import streamlit as st
import re

# Endpoint do LM Studio 
LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"

@st.cache_data
def carregar_dados():
    perfil = json.load(open('data/perfil_investidor.json'))
    produtos = json.load(open('data/produtos_financeiros.json'))
    historico = pd.read_csv('data/historico_atendimento.csv')
    transacoes = pd.read_csv('data/transacoes.csv')
    return perfil, produtos, historico, transacoes

perfil, produtos, historico, transacoes = carregar_dados()

contexto = f"""
CLIENTE:{perfil['nome']}, {perfil['idade']} anos, {perfil['perfil_investidor']}
OBJETIVO: {perfil['objetivo_principal']}
PATRIMONIO: R$ {perfil['patrimonio_total']} | RESERVA: R$ {perfil['reserva_emergencia_atual']}

TRANSAÇÕES RECENTES: 
{transacoes.to_string(index=False)}

ATENDIMENTOS ANTERIORES:
{historico.to_string(index=False)}

PRODUTOS FINANCEIROS OFERECIDOS:
{json.dumps(produtos, indent=2, ensure_ascii=False)}
"""
SYSTEM_PROMPT = f"""
Você é um agente financeiro inteligente especializado em investimentos.
Seu objetivo é otimizar finanças e incentivar boas práticas que proporcionem saúde financeira.

REGRAS:
1. Sempre baseie suas respostas nos dados fornecidos
2. Nunca invente informações financeiras
3. Se não souber algo, admita e ofereça alternativas

CONTEXTO DO CLIENTE:
{contexto}
"""

def remover_pensamento(texto: str) -> str:
    """Remove o bloco <think>...</think> da resposta do modelo DeepSeek R1."""
    # Remove tudo entre <think> e </think>, incluindo as tags
    texto_limpo = re.sub(r'<think>.*?</think>', '', texto, flags=re.DOTALL)
    return texto_limpo.strip()

def chat(mensagem_usuario: str, historico_mensagens: list) -> str:
    """Envia uma mensagem para o modelo e retorna a resposta."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(historico_mensagens)
    messages.append({"role": "user", "content": mensagem_usuario})
    
    payload = {
        "model": "deepseek/deepseek-r1-0528-qwen3-8bx",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1024
    }
    
    response = requests.post(LM_STUDIO_URL, json=payload)
    response.raise_for_status()
    resposta_bruta = response.json()["choices"][0]["message"]["content"]
    return remover_pensamento(resposta_bruta)

# ============== INTERFACE STREAMLIT ==============

st.set_page_config(
    page_title="Agente Financeiro IA",
    page_icon="💰",
    layout="centered"
)

st.title("💰 Agente Financeiro IA")
st.caption("Seu assistente inteligente para investimentos e finanças pessoais")

# Sidebar com informações do cliente
with st.sidebar:
    st.header("📊 Perfil do Cliente")
    st.write(f"**Nome:** {perfil['nome']}")
    st.write(f"**Idade:** {perfil['idade']} anos")
    st.write(f"**Perfil:** {perfil['perfil_investidor']}")
    st.write(f"**Objetivo:** {perfil['objetivo_principal']}")
    st.divider()
    st.write(f"**Patrimônio:** R$ {perfil['patrimonio_total']:,.2f}")
    st.write(f"**Reserva:** R$ {perfil['reserva_emergencia_atual']:,.2f}")
    
    if st.button("🗑️ Limpar conversa"):
        st.session_state.messages = []
        st.rerun()

# Inicializa o histórico de mensagens
if "messages" not in st.session_state:
    st.session_state.messages = []

# Exibe mensagens anteriores
for message in st.session_state.messages:
    with st.chat_message(message["role"], avatar="🧑" if message["role"] == "user" else "🤖"):
        st.markdown(message["content"])

# Input do usuário
if prompt := st.chat_input("Digite sua pergunta sobre finanças..."):
    # Adiciona mensagem do usuário
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="🧑"):
        st.markdown(prompt)
    
    # Gera resposta do assistente
    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("Pensando..."):
            try:
                # Passa o histórico para manter contexto da conversa
                historico_para_api = [
                    {"role": m["role"], "content": m["content"]} 
                    for m in st.session_state.messages[:-1]  # Exclui a última (já incluída no chat)
                ]
                resposta = chat(prompt, historico_para_api)
                st.markdown(resposta)
                st.session_state.messages.append({"role": "assistant", "content": resposta})
            except requests.exceptions.ConnectionError:
                st.error("❌ Não foi possível conectar ao LM Studio. Verifique se o servidor está rodando em localhost:1234")        
                resposta = chat(prompt, historico_para_api)
        print(f"\n🤖 Agente: {resposta}\n")