#!/usr/bin/env python3
"""Scan ACP marketplace for agent activity data."""
import json
import urllib.request
import time

all_agents = []
for page in range(1, 15):
    url = (
        f"https://acpx.virtuals.gg/api/agents?keyword=&top_k=500"
        f"&graduation_status=all&online_status=all&page={page}&pageSize=25"
    )
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            agents = data.get("data", [])
            all_agents.extend(agents)
            if not agents:
                break
    except Exception as e:
        print(f"Page {page} error: {e}")
        break
    time.sleep(0.3)

print(f"Total agents fetched: {len(all_agents)}")
print()

active = [a for a in all_agents if (a.get("successfulJobCount") or 0) > 0]
graduated = [a for a in all_agents if a.get("hasGraduated")]
has_offerings = [a for a in all_agents if len(a.get("offerings", [])) > 0]

print("=== Overview ===")
print(f"Total registered: {len(all_agents)}")
print(f"With offerings (services listed): {len(has_offerings)}")
print(f"With successful jobs: {len(active)}")
print(f"Graduated: {len(graduated)}")
print()

total_jobs = sum(a.get("successfulJobCount") or 0 for a in all_agents)
total_buyers = sum(a.get("uniqueBuyerCount") or 0 for a in all_agents)
print(f"Total successful jobs across all agents: {total_jobs}")
print(f"Total unique buyers across all agents: {total_buyers}")
print()

print("=== TOP 20 by successful jobs ===")
for a in sorted(all_agents, key=lambda x: x.get("successfulJobCount") or 0, reverse=True)[:20]:
    name = a.get("name", "?")
    jobs = a.get("successfulJobCount") or 0
    buyers = a.get("uniqueBuyerCount") or 0
    rate = a.get("successRate") or 0
    balance = a.get("walletBalance", "0")
    grad = a.get("hasGraduated")
    print(f"  {name}: {jobs} jobs, {buyers} buyers, {rate}% success, balance={balance}, grad={grad}")
    for o in a.get("offerings", [])[:3]:
        oname = o.get("name", "?")
        oprice = o.get("priceUsd", "?")
        print(f"    -> {oname} (${oprice})")

print()

# Price analysis
all_prices = []
for a in all_agents:
    for o in a.get("offerings", []):
        p = o.get("priceUsd")
        if p and p > 0:
            all_prices.append(p)

if all_prices:
    print("=== Pricing ===")
    print(f"Total offerings with price: {len(all_prices)}")
    print(f"Min: ${min(all_prices)}")
    print(f"Max: ${max(all_prices)}")
    avg = sum(all_prices) / len(all_prices)
    print(f"Avg: ${avg:.2f}")
    median = sorted(all_prices)[len(all_prices) // 2]
    print(f"Median: ${median}")

print()
print("=== Service categories ===")
cats = {}
for a in all_agents:
    for o in a.get("offerings", []):
        name = (o.get("name") or "").lower()
        keywords = [
            "meme", "image", "content", "trade", "swap", "analysis",
            "research", "translate", "data", "code", "design", "write",
            "monitor", "defi", "token", "nft", "tweet", "social",
            "market", "price", "yield", "farm", "bridge"
        ]
        for kw in keywords:
            if kw in name:
                cats[kw] = cats.get(kw, 0) + 1
for k, v in sorted(cats.items(), key=lambda x: x[1], reverse=True):
    print(f"  {k}: {v} offerings")

print()
print("=== Creation timeline ===")
months = {}
for a in all_agents:
    created = a.get("createdAt", "")[:7]
    if created:
        months[created] = months.get(created, 0) + 1
for m, c in sorted(months.items()):
    print(f"  {m}: {c} agents registered")
