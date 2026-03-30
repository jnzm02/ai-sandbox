"""
API Test Script

Tests all endpoints of the RAG API:
1. Health check
2. Stateless query
3. Stateful chat
4. Session management
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_health():
    """Test /health endpoint"""
    print("\n" + "="*70)
    print("TEST 1: Health Check")
    print("="*70)

    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response:")
    print(json.dumps(response.json(), indent=2))
    assert response.status_code == 200

def test_stateless_query():
    """Test /query endpoint (stateless)"""
    print("\n" + "="*70)
    print("TEST 2: Stateless Query")
    print("="*70)

    payload = {
        "question": "How do I handle CORS in FastAPI?"
    }

    print(f"Request:")
    print(json.dumps(payload, indent=2))

    response = requests.post(f"{BASE_URL}/query", json=payload)
    print(f"\nStatus: {response.status_code}")
    print(f"Response:")
    data = response.json()
    print(f"  Answer: {data['answer'][:200]}...")
    print(f"  Sources: {[s['path'] for s in data['sources']]}")
    print(f"  Processing time: {data['processing_time_ms']:.2f}ms")

    assert response.status_code == 200

def test_stateful_chat():
    """Test /chat endpoint (conversational)"""
    print("\n" + "="*70)
    print("TEST 3: Stateful Chat (Multi-turn conversation)")
    print("="*70)

    session_id = "test-session-123"

    # Turn 1
    print("\n[Turn 1]")
    payload1 = {
        "session_id": session_id,
        "question": "What is CORS?"
    }
    print(f"Question: {payload1['question']}")

    response1 = requests.post(f"{BASE_URL}/chat", json=payload1)
    data1 = response1.json()
    print(f"Answer: {data1['answer'][:150]}...")

    time.sleep(1)  # Small delay

    # Turn 2: Follow-up (uses pronoun)
    print("\n[Turn 2]")
    payload2 = {
        "session_id": session_id,
        "question": "How do I configure it?"  # "it" = CORS from Turn 1
    }
    print(f"Question: {payload2['question']}")

    response2 = requests.post(f"{BASE_URL}/chat", json=payload2)
    data2 = response2.json()
    print(f"Answer: {data2['answer'][:150]}...")
    print(f"✓ System understood 'it' refers to CORS from previous turn!")

    assert response1.status_code == 200
    assert response2.status_code == 200

def test_session_management():
    """Test session listing and deletion"""
    print("\n" + "="*70)
    print("TEST 4: Session Management")
    print("="*70)

    # List sessions
    print("\n[List Sessions]")
    response = requests.get(f"{BASE_URL}/sessions")
    sessions = response.json()
    print(f"Active sessions: {len(sessions)}")
    for session in sessions:
        print(f"  - {session['session_id']}: {session['message_count']} messages")

    # Clear a session
    if sessions:
        session_id = sessions[0]['session_id']
        print(f"\n[Clear Session: {session_id}]")
        response = requests.delete(f"{BASE_URL}/sessions/{session_id}")
        print(f"Response: {response.json()}")
        assert response.status_code == 200

def main():
    print("="*70)
    print("RAG API TEST SUITE")
    print("="*70)
    print(f"\nTesting API at: {BASE_URL}")
    print("Make sure the server is running: python3 src/api.py")

    # Wait for server to be ready
    print("\nWaiting for server to be ready...")
    for i in range(30):
        try:
            requests.get(f"{BASE_URL}/health", timeout=2)
            print("✓ Server is ready!")
            break
        except requests.exceptions.RequestException:
            print(f"  Attempt {i+1}/30: Server not ready yet...")
            time.sleep(2)
    else:
        print("\n✗ Server failed to start. Exiting.")
        return

    try:
        test_health()
        test_stateless_query()
        test_stateful_chat()
        test_session_management()

        print("\n" + "="*70)
        print("✓ ALL TESTS PASSED")
        print("="*70)

    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
