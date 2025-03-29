import json
import subprocess
import requests
import re

def get_sysstat():
    # Collect CPU stats
    cpu_stats = subprocess.run(['mpstat', '1', '1'], capture_output=True, text=True)
    
    # Collect Memory stats
    mem_stats = subprocess.run(['sar', '-r', '1', '1'], capture_output=True, text=True)
    
    # Collect Network stats
    net_stats = subprocess.run(['sar', '-n', 'DEV', '1', '1'], capture_output=True, text=True)
    
    # Collect Disk stats
    disk_stats = subprocess.run(['sar', '-d', '1', '1'], capture_output=True, text=True)
    
    # Parse CPU usage (last line contains the idle CPU %)
    cpu_usage_match = re.search(r'(\d+\.\d+)\s*$', cpu_stats.stdout.strip().split("\n")[-1])
    cpu_usage = 100.0 - float(cpu_usage_match.group(1)) if cpu_usage_match else None
    
    # Parse Memory usage
    mem_lines = mem_stats.stdout.strip().split("\n")
    if len(mem_lines) > 2:
        mem_parts = mem_lines[-1].split()
        memory_usage = {"kbmemfree": mem_parts[1], "kbmemused": mem_parts[2], "memused_percent": mem_parts[3]}
    else:
        memory_usage = {}

    # Parse Network stats
    net_lines = net_stats.stdout.strip().split("\n")[2:]  # Ignore headers
    network_usage = [{"interface": line.split()[1], "rxkB": line.split()[3], "txkB": line.split()[4]} for line in net_lines if len(line.split()) > 4]

    # Parse Disk stats
    disk_lines = disk_stats.stdout.strip().split("\n")[2:]  # Ignore headers
    disk_usage = [{"device": line.split()[1], "tps": line.split()[2], "MB_read": line.split()[3], "MB_wrtn": line.split()[4]} for line in disk_lines if len(line.split()) > 4]

    return {
        "cpu_usage_percent": cpu_usage,
        "memory": memory_usage,
        "network": network_usage,
        "disk": disk_usage
    }

def send_data(server_url):
    data = get_sysstat()
    headers = {'Content-Type': 'application/json'}
    response = requests.post(f"{server_url}/data", json=data, headers=headers)
    print("Response:", response.status_code, response.text)

if __name__ == "__main__":
    server_url = "http://107.21.161.21:8000"
    send_data(server_url)

