# ⚽ Calculadora Live — Over 1.5 / Over 2.5 FT

Aplicação Streamlit para avaliação em tempo real de mercados Over 1.5 e Over 2.5 FT em jogos de futebol, usando **modelo Poisson bivariado (Dixon–Coles)** com xG remanescente ponderado pelo tempo de jogo.

A cada alteração de minuto, gols, xG ou odds, o modelo recalcula:

- Probabilidade de Over 1.5 e Over 2.5 FT
- **Fair odd** (ponto de equilíbrio)
- **EV** (valor esperado) das odds in-live
- Comparação com odds pré-jogo
- Veredito automático: apostar, marginal ou não apostar

---

## 🚀 Deploy no Streamlit Community Cloud

### Passo 1 — Subir os arquivos para o GitHub

Crie um repositório (público ou privado) com a seguinte estrutura:

```
seu-repo/
├── app.py
├── requirements.txt
├── README.md
└── .streamlit/
    └── config.toml
```

Como subir:

1. Acesse [github.com](https://github.com) e crie um repositório novo (ex.: `over-live-calc`).
2. Faça upload dos quatro arquivos mantendo a estrutura acima. **Atenção:** a pasta `.streamlit` deve ser preservada — no upload web do GitHub, arraste a pasta inteira ou crie o arquivo manualmente usando o caminho `.streamlit/config.toml`.

### Passo 2 — Conectar ao Streamlit Cloud

1. Acesse [share.streamlit.io](https://share.streamlit.io) e faça login com sua conta do GitHub.
2. Clique em **"Create app"** → **"Deploy a public app from GitHub"**.
3. Selecione:
   - **Repository:** `seu-usuario/over-live-calc`
   - **Branch:** `main`
   - **Main file path:** `app.py`
4. (Opcional) Defina uma URL customizada em **"Advanced settings"**.
5. Clique em **Deploy**.

O Streamlit instala as dependências do `requirements.txt` e disponibiliza a URL pública em ~2 minutos.

### Passo 3 — Atualizações

Qualquer push para a branch `main` re-deploya o app automaticamente.

---

## 💻 Rodar localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## 🧠 Sobre o modelo

- **Taxa instantânea de xG:** `λ_rem = (xG_acumulado / minuto_atual) × (90 − minuto_atual)`
- **Poisson bivariado** com correção **Dixon–Coles** (parâmetro ρ ajustável; típico entre −0.05 e −0.15).
- Matriz de gols restantes Home × Away, somada aos gols já marcados, define P(Over X.5).
- **Fair odd** = 1 / P. **EV** = (P × odd) − 1.

### Premissas

- A taxa de xG observada se mantém estacionária no tempo restante.
- Em cenários atípicos (vermelho, virada, time desistindo), ajuste manualmente o xG acumulado para refletir a produção esperada.

---

## ⚠️ Aviso

Ferramenta de apoio analítico. Não constitui recomendação de aposta.
