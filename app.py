import json
from pathlib import Path
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection

# ============================================================
# 1. CONFIGURAÇÃO BÁSICA E CONEXÃO
# ============================================================
st.set_page_config(layout="wide")

MESES_NOMES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
DIAS_UTEIS_PADRAO = [21, 20, 22, 20, 20, 22, 23, 21, 21, 22, 19, 22]

# Coloque aqui a URL completa da sua Planilha do Google Sheets compartilhada
URL_PLANILHA = "https://google.com"

# Inicializa a conexão nativa com o Google Sheets
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Erro ao inicializar conexão com o Google Sheets. Verifique os Secrets. Erro: {e}")
    st.stop()

# ============================================================
# 2. DADOS PADRÃO
# ============================================================
def criar_dados_padrao():
    valores_selic = {"2026": {m: 13.75 for m in MESES_NOMES}}
    for mes, valor in [
        ("Jan", 15.0), ("Fev", 15.0), ("Mar", 14.75), ("Abr", 14.5),
        ("Mai", 14.5), ("Jun", 14.25), ("Jul", 14.25), ("Ago", 14.0)
    ]:
        valores_selic["2026"][mes] = valor

    valores_aportes = {"2026": {m: [0.0] * 100 for m in MESES_NOMES}}
    valores_aportes["2026"]["Out"][0] = 301.22
    valores_aportes["2026"]["Out"][5] = 2000.00
    valores_aportes["2026"]["Nov"][4] = 1000.00
    valores_aportes["2026"]["Dez"][4] = 4000.00

    return {
        "versao": 1,
        "lista_anos_ativos": ["2026"],
        "lista_produtos": [
            {"nome": "Selic (CDI Padrão)", "fator": 100.0},
            {"nome": "Selic (PicPay)", "fator": 102.0},
            {"nome": "Selic (Mercado Pago Inicial)", "fator": 105.0},
            {"nome": "Selic (Mercado Pago Turbinado)", "fator": 115.0},
            {"nome": "Selic (Mercado Pago Turbinado)", "fator": 120.0},
            {"nome": "Selic (Cofrinho MP Promocional)", "fator": 140.0},
        ],
        "valores_selic": valores_selic,
        "valores_dias_uteis": {
            "2026": dict(zip(MESES_NOMES, DIAS_UTEIS_PADRAO))
        },
        "valores_aportes_limpos": valores_aportes,
    }

# ============================================================
# 3. CARREGAMENTO E SALVAMENTO EM SEGUNDO PLANO (NUVEM)
# ============================================================
def carregar_dados_nuvem():
    """Lê a string JSON armazenada na célula A1 da Planilha Google."""
    try:
        df = conn.read(spreadsheet=URL_PLANILHA, usecols=[0], nrows=1, header=None)
        if df.empty or pd.isna(df.iloc[0, 0]):
            return None
        dados_json = str(df.iloc[0, 0])
        return json.loads(dados_json)
    except Exception as e:
        st.sidebar.warning(f"Planilha vazia ou inacessível. Usando dados padrão. {e}")
        return None

def salvar_dados_nuvem():
    """Grava toda a estrutura do Session State na célula A1 do Google Sheets."""
    dados_para_salvar = {
        "versao": 1,
        "lista_anos_ativos": st.session_state.lista_anos_ativos,
        "lista_produtos": st.session_state.lista_produtos,
        "valores_selic": st.session_state.valores_selic,
        "valores_dias_uteis": st.session_state.valores_dias_uteis,
        "valores_aportes_limpos": st.session_state.valores_aportes_limpos,
    }
    try:
        conteudo_json = json.dumps(dados_para_salvar, ensure_ascii=False)
        df_salvar = pd.DataFrame([[conteudo_json]])
        conn.update(spreadsheet=URL_PLANILHA, data=df_salvar, header=False)
        return True
    except Exception as e:
        st.error(f"Erro crítico ao salvar dados na nuvem: {e}")
        return False

def normalizar_dados(dados):
    padrao = criar_dados_padrao()
    if not isinstance(dados, dict):
        dados = {}

    anos = dados.get("lista_anos_ativos", padrao["lista_anos_ativos"])
    anos = [str(ano) for ano in anos] if isinstance(anos, list) else ["2026"]
    if not anos:
        anos = ["2026"]

    produtos = dados.get("lista_produtos", padrao["lista_produtos"])
    if not isinstance(produtos, list):
        produtos = padrao["lista_produtos"]
    produtos_normalizados = []
    for item in produtos:
        if isinstance(item, dict):
            try:
                produtos_normalizados.append({
                    "nome": str(item.get("nome", "Ativo")),
                    "fator": float(item.get("fator", 100.0)),
                })
            except (TypeError, ValueError):
                produtos_normalizados.append({"nome": "Ativo", "fator": 100.0})

    selic = dados.get("valores_selic", {})
    dias = dados.get("valores_dias_uteis", {})
    aportes = dados.get("valores_aportes_limpos", {})
    if not isinstance(selic, dict): selic = {}
    if not isinstance(dias, dict): dias = {}
    if not isinstance(aportes, dict): aportes = {}

    capacidade = max(100, len(produtos_normalizados))
    for ano in anos:
        selic.setdefault(ano, {})
        dias.setdefault(ano, {})
        aportes.setdefault(ano, {})

        for indice, mes in enumerate(MESES_NOMES):
            valor_selic_padrao = padrao["valores_selic"].get(ano, {}).get(mes, 13.75)
            valor_dias_padrao = DIAS_UTEIS_PADRAO[indice]

            try:
                selic[ano][mes] = float(selic[ano].get(mes, valor_selic_padrao))
            except (TypeError, ValueError):
                selic[ano][mes] = float(valor_selic_padrao)

            try:
                dias[ano][mes] = int(dias[ano].get(mes, valor_dias_padrao))
            except (TypeError, ValueError):
                dias[ano][mes] = valor_dias_padrao

            lista_aportes = aportes[ano].get(mes, [])
            if not isinstance(lista_aportes, list):
                lista_aportes = []
            lista_normalizada = []
            for valor in lista_aportes[:capacidade]:
                try:
                    lista_normalizada.append(float(valor))
                except (TypeError, ValueError):
                    lista_normalizada.append(0.0)
            lista_normalizada.extend([0.0] * (capacidade - len(lista_normalizada)))
            aportes[ano][mes] = lista_normalizada

    return {
        "lista_anos_ativos": anos,
        "lista_produtos": produtos_normalizados,
        "valores_selic": selic,
        "valores_dias_uteis": dias,
        "valores_aportes_limpos": aportes,
    }

# Inicialização única dos dados da nuvem por ciclo de execução
if "dados_inicializados" not in st.session_state:
    dados_carregados = carregar_dados_nuvem()
    if dados_carregados is None:
        dados_iniciais = criar_dados_padrao()
    else:
        dados_iniciais = normalizar_dados(dados_carregados)

    dados_iniciais = normalizar_dados(dados_iniciais)
    st.session_state.lista_anos_ativos = dados_iniciais["lista_anos_ativos"]
    st.session_state.lista_produtos = dados_iniciais["lista_produtos"]
    st.session_state.valores_selic = dados_iniciais["valores_selic"]
    st.session_state.valores_dias_uteis = dados_iniciais["valores_dias_uteis"]
    st.session_state.valores_aportes_limpos = dados_iniciais["valores_aportes_limpos"]
    st.session_state.dados_inicializados = True

    if dados_carregados is None:
        salvar_dados_nuvem()

# ============================================================
# 4. INTERFACE E GERENCIAMENTO DE ANOS
# ============================================================
st.title("📊 Planejamento e Controle de Investimentos")

# Botão na barra lateral para recarregar manualmente de forma rápida caso queira forçar sincronismo
if st.sidebar.button("🔄 Forçar Atualização da Nuvem"):
    st.cache_data.clear()
    del st.session_state["dados_inicializados"]
    st.rerun()

aba_selecionada = st.radio(
    "Selecione o Ano:",
    st.session_state.lista_anos_ativos,
    horizontal=True,
)

if st.button("➕ Acrescentar Próximo Ano"):
    proximo_ano = str(int(max(st.session_state.lista_anos_ativos)) + 1)
    if proximo_ano not in st.session_state.lista_anos_ativos:
        st.session_state.lista_anos_ativos.append(proximo_ano)
        st.session_state.valores_aportes_limpos[proximo_ano] = {
            mes: [0.0] * max(100, len(st.session_state.lista_produtos))
            for mes in MESES_NOMES
        }
        st.session_state.valores_selic[proximo_ano] = {mes: 13.75 for mes in MESES_NOMES}
        st.session_state.valores_dias_uteis[proximo_ano] = dict(zip(MESES_NOMES, DIAS_UTEIS_PADRAO))
        salvar_dados_nuvem()
        st.rerun()

st.write("---")
st.subheader(f"⚙️ Parâmetros e Entradas — Ano {aba_selecionada}")

# ============================================================
# 5. TABELA DE SELIC E DIAS ÚTEIS
# ============================================================
linha_selic = {
    "Indicador": "Taxa Selic Base (%)",
    **{mes: float(st.session_state.valores_selic[aba_selecionada][mes]) for mes in MESES_NOMES},
}
linha_dias = {
    "Indicador": "Dias Úteis no Mês",
    **{mes: int(st.session_state.valores_dias_uteis[aba_selecionada][mes]) for mes in MESES_NOMES},
}

config_colunas_params = {
    "Indicador": st.column_config.TextColumn("Indicador", width="medium"),
    **{mes: st.column_config.NumberColumn(mes, width="small", format="%.2f") for mes in MESES_NOMES},
}

df_parametros_ed = st.data_editor(
    pd.DataFrame([linha_selic, linha_dias]),
    hide_index=True,
    column_config=config_colunas_params,
    key=f"parametros_v4_{aba_selecionada}",
)

modificado_param = False
for mes in MESES_NOMES:
    novo_selic = float(df_parametros_ed.at[0, mes])
    novo_dias = int(df_parametros_ed.at[1, mes])
    if (
        st.session_state.valores_selic[aba_selecionada][mes] != novo_selic
        or st.session_state.valores_dias_uteis[aba_selecionada][mes] != novo_dias
    ):
        st.session_state.valores_selic[aba_selecionada][mes] = novo_selic
