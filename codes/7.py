import csv
import re
import os
import sys

EXCEPTIONS_PATTERN = r'\b(?:Dr|dr|Mr|mr|Ms|ms|Mrs|mrs|a\.m|p\.m|i\.e|e\.g|u\.s|a\.k\.a|F\.B\.I)\.'

def get_clean_puncts(text, is_telugu=False):
    if not text: return []
    # 1. Remove brackets first
    text = re.sub(r'\[.*?\]', '', text).strip()
    # 2. Remove abbreviations
    text = re.sub(EXCEPTIONS_PATTERN, '', text)
    # 3. Handle Telugu internal dots
    if is_telugu:
        text = re.sub(r'\.(?=[\u0C00-\u0C7F0-9])', '', text)
    return [char for char in text if char in ['.', '?']]

def process_question_marks(t_syms, e_syms):
    if '?' in t_syms and '?' in e_syms:
        t_idx, e_idx = t_syms.index('?'), e_syms.index('?')
        t_fol = (t_idx + 1 < len(t_syms)) and (t_syms[t_idx + 1] == '?')
        e_fol = (e_idx + 1 < len(e_syms)) and (e_syms[e_idx + 1] == '?')
        if not t_fol and not e_fol:
            if t_syms[:t_idx] == e_syms[:e_idx]:
                return t_syms[t_idx + 1:], e_syms[e_idx + 1:]
    return t_syms, e_syms

def check_file_mismatches(input_path, output_path, output_folder):
    mismatch_rows = []
    try:
        with open(input_path, mode='r', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            for row in reader:
                t_raw = row.get("Telugu Text", "")
                e_raw = row.get("Mapped English Text", "")
                t_list = get_clean_puncts(t_raw, True)
                e_list = get_clean_puncts(e_raw, False)
                t_fin, e_fin = process_question_marks(t_list, e_list)
                st, se = len(t_fin), len(e_fin)
                
                if st != se and st > 1 and se > 1:
                    details = f"t({st})-e({se}) | {''.join(t_fin)} vs {''.join(e_fin)}"
                    mismatch_rows.append([row.get("Index"), details, t_raw, e_raw, "MISMATCH"])

        if mismatch_rows:
            os.makedirs(output_folder, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Index", "Details", "Telugu", "English", "Status"])
                writer.writerows(mismatch_rows)
            return len(mismatch_rows)
    except Exception: return 0
    return 0

if __name__ == "__main__":
    if len(sys.argv) == 3:
        in_f, out_f = sys.argv[1], sys.argv[2]
        for f in [f for f in os.listdir(in_f) if f.endswith('.csv')]:
            check_file_mismatches(os.path.join(in_f, f), os.path.join(out_f, f"audit_{f}"), out_f)