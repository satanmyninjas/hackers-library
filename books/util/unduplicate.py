import zipfile
import hashlib
import os
import shutil
from pathlib import Path

def compute_md5(file_path, chunk_size=8192):
    """Compute MD5 hash of a file."""
    hasher = hashlib.md5()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()

def extract_and_dedup(zip_files, output_dir):
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    seen_hashes = {}

    for zip_file in zip_files:
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            for member in zip_ref.infolist():
                if member.is_dir():
                    continue

                # Extract to temp location
                extracted_path = zip_ref.extract(member, path=output_path / "__temp")
                file_hash = compute_md5(extracted_path)

                if file_hash in seen_hashes:
                    print(f"Duplicate found: {member.filename} — skipping")
                    os.remove(extracted_path)
                else:
                    final_path = output_path / Path(member.filename).name
                    # Avoid overwrite in case of name clash
                    while final_path.exists():
                        final_path = final_path.with_stem(final_path.stem + "_copy")
                    shutil.move(extracted_path, final_path)
                    seen_hashes[file_hash] = final_path

        # Clean up temp dir
        temp_path = output_path / "__temp"
        if temp_path.exists():
            shutil.rmtree(temp_path)

    print(f"\nDone! Unique files saved to: {output_path}")

# ==== Usage ====

if __name__ == "__main__":
    # Example usage: modify these paths as needed
    zip_files = [
        "books_part1.zip",
        "books_part2.zip",
        "more_books.zip"
    ]
    output_dir = "organized_books"

    extract_and_dedup(zip_files, output_dir)

