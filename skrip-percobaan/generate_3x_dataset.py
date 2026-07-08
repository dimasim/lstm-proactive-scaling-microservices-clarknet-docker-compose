import pandas as pd
import os

input_csv = "dataset/aggregated_clarknet_rps.csv"
output_csv = "dataset/aggregated_clarknet_rps_3x.csv"

if not os.path.exists(input_csv):
    print(f"Error: {input_csv} not found.")
    exit(1)

print(f"Reading dataset {input_csv}...")
df = pd.read_csv(input_csv)

print("Processing columns (scaling Content & Media by 3, dropping unused services)...")
df["Content_Service"] = df["Content_Service"] * 3
df["Media_Service"] = df["Media_Service"] * 3

# Drop unused columns
df = df.drop(columns=["DynamicAPI_Service", "Others"])

# Recalculate total_rps
df["total_rps"] = df["Content_Service"] + df["Media_Service"]

print(f"Saving new dataset to {output_csv}...")
df.to_csv(output_csv, index=False)
print("Finished successfully!")
