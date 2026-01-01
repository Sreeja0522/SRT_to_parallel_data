import os
import shutil
import csv
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple

SubtitleBlock = Dict[str, str]

# --- CONFIGURATION ---
TELUGU_CHAR_THRESHOLD = 50 
LOG_FILE_NAME = "english_merge_log.csv"

# -----------------------------
# SRT BLOCK PARSING / FORMATTING
# -----------------------------

def parse_srt_block(block_text: str) -> SubtitleBlock | None:
    lines = block_text.strip().split("\n")
    if len(lines) < 3:
        return None
    return {
        "index": lines[0].strip(),
        "timestamp": lines[1].strip(),
        "text": "\n".join(lines[2:]).strip()
    }

def format_srt_block(block: SubtitleBlock) -> str:
    return f"{block['index']}\n{block['timestamp']}\n{block['text']}\n\n"

# -----------------------------
# NEW: BRACE REMOVAL LOGIC
# -----------------------------

def remove_braces_and_log(text: str, filename: str) -> str:
    """Removes { } and everything inside, logging removals to the terminal."""
    # Pattern matches { followed by anything (non-greedy) until }
    pattern = r'\{.*?\}'
    
    removals = re.findall(pattern, text)
    if removals:
        for item in removals:
            print(f"✂️  [REMOVED] in {filename}: {item}")
    
    return re.sub(pattern, "", text).strip()

# -----------------------------
# CORE HELPERS
# -----------------------------

def remove_i_tags(text: str) -> str:
    return re.sub(r"</?i>", "", text)

def is_entirely_bracketed(text: str) -> bool:
    return bool(re.fullmatch(r"\s*\[.*?\]\s*", text.strip()))

def ends_with_sentence_end(text: str) -> bool:
    text_clean = re.sub(r"\[.*?\]", "", text).strip()
    return bool(re.search(r'([.!?]+)(["\']?)\s*$', text_clean))

def get_file_type(file_path: str) -> str:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        telugu_char_count = len(re.findall(r'[\u0C00-\u0C7F]', content))
        return "Telugu" if telugu_char_count >= TELUGU_CHAR_THRESHOLD else "English"
    except:
        return "Unknown"

# ------------------------------------------------
# ENGLISH PROCESSING
# ------------------------------------------------

def process_english(input_srt_content: str, filename: str) -> Tuple[str, List[Dict[str, str]]]:
    # 1. First, remove i tags AND flower braces
    content = remove_i_tags(input_srt_content)
    content = remove_braces_and_log(content, filename)
    
    raw_blocks = re.split(r"\n\s*\n", content.strip())
    blocks = [parse_srt_block(b) for b in raw_blocks if b.strip()]
    blocks = [b for b in blocks if b]

    merged_blocks: List[SubtitleBlock] = []
    csv_log: List[Dict[str, str]] = []

    i = 0
    while i < len(blocks):
        current = blocks[i].copy()
        if is_entirely_bracketed(current["text"]):
            merged_blocks.append(current)
            i += 1
            continue

        start_time, end_time = current["timestamp"].split(" --> ")
        j = i + 1
        merged_count = 0
        original_second_text = ""

        while j < len(blocks):
            next_block = blocks[j]
            next_text = remove_i_tags(next_block["text"])
            # Ensure braces are removed from next_text as well if any exist
            next_text = remove_braces_and_log(next_text, filename)
            
            if is_entirely_bracketed(next_text) or ends_with_sentence_end(current["text"]):
                break
            
            current["text"] += " " + next_text.replace("\n", " ")
            end_time = next_block["timestamp"].split(" --> ")[1]
            current["timestamp"] = f"{start_time} --> {end_time}"
            
            if merged_count == 0:
                original_second_text = next_block["text"].replace("\n", " ")
            merged_count += 1
            j += 1

        if merged_count > 0:
            csv_log.append({
                "Original First Index": blocks[i]["index"],
                "Original Last Index": blocks[j - 1]["index"],
                "Original First Timestamp": blocks[i]["timestamp"],
                "Original Last Timestamp": blocks[j - 1]["timestamp"],
                "New Index": "TEMP", 
                "New Timestamp": current["timestamp"],
                "Original Second Text": original_second_text,
                "New Text (Full)": current["text"].replace("\n", " "),
            })
        merged_blocks.append(current)
        i = j

    for idx, block in enumerate(merged_blocks, start=1):
        block["index"] = str(idx)

    timestamp_to_index = {b["timestamp"]: b["index"] for b in merged_blocks}
    for entry in csv_log:
        entry["New Index"] = timestamp_to_index.get(entry["New Timestamp"], "N/A")

    return "".join(format_srt_block(b) for b in merged_blocks).strip() + "\n", csv_log

# ---------------------------------------
# PROCESS FOLDER
# ---------------------------------------

def process_folder(input_dir: str, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    all_logs = []

    for filename in os.listdir(input_dir):
        if filename.lower().endswith(".csv"): continue
        inp_path = os.path.join(input_dir, filename)
        if not os.path.isfile(inp_path): continue

        file_type = get_file_type(inp_path)
        out_path = os.path.join(output_dir, filename)

        with open(inp_path, "r", encoding="utf-8") as f:
            content = f.read()

        if file_type == "Telugu":
            # Clean Telugu files for tags and braces too
            cleaned_telugu = remove_i_tags(content)
            cleaned_telugu = remove_braces_and_log(cleaned_telugu, filename)
            
            tel_blocks = [parse_srt_block(b) for b in re.split(r"\n\s*\n", cleaned_telugu.strip()) if b.strip()]
            with open(out_path, "w", encoding="utf-8") as f:
                f.write("".join(format_srt_block(b) for b in tel_blocks if b))
        
        elif file_type == "English":
            # Pass filename to process_english for terminal logging
            processed_content, logs = process_english(content, filename)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(processed_content)
            for entry in logs:
                entry["Source Filename"] = filename
            all_logs.extend(logs)

    if all_logs:
        log_path = os.path.join(output_dir, LOG_FILE_NAME)
        with open(log_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=["Source Filename", "Original First Index", "Original Last Index", "Original First Timestamp", "Original Last Timestamp", "New Index", "New Timestamp", "Original Second Text", "New Text (Full)"])
            writer.writeheader()
            writer.writerows(all_logs)

if __name__ == "__main__":
    if len(sys.argv) == 3:
        process_folder(sys.argv[1], sys.argv[2])
    else:
        print("Usage: python 3.py <input_dir> <output_dir>")