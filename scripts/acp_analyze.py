#!/usr/bin/env python3
"""Analyze ACP agent data from downloaded JSON pages."""
import json
import glob

all_agents = []
for f in sorted(glob.glob("/tmp/acp_page_*.json")):
    with open(f) as fh:
        try:
            data = json.load(fh)
            agents = data.get("data", [])
            all_agents.extend(agents)
        except Exception:
            pass

print(f"Total agents: {len(all_agents)}")

active = [a for a in all_agents if (a.get("successfulJobCount") or 0) > 0]
has_offerings = [a for a in all_agents if len(a.get("offerings", [])) > 0]
graduated = [a for a in all_agents if a.get("hasGraduated")]

print(f"With offerings: {len(has_offerings)}")
print(f"With successful jobs: {len(active)}")
print(f"Graduated: {len(graduated)}")
print()

total_jobs = sum(a.get("successfulJobCount") or 0 for a in all_agents)
total_buyers = sum(a.get("uniqueBuyerCount") or 0 for a in all_agents)
print(f"Total successful jobs: {total_jobs}")
print(f"Total unique buyers: {total_buyers}")
print()

print("=== TOP 20 by jobs ===")
for a in sorted(all_agents, key=lambda x: x.get("successfulJobCount") or 0, reverse=True)[:20]:
    name = a.get("name", "?")
    jobs = a.get("successfulJobCount") or 0
    buyers = a.get("uniqueBuyerCount") or 0
    rate = a.get("successRate") or 0
    bal = a.get("walletBalance", "0")
    print(f"  {name}: {jobs} jobs, {buyers} buyers, {rate}% rate, bal={bal}")
    for o in a.get("offerings", [])[:2]:
        oname = o.get("name", "?")
        oprice = o.get("priceUsd", "?")
        print(f"    -> {oname} (${oprice})")

print()
all_prices = []
for a in all_agents:
    for o in a.get("offerings", []):
        p = o.get("priceUsd")
        if p and p > 0:
            all_prices.append(p)

if all_prices:
    print(f"=== Pricing ({len(all_prices)} offerings) ===")
    avg = sum(all_prices) / len(all_prices)
    print(f"Min: ${min(all_prices)}, Max: ${max(all_prices)}, Avg: ${avg:.2f}")
    median = sorted(all_prices)[len(all_prices) // 2]
    print(f"Median: ${median}")

print()
months = {}
for a in all_agents:
    created = a.get("createdAt", "")[:7]
    if created:
        months[created] = months.get(created, 0) + 1
print("=== Registration timeline ===")
for m, c in sorted(months.items()):
    bar = "#" * c
    print(f"  {m}: {c:3d} {bar}")

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
            "market", "price", "yield", "farm", "bridge", "pizza"
        ]
        for kw in keywords:
            if kw in name:
                cats[kw] = cats.get(kw, 0) + 1
for k, v in sorted(cats.items(), key=lambda x: x[1], reverse=True):
    print(f"  {k}: {v}")
