import os
import csv
import re
import sys

# --- CLEANUP FUNCTIONS ---

def remove_fillers(text):
    if not text: return ""
    fillers = r'\b(Mmm|Hmm|Oh|Uh-huh|Uh|Ah|Mm)\b([\.?]+)?\s*'
    return re.sub(fillers, "", text, flags=re.IGNORECASE).strip()

def remove_tags(text):
    if not text: return ""
    text = re.sub(r"</?i>", "", text)
    text = re.sub(r"\[.*?\]", "", text)
    return text

def clean_dots_and_ellipses(text):
    if not text: return ""
    text = text.replace("…", "...")
    text = re.sub(r'(\.\s*){2,}\.', '...', text) 
    text = re.sub(r'\.{2,}\s*$', '.', text)
    text = re.sub(r'\.{2,}', ' ', text)
    return text

def clean_hyphens(text):
    if not text: return ""
    text = re.sub(r'(^|\s)-+', r'\1', text)
    text = re.sub(r'-+(\s|$)', r'\1', text)
    return text

def apply_final_cleanup(text, is_telugu=False, keep_tags=False):
    if not text or text.startswith("**["):
        return text
    
    if not keep_tags:
        text = remove_tags(text)
    else:
        text = re.sub(r"</?i>", "", text)
        
    text = remove_fillers(text)
    text = clean_dots_and_ellipses(text)
    text = clean_hyphens(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# --- PROCESSING ENGINE ---

def process_csv_files(input_folder, output_folder, keep_tags=False):
    if not os.path.exists(input_folder):
        print(f"    🛑 Error: Folder '{input_folder}' not found.")
        return

    os.makedirs(output_folder, exist_ok=True)
    csv_files = [f for f in os.listdir(input_folder) if f.lower().endswith('.csv')]

    for filename in csv_files:
        input_path = os.path.join(input_folder, filename)
        output_path = os.path.join(output_folder, filename)
        cleaned_rows = []

        with open(input_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            if not fieldnames: continue

            for row in reader:
                # 1. Capture the original index immediately to preserve it
                original_index = row.get('Index', "")
                
                tel_text = row.get('Telugu Text', "")
                eng_text = row.get('Mapped English Text', "")

                # Skip "No Match" rows
                if "**[NO TELUGU MATCH FOUND]**" in tel_text or "**[NO ENGLISH MATCH FOUND]**" in eng_text:
                    continue

                # Clean text
                cleaned_tel = apply_final_cleanup(tel_text, is_telugu=True, keep_tags=keep_tags)
                cleaned_eng = apply_final_cleanup(eng_text, is_telugu=False, keep_tags=keep_tags)

                if cleaned_tel and cleaned_eng:
                    # 2. Put the cleaned text back but DON'T touch row['Index']
                    row['Telugu Text'] = cleaned_tel
                    row['Mapped English Text'] = cleaned_eng
                    cleaned_rows.append(row)

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            # 3. This writes the original index values back to the file
            writer.writerows(cleaned_rows)

        status = " (Tags Kept)" if keep_tags else ""
        print(f"    ✅ Processed {filename}{status} | Kept {len(cleaned_rows)} rows")

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        in_folder = sys.argv[1]
        out_folder = sys.argv[2]
        keep = "--keep" in sys.argv
        process_csv_files(in_folder, out_folder, keep_tags=keep)
    else:
        print("Usage: python 5.py <input_folder> <output_folder> [--keep]")