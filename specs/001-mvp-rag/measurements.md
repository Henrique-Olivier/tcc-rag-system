# Medições 001 — MVP Assistente de pesquisa para TCC

Números reais que calibram o plano (seções 5.4, 6.7 e 12). Cada seção indica a tarefa que a preenche.

## Limites do Groq (T03)

Fonte: console do Groq (https://console.groq.com/settings/limits), consultado em 25/09/2026, plano gratuito. Os modelos `llama-3.3-70b-versatile` e `llama-3.1-8b-instant` do plano original não estavam mais disponíveis, o que motivou a revisão v6 do plano.

| Modelo | Uso | Requisições/min | Requisições/dia | Tokens/min | Tokens/dia |
|---|---|---|---|---|---|
| `openai/gpt-oss-120b` | Respostas | 30 | 1K | 8K | 200K |
| `openai/gpt-oss-20b` | Reescrita e títulos | 30 | 1K | 8K | 200K |

Com ~6 mil tokens por pergunta (seção 6.7): cerca de **33 perguntas por dia** (200K / 6K) e **1 por minuto** (8K / 6K) no modelo principal. A reescrita consome a cota separada do `gpt-oss-20b`.

Limites do tier Developer: não consultados; conferir no console se o plano gratuito ficar apertado.

## Dimensionamento da indexação (T11)

_A preencher._

## Latência (T27)

_A preencher._
