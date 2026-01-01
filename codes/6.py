import pandas as pd
import re
import os
import glob
import logging
import sys

def setup_script_logging(output_folder):
    log_file = os.path.join(output_folder, 'processing_log.txt')
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
        
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

def fix_punctuation(row, file_name):
    telugu = str(row.get('Telugu Text', "")).strip()
    english = str(row.get('Mapped English Text', "")).strip()
    punctuation_marks = ('.', '!', '?')
    
    # 1. Find the last Telugu Script character (\u0C00-\u0C7F)
    # This correctly finds the 'ల్' in 'ఫ్యూయల్'
    tel_chars_indices = [m.start() for m in re.finditer(r'[\u0C00-\u0C7F]', telugu)]
    
    if not tel_chars_indices:
        return telugu
    
    last_tel_idx = tel_chars_indices[-1]
    
    # 2. Check what follows the last Telugu character
    suffix = telugu[last_tel_idx + 1:].strip()
    
    # Rule: If no punctuation exists after the last Telugu character...
    if not any(p in suffix for p in punctuation_marks):
        # 3. Clean English text of [brackets] to find its punctuation
        eng_clean = re.sub(r'\[.*?\]', '', english).strip()
        match = re.search(r'[.!?]+$', eng_clean)
        
        if match:
            new_punc = match.group()
            
            # 4. Insert punctuation immediately after the last Telugu character index
            # This handles: "ఫ్యూయల్ [tags]" -> "ఫ్యూయల్. [tags]"
            updated_telugu = telugu[:last_tel_idx + 1] + new_punc + telugu[last_tel_idx + 1:]
            
            logging.info(f"[{file_name}] Row {row.get('Index', 'N/A')}: Added '{new_punc}'")
            logging.info(f"   Original: {telugu}")
            logging.info(f"   Updated : {updated_telugu}\n")
            
            return updated_telugu
                
    return telugu

def process_files(input_folder, output_folder):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    setup_script_logging(output_folder)
    csv_files = glob.glob(os.path.join(input_folder, "*.csv"))

    logging.info(f"--- Punctuation Fix Started: Found {len(csv_files)} files ---\n")

    for file_path in csv_files:
        file_name = os.path.basename(file_path)
        try:
            # Low_memory=False helps with large datasets
            df = pd.read_csv(file_path, low_memory=False)
            if 'Telugu Text' in df.columns and 'Mapped English Text' in df.columns:
                df['Telugu Text'] = df.apply(lambda row: fix_punctuation(row, file_name), axis=1)
                df.to_csv(os.path.join(output_folder, file_name), index=False)
            else:
                logging.warning(f"SKIPPED: {file_name} (Missing Columns)\n")
        except Exception as e:
            logging.error(f"Error processing {file_name}: {e}")

    logging.info("--- Process Completed ---")

if __name__ == "__main__":
    if len(sys.argv) == 3:
        process_files(sys.argv[1], sys.argv[2])