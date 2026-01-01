import pandas as pd
from pathlib import Path
import shutil
import argparse

def inject_manual_fixes(master_csv_path, split_dir, output_dir):
    master_path = Path(master_csv_path)
    split_path = Path(split_dir)
    out_path = Path(output_dir)

    # 1. Create a fresh copy of the Stage 9 folder
    if out_path.exists():
        shutil.rmtree(out_path)
    shutil.copytree(split_path, out_path)

    # 2. Load the Manual Fixes (The Source of Truth)
    try:
        df_fixes = pd.read_csv(master_path)
        # Clean up column names in case of leading/trailing spaces
        df_fixes.columns = [c.strip() for c in df_fixes.columns]
        
        # Ensure Index is treated as a string for comparison
        fix_col = 'Index' if 'Index' in df_fixes.columns else 'index'
        df_fixes[fix_col] = df_fixes[fix_col].astype(str).str.strip()
    except Exception as e:
        print(f"❌ Error reading master CSV: {e}")
        return

    # 3. Process file by file based on the 'source_file' column
    grouped = df_fixes.groupby('source_file')

    for source_file, fix_group in grouped:
        target_file = out_path / source_file
        
        if not target_file.exists():
            continue

        try:
            # Load the original split file from the new output folder
            df_orig = pd.read_csv(target_file)
            col_orig = 'Index' if 'Index' in df_orig.columns else 'index'
            df_orig[col_orig] = df_orig[col_orig].astype(str).str.strip()

            # Identify which indices in this specific file need a replacement
            indices_to_replace = set(fix_group[fix_col].unique())
            
            new_rows = []
            seen_indices = set()

            # Iterate through the original file
            for _, row in df_orig.iterrows():
                curr_idx = row[col_orig]

                if curr_idx in indices_to_replace:
                    # If this is the first time we've hit this index in the original file,
                    # insert ALL the rows from our manual fix CSV (handles manual splitting)
                    if curr_idx not in seen_indices:
                        replacements = fix_group[fix_group[fix_col] == curr_idx]
                        for _, r_row in replacements.iterrows():
                            new_rows.append({
                                'Index': r_row[fix_col],
                                'Telugu Text': r_row['Telugu Text'],
                                'Mapped English Text': r_row['Mapped English Text']
                            })
                        seen_indices.add(curr_idx)
                    else:
                        # If we already inserted the fix for this index (e.g., if the original had duplicates),
                        # we skip any subsequent original rows with the same index.
                        continue
                else:
                    # If the index is not in our "Fix List", keep the original data exactly as is
                    new_rows.append(row.to_dict())

            # 4. Overwrite the file in the new output folder
            df_final = pd.DataFrame(new_rows)
            # Match your standard column order
            final_cols = ['Index', 'Telugu Text', 'Mapped English Text']
            df_final = df_final[final_cols]
            
            df_final.to_csv(target_file, index=False, quoting=1) 
            
        except Exception as e:
            print(f"❌ Failed to update {source_file}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("master_csv")
    parser.add_argument("split_dir")
    parser.add_argument("output_dir")
    args = parser.parse_args()
    inject_manual_fixes(args.master_csv, args.split_dir, args.output_dir)