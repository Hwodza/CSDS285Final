#!/usr/bin/env python3
import json
import subprocess
import requests
import re
import time
import uuid
import argparse
import sys
from datetime import datetime


def get_sysstat(device_id=None):
    """Collect system statistics using sysstat utilities"""
    try:
        # Generate timestamp once for consistency
        timestamp = int(time.time())

        # Collect CPU stats
        cpu_stats = subprocess.run(['mpstat', '1', '1'], capture_output=True, text=True)
        cpu_usage_match = re.search(r'(\d+\.\d+)\s*$', cpu_stats.stdout.strip().split("\n")[-1])
        cpu_usage = 100.0 - float(cpu_usage_match.group(1)) if cpu_usage_match else None

        # Collect Memory stats
        mem_stats = subprocess.run(['sar', '-r', '1', '1'], capture_output=True, text=True)
        mem_lines = mem_stats.stdout.strip().split("\n")
        if len(mem_lines) > 2:
            mem_parts = mem_lines[-1].split()
            memory_usage = {
                "kbmemfree": mem_parts[1],
                "kbmemused": mem_parts[3],
                "memused_percent": mem_parts[4]
            }
        else:
            memory_usage = {}

        # Collect Disk stats using iostat
        disk_stats = []
        iostat_result = subprocess.run(['iostat', '-dx', '1', '1'], 
                                      stdout=subprocess.PIPE, 
                                      stderr=subprocess.PIPE, 
                                      text=True)
        for line in iostat_result.stdout.strip().split('\n'):
            if line.startswith('Device'):
                continue
            parts = line.split()
            if len(parts) >= 12:
                try:
                    disk_stats.append({
                        'device': parts[0],
                        'wait': float(parts[9]),  # await
                        'util': float(parts[11])  # %util
                    })
                except (ValueError, IndexError):
                    continue

        # Collect Network stats using sar
        networks = []
        sar_result = subprocess.run(['sar', '-n', 'DEV', '1', '1'], 
                                   capture_output=True, 
                                   text=True)
        for line in sar_result.stdout.strip().split('\n'):
            if any(dev in line for dev in ['eth', 'en', 'wl', 'lo']) and line.startswith("Average"):
                parts = line.split()
                networks.append({
                    'iface': parts[1],
                    'rx_kb': parts[4],
                    'tx_kb': parts[5]
                })

        return {
            "id": device_id or str(uuid.uuid4()),
            "timestamp": timestamp,
            "cpu_usage_percent": cpu_usage,
            "memory": memory_usage,
            "network": networks,
            "disk": disk_stats
        }
    except Exception as e:
        print(f"Error collecting system stats: {str(e)}", file=sys.stderr)
        return None


def send_data(server_url, data, verbose=False):
    """Send data to monitoring server"""
    headers = {'Content-Type': 'application/json'}
    try:
        if verbose:
            print(f"Sending data to {server_url}...")
            print(json.dumps(data, indent=2))

        response = requests.post(
            f"{server_url}/data", 
            json=data, 
            headers=headers,
            timeout=5
        )

        if verbose:
            print(f"Server response: {response.status_code} {response.text}")

        return response.ok
    except requests.exceptions.RequestException as e:
        print(f"Error sending data: {str(e)}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description='System Monitoring Data Sender',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        '-s', '--server',
        default='http://107.21.161.21:8080',
        help='Monitoring server URL'
    )
    parser.add_argument(
        '-i', '--interval',
        type=int,
        default=5,
        help='Collection interval in seconds'
    )
    parser.add_argument(
        '-d', '--device-id',
        help='Custom device identifier (default: random UUID)'
    )
    parser.add_argument(
        '-c', '--count',
        type=int,
        default=0,
        help='Number of times to send data (0 for infinite)'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Collect stats but don\'t send to server'
    )
    parser.add_argument(
        '--once',
        action='store_true',
        help='Send data once and exit'
    )

    args = parser.parse_args()

    if args.once:
        args.count = 1

    try:
        sent_count = 0
        while True:
            start_time = time.time()

            data = get_sysstat(args.device_id)
            if data is None:
                time.sleep(args.interval)
                continue

            if not args.dry_run:
                success = send_data(args.server, data, args.verbose)
                if not success:
                    time.sleep(args.interval)
                    continue

            sent_count += 1
            if args.verbose:
                print(f"[{datetime.now().isoformat()}] Sent {sent_count} packets")

            if 0 < args.count <= sent_count:
                break

            # Sleep for remaining interval time
            elapsed = time.time() - start_time
            sleep_time = max(0, args.interval - elapsed)
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")
    except Exception as e:
        print(f"Fatal error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()