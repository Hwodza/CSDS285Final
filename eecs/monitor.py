#!/usr/bin/env python3
import requests
import argparse
from datetime import datetime
import textwrap
import sys

def get_all_devices(server_url):
    try:
        response = requests.get(f"{server_url}/devices")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching devices: {e}", file=sys.stderr)
        sys.exit(1)

def get_device_stats(server_url, device_id, hours=24):
    try:
        response = requests.get(
            f"{server_url}/data/{device_id}",
            params={'limit': 100, 'hours': hours}
        )
        response.raise_for_status()
        # print(response.json())
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching stats for device {device_id}: {e}", file=sys.stderr)
        sys.exit(1)

def format_timestamp(ts):
    return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

def print_stats(stats, verbose=False):
    if not stats:
        print("No statistics available for this device/time range")
        return

    latest = stats[0]  # Most recent entry is first
    
    print(f"\n Device: {latest['device_id']}")
    print(f"  Last Updated: {format_timestamp(latest['timestamp'])}")
    print("\n System Metrics:")
    print(f"  CPU Usage: {latest['cpu_usage_percent']:.1f}%")
    print(f"  Memory: {latest['memused_percent']}% used")
    print(f"    Free: {latest['kbmemfree']} KB")
    print(f"    Used: {latest['kbmemused']} KB")

    print("\n Network Interfaces:")
    for iface in latest['network']:
        print(f"  {iface['iface']}:")
        print(f"    ▼ Received: {iface['rx_kb']} KB/s")
        print(f"    ▲ Transmitted: {iface['tx_kb']} KB/s")

    print("\n Disk Activity:")
    for disk in latest['disk']:
        print(f"  {disk['device']}:")
        print(f"    Wait: {disk['wait']:.1f}ms")
        print(f"    Utilization: {disk['util']:.1f}%")

    if verbose and len(stats) > 1:
        print("\n Historical Data:")
        print(textwrap.dedent("""
        Time                 CPU%  Memory%  Net(RX/TX)       Disk(Util%)
        ----------------------------------------------------------------"""))
        for entry in stats[:10]:  # Show first 10 entries
            net_stats = "/".join(
                f"{iface['rx_kb']}/{iface['tx_kb']}" 
                for iface in entry['network']
            )
            disk_stats = "/".join(
                f"{disk['util']:.1f}" 
                for disk in entry['disk']
            )
            print(f"{format_timestamp(entry['timestamp'])}  "
                  f"{entry['cpu_usage_percent']:>5.1f}%  "
                  f"{entry['memused_percent']:>7}%  "
                  f"{net_stats:>15}  "
                  f"{disk_stats:>15}")

def main():
    parser = argparse.ArgumentParser(
        description='Fetch and display device statistics from monitoring server',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        '-s', '--server',
        default='http://107.21.161.21:8080',
        help='Monitoring server URL'
    )
    parser.add_argument(
        '-d', '--device',
        help='Show only this device ID'
    )
    parser.add_argument(
        '-t', '--hours',
        type=int,
        default=24,
        help='Time range in hours to fetch history for'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show historical data'
    )
    parser.add_argument(
        '-l', '--list',
        action='store_true',
        help='List all available devices and exit'
    )
    
    args = parser.parse_args()

    if args.list:
        devices = get_all_devices(args.server)
        print("Available devices:")
        for device in devices:
            print(f"  - {device}")
        return

    if args.device:
        device_ids = [args.device]
    else:
        device_ids = get_all_devices(args.server)

    for device_id in device_ids:
        stats = get_device_stats(args.server, device_id, args.hours)
        print_stats(stats, args.verbose)

if __name__ == '__main__':
    main()
