#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cloudflare 官方 IPv4 → 每段 500 IP → 测速 → 能用的写入 yxip.txt（纯 IPv4）
"""

import requests
import ipaddress
import subprocess
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==================== 配置 ====================
IPV4_URL = "https://www.cloudflare.com/ips-v4"
OUTPUT_FILE = "yxip.txt"
TIMEOUT = 6              # 测速超时（秒）
MAX_WORKERS = 150        # 并发测速
IPS_PER_CIDR = 500       # 每个 CIDR 取 500 个 IP
# ==============================================

def get_ipv4_cidrs():
    """获取官方 IPv4 CIDR 列表"""
    try:
        r = requests.get(IPV4_URL, timeout=10)
        r.raise_for_status()
        return [line.strip() for line in r.text.strip().split('\n') if line.strip()]
    except Exception as e:
        print(f"获取 CIDR 失败: {e}")
        return []

def expand_cidr_random(cidr, count=IPS_PER_CIDR):
    """从 CIDR 随机取 count 个主机 IP"""
    try:
        net = ipaddress.ip_network(cidr, strict=False)
        if net.num_addresses <= 2:
            return []
        # 取主机 IP
        hosts = list(net.hosts())
        if len(hosts) <= count:
            return [str(ip) for ip in hosts]
        return [str(ip) for ip in random.sample(hosts, count)]
    except:
        return []

def test_ip(ip):
    """测速：返回 (延迟ms, IP) 或 (inf, ip)"""
    cmd = ['curl', '-s', '-o', '/dev/null', '-w', '%{time_total}', '--max-time', str(TIMEOUT), f"http://{ip}"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT + 2)
        if result.returncode == 0:
            latency = round(float(result.stdout.strip()) * 1000, 2)
            return latency, ip
        return float('inf'), ip
    except:
        return float('inf'), ip

def main():
    print("正在获取 Cloudflare 官方 IPv4 CIDR...")
    cidrs = get_ipv4_cidrs()
    if not cidrs:
        print("获取 CIDR 失败")
        return

    print(f"共 {len(cidrs)} 个 CIDR，开始展开 IP（每段 {IPS_PER_CIDR} 个）...")
    all_ips = []
    for i, cidr in enumerate(cidrs, 1):
        ips = expand_cidr_random(cidr, IPS_PER_CIDR)
        all_ips.extend(ips)
        print(f"  [{i:2d}/{len(cidrs)}] {cidr} → {len(ips)} IPs")

    if not all_ips:
        print("未生成任何 IP")
        return

    print(f"\n总计 {len(all_ips)} 个 IPv4，开始测速（并发 {MAX_WORKERS}）...")
    usable_ips = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(test_ip, ip): ip for ip in all_ips}
        for future in as_completed(futures):
            lat, ip = future.result()
            if lat != float('inf'):
                usable_ips.append((lat, ip))
                print(f"  {ip} → {lat} ms")
            else:
                print(f"  {ip} → 超时")

    # 排序（可选）
    usable_ips.sort()

    # 只写入能用的 IP（有速度）
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for _, ip in usable_ips:
            f.write(ip + '\n')

    print(f"\n完成！{len(usable_ips)} 个可用 IPv4 已写入 → {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
