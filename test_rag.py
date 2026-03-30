"""
Test script to demonstrate the RAG system

This script tests the knowledge base with predefined questions
to show how the system works end-to-end.
"""

import sys
sys.path.append('src')

from dotenv import load_dotenv
from query import load_vectorstore, create_qa_chain, format_sources

load_dotenv()

# Test questions
test_questions = [
    "How do I handle CORS in FastAPI?",
    "How do I use path parameters?",
    "What is dependency injection in FastAPI?",
]

def main():
    print("=" * 70)
    print("RAG SYSTEM TEST - FastAPI Documentation Q&A")
    print("=" * 70)
    print()

    # Load knowledge base
    vectorstore = load_vectorstore()

    # Create QA chain
    qa_chain = create_qa_chain(vectorstore)

    # Test each question
    for i, question in enumerate(test_questions, 1):
        print(f"\n[Question {i}]")
        print(f"{question}")
        print()

        result = qa_chain.invoke({"query": question})

        print("Answer:")
        print(result['result'])
        print()
        print("Sources:")
        print(format_sources(result['source_documents']))
        print()
        print("-" * 70)

if __name__ == "__main__":
    main()