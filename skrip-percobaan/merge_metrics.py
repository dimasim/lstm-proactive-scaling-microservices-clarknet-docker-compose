import shutil
import os
import pandas as pd

def main():
    suffixes = ['a', 'b']
    limit_rows = 2613 # Number of rows to replace (43.5 minutes)

    print("=== Reorganizing and Merging Metrics ===")
    
    for suffix in suffixes:
        raw_csv = f"collected_metrics_{suffix}.csv"
        first_43m_csv = f"collected_metrics_{suffix}_first_43m.csv"
        backup_3day_csv = f"collected_metrics_{suffix}_3day_raw.csv"
        merged_csv = f"collected_metrics_{suffix}_merged.csv"
        
        # 1. Rename newly collected metrics to first_43m
        if os.path.exists(raw_csv):
            print(f"Renaming {raw_csv} to {first_43m_csv}...")
            shutil.move(raw_csv, first_43m_csv)
        else:
            print(f"Warning: {raw_csv} not found. Skipping rename step.")
            
        # 2. Check if backup and first_43m exist before merging
        if not os.path.exists(backup_3day_csv):
            print(f"Error: Backup file {backup_3day_csv} is missing. Cannot merge.")
            continue
        if not os.path.exists(first_43m_csv):
            print(f"Error: First 43m file {first_43m_csv} is missing. Cannot merge.")
            continue
            
        print(f"Merging {first_43m_csv} into {backup_3day_csv}...")
        
        # Load datasets
        df_3day = pd.read_csv(backup_3day_csv)
        df_43m = pd.read_csv(first_43m_csv)
        
        # Replace the first `limit_rows` in the 3-day data with the 43-minute data
        # Keep the timestamps of the 3-day data to ensure continuous timestamps
        for col in df_3day.columns:
            if col == 'timestamp':
                continue
            df_3day.loc[0:limit_rows-1, col] = df_43m.loc[0:limit_rows-1, col].values
            
        # Save merged results
        df_3day.to_csv(merged_csv, index=False)
        print(f"Merged output saved successfully to {merged_csv}!")

if __name__ == "__main__":
    main()
