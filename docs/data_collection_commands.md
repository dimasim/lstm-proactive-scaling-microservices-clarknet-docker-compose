# 📋 14-Day Data Collection Commands List

Follow this step-by-step list of commands day-by-day to collect your 2-week dataset.

---

## 📅 WEEk 1: 1 Replica Configuration

Run this command **once** at the start of Week 1:
```bash
docker compose up --scale media-service=1 --scale content-service=1 -d
```

### Day-by-Day Commands:

* **Hari 1** (Starts at second 0):
  ```bash
  python3 skrip-percobaan/run_k6_test.py data_hari_1.csv 86400 0
  ```
* **Hari 2** (Starts at second 86400):
  ```bash
  python3 skrip-percobaan/run_k6_test.py data_hari_2.csv 86400 86400
  ```
* **Hari 3** (Starts at second 172800):
  ```bash
  python3 skrip-percobaan/run_k6_test.py data_hari_3.csv 86400 172800
  ```
* **Hari 4** (Starts at second 259200):
  ```bash
  python3 skrip-percobaan/run_k6_test.py data_hari_4.csv 86400 259200
  ```
* **Hari 5** (Starts at second 345600):
  ```bash
  python3 skrip-percobaan/run_k6_test.py data_hari_5.csv 86400 345600
  ```
* **Hari 6** (Starts at second 432000):
  ```bash
  python3 skrip-percobaan/run_k6_test.py data_hari_6.csv 86400 432000
  ```
* **Hari 7** (Starts at second 518400 - remaining seconds):
  ```bash
  python3 skrip-percobaan/run_k6_test.py data_hari_7.csv 86308 518400
  ```

---

## 📅 WEEk 2: 2 Replicas Configuration

Run this command **once** at the start of Week 2:
```bash
docker compose up --scale media-service=2 --scale content-service=2 -d
```

### Day-by-Day Commands:

* **Hari 8** (Replay Week 1 Day 1):
  ```bash
  python3 skrip-percobaan/run_k6_test.py data_hari_8.csv 86400 0
  ```
* **Hari 9** (Replay Week 1 Day 2):
  ```bash
  python3 skrip-percobaan/run_k6_test.py data_hari_9.csv 86400 86400
  ```
* **Hari 10** (Replay Week 1 Day 3):
  ```bash
  python3 skrip-percobaan/run_k6_test.py data_hari_10.csv 86400 172800
  ```
* **Hari 11** (Replay Week 1 Day 4):
  ```bash
  python3 skrip-percobaan/run_k6_test.py data_hari_11.csv 86400 259200
  ```
* **Hari 12** (Replay Week 1 Day 5):
  ```bash
  python3 skrip-percobaan/run_k6_test.py data_hari_12.csv 86400 345600
  ```
* **Hari 13** (Replay Week 1 Day 6):
  ```bash
  python3 skrip-percobaan/run_k6_test.py data_hari_13.csv 86400 432000
  ```
* **Hari 14** (Replay Week 1 Day 7):
  ```bash
  python3 skrip-percobaan/run_k6_test.py data_hari_14.csv 86308 518400
  ```
