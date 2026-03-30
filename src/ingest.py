"""
Architecture Notes:
- Uses RecursiveCharacterTextSplitter: smart splitting that respects markdown structure
- Chroma persists to disk: no re-indexing on every run (production pattern)
- Embedding: Using Voyage AI embeddings (via Anthropic ecosystem) for better quality
  Alternative: Can use sentence-transformers for fully local embeddings
"""

import os
from pathlib import Path
from git import Repo
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from dotenv import load_dotenv

load_dotenv()

# Config
REPO_URL = "https://github.com/tiangolo/fastapi"
REPO_PATH = "./data/fastapi_repo"
DOCS_PATH = f"{REPO_PATH}/docs/en/docs"
CHROMA_PATH = "./data/chroma_db"

def clone_repo():
    """Clone FastAPI repo if not exists"""
    if not Path(REPO_PATH).exists():
        print(f"Cloning {REPO_URL}...")
        Repo.clone_from(REPO_URL, REPO_PATH, depth=1)  # Shallow clone
        print("✓ Cloned successfully")
    else:
        print("✓ Repo already exists, skipping clone")

def load_documents():
    """Load markdown files from docs folder"""
    print(f"\nLoading documents from {DOCS_PATH}...")
    loader = DirectoryLoader(
        DOCS_PATH,
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={'autodetect_encoding': True}
    )
    docs = loader.load()
    print(f"✓ Loaded {len(docs)} documents")
    return docs

def split_documents(docs):
    """
    Split docs into chunks with overlap

    Key Decision: 1000 char chunks with 200 overlap
    - Why not tokens? Simpler to reason about, avoids tokenizer dependency
    - Why 1000? Balances context preservation vs retrieval precision
    - Why 200 overlap? Prevents semantic breaks at chunk boundaries
    """
    print("\nSplitting documents into chunks...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,        # ~750 words
        chunk_overlap=200,      # Preserve context across chunks
        length_function=len,
        separators=["\n## ", "\n### ", "\n\n", "\n", " ", ""]  # Respect markdown headers
    )
    chunks = splitter.split_documents(docs)
    print(f"✓ Split into {len(chunks)} chunks")

    # Show sample chunk for debugging
    if chunks:
        print(f"\nSample chunk (first 200 chars):")
        print(f"  Source: {chunks[0].metadata.get('source', 'Unknown')}")
        print(f"  Content: {chunks[0].page_content[:200]}...")

    return chunks

def create_vectorstore(chunks):
    """
    Generate embeddings and store in Chroma

    Key Decision: Using HuggingFace embeddings (local, free)
    - Model: all-MiniLM-L6-v2 (384 dimensions, fast, decent quality)
    - Alternative: OpenAI embeddings (better quality, costs $0.0001/1k tokens)
    - Why local? No API costs, no rate limits, reproducible
    """
    print("\nGenerating embeddings (this may take a few minutes)...")

    # Use local embeddings model
    embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )

    print("Creating vector store...")
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_PATH
    )

    count = vectorstore._collection.count()
    print(f"✓ Stored {count} embeddings in Chroma at {CHROMA_PATH}")
    return vectorstore

if __name__ == "__main__":
    print("=== Phase 1: Indexing FastAPI Documentation ===\n")

    try:
        clone_repo()
        docs = load_documents()
        chunks = split_documents(docs)
        create_vectorstore(chunks)

        print("\n" + "="*50)
        print("✓ Indexing complete!")
        print("="*50)
        print(f"\nNext step: Run 'python src/query.py' to query the knowledge base")

    except Exception as e:
        print(f"\n✗ Error during indexing: {e}")
        raise