import os
import re
import zipfile
import hashlib
import shutil
from pathlib import Path
from ebooklib import epub
import fitz  # PyMuPDF

# --- Configuration ---
ZIP_FILES = ["deepweb_dump-20250406T061054Z-001.zip", "deepweb_dump-20250406T061054Z-002.zip", "deepweb_dump-20250406T061054Z-003.zip"]
ROOT_OUTPUT = Path("library_root")
SORTED_DIR = Path("sorted_books")
KEYWORD_TRIGGERS = ["keywords", "index terms", "topics", "subject"]
CATEGORIES = {
    "Programming": ["programming", "code", "software", "python", "java"],
    "Penetration Testing": ["exploit", "payload", "burp", "nmap", "pentest"],
    "Cryptography": ["rsa", "aes", "encryption", "cipher"],
    "Digital Forensics": ["forensics", "evidence", "analysis"],
    "Network Security": ["firewall", "network", "tcp/ip", "snort", "vpn"],
    "Cyber Law": ["compliance", "regulation", "law", "gdpr"]
}

# --- Utility Functions ---
def compute_md5(file_path, chunk_size=8192):
    hasher = hashlib.md5()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()

def extract_text_from_pdf(file_path):
    try:
        doc = fitz.open(file_path)
        return " ".join(page.get_text() for page in doc[:5])
    except Exception:
        return ""

def extract_text_from_epub(file_path):
    try:
        book = epub.read_epub(file_path)
        text = ""
        for item in book.get_items():
            if item.get_type() == epub.ITEM_DOCUMENT:
                text += re.sub(r"\s+", " ", item.get_content().decode("utf-8"))
        return text[:10000]
    except Exception:
        return ""

def extract_text_from_txt(file_path):
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(10000)
    except Exception:
        return ""

def extract_keywords(text):
    lines = text.lower().splitlines()
    keywords = []
    for line in lines:
        for trigger in KEYWORD_TRIGGERS:
            if trigger in line:
                words = re.findall(r"[a-zA-Z0-9\- ]+", line)
                keywords.extend(word.strip() for word in words if len(word.strip()) > 3)
    return list(set(keywords))

def categorize_by_keywords(keywords):
    for category, terms in CATEGORIES.items():
        for term in terms:
            for kw in keywords:
                if term in kw.lower():
                    return category
    return "Uncategorized"

# --- Main Logic ---
def prepare_root_dir():
    ROOT_OUTPUT.mkdir(exist_ok=True)
    seen_hashes = set()
    total_extracted = 0
    total_duplicates = 0
    total_empty = 0

    for zip_path in ZIP_FILES:
        print(f"[🔍] Processing archive: {zip_path}")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for member in zip_ref.infolist():
                if member.is_dir():
                    continue

                extracted_path = zip_ref.extract(member, ROOT_OUTPUT)

                if os.path.getsize(extracted_path) == 0:
                    os.remove(extracted_path)
                    total_empty += 1
                    print(f"    ⚠️  Removed empty file: {member.filename}")
                    continue

                file_hash = compute_md5(extracted_path)
                if file_hash in seen_hashes:
                    os.remove(extracted_path)
                    total_duplicates += 1
                    print(f"    🔁 Duplicate removed: {member.filename}")
                    continue

                seen_hashes.add(file_hash)

                final_path = ROOT_OUTPUT / Path(member.filename).name
                if final_path.exists():
                    final_path = ROOT_OUTPUT / f"{final_path.stem}_copy{final_path.suffix}"
                shutil.move(extracted_path, final_path)
                print(f"    ✅ Extracted: {final_path.name}")
                total_extracted += 1

    print(f"\n[✔] Extraction and de-duplication complete.")
    print(f"    Total extracted: {total_extracted}")
    print(f"    Duplicates removed: {total_duplicates}")
    print(f"    Empty files removed: {total_empty}\n")

def organize_by_keywords():
    SORTED_DIR.mkdir(exist_ok=True)
    total_sorted = 0

    files = [f for f in ROOT_OUTPUT.glob("*") if f.is_file()]
    print(f"[📂] Sorting {len(files)} files by keyword...")

    for file in files:
        text = ""
        suffix = file.suffix.lower()
        if suffix == ".pdf":
            text = extract_text_from_pdf(file)
        elif suffix == ".epub":
            text = extract_text_from_epub(file)
        elif suffix == ".txt":
            text = extract_text_from_txt(file)

        keywords = extract_keywords(text)
        category = categorize_by_keywords(keywords)
        target_dir = SORTED_DIR / category
        target_dir.mkdir(exist_ok=True)
        shutil.copy2(file, target_dir / file.name)
        print(f"    📘 {file.name} → [{category}] | Keywords: {keywords if keywords else 'None found'}")
        total_sorted += 1

    print(f"\n[✔] Keyword-based sorting complete. Total files sorted: {total_sorted}\n")

# --- Entrypoint ---
if __name__ == "__main__":
    prepare_root_dir()
    organize_by_keywords()

