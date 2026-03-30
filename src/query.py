"""
Phase 2: Query Interface

Architecture Notes:
- Retriever: Top-3 chunks via cosine similarity
- LLM: Claude 3 Haiku (fast, cheap)
- Prompt: Explicitly instructs model to say "I don't know" if context insufficient
- Source attribution: Shows which chunks were used for answer
"""

import os
from dotenv import load_dotenv
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_anthropic import ChatAnthropic
from langchain_classic.chains import RetrievalQA
from langchain_core.prompts import PromptTemplate

load_dotenv()

# Config
CHROMA_PATH = "./data/chroma_db"
MODEL_NAME = "claude-3-haiku-20240307"  # Validated model

def load_vectorstore():
    """
    Load existing Chroma DB

    Key Decision: Use SAME embedding model as indexing
    - If you change models, embeddings won't match → poor retrieval
    - This is a common production bug: index with model A, query with model B
    """
    print("Loading knowledge base...")
    embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )

    vectorstore = Chroma(
        persist_directory=CHROMA_PATH,
        embedding_function=embeddings
    )

    count = vectorstore._collection.count()
    print(f"✓ Loaded {count} embeddings from {CHROMA_PATH}\n")
    return vectorstore

def create_qa_chain(vectorstore):
    """
    Build RAG chain with custom prompt

    Key Decisions:
    1. Retriever: k=3 chunks (more chunks = more context, but also more noise)
    2. Prompt: Explicitly handles "no answer" case
    3. Temperature: 0 for deterministic answers (good for docs Q&A)
    """

    # Retriever: top-3 most similar chunks
    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 3}
    )

    # Custom prompt template
    # Notice the explicit instruction to say "I don't know" - critical for production
    template = """You are a FastAPI documentation assistant. Use the following context to answer the question.

If the context doesn't contain enough information to answer the question, say:
"I don't have enough information in the FastAPI docs to answer that. Could you rephrase or ask about a specific FastAPI feature?"

Do not make up information. Only use what's in the context below.

Context:
{context}

Question: {question}

Answer:"""

    prompt = PromptTemplate(
        template=template,
        input_variables=["context", "question"]
    )

    # LLM: Claude 3 Haiku
    llm = ChatAnthropic(
        model=MODEL_NAME,
        temperature=0,  # Deterministic for factual Q&A
        max_tokens=500
    )

    # Chain: stuff all retrieved docs into prompt (works for small doc sets)
    # Alternative: "map_reduce" for large doc sets (process each chunk separately, then combine)
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",  # Inject all chunks directly into prompt
        retriever=retriever,
        chain_type_kwargs={"prompt": prompt},
        return_source_documents=True  # Essential for debugging & transparency
    )

    return qa_chain

def format_sources(source_docs):
    """Format source documents for display"""
    sources = []
    for i, doc in enumerate(source_docs, 1):
        source_path = doc.metadata.get('source', 'Unknown')
        # Clean up path for readability
        source_path = source_path.replace('data/fastapi_repo/docs/en/docs/', '')
        sources.append(f"  [{i}] {source_path}")
    return "\n".join(sources)

def main():
    print("=== FastAPI Documentation Q&A ===")
    print("Powered by Claude 3 Haiku + Chroma VectorDB\n")

    # Check API key
    if not os.getenv('ANTHROPIC_API_KEY'):
        print("Error: ANTHROPIC_API_KEY not found in .env file")
        return

    # Load vector store
    try:
        vectorstore = load_vectorstore()
    except Exception as e:
        print(f"Error loading vector store: {e}")
        print("Did you run 'python src/ingest.py' first?")
        return

    # Create QA chain
    qa_chain = create_qa_chain(vectorstore)

    print("Ready! Type 'exit' to quit\n")
    print("-" * 60)

    while True:
        question = input("\nYour question: ").strip()

        if question.lower() in ['exit', 'quit', 'q']:
            print("\nGoodbye!")
            break

        if not question:
            continue

        try:
            # Query the knowledge base
            result = qa_chain.invoke({"query": question})

            # Display answer
            print(f"\nAnswer:")
            print(f"{result['result']}")

            # Display sources (for transparency & debugging)
            print(f"\nSources:")
            print(format_sources(result['source_documents']))

            print("\n" + "-" * 60)

        except Exception as e:
            print(f"\nError: {e}")
            print("Please try again or check your API key.\n")

if __name__ == "__main__":
    main()