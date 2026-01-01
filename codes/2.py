import re
from pathlib import Path
import os
import shutil
import csv
import sys

# --- Configuration ---
# Minimum number of Telugu characters required to consider a file "Telugu"
TELUGU_CHAR_THRESHOLD = 50 
LOG_FILE_NAME = "merge_log.csv"

# Global list to store all merge details
MERGE_LOG_DATA = []

# --- Helper Functions ---

def is_telugu_file(content: str, threshold: int) -> bool:
    """Checks if the content contains Telugu characters."""
    telugu_char_count = len(re.findall(r'[\u0C00-\u0C7F]', content))
    return telugu_char_count >= threshold

def write_merge_log(output_dir: Path):
    """Writes the collected merge data to a CSV file in the output directory."""
    if not MERGE_LOG_DATA:
        return

    csv_file_path = output_dir / LOG_FILE_NAME
    fieldnames = ['File_Path', 'Original_Index_1', 'Original_Index_2', 'New_Timestamp', 'Merged_Dialogue_Start']

    try:
        with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
            writer.writeheader()
            writer.writerows(MERGE_LOG_DATA)
        print(f"    📝 Log saved: {csv_file_path.name}")
    except Exception as e:
        print(f"    🛑 Error writing log: {e}")

# --- Core Merger Logic ---

def merge_srt_blocks(file_path: Path, output_dir: Path, original_blocks: list):
    """Merges blocks where dialogue ends with a comma."""
    CONTINUATION_PUNCTUATION = r'[,]$'
    merged_blocks = []
    i = 0
    merge_count = 0
    content_changed = False

    while i < len(original_blocks):
        current_block = original_blocks[i]
        next_block = original_blocks[i+1] if i + 1 < len(original_blocks) else None
        
        lines = current_block.splitlines()
        if len(lines) < 3 or not next_block:
            merged_blocks.append(current_block)
            i += 1
            continue
            
        last_dialogue_line = lines[-1].strip()
        
        if re.search(CONTINUATION_PUNCTUATION, last_dialogue_line):
            next_lines = next_block.splitlines()
            if len(next_lines) < 3:
                merged_blocks.append(current_block)
                i += 1
                continue

            # Time processing
            time_match_current = re.search(r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})', lines[1])
            time_match_next = re.search(r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})', next_lines[1])
            
            if not time_match_current or not time_match_next:
                merged_blocks.append(current_block)
                i += 1
                continue
                
            new_timestamp = f"{time_match_current.group(1)} --> {time_match_next.group(2)}"
            new_dialogue = " ".join(lines[2:]) + " " + " ".join(next_lines[2:])
            
            # Log Data
            MERGE_LOG_DATA.append({
                'File_Path': file_path.name,
                'Original_Index_1': lines[0],
                'Original_Index_2': next_lines[0],
                'New_Timestamp': new_timestamp,
                'Merged_Dialogue_Start': new_dialogue[:100]
            })
            
            # Reconstruct
            merged_block = [lines[0], new_timestamp, new_dialogue]
            merged_blocks.append('\n'.join(merged_block))
            merge_count += 1
            content_changed = True
            i += 2 
        else:
            merged_blocks.append(current_block)
            i += 1

    # Write output
    output_path = output_dir / file_path.name
    final_content = '\n\n'.join(merged_blocks) + '\n'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(final_content)
    
    return merge_count

# --- Main Execution ---

def main_processor(input_dir: Path, output_dir: Path):
    """Processes a specific series folder and saves to a specific output folder."""
    
    # Ensure the output folder for this series exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    all_srt_files = sorted(input_dir.rglob('*.srt'))
    
    total_merges = 0

    for file_path in all_srt_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            original_blocks = content.strip().split('\n\n')
        except Exception:
            continue
        
        if is_telugu_file(content, TELUGU_CHAR_THRESHOLD):
            merges = merge_srt_blocks(file_path, output_dir, original_blocks)
            total_merges += max(0, merges)
        else:
            # Copy non-telugu files directly to the same series output folder
            shutil.copy2(file_path, output_dir / file_path.name)

    write_merge_log(output_dir)
    print(f"    ✅ Finished: {total_merges} merges in {input_dir.name}")

if __name__ == '__main__':
    # Usage: python 2.py [input_series_path] [output_series_path]
    if len(sys.argv) == 3:
        input_p = Path(sys.argv[1])
        output_p = Path(sys.argv[2])
        main_processor(input_p, output_p)
    else:
        print("Usage: 2.py <input_folder> <output_folder>")