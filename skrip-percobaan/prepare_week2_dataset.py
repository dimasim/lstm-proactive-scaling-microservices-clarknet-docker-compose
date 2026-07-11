import os
import gzip
import urllib.request
from datetime import datetime
import pandas as pd

URL = "https://ita.ee.lbl.gov/traces/clarknet_access_log_Sep4.gz"
GZ_PATH = "dataset/clarknet_access_log_Sep4.gz"
LOG_PATH = "dataset/clarknet_access_log_Sep4"
OUTPUT_CSV = "dataset/aggregated_clarknet_rps_week2_3x.csv"

def download_file():
    if not os.path.exists(GZ_PATH):
        print(f"Downloading Week 2 log from {URL}...")
        os.makedirs(os.path.dirname(GZ_PATH), exist_ok=True)
        urllib.request.urlretrieve(URL, GZ_PATH)
        print("Download completed.")
    else:
        print("Week 2 gz log already exists.")

def decompress_file():
    if not os.path.exists(LOG_PATH):
        print(f"Decompressing {GZ_PATH} to {LOG_PATH}...")
        with gzip.open(GZ_PATH, 'rb') as f_in:
            with open(LOG_PATH, 'wb') as f_out:
                f_out.write(f_in.read())
        print("Decompression completed.")
    else:
        print("Uncompressed Week 2 log already exists.")

def parse_log():
    print(f"Parsing log file: {LOG_PATH}...")
    data = []
    html_exts = {'html', 'htm', 'txt', 'shtml', 'no_ext'}
    image_exts = {'gif', 'jpg', 'jpeg', 'xbm', 'png'}
    
    with open(LOG_PATH, 'r', encoding='latin1') as f:
        for i, line in enumerate(f):
            try:
                parts = line.split('"')
                ts_start = parts[0].find('[') + 1
                ts_end = parts[0].find(']')
                ts_str = parts[0][ts_start:ts_end-6]
                dt = datetime.strptime(ts_str, '%d/%b/%Y:%H:%M:%S')
                
                req_parts = parts[1].split()
                filename = req_parts[1]
                
                ext = filename.split('.')[-1].split('?')[0].lower() if '.' in filename else 'no_ext'
                
                service = 'Others'
                if ext in html_exts:
                    service = 'Content_Service'
                elif ext in image_exts:
                    service = 'Media_Service'
                
                if service != 'Others':
                    data.append((dt, service))
            except Exception:
                continue
            if (i + 1) % 500000 == 0:
                print(f"Processed {i + 1} lines...")
                
    df = pd.DataFrame(data, columns=['datetime', 'service'])
    df.set_index('datetime', inplace=True)
    df.sort_index(inplace=True)
    
    print(f"Total parsed log rows: {len(df)}")
    return df

def aggregate_and_scale(df):
    print("Resampling and calculating RPS per second...")
    # Generate full second range to ensure no seconds are missing
    start_time = df.index.min()
    end_time = df.index.max()
    full_range = pd.date_range(start=start_time, end=end_time, freq='1s')
    
    # Calculate sizes
    content_rps = df[df['service'] == 'Content_Service'].resample('1s').size().reindex(full_range, fill_value=0)
    media_rps = df[df['service'] == 'Media_Service'].resample('1s').size().reindex(full_range, fill_value=0)
    
    rps_df = pd.DataFrame({
        'Content_Service': content_rps,
        'Media_Service': media_rps
    })
    
    print("Scaling Content and Media services by 3x (aggregated triply)...")
    rps_df['Content_Service'] = rps_df['Content_Service'] * 3
    rps_df['Media_Service'] = rps_df['Media_Service'] * 3
    rps_df['total_rps'] = rps_df['Content_Service'] + rps_df['Media_Service']
    
    # Format index
    rps_df.index.name = 'datetime'
    
    print(f"Saving dataset to {OUTPUT_CSV}...")
    rps_df.to_csv(OUTPUT_CSV)
    print("Completed successfully!")

def main():
    download_file()
    decompress_file()
    df = parse_log()
    aggregate_and_scale(df)

if __name__ == '__main__':
    main()
