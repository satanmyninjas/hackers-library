import os
import shutil
import zipfile
import hashlib
import re
from pathlib import Path
from ebooklib import epub
import fitz  # PyMuPDF
from transformers import pipeline
from tqdm import tqdm

# Load zero-shot classification pipeline (PyTorch backend)
classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

# Define topics for cybersecurity books
LABELS = [
    "Cryptography", "Network Security", "Penetration Testing",
    "Digital Forensics", "Malware Analysis", "Cyber Law", 
    "Cybersecurity Certifications", "General Cybersecurity"
]

def compute_md5(file_path, chunk_size=8192):
    """
    Compute the MD5 hash of a file.

    Args:
        file_path (str or Path): File to hash.
        chunk_size (int): Bytes per read.

    Returns:
        str: Hex digest of MD5 hash.
    """
    hasher = hashlib.md5()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()

def extract_and_dedup(zip_files, output_dir):
    """
    Extract files from multiple .zip archives and remove duplicates by MD5.

    Args:
        zip_files (list): List of paths to .zip files.
        output_dir (str or Path): Directory to extract and store unique files.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    seen_hashes = {}

    print(f"\n📦 Extracting and deduplicating from {len(zip_files)} ZIP archives...\n")

    for zip_file in zip_files:
        print(f"→ Processing archive: {zip_file}")
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            for member in zip_ref.infolist():
                if member.is_dir():
                    continue

                extracted_path = zip_ref.extract(member, path=output_path / "__temp")
                file_hash = compute_md5(extracted_path)

                if file_hash in seen_hashes:
                    print(f"[WARNING]  Duplicate skipped: {member.filename}")
                    os.remove(extracted_path)
                else:
                    final_path = output_path / Path(member.filename).name
                    while final_path.exists():
                        final_path = final_path.with_stem(final_path.stem + "_copy")
                    shutil.move(extracted_path, final_path)
                    seen_hashes[file_hash] = final_path

        temp_path = output_path / "__temp"
        if temp_path.exists():
            shutil.rmtree(temp_path)

    print(f"\n[DONE] Deduplication complete. Unique files saved to: {output_path}")

def extract_text_from_pdf(file_path, max_pages=5):
    """Extract text from first few pages of a PDF."""
    try:
        doc = fitz.open(file_path)
        return " ".join([page.get_text() for page in doc[:max_pages]])
    except Exception as e:
        print(f"[ERROR] Failed to extract PDF: {file_path.name} — {e}")
        return ""

def extract_text_from_epub(epub_path):
    """Extract readable text from an EPUB file."""
    try:
        book = epub.read_epub(epub_path)
        text = ""
        for item in book.get_items():
            if item.get_type() == epub.ITEM_DOCUMENT:
                text += re.sub(r'\s+', ' ', item.get_content().decode("utf-8"))
        return text[:10000]
    except Exception as e:
        print(f"[ERROR] Failed to read EPUB: {epub_path.name} — {e}")
        return ""

def extract_text_from_txt(file_path):
    """Read and return the first ~10,000 characters from a TXT file."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(10000)
    except Exception as e:
        print(f"[ERROR] Failed to read TXT: {file_path.name} — {e}")
        return ""

def classify_text(text):
    """Classify text using zero-shot model and predefined cybersecurity topics."""
    result = classifier(text, candidate_labels=LABELS)
    return result["labels"][0] if result["scores"][0] > 0.4 else "Uncategorized"

def organize_files(input_dir, output_dir):
    """
    Classify and sort PDF, EPUB, and TXT files into topic folders.

    Args:
        input_dir (str or Path): Directory with unorganized files.
        output_dir (str or Path): Directory to place categorized files.
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    files = list(input_path.glob("*.pdf")) + list(input_path.glob("*.epub")) + list(input_path.glob("*.txt"))
    print(f"\n[BUSY] Found {len(files)} files to process in '{input_dir}'...\n")

    for file_path in tqdm(files, desc="🧠 Classifying files", unit="file"):
        suffix = file_path.suffix.lower()
        text = ""

        if suffix == ".pdf":
            text = extract_text_from_pdf(file_path)
        elif suffix == ".epub":
            text = extract_text_from_epub(file_path)
        elif suffix == ".txt":
            text = extract_text_from_txt(file_path)

        if not text.strip():
            print(f"[WARNING]  Skipping unreadable or empty file: {file_path.name}")
            continue

        category = classify_text(text)
        target_dir = output_path / category
        target_dir.mkdir(exist_ok=True)

        new_name = target_dir / file_path.name
        counter = 1
        while new_name.exists():
            new_name = target_dir / f"{file_path.stem}_{counter}{file_path.suffix}"
            counter += 1

        shutil.copy2(file_path, new_name)
        print(f"[DONE] {file_path.name} → [{category}]")

    print(f"\n[DONE] Sorting complete. Categorized documents saved in: {output_path}")

# ==== Main Entrypoint ====

if __name__ == "__main__":
    # Set your ZIP archive paths and output directory here
    zip_files = [
        "books_part1.zip",
        "books_part2.zip",
        "more_books.zip"
    ]
    temp_extract_dir = "deduped_books"
    final_sorted_dir = "cyber-library"

    # Step 1: Extract and deduplicate
    extract_and_dedup(zip_files, temp_extract_dir)

    # Step 2: Organize into topics
    organize_files(temp_extract_dir, final_sorted_dir)

