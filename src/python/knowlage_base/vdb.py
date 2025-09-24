from langchain_community.vectorstores import FAISS
import os , pickle
from langchain.schema import Document

DATA_DIR = "data_store"
FAISS_DIR = os.path.join(DATA_DIR, "faiss_index")
METADATA_FILE = os.path.join(DATA_DIR, "metadata.pkl")

def csv_to_document(csv_path: str) -> Document:
    with open(csv_path, "r", encoding="utf-8") as f:
        csv_text = f.read()
    metadata = {"source": csv_path, "type": "csv"}
    return Document(page_content=csv_text, metadata=metadata)

def json_to_document(json_path: str) -> Document:
    with open(json_path, "r", encoding="utf-8") as f:
        json_text = f.read()
    metadata = {"source": json_path, "type": "json"}
    return Document(page_content=json_text, metadata=metadata)

def text_to_document(text_path: str) -> Document:
    with open(text_path, "r", encoding="utf-8") as f:
        text_content = f.read()
    metadata = {"source": text_path, "type": "text"}
    return Document(page_content=text_content, metadata=metadata)

def pdf_to_document(pdf_path: str) -> Document:
    with open(pdf_path, "rb") as f:
        pdf_content = f.read()
    metadata = {"source": pdf_path, "type": "pdf"}
    return Document(page_content=pdf_content, metadata=metadata)

def docx_to_document(docx_path: str) -> Document:
    with open(docx_path, "rb") as f:
        docx_content = f.read()
    metadata = {"source": docx_path, "type": "docx"}
    return Document(page_content=docx_content, metadata=metadata)

def load_or_create_vectorstore(embeddings):
    # try load FAISS index
    try:
        db = FAISS.load_local(FAISS_DIR, embeddings)
        print("Loaded FAISS index")
        return db
    except Exception:
        # create empty FAISS with no docs
        empty_docs = []
        db = FAISS.from_documents(empty_docs, embeddings)
        db.save_local(FAISS_DIR)
        print("Created new FAISS index")
        return db

# metadata format: mapping id->metadata (we persist separately)
def load_metadata_map():
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, "rb") as f:
            return pickle.load(f)
    return {}

def save_metadata_map(m):
    with open(METADATA_FILE, "wb") as f:
        pickle.dump(m, f)
