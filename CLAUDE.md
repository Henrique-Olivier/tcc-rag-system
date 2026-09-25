# RAG TCC — contexto do projeto

## O que é

Assistente de pesquisa para o TCC de uma estudante de Medicina Veterinária. Ela sobe os PDFs da pesquisa (artigos científicos, muitos em inglês) e faz perguntas em português. O sistema responde **apenas** com base nesses documentos, sempre citando arquivo e página, porque num TCC toda afirmação precisa ser referenciada e verificável. É um sistema pessoal: uma única usuária, rodando localmente.

## Metodologia: Spec-Driven Development (SDD)

O projeto segue SDD. Cada funcionalidade tem uma pasta em `specs/` com três artefatos, nesta ordem:

1. `spec.md`: o quê e por quê (user story, escopo, critérios de aceite CA01, CA02...). Não fala de tecnologia.
2. `plan.md`: como (arquitetura, modelo de dados, contrato da API, testes). Cada decisão aponta os CAs que atende, e há uma tabela de rastreabilidade no final.
3. `tasks.md`: o plano quebrado em tarefas pequenas, ordenadas por dependência, cada uma ligada aos CAs e às seções do plano.

Regras:

- A spec e o plano são a fonte da verdade. Não implemente nada que não esteja neles. Se algo estiver ambíguo, contraditório ou faltando, pare e pergunte em vez de decidir sozinho.
- Se durante a implementação uma decisão do plano se mostrar errada, proponha a mudança no `plan.md` (com uma linha nova no histórico de revisões) antes de mudar o código.
- Cada tarefa só é considerada pronta quando os testes dos CAs que ela cobre passam.

Estado atual: `specs/001-mvp-rag/spec.md` e `plan.md` (v8) estão aprovados. O `tasks.md` existe (T00 a T28); o scaffolding (T00) está feito e a implementação começa pela T01.

## Decisões principais (detalhes no plan.md)

- **Monorepo** com Docker Compose: `db` (Postgres + pgvector, também usado como fila de ingestão), `migrate` (Alembic, execução única), `api` (FastAPI), `worker` (ingestão, processo separado), `frontend` (React).
- **Back-end:** Python 3.12, FastAPI, SQLAlchemy 2, Alembic, psycopg 3, PyMuPDF, sentence-transformers.
- **Embedding:** `BAAI/bge-m3`, local, em CPU (multilíngue, essencial para pergunta em português sobre artigo em inglês).
- **LLM:** Groq, via SDK da OpenAI (API compatível), atrás de uma interface `LLMProvider`. `openai/gpt-oss-120b` para respostas, `openai/gpt-oss-20b` para reescrita de perguntas e títulos (plano v6).
- **Front-end:** React + Vite + TypeScript, TanStack Query, react-pdf, `@microsoft/fetch-event-source` para SSE, React Router e shadcn/ui (Tailwind) para os componentes.
- **Conversas:** salvas automaticamente, mensagem a mensagem; depois de encerradas ficam somente leitura. Não é possível retomar uma conversa.
- **Documentos:** soft delete; reenvio de documento removido reativa sem reprocessar.

## Ambiente de desenvolvimento

- Ryzen 5 5600G (6 núcleos / 12 threads), 16 GB de RAM, GPU AMD RX 580 **não usada** (sem CUDA; o ROCm não suporta essa placa). Tudo roda em CPU.
- O PyTorch deve ser instalado na versão **somente CPU**, para a imagem Docker não baixar as bibliotecas CUDA.
- O desenvolvedor tem bastante experiência com React.

## Convenções

- Código, nomes de arquivos, identificadores e commits em inglês.
- Documentação em `specs/`, textos da interface e mensagens para a usuária em português do Brasil.
- Os módulos `ingestion`, `retrieval`, `llm` e `chat` não importam nada do FastAPI; rotas e worker apenas os chamam.
- Portas publicadas apenas em `127.0.0.1`.
- Segredos só no `.env` (nunca commitado); `.env.example` documenta todas as variáveis.

## Gestão do trabalho

Quadro no Trello: https://trello.com/b/kiVC5tnp/projeto-rag-tcc
Listas: Specs, Backlog, A fazer, Fazendo, Em revisão, Feito. A Spec 001 está no card https://trello.com/c/KKeHxpKj, com os 17 CAs em checklist. As tarefas do `tasks.md` virarão cards no Backlog. O repositório é a fonte da verdade; o Trello só acompanha o andamento.
