import pandas as pd
import os

def split_file(filepath, prefix):
    print(f"Reading {filepath}...")
    df = pd.read_csv(filepath)
    total_len = len(df)
    print(f"Total rows: {total_len}")
    
    day_seconds = 86400
    three_days = 3 * day_seconds
    
    # 3 hari pertama (Rows 0 to 259200)
    df_part1 = df.iloc[0:three_days]
    part1_path = f"dataset/{prefix}_3days_1.csv"
    df_part1.to_csv(part1_path, index=False)
    print(f"Saved {part1_path} ({len(df_part1)} rows)")
    
    # 3 hari kedua (Rows 259200 to 518400)
    df_part2 = df.iloc[three_days:2 * three_days]
    part2_path = f"dataset/{prefix}_3days_2.csv"
    df_part2.to_csv(part2_path, index=False)
    print(f"Saved {part2_path} ({len(df_part2)} rows)")
    
    # 1 hari terakhir (Rows 518400 to end)
    df_part3 = df.iloc[2 * three_days:]
    part3_path = f"dataset/{prefix}_last_day.csv"
    df_part3.to_csv(part3_path, index=False)
    print(f"Saved {part3_path} ({len(df_part3)} rows)")

def main():
    split_file("dataset/aggregated_clarknet_rps.csv", "aggregated_clarknet_rps")
    split_file("dataset/aggregated_clarknet_rps_3x.csv", "aggregated_clarknet_rps_3x")
    print("Splitting completed successfully!")

if __name__ == "__main__":
    main()
