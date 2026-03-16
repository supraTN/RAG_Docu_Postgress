import os
import sys
import glob
import json
import re
import tiktoken
from bs4 import BeautifulSoup, NavigableString
from markdownify import markdownify as md
from langchain_text_splitters import RecursiveCharacterTextSplitter


def _find_pg_docs_dir() -> str:
    root = os.path.join(os.path.dirname(__file__), "..")
    candidates = sorted(
        glob.glob(os.path.join(root, "postgresql-*", "doc", "src", "sgml", "html"))
    )
    if not candidates:
        raise FileNotFoundError(
            "No postgresql-*/ folder found at project root.\n"
            "Run scripts/setup.sh (or setup.bat) first, or set POSTGRES_DOCS_DIR."
        )
    return candidates[-1]


INPUT_DIR = os.getenv("POSTGRES_DOCS_DIR") or _find_pg_docs_dir()
OUTPUT_FILE = os.getenv("OUTPUT_FILE", "postgres_rag_data_v8.json")

TARGET_CHUNK_SIZE = 400
CHUNK_OVERLAP = 80
MIN_TOKEN_THRESHOLD = 20
MERGE_THRESHOLD = 200  # chunks below this token count get merged with the next one
MERGE_MAX_TOKENS = 600  # max combined size after merging (1.5x TARGET_CHUNK_SIZE)

SPLIT_MARKER = "SEMANTICSPLITMARKER"
CODE_MARKER_TEMPLATE = "CODEBLOCKX{}X"

encoder = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(encoder.encode(text))


def protect_code_blocks(soup, code_store):
    tags = soup.find_all(["pre", "programlisting"])
    for i, pre_tag in enumerate(tags):
        code_content = pre_tag.get_text()
        placeholder = CODE_MARKER_TEMPLATE.format(i)
        code_store[placeholder] = code_content.strip()
        pre_tag.replace_with(NavigableString(f"\n\n{placeholder}\n\n"))


def inject_semantic_splits(soup):
    for admo in soup.select("div.tip, div.note, div.warning"):
        if admo.next_sibling:
            admo.insert_after(NavigableString(f"\n\n{SPLIT_MARKER}\n\n"))
        else:
            admo.parent.append(NavigableString(f"\n\n{SPLIT_MARKER}\n\n"))

    for el in soup.select("dl, div.variablelist, div.sect2"):
        el.insert_before(NavigableString(f"\n\n{SPLIT_MARKER}\n\n"))


def restore_code_blocks(text: str, code_store: dict[str, str]) -> str:
    def restore_code_match(match):
        key = match.group(0)
        code_content = code_store.get(key.strip(), "")
        return f"\n```sql\n{code_content}\n```\n"

    return re.sub(r"CODEBLOCKX\d+X", restore_code_match, text)


def finalize_text(text: str) -> str:
    text = re.sub(r"\[#\]\(#.*?\)", "", text)
    text = text.replace(SPLIT_MARKER, "")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def is_bad_chunk(text: str) -> bool:
    stripped = text.strip()

    if not stripped:
        return True

    if stripped == "\\":
        return True

    lines = [line.strip() for line in stripped.splitlines() if line.strip()]

    if not lines:
        return True

    # heading seul
    if len(lines) == 1 and lines[0].startswith("#"):
        return True

    # option seule, sans explication
    if len(lines) <= 2 and re.match(r"^`-{1,2}[^`]+`$", lines[0]):
        return True

    return False


def extract_section_label(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for line in lines[:10]:
        if line.startswith("#"):
            return re.sub(r"^#+\s*", "", line).strip()

    for line in lines[:10]:
        if re.match(r"^`-{1,2}[A-Za-z0-9][^`]*`", line):
            return line.strip("` ").strip()

    for line in lines[:10]:
        if re.match(r"^\*\*Example", line, re.IGNORECASE):
            return re.sub(r"^\*\*|\*\*$", "", line).strip()

    return ""


def merge_small_chunks(chunks: list[str]) -> list[str]:
    """Merge consecutive small chunks (< MERGE_THRESHOLD tokens) with their neighbor.

    This avoids tiny standalone chunks like a synopsis or heading+one line
    that pollute retrieval results without carrying enough context.
    Merges when EITHER the current buffer OR the next chunk is small,
    as long as the combined size stays under MERGE_MAX_TOKENS.
    """
    if len(chunks) <= 1:
        return chunks

    merged = []
    buffer = chunks[0]

    for i in range(1, len(chunks)):
        buf_tokens = count_tokens(buffer)
        next_tokens = count_tokens(chunks[i])
        either_small = buf_tokens < MERGE_THRESHOLD or next_tokens < MERGE_THRESHOLD
        fits = (buf_tokens + next_tokens) <= MERGE_MAX_TOKENS

        if either_small and fits:
            buffer = buffer.rstrip() + "\n\n" + chunks[i].lstrip()
        else:
            merged.append(buffer)
            buffer = chunks[i]

    merged.append(buffer)
    return merged


def build_embedding_text(title: str, source: str, section: str, content: str) -> str:
    parts = [f"Page title: {title}", f"Source file: {source}"]
    if section:
        parts.append(f"Section: {section}")
    return "\n".join(parts) + "\n\n" + content


def process_files():
    final_data = []

    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        model_name="gpt-3.5-turbo",
        chunk_size=TARGET_CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=[
            "\n## ",
            "\n### ",
            "\n#### ",
            "\n\n",
            "\n",
            ". ",
            " ",
        ],
    )

    if not os.path.exists(INPUT_DIR):
        print(f"Error: directory {INPUT_DIR} not found.")
        return

    files = glob.glob(os.path.join(INPUT_DIR, "*.html"))
    print(f"Processing {len(files)} HTML files...")

    for file_path in files:
        filename = os.path.basename(file_path)

        with open(file_path, "r", encoding="utf-8") as f:
            raw_html = f.read()

        soup = BeautifulSoup(raw_html, "html.parser")

        for noise in soup.select("div.navheader, div.navfooter, div.toc, script, style"):
            noise.decompose()

        title_tag = soup.find("title")
        title = title_tag.get_text().strip() if title_tag else "Unknown"

        code_store = {}
        protect_code_blocks(soup, code_store)
        inject_semantic_splits(soup)

        content_div = soup.find("div", id="docContent") or soup.find("body")
        if not content_div:
            continue

        md_text = md(
            str(content_div),
            heading_style="ATX",
            newline_style="BACKSLASH",
            code_language="",
        )

        raw_blocks = re.split(r"\s*" + re.escape(SPLIT_MARKER) + r"\s*", md_text)

        chunk_counter = 0

        for block in raw_blocks:
            block = block.strip()
            if not block:
                continue

            sub_chunks = text_splitter.split_text(block)
            sub_chunks = merge_small_chunks(sub_chunks)

            for sub in sub_chunks:
                sub = restore_code_blocks(sub, code_store)
                cleaned_content = finalize_text(sub)

                if is_bad_chunk(cleaned_content):
                    continue

                raw_token_count = count_tokens(cleaned_content)
                if raw_token_count < MIN_TOKEN_THRESHOLD:
                    continue

                section = extract_section_label(cleaned_content)
                embedding_text = build_embedding_text(
                    title=title,
                    source=filename,
                    section=section,
                    content=cleaned_content,
                )

                final_data.append(
                    {
                        "id": f"{filename}_{chunk_counter}",
                        "source": filename,
                        "title": title,
                        "section": section,
                        "content": cleaned_content,
                        "embedding_text": embedding_text,
                        "token_count": raw_token_count,
                        "type": "text_block",
                    }
                )
                chunk_counter += 1

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)

    print(f"Done. {len(final_data)} chunks written to {OUTPUT_FILE}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        INPUT_DIR = sys.argv[1]
    process_files()