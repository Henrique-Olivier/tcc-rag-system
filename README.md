# RAG TCC

Assistente de pesquisa para TCC: responde perguntas em português com base apenas nos PDFs enviados, citando arquivo e página. Especificação e plano em `specs/001-mvp-rag/`.

## Subir o ambiente

Requisitos: Docker Desktop (com pelo menos 8 GB de memória para a VM, ver plano seção 11).

```sh
cp .env.example .env   # preencha GROQ_API_KEY e troque a senha do Postgres
docker compose up -d --build
```

- Front-end: http://127.0.0.1:5173
- API: http://127.0.0.1:8000/health (documentação em `/docs`)

O serviço `migrate` aplica as migrações e termina; `api` e `worker` só sobem depois dele.

## Testes

Back-end (requer [uv](https://docs.astral.sh/uv/)):

```sh
cd backend
uv sync
uv run pytest
```

Front-end:

```sh
cd frontend
npm install
npm run build
```
