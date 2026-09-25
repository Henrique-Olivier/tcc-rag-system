import logging
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from transformers import PreTrainedTokenizerBase

BATCH_SIZE = 16


class Embedder:
    """bge-m3 em CPU. `num_threads` vem de API_TORCH_THREADS ou WORKER_TORCH_THREADS (seção 10)."""

    def __init__(self, model_name: str, num_threads: int) -> None:
        # Import tardio: torch leva dezenas de segundos para importar e só quem carrega o modelo precisa dele.
        import torch
        from sentence_transformers import SentenceTransformer

        # Vale para o processo inteiro; por isso api e worker são processos separados (seção 1).
        torch.set_num_threads(num_threads)
        self._model = SentenceTransformer(model_name, device="cpu")

    @property
    def tokenizer(self) -> "PreTrainedTokenizerBase":
        """Tokenizador do próprio modelo, usado para contar tokens no chunking (seção 5.3)."""
        return self._model.tokenizer

    def encode(self, texts: list[str]) -> list[list[float]]:
        """Vetores normalizados: similaridade de cosseno = produto interno."""
        vectors = self._model.encode(texts, batch_size=BATCH_SIZE, normalize_embeddings=True, convert_to_numpy=True)
        return vectors.tolist()


class EmbedderLoader:
    """Carrega o Embedder numa thread, para a api responder o /health enquanto o modelo sobe."""

    def __init__(self) -> None:
        self.embedder: Embedder | None = None
        self.failed = False

    @property
    def status(self) -> str:
        return "ready" if self.embedder else "failed" if self.failed else "loading"

    def load_in_background(self, model_name: str, num_threads: int) -> None:
        def load() -> None:
            try:
                self.embedder = Embedder(model_name, num_threads)
            except Exception:
                logging.getLogger("api").exception("falha ao carregar o modelo de embedding")
                self.failed = True

        threading.Thread(target=load, name="embedder-loader", daemon=True).start()
