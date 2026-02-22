from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from src.retrieval.bm25 import BM25Retriever
from src.protocols.loader import load_and_chunk_protocols
from src.core.config import settings
from src.api.routes import router


app = FastAPI(title="Medical Diagnosis Assistant")
app.include_router(router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

retriever: BM25Retriever | None = None


@app.on_event("startup")
def startup():
    global retriever
    chunks = load_and_chunk_protocols(settings.protocols_path)
    app.state.retriever = BM25Retriever(chunks)
    print(f"✅ Loaded chunks: {len(chunks)}")