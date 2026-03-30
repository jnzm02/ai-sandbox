"""
Demonstration: Stateless vs Stateful RAG

This script shows the critical difference between:
1. Stateless RAG (query.py): Each question is independent
2. Stateful RAG (chat.py): Conversation history is maintained
"""

import sys
sys.path.append('src')

from dotenv import load_dotenv
from query import load_vectorstore as load_vectorstore_stateless, create_qa_chain
from chat import load_vectorstore as load_vectorstore_stateful, create_conversational_chain

load_dotenv()

def test_stateless_rag():
    """Test query.py: Each question is independent"""
    print("=" * 70)
    print("TEST 1: STATELESS RAG (query.py)")
    print("=" * 70)
    print("Each question is answered independently (no memory)\n")

    vectorstore = load_vectorstore_stateless()
    qa_chain = create_qa_chain(vectorstore)

    # Conversation sequence
    questions = [
        "How do I handle CORS in FastAPI?",
        "Can you show me an example?",  # ← This will FAIL (no context)
    ]

    for i, question in enumerate(questions, 1):
        print(f"\n[Question {i}] {question}")
        result = qa_chain.invoke({"query": question})
        print(f"\n[Answer {i}]")
        print(result['result'])
        print("\n" + "-" * 70)

    print("\n⚠️  PROBLEM: Question 2 fails because the system doesn't know")
    print("    what 'that' refers to (no conversation memory).\n")

def test_stateful_rag():
    """Test chat.py: Conversation history is maintained"""
    print("\n\n")
    print("=" * 70)
    print("TEST 2: STATEFUL RAG (chat.py)")
    print("=" * 70)
    print("Conversation history is maintained (has memory)\n")

    vectorstore = load_vectorstore_stateful()
    chain = create_conversational_chain(vectorstore)

    # Same conversation sequence
    questions = [
        "How do I handle CORS in FastAPI?",
        "Can you show me an example?",  # ← This will SUCCEED (uses memory)
    ]

    for i, question in enumerate(questions, 1):
        print(f"\n[Question {i}] {question}")
        result = chain.invoke({"question": question})
        print(f"\n[Answer {i}]")
        print(result['answer'])
        print("\n" + "-" * 70)

    print("\n✓ SUCCESS: Question 2 works because the system remembers")
    print("  the conversation about CORS and understands the context.\n")

def main():
    print("\n" + "=" * 70)
    print("CONVERSATIONAL RAG DEMONSTRATION")
    print("=" * 70)
    print("\nThis test shows why conversation memory matters in RAG systems.")
    print("We'll ask the SAME questions to both stateless and stateful systems.\n")

    input("Press Enter to start the stateless test...")
    test_stateless_rag()

    input("\nPress Enter to start the stateful test...")
    test_stateful_rag()

    print("\n" + "=" * 70)
    print("KEY TAKEAWAY:")
    print("=" * 70)
    print("""
Stateless RAG (query.py):
  ✓ Simple, no memory overhead
  ✓ Each question is independent
  ✗ Can't handle follow-up questions
  ✗ User must provide full context each time

Stateful RAG (chat.py):
  ✓ Natural conversation flow
  ✓ Handles pronouns ("it", "that", "the example")
  ✓ Better user experience
  ✗ Memory grows over time (context window limit)
  ✗ More complex state management

Production Choice:
  - Use stateless for search/lookup (one-off questions)
  - Use stateful for support chatbots (ongoing conversations)
""")

if __name__ == "__main__":
    main()
