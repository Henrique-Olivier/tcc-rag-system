"""Montagem do prompt de resposta (plano, seção 6, etapa 4, e seção 6.2)."""

from app.chat.history import HistoryTurn
from app.llm.provider import ChatMessage
from app.retrieval.search import RetrievedChunk

ANSWER_INSTRUCTIONS = """\
Você é um assistente de pesquisa que ajuda uma estudante de Medicina Veterinária a escrever o TCC.

Regras obrigatórias:
- Responda apenas com base nos trechos numerados em <trechos>. Não complete com conhecimento próprio ou externo.
- Cite cada afirmação com o marcador do trecho de onde ela veio, no formato [n] com colchetes simples, por exemplo [1] ou [2, 3]. \
Não use outros tipos de colchete, como 【1】.
- A única forma válida de citação é [n]. Nunca use o formato "(arquivo, p. X)" que aparece no histórico.
- O histórico em <historico> serve apenas para entender a que a pergunta se refere. Não use o histórico como fonte: \
afirmações que aparecem só no histórico e não nos trechos atuais não podem ser repetidas.
- Responda em português do Brasil, mesmo quando os trechos estiverem em outro idioma.
- Se os trechos não forem suficientes para responder, diga isso explicitamente em vez de supor ou inventar."""


def format_history(history: list[HistoryTurn]) -> str:
    lines: list[str] = []
    for turn in history:
        lines.append(f"Pergunta: {turn.question}")
        if turn.answer is not None:
            lines.append(f"Resposta: {turn.answer}")
    return "\n".join(lines)


def build_answer_messages(question: str, sources: list[RetrievedChunk], history: list[HistoryTurn]) -> list[ChatMessage]:
    """Trechos numerados a partir de [1] na ordem recebida; o número é o marcador que a resposta usa."""
    parts = ["<trechos>"]
    for number, source in enumerate(sources, start=1):
        parts.append(f"[{number}] ({source.filename}, p. {source.page_number})\n{source.content}\n")
    parts.append("</trechos>")
    if history:
        parts.append(f"\n<historico>\n{format_history(history)}\n</historico>")
    parts.append(f"\nPergunta: {question}")
    return [{"role": "system", "content": ANSWER_INSTRUCTIONS}, {"role": "user", "content": "\n".join(parts)}]
