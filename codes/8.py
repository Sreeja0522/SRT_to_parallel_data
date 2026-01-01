import csv
import re
import os
import sys
from collections import defaultdict

def count_puncts(text, punct_list):
    # Bracket-blind analysis
    cleaned = re.sub(r'\[.*?\]', '', text).strip()
    counts = defaultdict(int)
    symbols = []
    for char in cleaned:
        if char in punct_list:
            counts[char] += 1
            symbols.append(char)
    return counts, symbols

def check_strict(input_file, output_file):
    mismatch_rows = []
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                t_raw, e_raw = row.get("Telugu Text", ""), row.get("Mapped English Text", "")
                t_c, t_s = count_puncts(t_raw, ['.', '?'])
                e_c, e_s = count_puncts(e_raw, ['.', '?'])
                if sum(t_c.values()) != sum(e_c.values()) or any(t_c[p] != e_c[p] for p in ['.', '?']):
                    details = f"t({sum(t_c.values())})-e({sum(e_c.values())}) | {''.join(t_s)} vs {''.join(e_s)}"
                    mismatch_rows.append([row.get("Index"), details, t_raw, e_raw, "STRICT_MISMATCH"])

        if mismatch_rows:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Index", "Details", "Telugu", "English", "Status"])
                writer.writerows(mismatch_rows)
    except Exception: pass

if __name__ == "__main__":
    if len(sys.argv) == 3:
        in_d, out_d = sys.argv[1], sys.argv[2]
        for f in os.listdir(in_d):
            if f.endswith(".csv"):
                check_strict(os.path.join(in_d, f), os.path.join(out_d, f"strict_{f}"))