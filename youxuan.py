#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Cloudflare 官方 IPv4 → cdn-cgi/trace 判断真实落地（SG / US / JP）
alive.txt → SG + 443 → checkproxyip success → proxyipmy
两条线完全独立
"""

import requests
import ipaddress
import random
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

# ================= 配置 =================
IPV4_URL = "https://www.cloudflare.com/ips-v4"
IPS_PER_CIDR = 500
MAX_WORKERS = 50
TOP_N = 30
TRACE_TIMEOUT = 4

# dynv6
DYNV6 = {
    "SG": ("mythink.dns.army", "sKzuT7Sowr-uTpQSuS-JmY5ejAQTy8"),
    "US": ("usthink.dns.army", "sKzuT7Sowr-uTpQSuS-JmY5ejAQTy8"),
    "JP": ("jpthink.dns.army", "sKzuT7Sowr-uTpQSuS-JmY5ejAQTy8"),
}

# colo 映射
COLO_MAP = {
    "SG": {"SIN"},
    "JP": {"NRT", "HND", "KIX", "ITM", "FUK", "OSA"},
    "US": {
        "LAX", "SJC", "SEA", "ORD", "DFW",
        "IAD", "EWR", "ATL", "MIA", "DEN"
    }
}

# alive.txt
ALIVE_TXT_URL = "https://raw.githubusercontent.com/ddwx3399/Emilia/refs/heads/main/Data/alive.txt"
CHECK_PROXY_API = "https://checkproxyip.918181.xyz/check?proxyip="
PROXY_HOSTNAME = "proxyipmy.dns.army"
PROXY_TOKEN = "sKzuT7Sowr-uTpQSuS-JmY5ejAQTy8"

# =======================================


def dynv6_update(hostname, token, ip):
    url = "http://dynv6.com/api/update"
    params = {"hostname": hostname, "token": token, "ipv4": ip}
    try:
        r = requests.get(url, params=params, timeout=8)
        print(f"✅ dynv6 更新 {hostname} → {ip} | {r.text.strip()}")
    except Exception as e:
        print(f"⚠️ dynv6 更新异常 {hostname} → {ip} | {e}")


# ---------- 线路一：Cloudflare 落地 ----------
def get_cf_cidrs():
    r = requests.get(IPV4_URL, timeout=10)
    r.raise_for_status()
    return [i.strip() for i in r.text.splitlines() if i.strip()]


def expand_cidr(cidr):
    net = ipaddress.ip_network(cidr, strict=False)
    hosts = list(net.hosts())
    return random.sample(hosts, min(len(hosts), IPS_PER_CIDR))


def trace_ip(ip):
    try:
        r = requests.get(
            f"http://{ip}/cdn-cgi/trace",
            timeout=TRACE_TIMEOUT,
            headers={"Host": "www.cloudflare.com"},
        )
        if "colo=" in r.text:
            for line in r.text.splitlines():
                if line.startswith("colo="):
                    return ip, line.split("=")[1]
    except:
        pass
    return ip, None


def cloudflare_landing():
    cidrs = get_cf_cidrs()
    pool_ips = []
    for c in cidrs:
        pool_ips.extend(map(str, expand_cidr(c)))

    results = {"SG": [], "US": [], "JP": []}

    with ThreadPoolExecutor(MAX_WORKERS) as pool:
        futures = [pool.submit(trace_ip, ip) for ip in pool_ips]
        for f in as_completed(futures):
            ip, colo = f.result()
            if not colo:
                continue
            for region, colos in COLO_MAP.items():
                if any(colo.startswith(c) for c in colos) and len(results[region]) < TOP_N:
                    results[region].append(ip)

    for region, ips in results.items():
        with open(f"{region}.txt", "w") as f:
            for ip in ips:
                f.write(ip + "\n")
        if ips:
            dynv6_update(*DYNV6[region], ips[0])


# ---------- 线路二：alive.txt 反代 ----------
def update_proxy_from_alive():
    r = requests.get(ALIVE_TXT_URL, timeout=10)
    r.raise_for_status()

    for line in r.text.splitlines():
        parts = line.split(",")
        if len(parts) < 3:
            continue
        ip, port, cc = parts[:3]
        if port != "443" or cc != "SG":
            continue

        try:
            chk = requests.get(CHECK_PROXY_API + ip, timeout=6).text
            if "success" in chk:
                dynv6_update(PROXY_HOSTNAME, PROXY_TOKEN, ip)
                print("🏁 proxyipmy 完成")
                return
        except:
            continue

    print("❌ alive.txt 中未找到可用 SG 反代 IP")


# ---------------- main ----------------
def main():
    print("🚀 Cloudflare 落地 IP 任务开始")
    cloudflare_landing()

    print("\n🚀 alive.txt 反代 IP 任务开始")
    update_proxy_from_alive()

    print("\n✅ 全部任务完成")


if __name__ == "__main__":
    main()
