# Tarefas 001 — MVP Assistente de pesquisa para TCC

> Spec: `spec.md` · Plano: `plan.md` (v8) · Quadro: https://trello.com/b/kiVC5tnp/projeto-rag-tcc

Tarefas pequenas, em ordem de dependência. Cada uma aponta os CAs que atende e as seções do plano que a descrevem. Uma tarefa só está pronta quando os testes indicados em "Pronto quando" passam.

**Tipos de teste** (plano, seção 12):

- **unit:** sem banco nem rede; roda com `uv run pytest`.
- **integração:** contra o Postgres do Compose, com o `LLMProvider` falso; marcados com `@pytest.mark.integration`.
- **manual:** validação na interface ou com o conjunto de avaliação; a tarefa passa pela coluna "Em revisão".

O plano não define testes automatizados de front-end, então as tarefas de front são validadas por build (`npm run build`) mais verificação manual dos CAs.

## Fase 0 — Estrutura

### T00 — Scaffolding do repositório ✅

Monorepo, back-end com uv e pacotes da seção 3, config da seção 10, `/health` mínimo, worker vazio, Alembic com a extensão `vector`, front-end com proxy de `/api`, React Router e shadcn/ui (plano v4), Docker Compose com os cinco serviços. Commits `bebf16b` e o de router/shadcn.

- **Plano:** 2, 3, 10, 11

## Fase 1 — Fundações

### T01 — Modelos e migração das tabelas

Modelos SQLAlchemy das seis tabelas da seção 4 (`documents`, `chunks` com `vector(1024)` e sem índice vetorial, `conversations`, `messages`, `citations`, `worker_heartbeat`), com a restrição única de `file_hash` e a cascata de `messages`/`citations` a partir de `conversations`. Migração Alembic `0002`. Engine e fábrica de sessões em `db/`, dependência de sessão para o FastAPI em `core/`. Fixture de pytest para os testes de integração (banco do Compose, tabelas limpas entre testes) e o marcador `integration`.

- **CAs:** 10 (base para todos)
- **Plano:** 4, 5.2, 12
- **Depende de:** T00
- **Pronto quando:** integração: `alembic upgrade head` e `downgrade` funcionam; inserir dois documentos com o mesmo `file_hash` gera `IntegrityError`; apagar uma conversa apaga mensagens e citações.

### T02 — Módulo de embeddings

Carregamento do bge-m3 (`EMBEDDING_MODEL`) com `torch.set_num_threads` recebido de quem chama (`API_TORCH_THREADS` ou `WORKER_TORCH_THREADS`). Função de encode em lotes de 16, com vetores normalizados, e acesso ao tokenizador do modelo para o chunking. Sem FastAPI.

- **CAs:** 01, 09
- **Plano:** 1, 2, 5.3, 10
- **Depende de:** T00
- **Pronto quando:** unit (marcado `slow`, baixa o modelo): vetores têm 1024 dimensões e norma 1; uma frase em português e sua tradução em inglês têm similaridade maior que a de uma frase não relacionada.

### T03 — Interface LLMProvider, Groq e provedor falso

Interface `LLMProvider` com `complete` e `stream`. Implementação Groq com o SDK da OpenAI apontando para a URL do Groq, e com o limite de requisições (HTTP 429) convertido numa exceção própria. Implementação falsa com respostas fixas para os testes. Antes de fechar, confirmar no console do Groq os limites reais do plano gratuito e do tier Developer, e registrá-los em `specs/001-mvp-rag/measurements.md`.

- **CAs:** 06 (base para 06 a 09, 11)
- **Plano:** 2, 6.7, 10
- **Depende de:** T00
- **Pronto quando:** unit: o provedor falso devolve e transmite a resposta configurada; com o cliente OpenAI simulado, o Groq transmite os pedaços em ordem e um 429 vira a exceção de limite; limites do Groq registrados em `measurements.md`.

## Fase 2 — Ingestão

### T04 — Verificações de arquivo

Função que abre o PDF com PyMuPDF e classifica, nesta ordem: corrompido/inválido, protegido por senha, sem texto extraível (média abaixo de ~50 caracteres por página). Devolve as mensagens exatas da seção 5.3.

- **CAs:** 03
- **Plano:** 5.3
- **Depende de:** T00
- **Pronto quando:** unit com PDFs gerados no próprio teste: um caso por verificação, mais um PDF válido que passa.

### T05 — Extração por página e chunking

Extração do texto página a página, com `page_number` a partir de 1. Divisão de cada página em trechos de `CHUNK_SIZE` tokens com `CHUNK_OVERLAP` de sobreposição, contados com o tokenizador do bge-m3; trechos nunca cruzam páginas.

- **CAs:** 01, 07
- **Plano:** 4 (páginas e chunking por página), 5.3
- **Depende de:** T02
- **Pronto quando:** unit: nenhum trecho mistura páginas; tamanho e sobreposição respeitam a configuração; a primeira página vem como 1; página curta vira um único trecho.

### T06 — Regras de upload

Função de domínio que recebe os arquivos, recusa os que não são PDF ou passam de `MAX_UPLOAD_MB`, calcula o SHA-256, agrupa repetições na mesma requisição e aplica a tabela da seção 5.1 (novo, duplicado, reprocessado, reativado). Salva o arquivo como `{DATA_DIR}/{file_hash}.pdf`, sem usar o nome enviado em caminhos. Trata o `IntegrityError` de uploads concorrentes como duplicado.

- **CAs:** 01, 03, 04, 17
- **Plano:** 4 (armazenamento), 5.1
- **Depende de:** T01
- **Pronto quando:** integração: um caso por linha da tabela 5.1; arquivo não PDF e arquivo grande demais recusados; mesmo arquivo duas vezes na requisição; dois uploads simultâneos do mesmo hash resultam em um registro e um duplicado; nome malicioso (`../x.pdf`) não afeta o caminho salvo.

### T07 — Rotas de documentos

`POST /documents` (multipart; adicionar `python-multipart`), `GET /documents` e `GET /documents/{id}` com posição na fila, `GET /documents/{id}/file` só para ativos, `DELETE /documents/{id}` como soft delete. Schemas Pydantic de entrada e saída.

- **CAs:** 01, 02, 04, 05, 17
- **Plano:** 5.1, 8
- **Depende de:** T06
- **Pronto quando:** integração: upload múltiplo devolve o resultado por arquivo; posição na fila conta só `pending` não removidos criados antes; documento removido some da lista e o `/file` responde 404; reenvio reativa.

### T08 — Worker: fila e processamento

Loop do worker que reivindica o próximo documento com `FOR UPDATE SKIP LOCKED`, passa para `processing` e incrementa `attempts` na mesma transação; espera alguns segundos quando a fila está vazia. Processa com T04, T05 e T02 e grava trechos e embeddings numa única transação, terminando em `ready`. Qualquer exceção não prevista faz rollback dos trechos, marca `failed` com a mensagem genérica, registra no log e segue para o próximo. Define `OMP`/`MKL` e as threads do PyTorch a partir de `WORKER_TORCH_THREADS`.

- **CAs:** 01, 03, 10
- **Plano:** 5.2, 5.3, 10
- **Depende de:** T01, T02, T04, T05
- **Pronto quando:** integração (embedding simulado): documento válido vira `ready` com trechos; PDF sem texto vira `failed` com a mensagem certa; exceção inesperada num documento o marca `failed` e o seguinte é processado; dois consumidores não pegam o mesmo documento; documento removido e `pending` não é reivindicado; documento removido durante o processamento termina de ser processado e continua removido.

### T09 — Worker: recuperação e limite de tentativas

Na inicialização, para cada documento em `processing`: apaga trechos parciais; volta para `pending` se `attempts < MAX_ATTEMPTS`, senão marca `failed` com "o processamento deste arquivo falhou repetidamente".

- **CAs:** 03, 10
- **Plano:** 5.2
- **Depende de:** T08
- **Pronto quando:** integração: documento em `processing` abaixo do limite volta para `pending` sem trechos; no limite, vira `failed` com a mensagem.

### T10 — Heartbeat do worker e /health

Thread do worker que grava `last_seen_at` a cada 10 s, mesmo ocioso. `GET /health` informa o estado do banco e do worker (parado se o heartbeat tiver mais de 60 s). O estado do modelo de embedding entra no `/health` na T12, junto com o carregamento do bge-m3 na `api`.

- **CAs:** — (suporte a 02 e 03)
- **Plano:** 5.5, 8
- **Depende de:** T08
- **Pronto quando:** integração: heartbeat é atualizado durante um processamento longo simulado; `/health` mostra o worker parado com heartbeat antigo e ativo com heartbeat recente; banco fora do ar aparece no `/health`.

### T11 — Medição de dimensionamento

Indexar 5 documentos típicos dela, medir o tempo e extrapolar para o cenário de 100 documentos de 50 páginas. Conferir o limite de memória da VM do Docker Desktop (pelo menos 8 GB). Registrar os números em `specs/001-mvp-rag/measurements.md` e, se a expectativa mudar, propor revisão no plano.

- **CAs:** RNF de volume
- **Plano:** 5.4, 11 (memória), 12
- **Depende de:** T07, T08
- **Pronto quando:** manual: medição registrada e revisada com ela.

## Fase 3 — Consulta

### T12 — Busca vetorial

Busca exata (sem índice) dos `TOP_K` trechos mais próximos com `<=>`, só de documentos `ready` e sem `deleted_at`, com similaridade `1 - distância`, descartando os que ficam abaixo de `MIN_SIMILARITY`. O módulo de busca não importa FastAPI. Na `api`, o bge-m3 é carregado na inicialização com `API_TORCH_THREADS`, para gerar o embedding das perguntas, e o `/health` passa a informar o estado do modelo.

- **CAs:** 05, 08, 09
- **Plano:** 1, 6 (etapas 2 e 3), 6.3, 8
- **Depende de:** T01, T02, T10
- **Pronto quando:** integração com vetores montados no teste: ordem por similaridade; documentos removidos, `pending` e `failed` nunca aparecem; limiar descarta trechos fracos; sem trechos acima do limiar devolve lista vazia; `/health` informa o modelo como carregado (modelo simulado).

### T13 — Parser de marcadores

Extração de `[1]`, `[1, 3]`, `[1-3]` e `[1–3]` da resposta, ignorando números fora do intervalo de trechos enviados.

- **CAs:** 07
- **Plano:** 6.4
- **Depende de:** T00
- **Pronto quando:** unit: marcador simples, lista, intervalo com hífen e com travessão, número inexistente, resposta sem marcadores.

### T14 — Preparação do histórico

Monta as últimas `HISTORY_TURNS` trocas: troca cada `[n]` das respostas anteriores por "(arquivo, p. X)" usando `citations`; omite respostas que citam documento removido (mantém a pergunta); omite respostas com status `error`.

- **CAs:** 05, 07, 11
- **Plano:** 6.1
- **Depende de:** T01
- **Pronto quando:** unit: substituição de marcadores; resposta com documento removido omitida e pergunta mantida; resposta `error` omitida; limite de trocas respeitado; resposta "não encontrei" presente.

### T15 — Montagem do prompt

Instruções em português da seção 6.2, trechos numerados a partir de [1] com arquivo e página, histórico preparado numa seção delimitada e a pergunta.

- **CAs:** 06, 07, 08, 09
- **Plano:** 6 (etapa 4), 6.2
- **Depende de:** T12, T14
- **Pronto quando:** unit: numeração dos trechos bate com a ordem enviada; histórico aparece só dentro da seção delimitada; sem histórico, a seção não aparece.

### T16 — Reescrita da pergunta

Com histórico, o modelo pequeno (`LLM_REWRITE_MODEL`) reescreve a pergunta como independente; sem histórico, a pergunta original segue direto.

- **CAs:** 11
- **Plano:** 6 (etapa 1), 6.1
- **Depende de:** T03, T14
- **Pronto quando:** unit com provedor falso: sem histórico não chama a LLM; com histórico devolve a versão reescrita.

### T17 — Rotas de conversas

`POST /conversations` (fecha as abertas), `POST /conversations/close-open`, `GET /conversations` (sem conversas vazias, com data e título), `GET /conversations/{id}` (mensagens, status, citações e flag de documento removido), `DELETE /conversations/{id}` em cascata. Função de domínio que verifica se uma conversa está aberta, usada pela T18 para a regra do 409.

- **CAs:** 13, 14, 15, 16
- **Plano:** 4, 7, 8
- **Depende de:** T01
- **Pronto quando:** integração: criar fecha a anterior; `close-open` fecha todas; lista esconde conversas vazias; citação de documento removido vem com a flag e o trecho copiado; exclusão remove mensagens e citações; a função de verificação distingue conversa aberta, fechada e inexistente.

### T18 — Envio de pergunta com SSE

`POST /conversations/{id}/messages`: responde 409 se a conversa estiver fechada (função da T17), sem salvar nada; senão salva a pergunta, reescreve (T16), busca (T12), responde "não encontrei" sem chamar a LLM quando nada passa do limiar (salva como `complete`, sem citações), monta o prompt (T15), transmite a resposta e, ao final, salva a mensagem com uma citação por marcador válido (T13), copiando trecho e nome do arquivo. Eventos `sources`, `token`, `done` e `error`.

- **CAs:** 06, 07, 08, 09, 11, 12, 13
- **Plano:** 6, 6.5, 7
- **Depende de:** T12, T13, T15, T16, T17
- **Pronto quando:** integração com provedor falso: mensagem para conversa fechada recebe 409 e não é gravada; a pergunta é salva antes da geração; eventos chegam na ordem certa; `rewritten_query` gravado quando há histórico; "não encontrei" salvo como `complete` e presente no histórico seguinte; citações salvas com cópia do trecho só para marcadores válidos.

### T19 — Falhas no streaming e limite do Groq

Erro do provedor ou desconexão do cliente (`request.is_disconnected()`, cancelando a chamada) descartam a resposta parcial e gravam uma mensagem da assistente com status `error`, protegida contra cancelamento (`asyncio.shield` ou sessão síncrona em thread). Limite do Groq atingido vira evento `error` com mensagem clara.

- **CAs:** 12
- **Plano:** 6.6, 6.7
- **Depende de:** T18
- **Pronto quando:** integração: erro do provedor no meio da resposta grava `error` sem conteúdo; desconexão do cliente grava `error` mesmo com o gerador cancelado; 429 gera o evento com a mensagem de limite.

### T20 — Título da conversa

Depois da primeira resposta, o modelo pequeno gera um título de até 6 palavras; se falhar, usa a primeira pergunta truncada.

- **CAs:** 14
- **Plano:** 6.8
- **Depende de:** T18
- **Pronto quando:** integração com provedor falso: título gerado após a primeira resposta; falha do provedor usa a pergunta truncada.

## Fase 4 — Front-end

### T21 — Layout, cliente da API e ciclo de vida da conversa

Barra lateral com as seções Documentos e Conversas e área principal do chat. Cliente da API com TanStack Query. Ao carregar o front, chama `POST /conversations/close-open`. O id da conversa atual fica só em memória.

- **CAs:** 13
- **Plano:** 7, 9
- **Depende de:** T17
- **Pronto quando:** build passa; manual: recarregar a página fecha a conversa aberta.

### T22 — Seção Documentos

Upload por arrastar ou selecionar vários arquivos, resultado por arquivo (novo, duplicado, reativado, reprocessado, recusado), polling de `GET /documents` a cada 2 s enquanto houver documentos `pending` ou `processing` (plano v8), posição na fila ("aguardando, 3º na fila"), mensagem de erro dos `failed`, botão de remover e aviso de worker parado a partir do `/health`.

- **CAs:** 01, 02, 03, 04, 05, 17
- **Plano:** 5.5, 9
- **Depende de:** T07, T10, T21
- **Pronto quando:** build passa; manual: cada CA listado verificado na interface com PDFs reais.

### T23 — Chat com streaming

Envio de pergunta com `@microsoft/fetch-event-source`, resposta aparecendo token a token e renderizada como markdown (`react-markdown`), criação da conversa na primeira mensagem, botão "Nova conversa" e tratamento do 409 (mensagem da seção 7, botão para nova conversa, pergunta mantida no campo). Mensagem clara quando o limite do Groq é atingido.

- **CAs:** 11, 12, 13
- **Plano:** 6.5, 6.7, 7, 9
- **Depende de:** T18, T19, T21
- **Pronto quando:** build passa; manual: pergunta de acompanhamento entendida; segunda aba fecha a conversa da primeira e o 409 aparece com a pergunta preservada.

### T24 — Citações e visualizador de PDF

Marcadores [n] clicáveis dentro do markdown renderizado, que abrem um painel com o trecho, o arquivo e a página, e um botão que abre o PDF naquela página com react-pdf.

- **CAs:** 07
- **Plano:** 9
- **Depende de:** T07, T23
- **Pronto quando:** build passa; manual: clicar numa citação mostra o trecho e abre o PDF na página certa.

### T25 — Conversas salvas

Lista de conversas com data e título, abertura em modo somente leitura (sem campo de pergunta), exclusão, citações de documentos removidos com aviso e sem o botão de abrir PDF, e mensagens `error` exibidas como "resposta não concluída".

- **CAs:** 14, 15, 16
- **Plano:** 9
- **Depende de:** T17, T24
- **Pronto quando:** build passa; manual: cada CA listado verificado na interface.

## Fase 5 — Validação

### T26 — Conjunto de avaliação e calibração

Montar com ela 10 a 15 perguntas reais, cada uma com documento e página esperados, incluindo perguntas em português sobre artigos em inglês, perguntas sem resposta nos documentos e sequências de acompanhamento. Medir se a busca encontra os trechos certos, calibrar `MIN_SIMILARITY` (começando baixo) e `TOP_K`, e avaliar a qualidade do português do `openai/gpt-oss-120b`. Validar manualmente os CAs que dependem da LLM real.

- **CAs:** 06, 07, 08, 09, 11
- **Plano:** 6 (etapa 5), 6.2, 6.3, 12
- **Depende de:** T18, T22, T23, T24
- **Pronto quando:** manual: conjunto registrado no repositório; valores calibrados no `.env.example`; CAs 06 a 09 e 11 aprovados na coluna "Em revisão".

### T27 — Teste de latência

Medir o tempo entre o envio da pergunta e o fim da resposta com o sistema ocioso e com o worker indexando um lote. Ajustar threads e `cpus` se o cenário com indexação passar de ~15 s.

- **CAs:** RNF de tempo de resposta
- **Plano:** 11, 12
- **Depende de:** T11, T18
- **Pronto quando:** manual: os dois cenários ficam em até ~15 s, com os números registrados em `measurements.md`.

### T28 — Aceite final

Percorrer os 17 CAs com o ambiente completo no Docker e PDFs reais, marcando cada um no checklist da Spec 001 no Trello (https://trello.com/c/KKeHxpKj).

- **CAs:** 01 a 17
- **Plano:** 12, 15
- **Depende de:** T25, T26, T27
- **Pronto quando:** manual: os 17 itens do checklist da Spec 001 marcados.

## Rastreabilidade

| Requisito | Tarefas |
|---|---|
| CA01 | T02, T05, T06, T07, T08, T22, T28 |
| CA02 | T07, T22, T28 |
| CA03 | T04, T06, T08, T09, T22, T28 |
| CA04 | T06, T07, T22, T28 |
| CA05 | T07, T12, T14, T22, T28 |
| CA06 | T03, T15, T18, T26, T28 |
| CA07 | T05, T13, T14, T15, T18, T24, T26, T28 |
| CA08 | T12, T15, T18, T26, T28 |
| CA09 | T02, T12, T15, T18, T26, T28 |
| CA10 | T01, T08, T09, T28 |
| CA11 | T14, T16, T18, T23, T26, T28 |
| CA12 | T18, T19, T23, T28 |
| CA13 | T17, T18, T21, T23, T28 |
| CA14 | T17, T20, T25, T28 |
| CA15 | T17, T25, T28 |
| CA16 | T17, T25, T28 |
| CA17 | T06, T07, T22, T28 |
| RNF: 100 documentos de 50 páginas | T11 |
| RNF: resposta em até ~15 s | T27 |
| RNF: dados não expostos | T00 (portas em 127.0.0.1), T06 (arquivos salvos por hash) |
