import csv
import os
from locust import HttpUser, task, between, LoadTestShape

CSV_PATH = "/mnt/locust/aggregated_clarknet_rps.csv"

class ClarkNetUser(HttpUser):
    # Set thin wait time so users send requests rapidly, allowing the shape class to control the load
    wait_time = between(0.01, 0.05)

    @task(3)
    def get_media(self):
        self.client.get("/media")

    @task(1)
    def get_content(self):
        self.client.get("/content")

class ClarkNetWorkloadShape(LoadTestShape):
    """
    A custom LoadTestShape that reads the second-by-second RPS profile from the dataset
    and dynamically sets the number of concurrent Locust users to match the workload shape.
    """
    def __init__(self):
        super().__init__()
        self.user_points = []
        
        # Resolve path inside the Docker mount
        dataset_path = CSV_PATH
        if not os.path.exists(dataset_path):
            # Fallback path for local testing
            dataset_path = "dataset/aggregated_clarknet_rps.csv"

        if os.path.exists(dataset_path):
            try:
                with open(dataset_path, mode='r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        media_val = int(row.get("Media_Service", 0))
                        content_val = int(row.get("Content_Service", 0))
                        total_rps = media_val + content_val
                        
                        # Set target users. As wait_time is ~0.03s, one user generates ~30 requests/sec.
                        # We scale target users proportionally to match the shape.
                        target_users = max(1, int(total_rps * 1.5))
                        self.user_points.append(target_users)
            except Exception as e:
                print(f"Error reading dataset in shape: {e}")
        
        if not self.user_points:
            # Fallback curve if dataset is missing
            self.user_points = [5, 10, 20, 35, 50, 35, 20, 10, 5]

    def tick(self):
        run_time = int(self.get_run_time())
        if run_time < len(self.user_points):
            user_count = self.user_points[run_time]
            # Spawn rate represents how many users to add/remove per second
            return (user_count, max(5, int(user_count / 2)))
        return None
