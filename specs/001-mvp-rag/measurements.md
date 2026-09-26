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

## Avaliação da busca e calibração (T26)

Medido em 25/09/2026 com `test/eval_retrieval.py`: as 16 perguntas de `test/questions.yaml` contra o banco da aplicação (os 5 artigos do conjunto simulado mais 2 PDFs sobre doença articular enviados antes, que entram como ruído realista), sem limiar, com os 12 melhores trechos. Acerto = algum trecho recuperado no documento e na página esperados (nas perguntas `multi_doc`, pelo menos N documentos).

| TOP_K | 4 | 6 | 8 | 10 | 12 |
|---|---|---|---|---|---|
| Acertos (14 perguntas com resposta) | 10 | 10 | **11** | 12 | 12 |

- **Cross-lingual (CA09):** as 8 perguntas em português sobre artigos em inglês acertaram, 7 delas em 1º lugar.
- **Erros com TOP_K=8:** Q01 (creatinina por estágio, D2 p. 3) não aparece nem entre os 12; Q14 (sódio, D2 p. 7) só na 10ª posição; Q09 (prevalência em 3 dos 4 artigos) não reúne documentos suficientes. Nos dois primeiros o texto foi extraído corretamente, mas a informação ocupa uma parte pequena de um trecho de 500 tokens que mistura vários assuntos, o que dilui o embedding. Trechos menores (`CHUNK_SIZE`) são o ajuste natural; exige reindexar e fica como proposta para uma próxima spec.
- **Similaridades comprimidas:** tudo entre ~0,50 e ~0,75. O acerto mais fraco decidiu com 0,579; a pergunta sem resposta Q12 chegou a 0,553 e a Q13 a **0,660**, acima de vários acertos.

**Decisões:**

- **`MIN_SIMILARITY` = 0,5.** Não barra nenhuma pergunta válida e deixa 0,08 de margem para perguntas reais, mais vagas que as simuladas. Subir até 0,56 barraria a Q12, mas com só 0,02 de margem para o acerto mais fraco (prioridade ao CA09, seção 6.3). Como a Q13 fica acima de acertos válidos, nenhum limiar separa as perguntas sem resposta: o CA08 depende, na prática, da instrução do prompt (seção 6.2), verificada nas respostas (parte 2).
**Respostas (parte 2):** `test/eval_answers.py` rodou as 16 perguntas e as 2 sequências contra o Groq real; o relatório completo, para marcar os CAs à mão, está em `test/answers-2026-09-25.md`. Resumo da revisão:

- **Tempo:** todas entre 1,7 e 3,8 s, sem bater no limite do Groq com 65 s entre perguntas.
- **CA06/CA08:** a armadilha de espécie (Q10, F02.3) diz explicitamente que o estudo é em cães; as perguntas sem resposta (Q12, Q13) respondem que não há informação, sem inventar. Onde a busca errou (Q01, Q14, F01.1) o modelo também não inventa: diz que os trechos não bastam.
- **CA09 e CA11:** respostas em português com os números certos dos artigos em inglês; as reescritas das sequências (F01, F02) ficaram corretas.
- **CA07:** 12 respostas citaram o documento e a página esperados. A F01.3 revelou um formato de citação do `gpt-oss` que o parser não reconhecia (`[2†L20-L23]`), e a resposta ficou sem citações: corrigido na revisão v10 do plano.
- **Exaustividade:** a Q09 (prevalência em 4 artigos) trouxe 2 fontes; limitação da busca com `TOP_K=8`, candidata à próxima spec.

- **`TOP_K` = 8, mantido.** Com 10 a busca ganharia a Q14, mas cada pergunta passaria de ~7 mil tokens, acima do limite de 8 mil tokens por minuto do Groq quando há histórico (seção 6.7).

## Reavaliação, ajuste da recuperação e comparação de modelos (T35, plano v11 e v12)

Medido em 25/09/2026, depois de tirar a seção de referências do índice (T30) e reindexar (T31). Relatórios: `test/retrieval-2026-09-25-chunk500.md`, `test/retrieval-2026-09-25.md`, `test/answers-2026-09-25-openai-gpt-oss-120b.md` e `test/answers-2026-09-25-qwen-qwen3.8-27b.md`.

**Recuperação** (página esperada entre os trechos enviados, 14 perguntas com resposta; `eval_retrieval.py`):

| Configuração | TOP_K 8 | TOP_K 10 | TOP_K 12 |
|---|---|---|---|
| T26: trechos de 500, com referências | 11/14 | 12/14 | 12/14 |
| Trechos de 500, sem referências | 12/14 | 12/14 | 12/14 |
| **Trechos de 300 (sobreposição 50), sem referências** | 11/14 | 13/14 | **14/14** |

- Tirar as referências resolveu a Q14 (posição 10 para 4). A Q01 (D2) continuou na posição 17: pela regra da seção 6.3, item 2 (falha além da posição 10 em documento de páginas densas), `CHUNK_SIZE` caiu para 300.
- Com trechos de 300, a Q01 subiu para a posição 9; a Q03 desceu de 7 para 12, porque o dado dela ficou dividido em mais trechos. Com `TOP_K` 12 todas acertam, inclusive a Q09 (exaustividade, 3 documentos), e todos os trechos que decidiram um acerto têm similaridade de pelo menos 0,54, acima do `MIN_SIMILARITY` de 0,5.
- **Decisão (plano v12):** `CHUNK_SIZE` 300, `CHUNK_OVERLAP` 50, `TOP_K` 12. São 3,6 mil tokens de trechos por pergunta, menos que os 4 mil de antes (8 × 500). A busca híbrida não foi necessária.
- **Falha que continua:** a F01.1 ("valores de creatinina de cada estágio IRIS") não traz a D2 p. 3 entre os 12, embora a Q01, com outra redação, traga. Perguntas com siglas e termos exatos são o caso previsto para a busca híbrida (seção 6.3, item 3); fica registrado para a próxima spec.

**Comparação de modelos** (`eval_answers.py`, mesmo índice e configuração):

| Métrica | `openai/gpt-oss-120b` | `qwen/qwen3.8-27b` |
|---|---|---|
| Itens concluídos | 16 de 22 (limite diário do Groq na F01.1) | 22 de 22 |
| Recuperação | 15/15 | 17/19 |
| Citação no documento esperado | 13/15 | 17/19 |
| Respostas sem citação (`uncited`) | 3 (Q10, Q12, Q13: respostas "os trechos não bastam") | 0 |
| Tempo médio | 2,5 s | 2,1 s |

Revisão das respostas:

- **qwen:** cita sempre e acerta a armadilha de espécie (Q10, F02.3), mas perde nas regras de conteúdo da seção 6.2: erro factual na Q12 ("hipofosfatemia" onde o artigo trata de hiperfosfatemia), português com erros ("gatos giovani", "estudorelata", "concentração séria de creatinina", nome do autor trocado), classifica como efeito colateral o aumento de frequência cardíaca que o estudo só registra (Q11), e nas perguntas sem resposta continua falando de outros assuntos depois de dizer que não há informação.
- **gpt-oss:** português correto e respostas mais contidas; a Q10 está certa no conteúdo (dados só de cães), mas sem citação, o que o aviso da seção 6.4 sinaliza.
- **Decisão:** pelo critério da seção 12 (trocar só se o outro for melhor em citação **sem perder nas regras de conteúdo**), o padrão continua `openai/gpt-oss-120b`.

**Pendente:** as sequências F01 e F02 com o `gpt-oss-120b`, interrompidas pelo limite diário, rodam no dia seguinte com `eval_answers.py --model openai/gpt-oss-120b --only F01,F02`. Na rodada interrompida, as tentativas repetidas na mesma conversa geraram histórico e mudaram a busca da F01.1; o script não repete mais (para no 429).

## Latência (T27)

Medido em 25/09/2026 com `test/measure_latency.py`: tempo entre o envio da pergunta e o fim da resposta (evento `done`), Q01 a Q05 do conjunto simulado, cada uma numa conversa nova, 65 s entre perguntas por causa do limite do Groq. No cenário com indexação, o worker processava um PDF sintético de 80 páginas enviado antes das perguntas.

| Pergunta | Ocioso | Worker indexando |
|---|---|---|
| Q01 | 10,5 s | 3,3 s |
| Q02 | 2,8 s | 3,7 s |
| Q03 | 3,8 s | 3,1 s |
| Q04 | 2,8 s | 2,4 s |
| Q05 | 2,9 s | 1,9 s¹ |
| **Média / máximo** | **4,6 s / 10,5 s** | **2,9 s / 3,7 s** |

¹ A indexação terminou pouco antes da Q05; as outras quatro rodaram com o documento em `processing`.

- **RNF de ~15 s atendido nos dois cenários**, com folga. A divisão de CPU da seção 11 (worker com 4 threads, `cpus: 4` e `nice 10`) funciona: a indexação não atrasou as perguntas. Não há ajuste de threads a fazer.
- **Q01 ociosa (10,5 s):** foi a primeira pergunta depois de recriar a `api`; o tempo extra é aquecimento (primeira execução do modelo de embedding e primeiras conexões), não se repetiu.
- A maior parte do tempo é a geração no Groq; busca e embedding da pergunta levam frações de segundo.
