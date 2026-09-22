# surfscout

Motor de recomendação de picos de surf (Florianópolis e região). Cruza dados de
previsão (swell, vento, maré) com o perfil estático de cada pico para sugerir
onde e quando surfar, de acordo com a janela de tempo e o nível do usuário.

Estágio atual: **POC** — ver `CLAUDE.md` para convenções do projeto.

## Setup

Requer [uv](https://docs.astral.sh/uv/) e Python 3.12+.

```bash
make install     # instala dependências + hooks de pre-commit
cp .env.example .env
```

## Comandos de desenvolvimento

```bash
make check        # lint + type-check + testes (roda tudo)
make lint          # ruff check
make format        # ruff format
make typecheck      # mypy
make test           # pytest com cobertura
```

## Uso diário (direto no terminal, sem precisar do Claude Code)

Todos os comandos abaixo rodam offline sem gastar tokens — só a `recommend`
bate nas APIs externas (Open-Meteo). Rode `uv run surfscout --help` ou
`uv run surfscout <comando> --help` a qualquer momento pra ver todas as opções.

### Pedir uma recomendação

```bash
uv run surfscout recommend --nivel intermediario
# --when "2026-09-22T07:00"  → data/hora específica (padrão: amanhã 07:00)
# --spots-path <arquivo>      → outro spots.yaml, se precisar
```

### Registrar uma sessão (ou julgamento pré-sessão) depois

```bash
uv run surfscout log \
  --data 2026-09-22 \
  --pico matadeiro \
  --nota 4 \
  --obs "Vento sul bateu certinho, ondas boas" \
  --pico-recomendado matadeiro \
  --score-recomendado 90.2
```

- `--data` e `--pico` são obrigatórios (`--pico` precisa ser um id válido do
  `spots.yaml` — mole, campeche, matadeiro, joaquina, barra-da-lagoa).
- `--nota` (1-5), `--obs`, `--horario` (HH:MM), `--pico-recomendado`,
  `--score-recomendado` e `--score-pico` são opcionais — preencha o quanto der
  pra comparar depois com o que o sistema previu.
- `--tipo sessao_real` (padrão) ou `--tipo julgamento_pre_sessao` (quando você
  não foi surfar, só comparou fontes).
- Grava em `data/historico.db` (sqlite, local, gitignored) — use `--db-path`
  pra apontar pra outro arquivo se quiser.

### Ver o histórico registrado

```bash
uv run surfscout historico
uv run surfscout historico --pico campeche   # filtra por pico
```
