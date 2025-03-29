import json
import subprocess
import requests

def get_sysstat():
    # Collect CPU stats
    cpu_stats = subprocess.run(['mpstat', '1', '1', '-o', 'JSON'], capture_output=True, text=True)
    cpu_data = json.loads(cpu_stats.stdout) if cpu_stats.stdout else {}
    
    # Collect Memory stats
    mem_stats = subprocess.run(['sar', '-r', '1', '1', '-o', 'JSON'], capture_output=True, text=True)
    mem_data = json.loads(mem_stats.stdout) if mem_stats.stdout else {}
    
    # Collect Network stats
    net_stats = subprocess.run(['sar', '-n', 'DEV', '1', '1', '-o', 'JSON'], capture_output=True, text=True)
    net_data = json.loads(net_stats.stdout) if net_stats.stdout else {}
    
    # Collect Disk stats
    disk_stats = subprocess.run(['sar', '-d', '1', '1', '-o', 'JSON'], capture_output=True, text=True)
    disk_data = json.loads(disk_stats.stdout) if disk_stats.stdout else {}
    
    return {
        "cpu": cpu_data,
        "memory": mem_data,
        "network": net_data,
        "disk": disk_data
    }

def send_data(server_url):
    data = get_sysstat()
    headers = {'Content-Type': 'application/json'}
    response = requests.post(f"{server_url}/data", json=data, headers=headers)
    print("Response:", response.status_code, response.text)

if __name__ == "__main__":
    server_url = "http://your-server-ip:5000"  # Replace with the actual IP of the Flask server
    send_data(server_url)

