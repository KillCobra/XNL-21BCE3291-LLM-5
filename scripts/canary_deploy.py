import time
import requests
import argparse
import logging
import random

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def check_health(url, max_retries=10, retry_interval=3):
    """Check if a service is healthy"""
    for i in range(max_retries):
        try:
            response = requests.get(f"{url}/health", timeout=5)
            if response.status_code == 200:
                return True
        except:
            pass
        
        logging.info(f"Health check failed, retrying in {retry_interval}s ({i+1}/{max_retries})")
        time.sleep(retry_interval)
    
    return False

def canary_deploy(version, steps=5, step_interval=60, port_stable=8080, port_canary=8081):
    """Perform a canary deployment"""
    logging.info(f"Starting canary deployment for version {version}")
    
    # Start canary environment
    logging.info(f"Deploying canary environment with version {version} on port {port_canary}")
    # In a real environment, you would deploy a container or pod here
    logging.info(f"docker run -d -p {port_canary}:8080 --name llm-canary llm-service:{version}")
    
    # Check if canary is healthy
    if not check_health(f"http://localhost:{port_canary}"):
        logging.error("Canary environment failed health checks, aborting deployment")
        logging.info("docker stop llm-canary && docker rm llm-canary")
        return
    
    # Gradually shift traffic to canary
    for step in range(1, steps + 1):
        canary_percent = (step / steps) * 100
        logging.info(f"Shifting {canary_percent:.1f}% traffic to canary")
        
        # Simulate traffic for monitoring
        simulate_traffic(port_stable, port_canary, canary_percent)
        
        # In a real environment, you would update ingress/load balancer weights here
        
        # Wait and monitor
        logging.info(f"Monitoring canary for {step_interval} seconds")
        if not monitor_canary(port_canary, step_interval):
            logging.error("Canary monitoring failed, rolling back")
            logging.info("Shifting 100% traffic back to stable")
            # In a real environment, you would update ingress/load balancer weights here
            logging.info("docker stop llm-canary && docker rm llm-canary")
            return
    
    # Canary successful, complete the deployment
    logging.info("Canary deployment successful, completing deployment")
    logging.info("Stopping stable environment")
    # In a real environment, you would stop the stable environment here
    logging.info("docker stop llm-stable && docker rm llm-stable")
    
    # Rename canary to stable
    logging.info("Promoting canary to stable")
    # In a real environment, you would update labels/selectors here
    logging.info("docker rename llm-canary llm-stable")

def simulate_traffic(port_stable, port_canary, canary_percent):
    """Simulate traffic distribution between stable and canary"""
    total_requests = 100
    canary_requests = int(total_requests * (canary_percent / 100))
    stable_requests = total_requests - canary_requests
    
    logging.info(f"Simulating traffic: {stable_requests} requests to stable, {canary_requests} requests to canary")
    
    # Simulate requests to both environments
    canary_success = 0
    stable_success = 0
    
    for _ in range(canary_requests):
        try:
            response = requests.post(
                f"http://localhost:{port_canary}/generate",
                json={"prompt": "Canary test", "max_length": 50},
                timeout=5
            )
            if response.status_code == 200:
                canary_success += 1
        except:
            pass
    
    for _ in range(stable_requests):
        try:
            response = requests.post(
                f"http://localhost:{port_stable}/generate",
                json={"prompt": "Stable test", "max_length": 50},
                timeout=5
            )
            if response.status_code == 200:
                stable_success += 1
        except:
            pass
    
    canary_success_rate = (canary_success / canary_requests) * 100 if canary_requests > 0 else 0
    stable_success_rate = (stable_success / stable_requests) * 100 if stable_requests > 0 else 0
    
    logging.info(f"Canary success rate: {canary_success_rate:.1f}%")
    logging.info(f"Stable success rate: {stable_success_rate:.1f}%")
    
    return canary_success_rate >= 95  # Require 95% success rate

def monitor_canary(port_canary, duration):
    """Monitor canary for a specified duration"""
    start_time = time.time()
    end_time = start_time + duration
    
    check_interval = 5  # Check every 5 seconds
    success_threshold = 0.95  # 95% success rate required
    
    total_checks = 0
    successful_checks = 0
    
    while time.time() < end_time:
        try:
            # Check health
            health_response = requests.get(f"http://localhost:{port_canary}/health", timeout=2)
            
            # Send test request
            test_response = requests.post(
                f"http://localhost:{port_canary}/generate",
                json={"prompt": "Monitoring test", "max_length": 50},
                timeout=5
            )
            
            total_checks += 1
            if health_response.status_code == 200 and test_response.status_code == 200:
                successful_checks += 1
                logging.info("Canary check successful")
            else:
                logging.warning(f"Canary check failed: Health={health_response.status_code}, Test={test_response.status_code}")
        
        except Exception as e:
            total_checks += 1
            logging.warning(f"Canary check failed: {str(e)}")
        
        time.sleep(check_interval)
    
    success_rate = successful_checks / total_checks if total_checks > 0 else 0
    logging.info(f"Canary monitoring complete: {success_rate:.1f}% success rate ({successful_checks}/{total_checks})")
    
    return success_rate >= success_threshold

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Canary Deployment")
    parser.add_argument("version", help="Version to deploy")
    parser.add_argument("--steps", type=int, default=5, help="Number of traffic shift steps")
    parser.add_argument("--interval", type=int, default=60, help="Interval between steps (seconds)")
    parser.add_argument("--stable-port", type=int, default=8080, help="Stable environment port")
    parser.add_argument("--canary-port", type=int, default=8081, help="Canary environment port")
    
    args = parser.parse_args()
    canary_deploy(args.version, args.steps, args.interval, args.stable_port, args.canary_port) 