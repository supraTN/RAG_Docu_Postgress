import os
import sys
import glob
import json
import re
import tiktoken
from bs4 import BeautifulSoup, NavigableString
from markdownify import markdownify as md
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Set INPUT_DIR via env var or first CLI argument.
# Auto-detects any postgresql-*/ folder at the project root if not specified.
def _find_pg_docs_dir() -> str:
    root = os.path.join(os.path.dirname(__file__), "..")
    candidates = sorted(glob.glob(os.path.join(root, "postgresql-*", "doc", "src", "sgml", "html")))
    if not candidates:
        raise FileNotFoundError(
            "No postgresql-*/ folder found at project root.\n"
            "Run scripts/setup.sh (or setup.bat) first, or set POSTGRES_DOCS_DIR."
        )
    return candidates[-1]  # pick latest version if multiple

INPUT_DIR = os.getenv("POSTGRES_DOCS_DIR") or _find_pg_docs_dir()
OUTPUT_FILE = os.getenv("OUTPUT_FILE", "postgres_rag_data_v6_perfect.json")
TARGET_CHUNK_SIZE = 400
CHUNK_OVERLAP = 50
MIN_TOKEN_THRESHOLD = 20

SPLIT_MARKER = "SEMANTICSPLITMARKER"
CODE_MARKER_TEMPLATE = "CODEBLOCKX{}X"

encoder = tiktoken.get_encoding("cl100k_base")

def count_tokens(text):
    return len(encoder.encode(text))

def protect_code_blocks(soup, code_store):
    tags = soup.find_all(['pre', 'programlisting'])
    for i, pre_tag in enumerate(tags):
        code_content = pre_tag.get_text()
        placeholder = CODE_MARKER_TEMPLATE.format(i)
        code_store[placeholder] = code_content.strip()
        # Surround with whitespace so the splitter can cut around the placeholder
        pre_tag.replace_with(NavigableString(f"\n\n {placeholder} \n\n"))

def inject_semantic_splits(soup):
    for admo in soup.select('div.tip, div.note, div.warning'):
        if admo.next_sibling:
            admo.insert_after(NavigableString(f"\n\n{SPLIT_MARKER}\n\n"))
        else:
            admo.parent.append(NavigableString(f"\n\n{SPLIT_MARKER}\n\n"))

    for dl in soup.select('dl, div.variablelist, div.sect2'):
        dl.insert_before(NavigableString(f"\n\n{SPLIT_MARKER}\n\n"))

def finalize_text(text):
    text = re.sub(r'\[#\]\(#.*?\)', '', text)
    text = text.replace(SPLIT_MARKER, "")
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def process_files():
    final_data = []
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        model_name="gpt-3.5-turbo",
        chunk_size=TARGET_CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n## ", "\n### ", "\n\n", "\n", ". ", " "]
    )

    if not os.path.exists(INPUT_DIR):
        print(f"Error: directory {INPUT_DIR} not found.")
        return

    files = glob.glob(os.path.join(INPUT_DIR, "*.html"))
    print(f"Processing {len(files)} HTML files...")

    for file_path in files:
        filename = os.path.basename(file_path)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_html = f.read()

        soup = BeautifulSoup(raw_html, 'html.parser')
        
        for noise in soup.select('div.navheader, div.navfooter, div.toc, script, style'):
            noise.decompose()
        
        title_tag = soup.find('title')
        title = title_tag.get_text().strip() if title_tag else "Unknown"

        code_store = {}
        protect_code_blocks(soup, code_store)
        inject_semantic_splits(soup)

        content_div = soup.find('div', id='docContent') or soup.find('body')
        if not content_div: continue
        
        md_text = md(str(content_div), heading_style="ATX", newline_style="BACKSLASH", code_language="")

        # Découpage sémantique majeur
        raw_chunks = re.split(r"\s*" + re.escape(SPLIT_MARKER) + r"\s*", md_text)

        chunk_counter = 0

        for block in raw_chunks:
            block = block.strip()
            if not block: continue

            sub_chunks = text_splitter.split_text(block)

            for sub in sub_chunks:
                if "CODEBLOCKX" in sub:
                    def restore_code_match(match):
                        key = match.group(0)
                        code_content = code_store.get(key.strip(), "")
                        return f"\n```sql\n{code_content}\n```\n"

                    sub = re.sub(r"CODEBLOCKX\d+X", restore_code_match, sub)
                    # Chunks containing large code blocks may exceed TARGET_CHUNK_SIZE — expected.

                cleaned_content = finalize_text(sub)

                token_count = count_tokens(cleaned_content)
                if token_count < MIN_TOKEN_THRESHOLD:
                    continue

                final_data.append({
                    "id": f"{filename}_{chunk_counter}",
                    "source": filename,
                    "title": title,
                    "content": cleaned_content,
                    "token_count": token_count,
                    "type": "text_block"
                })
                chunk_counter += 1

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
    
    print(f"Done. {len(final_data)} chunks written to {OUTPUT_FILE}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        INPUT_DIR = sys.argv[1]
    process_files()