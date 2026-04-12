"""
Evaluation Metrics for RAG System

Implements:
1. Recall@K - Does the retrieved context contain the answer?
2. Faithfulness - Is the generated answer grounded in the sources?

Uses "Judge LLM" pattern for semantic evaluation.
"""

from typing import List, Dict
from anthropic import Anthropic
from dotenv import load_dotenv
import json

load_dotenv()

client = Anthropic()


def calculate_recall_at_k(
    question: str,
    expected_answer: str,
    retrieved_docs: List[Dict],
    k: int = 3
) -> Dict:
    """
    Recall@K: Does the top-K retrieved documents contain information to answer the question?

    Uses Judge LLM to determine if retrieved context is sufficient.

    Returns:
        {
            "recall_at_k": 1.0 or 0.0,
            "reasoning": "Why the context is/isn't sufficient"
        }
    """

    # Combine top-K documents
    context = "\n\n".join([
        f"Document {i+1}:\n{doc.get('page_content', '')}"
        for i, doc in enumerate(retrieved_docs[:k])
    ])

    # Judge LLM prompt
    judge_prompt = f"""You are evaluating a RAG system's retrieval quality.

Question: {question}

Expected Answer (reference): {expected_answer}

Retrieved Context (top-{k} documents):
{context}

Task: Determine if the retrieved context contains enough information to answer the question.

Respond with JSON:
{{
    "contains_answer": true/false,
    "reasoning": "Brief explanation of why context is sufficient or not"
}}

Be strict: Only return true if the context clearly contains the information needed to answer the question."""

    try:
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=300,
            temperature=0,
            messages=[{"role": "user", "content": judge_prompt}]
        )

        # Parse JSON response
        result = json.loads(response.content[0].text)

        return {
            "recall_at_k": 1.0 if result["contains_answer"] else 0.0,
            "reasoning": result["reasoning"]
        }

    except Exception as e:
        return {
            "recall_at_k": 0.0,
            "reasoning": f"Error in evaluation: {str(e)}"
        }


def calculate_faithfulness(
    generated_answer: str,
    source_documents: List[Dict]
) -> Dict:
    """
    Faithfulness: Is the generated answer grounded in the source documents?

    Checks for hallucinations - does the answer contain information not in sources?

    Returns:
        {
            "faithfulness_score": 0.0 to 1.0,
            "reasoning": "Why answer is/isn't faithful",
            "hallucination_detected": bool
        }
    """

    # Combine source documents
    sources = "\n\n".join([
        f"Source {i+1}:\n{doc.get('page_content', '')}"
        for i, doc in enumerate(source_documents)
    ])

    # Judge LLM prompt
    judge_prompt = f"""You are evaluating whether an AI-generated answer is faithful to its sources.

Generated Answer:
{generated_answer}

Source Documents:
{sources}

Task: Determine if the answer is grounded in the sources or contains hallucinated information.

Check:
1. Are all facts in the answer present in the sources?
2. Does the answer make claims not supported by the sources?
3. Is the answer's tone/certainty appropriate given the sources?

Respond with JSON:
{{
    "is_faithful": true/false,
    "faithfulness_score": 0.0-1.0,
    "reasoning": "Explanation of why answer is/isn't faithful",
    "hallucination_detected": true/false
}}

Be strict: Even minor unsupported claims should reduce the score."""

    try:
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=400,
            temperature=0,
            messages=[{"role": "user", "content": judge_prompt}]
        )

        # Parse JSON response
        result = json.loads(response.content[0].text)

        return {
            "faithfulness_score": result["faithfulness_score"],
            "reasoning": result["reasoning"],
            "hallucination_detected": result["hallucination_detected"]
        }

    except Exception as e:
        return {
            "faithfulness_score": 0.0,
            "reasoning": f"Error in evaluation: {str(e)}",
            "hallucination_detected": True
        }


def calculate_answer_relevance(
    question: str,
    generated_answer: str
) -> Dict:
    """
    Answer Relevance: Does the answer actually address the question?

    Returns:
        {
            "relevance_score": 0.0 to 1.0,
            "reasoning": "Why answer is/isn't relevant"
        }
    """

    judge_prompt = f"""You are evaluating whether an answer is relevant to the question.

Question: {question}

Generated Answer: {generated_answer}

Task: Determine if the answer actually addresses the question.

Check:
1. Does the answer respond to what was asked?
2. Is the answer on-topic?
3. Does the answer avoid the question or go off-topic?

Respond with JSON:
{{
    "is_relevant": true/false,
    "relevance_score": 0.0-1.0,
    "reasoning": "Explanation of relevance"
}}"""

    try:
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=300,
            temperature=0,
            messages=[{"role": "user", "content": judge_prompt}]
        )

        result = json.loads(response.content[0].text)

        return {
            "relevance_score": result["relevance_score"],
            "reasoning": result["reasoning"]
        }

    except Exception as e:
        return {
            "relevance_score": 0.0,
            "reasoning": f"Error in evaluation: {str(e)}"
        }


def calculate_all_metrics(
    question: str,
    expected_answer: str,
    generated_answer: str,
    retrieved_docs: List[Dict],
    k: int = 3
) -> Dict:
    """
    Calculate all metrics for a single Q&A pair.

    Returns comprehensive evaluation results.
    """

    recall = calculate_recall_at_k(question, expected_answer, retrieved_docs, k)
    faithfulness = calculate_faithfulness(generated_answer, retrieved_docs[:k])
    relevance = calculate_answer_relevance(question, generated_answer)

    return {
        "recall_at_k": recall["recall_at_k"],
        "recall_reasoning": recall["reasoning"],
        "faithfulness_score": faithfulness["faithfulness_score"],
        "faithfulness_reasoning": faithfulness["reasoning"],
        "hallucination_detected": faithfulness["hallucination_detected"],
        "relevance_score": relevance["relevance_score"],
        "relevance_reasoning": relevance["reasoning"]
    }
