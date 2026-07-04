import csv
import os
import random
from locust import HttpUser, task, between

# Load unique users once at startup
users_list = []
users_path = '/mnt/locust/list_login_user_diawal.csv'
if os.path.exists(users_path):
    with open(users_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        users_list = [row['Student_ID'] for row in reader]
else:
    users_list = ['STUD0014859', 'STUD0015018']

# Load quiz attempts dataset once at startup
attempts_list = []
attempts_path = '/mnt/locust/ISTN101_quiz_attempts.csv'
if os.path.exists(attempts_path):
    with open(attempts_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        attempts_list = [row['Student_ID'] for row in reader]
else:
    attempts_list = ['STUD0014859', 'STUD0015018']

class QuickstartUser(HttpUser):
    wait_time = between(1, 2)
    attempt_index = 0

    def on_start(self):
        self.token = None
        self.student_id = random.choice(users_list)
        self.login()

    def login(self):
        # Case 1: Login to Auth Service (routes via HAProxy /auth/login)
        response = self.client.post("/auth/login", json={
            "student_id": self.student_id,
            "password": "password123"
        })
        if response.status_code == 200:
            self.token = response.json().get("access_token")
            # Set authorization header for subsequent requests
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.token = None

    @task
    def quiz_attempt(self):
        # If token is expired or not set, trigger login
        if not self.token:
            self.login()
            return

        # Case 2: Quiz operation (routes via HAProxy /quiz)
        # We can simulate sequential/random student activity from dataset
        target_student = attempts_list[QuickstartUser.attempt_index % len(attempts_list)]
        QuickstartUser.attempt_index += 1

        # Real JWT token is used
        question_id = random.choice([1, 2, 3])
        # Randomly choose correct or wrong answer to simulate student behavior
        if question_id == 1:
            selected_option = random.choice(["Central Processing Unit", "Computer Personal Unit", "Control Process Utility"])
        elif question_id == 2:
            selected_option = random.choice(["Go", "Python", "Javascript", "PHP"])
        else:
            selected_option = random.choice(["PostgreSQL", "MongoDB", "Redis"])

        response = self.client.post("/quiz", json={
            "question_id": question_id,
            "selected_option": selected_option
        }, headers=self.headers)
        
        # Periodically simulate token expiration (every 20 requests)
        if QuickstartUser.attempt_index % 20 == 0:
            self.token = None

