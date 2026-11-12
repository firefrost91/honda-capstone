import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path


INPUT_FILE = Path("data/document_chunks.jsonl")
OUTPUT_FILE = Path("data/document_chunks.sentence_aware.jsonl")

TARGET_WORDS = 325
OVERLAP_SENTENCES = 1

ABBREVIATIONS = {
    "mr.", "mrs.", "ms.", "dr.", "prof.", "sr.", "jr.",
    "inc.", "ltd.", "dept.", "vs.", "etc.", "e.g.",
    "i.e.", "u.s.", "u.k.", "no."
}


def reconstruct_text(chunks):
    """Reconstruct original text from overlapping chunks."""
    chunks = sorted(chunks, key=lambda r: r["char_start"])

    first = chunks[0]
    base_offset = first["char_start"]
    text = first["text"]

    for record in chunks:
        start = record["char_start"]
        end = record["char_end"]
        chunk_text = record["text"]

        if end - start != len(chunk_text):
            raise ValueError(
                f"Character offset mismatch in {record['chunk_id']}"
            )

        if record is first:
            continue

        expected_end = base_offset + len(text)

        if start > expected_end:
            raise ValueError(
                f"Gap detected in {record['chunk_id']}: "
                f"expected {expected_end}, found {start}"
            )

        overlap = expected_end - start

        if overlap > 0:
            if text[-overlap:] != chunk_text[:overlap]:
                raise ValueError(
                    f"Overlap mismatch in {record['chunk_id']}"
                )
            text += chunk_text[overlap:]
        else:
            text += chunk_text

    return text, base_offset


def split_sentences(text):
    """Split text at likely sentence boundaries."""
    sentences = []
    start = 0

    pattern = re.compile(r'[.!?]["\')\]]*[ \t]+|\n+')

    for match in pattern.finditer(text):
        previous_text = text[start:match.end()].rstrip()
        words = previous_text.split()

        if words:
            last_word = words[-1].lower().strip('"\'()[]')

            # Avoid splitting after common abbreviations.
            if last_word in ABBREVIATIONS:
                continue

            sentences.append((start, match.end()))
            start = match.end()

    if start < len(text):
        sentences.append((start, len(text)))

    return sentences


def get_web_locator(start, end, original_chunks):
    """Preserve the web segment references covered by a new chunk."""
    locators = []

    for record in original_chunks:
        overlaps = (
            max(start, record["char_start"])
            < min(end, record["char_end"])
        )

        if overlaps and record.get("locator"):
            if record["locator"] not in locators:
                locators.append(record["locator"])

    return "; ".join(locators) if locators else "Web text"


def make_chunks(text, base_offset, template, original_chunks):
    """Create sentence-aware chunks with sentence overlap."""
    sentences = split_sentences(text)

    if not sentences:
        return []

    new_chunks = []
    start_index = 0
    chunk_number = 1

    while start_index < len(sentences):
        end_index = start_index
        word_count = 0

        while end_index < len(sentences):
            sentence_start, sentence_end = sentences[end_index]
            sentence_words = len(
                text[sentence_start:sentence_end].split()
            )

            if end_index > start_index and word_count + sentence_words > TARGET_WORDS:
                break

            word_count += sentence_words
            end_index += 1

            if word_count >= TARGET_WORDS:
                break

        chunk_start = sentences[start_index][0]
        chunk_end = sentences[end_index - 1][1]
        chunk_text = text[chunk_start:chunk_end]

        absolute_start = base_offset + chunk_start
        absolute_end = base_offset + chunk_end

        record = dict(template)

        source_id = template["source_id"]
        page_number = template.get("page_number")

        # Use page 0000 for web sources that have no page number.
        page_label = page_number if page_number is not None else 0

        record["chunk_id"] = (
            f"{source_id}__p{page_label:04d}__c{chunk_number:03d}"
        )

        record["text"] = chunk_text
        record["word_count"] = len(chunk_text.split())
        record["char_start"] = absolute_start
        record["char_end"] = absolute_end
        record["content_sha256"] = hashlib.sha256(
            chunk_text.encode("utf-8")
        ).hexdigest()

        if page_number is not None:
            record["locator"] = template.get(
                "locator", f"PDF page {page_number}"
            )
        else:
            record["locator"] = get_web_locator(
                absolute_start,
                absolute_end,
                original_chunks
            )

        new_chunks.append(record)
        chunk_number += 1

        if end_index >= len(sentences):
            break

        # Start the next chunk one sentence before the previous one ended.
        start_index = max(
            end_index - OVERLAP_SENTENCES,
            start_index + 1
        )

    return new_chunks


def main():
    with INPUT_FILE.open("r", encoding="utf-8") as file:
        records = [json.loads(line) for line in file]

    # Group PDF chunks by source and page.
    # Web chunks have no page number, so they are grouped by source.
    groups = defaultdict(list)

    for record in records:
        key = (
            record["source_id"],
            record.get("page_number")
        )
        groups[key].append(record)

    output_records = []

    for (source_id, page_number), chunks in sorted(
        groups.items(),
        key=lambda item: (
            item[0][0],
            -1 if item[0][1] is None else item[0][1]
        )
    ):
        reconstructed_text, base_offset = reconstruct_text(chunks)

        new_chunks = make_chunks(
            reconstructed_text,
            base_offset,
            chunks[0],
            chunks
        )

        output_records.extend(new_chunks)

    with OUTPUT_FILE.open("w", encoding="utf-8") as file:
        for record in output_records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

    print("Rechunking complete!")
    print(f"Original chunks: {len(records)}")
    print(f"New chunks: {len(output_records)}")
    print(f"Output file: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()