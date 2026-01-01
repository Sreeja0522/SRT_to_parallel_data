import re
import csv
import os
import glob
import sys
from datetime import timedelta

# ==========================================================
# 1. UTILITY FUNCTIONS
# ==========================================================

def time_to_seconds(time_str):
    """Converts SRT time string (HH:MM:SS,mmm) to seconds."""
    match = re.match(r'(\d{2}):(\d{2}):(\d{2}),(\d{3})', time_str)
    if match:
        hours, minutes, seconds, milliseconds = map(int, match.groups())
        return timedelta(hours=hours, minutes=minutes, seconds=seconds, milliseconds=milliseconds).total_seconds()
    return 0.0

def seconds_to_time(total_seconds):
    """Converts seconds back to SRT time string."""
    td = timedelta(seconds=total_seconds)
    total_milliseconds = int(td.total_seconds() * 1000)
    milliseconds = total_milliseconds % 1000
    seconds = int(total_milliseconds / 1000) % 60
    minutes = int(total_milliseconds / (1000 * 60)) % 60
    hours = int(total_milliseconds / (1000 * 60 * 60))
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"

# --- Logging Utilities ---
telugu_merge_log = []
english_merge_log = []

def parse_srt(filename):
    """Reads an SRT file and returns a list of dictionaries."""
    subs = []
    timestamp_pattern = re.compile(r'(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})')
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read().strip()
    except FileNotFoundError:
        return []
        
    blocks = re.split(r'\n\s*\n', content) 
    
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 2:
            index_number = next((int(line) for line in lines if line.isdigit()), None)
            timestamp_line = next((line for line in lines if '-->' in line), None)
            
            if timestamp_line:
                match = timestamp_pattern.search(timestamp_line)
                if match:
                    start_time_str, end_time_str = match.groups()
                    start_sec = time_to_seconds(start_time_str)
                    end_sec = time_to_seconds(end_time_str)
                    
                    text_lines = [line for line in lines if not line.isdigit() and '-->' not in line]
                    text = '\n'.join(text_lines).strip() 
                    
                    if text:
                        subs.append({
                            'index': index_number,
                            'start_sec': start_sec,
                            'end_sec': end_sec,
                            'start_time_str': start_time_str,
                            'end_time_str': end_time_str,
                            'text': text
                        })
    return subs

# ==========================================================
# 2. THE CORE RECURSIVE MAPPING LOGIC
# ==========================================================

def map_and_merge_subtitles(telugu_subs, english_subs, file_prefix):
    # Mark English tags (like [Music]) to be ignored during merging
    for eng_sub in english_subs:
        eng_sub['ignore_for_merge'] = bool(re.fullmatch(r'\[.*?\]', eng_sub['text'].strip()))

    used_telugu_indices = set()
    used_english_indices = set()
    merged_blocks = []

    # Iterate through every Telugu sub to start a "bridge"
    for tel_index, tel_sub in enumerate(telugu_subs):
        if tel_index in used_telugu_indices:
            continue

        # --- START RECURSIVE BRIDGE ---
        merged_telugu_indices = {tel_index}
        merged_english_indices = set()
        
        changed = True
        while changed:
            changed = False
            
            # 1. Find all English subs that overlap ANY currently merged Telugu sub
            for t_idx in list(merged_telugu_indices):
                t_sub = telugu_subs[t_idx]
                for e_idx, e_sub in enumerate(english_subs):
                    if e_idx not in merged_english_indices and not e_sub.get('ignore_for_merge', False):
                        if (e_sub['start_sec'] < t_sub['end_sec']) and (e_sub['end_sec'] > t_sub['start_sec']):
                            merged_english_indices.add(e_idx)
                            changed = True
            
            # 2. Find all Telugu subs that overlap ANY currently merged English sub
            for e_idx in list(merged_english_indices):
                e_sub = english_subs[e_idx]
                for t_idx, t_sub in enumerate(telugu_subs):
                    if t_idx not in merged_telugu_indices:
                        if (t_sub['start_sec'] < e_sub['end_sec']) and (t_sub['end_sec'] > e_sub['start_sec']):
                            merged_telugu_indices.add(t_idx)
                            changed = True

        # --- AFTER THE LOOP: Finalize the Block ---
        all_starts = []
        all_ends = []
        merged_telugu_texts = []
        merged_eng_texts = []

        # Sort indices to keep text in chronological order
        for t_idx in sorted(list(merged_telugu_indices)):
            sub = telugu_subs[t_idx]
            merged_telugu_texts.append(sub['text'].replace('\n',' ').strip())
            all_starts.append(sub['start_sec'])
            all_ends.append(sub['end_sec'])
            used_telugu_indices.add(t_idx)

        for e_idx in sorted(list(merged_english_indices)):
            sub = english_subs[e_idx]
            merged_eng_texts.append(sub['text'].replace('\n',' ').strip())
            all_starts.append(sub['start_sec'])
            all_ends.append(sub['end_sec'])
            used_english_indices.add(e_idx)

        mapped_english_text = ' '.join(merged_eng_texts) if merged_eng_texts else "**[NO ENGLISH MATCH FOUND]**"
        
        merged_blocks.append({
            'original_srt_index': tel_sub['index'],
            'start_sec': min(all_starts),
            'end_sec': max(all_ends),
            'start_time_str': seconds_to_time(min(all_starts)),
            'end_time_str': seconds_to_time(max(all_ends)),
            'telugu_text': ' '.join(merged_telugu_texts),
            'mapped_english_text': mapped_english_text
        })

    # Handle remaining English subtitles (orphans or tags)
    for eng_index, eng_sub in enumerate(english_subs):
        if eng_index in used_english_indices:
            continue
        
        mapped_english_text = eng_sub['text'].replace('\n',' ').strip()
        telugu_text = "[TAGS BLOCK - NO MERGING ATTEMPTED]" if eng_sub.get('ignore_for_merge', False) else "**[NO TELUGU MATCH FOUND]**"

        merged_blocks.append({
            'original_srt_index': None,
            'start_sec': eng_sub['start_sec'],
            'end_sec': eng_sub['end_sec'],
            'start_time_str': eng_sub['start_time_str'],
            'end_time_str': eng_sub['end_time_str'],
            'telugu_text': telugu_text,
            'mapped_english_text': mapped_english_text
        })
        used_english_indices.add(eng_index)

    merged_blocks.sort(key=lambda x: x['start_sec'])

    # --- DEDUPLICATION PASS ---
    final_cleaned_subs = []
    if not merged_blocks: return []

    current_entry = merged_blocks[0].copy()
    for next_entry in merged_blocks[1:]:
        if (next_entry['mapped_english_text'] == current_entry['mapped_english_text']) and \
           (next_entry['mapped_english_text'] != "**[NO ENGLISH MATCH FOUND]**"):
            current_entry['end_sec'] = max(current_entry['end_sec'], next_entry['end_sec'])
            current_entry['end_time_str'] = seconds_to_time(current_entry['end_sec'])
            if next_entry['telugu_text'] not in current_entry['telugu_text']:
                if current_entry['telugu_text'] == "**[NO TELUGU MATCH FOUND]**":
                    current_entry['telugu_text'] = next_entry['telugu_text']
                else:
                    current_entry['telugu_text'] += " " + next_entry['telugu_text']
        else:
            final_cleaned_subs.append(current_entry)
            current_entry = next_entry.copy()

    final_cleaned_subs.append(current_entry)
    
    for item in final_cleaned_subs:
        if item['telugu_text'] == "[TAGS BLOCK - NO MERGING ATTEMPTED]":
            item['telugu_text'] = "**[NO TELUGU MATCH FOUND]**"

    return final_cleaned_subs

# ==========================================================
# 3. OUTPUT & EXECUTION
# ==========================================================

def write_csv(data, output_path, fieldnames):
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=',', quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(data)

def write_merged_csv(mapped_subs, output_path):
    fieldnames = ['Index', 'Start Time', 'End Time', 'Telugu Text', 'Mapped English Text']
    write_csv([{
        'Index': i+1,
        'Start Time': sub['start_time_str'],
        'End Time': sub['end_time_str'],
        'Telugu Text': sub['telugu_text'],
        'Mapped English Text': sub['mapped_english_text']
    } for i, sub in enumerate(mapped_subs)], output_path, fieldnames)

def write_text_only_csv(mapped_subs, output_path):
    fieldnames = ['Index', 'Telugu Text', 'Mapped English Text']
    write_csv([{
        'Index': i+1,
        'Telugu Text': sub['telugu_text'],
        'Mapped English Text': sub['mapped_english_text']
    } for i, sub in enumerate(mapped_subs)], output_path, fieldnames)

def get_episode_number(filename):
    match = re.search(r'\d+', filename)
    return match.group() if match else None

def is_telugu_by_content(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        telugu_char_count = len(re.findall(r'[\u0C00-\u0C7F]', content))
        return telugu_char_count > 100
    except:
        return False

def process_folder(input_folder, output_base_dir):
    OUTPUT_FOLDER_MERGED = os.path.join(output_base_dir, 'TIME_ACCURATE_CSV_OUTPUT')
    OUTPUT_FOLDER_TEXT_ONLY = os.path.join(output_base_dir, 'TEXT_ONLY_CSV_OUTPUT')
    for folder in [OUTPUT_FOLDER_MERGED, OUTPUT_FOLDER_TEXT_ONLY]:
        os.makedirs(folder, exist_ok=True)

    episodes = {} 
    for filename in os.listdir(input_folder):
        if not filename.lower().endswith('.srt'): continue
        ep_num = get_episode_number(filename)
        if ep_num:
            if ep_num not in episodes: episodes[ep_num] = []
            episodes[ep_num].append(os.path.join(input_folder, filename))

    for ep_num, files in sorted(episodes.items()):
        if len(files) < 2: continue
        tel_file, eng_file = None, None
        for f_path in files[:2]:
            if is_telugu_by_content(f_path): tel_file = f_path
            else: eng_file = f_path

        if tel_file and eng_file:
            print(f"🔗 Aligning Ep {ep_num}...")
            tel_subs = parse_srt(tel_file)
            eng_subs = parse_srt(eng_file)
            final_merged_subs = map_and_merge_subtitles(tel_subs, eng_subs, ep_num)
            series_name = os.path.basename(output_base_dir)
            output_name = f'{series_name}.Ep{ep_num}.csv'
            write_merged_csv(final_merged_subs, os.path.join(OUTPUT_FOLDER_MERGED, output_name))
            write_text_only_csv(final_merged_subs, os.path.join(OUTPUT_FOLDER_TEXT_ONLY, output_name))

if __name__ == "__main__":
    if len(sys.argv) == 3:
        process_folder(sys.argv[1], sys.argv[2])
    else:
        print("Usage: python 4.py <input_folder> <output_folder>")