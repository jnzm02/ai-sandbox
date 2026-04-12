"""
Experiment Runner - RAG System Evaluation

Runs the RAG pipeline against the golden dataset and generates a comprehensive report.

Output JSON includes:
- Overall accuracy %
- p50 and p95 latency
- Cost per 100 queries
- Per-question detailed results

Usage:
    python evaluation/run_experiment.py

Output:
    evaluation/results/baseline_TIMESTAMP.json
"""

import json
import time
import statistics
from pathlib import Path
from datetime import datetime
from typing import List, Dict
import os

from dotenv import load_dotenv
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_anthropic import ChatAnthropic
from langchain_classic.chains import RetrievalQA
from langchain_core.prompts import PromptTemplate

from metrics import calculate_all_metrics

load_dotenv()

# Configuration
CHROMA_PATH = "./data/chroma_db"
MODEL_NAME = "claude-3-haiku-20240307"
GOLDEN_DATASET_PATH = "evaluation/golden_dataset.json"
RESULTS_DIR = "evaluation/results"

# Pricing (as of April 2024 - update if needed)
ANTHROPIC_PRICING = {
    "claude-3-haiku-20240307": {
        "input": 0.25 / 1_000_000,   # $0.25 per 1M input tokens
        "output": 1.25 / 1_000_000   # $1.25 per 1M output tokens
    }
}


class RAGEvaluator:
    """Evaluates RAG system against golden dataset"""

    def __init__(self):
        self.vectorstore = None
        self.qa_chain = None
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    def initialize(self):
        """Load vector store and create QA chain"""
        print("🔧 Initializing RAG system...")

        # Load embeddings
        embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )

        # Load vector DB
        self.vectorstore = Chroma(
            persist_directory=CHROMA_PATH,
            embedding_function=embeddings
        )

        # Create retriever
        retriever = self.vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 3}
        )

        # Create prompt
        template = """You are a FastAPI documentation assistant.

If the context doesn't contain enough information, say:
"I don't have enough information in the FastAPI docs to answer that."

Do not make up information.

Context:
{context}

Question: {question}

Answer:"""

        prompt = PromptTemplate(
            template=template,
            input_variables=["context", "question"]
        )

        # Create LLM with token tracking
        llm = ChatAnthropic(
            model=MODEL_NAME,
            temperature=0,
            max_tokens=500
        )

        # Create QA chain
        self.qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=retriever,
            chain_type_kwargs={"prompt": prompt},
            return_source_documents=True
        )

        count = self.vectorstore._collection.count()
        print(f"✅ Loaded {count} embeddings")
        print(f"✅ QA chain ready\n")

    def run_single_query(self, question: str, expected_answer: str) -> Dict:
        """
        Run a single query through the RAG pipeline and measure performance.

        Returns:
            {
                "question": str,
                "expected_answer": str,
                "generated_answer": str,
                "latency_ms": float,
                "retrieved_docs": List[Dict],
                "metrics": Dict (recall, faithfulness, etc.)
            }
        """
        start_time = time.time()

        # Query the RAG system
        result = self.qa_chain.invoke({"query": question})

        latency_ms = (time.time() - start_time) * 1000

        # Extract source documents
        retrieved_docs = [
            {
                "page_content": doc.page_content,
                "source": doc.metadata.get('source', 'Unknown')
            }
            for doc in result['source_documents']
        ]

        # Calculate metrics
        metrics = calculate_all_metrics(
            question=question,
            expected_answer=expected_answer,
            generated_answer=result['result'],
            retrieved_docs=retrieved_docs,
            k=3
        )

        # Estimate token usage (rough approximation)
        # Input: question + context (~1500 chars = ~375 tokens)
        # Output: answer (~500 chars = ~125 tokens)
        estimated_input_tokens = len(question + str(retrieved_docs)) // 4
        estimated_output_tokens = len(result['result']) // 4

        self.total_input_tokens += estimated_input_tokens
        self.total_output_tokens += estimated_output_tokens

        return {
            "question": question,
            "expected_answer": expected_answer,
            "generated_answer": result['result'],
            "latency_ms": latency_ms,
            "retrieved_docs": retrieved_docs,
            "metrics": metrics,
            "estimated_tokens": {
                "input": estimated_input_tokens,
                "output": estimated_output_tokens
            }
        }

    def run_experiment(self, golden_dataset_path: str) -> Dict:
        """
        Run evaluation on entire golden dataset.

        Returns comprehensive report.
        """
        print(f"📊 Loading golden dataset from {golden_dataset_path}...")

        with open(golden_dataset_path, 'r') as f:
            dataset = json.load(f)

        questions = dataset['questions']
        print(f"✅ Loaded {len(questions)} questions\n")

        print("🚀 Running evaluation...")
        print("=" * 60)

        results = []
        latencies = []

        for i, item in enumerate(questions, 1):
            question = item['question']
            expected_answer = item['expected_answer']
            difficulty = item.get('difficulty', 'unknown')

            print(f"\n[{i}/{len(questions)}] {difficulty.upper()}: {question[:60]}...")

            try:
                result = self.run_single_query(question, expected_answer)
                results.append(result)
                latencies.append(result['latency_ms'])

                # Print key metrics
                print(f"  ⏱️  Latency: {result['latency_ms']:.0f}ms")
                print(f"  📏 Recall@3: {result['metrics']['recall_at_k']:.2f}")
                print(f"  ✅ Faithfulness: {result['metrics']['faithfulness_score']:.2f}")
                print(f"  🎯 Relevance: {result['metrics']['relevance_score']:.2f}")

            except Exception as e:
                print(f"  ❌ Error: {e}")
                results.append({
                    "question": question,
                    "error": str(e)
                })

        print("\n" + "=" * 60)
        print("📈 Generating report...")

        # Calculate aggregate metrics
        recall_scores = [r['metrics']['recall_at_k'] for r in results if 'metrics' in r]
        faithfulness_scores = [r['metrics']['faithfulness_score'] for r in results if 'metrics' in r]
        relevance_scores = [r['metrics']['relevance_score'] for r in results if 'metrics' in r]

        # Calculate cost
        model_pricing = ANTHROPIC_PRICING[MODEL_NAME]
        total_cost = (
            self.total_input_tokens * model_pricing['input'] +
            self.total_output_tokens * model_pricing['output']
        )
        cost_per_100_queries = (total_cost / len(questions)) * 100

        # Generate report
        report = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "model": MODEL_NAME,
                "total_questions": len(questions),
                "successful_queries": len(recall_scores),
                "failed_queries": len(questions) - len(recall_scores)
            },
            "performance": {
                "latency": {
                    "p50_ms": statistics.median(latencies) if latencies else 0,
                    "p95_ms": statistics.quantiles(latencies, n=20)[18] if len(latencies) > 1 else 0,
                    "mean_ms": statistics.mean(latencies) if latencies else 0,
                    "min_ms": min(latencies) if latencies else 0,
                    "max_ms": max(latencies) if latencies else 0
                },
                "cost": {
                    "total_queries": len(questions),
                    "total_cost_usd": round(total_cost, 4),
                    "cost_per_query_usd": round(total_cost / len(questions), 4),
                    "cost_per_100_queries_usd": round(cost_per_100_queries, 4),
                    "total_input_tokens": self.total_input_tokens,
                    "total_output_tokens": self.total_output_tokens
                }
            },
            "quality_metrics": {
                "recall_at_3": {
                    "mean": round(statistics.mean(recall_scores), 3) if recall_scores else 0,
                    "percentage": f"{round(statistics.mean(recall_scores) * 100, 1)}%" if recall_scores else "0%"
                },
                "faithfulness": {
                    "mean": round(statistics.mean(faithfulness_scores), 3) if faithfulness_scores else 0,
                    "percentage": f"{round(statistics.mean(faithfulness_scores) * 100, 1)}%" if faithfulness_scores else "0%"
                },
                "relevance": {
                    "mean": round(statistics.mean(relevance_scores), 3) if relevance_scores else 0,
                    "percentage": f"{round(statistics.mean(relevance_scores) * 100, 1)}%" if relevance_scores else "0%"
                },
                "hallucination_rate": {
                    "count": sum(1 for r in results if r.get('metrics', {}).get('hallucination_detected')),
                    "percentage": f"{round(sum(1 for r in results if r.get('metrics', {}).get('hallucination_detected')) / len(results) * 100, 1)}%" if results else "0%"
                }
            },
            "detailed_results": results
        }

        return report


def main():
    """Run evaluation experiment"""

    # Create results directory
    Path(RESULTS_DIR).mkdir(parents=True, exist_ok=True)

    # Initialize evaluator
    evaluator = RAGEvaluator()
    evaluator.initialize()

    # Run experiment
    report = evaluator.run_experiment(GOLDEN_DATASET_PATH)

    # Save report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"{RESULTS_DIR}/baseline_{timestamp}.json"

    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\n✅ Report saved to {output_path}")
    print("\n" + "=" * 60)
    print("📊 BASELINE METRICS SUMMARY")
    print("=" * 60)
    print(f"\n🎯 Quality Metrics:")
    print(f"   Recall@3:      {report['quality_metrics']['recall_at_3']['percentage']}")
    print(f"   Faithfulness:  {report['quality_metrics']['faithfulness']['percentage']}")
    print(f"   Relevance:     {report['quality_metrics']['relevance']['percentage']}")
    print(f"   Hallucinations: {report['quality_metrics']['hallucination_rate']['percentage']}")

    print(f"\n⏱️  Performance:")
    print(f"   p50 Latency:   {report['performance']['latency']['p50_ms']:.0f}ms")
    print(f"   p95 Latency:   {report['performance']['latency']['p95_ms']:.0f}ms")

    print(f"\n💰 Cost:")
    print(f"   Per Query:     ${report['performance']['cost']['cost_per_query_usd']:.4f}")
    print(f"   Per 100:       ${report['performance']['cost']['cost_per_100_queries_usd']:.2f}")

    print("\n" + "=" * 60)
    print("\n🎉 Baseline established!")
    print("   Now you can add features and measure if they improve these metrics.")


if __name__ == "__main__":
    main()
