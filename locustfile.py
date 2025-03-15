from locust import HttpUser, task, between
import random

class LLMUser(HttpUser):
    wait_time = between(0.5, 3)  # Wait between 0.5-3 seconds between tasks
    
    @task(3)
    def generate_text(self):
        prompts = [
            "Explain artificial intelligence",
            "What is machine learning?",
            "Tell me about neural networks",
            "How do transformers work?",
            "Explain the concept of attention in deep learning"
        ]
        
        payload = {
            "prompt": random.choice(prompts),
            "max_length": random.randint(30, 100)
        }
        
        with self.client.post("/generate", json=payload, catch_response=True) as response:
            if response.status_code == 200:
                if "generated_text" in response.json():
                    response.success()
                else:
                    response.failure("Response missing generated_text")
            else:
                response.failure(f"Failed with status code: {response.status_code}")
    
    @task(1)
    def check_health(self):
        self.client.get("/health")
    
    @task(1)
    def get_model_info(self):
        self.client.get("/model-info") 