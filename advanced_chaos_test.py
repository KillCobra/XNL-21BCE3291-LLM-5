import threading
import time
import random
import requests
import logging
import psutil
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("chaos_test_results.log"), logging.StreamHandler()]
)

# LLM Service URL
BASE_URL = "http://localhost:8080"

class ChaosTest:
    def __init__(self):
        self.running = False
        self.threads = []
        self.test_duration = 300  # 5 minutes default
    
    def start_test(self, duration=300):
        """Start chaos testing for specified duration"""
        self.test_duration = duration
        self.running = True
        
        # Start different chaos scenarios in separate threads
        self.threads = [
            threading.Thread(target=self.cpu_stress),
            threading.Thread(target=self.memory_pressure),
            threading.Thread(target=self.network_latency),
            threading.Thread(target=self.request_flooding),
            threading.Thread(target=self.error_injection)
        ]
        
        for thread in self.threads:
            thread.start()
        
        # Monitor service health during chaos
        self.monitor_service()
        
        # Wait for test duration
        time.sleep(self.test_duration)
        
        # Stop all chaos
        self.running = False
        for thread in self.threads:
            thread.join()
        
        logging.info("Chaos testing completed")
    
    def cpu_stress(self):
        """Simulate CPU stress"""
        logging.info("Starting CPU stress test")
        while self.running:
            # Simulate CPU spike for 5-15 seconds
            if random.random() < 0.3:  # 30% chance of CPU spike
                logging.info("Injecting CPU stress")
                end_time = time.time() + random.randint(5, 15)
                while time.time() < end_time and self.running:
                    # Perform CPU-intensive calculation
                    [i**2 for i in range(10000)]
            time.sleep(random.randint(10, 30))
    
    def memory_pressure(self):
        """Simulate memory pressure"""
        logging.info("Starting memory pressure test")
        while self.running:
            # Simulate memory pressure for 5-10 seconds
            if random.random() < 0.2:  # 20% chance of memory pressure
                logging.info("Injecting memory pressure")
                # Allocate large chunks of memory temporarily
                large_list = [bytearray(1024*1024) for _ in range(50)]  # ~50MB
                time.sleep(random.randint(5, 10))
                # Release memory
                large_list = None
            time.sleep(random.randint(20, 40))
    
    def network_latency(self):
        """Simulate network latency and packet loss"""
        logging.info("Starting network latency simulation")
        while self.running:
            # Simulate network issues for 10-20 seconds
            if random.random() < 0.25:  # 25% chance of network issues
                latency_type = random.choice(["delay", "loss", "corruption"])
                logging.info(f"Injecting network {latency_type}")
                
                if latency_type == "delay":
                    # Add delay to requests
                    delay_seconds = random.uniform(0.5, 3.0)
                    end_time = time.time() + random.randint(10, 20)
                    while time.time() < end_time and self.running:
                        self.delayed_request(delay_seconds)
                        time.sleep(1)
                
                elif latency_type == "loss":
                    # Simulate packet loss by dropping requests
                    end_time = time.time() + random.randint(10, 20)
                    while time.time() < end_time and self.running:
                        if random.random() < 0.3:  # 30% packet loss
                            self.send_request()  # Request might succeed
                        time.sleep(0.5)
                
                elif latency_type == "corruption":
                    # Send malformed requests
                    end_time = time.time() + random.randint(10, 20)
                    while time.time() < end_time and self.running:
                        self.corrupt_request()
                        time.sleep(0.5)
            
            time.sleep(random.randint(30, 60))
    
    def request_flooding(self):
        """Simulate request flooding (DDoS-like)"""
        logging.info("Starting request flooding simulation")
        while self.running:
            # Simulate request flood for 5-15 seconds
            if random.random() < 0.15:  # 15% chance of request flood
                logging.info("Injecting request flood")
                
                # Number of concurrent requests
                num_requests = random.randint(50, 200)
                
                # Create a thread pool and flood with requests
                with ThreadPoolExecutor(max_workers=20) as executor:
                    end_time = time.time() + random.randint(5, 15)
                    while time.time() < end_time and self.running:
                        futures = [executor.submit(self.send_request) for _ in range(num_requests)]
                        # Wait for all requests to complete
                        for future in futures:
                            try:
                                future.result(timeout=2)
                            except:
                                pass
            
            time.sleep(random.randint(60, 120))
    
    def error_injection(self):
        """Inject various error conditions"""
        logging.info("Starting error injection")
        while self.running:
            # Inject errors every 30-60 seconds
            if random.random() < 0.2:  # 20% chance of error injection
                error_type = random.choice(["malformed", "large_input", "empty", "special_chars"])
                logging.info(f"Injecting error: {error_type}")
                
                if error_type == "malformed":
                    # Send malformed JSON
                    try:
                        requests.post(f"{BASE_URL}/generate", 
                                     data="This is not valid JSON", 
                                     headers={"Content-Type": "application/json"},
                                     timeout=5)
                    except:
                        pass
                
                elif error_type == "large_input":
                    # Send extremely large prompt
                    try:
                        large_prompt = "test " * 5000  # Very large input
                        requests.post(f"{BASE_URL}/generate",
                                     json={"prompt": large_prompt, "max_length": 100},
                                     timeout=10)
                    except:
                        pass
                
                elif error_type == "empty":
                    # Send empty values
                    try:
                        requests.post(f"{BASE_URL}/generate",
                                     json={"prompt": "", "max_length": 50},
                                     timeout=5)
                    except:
                        pass
                
                elif error_type == "special_chars":
                    # Send special characters
                    try:
                        special_prompt = "!@#$%^&*()_+<>?:\"{}|~`\n\t\r"
                        requests.post(f"{BASE_URL}/generate",
                                     json={"prompt": special_prompt, "max_length": 50},
                                     timeout=5)
                    except:
                        pass
            
            time.sleep(random.randint(30, 60))
    
    def delayed_request(self, delay_seconds):
        """Send a request with artificial delay"""
        try:
            prompt = random.choice([
                "What is artificial intelligence?",
                "Explain machine learning",
                "Tell me about neural networks"
            ])
            
            # Add artificial delay
            time.sleep(delay_seconds)
            
            requests.post(f"{BASE_URL}/generate",
                         json={"prompt": prompt, "max_length": 50},
                         timeout=10)
        except:
            pass
    
    def send_request(self):
        """Send a normal request"""
        try:
            prompt = random.choice([
                "What is artificial intelligence?",
                "Explain machine learning",
                "Tell me about neural networks"
            ])
            
            requests.post(f"{BASE_URL}/generate",
                         json={"prompt": prompt, "max_length": 50},
                         timeout=5)
        except:
            pass
    
    def corrupt_request(self):
        """Send a corrupted request"""
        try:
            # Randomly corrupt the JSON structure
            corrupt_json = {
                "prmpt": "This is misspelled",  # Misspelled key
                "max_length": "not_a_number",   # Wrong type
                "extra_field": {}               # Unexpected field
            }
            
            requests.post(f"{BASE_URL}/generate",
                         json=corrupt_json,
                         timeout=5)
        except:
            pass
    
    def monitor_service(self):
        """Monitor service health during chaos testing"""
        logging.info("Starting service monitoring")
        
        monitor_thread = threading.Thread(target=self._monitor_loop)
        monitor_thread.start()
        self.threads.append(monitor_thread)
    
    def _monitor_loop(self):
        """Monitoring loop to check service health"""
        metrics = {
            "requests_total": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "response_times": []
        }
        
        start_time = time.time()
        check_interval = 5  # Check every 5 seconds
        
        while self.running:
            try:
                # Check service health
                health_start = time.time()
                health_response = requests.get(f"{BASE_URL}/health", timeout=2)
                health_time = time.time() - health_start
                
                metrics["requests_total"] += 1
                metrics["response_times"].append(health_time)
                
                if health_response.status_code == 200:
                    metrics["successful_requests"] += 1
                    
                    # Get system metrics
                    cpu_percent = psutil.cpu_percent()
                    memory_percent = psutil.virtual_memory().percent
                    
                    # Log current status
                    avg_response = sum(metrics["response_times"][-10:]) / min(len(metrics["response_times"]), 10)
                    success_rate = (metrics["successful_requests"] / metrics["requests_total"]) * 100
                    
                    logging.info(f"Service health: OK | "
                                f"CPU: {cpu_percent:.1f}% | "
                                f"Memory: {memory_percent:.1f}% | "
                                f"Avg Response: {avg_response:.3f}s | "
                                f"Success Rate: {success_rate:.1f}%")
                else:
                    metrics["failed_requests"] += 1
                    logging.warning(f"Service health check failed: {health_response.status_code}")
            
            except Exception as e:
                metrics["requests_total"] += 1
                metrics["failed_requests"] += 1
                logging.error(f"Service monitoring error: {str(e)}")
            
            # Sleep until next check
            time.sleep(check_interval)
            
            # Log summary every minute
            elapsed = time.time() - start_time
            if int(elapsed) % 60 < check_interval:
                self._log_summary(metrics, elapsed)
    
    def _log_summary(self, metrics, elapsed):
        """Log a summary of the monitoring metrics"""
        if metrics["requests_total"] > 0:
            success_rate = (metrics["successful_requests"] / metrics["requests_total"]) * 100
            avg_response = sum(metrics["response_times"]) / len(metrics["response_times"]) if metrics["response_times"] else 0
            
            logging.info(f"=== CHAOS TEST SUMMARY ({int(elapsed)}s elapsed) ===")
            logging.info(f"Total Requests: {metrics['requests_total']}")
            logging.info(f"Success Rate: {success_rate:.2f}%")
            logging.info(f"Average Response Time: {avg_response:.3f}s")
            logging.info(f"Failed Requests: {metrics['failed_requests']}")
            logging.info("=====================================")

if __name__ == "__main__":
    # Check if service is running
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("LLM service is running. Starting chaos tests...")
            
            # Run chaos test for 5 minutes
            chaos = ChaosTest()
            chaos.start_test(duration=300)
        else:
            print(f"LLM service health check failed with status code {response.status_code}")
    except Exception as e:
        print(f"Failed to connect to LLM service: {str(e)}")
        print(f"Please make sure the service is running at {BASE_URL}")