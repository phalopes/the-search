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

## Comandos

```bash
make check        # lint + type-check + testes (roda tudo)
make lint          # ruff check
make format        # ruff format
make typecheck      # mypy
make test           # pytest com cobertura
```
