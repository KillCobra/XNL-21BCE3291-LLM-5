import time
import requests
import argparse
import logging
import subprocess
import os
import signal
import sys
import socket

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

def is_port_in_use(port):
    """Check if a port is in use"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def blue_green_deploy(version, port_blue=8080, port_green=8081):
    """Perform a blue/green deployment"""
    logging.info(f"Starting blue/green deployment for version {version}")
    
    # Determine which is active (blue) and which is new (green)
    blue_active = is_port_in_use(port_blue)
    green_active = is_port_in_use(port_green)
    
    if blue_active:
        logging.info(f"Blue environment is active on port {port_blue}")
    else:
        logging.info(f"Blue environment is not active")
    
    if green_active:
        logging.info(f"Green environment is active on port {port_green}")
    else:
        logging.info(f"Green environment is not active")
    
    # If neither is active, start blue
    if not blue_active and not green_active:
        logging.info("No environments active, starting blue")
        start_blue(version, port_blue)
        return
    
    # If blue is active, deploy to green
    if blue_active:
        logging.info(f"Deploying version {version} to green environment")
        
        # Stop green if it's already running
        if green_active:
            stop_green(port_green)
        
        # Start green environment
        process = start_green(version, port_green)
        
        if process:
            # Check if green is healthy
            if check_health(f"http://localhost:{port_green}"):
                logging.info("Green environment is healthy, switching traffic")
                # In a real environment, you would update load balancer/ingress here
                logging.info("Traffic switched to green environment")
                
                # Optionally stop blue after successful switch
                logging.info("Stopping blue environment")
                stop_blue(port_blue)
                logging.info("Blue/Green deployment completed successfully!")
            else:
                logging.error("Green environment failed health checks, aborting deployment")
                stop_green(port_green)
        else:
            logging.error("Failed to start green environment")
    
    # If green is active, deploy to blue
    elif green_active:
        logging.info(f"Deploying version {version} to blue environment")
        
        # Stop blue if it's already running
        if blue_active:
            stop_blue(port_blue)
        
        # Start blue environment
        process = start_blue(version, port_blue)
        
        if process:
            # Check if blue is healthy
            if check_health(f"http://localhost:{port_blue}"):
                logging.info("Blue environment is healthy, switching traffic")
                # In a real environment, you would update load balancer/ingress here
                logging.info("Traffic switched to blue environment")
                
                # Optionally stop green after successful switch
                logging.info("Stopping green environment")
                stop_green(port_green)
                logging.info("Blue/Green deployment completed successfully!")
            else:
                logging.error("Blue environment failed health checks, aborting deployment")
                stop_blue(port_blue)
        else:
            logging.error("Failed to start blue environment")

def start_blue(version, port):
    """Start the blue environment"""
    logging.info(f"Starting blue environment with version {version} on port {port}")
    
    # For local testing, actually start a Flask server
    try:
        # Clone the current app.py to a temporary version-specific file
        import shutil
        src_file = "applications/llm-service/app.py"
        dst_file = f"applications/llm-service/app_blue_{version}.py"
        shutil.copy(src_file, dst_file)
        
        # Modify the port in the copied file
        with open(dst_file, 'r') as f:
            content = f.read()
        
        content = content.replace("port=8080", f"port={port}")
        
        with open(dst_file, 'w') as f:
            f.write(content)
        
        # Start the Flask server as a subprocess
        process = subprocess.Popen(
            [sys.executable, dst_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        logging.info(f"Started blue environment with PID {process.pid}")
        
        # Give it a moment to start
        time.sleep(5)
        
        return process
    except Exception as e:
        logging.error(f"Error starting blue environment: {str(e)}")
        return None

def stop_blue(port):
    """Stop the blue environment"""
    logging.info(f"Stopping blue environment on port {port}")
    
    # Find and kill the process using the port
    try:
        if os.name == 'nt':  # Windows
            result = subprocess.run(f"netstat -ano | findstr :{port}", shell=True, capture_output=True, text=True)
            for line in result.stdout.splitlines():
                if "LISTENING" in line:
                    pid = line.strip().split()[-1]
                    subprocess.run(f"taskkill /F /PID {pid}", shell=True)
                    logging.info(f"Killed process with PID {pid}")
        else:  # Linux/Mac
            result = subprocess.run(f"lsof -i :{port} -t", shell=True, capture_output=True, text=True)
            pid = result.stdout.strip()
            if pid:
                os.kill(int(pid), signal.SIGTERM)
                logging.info(f"Killed process with PID {pid}")
    except Exception as e:
        logging.error(f"Error stopping blue environment: {str(e)}")

def start_green(version, port):
    """Start the green environment"""
    logging.info(f"Starting green environment with version {version} on port {port}")
    
    # For local testing, actually start a Flask server
    try:
        # Clone the current app.py to a temporary version-specific file
        import shutil
        src_file = "applications/llm-service/app.py"
        dst_file = f"applications/llm-service/app_green_{version}.py"
        shutil.copy(src_file, dst_file)
        
        # Modify the port in the copied file
        with open(dst_file, 'r') as f:
            content = f.read()
        
        content = content.replace("port=8080", f"port={port}")
        
        with open(dst_file, 'w') as f:
            f.write(content)
        
        # Start the Flask server as a subprocess
        process = subprocess.Popen(
            [sys.executable, dst_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        logging.info(f"Started green environment with PID {process.pid}")
        
        # Give it a moment to start
        time.sleep(5)
        
        return process
    except Exception as e:
        logging.error(f"Error starting green environment: {str(e)}")
        return None

def stop_green(port):
    """Stop the green environment"""
    logging.info(f"Stopping green environment on port {port}")
    
    # Find and kill the process using the port
    try:
        if os.name == 'nt':  # Windows
            result = subprocess.run(f"netstat -ano | findstr :{port}", shell=True, capture_output=True, text=True)
            for line in result.stdout.splitlines():
                if "LISTENING" in line:
                    pid = line.strip().split()[-1]
                    subprocess.run(f"taskkill /F /PID {pid}", shell=True)
                    logging.info(f"Killed process with PID {pid}")
        else:  # Linux/Mac
            result = subprocess.run(f"lsof -i :{port} -t", shell=True, capture_output=True, text=True)
            pid = result.stdout.strip()
            if pid:
                os.kill(int(pid), signal.SIGTERM)
                logging.info(f"Killed process with PID {pid}")
    except Exception as e:
        logging.error(f"Error stopping green environment: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Blue/Green Deployment")
    parser.add_argument("version", help="Version to deploy")
    parser.add_argument("--blue-port", type=int, default=8080, help="Blue environment port")
    parser.add_argument("--green-port", type=int, default=8081, help="Green environment port")
    
    args = parser.parse_args()
    blue_green_deploy(args.version, args.blue_port, args.green_port)