import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Konfigurasi Tema
sns.set_theme(style="darkgrid")
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['axes.labelsize'] = 12

def generate_dashboard():
    csv_file = 'k6_20min_full_with_preds.csv'
    if not os.path.exists(csv_file):
        print(f"File {csv_file} tidak ditemukan!")
        return
        
    df = pd.read_csv(csv_file)
    
    # 1. Menyelaraskan Prediksi (Shift +1)
    # Prediksi yang dieksekusi model pada detik T sebenarnya ditujukan untuk detik T+1.
    # Oleh karena itu, kita geser kolom prediksi 1 detik ke depan agar sejajar secara visual dengan beban riil.
    df['aligned_pred_media'] = df['predicted_rps_media'].shift(1)
    df['aligned_pred_content'] = df['predicted_rps_content'].shift(1)
    df['aligned_target_rep_media'] = df['target_replicas_media'].shift(1)
    
    # Supaya grafiknya tidak terlalu berdesakan (karena 1200 detik sangat padat),
    # kita bisa memotong (slice) bagian paling menarik saja, misal 5 menit puncak (300 detik).
    # Namun untuk sidang, kita plot keseluruhan 20 menit!
    
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(16, 12), sharex=True)
    
    time_seconds = range(len(df))
    
    # --- PANEL 1: WORKLOAD (Actual vs Predicted) ---
    ax1.plot(time_seconds, df['rps_media'], label='Actual RPS (Demand)', color='#2ca02c', linewidth=2)
    ax1.plot(time_seconds, df['aligned_pred_media'], label='Predicted RPS (LSTM)', color='#ff7f0e', linestyle='--', linewidth=2)
    ax1.set_title('Panel 1: Workload Arrival vs LSTM Prediction (Media Service)')
    ax1.set_ylabel('Requests per Second (RPS)')
    ax1.legend(loc='upper left')
    
    # --- PANEL 2: AUTO-SCALING REPLICAS ---
    ax2.plot(time_seconds, df['replicas_media'], label='Active Replicas (Supply)', color='#1f77b4', linewidth=2, drawstyle='steps-post')
    ax2.plot(time_seconds, df['aligned_target_rep_media'], label='Target Replicas (Calculated)', color='#d62728', linestyle=':', linewidth=2, drawstyle='steps-post')
    ax2.set_title('Panel 2: Proactive Auto-scaling Supply (Media Service)')
    ax2.set_ylabel('Total Containers')
    ax2.legend(loc='upper left')
    ax2.set_ylim(bottom=0)
    
    # --- PANEL 3: SLA LATENCY ---
    ax3.plot(time_seconds, df['latency_media'], label='P95 Latency', color='#9467bd', linewidth=1.5)
    ax3.axhline(y=500, color='r', linestyle='-', linewidth=2, label='SLA Threshold (500ms)')
    ax3.set_title('Panel 3: Service Level Agreement (SLA) Compliance')
    ax3.set_ylabel('Latency (ms)')
    ax3.set_xlabel('Time (Seconds)')
    ax3.legend(loc='upper left')
    # Limit y-axis if needed to make 500ms visible
    max_lat = df['latency_media'].max()
    ax3.set_ylim(0, max(600, min(max_lat + 100, 1000))) 
    
    plt.tight_layout()
    output_filename = 'dashboard_sidang_media_service.png'
    plt.savefig(output_filename, dpi=300)
    print(f"Dashboard berhasil dibuat: {output_filename}")

if __name__ == "__main__":
    generate_dashboard()
