"""
Phase 3: Conversational RAG with Memory

Architecture Notes:
- ConversationBufferMemory: Stores full conversation history
- Contextual retrieval: Uses conversation context to improve chunk selection
- Memory-aware prompts: System knows what was discussed previously
- Follow-up handling: "Can you explain that further?" works

Key Difference from query.py:
- query.py: Stateless (each question independent)
- chat.py: Stateful (remembers previous Q&A pairs)
"""

import os
from dotenv import load_dotenv
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import PromptTemplate
from langchain_classic.chains import ConversationalRetrievalChain
from langchain_classic.memory import ConversationBufferMemory

load_dotenv()

# Config
CHROMA_PATH = "./data/chroma_db"
MODEL_NAME = "claude-3-haiku-20240307"

def load_vectorstore():
    """Load existing Chroma DB"""
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

def create_conversational_chain(vectorstore):
    """
    Build conversational RAG chain with memory

    Key Architecture Decision:
    - ConversationBufferMemory stores ALL chat history
    - Alternative: ConversationSummaryMemory (summarizes old messages to save tokens)
    - Alternative: ConversationBufferWindowMemory (keeps last K messages)

    Production Consideration:
    - BufferMemory grows unbounded → will eventually exceed context limit
    - For long conversations, use SummaryMemory or WindowMemory
    """

    # Memory: stores chat history as (human, ai) pairs
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True,  # Return as Message objects (not strings)
        output_key="answer"    # Which output to store (important for chains with multiple outputs)
    )

    # Retriever
    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 3}
    )

    # LLM
    llm = ChatAnthropic(
        model=MODEL_NAME,
        temperature=0,
        max_tokens=500
    )

    # Custom prompt for conversational context
    # Notice: {chat_history} is injected automatically by ConversationalRetrievalChain
    qa_prompt = PromptTemplate(
        template="""You are a FastAPI documentation assistant engaged in a conversation.

Use the conversation history and the context below to answer the current question.

If the question refers to previous messages (e.g., "Can you explain that further?", "What about the example you mentioned?"),
use the chat history to understand what "that" or "it" refers to.

If the context doesn't contain enough information, say:
"I don't have enough information in the FastAPI docs to answer that."

Do not make up information.

Context from documentation:
{context}

Chat History:
{chat_history}

Current Question: {question}

Answer:""",
        input_variables=["context", "chat_history", "question"]
    )

    # ConversationalRetrievalChain: combines retrieval + memory + generation
    chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=retriever,
        memory=memory,
        combine_docs_chain_kwargs={"prompt": qa_prompt},
        return_source_documents=True,
        verbose=False  # Set to True to see internal chain steps
    )

    return chain

def format_sources(source_docs):
    """Format source documents for display"""
    sources = []
    for i, doc in enumerate(source_docs, 1):
        source_path = doc.metadata.get('source', 'Unknown')
        source_path = source_path.replace('data/fastapi_repo/docs/en/docs/', '')
        sources.append(f"  [{i}] {source_path}")
    return "\n".join(sources)

def main():
    print("=" * 70)
    print("FastAPI Documentation Chat (Conversational RAG)")
    print("=" * 70)
    print("\nFeatures:")
    print("  ✓ Remembers conversation history")
    print("  ✓ Handles follow-up questions")
    print("  ✓ Contextual understanding (e.g., 'Can you explain that?')")
    print("\nType 'exit' to quit, 'clear' to reset conversation\n")

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

    # Create conversational chain
    chain = create_conversational_chain(vectorstore)

    print("Ready! Start asking questions about FastAPI.")
    print("-" * 70)

    conversation_count = 0

    while True:
        question = input(f"\n[{conversation_count + 1}] You: ").strip()

        if question.lower() in ['exit', 'quit', 'q']:
            print("\nGoodbye!")
            break

        if question.lower() == 'clear':
            chain.memory.clear()
            conversation_count = 0
            print("\n✓ Conversation history cleared.\n")
            print("-" * 70)
            continue

        if not question:
            continue

        try:
            # Query with conversation context
            result = chain.invoke({"question": question})

            conversation_count += 1

            # Display answer
            print(f"\n[{conversation_count}] Assistant:")
            print(result['answer'])

            # Display sources
            print(f"\n    Sources: {', '.join([doc.metadata.get('source', 'Unknown').replace('data/fastapi_repo/docs/en/docs/', '') for doc in result['source_documents']])}")

            print("\n" + "-" * 70)

        except Exception as e:
            print(f"\nError: {e}")
            print("Please try again.\n")

if __name__ == "__main__":
    main()