"""
RAG Evaluation Script
=====================
Evaluates the RAG pipeline on two independent axes:

  RETRIEVAL (no LLM needed, cheap & fast)
  ─────────────────────────────────────────
  Hit Rate @k  — % of questions where an acceptable chunk appears in top-k results.
                 k=1, k=3, k=5 are reported.
  MRR          — Mean Reciprocal Rank. Average of 1/rank of the acceptable chunk.
                 1.0 = always first. 0.0 = never found.
  Boundary Hit — % of failed retrievals where an ADJACENT chunk (same file, ±2 index)
                 was retrieved instead. High value → chunking boundary problem,
                 not a pure retrieval problem.

  GENERATION (uses RAGAS + OpenAI, has a cost)
  ─────────────────────────────────────────────
  Faithfulness      — Answer is grounded in the retrieved chunks (no hallucination).
  Answer Relevancy  — Answer actually addresses the question.

Usage:
    python evaluate.py
    python evaluate.py --retrieval-only
    python evaluate.py --dataset eval_dataset.json
    python evaluate.py --top-k 10
    python evaluate.py --limit 10
    python evaluate.py --skip-answer-relevancy
    python evaluate.py --judge-model gpt-4.1-mini
    python evaluate.py --output results.json
"""

import sys
import json
import time
import argparse
import os
from pathlib import Path
from datetime import datetime

BACKEND_DIR = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from models import QuestionRequest
import rag_service

DEFAULT_DATASET = Path(__file__).parent / "eval_dataset.json"
DEFAULT_OUTPUT = Path(__file__).parent / "evaluation_results.json"


def _parse_chunk_index(chunk_id: str) -> tuple[str, int] | tuple[None, None]:
    """
    Extract (source_file, index) from a chunk id like 'mvcc.html_3'.
    Returns (None, None) if the format is unexpected.
    """
    try:
        parts = chunk_id.rsplit("_", 1)
        return parts[0], int(parts[1])
    except (ValueError, IndexError):
        return None, None


def _is_adjacent(source_id: str, retrieved_id: str, window: int = 2) -> bool:
    """
    Return True if retrieved_id is from the same file and within ±window
    index positions of source_id.
    e.g. source='mvcc.html_3', retrieved='mvcc.html_5', window=2 → True
    """
    src_file, src_idx = _parse_chunk_index(source_id)
    ret_file, ret_idx = _parse_chunk_index(retrieved_id)

    if src_file is None or ret_file is None:
        return False
    if src_file != ret_file:
        return False
    return abs(src_idx - ret_idx) <= window


def evaluate_retrieval(dataset: list[dict], top_k: int = 5) -> dict:
    """
    For each question, run the vector search and check whether an acceptable chunk
    appears in the top-k results. Computes Hit Rate @1/3/5, MRR, and Boundary Hit Rate.
    """
    hits = {1: 0, 3: 0, top_k: 0}
    reciprocal_ranks = []
    boundary_hits = 0
    missed = 0
    details = []

    total = len(dataset)
    for i, item in enumerate(dataset):
        question = item["question"]
        source_id = item["source_chunk_id"]
        acceptable_ids = set(item.get("acceptable_chunk_ids", [source_id]))

        fetch_k = top_k * 8 if rag_service.RERANKER_ENABLED else top_k
        docs_and_scores = rag_service.vectorstore.similarity_search_with_relevance_scores(
            question, fetch_k
        )
        if rag_service.RERANKER_ENABLED:
            docs_and_scores = rag_service.rerank_docs(question, docs_and_scores)[:top_k]

        retrieved_ids = [doc.metadata.get("id", "") for doc, _ in docs_and_scores]
        retrieved_scores = [round(score, 4) for _, score in docs_and_scores]

        rank = 0
        matched_chunk_id = None
        for pos, doc_id in enumerate(retrieved_ids, start=1):
            if doc_id in acceptable_ids:
                rank = pos
                matched_chunk_id = doc_id
                break

        found = rank > 0
        rr = 1.0 / rank if found else 0.0
        reciprocal_ranks.append(rr)

        for k in hits:
            if found and rank <= k:
                hits[k] += 1

        boundary_hit = False
        if not found:
            missed += 1
            boundary_hit = any(_is_adjacent(source_id, rid) for rid in retrieved_ids)
            if boundary_hit:
                boundary_hits += 1

        details.append({
            "question": question,
            "source_chunk_id": source_id,
            "acceptable_chunk_ids": sorted(acceptable_ids),
            "matched_chunk_id": matched_chunk_id,
            "source_file": item["source_file"],
            "rank": rank,
            "found_in_top_k": found,
            "boundary_hit": boundary_hit,
            "top_retrieved_ids": retrieved_ids[:3],
            "top_scores": retrieved_scores[:3],
        })

        if found:
            status = f"rank {rank:<2}"
        elif boundary_hit:
            status = "BOUNDARY HIT"
        else:
            status = "MISS        "

        print(f"  [{i + 1:>2}/{total}] {status}  {question[:60]}...")

    mrr = sum(reciprocal_ranks) / total if total else 0.0
    boundary_rate = boundary_hits / missed if missed > 0 else 0.0

    return {
        "hit_rate_at_1": round(hits[1] / total, 4),
        "hit_rate_at_3": round(hits[3] / total, 4),
        f"hit_rate_at_{top_k}": round(hits[top_k] / total, 4),
        "mrr": round(mrr, 4),
        "boundary_hit_rate": round(boundary_rate, 4),
        "_boundary_hits": boundary_hits,
        "_missed": missed,
        "details": details,
    }


def evaluate_generation(
    dataset: list[dict],
    judge_model: str,
    skip_answer_relevancy: bool = False,
) -> dict:
    """
    Run the full RAG pipeline on each question, collect (answer, contexts),
    then score with RAGAS faithfulness and answer relevancy.
    """
    questions, answers, contexts = [], [], []

    total = len(dataset)
    for i, item in enumerate(dataset):
        question = item["question"]
        req = QuestionRequest(message=question)

        docs_and_scores = rag_service.get_embedding_score(req)
        valid_docs, _ = rag_service._select_valid_docs_and_sources(docs_and_scores)
        chunk_texts = [doc.page_content for doc in valid_docs]
        result = rag_service.generate_answer_with_score(req, docs_and_scores=docs_and_scores)

        questions.append(question)
        answers.append(result.answer)
        contexts.append(chunk_texts if chunk_texts else ["No relevant context found."])

        print(f"  [{i + 1:>2}/{total}] {len(chunk_texts)} chunk(s) retrieved  {question[:60]}...")

    from openai import AsyncOpenAI
    from ragas.metrics.collections import Faithfulness, AnswerRelevancy
    from ragas.llms import llm_factory
    from ragas.embeddings import OpenAIEmbeddings as RagasOpenAIEmbeddings

    openai_client = AsyncOpenAI(api_key=rag_service.OPENAI_API_KEY)
    ragas_llm = llm_factory(judge_model, client=openai_client, max_tokens=4096)
    ragas_embeddings = RagasOpenAIEmbeddings(
        client=openai_client, model=rag_service.EMBEDDING_MODEL
    )

    faithfulness_metric = Faithfulness(llm=ragas_llm)
    relevancy_metric = None
    if not skip_answer_relevancy:
        relevancy_metric = AnswerRelevancy(llm=ragas_llm, embeddings=ragas_embeddings, strictness=1)

    faith_inputs = [
        {"user_input": q, "response": a, "retrieved_contexts": ctx}
        for q, a, ctx in zip(questions, answers, contexts)
    ]
    relev_inputs = [
        {"user_input": q, "response": a}
        for q, a in zip(questions, answers)
    ]

    batch_size = 5
    faith_results, relev_results = [], []
    for i in range(0, len(faith_inputs), batch_size):
        faith_results += faithfulness_metric.batch_score(faith_inputs[i:i + batch_size])
        if relevancy_metric is not None:
            relev_results += relevancy_metric.batch_score(relev_inputs[i:i + batch_size])
        print(f"  RAGAS scored {min(i + batch_size, len(faith_inputs))}/{len(faith_inputs)} questions...")

    faithfulness_score = sum(r.value for r in faith_results) / len(faith_results)
    scores = {
        "faithfulness": round(faithfulness_score, 4),
    }
    if relev_results:
        relevancy_score = sum(r.value for r in relev_results) / len(relev_results)
        scores["answer_relevancy"] = round(relevancy_score, 4)
    return scores


METRIC_META = {
    "hit_rate_at_1":       ("Hit Rate @1",       "Acceptable chunk ranked 1st"),
    "hit_rate_at_3":       ("Hit Rate @3",       "Acceptable chunk in top 3"),
    "hit_rate_at_5":       ("Hit Rate @5",       "Acceptable chunk in top 5"),
    "hit_rate_at_10":      ("Hit Rate @10",      "Acceptable chunk in top 10"),
    "mrr":                 ("MRR",               "Mean Reciprocal Rank"),
    "boundary_hit_rate":   ("Boundary Hit Rate", "Misses where adjacent chunk found → chunking issue"),
    "faithfulness":        ("Faithfulness",      "Answer grounded in retrieved chunks"),
    "answer_relevancy":    ("Answer Relevancy",  "Answer addresses the question"),
}


def score_label(score: float) -> str:
    if score >= 0.75:
        return "GOOD"
    if score >= 0.50:
        return "OK  "
    return "POOR"


def print_report(retrieval: dict | None, generation: dict | None, n: int, elapsed: float):
    W = 76
    print("\n" + "=" * W)
    print("  RAG EVALUATION REPORT — PostgreSQL Docs Assistant")
    print("=" * W)
    print(f"  Questions : {n}   |   Total time : {elapsed:.1f}s   |   {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    def print_section(title: str, scores: dict):
        print(f"\n  ── {title} {'─' * (W - 6 - len(title))}")
        print(f"  {'Metric':<25} {'Description':<36} {'Score':>6}  Bar")
        print(f"  {'─' * (W - 2)}")
        for key, value in scores.items():
            if key.startswith("_") or key == "details" or not isinstance(value, float):
                continue
            name, desc = METRIC_META.get(key, (key, ""))
            bar = "█" * int(value * 20) + "░" * (20 - int(value * 20))
            label = score_label(value)
            print(f"  {name:<25} {desc:<36} {value:>5.3f}  {bar}  {label}")

    if retrieval:
        print_section("RETRIEVAL", retrieval)
    if generation:
        print_section("GENERATION (RAGAS)", generation)

    print(f"\n  ── Diagnosis {'─' * (W - 14)}")
    issues_found = False

    if retrieval:
        if "hit_rate_at_5" in retrieval:
            hit_k = retrieval["hit_rate_at_5"]
            hit_k_name = "Hit Rate @5"
        elif "hit_rate_at_10" in retrieval:
            hit_k = retrieval["hit_rate_at_10"]
            hit_k_name = "Hit Rate @10"
        else:
            hit_k = retrieval.get("hit_rate_at_3", retrieval.get("hit_rate_at_1", 1.0))
            hit_k_name = "retrieval hit rate"

        boundary = retrieval.get("boundary_hit_rate", 0.0)
        missed = retrieval.get("_missed", 0)
        boundary_hits = retrieval.get("_boundary_hits", 0)

        if hit_k < 0.5:
            issues_found = True
            if boundary > 0.4:
                print(f"  ⚠ CHUNKING PROBLEM : {boundary*100:.0f}% of misses retrieved an adjacent chunk.")
                print(f"    The right content exists but was split across chunk boundaries.")
                print(f"    → Try increasing CHUNK_OVERLAP or TARGET_CHUNK_SIZE in pdf6.py.")
            else:
                print(f"  ⚠ RETRIEVAL PROBLEM : {hit_k_name} is low ({hit_k:.2f}) and adjacent chunks were rarely found.")
                print(f"    The embedding model may not be capturing semantic similarity well.")
                print(f"    → Check that EMBEDDING_MODEL is appropriate for technical PostgreSQL content.")
        elif boundary > 0.3 and missed > 0:
            issues_found = True
            print(f"  ⚠ PARTIAL CHUNKING ISSUE : {boundary_hits}/{missed} misses found adjacent chunks.")
            print(f"    Some concepts are split across boundaries. Not critical but worth investigating.")
            print(f"    → Consider slightly increasing CHUNK_OVERLAP in pdf6.py.")

    if generation:
        faith = generation.get("faithfulness", generation.get("Faithfulness", 1.0))
        if isinstance(faith, float) and faith < 0.6:
            issues_found = True
            print(f"  ⚠ HALLUCINATION RISK : Faithfulness is low ({faith:.2f}).")
            print(f"    The LLM generates content not grounded in the retrieved chunks.")
            print(f"    → Tighten SYSTEM_PROMPT rules or increase SIMILARITY_THRESHOLD.")

    if not issues_found:
        print(f"  ✓ No major issues detected.")

    print("=" * W)


def save_results(retrieval: dict | None, generation: dict | None, n: int, output: Path):
    out = {
        "timestamp": datetime.now().isoformat(),
        "n_questions": n,
        "retrieval": retrieval,
        "generation": generation,
    }
    with open(output, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n  Results saved → {output}")


def main():
    default_judge_model = os.getenv("BENCHMARK_JUDGE_MODEL", rag_service.LLM_MODEL)
    parser = argparse.ArgumentParser(description="Evaluate the PostgreSQL RAG pipeline.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET,
                        help="eval_dataset.json produced by generate_dataset.py")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--top-k", type=int, default=5,
                        help="Number of chunks retrieved during evaluation (default: 5)")
    parser.add_argument("--retrieval-only", action="store_true",
                        help="Skip RAGAS generation evaluation (faster, no extra API cost)")
    parser.add_argument("--judge-model", default=default_judge_model,
                        help="Model used by RAGAS to score outputs. Defaults to BENCHMARK_JUDGE_MODEL or LLM_MODEL.")
    parser.add_argument("--skip-answer-relevancy", action="store_true",
                        help="Score faithfulness only to reduce evaluation cost.")
    parser.add_argument("--limit", type=int, default=None,
                        help="Only evaluate the first N questions (useful for quick testing)")
    args = parser.parse_args()

    if not args.dataset.exists():
        print(f"ERROR: Dataset not found: {args.dataset}")
        print("Run generate_dataset.py first.")
        sys.exit(1)

    with open(args.dataset, encoding="utf-8") as f:
        dataset = json.load(f)

    if args.limit is not None:
        dataset = dataset[:args.limit]

    print(f"\nPostgreSQL RAG Evaluation")
    print(f"  Dataset   : {args.dataset.name}  ({len(dataset)} questions)")
    print(f"  Answer    : {rag_service.LLM_MODEL}")
    print(f"  Judge     : {args.judge_model}")
    print(f"  Embedding : {rag_service.EMBEDDING_MODEL}")
    print(f"  Threshold : {rag_service.SIMILARITY_THRESHOLD}")
    print(f"  Top-k     : {args.top_k}\n")

    t_start = time.time()

    print("── Step 1/2 : Retrieval evaluation ─────────────────────────────")
    retrieval_scores = evaluate_retrieval(dataset, top_k=args.top_k)

    generation_scores = None
    if not args.retrieval_only:
        print("\n── Step 2/2 : Generation evaluation (RAGAS) ─────────────────────")
        print("  (Calls OpenAI API for each metric — see ragas docs for cost estimate)\n")
        generation_scores = evaluate_generation(
            dataset,
            judge_model=args.judge_model,
            skip_answer_relevancy=args.skip_answer_relevancy,
        )

    elapsed = time.time() - t_start

    print_report(retrieval_scores, generation_scores, len(dataset), elapsed)
    save_results(retrieval_scores, generation_scores, len(dataset), args.output)


if __name__ == "__main__":
    main()