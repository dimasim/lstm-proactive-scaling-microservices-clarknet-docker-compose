import pandas as pd
import numpy as np
import os

# Konfigurasi Path
DATASET_PATH = "./dataset/aggregated_clarknet_rps_3x.csv"
OUTPUT_DIR = "./skenario_k6_data"

def main():
    print("Memuat dataset ClarkNet per detik...")
    df = pd.read_csv(DATASET_PATH)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.sort_values('datetime').reset_index(drop=True)
    df['total_rps'] = df['Content_Service'] + df['Media_Service']
    
    # Buat folder output jika belum ada
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # ---------------------------------------------------------
    # 1. SKENARIO LONJAKAN (FLASH CROWD) - 30 Menit
    # ---------------------------------------------------------
    # Cari detik di mana total_rps mencapai nilai maksimum absolut
    max_idx = df['total_rps'].idxmax()
    
    # Ambil 5 menit (300 detik) sebelum puncak, dan 25 menit (1500 detik) setelah puncak
    # (Total 30 menit = 1800 detik)
    start_idx_flash = max(0, max_idx - 300)
    end_idx_flash = min(len(df), start_idx_flash + 1800)
    
    df_flash = df.iloc[start_idx_flash:end_idx_flash]
    flash_path = os.path.join(OUTPUT_DIR, "skenario_lonjakan.csv")
    df_flash.to_csv(flash_path, index=False)
    print(f"[OK] Skenario Lonjakan (30 menit) diekstrak ke: {flash_path}")
    print(f"     -> RPS Puncak: {df_flash['total_rps'].max()}")
    
    # ---------------------------------------------------------
    # 2. SKENARIO PENURUNAN MENDADAK (DROP) - 15 Menit
    # ---------------------------------------------------------
    # Cari interval di mana RPS turun drastis. 
    # Kita hitung selisih RPS antara waktu sekarang dengan 5 menit ke depan
    df['rps_diff_5m'] = df['total_rps'].shift(-300) - df['total_rps']
    
    # Cari penurunan paling tajam (nilai negatif paling kecil)
    drop_idx = df['rps_diff_5m'].idxmin()
    
    # Ambil 15 menit (900 detik) dari titik mulai turun
    end_idx_drop = min(len(df), drop_idx + 900)
    df_drop = df.iloc[drop_idx:end_idx_drop].drop(columns=['rps_diff_5m'])
    
    drop_path = os.path.join(OUTPUT_DIR, "skenario_turun.csv")
    df_drop.to_csv(drop_path, index=False)
    print(f"[OK] Skenario Turun (15 menit) diekstrak ke: {drop_path}")
    
    # Bersihkan kolom bantu
    df = df.drop(columns=['rps_diff_5m'])
    
    # ---------------------------------------------------------
    # 3. SKENARIO NORMAL (STABIL) - 15 Menit
    # ---------------------------------------------------------
    # Kita cari window 15 menit (900 baris) dengan standar deviasi (fluktuasi) paling rendah,
    # tetapi rata-ratanya harus di atas 0 (misalnya di atas persentil ke-25 agar tidak mengambil data malam yang kosong).
    
    print("Mencari Skenario Normal (Bisa memakan waktu beberapa detik)...")
    # Hitung rolling mean & std per 15 menit (900 detik)
    rolling_std = df['total_rps'].rolling(window=900).std()
    rolling_mean = df['total_rps'].rolling(window=900).mean()
    
    # Tentukan batas bawah RPS agar tidak ngambil waktu sepi
    min_rps_threshold = df['total_rps'].quantile(0.30)
    
    # Filter hanya window yang rata-ratanya cukup lumayan
    valid_windows = rolling_std[rolling_mean > min_rps_threshold]
    
    if not valid_windows.empty:
        # Cari window dengan std (fluktuasi) terkecil
        normal_end_idx = valid_windows.idxmin()
        normal_start_idx = normal_end_idx - 900 + 1
        
        df_normal = df.iloc[normal_start_idx:normal_end_idx+1]
        normal_path = os.path.join(OUTPUT_DIR, "skenario_normal.csv")
        df_normal.to_csv(normal_path, index=False)
        print(f"[OK] Skenario Normal (15 menit) diekstrak ke: {normal_path}")
        print(f"     -> Rata-rata RPS: {df_normal['total_rps'].mean():.2f}, Fluktuasi (std): {df_normal['total_rps'].std():.2f}")
    else:
        print("[!] Gagal menemukan skenario normal yang sesuai.")

    print("\nSELESAI! Tiga skenario Anda sudah siap disuapkan ke K6/Locust.")

if __name__ == "__main__":
    main()
