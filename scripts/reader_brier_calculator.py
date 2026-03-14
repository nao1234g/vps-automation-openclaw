#!/usr/bin/env python3
"""
reader_brier_calculator.py — 読者Brier Score計算モジュール

I5: 読者Brier Score自動計算
- 計算式: brier_score = (probability/100 - outcome)^2
- 単独モジュール（VPS の prediction_auto_verifier.py からインポート可能）

使用例:
    from scripts.reader_brier_calculator import calc_brier, verify_self_test
    score = calc_brier(probability=70, outcome=1.0)   # → 0.09
    score = calc_brier(probability=30, outcome=0.0)   # → 0.09
    verify_self_test()   # → AssertionError がなければ PASS

Brier Score の解釈:
    0.00  完璧な予測（確実な予測が的中）
    0.25  ランダム予測（無情報予測の基準点）
    0.50  確実な予測が外れた（最悪スコア）

    < 0.15  優秀
    0.15〜0.25  普通
    >= 0.25  改善が必要
"""

import sys
import os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ─── コア計算 ──────────────────────────────────────────────────────────

def calc_brier(probability: float, outcome: float) -> float:
    """Brier Score を計算する。

    Args:
        probability: 読者が入力した確率（0〜100 の整数または浮動小数点数）
        outcome:     実際の結果（1.0 = 的中 / 0.0 = 外れ）

    Returns:
        Brier Score（0.0〜1.0、低いほど良い）

    Raises:
        ValueError: probability が 0〜100 の範囲外の場合
        ValueError: outcome が 0.0 または 1.0 以外の場合
    """
    if not (0 <= probability <= 100):
        raise ValueError(f"probability は 0〜100 の範囲で指定してください: {probability}")
    if outcome not in (0.0, 1.0, 0, 1):
        raise ValueError(f"outcome は 0.0 または 1.0 で指定してください: {outcome}")

    p = probability / 100.0
    o = float(outcome)
    return round((p - o) ** 2, 6)


def calc_brier_bulk(votes: list) -> list:
    """複数の投票に対して Brier Score を一括計算する。

    Args:
        votes: [{"probability": 70, "outcome": 1.0}, ...] のリスト

    Returns:
        [{"probability": 70, "outcome": 1.0, "brier_score": 0.09}, ...] のリスト
    """
    result = []
    for v in votes:
        prob = v.get("probability", 50)
        out = v.get("outcome", 0.0)
        try:
            score = calc_brier(prob, out)
            result.append({**v, "brier_score": score})
        except (ValueError, TypeError) as e:
            result.append({**v, "brier_score": None, "error": str(e)})
    return result


def mean_brier(scores: list) -> float | None:
    """Brier Score リストの平均を計算する。None/エラーは除外。

    Args:
        scores: brier_score 値のリスト（None 混在可）

    Returns:
        平均 Brier Score、または valid スコアが 0 件の場合は None
    """
    valid = [s for s in scores if s is not None]
    if not valid:
        return None
    return round(sum(valid) / len(valid), 6)


# ─── 自己テスト ─────────────────────────────────────────────────────────

def verify_self_test() -> bool:
    """既知の値で計算結果を検証する。PASS なら True を返す。

    呼び出し時に AssertionError が発生した場合は計算式にバグがある。
    """
    test_cases = [
        # (probability, outcome, expected_brier_score)
        (100, 1.0, 0.0),     # 完璧な予測（的中）
        (0,   0.0, 0.0),     # 完璧な予測（外れを正しく予測）
        (100, 0.0, 1.0),     # 完全な誤り（確信して外れた）
        (0,   1.0, 1.0),     # 完全な誤り（0%予測が的中）
        (50,  1.0, 0.25),    # 50%ランダム（的中）= (0.5-1)^2 = 0.25
        (50,  0.0, 0.25),    # 50%ランダム（外れ）= (0.5-0)^2 = 0.25
        (70,  1.0, 0.09),    # 70%予測が的中   = (0.7-1)^2 = 0.09
        (70,  0.0, 0.49),    # 70%予測が外れ   = (0.7-0)^2 = 0.49
        (30,  0.0, 0.09),    # 30%予測が外れ正解 = (0.3-0)^2 = 0.09
        (30,  1.0, 0.49),    # 30%予測が的中   = (0.3-1)^2 = 0.49
    ]
    errors = []
    for prob, out, expected in test_cases:
        got = calc_brier(prob, out)
        if abs(got - expected) > 1e-9:
            errors.append(f"  calc_brier({prob}, {out}) = {got}, expected {expected}")

    if errors:
        print("[FAIL] Brier Score 計算に誤りがあります:")
        for e in errors:
            print(e)
        return False

    # mean_brier テスト
    scores = [0.0, 0.25, 0.09]
    expected_mean = round((0.0 + 0.25 + 0.09) / 3, 6)
    got_mean = mean_brier(scores)
    if abs(got_mean - expected_mean) > 1e-9:
        print(f"[FAIL] mean_brier テスト失敗: got={got_mean}, expected={expected_mean}")
        return False

    # None 混在テスト
    if mean_brier([None, None]) is not None:
        print("[FAIL] mean_brier([None, None]) は None を返すべきです")
        return False

    print(f"[PASS] Brier Score 計算テスト {len(test_cases)} 件: 全て正常")
    return True


# ─── CLI ───────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="読者Brier Score計算ツール"
    )
    parser.add_argument("--test", action="store_true", help="自己テストを実行する")
    parser.add_argument("--prob", type=float, help="確率（0〜100）")
    parser.add_argument("--outcome", type=float, choices=[0.0, 1.0], help="結果（0=外れ, 1=的中）")
    args = parser.parse_args()

    if args.test:
        ok = verify_self_test()
        sys.exit(0 if ok else 1)

    if args.prob is not None and args.outcome is not None:
        score = calc_brier(args.prob, args.outcome)
        print(f"Brier Score: {score}")
        interpretation = (
            "優秀 (<0.15)" if score < 0.15
            else "普通 (0.15〜0.25)" if score < 0.25
            else "改善が必要 (>=0.25)"
        )
        print(f"評価: {interpretation}")
        sys.exit(0)

    parser.print_help()


if __name__ == "__main__":
    main()
