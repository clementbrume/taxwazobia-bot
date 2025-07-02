# retriever.py

import os
import faiss
import pickle
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Paths
INDEX_DIR = "faiss_index"
EMBEDDING_MODEL = "text-embedding-3-small"

# Load FAISS index and metadata
def load_faiss_index():
    index = faiss.read_index(os.path.join(INDEX_DIR, "index.faiss"))
    with open(os.path.join(INDEX_DIR, "index.pkl"), "rb") as f:
        documents = pickle.load(f)
    return index, documents

# Embed user question
def embed_query(text):
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=[text]
    )
    return response.data[0].embedding

# Search index for top_k relevant chunks
def search_knowledge_base(query, top_k=3):
    index, documents = load_faiss_index()
    query_embedding = embed_query(query)
    D, I = index.search([query_embedding], top_k)

    matched_chunks = [documents[i] for i in I[0] if i < len(documents)]
    return matched_chunks
