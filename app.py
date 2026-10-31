import json
import os
from pathlib import Path

import pandas as pd
import streamlit as st

# ============================================================
# 1. CONFIGURAÇÃO BÁSICA
# ============================================================
st.set_page_config(page_title="Ronicharles Santos", page_icon="📊", layout="wide")

MESES_NOMES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
DIAS_UTEIS_PADRAO = [21, 20, 22, 20, 20, 22, 23, 21, 21, 22, 19, 22]

# O arquivo JSON fica na mesma pasta deste arquivo Python.
PASTA_PROGRAMA = Path(__file__).resolve().parent
ARQUIVO_BANCO = PASTA_PROGRAMA / "dados_investimentos.json"
ARQUIVO_TEMPORARIO = PASTA_PROGRAMA / "dados_investimentos.tmp"


# ============================================================
# 2. DADOS PADRÃO
# ============================================================
def criar_dados_padrao():
    """Cria a estrutura inicial utilizada quando ainda não há banco salvo."""
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
# 3. CARREGAMENTO E SALVAMENTO PERMANENTE
# ============================================================
def carregar_dados_locais():
    """Lê o banco JSON. Se não existir ou estiver inválido, retorna None."""
    if not ARQUIVO_BANCO.exists():
        return None

    try:
        with open(ARQUIVO_BANCO, "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
        if not isinstance(dados, dict):
            raise ValueError("A estrutura do banco de dados não é válida.")
        return dados
    except (OSError, json.JSONDecodeError, ValueError) as erro:
        st.warning(
            f"Não foi possível ler {ARQUIVO_BANCO.name}: {erro}. "
            "O programa será iniciado com os dados padrão. Não apague o arquivo original "
            "caso precise tentar recuperar os dados manualmente."
        )
        return None


def salvar_dados_locais():
    """Grava os dados em JSON usando arquivo temporário para reduzir risco de corrupção."""
    dados_para_salvar = {
        "versao": 1,
        "lista_anos_ativos": st.session_state.lista_anos_ativos,
        "lista_produtos": st.session_state.lista_produtos,
        "valores_selic": st.session_state.valores_selic,
        "valores_dias_uteis": st.session_state.valores_dias_uteis,
        "valores_aportes_limpos": st.session_state.valores_aportes_limpos,
    }

    try:
        with open(ARQUIVO_TEMPORARIO, "w", encoding="utf-8") as arquivo:
            json.dump(dados_para_salvar, arquivo, indent=4, ensure_ascii=False)
            arquivo.flush()
            os.fsync(arquivo.fileno())
        os.replace(ARQUIVO_TEMPORARIO, ARQUIVO_BANCO)
        return True
    except OSError as erro:
        st.error(f"Erro ao salvar os dados: {erro}")
        return False


def normalizar_dados(dados):
    """Completa campos ausentes e ajusta a estrutura de dados carregada do JSON."""
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
    if not isinstance(selic, dict):
        selic = {}
    if not isinstance(dias, dict):
        dias = {}
    if not isinstance(aportes, dict):
        aportes = {}

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


# Carrega os dados uma vez por sessão e inicializa o Session State.
dados_carregados = carregar_dados_locais()
if "dados_inicializados" not in st.session_state:
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

    # Cria o JSON com os valores iniciais na primeira execução.
    # Se já existir um arquivo (inclusive um arquivo inválido), não o sobrescreve aqui.
    if not ARQUIVO_BANCO.exists():
        salvar_dados_locais()


# ============================================================
# 4. INTERFACE E GERENCIAMENTO DE ANOS
# ============================================================
st.title("📊 Planejamento e Controle de Investimentos")

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
        salvar_dados_locais()
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
        st.session_state.valores_dias_uteis[aba_selecionada][mes] = novo_dias
        modificado_param = True

if modificado_param:
    salvar_dados_locais()

st.write("")


# ============================================================
# 6. TABELA PRINCIPAL: ATIVOS, REFERÊNCIAS E APORTES
# ============================================================
linhas_ap = []
for indice, produto in enumerate(st.session_state.lista_produtos):
    linha = {"Ativo": produto["nome"], "Referência (%)": produto["fator"]}
    for mes in MESES_NOMES:
        linha[mes] = float(st.session_state.valores_aportes_limpos[aba_selecionada][mes][indice])
    linhas_ap.append(linha)

config_colunas_moeda_geral = {
    "Ativo": st.column_config.TextColumn("Indicador / Ativo", width="medium"),
    "Referência (%)": st.column_config.NumberColumn("Referência (%)", width="small", format="%.2f"),
    **{mes: st.column_config.NumberColumn(mes, width="small", format="R$ %,.2f") for mes in MESES_NOMES},
}

df_ap_ed = st.data_editor(
    pd.DataFrame(linhas_ap),
    hide_index=True,
    column_config=config_colunas_moeda_geral,
    key=f"aportes_v4_{aba_selecionada}",
)

modificado_aportes = False
for indice, produto in enumerate(st.session_state.lista_produtos):
    novo_nome = str(df_ap_ed.at[indice, "Ativo"])
    novo_fator = float(df_ap_ed.at[indice, "Referência (%)"])

    if produto["nome"] != novo_nome or produto["fator"] != novo_fator:
        st.session_state.lista_produtos[indice]["nome"] = novo_nome
        st.session_state.lista_produtos[indice]["fator"] = novo_fator
        modificado_aportes = True

    for mes in MESES_NOMES:
        novo_aporte = float(df_ap_ed.at[indice, mes])
        if st.session_state.valores_aportes_limpos[aba_selecionada][mes][indice] != novo_aporte:
            st.session_state.valores_aportes_limpos[aba_selecionada][mes][indice] = novo_aporte
            modificado_aportes = True

if modificado_aportes:
    salvar_dados_locais()


# ============================================================
# 7. BOTÕES PARA ADICIONAR E REMOVER ATIVOS
# ============================================================
col_btn1, col_btn2, _ = st.columns([1.2, 1.2, 4])

with col_btn1:
    if st.button("➕ Adicionar Novo Ativo", use_container_width=True):
        num_novo = len(st.session_state.lista_produtos) + 1
        st.session_state.lista_produtos.append({"nome": f"Novo Ativo {num_novo}", "fator": 100.0})
        for ano in st.session_state.lista_anos_ativos:
            for mes in MESES_NOMES:
                lista = st.session_state.valores_aportes_limpos[ano][mes]
                if len(lista) < len(st.session_state.lista_produtos):
                    lista.append(0.0)
        salvar_dados_locais()
        st.rerun()

with col_btn2:
    if st.button("❌ Remover Último Ativo", use_container_width=True):
        if st.session_state.lista_produtos:
            indice_removido = len(st.session_state.lista_produtos) - 1
            for ano in st.session_state.lista_anos_ativos:
                for mes in MESES_NOMES:
                    st.session_state.valores_aportes_limpos[ano][mes][indice_removido] = 0.0
            st.session_state.lista_produtos.pop()
            salvar_dados_locais()
            st.rerun()


# ============================================================
# 8. MOTOR DE CÁLCULO SEQUENCIAL
# ============================================================
num_ativos = len(st.session_state.lista_produtos)
saldos_globais = [0.0] * num_ativos

historico_saldos_global = {
    ano: {indice: {mes: 0.0 for mes in MESES_NOMES} for indice in range(num_ativos)}
    for ano in st.session_state.lista_anos_ativos
}
patrimonio_total_global = {
    ano: {mes: 0.0 for mes in MESES_NOMES}
    for ano in st.session_state.lista_anos_ativos
}
rendimento_total_global = {
    ano: {mes: 0.0 for mes in MESES_NOMES}
    for ano in st.session_state.lista_anos_ativos
}

for ano in st.session_state.lista_anos_ativos:
    for mes in MESES_NOMES:
        dias_mes = int(st.session_state.valores_dias_uteis[ano][mes])
        selic_anual = st.session_state.valores_selic[ano][mes] / 100.0
        rendimento_mes_acumulado = 0.0

        for indice in range(num_ativos):
            produto = st.session_state.lista_produtos[indice]
            taxa_anual_produto = selic_anual * (produto["fator"] / 100.0)
            taxa_diaria = (1 + taxa_anual_produto) ** (1 / 252) - 1
            taxa_mensal = (1 + taxa_diaria) ** dias_mes - 1

            aporte = st.session_state.valores_aportes_limpos[ano][mes][indice]
            base_calculo = saldos_globais[indice] + aporte
            rendimento = base_calculo * taxa_mensal

            saldos_globais[indice] = base_calculo + rendimento
            historico_saldos_global[ano][indice][mes] = saldos_globais[indice]
            rendimento_mes_acumulado += rendimento

        rendimento_total_global[ano][mes] = rendimento_mes_acumulado
        patrimonio_total_global[ano][mes] = sum(saldos_globais)


# ============================================================
# 9. RESULTADOS CONSOLIDADOS
# ============================================================
st.write("---")
st.subheader(f"💰 Saldo da Selic e Consolidação — Ano Base {aba_selecionada}")

linhas_saldos_tabela = []
for indice, produto in enumerate(st.session_state.lista_produtos):
    fator = float(produto["fator"])
    taxa_exibicao = f"{int(fator)}%" if fator.is_integer() else f"{fator}%"
    item_saldo = {
        "Indicador / Ativo": f"Saldo + Rendimento: {produto['nome']}"
    }
    for mes in MESES_NOMES:
        item_saldo[mes] = float(historico_saldos_global[aba_selecionada][indice][mes])
    linhas_saldos_tabela.append(item_saldo)

item_patrimonio = {
    "Indicador / Ativo": "Patrimônio Total Acumulado",
    **{mes: float(patrimonio_total_global[aba_selecionada][mes]) for mes in MESES_NOMES},
}
item_rendimento = {
    "Indicador / Ativo": "Rendimento Líquido do Mês",
    **{mes: float(rendimento_total_global[aba_selecionada][mes]) for mes in MESES_NOMES},
}
linhas_saldos_tabela.extend([item_patrimonio, item_rendimento])

st.dataframe(
    pd.DataFrame(linhas_saldos_tabela),
    hide_index=True,
    column_config={
        mes: st.column_config.NumberColumn(mes, format="R$ %,.2f")
        for mes in MESES_NOMES
    },
    use_container_width=True,
)
# Injetar CSS para esconder o botão "Manage app" e o menu do Streamlit
st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    div[data-testid="stStatusWidget"] {visibility: hidden;}
    .stAppDeployButton {display:none;}
    viewer-badge {display: none !important;}
    iframe[title="Manage app"] {display: none !important;}
    </style>
    """,
    unsafe_allow_html=True
)
