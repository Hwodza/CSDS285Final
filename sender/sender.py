import json
import subprocess
import requests
import re
import time
import uuid

def get_sysstat():
    try:
        # Collect CPU stats
        cpu_stats = subprocess.run(['mpstat', '1', '1'], capture_output=True, text=True)
        
        # Collect Memory stats
        mem_stats = subprocess.run(['sar', '-r', '1', '1'], capture_output=True, text=True)
        
        # Collect Network stats
        net_stats = subprocess.run(['sar', '-n', 'DEV', '1', '1'], capture_output=True, text=True)
        
        # Collect Disk stats
        disk_stats = subprocess.run(['sar', '-d', '1', '1'], capture_output=True, text=True)
        
        # Parse CPU usage
        cpu_usage_match = re.search(r'(\d+\.\d+)\s*$', cpu_stats.stdout.strip().split("\n")[-1])
        cpu_usage = 100.0 - float(cpu_usage_match.group(1)) if cpu_usage_match else None
        
        # Parse Memory usage
        mem_lines = mem_stats.stdout.strip().split("\n")
        if len(mem_lines) > 2:
            mem_parts = mem_lines[-1].split()
            memory_usage = {
                "kbmemfree": mem_parts[1],
                "kbmemused": mem_parts[2],
                "memused_percent": mem_parts[3]
            }
        else:
            memory_usage = {}
        result = subprocess.run(['iostat', '-dx', '1', '1'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        output = result.stdout
        lines = output.strip().split('\n')
        device_lines_started = False
        disk_stats = []

        for line in lines:
            # Look for the header that starts with "Device"
            if line.strip().startswith('Device'):
                device_lines_started = True
                continue
            if device_lines_started:
                parts = line.split()
                # Ensure line has enough columns to parse
                if len(parts) >= 12:
                    try:
                        device = parts[0]
                        wait = float(parts[9])  # "await" value
                        util = float(parts[11])  # "%util" value
                        disk_stats.append({
                            'device': device,
                            'wait': wait,
                            'util': util
                        })
                    except ValueError:
                        # Skip line if conversion fails (e.g., malformed line)
                        continue

        # Network
        result = subprocess.run(['sar', '-n', 'DEV', '1', '1'], capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split('\n')

        # Find the header and data lines
        headers = []
        data_lines = []
        for line in lines:
            if 'IFACE' in line:
                headers = line.split()
            elif line and line[0].isdigit():  # Skip timestamped lines
                continue
            elif any(dev in line for dev in ['eth', 'en', 'wl', 'lo']) and line.startswith("Average"):
                # print(line)  # common interface prefixes
                data_lines.append(line.split())

        # Print KB/s received and transmitted for each interface
        networks = []
        for line in data_lines:
            networks.append({
                'iface': line[1],
                'rx_kb': line[4],
                'tx_kb': line[5]
                })
        # Parse Network stats
        #net_lines = net_stats.stdout.strip().split("\n")[2:]  # Ignore headers
        #network_usage = [
        #    {
        #        "interface": line.split()[1], 
        #        "rxkB": line.split()[3], 
        #        "txkB": line.split()[4]
        #    } 
        #    for line in net_lines if len(line.split()) > 4
        #]

        return {
            "id": "temporary", 
            "timestamp": int(time.time()),
            "cpu_usage_percent": cpu_usage,
            "memory": memory_usage,
            "network": networks,
            "disk": disk_stats
        }
    except Exception as e:
        print(f"Error collecting system stats: {str(e)}")
        return None

def send_data(server_url):
    data = get_sysstat()
    if not data:
        print("No data collected")
        return

    headers = {'Content-Type': 'application/json'}
    try:
        # Send via HTTP POST
        http_response = requests.post(
            f"{server_url}/data", 
            json=data, 
            headers=headers,
            timeout=5
        )
        print(f"HTTP Response: {http_response.status_code} {http_response.text}")

        # Alternatively, you could also send via WebSocket
        # Uncomment below if you want WebSocket support
        """
        from websocket import create_connection
        ws = create_connection(f"ws://{server_url.split('//')[1]}")
        ws.send(json.dumps(data))
        ws.close()
        print("Data sent via WebSocket")
        """
        
    except requests.exceptions.RequestException as e:
        print(f"HTTP Request failed: {str(e)}")
    except Exception as e:
        print(f"Error sending data: {str(e)}")

if __name__ == "__main__":
    # Update this to your Node.js server address (port 8080)
    server_url = "http://107.21.161.21:8080"
    
    # For continuous monitoring (uncomment if needed)
    """
    while True:
        send_data(server_url)
        time.sleep(5)  # Send every 5 seconds
    """
    # For one-time send
    send_data(server_url)
