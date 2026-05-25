"""
Calculadora Live: Over 1.5 / Over 2.5 FT
Modelo: Poisson bivariado (Dixon-Coles) ponderado pelo tempo de jogo
Rodar: streamlit run app.py
"""

import streamlit as st
import numpy as np
import pandas as pd
from scipy.stats import poisson
import math

# ============================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================
st.set_page_config(
    page_title="Live Over 1.5/2.5 — Poisson Bivariado",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("⚽ Calculadora Live — Over 1.5 / Over 2.5 FT")
st.caption(
    "Modelo Poisson bivariado (Dixon–Coles) com xG remanescente ponderado pelo tempo. "
    "Cálculo dinâmico a cada alteração de input."
)

# ============================================================
# SIDEBAR — PARÂMETROS DO MODELO
# ============================================================
with st.sidebar:
    st.header("⚙️ Parâmetros do Modelo")

    rho = st.slider(
        "ρ (Dixon-Coles)",
        min_value=-0.20, max_value=0.20, value=-0.08, step=0.01,
        help="Correção para placares baixos. ρ ≈ -0.1 a -0.15 é típico. "
             "ρ = 0 reduz ao modelo Poisson independente."
    )

    margem_ev = st.slider(
        "Margem mínima de EV para apostar (%)",
        min_value=0.0, max_value=15.0, value=3.0, step=0.5,
        help="EV mínimo exigido para sinalizar 'APOSTAR'."
    ) / 100

    max_goals = st.number_input(
        "Limite da matriz de placares",
        min_value=6, max_value=15, value=10, step=1,
        help="Tamanho da matriz Home × Away. 10 cobre 99.99% dos casos."
    )

    st.markdown("---")
    st.markdown("**Como o modelo trabalha**")
    st.caption(
        "1. xG acumulado → taxa por minuto.\n"
        "2. Projeta λ remanescente = taxa × (90 − minuto).\n"
        "3. Poisson bivariado gera matriz de gols restantes.\n"
        "4. Soma com gols já marcados → P(Over 1.5) e P(Over 2.5).\n"
        "5. Fair odd = 1/P. EV = (P × odd) − 1."
    )

# ============================================================
# INPUTS PRINCIPAIS
# ============================================================
col_a, col_b = st.columns(2, gap="large")

with col_a:
    st.subheader("📊 Estado do Jogo")
    minute = st.slider("Minuto atual", 1, 90, 45, 1)

    sub1, sub2 = st.columns(2)
    with sub1:
        goals_home = st.number_input("⚽ Gols Casa", 0, 20, 0, 1)
        xg_home = st.number_input(
            "xG Casa (acumulado)", min_value=0.00, value=0.80,
            step=0.05, format="%.2f"
        )
    with sub2:
        goals_away = st.number_input("⚽ Gols Fora", 0, 20, 0, 1)
        xg_away = st.number_input(
            "xG Fora (acumulado)", min_value=0.00, value=0.60,
            step=0.05, format="%.2f"
        )

with col_b:
    st.subheader("💰 Odds do Mercado")

    st.markdown("**Odds In-Live (atuais)**")
    sub3, sub4 = st.columns(2)
    with sub3:
        odd_o15_live = st.number_input(
            "Odd Over 1.5 (live)", min_value=1.01, value=1.40,
            step=0.01, format="%.2f"
        )
    with sub4:
        odd_o25_live = st.number_input(
            "Odd Over 2.5 (live)", min_value=1.01, value=2.10,
            step=0.01, format="%.2f"
        )

    st.markdown("**Odds Pré-Jogo (referência)**")
    sub5, sub6 = st.columns(2)
    with sub5:
        odd_o15_pre = st.number_input(
            "Odd Over 1.5 (pré)", min_value=1.01, value=1.30,
            step=0.01, format="%.2f"
        )
    with sub6:
        odd_o25_pre = st.number_input(
            "Odd Over 2.5 (pré)", min_value=1.01, value=1.85,
            step=0.01, format="%.2f"
        )

# ============================================================
# MODELO POISSON BIVARIADO COM DIXON-COLES
# ============================================================
def dc_tau(x: int, y: int, lh: float, la: float, rho: float) -> float:
    """Ajuste de Dixon-Coles para placares baixos."""
    if x == 0 and y == 0:
        return 1 - lh * la * rho
    if x == 0 and y == 1:
        return 1 + lh * rho
    if x == 1 and y == 0:
        return 1 + la * rho
    if x == 1 and y == 1:
        return 1 - rho
    return 1.0


def score_matrix(lh: float, la: float, rho: float, max_g: int) -> np.ndarray:
    """Matriz de probabilidade de gols restantes (Home × Away)."""
    i = np.arange(max_g + 1)
    pi_h = poisson.pmf(i, lh)
    pi_a = poisson.pmf(i, la)
    M = np.outer(pi_h, pi_a)

    # Aplica ajuste DC nas células de placar baixo
    for x in range(min(2, max_g + 1)):
        for y in range(min(2, max_g + 1)):
            M[x, y] *= dc_tau(x, y, lh, la, rho)

    # Renormaliza (cauda truncada + ajuste DC)
    s = M.sum()
    if s > 0:
        M /= s
    return M


def prob_over(matrix: np.ndarray, current_goals: int, line: float) -> float:
    """P(gols_totais > line) dado o estado atual."""
    # Mínimo de gols TOTAIS para vencer o Over
    min_total = math.floor(line) + 1
    # Mínimo de gols RESTANTES
    min_remaining = min_total - current_goals
    if min_remaining <= 0:
        return 1.0

    n = matrix.shape[0]
    # Soma das células onde i + j >= min_remaining
    idx_h, idx_a = np.indices((n, n))
    mask = (idx_h + idx_a) >= min_remaining
    return float(matrix[mask].sum())


# ----- CÁLCULOS -----
time_remaining = max(90 - minute, 0)

# Taxa por minuto e λ remanescentes
if minute > 0:
    rate_home = xg_home / minute
    rate_away = xg_away / minute
else:
    rate_home = rate_away = 0.0

lambda_h_rem = rate_home * time_remaining
lambda_a_rem = rate_away * time_remaining

# Matriz de gols restantes
M = score_matrix(lambda_h_rem, lambda_a_rem, rho, int(max_goals))

goals_current = goals_home + goals_away
p_o15 = prob_over(M, goals_current, 1.5)
p_o25 = prob_over(M, goals_current, 2.5)

# Fair odds & EV
fair_o15 = (1 / p_o15) if p_o15 > 0 else float("inf")
fair_o25 = (1 / p_o25) if p_o25 > 0 else float("inf")

ev_o15 = p_o15 * odd_o15_live - 1
ev_o25 = p_o25 * odd_o25_live - 1

# Probabilidade implícita das odds
imp_o15_live = 1 / odd_o15_live
imp_o25_live = 1 / odd_o25_live
imp_o15_pre = 1 / odd_o15_pre
imp_o25_pre = 1 / odd_o25_pre

# ============================================================
# PAINEL — PROBABILIDADES E EV
# ============================================================
st.markdown("---")
st.subheader("🎯 Resultado do Modelo")

m1, m2, m3, m4 = st.columns(4)
m1.metric("⏱️ Tempo restante", f"{time_remaining}'")
m2.metric("📈 xG/min Casa", f"{rate_home:.3f}")
m3.metric("📈 xG/min Fora", f"{rate_away:.3f}")
m4.metric("🎲 Gols esperados restantes", f"{lambda_h_rem + lambda_a_rem:.2f}")

st.markdown("### Comparação dos Mercados")

def card_mercado(nome, p_modelo, odd_live, odd_pre, fair, ev, margem):
    """Renderiza o cartão de cada mercado."""
    imp_live = 1 / odd_live
    imp_pre = 1 / odd_pre

    if ev >= margem:
        veredito = "✅ **APOSTAR** — EV positivo acima da margem"
        cor = "success"
    elif ev > 0:
        veredito = "🟡 **MARGINAL** — EV positivo, mas abaixo da margem mínima"
        cor = "warning"
    else:
        veredito = "❌ **NÃO APOSTAR** — sem valor esperado"
        cor = "error"

    with st.container(border=True):
        st.markdown(f"#### {nome}")

        c1, c2, c3 = st.columns(3)
        c1.metric("Probabilidade (modelo)", f"{p_modelo*100:.2f}%")
        c2.metric("Fair odd (equilíbrio)", f"{fair:.2f}" if math.isfinite(fair) else "∞")
        c3.metric(
            "EV (odd live)",
            f"{ev*100:+.2f}%",
            delta=f"{(ev - margem)*100:+.2f}% vs margem",
            delta_color="normal",
        )

        c4, c5, c6 = st.columns(3)
        c4.metric("Odd live", f"{odd_live:.2f}", help=f"Implícita: {imp_live*100:.2f}%")
        c5.metric("Odd pré", f"{odd_pre:.2f}", help=f"Implícita: {imp_pre*100:.2f}%")
        movimento = odd_live - odd_pre
        c6.metric("Δ live vs pré", f"{movimento:+.2f}")

        if cor == "success":
            st.success(veredito)
        elif cor == "warning":
            st.warning(veredito)
        else:
            st.error(veredito)


col_o15, col_o25 = st.columns(2, gap="large")
with col_o15:
    card_mercado("Over 1.5 FT", p_o15, odd_o15_live, odd_o15_pre, fair_o15, ev_o15, margem_ev)
with col_o25:
    card_mercado("Over 2.5 FT", p_o25, odd_o25_live, odd_o25_pre, fair_o25, ev_o25, margem_ev)

# ============================================================
# DIAGNÓSTICOS — MATRIZ DE PLACARES & DETALHES
# ============================================================
st.markdown("---")
with st.expander("🔬 Diagnóstico técnico (matriz de placares restantes e detalhes)", expanded=False):
    st.markdown(
        f"**λ remanescente Casa:** `{lambda_h_rem:.3f}`  |  "
        f"**λ remanescente Fora:** `{lambda_a_rem:.3f}`  |  "
        f"**Gols já marcados:** `{goals_current}`"
    )

    n_show = min(7, M.shape[0])
    df = pd.DataFrame(
        (M[:n_show, :n_show] * 100).round(2),
        index=[f"Casa {i}" for i in range(n_show)],
        columns=[f"Fora {j}" for j in range(n_show)],
    )
    st.markdown("**Matriz de probabilidades — gols restantes (%)**")
    st.dataframe(df.style.background_gradient(cmap="Blues", axis=None).format("{:.2f}"))

    # Distribuição agregada de gols TOTAIS no jogo
    n = M.shape[0]
    idx_h, idx_a = np.indices((n, n))
    total_remaining = idx_h + idx_a
    max_total_rem = int(total_remaining.max())

    dist_tot = []
    for k in range(max_total_rem + 1):
        p = float(M[total_remaining == k].sum())
        dist_tot.append({"Gols totais no jogo": goals_current + k, "Probabilidade (%)": round(p * 100, 2)})
    dist_df = pd.DataFrame(dist_tot)
    st.markdown("**Distribuição final de gols no jogo**")
    st.bar_chart(dist_df.set_index("Gols totais no jogo"))

    st.caption(
        "Premissa: a taxa de xG por minuto observada até agora é a melhor estimativa "
        "para a taxa do tempo restante. Isso ignora efeitos de placar (time perdendo ataca mais) "
        "e cartões. Para refinar, basta ajustar manualmente o xG acumulado para refletir o cenário esperado."
    )

# ============================================================
# RODAPÉ
# ============================================================
st.markdown("---")
st.caption(
    "⚠️ Ferramenta de apoio analítico, não recomendação de aposta. "
    "Modelo assume taxa de xG estacionária no tempo restante; ajuste manualmente em cenários extremos "
    "(vermelho, virada, time desistindo, etc.)."
)
