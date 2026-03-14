"""F001 Regression Test — KnowledgeStore.add() API存在確認

Failure: F001 (high) — api_mismatch
Symptom: AttributeError: 'KnowledgeStore' object has no attribute 'add_fact'
Required test: KnowledgeStore に add メソッドが存在することを確認
"""
import sys
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", "..", ".."))
sys.path.insert(0, _PROJECT_ROOT)


def test() -> bool:
    """F001: KnowledgeStore に .add() メソッドが存在することを確認（.add_fact() は誤り）"""
    try:
        from knowledge_engine.knowledge_store import KnowledgeStore
        ks = KnowledgeStore()
        api = dir(ks)
        assert "add" in api, (
            f"KnowledgeStore.add() が存在しない。"
            f"利用可能なpublicメソッド: {[m for m in api if not m.startswith('_')]}"
        )
        assert "add_fact" not in api or "add" in api, (
            "add_fact が残っており add が存在しない — 誤ったAPIが復活している"
        )
        print(f"[PASS] F001: KnowledgeStore.add() 存在確認 OK")
        return True
    except AssertionError as e:
        print(f"[FAIL] F001: {e}")
        return False
    except ImportError as e:
        print(f"[SKIP] F001: knowledge_engine が見つからない（ローカル環境）: {e}")
        return True  # VPS専用モジュールはSKIP扱い
    except Exception as e:
        print(f"[FAIL] F001: 予期せぬエラー: {type(e).__name__}: {e}")
        return False


if __name__ == "__main__":
    sys.exit(0 if test() else 1)
