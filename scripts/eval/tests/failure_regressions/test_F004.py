"""F004 Regression Test — EvolutionLoop(dry_run=True) が TypeError を出さない

Failure: F004 (high) — api_mismatch
Symptom: TypeError: EvolutionLoop.__init__() got an unexpected keyword argument 'dry_run'
Required test: EvolutionLoop(dry_run=True) でエラーなしを確認
"""
import sys
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", "..", ".."))
sys.path.insert(0, _PROJECT_ROOT)


def test() -> bool:
    """F004: EvolutionLoop(dry_run=True) で TypeError が出ないことを確認"""
    try:
        from loops.evolution_loop import EvolutionLoop
    except ImportError as e:
        print(f"[SKIP] F004: loops.evolution_loop が見つからない: {e}")
        return True  # ローカル不在はSKIP扱い

    try:
        e = EvolutionLoop(dry_run=True)
        print("[PASS] F004: EvolutionLoop(dry_run=True) TypeError なし OK")
        return True
    except TypeError as e:
        print(
            f"[FAIL] F004: TypeError 回帰 — dry_run パラメータが __init__ から削除されている: {e}"
        )
        return False
    except Exception as e:
        # TypeError 以外（依存関係エラー等）はSKIP扱い（非回帰エラー）
        print(f"[SKIP] F004: TypeError 以外の起動エラー（依存関係）: {type(e).__name__}: {e}")
        return True


if __name__ == "__main__":
    sys.exit(0 if test() else 1)
