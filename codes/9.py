import csv
import re
import os
import sys

# English abbreviation exceptions
EXCEPTIONS_PATTERN = r'\b(?:Dr|dr|Mr|mr|Ms|ms|Mrs|mrs|a\.m|p\.m|i\.e|e\.g|u\.s|a\.k\.a|F\.B\.I)\.'

def get_clean_puncts(text, is_telugu=False):
    if not text: return []
    # Remove brackets and exceptions for punctuation counting
    text = re.sub(r'\[.*?\]', '', text).strip()
    text = re.sub(EXCEPTIONS_PATTERN, '', text)
    if is_telugu:
        # Protect dots in Telugu initials/numbers
        text = re.sub(r'\.(?=[\u0C00-\u0C7F0-9])', '', text)
    return [char for char in text if char in ['.', '?']]

def get_segments(text, is_telugu=False):
    if not text: return []
    
    # Protect exceptions and brackets from splitting
    exceptions = re.findall(EXCEPTIONS_PATTERN, text)
    temp_text = re.sub(EXCEPTIONS_PATTERN, "[[EXC]]", text)
    
    # Remove bracketed content for splitting purposes but keep it in segments
    # Note: If you want to keep brackets in the final output, we split the raw text carefully
    dots_to_protect = []
    if is_telugu:
        dots_to_protect = re.findall(r'\.(?=[\u0C00-\u0C7F0-9])', temp_text)
        temp_text = re.sub(r'\.(?=[\u0C00-\u0C7F0-9])', "[[DOT]]", temp_text)

    # Split at . or ? while keeping the delimiter
    raw_parts = re.split(r'(?<=[.?])', temp_text)
    
    clean_parts = []
    for p in raw_parts:
        p = p.strip()
        if not p: continue
        while "[[EXC]]" in p and exceptions:
            p = p.replace("[[EXC]]", exceptions.pop(0), 1)
        if is_telugu:
            while "[[DOT]]" in p and dots_to_protect:
                p = p.replace("[[DOT]]", dots_to_protect.pop(0), 1)
        clean_parts.append(p)
    return clean_parts

def process_logic(idx, t_raw, e_raw):
    t_puncs = get_clean_puncts(t_raw, is_telugu=True)
    e_puncs = get_clean_puncts(e_raw, is_telugu=False)
    
    t_segs = get_segments(t_raw, is_telugu=True)
    e_segs = get_segments(e_raw, is_telugu=False)

    # --- STEP 1: CHECK FULL MATCH ---
    # If all punctuation and segment counts match perfectly, split everything.
    if t_puncs == e_puncs and len(t_segs) == len(e_segs):
        return [{"Index": idx, "Telugu Text": t, "Mapped English Text": e} for t, e in zip(t_segs, e_segs)]

    # --- STEP 2: QUESTION MARK ANCHOR LOGIC ---
    # Triggered if Step 1 failed (mismatch).
    t_q_idx = next((i for i, char in enumerate(t_puncs) if char == '?'), -1)
    e_q_idx = next((i for i, char in enumerate(e_puncs) if char == '?'), -1)

    # Check if first '?' is unique (not '??') and leading punctuation matches
    t_has_followup = (t_q_idx != -1 and t_q_idx + 1 < len(t_puncs) and t_puncs[t_q_idx + 1] == '?')
    e_has_followup = (e_q_idx != -1 and e_q_idx + 1 < len(e_puncs) and e_puncs[e_q_idx + 1] == '?')

    if (t_q_idx != -1 and e_q_idx != -1 and 
        not t_has_followup and not e_has_followup and 
        t_puncs[:t_q_idx] == e_puncs[:e_q_idx]):
        
        split_limit = t_q_idx + 1
        results = []
        
        # Pair up everything until the question mark anchor
        for i in range(min(split_limit, len(t_segs), len(e_segs))):
            results.append({"Index": idx, "Telugu Text": t_segs[i], "Mapped English Text": e_segs[i]})
        
        # --- STEP 3: RE-EVALUATE REMAINING TEXT ---
        rem_t_segs = t_segs[split_limit:]
        rem_e_segs = e_segs[split_limit:]
        rem_t_puncs = t_puncs[split_limit:]
        rem_e_puncs = e_puncs[split_limit:]

        # If the remainder matches perfectly, split it.
        if rem_t_puncs == rem_e_puncs and len(rem_t_segs) == len(rem_e_segs) and len(rem_t_segs) > 0:
            for t, e in zip(rem_t_segs, rem_e_segs):
                results.append({"Index": idx, "Telugu Text": t, "Mapped English Text": e})
        else:
            # If the remainder still mismatches, group it into one row.
            rem_t = " ".join(rem_t_segs).strip()
            rem_e = " ".join(rem_e_segs).strip()
            if rem_t or rem_e:
                results.append({"Index": idx, "Telugu Text": rem_t, "Mapped English Text": rem_e})
        
        return results

    # --- STEP 4: FINAL FALLBACK ---
    # If no match and no anchor found, return original text.
    return [{"Index": idx, "Telugu Text": t_raw, "Mapped English Text": e_raw}]

def process_folder_split(input_folder, output_folder):
    os.makedirs(output_folder, exist_ok=True)
    for filename in [f for f in os.listdir(input_folder) if f.endswith('.csv')]:
        final_rows = []
        try:
            with open(os.path.join(input_folder, filename), 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    idx = row.get("Index")
                    t_raw = row.get("Telugu Text", "")
                    e_raw = row.get("Mapped English Text", "")
                    processed = process_logic(idx, t_raw, e_raw)
                    final_rows.extend(processed)
            
            with open(os.path.join(output_folder, filename), 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=["Index", "Telugu Text", "Mapped English Text"], quoting=csv.QUOTE_ALL)
                writer.writeheader()
                writer.writerows(final_rows)
            print(f"Successfully processed {filename}")
        except Exception as e:
            print(f"Error splitting {filename}: {e}")

if __name__ == "__main__":
    if len(sys.argv) == 3:
        process_folder_split(sys.argv[1], sys.argv[2])
    else:
        print("Usage: python script.py <input_folder> <output_folder>")