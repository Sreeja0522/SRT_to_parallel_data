import os
import subprocess
import shutil
import pandas as pd
import re
from pathlib import Path

# --- CONFIGURATION ---
PROCESS_DIR = Path("./Process_Internal_Stages") 
REPORTS_DIR = Path("./Final_Audit_Reports_Central")
FINAL_PRODUCTION_DIR = Path("./Final_Polished_Production")
CODE_DIR = Path("./codes")

def clean_tags(text):
    if not isinstance(text, str): return text
    # Removes [Brackets] and the text inside them
    return re.sub(r'\[.*?\]', '', text).strip()

def run_global_batch_injection():
    print("🚀 STARTING SMART BATCH INJECTION...")
    
    if FINAL_PRODUCTION_DIR.exists():
        shutil.rmtree(FINAL_PRODUCTION_DIR)
    FINAL_PRODUCTION_DIR.mkdir(parents=True)

    for series_folder in PROCESS_DIR.iterdir():
        if not series_folder.is_dir(): continue
        
        master_csv_file = REPORTS_DIR / f"{series_folder.name}_MASTER_AUDIT.csv"
        series_prod_path = FINAL_PRODUCTION_DIR / series_folder.name

        if not master_csv_file.exists():
            print(f"ℹ️  SKIPPING {series_folder.name}: No Master Audit found.")
            for v in ["version_clean", "version_tags"]:
                src = series_folder / v / "9_split"
                if src.exists():
                    shutil.copytree(src, series_prod_path / v, dirs_exist_ok=True)
            continue

        print(f"🛠️  INJECTING FIXES: {series_folder.name}")

        # 1. Load the Master Fixes
        df_master = pd.read_csv(master_csv_file)

        for v_name in ["version_clean", "version_tags"]:
            split_in = series_folder / v_name / "9_split"
            polished_temp = series_folder / v_name / "11_polished_final"
            
            if not split_in.exists(): continue

            # 🎯 SMART LOGIC: If we are in the Clean branch, strip tags from the fix data
            current_fix_csv = master_csv_file
            if v_name == "version_clean":
                df_clean_fix = df_master.copy()
                # Clean both Telugu and English columns just in case
                df_clean_fix['Telugu Text'] = df_clean_fix['Telugu Text'].apply(clean_tags)
                df_clean_fix['Mapped English Text'] = df_clean_fix['Mapped English Text'].apply(clean_tags)
                
                # Save a temporary cleaned CSV to use for injection
                current_fix_csv = series_folder / "temp_clean_fix.csv"
                df_clean_fix.to_csv(current_fix_csv, index=False)

            try:
                subprocess.run([
                    'python', str(CODE_DIR / "11.py"),
                    str(current_fix_csv),
                    str(split_in),
                    str(polished_temp)
                ], check=True)

                shutil.copytree(polished_temp, series_prod_path / v_name, dirs_exist_ok=True)
                print(f"  ✅ {v_name} injected (Tags {'removed' if v_name == 'version_clean' else 'kept'}).")

            except subprocess.CalledProcessError as e:
                print(f"  ❌ Injection Error for {series_folder.name} ({v_name}): {e}")
            
            # Cleanup temp file
            if v_name == "version_clean" and current_fix_csv.exists():
                os.remove(current_fix_csv)

    print(f"\n🔥 ALL SERIES PROCESSED. Results in: {FINAL_PRODUCTION_DIR}")

if __name__ == "__main__":
    run_global_batch_injection()