import os
import subprocess
import shutil
from pathlib import Path

# --- CONFIGURATION ---
BASE_INPUT_DIR = Path("./All_Series_Input_original")  
PROCESS_DIR = Path("./Process_Internal_Stages") 
REPORTS_DIR = Path("./Final_Audit_Reports_Central")
CODE_DIR = Path("./codes")

def orchestrate():
    PROCESS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    for series_folder in BASE_INPUT_DIR.iterdir():
        if not series_folder.is_dir(): continue
        print(f"\n🎬 STARTING SERIES: {series_folder.name}")

        # Extension Fix
        for file in series_folder.iterdir():
            if file.is_file() and not file.suffix:
                file.rename(file.with_suffix('.srt'))

        # Paths
        s2 = PROCESS_DIR / series_folder.name / "2_tel_merged"
        s3 = PROCESS_DIR / series_folder.name / "3_eng_cleaned"
        s4 = PROCESS_DIR / series_folder.name / "4_aligned"
        s4_csv_in = s4 / "TEXT_ONLY_CSV_OUTPUT"

        # Version B: Tagged (Main Audit Branch)
        v_t = PROCESS_DIR / series_folder.name / "version_tags"
        s5_t, s6_t, s7_t, s9_t = v_t/"5_polished", v_t/"6_grammar", v_t/"7_audit", v_t/"9_split"

        # Version A: Clean
        v_c = PROCESS_DIR / series_folder.name / "version_clean"
        s5_c, s6_c, s9_c = v_c/"5_polished", v_c/"6_grammar", v_c/"9_split"

        try:
            print("  [Shared] Merging and Aligning...")
            subprocess.run(['python', str(CODE_DIR / "2.py"), str(series_folder), str(s2)], check=True)
            subprocess.run(['python', str(CODE_DIR / "3.py"), str(s2), str(s3)], check=True)
            subprocess.run(['python', str(CODE_DIR / "4.py"), str(s3), str(s4)], check=True)

            print("  [Branch A] Processing Clean...")
            subprocess.run(['python', str(CODE_DIR / "5.py"), str(s4_csv_in), str(s5_c)], check=True)
            subprocess.run(['python', str(CODE_DIR / "6.py"), str(s5_c), str(s6_c)], check=True)
            subprocess.run(['python', str(CODE_DIR / "9.py"), str(s6_c), str(s9_c)], check=True)

            print("  [Branch B] Processing Tagged & Auditing...")
            subprocess.run(['python', str(CODE_DIR / "5.py"), str(s4_csv_in), str(s5_t), "--keep"], check=True)
            subprocess.run(['python', str(CODE_DIR / "6.py"), str(s5_t), str(s6_t)], check=True)
            subprocess.run(['python', str(CODE_DIR / "7.py"), str(s6_t), str(s7_t)], check=True)
            subprocess.run(['python', str(CODE_DIR / "9.py"), str(s6_t), str(s9_t)], check=True)

            # Centralized Audit Generation
            subprocess.run(['python', str(CODE_DIR / "10.py"), str(s7_t), str(s9_t), str(REPORTS_DIR)], check=True)
            
            print(f"  ✨ SUCCESS: {series_folder.name} reports ready in Central folder.")

        except subprocess.CalledProcessError as e:
            print(f"  ❌ FAILED series {series_folder.name}: {e}")

if __name__ == "__main__":
    orchestrate()