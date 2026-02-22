import re
from rank_bm25 import BM25Okapi

_TOKEN_RE = re.compile(r"[а-яА-Яa-zA-Z0-9]+")

def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


class BM25Retriever:
    def __init__(self, chunks: list[dict]):
        self.chunks = chunks
        # Pretokenize once (важно для скорости)
        self.corpus_tokens = [tokenize(c["chunk_text"]) for c in chunks]
        self.bm25 = BM25Okapi(self.corpus_tokens)

    def search(self, query: str, k: int = 8) -> list[dict]:
        q = tokenize(query)
        scores = self.bm25.get_scores(q)
        top_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        return [self.chunks[i] for i in top_idx]