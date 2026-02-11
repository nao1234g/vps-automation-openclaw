#!/usr/bin/env python3
"""
Multi-Agent Cost Calculator
各エージェントの使用量からリアルタイムでコスト試算
"""

import sys
from datetime import datetime

# 料金表（Input/Output per 1M tokens）
PRICING = {
    "anthropic/claude-opus-4": {"input": 15.0, "output": 75.0},
    "anthropic/claude-sonnet-4": {"input": 3.0, "output": 15.0},
    "anthropic/claude-haiku-4": {"input": 0.25, "output": 1.25},
    "openai/gpt-4o": {"input": 2.5, "output": 10.0},
    "google/gemini-1.5-pro": {"input": 1.25, "output": 5.0},
    "google/gemini-2.0-flash": {"input": 0.075, "output": 0.30},
}

# エージェント→モデルマッピング
AGENTS = {
    "jarvis-cso": {"model": "anthropic/claude-opus-4", "name": "Jarvis (CSO)"},
    "alice-researcher": {"model": "anthropic/claude-haiku-4", "name": "Alice (Research)"},
    "codex-developer": {"model": "openai/gpt-4o", "name": "CodeX (Developer)"},
    "pixel-designer": {"model": "google/gemini-1.5-pro", "name": "Pixel (Designer)"},
    "luna-writer": {"model": "anthropic/claude-sonnet-4", "name": "Luna (Writer)"},
    "scout-data": {"model": "google/gemini-2.0-flash", "name": "Scout (Data)"},
    "guard-security": {"model": "anthropic/claude-haiku-4", "name": "Guard (Security)"},
}

def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """コスト計算"""
    if model not in PRICING:
        return 0.0
    
    pricing = PRICING[model]
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    
    return input_cost + output_cost

def format_currency(usd: float) -> str:
    """通貨フォーマット"""
    jpy = usd * 150  # 1ドル=150円
    return f"${usd:,.2f} (¥{jpy:,.0f})"

def main():
    print("=" * 70)
    print("Multi-Agent Cost Calculator - Monthly Estimate")
    print("=" * 70)
    print()
    
    # サンプル使用量（1ヶ月）
    usage_scenarios = {
        "軽量使用（個人開発）": {
            "jarvis-cso": {"input": 200_000, "output": 100_000},
            "alice-researcher": {"input": 300_000, "output": 100_000},
            "codex-developer": {"input": 300_000, "output": 180_000},
            "luna-writer": {"input": 400_000, "output": 200_000},
            "scout-data": {"input": 300_000, "output": 100_000},
            "pixel-designer": {"input": 150_000, "output": 50_000},
            "guard-security": {"input": 150_000, "output": 50_000},
        },
        "中規模使用（スタートアップ）": {
            "jarvis-cso": {"input": 600_000, "output": 300_000},
            "alice-researcher": {"input": 1_000_000, "output": 300_000},
            "codex-developer": {"input": 1_200_000, "output": 800_000},
            "luna-writer": {"input": 1_500_000, "output": 600_000},
            "scout-data": {"input": 1_000_000, "output": 400_000},
            "pixel-designer": {"input": 500_000, "output": 200_000},
            "guard-security": {"input": 400_000, "output": 200_000},
        },
        "重度使用（フル活用）": {
            "jarvis-cso": {"input": 2_000_000, "output": 1_000_000},
            "alice-researcher": {"input": 3_000_000, "output": 1_000_000},
            "codex-developer": {"input": 4_000_000, "output": 2_500_000},
            "luna-writer": {"input": 3_500_000, "output": 1_500_000},
            "scout-data": {"input": 3_000_000, "output": 1_000_000},
            "pixel-designer": {"input": 1_500_000, "output": 600_000},
            "guard-security": {"input": 1_000_000, "output": 400_000},
        },
    }
    
    for scenario_name, usage in usage_scenarios.items():
        print(f"\n📊 {scenario_name}")
        print("-" * 70)
        
        total_cost = 0.0
        
        for agent_id, tokens in usage.items():
            agent_info = AGENTS[agent_id]
            model = agent_info["model"]
            name = agent_info["name"]
            
            cost = calculate_cost(model, tokens["input"], tokens["output"])
            total_cost += cost
            
            print(f"{name:25s} | {format_currency(cost):25s} | {model}")
        
        print("-" * 70)
        print(f"{'月額合計':25s} | {format_currency(total_cost):25s}")
        print()
    
    # 現在の契約との比較
    print("\n" + "=" * 70)
    print("💰 コスト比較：現在 vs マルチエージェント")
    print("=" * 70)
    
    current_costs = {
        "Claude Code": 200,
        "Gemini": 25,
        "OpenAI Plus": 20,
    }
    
    new_costs_scenarios = {
        "軽量使用": {"Anthropic API": 15, "Google AI": 25, "OpenAI API": 25},
        "中規模使用": {"Anthropic API": 40, "Google AI": 30, "OpenAI API": 35},
        "重度使用": {"Anthropic API": 120, "Google AI": 40, "OpenAI API": 60},
    }
    
    print(f"\n現在の契約（月額）:")
    current_total = sum(current_costs.values())
    for service, cost in current_costs.items():
        print(f"  {service:20s}: {format_currency(cost)}")
    print(f"  {'合計':20s}: {format_currency(current_total)}")
    
    for scenario, costs in new_costs_scenarios.items():
        print(f"\n{scenario}（月額）:")
        new_total = sum(costs.values())
        for service, cost in costs.items():
            print(f"  {service:20s}: {format_currency(cost)}")
        print(f"  {'合計':20s}: {format_currency(new_total)}")
        
        savings = current_total - new_total
        savings_percent = (savings / current_total) * 100
        
        if savings > 0:
            print(f"  💰 削減額: {format_currency(savings)} ({savings_percent:.1f}%削減)")
        else:
            print(f"  ⚠️  増加額: {format_currency(abs(savings))} ({abs(savings_percent):.1f}%増加)")

if __name__ == "__main__":
    main()
