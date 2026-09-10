# the-search — convenções do projeto

Motor de recomendação de picos de surf (Floripa e região). Contexto completo do
produto/roadmap está em `docs/plano-desenvolvimento.md` (não versionado — se o
arquivo não existir na sua sessão, peça para o usuário compartilhar ou recriar).

## Estágio atual

Este projeto está em fase de **POC** (ver roadmap). Não introduzir infraestrutura
de produto (API, auth, múltiplos usuários, ML) antes do gate de decisão descrito
no plano, a menos que explicitamente pedido.

## Arquitetura — respeitar sempre

- `src/*/domain/` é **puro**: nunca importa `httpx`, `sqlite3`, SDKs de
  notificação ou qualquer I/O. Só lógica de score e modelos Pydantic.
- `src/*/adapters/` concentra todo I/O (APIs externas, storage, notificação).
- `src/*/app/` é orquestração/entrypoint (CLI hoje, API na fase de produto).
- Nunca passar `dict` solto entre camadas — toda leitura externa vira modelo
  Pydantic antes de chegar no domain.

## Padrões de código

- Python 3.12+. Type hints em tudo que for função pública.
- `ruff` para lint e format, `mypy` para type-check. Rodar os dois antes de
  considerar uma tarefa concluída.
- `uv` para dependências (não usar pip/poetry diretamente).
- Timeouts explícitos em qualquer chamada HTTP; retry (via `tenacity`) só em
  erro transitório (timeout/5xx), nunca em 4xx.
- Sem ML nesta fase — o motor de score é determinístico e explicável por
  design (é requisito de produto, não limitação técnica).

## Testes

- Toda função em `domain/scoring.py` precisa de teste unitário
  (parametrizado cobrindo casos de borda: dado faltante, vento onshore vs
  offshore, maré fora da faixa).
- Testes de `adapters/` mockam HTTP (respx) — nunca batem em API real em CI.
- Meta de cobertura: domain ≥90%, projeto geral ≥80%.
- Rodar `pytest` antes de reportar qualquer tarefa como concluída.

## O que NÃO fazer sem pedido explícito

- Não adicionar banco de dados além de sqlite nesta fase.
- Não construir API REST antes da Fase 3 do roadmap.
- Não commitar nada em `docs/` (está no `.gitignore` de propósito — é
  documentação auxiliar/planejamento, não parte do produto).
- Não adicionar abstrações (interfaces, plugins, config genérica) para casos
  hipotéticos futuros — três linhas parecidas é melhor que abstração prematura.
