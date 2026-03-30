"""
Phase 4: Production REST API

Architecture:
- FastAPI backend with multiple endpoints
- Session-based conversation management (multi-user support)
- Both stateless and stateful query modes
- Request/response validation with Pydantic
- Observability: structured logging, basic metrics

Key Production Patterns:
1. Session Management: Each user gets isolated conversation memory
2. Lazy Loading: Vector DB loaded once at startup (not per request)
3. Error Boundaries: Proper HTTP status codes + error messages
4. CORS: Frontend can call from different domain
"""

import os
import time
import uuid
from typing import Dict, List, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import PromptTemplate
from langchain_classic.chains import RetrievalQA, ConversationalRetrievalChain
from langchain_classic.memory import ConversationBufferMemory

load_dotenv()

# ============================================================================
# Configuration
# ============================================================================

CHROMA_PATH = "./data/chroma_db"
MODEL_NAME = "claude-3-haiku-20240307"
MAX_SESSIONS = 1000  # Prevent memory exhaustion

# ============================================================================
# Pydantic Models (Request/Response Schemas)
# ============================================================================

class QueryRequest(BaseModel):
    """Stateless query request"""
    question: str = Field(..., min_length=1, max_length=500, description="User question")

    class Config:
        json_schema_extra = {
            "example": {
                "question": "How do I handle CORS in FastAPI?"
            }
        }

class ChatRequest(BaseModel):
    """Stateful chat request"""
    session_id: str = Field(..., description="Unique session identifier")
    question: str = Field(..., min_length=1, max_length=500, description="User question")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "user-123",
                "question": "What is CORS?"
            }
        }

class Source(BaseModel):
    """Document source metadata"""
    path: str
    similarity: Optional[float] = None

class QueryResponse(BaseModel):
    """API response model"""
    answer: str
    sources: List[Source]
    session_id: Optional[str] = None
    processing_time_ms: float

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    vector_db_count: int
    active_sessions: int
    timestamp: str

class SessionInfo(BaseModel):
    """Session metadata"""
    session_id: str
    message_count: int
    created_at: str
    last_active: str

# ============================================================================
# Global State (Loaded Once at Startup)
# ============================================================================

class RAGService:
    """
    Singleton service managing RAG resources

    Why singleton?
    - Vector DB is expensive to load (embedding model + Chroma)
    - Loading per-request would be 100x slower
    - Shared across all API requests
    """

    def __init__(self):
        self.vectorstore = None
        self.embeddings = None
        self.llm = None
        self.sessions: Dict[str, dict] = {}  # session_id → {memory, metadata}

    def initialize(self):
        """Load models and vector DB (called at startup)"""
        print("Initializing RAG service...")

        # Load embeddings model
        self.embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )

        # Load vector DB
        self.vectorstore = Chroma(
            persist_directory=CHROMA_PATH,
            embedding_function=self.embeddings
        )

        # Initialize LLM
        self.llm = ChatAnthropic(
            model=MODEL_NAME,
            temperature=0,
            max_tokens=500
        )

        count = self.vectorstore._collection.count()
        print(f"✓ Loaded {count} embeddings")
        print("✓ RAG service ready")

    def get_stateless_chain(self):
        """Create stateless QA chain (for /query endpoint)"""
        retriever = self.vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 3}
        )

        prompt = PromptTemplate(
            template="""You are a FastAPI documentation assistant.

If the context doesn't contain enough information, say:
"I don't have enough information in the FastAPI docs to answer that."

Do not make up information.

Context:
{context}

Question: {question}

Answer:""",
            input_variables=["context", "question"]
        )

        return RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=retriever,
            chain_type_kwargs={"prompt": prompt},
            return_source_documents=True
        )

    def get_or_create_session(self, session_id: str):
        """Get existing session or create new one"""

        # Session management: prevent unbounded growth
        if session_id not in self.sessions and len(self.sessions) >= MAX_SESSIONS:
            # Evict oldest session (simple LRU)
            oldest = min(self.sessions.items(),
                        key=lambda x: x[1]['metadata']['last_active'])
            del self.sessions[oldest[0]]

        if session_id not in self.sessions:
            # Create new session
            memory = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True,
                output_key="answer"
            )

            retriever = self.vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 3}
            )

            prompt = PromptTemplate(
                template="""You are a FastAPI documentation assistant in a conversation.

Use the conversation history and context to answer the question.

If the context doesn't contain enough information, say:
"I don't have enough information in the FastAPI docs to answer that."

Context:
{context}

Chat History:
{chat_history}

Question: {question}

Answer:""",
                input_variables=["context", "chat_history", "question"]
            )

            chain = ConversationalRetrievalChain.from_llm(
                llm=self.llm,
                retriever=retriever,
                memory=memory,
                combine_docs_chain_kwargs={"prompt": prompt},
                return_source_documents=True,
                verbose=False
            )

            self.sessions[session_id] = {
                'chain': chain,
                'memory': memory,
                'metadata': {
                    'created_at': datetime.now().isoformat(),
                    'last_active': datetime.now().isoformat(),
                    'message_count': 0
                }
            }

        # Update last active
        self.sessions[session_id]['metadata']['last_active'] = datetime.now().isoformat()

        return self.sessions[session_id]

    def clear_session(self, session_id: str) -> bool:
        """Clear conversation history for a session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False

# Initialize singleton
rag_service = RAGService()

# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="FastAPI Documentation RAG API",
    description="Production RAG system for querying FastAPI documentation",
    version="1.0.0"
)

# CORS: Allow frontend from different domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production: specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Startup/Shutdown Lifecycle
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Load models when API starts"""
    rag_service.initialize()

# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/", tags=["root"])
async def root():
    """Root endpoint"""
    return {
        "service": "FastAPI Documentation RAG API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "stateless_query": "/query",
            "stateful_chat": "/chat",
            "sessions": "/sessions"
        }
    }

@app.get("/health", response_model=HealthResponse, tags=["monitoring"])
async def health_check():
    """Health check endpoint for monitoring"""
    return HealthResponse(
        status="healthy",
        vector_db_count=rag_service.vectorstore._collection.count(),
        active_sessions=len(rag_service.sessions),
        timestamp=datetime.now().isoformat()
    )

@app.post("/query", response_model=QueryResponse, tags=["rag"])
async def query_stateless(request: QueryRequest):
    """
    Stateless RAG query (no conversation memory)

    Use case: One-off questions, search functionality
    """
    start_time = time.time()

    try:
        chain = rag_service.get_stateless_chain()
        result = chain.invoke({"query": request.question})

        sources = [
            Source(
                path=doc.metadata.get('source', 'Unknown').replace('data/fastapi_repo/docs/en/docs/', ''),
                similarity=doc.metadata.get('score')
            )
            for doc in result['source_documents']
        ]

        processing_time = (time.time() - start_time) * 1000

        return QueryResponse(
            answer=result['result'],
            sources=sources,
            processing_time_ms=processing_time
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query failed: {str(e)}"
        )

@app.post("/chat", response_model=QueryResponse, tags=["rag"])
async def chat_stateful(request: ChatRequest):
    """
    Stateful RAG chat (with conversation memory)

    Use case: Multi-turn conversations, chatbots
    Session persists until /sessions/{session_id} DELETE is called
    """
    start_time = time.time()

    try:
        session = rag_service.get_or_create_session(request.session_id)
        chain = session['chain']

        result = chain.invoke({"question": request.question})

        # Update metadata
        session['metadata']['message_count'] += 1

        sources = [
            Source(
                path=doc.metadata.get('source', 'Unknown').replace('data/fastapi_repo/docs/en/docs/', ''),
                similarity=doc.metadata.get('score')
            )
            for doc in result['source_documents']
        ]

        processing_time = (time.time() - start_time) * 1000

        return QueryResponse(
            answer=result['answer'],
            sources=sources,
            session_id=request.session_id,
            processing_time_ms=processing_time
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat failed: {str(e)}"
        )

@app.get("/sessions", response_model=List[SessionInfo], tags=["session-management"])
async def list_sessions():
    """List all active sessions"""
    return [
        SessionInfo(
            session_id=sid,
            message_count=session['metadata']['message_count'],
            created_at=session['metadata']['created_at'],
            last_active=session['metadata']['last_active']
        )
        for sid, session in rag_service.sessions.items()
    ]

@app.delete("/sessions/{session_id}", tags=["session-management"])
async def clear_session(session_id: str):
    """Clear conversation history for a specific session"""
    if rag_service.clear_session(session_id):
        return {"message": f"Session {session_id} cleared"}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )

# ============================================================================
# Run Server (for development)
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
