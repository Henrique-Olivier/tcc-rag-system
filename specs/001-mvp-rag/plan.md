# Plano técnico 001 — MVP Assistente de pesquisa para TCC

> Spec de referência: `specs/001-mvp-rag/spec.md` (card no Trello: https://trello.com/c/KKeHxpKj)

Este plano descreve **como** atender a Spec 001. Cada decisão importante aponta os critérios de aceite (CA) ou requisitos não funcionais (RNF) que ela resolve.

## Histórico de revisões

| Versão | Mudanças |
|---|---|
| v1 | Versão inicial |
| v2 | Fila de ingestão no banco e worker em processo separado; regras de reenvio considerando status; marcadores removidos do histórico; fechamento explícito de conversas ao carregar o front; latência e dimensionamento cobertos; busca exata sem HNSW; limiar calibrado com perguntas cross-lingual; orçamento do Groq corrigido; tratamento de falhas no streaming; detalhes de segurança e numeração de páginas; decisão sobre envio de dados ao Groq |
| v3 | Limite de tentativas e captura de exceções no worker; serviço `migrate` e healthcheck do banco; heartbeat e reinício automático do worker; divisão de CPU por núcleos físicos; gravação protegida do erro após desconexão; tratamento do 409 com várias abas; instruções sobre o histórico no prompt; destino da resposta "não encontrei"; upload duplicado concorrente; posição na fila na API; limite de tamanho de upload; correções pontuais de texto |
| v4 | React Router e shadcn/ui (Tailwind) no front-end; padrões provisórios de `HISTORY_TURNS` e `MIN_SIMILARITY`; variáveis `POSTGRES_*` do container do banco; proxy de `/api` remove o prefixo; porta do banco publicada em `127.0.0.1` para os testes de integração |

## 1. Arquitetura

O sistema é um monorepo com cinco serviços orquestrados por Docker Compose:

- **`db`:** Postgres com pgvector, que guarda documentos, trechos com embeddings e conversas, e também funciona como fila de ingestão.
- **`migrate`:** execução única do Alembic, que aplica as migrações e termina. Os demais serviços de back-end só sobem depois dele.
- **`api`:** back-end FastAPI, que atende o front, faz a busca e orquestra a LLM. Carrega o bge-m3 apenas para gerar o embedding das perguntas.
- **`worker`:** processo Python separado, com a mesma imagem do `api`, que consome a fila de ingestão e gera os embeddings dos documentos.
- **`frontend`:** React, que só consome a API.

A única dependência externa é a API do Groq.

**Por que o worker é um processo separado:** o limite de threads do PyTorch (`torch.set_num_threads`) vale para o processo inteiro. Se a ingestão e as perguntas rodassem no mesmo processo, não haveria como reservar CPU para as perguntas enquanto um lote grande é indexado. Com processos separados, cada um tem seus próprios limites, e o Compose pode restringir a CPU do worker (seção 11), mantendo a resposta rápida durante a indexação (RNF de ~15 s). Outro ganho: se um documento derrubar o processo de ingestão, a API continua de pé. O custo é carregar o bge-m3 duas vezes, cerca de 2 GB de RAM em cada processo, o que cabe com folga em 16 GB.

Os PDFs ficam num volume compartilhado entre `api` e `worker`, e o cache do Hugging Face também, para o modelo não ser baixado de novo a cada rebuild.

## 2. Stack

**Back-end (api e worker):** Python 3.12, FastAPI, SQLAlchemy 2 com Alembic para migrações, psycopg 3, a biblioteca `pgvector` para Python, PyMuPDF para extração, sentence-transformers com `BAAI/bge-m3` (vetores de 1024 dimensões), pydantic-settings para configuração e pytest para testes. A comunicação com o Groq usa o SDK da OpenAI apontando para a URL do Groq, já que a API é compatível, o que deixa trocar de provedor trivial.

**Front-end:** React com Vite e TypeScript, TanStack Query para chamadas e cache da API, react-pdf para o visualizador de PDF, e `@microsoft/fetch-event-source` para o streaming. Esse último é necessário porque o `EventSource` nativo do navegador só faz GET, e o envio de pergunta é POST. React Router para as páginas, preparando o front para funcionalidades futuras; o id da conversa atual continua fora da URL (seção 7). shadcn/ui, sobre Tailwind CSS, para os componentes visuais; os componentes são copiados para `src/components/ui/` e só entram os que forem usados.

## 3. Estrutura do repositório

```
rag-tcc/
├── specs/001-mvp-rag/        spec.md, plan.md, tasks.md
├── backend/
│   ├── app/
│   │   ├── api/              rotas FastAPI
│   │   ├── core/             configuração e dependências
│   │   ├── db/               modelos e migrações
│   │   ├── ingestion/        extração, chunking, regras de upload
│   │   ├── worker/           loop do worker e heartbeat (entrypoint separado)
│   │   ├── embeddings/       carregamento e uso do bge-m3
│   │   ├── retrieval/        busca vetorial
│   │   ├── llm/              interface do provedor + implementação Groq
│   │   └── chat/             reescrita, histórico, prompt, streaming, citações
│   └── tests/
├── frontend/src/             api/, components/ (ui/ do shadcn), pages/, hooks/, lib/
├── docker-compose.yml
└── .env.example
```

Os módulos de `ingestion`, `retrieval`, `llm` e `chat` não importam nada do FastAPI. As rotas e o worker só chamam esses módulos, o que mantém o núcleo testável sem HTTP.

## 4. Modelo de dados

| Tabela | Campos principais | Observações |
|---|---|---|
| `documents` | id, filename, file_hash (SHA-256, único), file_path, num_pages, status, error_message, attempts, created_at, deleted_at | status: `pending`, `processing`, `ready`, `failed`. `attempts` conta reivindicações pelo worker. `deleted_at` preenchido = soft delete |
| `chunks` | id, document_id, page_number, chunk_index, content, token_count, embedding `vector(1024)` | Sem índice vetorial (seção 6.2) |
| `conversations` | id, title, created_at, closed_at | `closed_at` nulo = conversa aberta |
| `messages` | id, conversation_id, role, content, rewritten_query, status, created_at | role: `user` ou `assistant`. status: `complete` ou `error` |
| `citations` | id, message_id, chunk_id, document_id, marker, filename, page_number, excerpt | `excerpt` e `filename` são **cópias**, não referências |
| `worker_heartbeat` | id (linha única), last_seen_at | Atualizada periodicamente pelo worker (seção 5.5) |

**Páginas:** `page_number` é sempre armazenado a partir de 1. O PyMuPDF numera a partir de 0, então a conversão acontece uma única vez, na extração. O react-pdf também numera a partir de 1, então o front usa o valor do banco sem ajustes.

**Chunking por página:** os trechos nunca cruzam páginas. Isso deixa a citação de página sempre exata, ao custo de alguns trechos mais curtos no fim das páginas, o que é aceitável.

**Soft delete:** como nunca apaga chunks, as chaves estrangeiras de `citations` continuam válidas. O aviso de "documento removido" (CA16) sai de um join com `documents.deleted_at`.

**Armazenamento dos arquivos:** cada PDF é salvo como `{DATA_DIR}/{file_hash}.pdf`. O nome enviado pela usuária fica só no campo `filename`, para exibição, e nunca é usado para montar caminhos, o que elimina risco de path traversal.

## 5. Pipeline de ingestão

### 5.1 Regras de upload

Arquivos acima de `MAX_UPLOAD_MB` (padrão 50 MB) ou que não sejam PDF são recusados com mensagem clara, antes de qualquer processamento. Para os demais, a `api` calcula o SHA-256 e aplica a primeira regra que corresponder:

| Situação do hash existente | Ação | CA |
|---|---|---|
| Não existe | Salva o arquivo, cria o registro `pending` | 01 |
| Ativo, com status `ready`, `pending` ou `processing` | Responde como duplicado, sem alterar nada | 04 |
| Qualquer um (ativo ou removido) com status `failed` | Reprocessa: apaga chunks residuais, limpa `error_message` e `deleted_at`, zera `attempts`, volta para `pending` | 03 |
| Removido, com status `ready` | Reativa: limpa `deleted_at`; disponível na hora, sem reprocessar | 17 |
| Removido, com status `pending` ou `processing` | Reativa: limpa `deleted_at`; o documento segue na fila | 17 |

A regra de `failed` existe porque uma falha pode ser transitória, como uma exceção por falta de memória num momento em que a máquina estava sobrecarregada. Se o arquivo for de fato um PDF escaneado, o reprocessamento falha de novo em segundos e mostra a mesma mensagem, então não há custo relevante em permitir a nova tentativa.

**Duplicados na mesma requisição ou concorrentes:** se o mesmo arquivo vier duas vezes no mesmo upload, a `api` agrupa os arquivos por hash antes de gravar e processa cada hash uma única vez, marcando as repetições como duplicadas. Se dois uploads simultâneos tentarem inserir o mesmo hash, a restrição única gera um `IntegrityError`, que a `api` captura e responde como duplicado (CA04).

### 5.2 Fila no banco

Não existe fila em memória. A própria tabela `documents` é a fila. O `worker` roda um loop que reivindica o próximo documento assim:

```sql
SELECT id FROM documents
WHERE status = 'pending' AND deleted_at IS NULL
ORDER BY created_at
LIMIT 1
FOR UPDATE SKIP LOCKED;
```

Na mesma transação, o documento passa para `processing` e `attempts` é incrementado. Quando não há nada pendente, o worker espera alguns segundos antes de consultar de novo. Documentos removidos enquanto estão `pending` ficam fora da fila até serem reativados. Um documento removido durante o processamento termina de ser processado normalmente e continua removido.

**Recuperação na inicialização:** ao subir, o worker percorre os documentos em `processing`, que só existem se o processo anterior morreu no meio do trabalho, e apaga os chunks parciais de cada um. Se `attempts` for menor que `MAX_ATTEMPTS` (padrão 3), o documento volta para `pending`. Se já atingiu o limite, é marcado como `failed` com a mensagem "o processamento deste arquivo falhou repetidamente". Isso impede que um arquivo que derruba o processo (OOM kill, falha nativa no PyMuPDF) entre num loop infinito e trave a fila inteira. Os documentos que estavam `pending` já continuam na fila, porque ela está no banco.

### 5.3 Processamento

O worker abre o PDF com PyMuPDF e verifica, nesta ordem:

- **Arquivo corrompido ou inválido** (erro ao abrir): `failed` com "o arquivo está corrompido ou não é um PDF válido".
- **PDF protegido por senha** (`needs_pass`): `failed` com "o PDF está protegido por senha".
- **Sem texto extraível** (média menor que ~50 caracteres por página): `failed` com a mensagem de que o arquivo parece ser escaneado (CA03).

Passando pelas verificações, o texto é extraído página a página, cada página é dividida em trechos de ~500 tokens com sobreposição de ~80, contados com o tokenizador do próprio bge-m3, e os embeddings são gerados em lotes de 16, normalizados e gravados junto com os trechos numa única transação. O documento passa para `ready` (CA01). Como tudo fica no Postgres e nos volumes, os documentos sobrevivem a reinícios (CA10).

**Nenhuma exceção derruba o loop:** o processamento de cada documento roda dentro de um `try/except` amplo. Qualquer exceção não prevista acima faz rollback dos chunks daquele documento, marca-o como `failed` com a mensagem genérica "erro inesperado ao processar o arquivo", registra o erro completo no log, e o worker segue para o próximo documento. O que escapa a esse tratamento são as mortes do processo, cobertas pelo limite de tentativas da seção 5.2.

### 5.4 Dimensionamento

O cenário máximo da spec (100 documentos de 50 páginas, cerca de 5 mil páginas de artigo científico) gera algo entre 10 e 15 mil trechos. Com o bge-m3 em CPU e sequências de ~500 tokens, a indexação inicial desse volume pode levar **horas**. No uso real isso se dilui, porque ela adiciona documentos aos poucos, mas a expectativa precisa ser calibrada com dados reais: uma das primeiras tarefas da implementação é medir o tempo de indexação de 5 documentos típicos e extrapolar.

### 5.5 Saúde do worker

O worker grava `last_seen_at` na tabela `worker_heartbeat` a cada 10 segundos, inclusive quando está ocioso, numa thread própria para não depender do andamento de um documento longo. O `GET /health` informa o worker como parado se o último heartbeat tiver mais de 60 segundos. O front consulta o `/health` periodicamente enquanto houver documentos `pending` ou `processing`, e mostra um aviso ("o processamento de documentos está parado") em vez de deixar os documentos "aguardando" para sempre sem explicação. No Compose, o worker tem `restart: unless-stopped` (seção 11), então na maioria dos casos ele volta sozinho e o aviso desaparece.

## 6. Pipeline de consulta

A pergunta chega por `POST /conversations/{id}/messages` e a resposta volta por SSE. O fluxo tem seis etapas:

1. **Salvar e reescrever.** A mensagem da usuária é salva imediatamente (CA12). Se a conversa já tem trocas anteriores, o modelo pequeno reescreve a pergunta como uma pergunta independente usando o histórico preparado (seção 6.1), e a versão reescrita fica registrada em `rewritten_query` (CA11).
2. **Buscar.** A pergunta (reescrita ou original) é convertida em embedding e o banco busca os 8 trechos mais similares, considerando apenas documentos com status `ready` e sem `deleted_at` (CA05, CA09).
3. **Filtrar por relevância.** Trechos com similaridade abaixo de `MIN_SIMILARITY` são descartados. Se nenhum sobrar, o sistema responde diretamente que não encontrou informação suficiente nos documentos, sem chamar a LLM (CA08). Essa resposta é salva como mensagem da assistente com status `complete` e sem citações, e entra no histórico normalmente, porque é um contexto útil e inofensivo para as perguntas seguintes.
4. **Montar o prompt.** Instruções em português, os trechos restantes numerados a partir de [1] com arquivo e página, o histórico preparado numa seção claramente delimitada, e a pergunta. As instruções estão na seção 6.2.
5. **Gerar.** A resposta do modelo principal é transmitida token a token. O modelo começa como `llama-3.3-70b-versatile`, e o `openai/gpt-oss-120b` será comparado nos testes para ver qual escreve melhor em português.
6. **Salvar citações.** Ao final, o back-end extrai os marcadores da resposta (seção 6.4) e salva a mensagem da assistente com uma citação por marcador válido, copiando o trecho e o nome do arquivo (CA07, CA12).

### 6.1 Preparação do histórico

As últimas `HISTORY_TURNS` trocas da conversa entram no prompt de reescrita e no prompt de resposta, mas nunca com os marcadores originais. Um [3] da resposta anterior apontava para outro trecho, e o modelo poderia reaproveitar o número e gerar uma citação errada (CA07). Por isso, antes de montar o prompt:

- Cada marcador [n] das respostas anteriores é substituído pela referência textual correspondente, no formato "(arquivo, p. X)", usando a tabela `citations`.
- Respostas anteriores que citam algum documento removido são **omitidas** do histórico (a pergunta correspondente é mantida). Isso impede que conteúdo de um documento removido volte a aparecer numa resposta nova (CA05).
- Respostas com status `error` não entram no histórico.

### 6.2 Instruções do prompt

As instruções do sistema, em português, determinam que o modelo:

- Responda apenas com base nos trechos numerados desta pergunta (CA06).
- Cite cada afirmação com o marcador [n] do trecho de onde ela veio (CA07).
- Use o histórico **apenas** para entender a que a pergunta se refere, nunca como fonte de informação: afirmações que aparecem só no histórico e não nos trechos atuais não podem ser repetidas.
- Nunca use o formato "(arquivo, p. X)" do histórico para citar; a única forma válida de citação é [n].
- Responda em português do Brasil, mesmo quando os trechos estiverem em outro idioma (CA09).
- Diga explicitamente quando os trechos não forem suficientes para responder (CA08).

O conjunto de avaliação (seção 12) inclui perguntas de acompanhamento para verificar se o modelo respeita essas regras em relação ao histórico.

### 6.3 Busca e similaridade

A busca é **exata, sem índice vetorial**. Com 10 a 15 mil vetores de 1024 dimensões, uma varredura completa leva poucos milissegundos, e evita um problema do HNSW: o filtro `status = 'ready' AND deleted_at IS NULL` é aplicado depois de percorrer o índice, o que pode devolver menos de 8 trechos quando há documentos removidos. Se o volume crescer muito no futuro, a alternativa é o HNSW com `hnsw.iterative_scan` ativado (pgvector 0.8 ou superior).

O operador `<=>` do pgvector devolve **distância** de cosseno. A similaridade usada em todo o sistema é `1 - distância`.

**Calibração do limiar:** perguntas em português contra textos em inglês tendem a ter similaridade menor do que perguntas no mesmo idioma. Um limiar alto demais barraria respostas válidas (prejudicando o CA09) na tentativa de atender o CA08. Por isso `MIN_SIMILARITY` não tem valor fixo definido neste plano: ele é calibrado com o conjunto de avaliação (seção 12), que inclui perguntas cross-lingual de propósito. O critério de calibração é começar baixo, priorizando o CA09, e subir só enquanto nenhuma pergunta válida for barrada.

### 6.4 Extração de marcadores

O parser reconhece `[1]`, listas como `[1, 3]` e intervalos como `[1-3]` e `[1–3]`. Números fora do intervalo de trechos enviados no prompt (por exemplo, `[9]` quando só havia 6 trechos) são ignorados. Uma resposta sem nenhum marcador válido é salva normalmente, sem citações.

### 6.5 Eventos SSE

| Evento | Conteúdo |
|---|---|
| `sources` | Enviado primeiro, com os trechos que entraram no prompt, para o front já poder montar as citações |
| `token` | Pedaços do texto da resposta |
| `done` | Id da mensagem salva e marcadores efetivamente citados |
| `error` | Mensagem amigável (por exemplo, limite do Groq atingido) |

### 6.6 Falhas no streaming

A pergunta da usuária já está salva antes da geração começar. Se o Groq der erro no meio da resposta, ou se o navegador desconectar (detectado com `request.is_disconnected()`, o que também cancela a chamada ao Groq), a resposta parcial é **descartada** e uma mensagem da assistente é salva com status `error` e sem conteúdo. Assim a conversa salva mostra "resposta não concluída" no lugar certo, a pergunta não fica órfã, e nenhuma resposta incompleta sem citações é apresentada como se fosse válida. Mensagens com status `error` não entram no histórico enviado à LLM.

**Gravação protegida:** quando o cliente desconecta, o Starlette cancela o gerador do streaming, e um `await` de banco no bloco `finally` pode ser cancelado junto, fazendo a mensagem de erro nunca ser salva. Por isso essa gravação é feita dentro de `asyncio.shield`, ou numa sessão síncrona executada em thread, de forma que o cancelamento não a interrompa.

### 6.7 Orçamento de tokens

Cada pergunta consome cerca de 6 mil tokens no modelo principal (4 mil de trechos, 1,5 mil de histórico e 500 de instruções), mais uma chamada pequena ao modelo de reescrita quando há histórico. Com os limites do plano gratuito do Groq para o `llama-3.3-70b-versatile` (na ordem de 100 mil tokens por dia e 12 mil por minuto, a confirmar no console do Groq antes da implementação), isso dá cerca de **15 perguntas por dia e 2 por minuto**.

Isso é pouco para um dia de escrita intensa. As mitigações são: ativar o tier Developer (segundo as fontes consultadas, limites cerca de 10 vezes maiores e custo baixo para o volume de uma usuária, ambos a confirmar no console do Groq); reduzir `TOP_K`, `CHUNK_SIZE` ou `HISTORY_TURNS`; e o próprio filtro de relevância, que tira trechos fracos do prompt. Quando o limite é atingido, o front mostra uma mensagem clara em vez de um erro genérico.

### 6.8 Título da conversa

Depois da primeira resposta, o modelo pequeno gera um título de até 6 palavras. Se a chamada falhar, o título vira a primeira pergunta truncada.

## 7. Ciclo de vida das conversas

O front **nunca retoma uma conversa**. O id da conversa atual existe apenas na memória da aplicação React, sem localStorage, sessionStorage ou parâmetro de URL.

- **Ao carregar o front,** ele chama `POST /conversations/close-open`, que fecha todas as conversas abertas. Isso implementa o "fechar o sistema" do CA13 sem depender de detectar o fechamento do navegador.
- **Ao enviar a primeira mensagem de uma sessão,** o front cria uma conversa com `POST /conversations`, que também fecha qualquer outra aberta.
- **Ao clicar em "Nova conversa",** o front descarta o id atual; a próxima mensagem cria uma conversa nova, fechando a anterior.
- **Mensagens enviadas para uma conversa fechada** recebem erro 409.
- **Conversas sem nenhuma mensagem** não aparecem na lista.

**Decisão consciente:** recarregar a página (F5) conta como "fechar o sistema". A conversa em andamento vira somente leitura e ela começa uma nova. Isso é aceitável, porque nada é perdido: a conversa continua disponível na lista.

**Várias abas:** abrir o sistema numa segunda aba chama o `close-open` e fecha a conversa da primeira. A próxima pergunta na primeira aba recebe 409. O front trata esse 409 especificamente, mostrando "Esta conversa foi encerrada, provavelmente porque o sistema foi aberto em outra aba. Comece uma nova conversa." com um botão para isso, e mantém a pergunta digitada no campo para ela não perder o texto.

## 8. Contrato da API

| Endpoint | Função | CAs |
|---|---|---|
| `POST /documents` | Upload multipart de um ou vários PDFs; retorna o resultado por arquivo (novo, duplicado, reativado, reprocessado ou recusado) | 01, 02, 03, 04, 17 |
| `GET /documents` | Lista os documentos ativos com status, mensagem de erro e posição na fila | 01, 02, 03 |
| `GET /documents/{id}` | Status e posição na fila de um documento (usado no polling) | 02 |
| `GET /documents/{id}/file` | Serve o PDF, apenas para documentos ativos | 07 |
| `DELETE /documents/{id}` | Soft delete | 05 |
| `POST /conversations` | Cria conversa e fecha as abertas | 13 |
| `POST /conversations/close-open` | Fecha todas as conversas abertas (chamado ao carregar o front) | 13 |
| `GET /conversations` | Lista conversas com data e título | 14 |
| `GET /conversations/{id}` | Conversa completa, com citações, status das mensagens e flag de documento removido | 14, 16 |
| `DELETE /conversations/{id}` | Exclusão definitiva, em cascata | 15 |
| `POST /conversations/{id}/messages` | Envia pergunta e recebe a resposta por SSE | 06, 07, 08, 09, 11, 12 |
| `GET /health` | Estado do banco, do modelo de embedding da `api` e do worker (pelo heartbeat) | — |

**Posição na fila:** para documentos `pending`, a posição é calculada na consulta como o número de documentos `pending`, não removidos, criados antes dele, mais um. Para os demais status, o campo vem nulo.

O contrato detalhado, com os schemas de entrada e saída, fica definido nos modelos Pydantic, e o FastAPI publica tudo automaticamente em `/docs`.

## 9. Front-end

A tela tem uma barra lateral com duas seções, **Documentos** e **Conversas**, e a área principal com o chat.

Na seção de documentos, o componente de upload aceita arrastar vários arquivos e mostra o resultado e o status de cada um, consultando `GET /documents/{id}` a cada 2 segundos até o documento ficar `ready` ou `failed` (CA02, CA03). Documentos na fila mostram a posição ("aguardando, 3º na fila"), já que a indexação pode demorar. Se o `/health` indicar o worker parado, a seção mostra o aviso da seção 5.5. Cada item da lista tem a opção de remover.

No chat, a resposta aparece sendo escrita conforme os eventos `token` chegam. Os marcadores [n] viram elementos clicáveis que abrem um painel com o trecho original, o arquivo e a página, e um botão que abre o PDF naquela página no visualizador (CA07). O 409 de conversa encerrada é tratado como descrito na seção 7.

Conversas antigas abrem numa visualização somente leitura, sem campo de pergunta. Citações de documentos removidos mostram o trecho com um aviso e sem o botão de abrir o PDF (CA16). Respostas com status `error` aparecem como "resposta não concluída".

## 10. Configuração

Variáveis do `.env`:

| Variável | Uso |
|---|---|
| `GROQ_API_KEY` | Chave da API do Groq |
| `LLM_ANSWER_MODEL` | Modelo que gera as respostas (padrão `llama-3.3-70b-versatile`) |
| `LLM_REWRITE_MODEL` | Modelo que reescreve perguntas e gera títulos (padrão `llama-3.1-8b-instant`) |
| `EMBEDDING_MODEL` | Modelo de embedding (padrão `BAAI/bge-m3`) |
| `TOP_K` | Número de trechos recuperados por pergunta |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | Tamanho e sobreposição dos trechos, em tokens |
| `MIN_SIMILARITY` | Limiar de similaridade (calibrado, seção 6.3; padrão provisório 0,3) |
| `HISTORY_TURNS` | Trocas anteriores enviadas à LLM (padrão 3, cerca de 1,5 mil tokens, seção 6.7) |
| `MAX_ATTEMPTS` | Tentativas de processamento antes de marcar `failed` (padrão 3) |
| `MAX_UPLOAD_MB` | Tamanho máximo por arquivo (padrão 50) |
| `API_TORCH_THREADS` / `WORKER_TORCH_THREADS` | Threads do PyTorch em cada processo (padrão 2 e 4) |
| `DATABASE_URL` | Conexão com o Postgres |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Credenciais do container `db`; devem bater com o `DATABASE_URL` |
| `DATA_DIR` | Diretório dos PDFs |

Cada processo também define `OMP_NUM_THREADS` e `MKL_NUM_THREADS` com o mesmo valor de suas threads do PyTorch, e `TOKENIZERS_PARALLELISM=false`, porque o tokenizador do Hugging Face cria threads próprias que escapariam ao limite.

A camada de LLM é uma interface `LLMProvider` com dois métodos, `complete` e `stream`. A implementação do Groq é a única no MVP, e os testes usam uma implementação falsa com respostas fixas.

## 11. Docker Compose

- **`db`:** imagem `pgvector/pgvector:pg16` com volume próprio, healthcheck com `pg_isready` e `restart: unless-stopped`.
- **`migrate`:** mesma imagem do back-end, roda `alembic upgrade head` e termina. Depende do `db` com `condition: service_healthy`.
- **`api`:** depende do `migrate` com `condition: service_completed_successfully`. Sobe o uvicorn com **um único worker** (`--workers 1`), para não duplicar o modelo em memória. Monta os volumes de PDFs e do cache do Hugging Face. `restart: unless-stopped`.
- **`worker`:** mesma imagem, outro entrypoint, executado com `nice -n 10` para ceder a vez à `api` quando houver disputa. Depende do `migrate` com `condition: service_completed_successfully`, monta os mesmos volumes e tem `restart: unless-stopped`.
- **`frontend`:** servidor do Vite em desenvolvimento; numa versão de produção, Nginx servindo o build com proxy de `/api` para o back-end. Nos dois casos o proxy remove o prefixo (`/api/health` → `/health`), mantendo as rotas da seção 8.

O `db` publica a porta 5432 em `127.0.0.1` para os testes de integração rodarem de fora do Compose (seção 12).

**Divisão de CPU:** o processador de referência (Ryzen 5 5600G) tem 6 núcleos físicos e 12 threads lógicas, e em multiplicação de matrizes o hyperthreading rende pouco, então a divisão é pensada em núcleos físicos. O ponto de partida é 4 threads para o worker e 2 para a `api`. Como o limite de threads não isola nada por si só (quem escala os processos é o sistema operacional), o worker também recebe `cpus: "4"` no Compose, garantindo que nunca ocupe mais do que o equivalente a 4 núcleos, e a prioridade reduzida com `nice`. O `cpuset` isolaria núcleos específicos, mas só vale a pena num Linux nativo, depois de conferir com `lscpu` quais CPUs lógicas pertencem a cada núcleo; no Docker Desktop as CPUs são da VM, e o `cpuset` não corresponde aos núcleos físicos. Na prática o risco é menor do que parece, porque o embedding de uma pergunta curta é leve, mas os números são ajustados com o teste de latência (seção 12).

**Memória:** os dois processos com bge-m3 somam cerca de 4 a 5 GB. Se ela usar Docker Desktop, é preciso conferir o limite de memória configurado para a VM do Docker (no Windows com WSL2, o padrão costuma ser uma fração da RAM total), que deve ser de pelo menos 8 GB.

Todas as portas são publicadas apenas em `127.0.0.1`, para que nada fique acessível pela rede.

## 12. Estratégia de testes

**Testes unitários** cobrem o chunking (trechos nunca cruzam páginas, tamanho e sobreposição corretos, páginas numeradas a partir de 1), as verificações de arquivo da seção 5.3 (corrompido, protegido por senha, sem texto), a tabela de regras de upload da seção 5.1 (um caso por linha), a preparação do histórico (substituição de marcadores e omissão de respostas com documentos removidos) e o parser de marcadores, incluindo listas, intervalos e números inexistentes.

**Testes de integração** rodam contra um Postgres real subido pelo Compose, com o provedor de LLM falso. Eles cobrem:

- Upload, remoção, reenvio e reprocessamento de `failed`.
- Duplicados na mesma requisição e uploads concorrentes do mesmo arquivo.
- Fila com `SKIP LOCKED`, recuperação após reinício e o limite de tentativas: um documento em `processing` com `attempts` no limite vira `failed` na recuperação.
- Exceção inesperada no processamento de um documento: ele vira `failed` e o worker processa o seguinte.
- Heartbeat e o estado do worker no `/health`.
- Criação e fechamento de conversas, incluindo `close-open` e o 409.
- Resposta "não encontrei" salva como `complete` e presente no histórico.
- Salvamento de citações com cópia do trecho.
- Falhas no streaming: erro do provedor e desconexão do cliente, verificando que a mensagem com status `error` é de fato gravada.

Isso valida de forma automática os CAs 01 a 05, 10 e 12 a 17.

**Conjunto de avaliação** com 10 a 15 perguntas reais sobre os artigos dela, cada uma com o documento e a página esperados, incluindo de propósito perguntas em português sobre artigos em inglês, algumas perguntas sem resposta nos documentos, e sequências de acompanhamento para verificar as regras do histórico (seção 6.2). Ele mede se a busca encontra os trechos certos (CA09) e serve para calibrar `MIN_SIMILARITY` e `TOP_K` equilibrando CA08 e CA09. Os CAs que dependem do comportamento da LLM real (06, 07, 08 e 11) são validados manualmente com esse mesmo conjunto, na coluna "Em revisão".

**Teste de latência** mede o tempo entre o envio da pergunta e o fim da resposta, em dois cenários: sistema ocioso e worker indexando um lote de documentos. O critério é ficar em até ~15 segundos nos dois casos (RNF). Se o cenário com indexação estourar, o ajuste é redistribuir threads e o limite de `cpus` da seção 11.

**Teste de dimensionamento** mede o tempo de indexação de 5 documentos típicos, logo no começo da implementação, para extrapolar o tempo do cenário de 100 documentos e alinhar a expectativa com ela.

## 13. Decisões registradas

- **Dados enviados ao Groq:** as perguntas, o histórico preparado e os trechos recuperados dos documentos são enviados à API do Groq a cada pergunta. Os documentos inteiros nunca saem da máquina. O requisito de não expor dados publicamente é atendido (nada fica acessível pela rede e o Groq não publica os dados), mas os trechos saem do computador dela. Para artigos publicados isso é de baixo risco; se ela subir anotações pessoais ou dados não publicados, vale saber disso e consultar a política de dados do Groq.
- **F5 fecha a conversa, e uma segunda aba fecha a da primeira:** ver seção 7.
- **Resposta parcial descartada em caso de falha:** ver seção 6.6.
- **Reenvio de documento `failed` reprocessa e zera as tentativas:** ver seção 5.1.
- **Limite de 3 tentativas por documento:** ver seção 5.2.
- **Resposta "não encontrei" é salva e entra no histórico:** ver seção 6, etapa 3.
- **Busca exata sem índice vetorial no MVP:** ver seção 6.3.

## 14. Riscos

| Risco | Mitigação |
|---|---|
| Limites do plano gratuito do Groq (~15 perguntas/dia no modelo principal) | Tier Developer, parâmetros configuráveis, mensagem clara ao atingir o limite |
| Indexação inicial de um volume grande leva horas | Fila persistente com posição visível; medição logo no início (seção 12) |
| Arquivo que derruba o processo do worker | Limite de tentativas (5.2), limite de tamanho de upload (5.1), worker isolado da `api` |
| Worker parado sem ninguém perceber | Heartbeat, aviso no front e `restart: unless-stopped` (5.5, 11) |
| Disputa de CPU entre ingestão e perguntas | Worker em processo separado, `cpus` limitado, `nice` e threads coerentes; teste de latência |
| Limiar de similaridade barrando perguntas cross-lingual | Calibração com conjunto de avaliação cross-lingual |
| Modelo usando o histórico como fonte ou citando fora do formato [n] | Instruções explícitas (6.2) e perguntas de acompanhamento no conjunto de avaliação |
| Artigos com duas colunas, cabeçalhos e rodapés geram trechos com texto misturado | Inspecionar os primeiros documentos processados |
| Seção de referências bibliográficas polui a busca | Filtrá-la como melhoria, se aparecer nos testes |
| Limite de memória do Docker Desktop menor que o necessário | Conferir e ajustar a configuração da VM (seção 11) |

## 15. Rastreabilidade

| Requisito | Onde é atendido |
|---|---|
| CA01 | Regras de upload e processamento (5.1, 5.3), `POST /documents`, `GET /documents` |
| CA02 | Upload múltiplo, polling de status e posição na fila (seções 8 e 9) |
| CA03 | Verificações de arquivo (5.3), captura de exceções e limite de tentativas (5.2, 5.3), reprocessamento de `failed` (5.1) |
| CA04 | Regras de upload por hash, duplicados na mesma requisição e concorrentes (5.1) |
| CA05 | Soft delete, filtro na busca (6.3) e omissão no histórico (6.1) |
| CA06 | Instruções do prompt (6.2) |
| CA07 | Marcadores [n], parser (6.4), histórico sem marcadores (6.1), instruções (6.2), painel de trecho e visualizador (9) |
| CA08 | Filtro de relevância (6, etapa 3), calibração (6.3) e instruções do prompt (6.2) |
| CA09 | bge-m3 multilíngue, calibração cross-lingual (6.3) e instrução de idioma (6.2) |
| CA10 | Persistência em Postgres e volumes; fila no banco (5.2) |
| CA11 | Reescrita de pergunta com histórico preparado (6, etapa 1; 6.1) |
| CA12 | Salvamento imediato de mensagens e citações (6); falhas no streaming com gravação protegida (6.6) |
| CA13 | Ciclo de vida das conversas, `close-open` e tratamento do 409 (seção 7) |
| CA14 | `GET /conversations` e `GET /conversations/{id}` |
| CA15 | `DELETE /conversations/{id}` |
| CA16 | Cópia do trecho e flag de documento removido (seções 4 e 9) |
| CA17 | Reativação por hash considerando status (5.1) |
| RNF: back-end em Python, uma usuária | Stack (2); uvicorn com um worker (11) |
| RNF: 100 documentos de 50 páginas | Dimensionamento (5.4); busca exata (6.3); teste de dimensionamento (12) |
| RNF: resposta em até ~15 s | Worker separado, `cpus`, `nice` e divisão de threads (1, 10, 11); teste de latência (12) |
| RNF: dados não expostos publicamente | Bind em 127.0.0.1 (11); PDFs salvos por hash (4); decisão sobre o Groq (13) |
