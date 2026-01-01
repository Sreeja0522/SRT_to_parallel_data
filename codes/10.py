import pandas as pd
import argparse
from pathlib import Path

def extract_audited_lines(audit_dir, split_dir, central_reports_dir):
    audit_path = Path(audit_dir)
    split_path = Path(split_dir)
    central_out = Path(central_reports_dir)
    
    central_out.mkdir(parents=True, exist_ok=True)
    all_matched_rows = []

    # Iterate through audit files (e.g., audit_ep1.csv)
    for a_file in audit_path.glob("*.csv"):
        original_filename = a_file.name.replace("audit_", "")
        target_split_file = split_path / original_filename

        if not target_split_file.exists():
            continue

        try:
            df_audit = pd.read_csv(a_file)
            col_a = 'Index' if 'Index' in df_audit.columns else 'index'
            if col_a not in df_audit.columns: continue
            
            flagged_indices = set(df_audit[col_a].astype(str).str.strip().tolist())
            if not flagged_indices: continue

            df_split = pd.read_csv(target_split_file)
            col_s = 'Index' if 'Index' in df_split.columns else 'index'
            
            if col_s in df_split.columns:
                df_split['temp_idx'] = df_split[col_s].astype(str).str.strip()
                
                # Filter only the flagged rows
                match = df_split[df_split['temp_idx'].isin(flagged_indices)].copy()
                
                if not match.empty:
                    match.drop(columns=['temp_idx'], inplace=True)
                    match['source_file'] = original_filename
                    all_matched_rows.append(match)

        except Exception as e:
            print(f"❌ Error processing {a_file.name}: {e}")

    if all_matched_rows:
        combined_df = pd.concat(all_matched_rows, ignore_index=True)
        # Assumes structure: ./Process_Internal_Stages/SeriesName/version_tags/7_audit
        series_name = audit_path.parents[1].name 
        
        output_file = central_out / f"{series_name}_MASTER_AUDIT.csv"
        combined_df.to_csv(output_file, index=False)
        print(f"✅ Created Master Report: {output_file.name} ({len(combined_df)} lines)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("audit_dir")
    parser.add_argument("split_dir")
    parser.add_argument("central_reports_dir")
    args = parser.parse_args()
    extract_audited_lines(args.audit_dir, args.split_dir, args.central_reports_dir)