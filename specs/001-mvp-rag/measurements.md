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

Medido em 25/09/2026 com `test/measure_indexing.py`: os 5 artigos do conjunto simulado (`test/README.md`) enviados numa só requisição ao sistema no Docker, worker com 4 threads, `cpus: 4` e `nice 10`, sistema sem outras perguntas. Tempo de processamento de cada documento, sem a espera na fila.

| Documento | Páginas | Trechos | Processamento | s/página |
|---|---|---|---|---|
| `freitas2025_vetworld_pressao_proteinuria.pdf` | 7 | 26 | 42,2 s | 6,0 |
| `miranda2024_fag_estadiamento_drc.pdf` | 9 | 19 | 27,4 s | 3,0 |
| `morita2025_frontiers_anlodipina_caes.pdf` | 10 | 35 | 50,8 s | 5,1 |
| `oliveira2020_mvez_sdma.pdf` | 6 | 15 | 22,9 s | 3,8 |
| `vergnano2016_actascivet_suplemento.pdf` | 9 | 24 | 36,0 s | 4,0 |
| **Total** | **41** | **119** | **179,3 s** | **4,4** |

O tempo acompanha o número de trechos (~1,5 s por trecho de até 500 tokens), não o de páginas: páginas densas de artigos em inglês geram mais trechos.

**Extrapolação** para o cenário da spec (100 documentos de 50 páginas = 5.000 páginas), por página, como pede o `test/README.md`: **~6 horas** e ~14,5 mil trechos. Confirma a previsão da seção 5.4 ("horas", 10 a 15 mil trechos); não muda o plano. No uso real a indexação se dilui, porque os documentos chegam aos poucos.

**Memória:** VM do Docker com 7,69 GiB (padrão do WSL2, metade dos 16 GB), no limite dos 8 GB da seção 11. Em repouso, `api` usa ~0,8 GB e `worker` ~0,9 GB; sem sinal de falta de memória durante a indexação.

**Ingestão (CA03, CA04):** `test/ingestion_checks.py` confirmou que um PDF só com imagem termina `failed` com a mensagem de escaneado, que o reenvio dele reprocessa e falha de novo, e que reenviar um artigo já indexado volta como duplicado.

## Latência (T27)

_A preencher._
