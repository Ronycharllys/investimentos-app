from pathlib import Path
import ast

codigo = r'''import json
import os
from pathlib import Path

import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode

# ============================================================
# 1. CONFIGURAÇÃO E IDENTIDADE VISUAL
# ============================================================
st.set_page_config(
    page_title="Ronicharles Santos | Painel",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

MESES_NOMES = [
    "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
    "Jul", "Ago", "Set", "Out", "Nov", "Dez",
]
DIAS_UTEIS_PADRAO = [21, 20, 22, 20, 20, 22, 23, 21, 21, 22, 19, 22]

PASTA_PROGRAMA = Path(__file__).resolve().parent
ARQUIVO_BANCO = PASTA_PROGRAMA / "dados_investimentos.json"
ARQUIVO_TEMPORARIO = PASTA_PROGRAMA / "dados_investimentos.tmp"


st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap');
    :root { color-scheme: dark; }
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
        background: #09090b !important; color: #f4f4f5 !important;
    }
    [data-testid="stHeader"] { background: rgba(9,9,11,.96) !important; }
    [data-testid="stSidebar"] { background: #111113 !important; border-right: 1px solid #27272a; }
    [data-testid="stSidebar"] * { color: #e4e4e7 !important; }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #a1a1aa !important; }
    .block-container { padding-top: 1.5rem; padding-bottom: 2.5rem; max-width: 1800px; }
    .hero { background: linear-gradient(120deg,#18181b 0%,#202027 60%,#172554 100%); padding: 26px 30px; border: 1px solid #30303a; border-radius: 18px; color: #fafafa; margin-bottom: 20px; }
    .hero-kicker { color: #93c5fd; font-size: .76rem; font-weight: 800; letter-spacing: .13em; text-transform: uppercase; }
    .hero h1 { color: #fafafa; font-size: 2rem; line-height: 1.15; margin: 7px 0 8px 0; font-weight: 800; }
    .hero p { color: #a1a1aa; margin: 0; font-size: .95rem; }
    .section-title { color: #f4f4f5; font-size: 1.18rem; font-weight: 800; margin: 8px 0 4px 0; }
    .section-subtitle { color: #a1a1aa; font-size: .88rem; margin-bottom: 14px; }
    div[data-testid="stMetric"] { background: #18181b !important; border: 1px solid #303038 !important; padding: 16px 18px; border-radius: 14px; box-shadow: none; }
    div[data-testid="stMetricLabel"] { color: #a1a1aa !important; font-weight: 600; }
    div[data-testid="stMetricValue"] { color: #fafafa !important; font-weight: 800; }
    div[data-testid="stMetricDelta"] { color: #a1a1aa !important; }
    .status-pill { display:inline-block; padding:5px 10px; border-radius:30px; background:#14251d; border:1px solid #24543c; color:#86efac; font-size:.76rem; font-weight:800; }
    .info-strip { background:#18181b; border:1px solid #303038; border-radius:12px; padding:11px 14px; color:#d4d4d8; font-size:.84rem; }
    div[data-testid="stTabs"] button { color:#a1a1aa; font-weight:700; }
    div[data-testid="stTabs"] button[aria-selected="true"] { color:#fafafa !important; border-bottom-color:#3b82f6 !important; }
    .stButton > button { background:#27272a; color:#fafafa; border:1px solid #3f3f46; border-radius:9px; font-weight:700; min-height:2.55rem; }
    .stButton > button:hover { background:#3f3f46; color:#fff; border-color:#52525b; }
    [data-testid="stSidebar"] .stButton > button { background:#2563eb; border:0; color:white !important; }
    [data-testid="stSidebar"] .stButton > button:hover { background:#1d4ed8; }
    input, textarea { background:#18181b !important; color:#fafafa !important; }
    [data-baseweb="select"] > div { background:#18181b !important; border-color:#3f3f46 !important; }
    [data-testid="stExpander"] { background:#18181b; border:1px solid #303038; border-radius:10px; }
    [data-testid="stAlert"] { background:#18181b; border:1px solid #3f3f46; color:#e4e4e7; }
    hr { border-color:#303038 !important; }
    ::-webkit-scrollbar { width:8px; height:8px; }
    ::-webkit-scrollbar-track { background:#09090b; }
    ::-webkit-scrollbar-thumb { background:#3f3f46; border-radius:8px; }
    </style>
    """,
    unsafe_allow_html=True,
)


def converter_numero(valor, padrao=0.0):
    """Converte valores numéricos vindos do AgGrid, inclusive decimais com vírgula."""
    if valor is None:
        return float(padrao)
    if isinstance(valor, str):
        valor = valor.strip().replace(",", ".")
        if not valor:
            return float(padrao)
    try:
        numero = float(valor)
        if pd.isna(numero):
            return float(padrao)
        return numero
    except (TypeError, ValueError):
        return float(padrao)


def exibir_tabela_aggrid(df, chave, editavel=True, altura_linha=38):
    """Exibe AgGrid e devolve DataFrame com índice sequencial e estrutura validada."""
    if df is None:
        df = pd.DataFrame()

    df_original = pd.DataFrame(df).copy().reset_index(drop=True)

    if df_original.empty and len(df_original.columns) == 0:
        return df_original

    construtor = GridOptionsBuilder.from_dataframe(df_original)
    construtor.configure_default_column(
        editable=editavel,
        resizable=True,
        sortable=False,
        filter=False,
        minWidth=68,
        wrapText=True,
        autoHeight=True,
        cellStyle={"textAlign": "center"},
    )

    for coluna in df_original.columns:
        if coluna in ("Indicador", "Ativo"):
            construtor.configure_column(
                coluna,
                minWidth=150,
                flex=2,
                cellStyle={"textAlign": "left"},
            )
        else:
            construtor.configure_column(coluna, minWidth=68, flex=1)

    construtor.configure_grid_options(
        domLayout="autoHeight",
        suppressHorizontalScroll=True,
        alwaysShowHorizontalScroll=False,
        suppressColumnVirtualisation=True,
        rowHeight=altura_linha,
        headerHeight=42,
        animateRows=False,
    )

    opcoes = construtor.build()
    altura = max(105, (len(df_original) + 1) * (altura_linha + 2) + 12)

    retorno = AgGrid(
        df_original,
        gridOptions=opcoes,
        height=altura,
        width="100%",
        theme="alpine-dark",
        key=chave,
        update_mode=GridUpdateMode.VALUE_CHANGED,
        data_return_mode=DataReturnMode.AS_INPUT,
        fit_columns_on_grid_load=True,
        allow_unsafe_jscode=False,
    )

    dados = retorno.get("data", df_original) if isinstance(retorno, dict) else df_original
    resultado = pd.DataFrame(dados).copy()

    # O AgGrid pode devolver índice original, índice parcial ou outra estrutura.
    # A normalização evita KeyError ao acessar linhas por posição.
    if list(resultado.columns) != list(df_original.columns):
        resultado = df_original.copy()
    elif len(resultado) != len(df_original):
        resultado = df_original.copy()

    return resultado.reset_index(drop=True)


# ============================================================
# 2. DADOS PADRÃO
# ============================================================
def criar_dados_padrao():
    valores_selic = {"2026": {mes: 13.75 for mes in MESES_NOMES}}
    for mes, valor in [
        ("Jan", 15.0), ("Fev", 15.0), ("Mar", 14.75), ("Abr", 14.5),
        ("Mai", 14.5), ("Jun", 14.25), ("Jul", 14.25), ("Ago", 14.0),
    ]:
        valores_selic["2026"][mes] = valor

    produtos = [
        {"nome": "100% da Selic", "fator": 100.0},
        {"nome": "102% da Selic", "fator": 102.0},
        {"nome": "105% da Selic", "fator": 105.0},
        {"nome": "115% da Selic", "fator": 115.0},
        {"nome": "120% da Selic", "fator": 120.0},
        {"nome": "140% da Selic", "fator": 140.0},
    ]
    aportes = {"2026": {mes: [0.0] * 100 for mes in MESES_NOMES}}

    return {
        "versao": 1,
        "lista_anos_ativos": ["2026"],
        "lista_produtos": produtos,
        "valores_selic": valores_selic,
        "valores_dias_uteis": {
            "2026": {
                mes: float(dias)
                for mes, dias in zip(MESES_NOMES, DIAS_UTEIS_PADRAO)
            }
        },
        "valores_aportes_limpos": aportes,
    }


# ============================================================
# 3. PERSISTÊNCIA JSON
# ============================================================
def carregar_dados_locais():
    if not ARQUIVO_BANCO.exists():
        return None

    try:
        with open(ARQUIVO_BANCO, "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
        if not isinstance(dados, dict):
            raise ValueError("Formato de dados inválido.")
        return dados
    except (OSError, json.JSONDecodeError, ValueError) as erro:
        st.error(f"Não foi possível ler o arquivo de dados: {erro}")
        st.warning(
            "O arquivo original foi preservado. Faça uma cópia antes de tentar recuperá-lo."
        )
        return None


def salvar_dados_locais():
    dados = {
        "versao": 1,
        "lista_anos_ativos": st.session_state.lista_anos_ativos,
        "lista_produtos": st.session_state.lista_produtos,
        "valores_selic": st.session_state.valores_selic,
        "valores_dias_uteis": st.session_state.valores_dias_uteis,
        "valores_aportes_limpos": st.session_state.valores_aportes_limpos,
    }

    try:
        with open(ARQUIVO_TEMPORARIO, "w", encoding="utf-8") as arquivo:
            json.dump(dados, arquivo, indent=4, ensure_ascii=False)
            arquivo.flush()
            os.fsync(arquivo.fileno())

        os.replace(ARQUIVO_TEMPORARIO, ARQUIVO_BANCO)
        st.session_state.ultimo_salvamento = pd.Timestamp.now().strftime(
            "%d/%m/%Y às %H:%M:%S"
        )
        return True
    except OSError as erro:
        st.error(f"Falha ao salvar os dados: {erro}")
        return False


def normalizar_dados(dados):
    padrao = criar_dados_padrao()

    anos = dados.get("lista_anos_ativos", padrao["lista_anos_ativos"])
    anos = [str(ano) for ano in anos] if isinstance(anos, list) and anos else ["2026"]
    anos = list(dict.fromkeys(anos))

    produtos = dados.get("lista_produtos", padrao["lista_produtos"])
    if not isinstance(produtos, list):
        produtos = padrao["lista_produtos"]

    produtos_ok = []
    for item in produtos:
        if isinstance(item, dict):
            produtos_ok.append({
                "nome": str(item.get("nome", "Ativo")),
                "fator": converter_numero(item.get("fator", 100.0), 100.0),
            })

    if not produtos_ok:
        produtos_ok = [item.copy() for item in padrao["lista_produtos"]]

    selic = dados.get("valores_selic", {})
    dias = dados.get("valores_dias_uteis", {})
    aportes = dados.get("valores_aportes_limpos", {})

    if not isinstance(selic, dict):
        selic = {}
    if not isinstance(dias, dict):
        dias = {}
    if not isinstance(aportes, dict):
        aportes = {}

    capacidade = max(100, len(produtos_ok))

    for ano in anos:
        if not isinstance(selic.get(ano), dict):
            selic[ano] = {}
        if not isinstance(dias.get(ano), dict):
            dias[ano] = {}
        if not isinstance(aportes.get(ano), dict):
            aportes[ano] = {}

        for indice_mes, mes in enumerate(MESES_NOMES):
            selic[ano][mes] = converter_numero(
                selic[ano].get(mes, 13.75), 13.75
            )
            dias[ano][mes] = round(
                converter_numero(
                    dias[ano].get(mes, DIAS_UTEIS_PADRAO[indice_mes]),
                    DIAS_UTEIS_PADRAO[indice_mes],
                ),
                2,
            )

            lista = aportes[ano].get(mes, [])
            if not isinstance(lista, list):
                lista = []

            limpa = [
                converter_numero(valor, 0.0)
                for valor in lista[:capacidade]
            ]
            limpa.extend([0.0] * (capacidade - len(limpa)))
            aportes[ano][mes] = limpa

    return {
        "lista_anos_ativos": anos,
        "lista_produtos": produtos_ok,
        "valores_selic": selic,
        "valores_dias_uteis": dias,
        "valores_aportes_limpos": aportes,
    }


if "dados_inicializados" not in st.session_state:
    dados_salvos = carregar_dados_locais()
    dados = normalizar_dados(
        dados_salvos if dados_salvos is not None else criar_dados_padrao()
    )

    st.session_state.lista_anos_ativos = dados["lista_anos_ativos"]
    st.session_state.lista_produtos = dados["lista_produtos"]
    st.session_state.valores_selic = dados["valores_selic"]
    st.session_state.valores_dias_uteis = dados["valores_dias_uteis"]
    st.session_state.valores_aportes_limpos = dados["valores_aportes_limpos"]
    st.session_state.dados_inicializados = True
    st.session_state.ultimo_salvamento = (
        "Banco carregado" if dados_salvos is not None else "Primeira execução"
    )

    if not ARQUIVO_BANCO.exists():
        salvar_dados_locais()


# ============================================================
# 4. CABEÇALHO E BARRA LATERAL
# ============================================================
st.markdown(
    """
    <div class="hero">
      <div class="hero-kicker">Gestão patrimonial • Renda fixa</div>
      <h1>Planejamento de Investimentos</h1>
      <p>Acompanhe aportes, taxas, evolução do patrimônio e rendimento dos seus ativos.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("## 📈 Investimentos")
    st.caption("PAINEL DE CONTROLE")
    st.markdown("---")
    st.markdown("### Período de análise")

    ano_selecionado = st.selectbox(
        "Ano",
        st.session_state.lista_anos_ativos,
        index=len(st.session_state.lista_anos_ativos) - 1,
        label_visibility="collapsed",
    )

    if st.button("＋ Adicionar próximo ano", use_container_width=True):
        proximo = str(max(int(ano) for ano in st.session_state.lista_anos_ativos) + 1)

        if proximo not in st.session_state.lista_anos_ativos:
            capacidade = max(100, len(st.session_state.lista_produtos))
            st.session_state.lista_anos_ativos.append(proximo)
            st.session_state.valores_aportes_limpos[proximo] = {
                mes: [0.0] * capacidade for mes in MESES_NOMES
            }
            st.session_state.valores_selic[proximo] = {
                mes: 13.75 for mes in MESES_NOMES
            }
            st.session_state.valores_dias_uteis[proximo] = {
                mes: float(valor)
                for mes, valor in zip(MESES_NOMES, DIAS_UTEIS_PADRAO)
            }
            salvar_dados_locais()
            st.rerun()

    st.markdown("---")
    st.markdown("### Gestão de ativos")

    if st.button("＋ Adicionar ativo", use_container_width=True):
        numero = len(st.session_state.lista_produtos) + 1
        st.session_state.lista_produtos.append({
            "nome": f"Novo Ativo {numero}",
            "fator": 100.0,
        })

        for ano in st.session_state.lista_anos_ativos:
            for mes in MESES_NOMES:
                lista = st.session_state.valores_aportes_limpos[ano][mes]
                lista.append(0.0)

        salvar_dados_locais()
        st.rerun()

    if st.button(
        "－ Remover último ativo",
        use_container_width=True,
        disabled=len(st.session_state.lista_produtos) == 0,
    ):
        indice = len(st.session_state.lista_produtos) - 1
        st.session_state.lista_produtos.pop()

        for ano in st.session_state.lista_anos_ativos:
            for mes in MESES_NOMES:
                lista = st.session_state.valores_aportes_limpos[ano][mes]
                if indice < len(lista):
                    lista[indice] = 0.0

        salvar_dados_locais()
        st.rerun()

    st.markdown("---")
    st.markdown("### Armazenamento")
    st.markdown(
        '<span class="status-pill">● Salvamento automático</span>',
        unsafe_allow_html=True,
    )
    st.caption(f"Arquivo: {ARQUIVO_BANCO.name}")
    st.caption(
        f"Último estado: {st.session_state.get('ultimo_salvamento', 'Em sessão')}"
    )
    st.caption("Mantenha este JSON junto ao programa para preservar seus dados.")


# ============================================================
# 5. ABAS DO APLICATIVO
# ============================================================
st.markdown(
    f'<div class="section-title">Visão do período — {ano_selecionado}</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="section-subtitle">Edite os campos nas tabelas. '
    'As alterações são gravadas automaticamente.</div>',
    unsafe_allow_html=True,
)

tab_painel, tab_aportes, tab_parametros, tab_graficos = st.tabs([
    "▦  Painel",
    "＋  Aportes e ativos",
    "⚙  Parâmetros",
    "▥  Gráficos",
])


# ============================================================
# 6. EDIÇÃO DE PARÂMETROS
# ============================================================
with tab_parametros:
    st.markdown("#### Taxa Selic e dias úteis")
    st.caption(
        "Informe a taxa anual de referência e a quantidade de dias úteis de cada mês."
    )

    linha_selic = {
        "Indicador": "Taxa Selic Base (%)",
        **{
            mes: float(st.session_state.valores_selic[ano_selecionado][mes])
            for mes in MESES_NOMES
        },
    }
    linha_dias = {
        "Indicador": "Dias úteis",
        **{
            mes: float(st.session_state.valores_dias_uteis[ano_selecionado][mes])
            for mes in MESES_NOMES
        },
    }

    df_param = exibir_tabela_aggrid(
        pd.DataFrame([linha_selic, linha_dias]),
        chave=f"parametros_dark_{ano_selecionado}",
        editavel=True,
        altura_linha=44,
    )

    alterou = False
    for mes in MESES_NOMES:
        # iloc acessa pela posição da linha, independentemente do índice.
        taxa = converter_numero(df_param.iloc[0][mes], 13.75)
        uteis = round(converter_numero(df_param.iloc[1][mes], 0.0), 2)

        if (
            taxa != st.session_state.valores_selic[ano_selecionado][mes]
            or uteis != st.session_state.valores_dias_uteis[ano_selecionado][mes]
        ):
            st.session_state.valores_selic[ano_selecionado][mes] = taxa
            st.session_state.valores_dias_uteis[ano_selecionado][mes] = uteis
            alterou = True

    if alterou:
        salvar_dados_locais()
        st.toast("Parâmetros salvos.", icon="💾")


# ============================================================
# 7. EDIÇÃO DE ATIVOS E APORTES
# ============================================================
with tab_aportes:
    st.markdown("#### Cadastro de ativos e aportes mensais")
    st.caption(
        "Altere o nome, o percentual de referência e os valores aportados em cada mês."
    )

    linhas = []
    for indice, produto in enumerate(st.session_state.lista_produtos):
        linha = {
            "Ativo": produto["nome"],
            "Referência (%)": float(produto["fator"]),
        }
        for mes in MESES_NOMES:
            linha[mes] = float(
                st.session_state.valores_aportes_limpos[ano_selecionado][mes][indice]
            )
        linhas.append(linha)

    df_aportes_original = pd.DataFrame(
        linhas,
        columns=["Ativo", "Referência (%)"] + MESES_NOMES,
    )

    df_aportes = exibir_tabela_aggrid(
        df_aportes_original,
        chave=f"aportes_dark_{ano_selecionado}",
        editavel=True,
        altura_linha=46,
    )

    alterou_aporte = False

    # Limita o processamento às linhas efetivamente existentes na tabela.
    quantidade_linhas = min(
        len(st.session_state.lista_produtos),
        len(df_aportes),
    )

    for indice in range(quantidade_linhas):
        nome = str(df_aportes.iloc[indice]["Ativo"])
        fator = converter_numero(
            df_aportes.iloc[indice]["Referência (%)"],
            st.session_state.lista_produtos[indice]["fator"],
        )

        if (
            nome != st.session_state.lista_produtos[indice]["nome"]
            or fator != st.session_state.lista_produtos[indice]["fator"]
        ):
            st.session_state.lista_produtos[indice] = {
                "nome": nome,
                "fator": fator,
            }
            alterou_aporte = True

        for mes in MESES_NOMES:
            valor = converter_numero(
                df_aportes.iloc[indice][mes],
                st.session_state.valores_aportes_limpos[ano_selecionado][mes][indice],
            )

            if (
                valor
                != st.session_state.valores_aportes_limpos[ano_selecionado][mes][indice]
            ):
                st.session_state.valores_aportes_limpos[ano_selecionado][mes][indice] = valor
                alterou_aporte = True

    if alterou_aporte:
        salvar_dados_locais()
        st.toast("Aportes e ativos salvos.", icon="💾")


# ============================================================
# 8. MOTOR DE CÁLCULO SEQUENCIAL
# ============================================================
num_ativos = len(st.session_state.lista_produtos)
saldos = [0.0] * num_ativos

historico = {
    ano: {
        indice: {mes: 0.0 for mes in MESES_NOMES}
        for indice in range(num_ativos)
    }
    for ano in st.session_state.lista_anos_ativos
}
patrimonio = {
    ano: {mes: 0.0 for mes in MESES_NOMES}
    for ano in st.session_state.lista_anos_ativos
}
rendimentos = {
    ano: {mes: 0.0 for mes in MESES_NOMES}
    for ano in st.session_state.lista_anos_ativos
}
aportes_por_mes = {
    ano: {mes: 0.0 for mes in MESES_NOMES}
    for ano in st.session_state.lista_anos_ativos
}

for ano in st.session_state.lista_anos_ativos:
    for mes in MESES_NOMES:
        dias_mes = converter_numero(
            st.session_state.valores_dias_uteis[ano][mes],
            0.0,
        )
        selic_anual = converter_numero(
            st.session_state.valores_selic[ano][mes],
            0.0,
        ) / 100.0

        rendimento_mes = 0.0
        aporte_mes = 0.0

        for indice in range(num_ativos):
            produto = st.session_state.lista_produtos[indice]
            taxa_anual = selic_anual * (
                converter_numero(produto["fator"], 100.0) / 100.0
            )

            if taxa_anual <= -1:
                taxa_mensal = 0.0
            else:
                taxa_diaria = (1 + taxa_anual) ** (1 / 252) - 1
                taxa_mensal = (1 + taxa_diaria) ** dias_mes - 1

            aporte = converter_numero(
                st.session_state.valores_aportes_limpos[ano][mes][indice],
                0.0,
            )
            base = saldos[indice] + aporte
            rendimento = base * taxa_mensal
            saldos[indice] = base + rendimento

            historico[ano][indice][mes] = saldos[indice]
            rendimento_mes += rendimento
            aporte_mes += aporte

        rendimentos[ano][mes] = rendimento_mes
        aportes_por_mes[ano][mes] = aporte_mes
        patrimonio[ano][mes] = sum(saldos)


# ============================================================
# 9. PAINEL EXECUTIVO — SEM GRÁFICOS
# ============================================================
with tab_painel:
    valores_patrimonio = [
        patrimonio[ano_selecionado][mes] for mes in MESES_NOMES
    ]
    valores_aportes = [
        aportes_por_mes[ano_selecionado][mes] for mes in MESES_NOMES
    ]

    total_patrimonio = valores_patrimonio[-1] if valores_patrimonio else 0.0
    total_aportado_ano = sum(valores_aportes)

    anos_ate_selecao = [
        ano
        for ano in st.session_state.lista_anos_ativos
        if int(ano) <= int(ano_selecionado)
    ]
    total_aportado_acumulado = sum(
        aportes_por_mes[ano][mes]
        for ano in anos_ate_selecao
        for mes in MESES_NOMES
    )
    rendimento_acumulado = total_patrimonio - total_aportado_acumulado
    aporte_mensal_medio = total_aportado_ano / 12 if MESES_NOMES else 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        "Patrimônio projetado em dezembro",
        f"R$ {total_patrimonio:,.2f}",
    )
    c2.metric("Aportes no ano", f"R$ {total_aportado_ano:,.2f}")
    c3.metric(
        "Rendimento acumulado estimado",
        f"R$ {rendimento_acumulado:,.2f}",
    )
    c4.metric(
        "Média mensal de aportes",
        f"R$ {aporte_mensal_medio:,.2f}",
    )

    st.markdown("#### Consolidação mensal")
    tabela = []

    for indice, produto in enumerate(st.session_state.lista_produtos):
        tabela.append({
            "Ativo": produto["nome"],
            **{
                mes: historico[ano_selecionado][indice][mes]
                for mes in MESES_NOMES
            },
        })

    tabela.append({
        "Ativo": "Patrimônio total",
        **{
            mes: patrimonio[ano_selecionado][mes]
            for mes in MESES_NOMES
        },
    })
    tabela.append({
        "Ativo": "Rendimento do mês",
        **{
            mes: rendimentos[ano_selecionado][mes]
            for mes in MESES_NOMES
        },
    })

    exibir_tabela_aggrid(
        pd.DataFrame(tabela, columns=["Ativo"] + MESES_NOMES),
        chave=f"consolidacao_dark_{ano_selecionado}",
        editavel=False,
        altura_linha=42,
    )


# ============================================================
# 10. ABA DE GRÁFICOS
# ============================================================
with tab_graficos:
    st.markdown("#### Evolução do patrimônio")
    st.caption(
        f"Projeção mensal do patrimônio acumulado em {ano_selecionado}."
    )

    valores_patrimonio_grafico = [
        patrimonio[ano_selecionado][mes] for mes in MESES_NOMES
    ]
    valores_aportes_grafico = [
        aportes_por_mes[ano_selecionado][mes] for mes in MESES_NOMES
    ]
    valores_rendimento_grafico = [
        rendimentos[ano_selecionado][mes] for mes in MESES_NOMES
    ]

    grafico_patrimonio = pd.DataFrame(
        {"Patrimônio": valores_patrimonio_grafico},
        index=MESES_NOMES,
    )
    st.area_chart(grafico_patrimonio, use_container_width=True)

    col_g1, col_g2 = st.columns(2)

    with col_g1:
        st.markdown("#### Aportes por mês")
        grafico_aportes = pd.DataFrame(
            {"Aportes": valores_aportes_grafico},
            index=MESES_NOMES,
        )
        st.bar_chart(grafico_aportes, use_container_width=True)

    with col_g2:
        st.markdown("#### Rendimentos por mês")
        grafico_rendimentos = pd.DataFrame(
            {"Rendimento": valores_rendimento_grafico},
            index=MESES_NOMES,
        )
        st.bar_chart(grafico_rendimentos, use_container_width=True)


# ============================================================
# 11. RODAPÉ E STATUS
# ============================================================
st.markdown("---")
col_status, col_path = st.columns([1, 3])

with col_status:
    st.markdown(
        '<span class="status-pill">● Dados persistidos</span>',
        unsafe_allow_html=True,
    )

with col_path:
    st.caption(f"Banco local: {ARQUIVO_BANCO}")

st.caption(
    "Os valores apresentados são projeções matemáticas baseadas nas taxas, "
    "dias úteis e aportes informados; não representam garantia de rentabilidade."
)
'''

# Verificação sintática antes de disponibilizar o arquivo.
ast.parse(codigo)

destino = Path(__file__).resolve().parent / "Planejamento_Investimentos_DARK_AutoAjuste.py"
destino.write_text(codigo, encoding="utf-8")

print(f"Arquivo salvo em: {destino}")

# Confirma que o arquivo salvo também pode ser compilado.
compile(destino.read_text(encoding="utf-8"), str(destino), "exec")

print(f"Arquivo criado e validado: {destino}")
print(f"Tamanho: {destino.stat().st_size:,} bytes")
print("Verificações concluídas: AST parse e compilação Python sem erros.")
