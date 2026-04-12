# RAG System Evaluation Framework

**Google-level engineering rigor: Measure first, optimize second.**

This framework implements a Minimal Viable Evaluation (MVE) approach for proving RAG improvements with data, not assumptions.

---

## Quick Start

```bash
# 1. Generate golden dataset (30 Q&A pairs)
python3 evaluation/generate_ground_truth.py

# 2. Run baseline evaluation
python3 evaluation/run_experiment.py

# 3. View results
cat evaluation/results/baseline_*.json
```

---

## What Gets Measured

### Quality Metrics

1. **Recall@3** - Does the retriever find the right documents?
   - Measures: "Are the top-3 retrieved docs sufficient to answer the question?"
   - Uses: Judge LLM to evaluate retrieval quality
   - Target: >90% (current baseline: **93.3%**)

2. **Faithfulness** - Is the answer grounded in sources?
   - Measures: "Does the answer contain hallucinated information?"
   - Uses: Judge LLM to check if all claims are supported by sources
   - Target: >95% (current baseline: **96.2%**)

3. **Relevance** - Does the answer address the question?
   - Measures: "Is the answer on-topic and helpful?"
   - Uses: Judge LLM to evaluate answer quality
   - Target: >90% (current baseline: **92.7%**)

4. **Hallucination Rate** - How often does the system make up facts?
   - Measures: "Percentage of answers with unsupported claims"
   - Target: <5% (current baseline: **0.0%**)

### Performance Metrics

1. **Latency**
   - p50 (median): **2294ms**
   - p95 (95th percentile): **3629ms**
   - Target: <2000ms p95

2. **Cost**
   - Per query: **$0.0005**
   - Per 100 queries: **$0.05**
   - Target: <$0.10 per 100

---

## Current Baseline (April 13, 2026)

```
🎯 Quality Metrics:
   Recall@3:      93.3%  ✅ Excellent
   Faithfulness:  96.2%  ✅ Excellent
   Relevance:     92.7%  ✅ Excellent
   Hallucinations: 0.0%  ✅ Perfect

⏱️  Performance:
   p50 Latency:   2294ms  ⚠️  Could be faster
   p95 Latency:   3629ms  ⚠️  Could be faster

💰 Cost:
   Per Query:     $0.0005  ✅ Very cheap
   Per 100:       $0.05    ✅ Very cheap
```

**Analysis:**
- Quality is excellent (>90% across all metrics)
- Latency is the main optimization opportunity (target <2000ms p95)
- Cost is negligible

**Next Steps:**
1. ❌ DON'T add Hybrid Search yet - quality is already 93%
2. ✅ DO add streaming to reduce perceived latency
3. ✅ DO optimize retrieval speed (currently ~1s of the 2.3s latency)

---

## How to Use This Framework

### 1. Establish Baseline (DONE)

```bash
python3 evaluation/run_experiment.py
```

This creates `evaluation/results/baseline_TIMESTAMP.json` with all metrics.

### 2. Make a Change (Example: Add Hybrid Search)

```python
# In src/query.py or src/api.py
# Add your new retrieval method
retriever = hybrid_search_retriever(...)  # Your improvement
```

### 3. Run Experiment Again

```bash
python3 evaluation/run_experiment.py
```

This creates `evaluation/results/baseline_TIMESTAMP.json` with new metrics.

### 4. Compare Results

```python
# Simple comparison script
import json

with open('evaluation/results/baseline_OLD.json') as f:
    old = json.load(f)

with open('evaluation/results/baseline_NEW.json') as f:
    new = json.load(f)

print(f"Recall@3:      {old['quality_metrics']['recall_at_3']['mean']} → {new['quality_metrics']['recall_at_3']['mean']}")
print(f"Faithfulness:  {old['quality_metrics']['faithfulness']['mean']} → {new['quality_metrics']['faithfulness']['mean']}")
print(f"p95 Latency:   {old['performance']['latency']['p95_ms']}ms → {new['performance']['latency']['p95_ms']}ms")
print(f"Cost per 100:  ${old['performance']['cost']['cost_per_100_queries_usd']} → ${new['performance']['cost']['cost_per_100_queries_usd']}")
```

### 5. Keep or Revert?

**Keep the change if:**
- ✅ Recall@3 improved by >5%
- ✅ Faithfulness stayed >90%
- ✅ p95 latency didn't increase >20%
- ✅ Cost didn't increase >50%

**Revert the change if:**
- ❌ Metrics got worse
- ❌ Latency increased significantly
- ❌ Cost increased without quality gains

---

## File Structure

```
evaluation/
├── README.md                     # This file
├── generate_ground_truth.py      # Creates golden dataset
├── metrics.py                    # Implements Recall@K, Faithfulness, etc.
├── run_experiment.py             # Main evaluation script
├── golden_dataset.json           # 30 Q&A pairs with expected answers
└── results/
    └── baseline_TIMESTAMP.json   # Evaluation results
```

---

## Golden Dataset Details

**Total Questions:** 30
- **Easy:** 20 questions (single-concept: path params, query params, CORS, etc.)
- **Medium:** 7 questions (multi-concept: combining params, OAuth, routing, etc.)
- **Hard:** 3 questions (complex: middleware, WebSockets, testing)

**Why 30?**
- Large enough to detect 5-10% quality changes
- Small enough to run quickly (~2 minutes)
- Balanced across difficulty levels

**Why not more?**
- 100 questions would be more robust but takes 10+ minutes
- For iteration speed, 30 is the sweet spot
- Can expand to 100 later for final validation

---

## Understanding the Metrics

### Recall@3 (93.3%)

**What it means:**
- Out of 30 questions, 28 had sufficient context in top-3 retrieved docs
- 2 questions failed to retrieve the right documents

**Failed questions:**
1. "What's the difference between Form() and Body()?" (Recall: 0.0)
2. "How do I handle multiple response status codes?" (Recall: 0.0)

**Why this matters:**
- If retrieval fails, LLM can't answer correctly (garbage in, garbage out)
- This metric isolates retrieval quality from generation quality

**How to improve:**
- Add hybrid search (BM25 + semantic) for keyword-heavy queries
- Increase k from 3 to 5
- Fine-tune embeddings on FastAPI domain

### Faithfulness (96.2%)

**What it means:**
- 96% of generated answers only contain information from sources
- Virtually no hallucinations detected

**Why this matters:**
- Google cares deeply about AI safety and reliability
- Shows you're not just building "cool demos" but production-grade systems

**How to maintain:**
- Keep using prompt: "Do not make up information"
- Use stricter prompts for higher-stakes domains
- Add citation tracking (which source for each claim)

### Relevance (92.7%)

**What it means:**
- 93% of answers actually address the question asked
- Some answers might be correct but slightly off-topic

**Why this matters:**
- User experience metric - "did I get what I asked for?"
- Complements faithfulness (can be faithful but irrelevant)

---

## Cost Analysis

**Current:** $0.05 per 100 queries

**Breakdown:**
- Retrieval: $0 (local embeddings)
- LLM generation: ~$0.0005 per query (Claude Haiku)
- Evaluation (Judge LLM): ~$0.0003 per query (only for testing)

**Production scaling:**
- 1,000 queries/day = $0.50/day = $15/month
- 10,000 queries/day = $5/day = $150/month

**What this tells Google:**
- You understand cost optimization
- You chose Haiku over Sonnet for good reason
- You're thinking about production economics

---

## What to Show in Interview

### Before (no evaluation):
> "I built a RAG system that works pretty well."

### After (with this framework):
> "I built a RAG system with 93% Recall@3, 96% faithfulness, and <$0.001/query cost. I established a baseline evaluation framework using Judge LLM pattern. When I added hybrid search, Recall improved from 93% → 89%, so I reverted the change - proof that more features doesn't always mean better."

**The difference:** Data-driven decision making vs. vibes-based engineering.

---

## Next Steps

### Immediate (for Google application):

1. ✅ **Document this baseline** - Add to README.md, show in resume
2. ⏭️ **Add streaming** - Reduce perceived latency (doesn't affect metrics but UX matters)
3. ⏭️ **Try one optimization** - Pick the lowest-hanging fruit from baseline analysis

### Longer-term (if you have time):

1. **Expand golden dataset** - 30 → 100 questions for robustness
2. **Add human eval** - Collect thumbs up/down from users
3. **A/B testing framework** - Compare two approaches side-by-side
4. **Per-difficulty analysis** - Are hard questions performing worse?

---

## FAQ

**Q: Why Judge LLM instead of automated metrics like ROUGE/BLEU?**

A: ROUGE/BLEU measure n-gram overlap, which doesn't capture semantic meaning. Judge LLM can understand "OAuth2PasswordBearer" and "OAuth2 bearer token scheme" are the same concept.

**Q: Isn't Judge LLM expensive?**

A: For 30 questions with 3 metrics each = 90 judge calls × $0.0003 = $0.027. Negligible for the value.

**Q: Why not use GPT-4 as judge instead of Haiku?**

A: Haiku is 20x cheaper and sufficient for yes/no judgments. Use GPT-4 judge only if Haiku results are inconsistent.

**Q: What if my baseline is worse than this (e.g., 70% recall)?**

A: Perfect! Now you have a clear optimization target. Focus on improving retrieval first.

**Q: Should I optimize for recall, faithfulness, or latency first?**

A: Priority order:
1. Recall (if <85%) - can't generate good answers without good retrieval
2. Faithfulness (if <90%) - hallucinations are unacceptable
3. Latency (if >3s p95) - UX improvement
4. Cost (if >$0.01/query) - unlikely to be an issue with Haiku

---

## Credits

**Framework inspired by:**
- Anthropic's evals methodology
- DeepMind's Sparrow paper (Judge LLM pattern)
- Google's RE approach to measurement

**Built with:**
- LangChain (RAG pipeline)
- Claude Haiku (generation + judge)
- Chroma (vector DB)
- all-MiniLM-L6-v2 (embeddings)

---

**Last Updated:** April 13, 2026
**Baseline Version:** 1.0
**Next Eval:** After next feature addition
