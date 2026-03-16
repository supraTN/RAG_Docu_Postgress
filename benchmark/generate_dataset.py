"""
Eval Dataset Generator
======================
Correct approach to build a RAG evaluation dataset:

    chunk (from docs) → LLM → { question, expected_answer, source_chunk_id }

The ground truth is derived from a documentation chunk, NOT from the retriever.
This ensures retrieval and generation evaluations are fully unbiased.

Each generated Q&A pair goes through a SELF-CONTAINMENT VALIDATION step:
the LLM re-reads only the chunk and judges whether the question can be answered
from it alone. Pairs that fail this check are flagged or discarded.

This catches bad chunks (too short, split mid-concept) before they pollute the dataset.

Usage:
    python generate_dataset.py                    # 40 chunks, auto-validates
    python generate_dataset.py --n 60             # more questions
    python generate_dataset.py --min-tokens 80    # only richer chunks
    python generate_dataset.py --no-validate      # skip validation (faster)
    python generate_dataset.py --chunk-report     # print chunk quality stats only
"""

import sys
import json
import random
import argparse
from pathlib import Path

BACKEND_DIR = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import rag_service
from langchain_core.messages import SystemMessage, HumanMessage

# ─────────────────────────────────────────────
#  Config
# ─────────────────────────────────────────────

CHUNKS_FILE = Path(__file__).parent.parent / "scripts" / "postgres_rag_data_v8.json"
DEFAULT_OUTPUT = Path(__file__).parent / "eval_dataset.json"

QA_GENERATION_PROMPT = """\
You are building a QA evaluation dataset for a PostgreSQL documentation chatbot.

Given the documentation excerpt below, generate exactly ONE question and its expected answer such that:
1. The question can be answered COMPLETELY from the excerpt alone — no outside knowledge needed.
2. The question is specific and technical (not vague like "what is PostgreSQL?").
3. The expected answer is 1-3 sentences, strictly derived from the excerpt.
4. Do NOT copy entire sentences verbatim — rephrase in your own words.

Respond ONLY with valid JSON, no markdown fences:
{"question": "...", "answer": "..."}
"""

QA_USERSTYLE_PROMPT = """\
You are building a realistic user-query dataset for a PostgreSQL documentation chatbot.

Given the documentation excerpt below, generate exactly ONE question and its expected answer.

Requirements:
1. The question must be answerable completely from the excerpt alone.
2. The question should sound like something a real user would ask in practice.
3. Prefer practical wording such as "how do I...", "how can I...", "what command do I use to...", or simple troubleshooting questions.
4. The question may be informal, but it must remain clear and answerable.
5. Avoid copying the wording of the excerpt too closely.
6. The expected answer must be 1-3 sentences and strictly derived from the excerpt.

Examples of good user-style questions:
- how do i start postgres?
- what command do i use to change the stopword list?
- how can i restore a table with row security enabled?
- what's the difference between search and ordering operators?
- comment changer la liste de stopwords d’un dictionnaire de recherche plein texte ?

Respond ONLY with valid JSON:
{"question": "...", "answer": "..."}
"""

VALIDATION_PROMPT = """\
You are a strict QA validator.

Read the documentation excerpt below and the question/answer pair.
Decide whether the question can be answered FULLY and CORRECTLY from the excerpt alone,
without needing any information from outside the excerpt.

Respond with a single JSON object:
{"self_contained": true/false, "reason": "one sentence explanation"}

- true  → the excerpt contains all the information needed to answer the question correctly.
- false → the question requires context that is missing from this excerpt (chunk too short,
          concept cut mid-way, answer references something not in this excerpt).
"""

# ─────────────────────────────────────────────
#  Chunk loading & quality report
# ─────────────────────────────────────────────

def load_chunks(min_tokens: int) -> tuple[list[dict], list[dict]]:
    if not CHUNKS_FILE.exists():
        raise FileNotFoundError(
            f"Chunks file not found: {CHUNKS_FILE}\n"
            "Run script/pdf6.py first to generate the chunks."
        )
    with open(CHUNKS_FILE, encoding="utf-8") as f:
        all_chunks = json.load(f)

    filtered = [c for c in all_chunks if c.get("token_count", 0) >= min_tokens]
    return all_chunks, filtered


def print_chunk_report(all_chunks: list[dict]):
    """Print chunk quality statistics to help diagnose chunking issues."""
    tokens = [c.get("token_count", 0) for c in all_chunks]
    total = len(tokens)

    buckets = {
        "< 20 tokens  (noise)":       sum(1 for t in tokens if t < 20),
        "20–49 tokens (very short)":  sum(1 for t in tokens if 20 <= t < 50),
        "50–99 tokens (short)":       sum(1 for t in tokens if 50 <= t < 100),
        "100–200 tokens (good)":      sum(1 for t in tokens if 100 <= t < 200),
        "200–400 tokens (ideal)":     sum(1 for t in tokens if 200 <= t < 400),
        "> 400 tokens (large)":       sum(1 for t in tokens if t >= 400),
    }

    avg = sum(tokens) / total
    median = sorted(tokens)[total // 2]

    print("\n── Chunk Quality Report ─────────────────────────────────────────")
    print(f"  Total chunks   : {total}")
    print(f"  Average tokens : {avg:.1f}")
    print(f"  Median tokens  : {median}")
    print(f"  Min / Max      : {min(tokens)} / {max(tokens)}")
    print()
    print(f"  {'Range':<30} {'Count':>6}  {'% of total':>10}  Bar")
    print(f"  {'─' * 65}")
    for label, count in buckets.items():
        pct = count / total * 100
        bar = "█" * int(pct / 2)
        print(f"  {label:<30} {count:>6}  {pct:>9.1f}%  {bar}")

    noise_pct = buckets["< 20 tokens  (noise)"] / total * 100
    short_pct = (buckets["< 20 tokens  (noise)"] + buckets["20–49 tokens (very short)"]) / total * 100

    print()
    if noise_pct > 5:
        print(f"  ⚠ {noise_pct:.1f}% of chunks are noise (< 20 tokens). Consider raising MIN_TOKEN_THRESHOLD in pdf6.py.")
    if short_pct > 20:
        print(f"  ⚠ {short_pct:.1f}% of chunks are < 50 tokens. Many may be incomplete concepts.")
        print(f"    → Try increasing TARGET_CHUNK_SIZE or CHUNK_OVERLAP in pdf6.py.")
    if avg < 80:
        print(f"  ⚠ Average chunk size is low ({avg:.0f} tokens). Chunks may lack sufficient context for retrieval.")
    if avg > 350:
        print(f"  ⚠ Average chunk size is high ({avg:.0f} tokens). Consider reducing TARGET_CHUNK_SIZE.")

    print("─" * 67 + "\n")

# ─────────────────────────────────────────────
#  Chunk helpers
# ─────────────────────────────────────────────

def _parse_chunk_index(chunk_id: str) -> tuple[str, int] | tuple[None, None]:
    try:
        parts = chunk_id.rsplit("_", 1)
        return parts[0], int(parts[1])
    except (ValueError, IndexError):
        return None, None


def build_acceptable_chunk_ids(chunk: dict, all_chunks: list[dict], window: int = 1) -> list[str]:
    """
    Return source chunk ±window adjacent chunks from the same file.
    This reduces false misses when the answer spans chunk boundaries.
    """
    source_id = chunk["id"]
    source_file, source_idx = _parse_chunk_index(source_id)

    if source_file is None:
        return [source_id]

    acceptable = []
    for c in all_chunks:
        cid = c.get("id", "")
        c_file, c_idx = _parse_chunk_index(cid)
        if c_file == source_file and c_idx is not None and abs(c_idx - source_idx) <= window:
            acceptable.append(cid)

    return sorted(set(acceptable), key=lambda x: _parse_chunk_index(x)[1] if _parse_chunk_index(x)[1] is not None else 10**9)

# ─────────────────────────────────────────────
#  Q&A generation
# ─────────────────────────────────────────────

def _parse_json_response(raw) -> dict | None:
    if isinstance(raw, list):
        raw = next((b["text"] for b in raw if isinstance(b, dict) and b.get("type") == "text"), "")
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:]).rstrip("`").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def generate_qa_from_chunk(chunk: dict, all_chunks: list[dict], style: str = "technical") -> dict | None:
    """Generate a (question, answer) pair strictly from a single chunk."""
    prompt = QA_USERSTYLE_PROMPT if style == "userstyle" else QA_GENERATION_PROMPT
    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content=chunk["content"]),
    ]
    response = rag_service.llm.invoke(messages)
    parsed = _parse_json_response(response.content)

    if not parsed:
        return None

    question = parsed.get("question", "").strip()
    answer = parsed.get("answer", "").strip()

    if not question or not answer:
        return None

    return {
        "question": question,
        "expected_answer": answer,
        "source_chunk_id": chunk["id"],
        "acceptable_chunk_ids": build_acceptable_chunk_ids(chunk, all_chunks, window=1),
        "source_chunk_content": chunk["content"],
        "source_file": chunk["source"],
        "source_title": chunk["title"],
        "source_url": rag_service.BASE_DOC_URL + chunk["source"],
        "token_count": chunk["token_count"],
    }

# ─────────────────────────────────────────────
#  Self-containment validation
# ─────────────────────────────────────────────

def is_bad_userstyle_chunk(chunk: dict) -> bool:
    source = chunk.get("source", "")
    title = (chunk.get("title") or "").lower()
    content = (chunk.get("content") or "").lower()

    bad_sources = {
        "bookindex.html",
        "release-16.html",
        "sql-keywords-appendix.html",
        "release-16-10.html",
        "features-sql-standard.html",
        "unsupported-features-sql-standard.html",
    }

    if source in bad_sources:
        return True

    if title.startswith("index"):
        return True
    if "appendix" in title:
        return True
    if "release " in title:
        return True

    pipe_count = content.count("|")
    if pipe_count > 20:
        return True

    return False

def validate_self_containment(item: dict) -> tuple[bool, str]:
    """
    Ask the LLM: given ONLY this chunk, can the question be answered?
    Returns (is_valid, reason).
    A False result indicates a chunking boundary problem:
    the concept was cut mid-way and the chunk lacks the necessary context.
    """
    prompt = (
        f"Documentation excerpt:\n{item['source_chunk_content']}\n\n"
        f"Question: {item['question']}\n"
        f"Answer: {item['expected_answer']}"
    )
    messages = [
        SystemMessage(content=VALIDATION_PROMPT),
        HumanMessage(content=prompt),
    ]
    response = rag_service.llm.invoke(messages)
    parsed = _parse_json_response(response.content)

    if not parsed:
        return True, "validation_parse_error"

    return bool(parsed.get("self_contained", True)), parsed.get("reason", "")

# ─────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Generate a RAG evaluation dataset from indexed PostgreSQL documentation chunks."
    )
    parser.add_argument("--n", type=int, default=40,
                        help="Number of Q&A pairs to generate (default: 40).")
    parser.add_argument("--min-tokens", type=int, default=60,
                        help="Minimum token count per chunk (default: 60). Raise to avoid short, incomplete chunks.")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for reproducibility (default: 42).")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help="Output JSON file.")
    parser.add_argument("--no-validate", action="store_true",
                        help="Skip self-containment validation (faster, but may include bad chunks).")
    parser.add_argument("--keep-invalid", action="store_true",
                        help="Keep Q&A pairs that fail validation (flagged with _valid=false).")
    parser.add_argument("--chunk-report", action="store_true",
                        help="Print chunk quality statistics and exit.")
    parser.add_argument("--style", choices=["technical", "userstyle"], default="technical",
                        help="Question style: 'technical' (default) or 'userstyle' (natural language).")
    args = parser.parse_args()

    if args.output == DEFAULT_OUTPUT and args.style == "userstyle":
        args.output = Path(__file__).parent / "eval_dataset_userstyle.json"

    print(f"Loading chunks from {CHUNKS_FILE.name}...")
    all_chunks, filtered = load_chunks(min_tokens=args.min_tokens)

    filtered = [c for c in filtered if not is_bad_userstyle_chunk(c)]

    if args.chunk_report:
        print_chunk_report(all_chunks)
        return

    print_chunk_report(all_chunks)

    print(f"  {len(filtered)} chunks with token_count >= {args.min_tokens} available for sampling")
    random.seed(args.seed)
    sampled = random.sample(filtered, min(args.n, len(filtered)))
    print(f"  Sampled {len(sampled)} chunks (seed={args.seed})\n")

    print("── Step 1/2 : Generating Q&A pairs from chunks ─────────────────")
    raw_items = []
    gen_failed = 0

    for i, chunk in enumerate(sampled):
        print(f"  [{i + 1:>2}/{len(sampled)}] {chunk['source']} ({chunk['token_count']} tokens)")

        item = generate_qa_from_chunk(chunk, all_chunks, style=args.style)
        if item is None:
            print(f"           ⚠ Invalid LLM output — skipping")
            gen_failed += 1
            continue

        print(f"           Q: {item['question'][:75]}...")
        raw_items.append(item)

    dataset = []
    flagged = []
    val_failed = 0

    if not args.no_validate:
        print(f"\n── Step 2/2 : Validating self-containment ({len(raw_items)} pairs) ─────")
        print("  (Checks that each question is answerable from its chunk alone)")
        print("  A 'false' result = chunk is missing context = chunking boundary issue\n")

        for i, item in enumerate(raw_items):
            is_valid, reason = validate_self_containment(item)
            item["_valid"] = is_valid
            item["_validation_reason"] = reason

            status = "OK  " if is_valid else "FAIL"
            print(f"  [{i + 1:>2}/{len(raw_items)}] {status}  {item['question'][:65]}...")
            if not is_valid:
                print(f"            → {reason}")
                val_failed += 1
                flagged.append(item)
                if args.keep_invalid:
                    dataset.append(item)
            else:
                dataset.append(item)
    else:
        dataset = raw_items
        print("\n  Validation skipped (--no-validate)")

    print(f"\n{'─' * 65}")
    print(f"  Generated         : {len(raw_items)} Q&A pairs from {len(sampled)} chunks")
    if gen_failed:
        print(f"  LLM parse errors  : {gen_failed} skipped")
    if not args.no_validate:
        print(f"  Passed validation : {len(dataset)} pairs")
        if val_failed:
            print(f"  Failed validation : {val_failed} pairs (chunking boundary issues)")
            if not args.keep_invalid:
                print(f"                     → excluded from dataset (use --keep-invalid to keep them)")
    print(f"{'─' * 65}")

    if flagged and not args.keep_invalid:
        flagged_path = args.output.parent / "flagged_chunks.json"
        with open(flagged_path, "w", encoding="utf-8") as f:
            json.dump(flagged, f, ensure_ascii=False, indent=2)
        print(f"\n  Flagged chunks saved → {flagged_path}")
        print(f"  Review these to improve your chunking strategy")

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    print(f"\n  Dataset saved → {args.output}  ({len(dataset)} questions)")
    print(f"\n  Each entry has 'source_url' — verify expected_answer against the actual docs.")
    print(f"  Next step: python evaluate.py")


if __name__ == "__main__":
    main()