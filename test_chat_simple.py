"""
Simple test: Demonstrate conversation memory in action
"""

import sys
sys.path.append('src')

from dotenv import load_dotenv
from chat import load_vectorstore, create_conversational_chain

load_dotenv()

def main():
    print("=" * 70)
    print("CONVERSATIONAL RAG TEST")
    print("=" * 70)
    print()

    # Load knowledge base
    vectorstore = load_vectorstore()
    chain = create_conversational_chain(vectorstore)

    # Multi-turn conversation
    conversation = [
        ("What is CORS?", "Should explain Cross-Origin Resource Sharing"),
        ("How do I configure it?", "Should understand 'it' = CORS from previous Q"),
        ("Show me the code", "Should provide CORSMiddleware example"),
    ]

    for i, (question, expected) in enumerate(conversation, 1):
        print(f"\n[Turn {i}]")
        print(f"Question: {question}")
        print(f"Expected: {expected}")
        print()

        result = chain.invoke({"question": question})

        print(f"Answer:")
        print(result['answer'])
        print()
        print(f"Sources: {', '.join([doc.metadata.get('source', '').replace('data/fastapi_repo/docs/en/docs/', '') for doc in result['source_documents']])}")
        print("\n" + "-" * 70)

    print("\n✓ Notice how questions 2 and 3 use pronouns ('it', 'the code')")
    print("  but the system understands from conversation context!")

if __name__ == "__main__":
    main()
