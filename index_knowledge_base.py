import os
import fitz  # PyMuPDF
import faiss
import pickle
import numpy as np
from openai import OpenAI
from dotenv import load_dotenv
from tqdm import tqdm

# Load API key
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Constants
DOCS_PATH = "knowledge_base"
INDEX_PATH = "vector_index"
EMBEDDING_MODEL = "text-embedding-ada-002"
CHUNK_SIZE = 700
CHUNK_OVERLAP = 100

def load_pdf_text(filepath):
    text = ""
    try:
        doc = fitz.open(filepath)
        for page in doc:
            text += page.get_text()
        return text
    except Exception as e:
        print(f"❌ Error reading {filepath}: {e}")
        return ""

def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk.strip())
        start += chunk_size - overlap
    return chunks

def load_documents():
    all_chunks = []
    sources = []
    for filename in os.listdir(DOCS_PATH):
        filepath = os.path.join(DOCS_PATH, filename)
        if filename.endswith(".txt"):
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read()
        elif filename.endswith(".pdf"):
            text = load_pdf_text(filepath)
        else:
            continue

        chunks = chunk_text(text)
        all_chunks.extend(chunks)
        sources.extend([filename] * len(chunks))

    return all_chunks, sources

def embed_chunks(chunks):
    embeddings = []
    print("📡 Generating embeddings...")
    for i in tqdm(range(0, len(chunks), 100)):
        batch = chunks[i:i+100]
        response = client.embeddings.create(
            input=batch,
            model=EMBEDDING_MODEL
        )
        batch_embeddings = [item.embedding for item in response.data]
        embeddings.extend(batch_embeddings)
    return embeddings

def save_index(embeddings, sources):
    dim = len(embeddings[0])
    index = faiss.IndexFlatL2(dim)
    index.add(np.array(embeddings).astype("float32"))

    if not os.path.exists(INDEX_PATH):
        os.makedirs(INDEX_PATH)

    faiss.write_index(index, os.path.join(INDEX_PATH, "index.faiss"))
    with open(os.path.join(INDEX_PATH, "sources.pkl"), "wb") as f:
        pickle.dump(sources, f)

    print("✅ Index and sources saved to disk.")

def build_index():
    print("🔍 Loading and chunking documents...")
    chunks, sources = load_documents()

    print(f"📄 Total chunks: {len(chunks)}")
    embeddings = embed_chunks(chunks)

    print("💾 Saving index...")
    save_index(embeddings, sources)

if __name__ == "__main__":
    build_index()
