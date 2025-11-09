#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import sys
import subprocess
import threading
import queue
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# 配置
URL = "https://stock.hostmonit.com/CloudFlareYes"
ALL_IP_FILE = "yxip.txt"
BEST_IP_FILE = "best_ip.txt"
TIMEOUT = 5        # 每个 IP 测速超时（秒）
MAX_WORKERS = 50   # 并发线程数
TOP_N = 10         # 保留最快的 N 个 IP
TEST_URL = "http://cp.cloudflare.com"  # 用于测速的轻量页面

# 全局队列
result_queue = queue.PriorityQueue()

def fetch_page_with_curl():
    cmd = [
        'curl', '-s', '--compressed', '--max-time', '15',
        '-H', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        '-H', 'Accept: text/html,application/xhtml+xml',
        '-H', 'Accept-Language: en-US,en;q=0.5',
        '-H', 'Connection: keep-alive',
        URL
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        if result.returncode == 0 and len(result.stdout) > 500:
            return result.stdout
        else:
            print("curl 返回内容异常")
            return None
    except Exception as e:
        print(f"curl 失败: {e}")
        return None

def extract_ips(text):
    ipv4_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
    ipv6_pattern = r'\b(?:[0-9a-fA-F]{0,4}:){1,7}[0-9a-fA-F]{0,4}\b'

    ipv4_list = re.findall(ipv4_pattern, text)
    ipv6_list = re.findall(ipv6_pattern, text)

    valid_ipv4 = []
    for ip in ipv4_list:
        parts = list(map(int, ip.split('.')))
        if all(0 <= p <= 255 for p in parts) and not ip.startswith('0.'):
            if ip != '255.255.255.255':
                valid_ipv4.append(ip)

    valid_ipv6 = [ip for ip in ipv6_list if ':' in ip and not ip.startswith(':') and not ip.endswith(':')]

    return valid_ipv4, valid_ipv6

def test_ip_speed(ip):
    """测试单个 IP 的 HTTP 响应延迟"""
    start_time = time.time()
    cmd = [
        'curl', '-s', '-o', '/dev/null', '-w', '%{time_total}', '--max-time', str(TIMEOUT),
        '-H', 'Host: cp.cloudflare.com',
        f'http://{ip}' if ':' not in ip else f'http://[{ip}]'
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT + 2)
        if result.returncode == 0:
            total_time = float(result.stdout.strip())
            latency = round(total_time * 1000, 2)  # 毫秒
            return ip, latency
        else:
            return ip, float('inf')
    except:
        return ip, float('inf')

def main():
    print(f"正在获取 {URL} ...")
    html = fetch_page_with_curl()
    if not html:
        print("无法获取页面内容，脚本退出")
        sys.exit(1)

    print(f"页面获取成功！正在提取 IP...")
    ipv4_ips, ipv6_ips = extract_ips(html)
    all_ips = sorted(set(ipv4_ips + ipv6_ips))

    print(f"共提取 {len(all_ips)} 个 IP，开始测速（并发 {MAX_WORKERS}）...")

    # 写入全部 IP
    with open(ALL_IP_FILE, 'w', encoding='utf-8') as f:
        f.write(f"# CloudFlareYes 全量 IP\n")
        f.write(f"# 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# 共 {len(all_ips)} 个\n\n")
        for ip in all_ips:
            f.write(ip + '\n')

    print(f"全部 IP 已保存到 {ALL_IP_FILE}")

    # 测速
    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_ip = {executor.submit(test_ip_speed, ip): ip for ip in all_ips}
        for future in as_completed(future_to_ip):
            ip, latency = future.result()
            if latency != float('inf'):
                results.append((latency, ip))
                print(f"  {ip} -> {latency} ms")
            else:
                print(f"  {ip} -> 超时")

    # 排序取最快 TOP_N
    results.sort()
    best_ips = results[:TOP_N]

    # 写入最优 IP
    with open(BEST_IP_FILE, 'w', encoding='utf-8') as f:
        f.write(f"# 最快 {TOP_N} 个 CloudFlare IP\n")
        f.write(f"# 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# 测速目标: {TEST_URL}\n\n")
        for latency, ip in best_ips:
            f.write(f"{ip}  # {latency} ms\n")

    print(f"\n测速完成！最快 {min(TOP_N, len(best_ips))} 个 IP 已保存到 {BEST_IP_FILE}")

if __name__ == "__main__":
    main()
