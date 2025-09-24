import os

DATA_DIR = "data_store"
FAISS_DIR = os.path.join(DATA_DIR, "faiss_index")
METADATA_FILE = os.path.join(DATA_DIR, "metadata.pkl")

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150

LLAMA3_API_URL = os.environ.get(
    "LLAMA3_API_URL",
    "http://127.0.0.1:8080/generate"
)

os.makedirs(DATA_DIR, exist_ok=True)
