#!/usr/bin/env python
"""
doctor.py — AI OS 全体健全性チェック
使い方: python scripts/doctor.py [--vps] [--verbose]
  --vps     VPS への SSH チェックも含める（デフォルト: ローカルのみ）
  --verbose 詳細ログを出す
  --json    JSON 形式で出力

終了コード:
  0 = PASS（全チェック通過）
  1 = WARN（警告あり）
  2 = FAIL（エラーあり）
"""

import os
import sys
import json
import subprocess
import argparse
from pathlib import Path

# Windows CP932 環境で絵文字・日本語を含む出力が壊れないようにする
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
from datetime import datetime, timezone

# ─── 設定 ────────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent.parent
POLICY_DIR = REPO_ROOT / "policy" / "canonical"
HOOKS_DIR = REPO_ROOT / ".claude" / "hooks"
DOCS_DIR = REPO_ROOT / "docs"
VPS_HOST = "root@163.44.124.123"


def c(color, text):
    colors = {"green": "\033[92m", "red": "\033[91m", "yellow": "\033[93m",
              "blue": "\033[94m", "reset": "\033[0m", "bold": "\033[1m"}
    return f"{colors.get(color, '')}{text}{colors['reset']}"


class Doctor:
    def __init__(self, verbose=False, include_vps=False, json_output=False):
        self.verbose = verbose
        self.include_vps = include_vps
        self.json_output = json_output
        self.results = []
        self.errors = 0
        self.warnings = 0

    def check(self, name, status, detail="", severity="INFO"):
        """チェック結果を記録"""
        entry = {"name": name, "status": status, "detail": detail, "severity": severity}
        self.results.append(entry)
        if status == "FAIL":
            self.errors += 1
        elif status == "WARN":
            self.warnings += 1

        if not self.json_output:
            icon = {"PASS": "[OK]  ", "FAIL": "[FAIL]", "WARN": "[WARN]", "INFO": "[INFO]"}.get(status, "      ")
            sev_color = {"PASS": "green", "FAIL": "red", "WARN": "yellow", "INFO": "blue"}.get(status, "reset")
            print(f"  {icon} {c(sev_color, status):6s}  {name}")
            if detail and (self.verbose or status in ("FAIL", "WARN")):
                print(f"         {c('reset', detail)}")

    # ─── ローカルチェック ─────────────────────────────────

    def check_policy_files(self):
        """policy/canonical/ の5YAMLファイル"""
        expected = [
            "runtime_truth_registry.yaml",
            "retirement_registry.yaml",
            "doctrine_index.yaml",
            "cli_permissions_policy.yaml",
            "generated_artifacts.yaml",
        ]
        for f in expected:
            p = POLICY_DIR / f
            if p.exists():
                self.check(f"policy/canonical/{f}", "PASS")
            else:
                self.check(f"policy/canonical/{f}", "FAIL",
                           f"ファイルが存在しない: {p}", "ERROR")

    def check_settings_files(self):
        """Claude Code 設定ファイル"""
        settings = REPO_ROOT / ".claude" / "settings.json"
        if settings.exists():
            try:
                data = json.loads(settings.read_text(encoding="utf-8"))
                mode = data.get("defaultMode", data.get("permissions", {}).get("defaultMode", "MISSING"))
                if mode in ("acceptEdits", "bypassPermissions"):
                    self.check(".claude/settings.json", "PASS", f"defaultMode={mode}")
                else:
                    self.check(".claude/settings.json", "WARN",
                               f"defaultMode={mode} — acceptEdits を推奨", "WARNING")
            except Exception as e:
                self.check(".claude/settings.json", "FAIL", f"JSON パースエラー: {e}", "ERROR")
        else:
            self.check(".claude/settings.json", "FAIL", "shared settings.json が存在しない", "ERROR")

        local_settings = REPO_ROOT / ".claude" / "settings.local.json"
        if local_settings.exists():
            try:
                data = json.loads(local_settings.read_text(encoding="utf-8"))
                perms = data.get("permissions", {})
                deny = perms.get("deny", [])
                has_env_deny = any(".env" in d for d in deny)
                if has_env_deny:
                    self.check(".claude/settings.local.json", "PASS", f"deny list あり ({len(deny)} entries)")
                else:
                    self.check(".claude/settings.local.json", "WARN",
                               "deny list に .env が含まれていない", "WARNING")
            except Exception as e:
                self.check(".claude/settings.local.json", "WARN", f"JSON パースエラー: {e}", "WARNING")
        else:
            self.check(".claude/settings.local.json", "WARN",
                       "settings.local.json が存在しない（settings.local.example.json を参考に作成を推奨）", "WARNING")

    def check_doctrine_files(self):
        """consolidated doctrine files (archived originals → 4 canonical files)"""
        canonical = [
            (".claude/rules/NORTH_STAR.md", REPO_ROOT / ".claude" / "rules" / "NORTH_STAR.md"),
            (".claude/rules/OPERATING_PRINCIPLES.md", REPO_ROOT / ".claude" / "rules" / "OPERATING_PRINCIPLES.md"),
            (".claude/rules/IMPLEMENTATION_REF.md", REPO_ROOT / ".claude" / "rules" / "IMPLEMENTATION_REF.md"),
            (".claude/CLAUDE.md", REPO_ROOT / ".claude" / "CLAUDE.md"),
        ]
        for label, p in canonical:
            if p.exists():
                self.check(f"{label}", "PASS")
            else:
                self.check(f"{label}", "WARN", f"canonical file が存在しない: {p}", "WARNING")

    def check_north_star(self):
        """NORTH_STAR.md の存在と Eternal Directives の存在確認"""
        p = REPO_ROOT / ".claude" / "rules" / "NORTH_STAR.md"
        if not p.exists():
            self.check("NORTH_STAR.md", "FAIL", "ファイルが存在しない", "ERROR")
            return
        content = p.read_text(encoding="utf-8")
        if "The Eternal Directives" in content:
            self.check("NORTH_STAR.md (Eternal Directives)", "PASS")
        else:
            self.check("NORTH_STAR.md (Eternal Directives)", "FAIL",
                       "Eternal Directives セクションが見当たらない", "ERROR")
        if "Yanai-Geneen" in content or "経営者OS" in content:
            self.check("NORTH_STAR.md (Yanai-Geneen OS)", "PASS")
        else:
            self.check("NORTH_STAR.md (Yanai-Geneen OS)", "WARN",
                       "Yanai-Geneen Executive OS セクションが見当たらない", "WARNING")

    def check_three_layer_constitution(self):
        """三層憲法ヒエラルキー整合性チェック
        NORTH_STAR（価値）→ OPERATING_PRINCIPLES（原則）→ IMPLEMENTATION_REF（技術参照）
        """
        rules_dir = REPO_ROOT / ".claude" / "rules"
        claude_md = REPO_ROOT / ".claude" / "CLAUDE.md"
        guard = REPO_ROOT / ".claude" / "hooks" / "north-star-guard.py"
        routing = REPO_ROOT / ".claude" / "state" / "memory_routing_rules.json"

        # 1. L1: NORTH_STAR.md 存在
        p_ns = rules_dir / "NORTH_STAR.md"
        self.check("3layer-L1: NORTH_STAR.md 存在",
                   "PASS" if p_ns.exists() else "FAIL",
                   "" if p_ns.exists() else f"NORTH_STAR.md が存在しない: {p_ns}",
                   "ERROR" if not p_ns.exists() else "INFO")

        # 2. L1: OPERATING_PRINCIPLES.md 存在（正式復活確認）
        p_op = rules_dir / "OPERATING_PRINCIPLES.md"
        self.check("3layer-L1: OPERATING_PRINCIPLES.md 存在 (.claude/rules/)",
                   "PASS" if p_op.exists() else "FAIL",
                   "" if p_op.exists() else f"OPERATING_PRINCIPLES.md が .claude/rules/ に存在しない — T012 要件未充足",
                   "ERROR" if not p_op.exists() else "INFO")

        # 3. CLAUDE.md が OPERATING_PRINCIPLES.md を @import しているか
        if claude_md.exists():
            claude_content = claude_md.read_text(encoding="utf-8")
            has_op_import = "@.claude/rules/OPERATING_PRINCIPLES.md" in claude_content
            self.check("3layer: CLAUDE.md @import OPERATING_PRINCIPLES.md",
                       "PASS" if has_op_import else "FAIL",
                       "" if has_op_import else "CLAUDE.md が @.claude/rules/OPERATING_PRINCIPLES.md を import していない",
                       "ERROR" if not has_op_import else "INFO")
        else:
            self.check("3layer: CLAUDE.md @import", "FAIL", "CLAUDE.md が存在しない", "ERROR")

        # 4. north-star-guard.py が新パスを保護しているか
        if guard.exists():
            guard_content = guard.read_text(encoding="utf-8")
            has_new_path = "/.claude/rules/operating_principles.md" in guard_content
            has_old_path = "/docs/archive/operating_principles.md" in guard_content
            if has_new_path and not has_old_path:
                self.check("3layer: north-star-guard.py パス更新", "PASS",
                           "/.claude/rules/operating_principles.md を保護")
            elif has_old_path:
                self.check("3layer: north-star-guard.py パス更新", "FAIL",
                           "古いパス /docs/archive/operating_principles.md が残存 — 更新が必要",
                           "ERROR")
            else:
                self.check("3layer: north-star-guard.py パス更新", "WARN",
                           "OPERATING_PRINCIPLES.md の保護パスが見当たらない", "WARNING")
        else:
            self.check("3layer: north-star-guard.py 存在", "FAIL",
                       f"north-star-guard.py が存在しない: {guard}", "ERROR")

        # 5. memory_routing_rules.json の L1 に OPERATING_PRINCIPLES.md が含まれるか
        if routing.exists():
            try:
                rdata = json.loads(routing.read_text(encoding="utf-8"))
                l1 = next((l for l in rdata.get("layers", []) if l.get("id") == "L1"), None)
                l2 = next((l for l in rdata.get("layers", []) if l.get("id") == "L2"), None)
                if l1:
                    l1_files = l1.get("files", [])
                    has_op_l1 = any("OPERATING_PRINCIPLES" in f for f in l1_files)
                    ir_in_l1 = any("IMPLEMENTATION_REF" in f for f in l1_files)
                    self.check("3layer: memory_routing_rules L1 OPERATING_PRINCIPLES",
                               "PASS" if has_op_l1 else "FAIL",
                               "" if has_op_l1 else "L1 に OPERATING_PRINCIPLES.md が含まれていない",
                               "ERROR" if not has_op_l1 else "INFO")
                    if ir_in_l1:
                        self.check("3layer: memory_routing_rules IMPLEMENTATION_REF L1誤配置",
                                   "FAIL", "IMPLEMENTATION_REF.md が L1 に残存 — L2 に移動が必要", "ERROR")
                    else:
                        self.check("3layer: memory_routing_rules IMPLEMENTATION_REF L1から除去", "PASS")
                if l2:
                    l2_files = l2.get("files", [])
                    ir_in_l2 = any("IMPLEMENTATION_REF" in f for f in l2_files)
                    self.check("3layer: memory_routing_rules L2 IMPLEMENTATION_REF",
                               "PASS" if ir_in_l2 else "WARN",
                               "" if ir_in_l2 else "L2 に IMPLEMENTATION_REF.md が含まれていない（推奨）",
                               "WARNING" if not ir_in_l2 else "INFO")
            except Exception as e:
                self.check("3layer: memory_routing_rules.json パース", "WARN",
                           f"パースエラー: {e}", "WARNING")
        else:
            self.check("3layer: memory_routing_rules.json 存在", "FAIL",
                       f"memory_routing_rules.json が存在しない: {routing}", "ERROR")

    def check_hooks(self):
        """重要 hooks の存在確認"""
        critical_hooks = [
            "pvqe-p-gate.py",
            "north-star-guard.py",
            "fact-checker.py",
            "llm-judge.py",
            "intent-confirm.py",
            "research-gate.sh",
            "feedback-trap.py",
            "session-start.sh",
        ]
        for hook in critical_hooks:
            p = HOOKS_DIR / hook
            if p.exists():
                self.check(f"hooks/{hook}", "PASS")
            else:
                self.check(f"hooks/{hook}", "FAIL", f"hook が存在しない: {p}", "ERROR")

    def check_scripts(self):
        """doctor / audit_retired_refs / build_canonical_outputs の存在確認"""
        scripts = [
            "doctor.py",
            "audit_retired_refs.py",
            "build_canonical_outputs.py",
        ]
        for s in scripts:
            p = REPO_ROOT / "scripts" / s
            if p.exists():
                self.check(f"scripts/{s}", "PASS")
            else:
                self.check(f"scripts/{s}", "WARN", f"script が存在しない: {p}", "WARNING")

    def check_civilization_os(self):
        """AI Civilization OS — モジュール存在 + importチェック"""
        # ─ ディレクトリ存在確認 ─
        required_dirs = [
            "truth_engine", "prediction_engine", "knowledge_engine",
            "agent_civilization", "agents", "loops", "apps",
            "configs", "decision_engine", "board", "data",
        ]
        for d in required_dirs:
            p = REPO_ROOT / d
            if p.is_dir():
                self.check(f"dir/{d}/", "PASS")
            else:
                self.check(f"dir/{d}/", "FAIL",
                           f"ディレクトリが存在しない: {p}", "ERROR")

        # ─ コアモジュール import チェック ─
        import sys as _sys
        orig_path = _sys.path[:]
        _sys.path.insert(0, str(REPO_ROOT))

        module_checks = [
            ("Truth Engine",      "truth_engine.truth_engine"),
            ("Prediction Engine", "prediction_engine.prediction_registry"),
            ("Knowledge Engine",  "knowledge_engine.knowledge_store"),
            ("Decision Engine",   "decision_engine"),
            ("CapitalEngine",     "decision_engine.capital_engine"),
            ("ExecutionPlanner",  "decision_engine.execution_planner"),
            ("StrategyEngine",    "decision_engine.strategy_engine"),
            ("BoardMeeting",      "board.board_meeting"),
        ]

        import importlib as _imp
        for label, mod_path in module_checks:
            try:
                _imp.import_module(mod_path)
                self.check(f"import: {label}", "PASS", mod_path)
            except ImportError as e:
                self.check(f"import: {label}", "FAIL",
                           f"{mod_path} — ImportError: {e}", "ERROR")
            except Exception as e:
                self.check(f"import: {label}", "WARN",
                           f"{mod_path} — {type(e).__name__}: {e}", "WARNING")

        _sys.path[:] = orig_path

        # ─ configs YAML パースチェック ─
        config_files = ["models.yaml", "agents.yaml", "system.yaml"]
        for cf in config_files:
            p = REPO_ROOT / "configs" / cf
            if not p.exists():
                self.check(f"configs/{cf}", "WARN",
                           f"設定ファイルが存在しない: {p}", "WARNING")
                continue
            try:
                import yaml as _yaml
                with open(p, encoding="utf-8") as fh:
                    _yaml.safe_load(fh)
                self.check(f"configs/{cf}", "PASS")
            except ImportError:
                self.check(f"configs/{cf}", "WARN",
                           "PyYAML未インストール（pip install pyyaml）", "WARNING")
            except Exception as e:
                self.check(f"configs/{cf}", "FAIL",
                           f"YAMLパースエラー: {e}", "ERROR")

        # ─ OS ドキュメント存在確認 ─
        for doc in [
            ".claude/SYSTEM_MAP.md",
            ".claude/rules/NORTH_STAR.md",
            ".claude/rules/IMPLEMENTATION_REF.md",
        ]:
            p = REPO_ROOT / doc
            self.check(f"doc: {doc}", "PASS" if p.exists() else "WARN",
                       "" if p.exists() else f"存在しない: {p}")

        # ─ OS エントリーポイント存在確認 ─
        os_scripts = [
            "run_civilization_os.py",
            "system_scheduler.py",
            "agent_orchestrator.py",
            "knowledge_ingestion.py",
            "article_pipeline.py",
        ]
        for s in os_scripts:
            p = REPO_ROOT / s
            self.check(f"os_script: {s}", "PASS" if p.exists() else "WARN",
                       "" if p.exists() else f"OSスクリプトが存在しない: {p}")

    def check_retired_refs(self):
        """退役済み artifact への参照チェック（ローカルのみ）"""
        retired_patterns = [
            ("/opt/CLAUDE.md", [
                # 退役注記のある行は除外
                ".retired",
                "退役済み",
                "retired",
                "tombstone",
                "RETIRED",
                "2026-03-14",
            ]),
        ]
        # 自己参照・バックアップ・歴史的記録は除外
        _AUDIT_EXCLUDE = [
            "doctor.py", "audit_retired_refs.py",
            "retirement_registry.yaml", "runtime_truth_registry.yaml",
            "generated_artifacts.yaml", "KNOWN_MISTAKES.md", "BACKLOG.md",
            ".bak-",  # .bak-YYYYMMDD バックアップファイル
        ]
        found_bad = []
        for pattern, allow_contexts in retired_patterns:
            try:
                result = subprocess.run(
                    ["grep", "-rn", pattern,
                     str(REPO_ROOT / ".claude"), str(REPO_ROOT / "docs"),
                     str(REPO_ROOT / "scripts"), str(REPO_ROOT / "policy")],
                    capture_output=True, text=True, errors="replace"
                )
                for line in result.stdout.splitlines():
                    if any(excl in line for excl in _AUDIT_EXCLUDE):
                        continue
                    is_allowed = any(ctx in line for ctx in allow_contexts)
                    if not is_allowed:
                        found_bad.append(line.strip())
            except FileNotFoundError:
                # grep not found (Windows) — skip
                pass

        if found_bad:
            self.check("retired refs (local)", "FAIL",
                       f"{len(found_bad)} 件の不正参照:\n" + "\n".join(found_bad[:5]), "ERROR")
        else:
            self.check("retired refs (local)", "PASS", "/opt/CLAUDE.md への不正参照: 0件")

    def check_guard_scripts(self):
        """scripts/guard/ の4ガードスクリプト存在確認"""
        guard_scripts = [
            "scripts/guard/pre_edit_task_guard.py",
            "scripts/guard/failure_capture.py",
            "scripts/guard/post_edit_task_reconcile.py",
            "scripts/guard/release_gate.py",
        ]
        for s in guard_scripts:
            p = REPO_ROOT / s
            self.check(
                f"guard: {Path(s).name}",
                "PASS" if p.exists() else "FAIL",
                "" if p.exists() else f"ガードスクリプトが存在しない: {p}",
                "ERROR" if not p.exists() else "INFO",
            )

    def check_research_scripts(self):
        """scripts/research/ の4リサーチスクリプト存在確認"""
        research_scripts = [
            "scripts/research/knowledge_timeline_recorder.py",
            "scripts/research/daily_paper_ingest.py",
            "scripts/research/daily_research_digest.py",
            "scripts/research/promote_research_to_tasks.py",
        ]
        for s in research_scripts:
            p = REPO_ROOT / s
            self.check(
                f"research: {Path(s).name}",
                "PASS" if p.exists() else "FAIL",
                "" if p.exists() else f"リサーチスクリプトが存在しない: {p}",
                "ERROR" if not p.exists() else "INFO",
            )

    def check_state_files(self):
        """state JSON ファイルの存在と基本スキーマ検証"""
        state_dir = REPO_ROOT / ".claude" / "state"
        checks = [
            ("task_ledger.json",           ["tasks"]),
            ("failure_memory.json",        ["failures"]),
            ("failure_regression_index.json", []),
            ("knowledge_timeline.json",    ["runs", "stats"]),
        ]
        for filename, required_keys in checks:
            p = state_dir / filename
            if not p.exists():
                self.check(f"state: {filename}", "FAIL",
                           f"状態ファイルが存在しない: {p}", "ERROR")
                continue
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                missing = [k for k in required_keys if k not in data]
                if missing:
                    self.check(f"state: {filename}", "WARN",
                               f"必須キーが不足: {missing}", "WARNING")
                else:
                    self.check(f"state: {filename}", "PASS")
            except Exception as e:
                self.check(f"state: {filename}", "FAIL",
                           f"JSONパースエラー: {e}", "ERROR")

    def check_memory_layer_integrity(self):
        """6層記憶アーキテクチャ L1-L6 の整合性チェック"""
        state_dir = REPO_ROOT / ".claude" / "state"
        rules_dir = REPO_ROOT / ".claude" / "rules"

        # L1: Constitution（NORTH_STAR + OPERATING_PRINCIPLES）
        for fname in ["NORTH_STAR.md", "OPERATING_PRINCIPLES.md"]:
            p = rules_dir / fname
            self.check(
                f"memory-L1: {fname}",
                "PASS" if p.exists() else "FAIL",
                "" if p.exists() else f"L1 Constitution ファイルが存在しない: {p}",
                "ERROR" if not p.exists() else "INFO",
            )

        # L1→L2 整合性: IMPLEMENTATION_REF.md は L1 ではなく L2（Operating Rules）
        p_ir = rules_dir / "IMPLEMENTATION_REF.md"
        if p_ir.exists():
            self.check("memory-L1→L2: IMPLEMENTATION_REF存在", "PASS",
                       "IMPLEMENTATION_REF.md が存在する（consolidated technical reference）")
        else:
            self.check("memory-L1→L2: IMPLEMENTATION_REF.md 存在", "FAIL",
                       f"IMPLEMENTATION_REF.md が存在しない: {p_ir}", "ERROR")

        # L2: Operating Rules — CLAUDE.md
        p_claude = REPO_ROOT / ".claude" / "CLAUDE.md"
        self.check(
            "memory-L2: CLAUDE.md",
            "PASS" if p_claude.exists() else "FAIL",
            "" if p_claude.exists() else "L2 Operating Rules CLAUDE.md が存在しない",
            "ERROR" if not p_claude.exists() else "INFO",
        )

        # L3: Failure Memory
        for fname in ["failure_memory.json", "failure_regression_index.json"]:
            p = state_dir / fname
            self.check(
                f"memory-L3: {fname}",
                "PASS" if p.exists() else "FAIL",
                "" if p.exists() else f"L3 Failure Memory ファイルが存在しない: {p}",
                "ERROR" if not p.exists() else "INFO",
            )
        p_mp = REPO_ROOT / ".claude" / "hooks" / "state" / "mistake_patterns.json"
        self.check(
            "memory-L3: mistake_patterns.json",
            "PASS" if p_mp.exists() else "FAIL",
            "" if p_mp.exists() else f"L3 mistake_patterns.json が存在しない: {p_mp}",
            "ERROR" if not p_mp.exists() else "INFO",
        )

        # L4: Learning Memory (knowledge_timeline.json)
        p_kt = state_dir / "knowledge_timeline.json"
        self.check(
            "memory-L4: knowledge_timeline.json",
            "PASS" if p_kt.exists() else "FAIL",
            "" if p_kt.exists() else f"L4 Learning Memory が存在しない: {p_kt}",
            "ERROR" if not p_kt.exists() else "INFO",
        )

        # L5: Execution State
        p_ledger = state_dir / "task_ledger.json"
        p_active = REPO_ROOT / ".claude" / "hooks" / "state" / "active_task_id.txt"
        self.check(
            "memory-L5: task_ledger.json",
            "PASS" if p_ledger.exists() else "FAIL",
            "" if p_ledger.exists() else f"L5 Task Ledger が存在しない: {p_ledger}",
            "ERROR" if not p_ledger.exists() else "INFO",
        )
        self.check(
            "memory-L5: active_task_id.txt",
            "PASS" if p_active.exists() else "WARN",
            "" if p_active.exists() else "L5 active_task_id.txt が存在しない（タスク未設定）",
            "WARNING" if not p_active.exists() else "INFO",
        )

        # L6: Approval Queue
        for fname in ["approval_queue.json", "constitution_candidates.json",
                      "memory_routing_rules.json"]:
            p = state_dir / fname
            self.check(
                f"memory-L6: {fname}",
                "PASS" if p.exists() else "FAIL",
                "" if p.exists() else f"L6 Approval/Routing ファイルが存在しない: {p}",
                "ERROR" if not p.exists() else "INFO",
            )

        # failure_regression_index の resolved_status 整合性チェック
        p_fri = state_dir / "failure_regression_index.json"
        p_fm = state_dir / "failure_memory.json"
        if p_fri.exists() and p_fm.exists():
            try:
                fri = json.loads(p_fri.read_text(encoding="utf-8"))
                fm = json.loads(p_fm.read_text(encoding="utf-8"))
                fm_statuses = {f["failure_id"]: f.get("resolved_status", "")
                               for f in fm.get("failures", [])}
                mismatches = []
                for entry in fri.get("failures", []):
                    fid = entry.get("failure_id", "")
                    idx_status = entry.get("resolved_status", "")
                    mem_status = fm_statuses.get(fid, "N/A")
                    if mem_status != "N/A" and idx_status != mem_status:
                        mismatches.append(
                            f"{fid}: index={idx_status} vs memory={mem_status}"
                        )
                if mismatches:
                    self.check(
                        "memory-L3: regression_index vs failure_memory 整合性",
                        "WARN",
                        f"resolved_status 不一致: {mismatches}",
                        "WARNING",
                    )
                else:
                    self.check(
                        "memory-L3: regression_index vs failure_memory 整合性",
                        "PASS",
                    )
            except Exception as e:
                self.check(
                    "memory-L3: regression_index vs failure_memory 整合性",
                    "WARN", f"チェックエラー: {e}", "WARNING"
                )

    def check_state_integrity(self):
        """承認キュー・Constitution候補・active_task_id の陳腐化チェック"""
        state_dir = REPO_ROOT / ".claude" / "state"
        now = datetime.now(timezone.utc)

        # approval_queue.json の陳腐化チェック
        p_aq = state_dir / "approval_queue.json"
        if p_aq.exists():
            try:
                aq = json.loads(p_aq.read_text(encoding="utf-8"))
                stale_7 = []
                stale_30 = []
                for item in aq.get("queue", []):
                    if item.get("status") != "pending":
                        continue
                    ts_str = item.get("created_at") or item.get("proposed_at", "")
                    if not ts_str:
                        continue
                    try:
                        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                        age_days = (now - ts).days
                        label = f"[{item.get('id','?')}] {item.get('title','')[:50]}"
                        if age_days > 30:
                            stale_30.append(f"{label} ({age_days}d)")
                        elif age_days > 7:
                            stale_7.append(f"{label} ({age_days}d)")
                    except Exception:
                        pass
                if stale_30:
                    self.check("state: approval_queue staleness >30d", "FAIL",
                               f"30日以上放置の承認待ち: {stale_30[:3]}", "ERROR")
                elif stale_7:
                    self.check("state: approval_queue staleness >7d", "WARN",
                               f"7日以上放置の承認待ち: {stale_7[:3]}", "WARNING")
                else:
                    self.check("state: approval_queue staleness", "PASS")
            except Exception as e:
                self.check("state: approval_queue staleness", "WARN",
                           f"チェックエラー: {e}", "WARNING")
        else:
            self.check("state: approval_queue staleness", "WARN",
                       "approval_queue.json が存在しない", "WARNING")

        # constitution_candidates.json の open 候補陳腐化チェック（30日超 WARN）
        p_cc = state_dir / "constitution_candidates.json"
        if p_cc.exists():
            try:
                cc = json.loads(p_cc.read_text(encoding="utf-8"))
                stale_cc = []
                for c in cc.get("candidates", []):
                    if c.get("status") != "open":
                        continue
                    ts_str = c.get("escalated_at", "")
                    if not ts_str:
                        continue
                    try:
                        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                        age_days = (now - ts).days
                        if age_days > 30:
                            label = f"[{c.get('candidate_id','?')}] {c.get('title','')[:50]}"
                            stale_cc.append(f"{label} ({age_days}d)")
                    except Exception:
                        pass
                if stale_cc:
                    self.check("state: constitution_candidates staleness", "WARN",
                               f"30日以上 open の候補: {stale_cc[:3]}", "WARNING")
                else:
                    self.check("state: constitution_candidates staleness", "PASS")
            except Exception as e:
                self.check("state: constitution_candidates staleness", "WARN",
                           f"チェックエラー: {e}", "WARNING")
        else:
            self.check("state: constitution_candidates staleness", "WARN",
                       "constitution_candidates.json が存在しない", "WARNING")

        # active_task_id.txt が done/archived を指していないかチェック
        p_active = REPO_ROOT / ".claude" / "hooks" / "state" / "active_task_id.txt"
        p_ledger = state_dir / "task_ledger.json"
        if p_active.exists() and p_ledger.exists():
            try:
                active_id = p_active.read_text(encoding="utf-8").strip()
                if active_id:
                    ledger = json.loads(p_ledger.read_text(encoding="utf-8"))
                    task_map = {t["id"]: t for t in ledger.get("tasks", [])}
                    task = task_map.get(active_id)
                    if task is None:
                        self.check("state: active_task_id validity", "WARN",
                                   f"active_task_id='{active_id}' が台帳に存在しない", "WARNING")
                    elif task.get("status") in ("done", "archived"):
                        self.check("state: active_task_id validity", "FAIL",
                                   f"active_task_id='{active_id}' は完了済み "
                                   f"(status={task.get('status')}) — 更新必要", "ERROR")
                    else:
                        self.check("state: active_task_id validity", "PASS",
                                   f"{active_id} status={task.get('status')}")
                else:
                    self.check("state: active_task_id validity", "PASS",
                               "active_task_id 空（タスク未設定）")
            except Exception as e:
                self.check("state: active_task_id validity", "WARN",
                           f"チェックエラー: {e}", "WARNING")

    def check_model_fixation_in_principles(self):
        """rules/ ガバナンスファイルにモデルバージョン文字列が埋め込まれていないか検証

        モデル名（claude-opus-4-6 等）は compute layer のみ許可:
          - MODEL_ROUTING_POLICY.md
          - settings*.json / settings*.local.json
        L1/L2 principles（NORTH_STAR.md 等）に書かれているとモデル固定化バイアスになる。
        """
        rules_dir = REPO_ROOT / ".claude" / "rules"
        # 許可ファイル: compute layer
        allowed_files = {"MODEL_ROUTING_POLICY.md"}
        # 検出するモデルバージョンパターン
        model_patterns = [
            "claude-opus-", "claude-sonnet-", "claude-haiku-",
            "claude-3-", "claude-4-",
            "gpt-4", "gpt-3.5", "gemini-pro", "gemini-flash",
        ]

        violations = []
        if rules_dir.exists():
            for md_file in rules_dir.glob("*.md"):
                if md_file.name in allowed_files:
                    continue
                try:
                    content = md_file.read_text(encoding="utf-8", errors="replace")
                    found = [p for p in model_patterns if p in content]
                    if found:
                        violations.append(f"{md_file.name}: {found}")
                except Exception:
                    pass

        if violations:
            self.check("principles: model-fixation check", "WARN",
                       f"ガバナンスファイルにモデル名が埋め込まれています "
                       f"(MODEL_ROUTING_POLICY.md のみ許可):\n"
                       + "\n".join(f"  - {v}" for v in violations[:5]),
                       "WARNING")
        else:
            self.check("principles: model-fixation check", "PASS",
                       "ガバナンスファイルにモデルバージョン文字列なし")

    # ─── Runtime Packet チェック ──────────────────────────────

    def check_runtime_packet(self):
        """RUNTIME_EXECUTION_PACKET.md の存在・鮮度・整合性チェック（4チェック）"""
        packet_path = REPO_ROOT / ".claude" / "RUNTIME_EXECUTION_PACKET.md"
        ssot_paths = [
            REPO_ROOT / ".claude" / "rules" / "NORTH_STAR.md",
            REPO_ROOT / ".claude" / "rules" / "OPERATING_PRINCIPLES.md",
            REPO_ROOT / ".claude" / "rules" / "IMPLEMENTATION_REF.md",
        ]
        active_id_path = REPO_ROOT / ".claude" / "hooks" / "state" / "active_task_id.txt"

        # Check 1: packet exists
        if not packet_path.exists():
            self.check("runtime-packet: exists", "FAIL",
                       f"RUNTIME_EXECUTION_PACKET.md が見つかりません\n"
                       f"  実行: python scripts/build_runtime_execution_packet.py",
                       "ERROR")
            # remaining checks meaningless without file
            self.check("runtime-packet: freshness", "FAIL",
                       "パケット未生成のためスキップ", "ERROR")
            self.check("runtime-packet: task-id match", "FAIL",
                       "パケット未生成のためスキップ", "ERROR")
            self.check("runtime-packet: SSOTs exist", "FAIL",
                       "パケット未生成のためスキップ", "ERROR")
            return

        self.check("runtime-packet: exists", "PASS",
                   str(packet_path.relative_to(REPO_ROOT)))

        # Check 2: freshness (<24h)
        content = ""
        try:
            content = packet_path.read_text(encoding="utf-8", errors="replace")
            generated_at = None
            for line in content.splitlines():
                if "**generated_at**:" in line:
                    val = line.split(":", 1)[1].strip()
                    try:
                        generated_at = datetime.fromisoformat(val)
                    except ValueError:
                        pass
                    break

            if generated_at is None:
                self.check("runtime-packet: freshness", "WARN",
                           "generated_at が読み取れません。パケットを再生成してください。",
                           "WARNING")
            else:
                now = datetime.now(timezone.utc)
                if generated_at.tzinfo is None:
                    generated_at = generated_at.replace(tzinfo=timezone.utc)
                age_sec = (now - generated_at).total_seconds()
                if age_sec > 24 * 3600:
                    self.check("runtime-packet: freshness", "WARN",
                               f"パケットが {int(age_sec/3600)}h 前のものです（閾値: 24h）。"
                               f"python scripts/build_runtime_execution_packet.py で再生成推奨。",
                               "WARNING")
                else:
                    self.check("runtime-packet: freshness", "PASS",
                               f"{int(age_sec/60)} 分前に生成済み")
        except Exception as e:
            self.check("runtime-packet: freshness", "WARN",
                       f"鮮度チェック中にエラー: {e}", "WARNING")

        # Check 3: active_task_id match
        try:
            packet_task_id = None
            for line in content.splitlines():
                if "**active_task_id**:" in line:
                    packet_task_id = line.split(":", 1)[1].strip()
                    break

            current_task_id = ""
            if active_id_path.exists():
                current_task_id = active_id_path.read_text(
                    encoding="utf-8", errors="replace").strip()

            # "(none)" と "" は両方「アクティブタスクなし」として一致扱い
            _normalize = lambda v: "" if v in (None, "(none)") else v
            if _normalize(packet_task_id) != _normalize(current_task_id):
                self.check("runtime-packet: task-id match", "FAIL",
                           f"packet の task_id ({packet_task_id!r}) と "
                           f"active_task_id.txt ({current_task_id!r}) が不一致\n"
                           f"  実行: python scripts/build_runtime_execution_packet.py",
                           "ERROR")
            else:
                self.check("runtime-packet: task-id match", "PASS",
                           f"active_task_id = {current_task_id!r}")
        except Exception as e:
            self.check("runtime-packet: task-id match", "WARN",
                       f"task-id 整合チェック中にエラー: {e}", "WARNING")

        # Check 4: SSOTs exist
        missing = [str(p.relative_to(REPO_ROOT)) for p in ssot_paths if not p.exists()]
        if missing:
            self.check("runtime-packet: SSOTs exist", "FAIL",
                       f"ソース SSOT が見つかりません: {missing}", "ERROR")
        else:
            self.check("runtime-packet: SSOTs exist", "PASS",
                       f"{len(ssot_paths)} 件の SSOT ファイルすべて存在")

    # ─── VPS チェック ─────────────────────────────────────

    def check_vps_services(self):
        """VPS サービス状態"""
        services = ["neo-telegram", "neo2-telegram", "neo3-telegram", "ghost-nowpattern"]
        for svc in services:
            try:
                result = subprocess.run(
                    ["ssh", "-o", "ConnectTimeout=5", VPS_HOST,
                     f"systemctl is-active {svc}.service"],
                    capture_output=True, text=True, timeout=10
                )
                status_text = result.stdout.strip()
                if status_text == "active":
                    self.check(f"VPS: {svc}.service", "PASS", "active")
                else:
                    self.check(f"VPS: {svc}.service", "WARN",
                               f"status={status_text}", "WARNING")
            except Exception as e:
                self.check(f"VPS: {svc}.service", "WARN", f"確認できなかった: {e}", "WARNING")

    def check_vps_retired_artifact(self):
        """VPS で /opt/CLAUDE.md が存在しないことを確認"""
        try:
            result = subprocess.run(
                ["ssh", "-o", "ConnectTimeout=5", VPS_HOST,
                 "test -f /opt/CLAUDE.md && echo EXISTS || echo ABSENT"],
                capture_output=True, text=True, timeout=10
            )
            output = result.stdout.strip()
            if output == "ABSENT":
                self.check("VPS: /opt/CLAUDE.md (retired)", "PASS", "ファイルなし（退役済み確認）")
            elif output == "EXISTS":
                self.check("VPS: /opt/CLAUDE.md (retired)", "FAIL",
                           "退役済みのはずが存在している！immediate investigation required", "ERROR")
            else:
                self.check("VPS: /opt/CLAUDE.md (retired)", "WARN",
                           f"確認結果不明: {output}", "WARNING")
        except Exception as e:
            self.check("VPS: /opt/CLAUDE.md (retired)", "WARN", f"SSH 失敗: {e}", "WARNING")

    def check_vps_tombstone(self):
        """VPS で tombstone が存在することを確認"""
        try:
            result = subprocess.run(
                ["ssh", "-o", "ConnectTimeout=5", VPS_HOST,
                 "test -f /opt/CLAUDE.md.retired-20260314 && echo EXISTS || echo ABSENT"],
                capture_output=True, text=True, timeout=10
            )
            output = result.stdout.strip()
            if output == "EXISTS":
                self.check("VPS: /opt/CLAUDE.md.retired-20260314 (tombstone)", "PASS")
            else:
                self.check("VPS: /opt/CLAUDE.md.retired-20260314 (tombstone)", "WARN",
                           "tombstone が見当たらない", "WARNING")
        except Exception as e:
            self.check("VPS: tombstone", "WARN", f"SSH 失敗: {e}", "WARNING")

    def check_vps_neo_reading_path(self):
        """NEO の実効 prompt source 確認"""
        for name, path in [
            ("NEO-ONE", "/opt/claude-code-telegram/src/sdk_integration.py"),
            ("NEO-TWO", "/opt/claude-code-telegram-neo2/src/sdk_integration.py"),
        ]:
            try:
                result = subprocess.run(
                    ["ssh", "-o", "ConnectTimeout=5", VPS_HOST,
                     f"grep -n 'neo_system_prompt' {path} | head -3"],
                    capture_output=True, text=True, timeout=10
                )
                if result.stdout.strip():
                    self.check(f"VPS: {name} runtime prompt source", "PASS",
                               f"neo_system_prompt found in {path}")
                else:
                    self.check(f"VPS: {name} runtime prompt source", "WARN",
                               f"neo_system_prompt が見つからない: {path}", "WARNING")
            except Exception as e:
                self.check(f"VPS: {name} runtime prompt source", "WARN",
                           f"SSH 失敗: {e}", "WARNING")

    def check_vps_prediction_links(self):
        """prediction_db.json の循環リンク（/predictions/）ゼロ確認"""
        try:
            result = subprocess.run(
                ["ssh", "-o", "ConnectTimeout=5", VPS_HOST,
                 "python3 -c \""
                 "import json;"
                 "d=json.load(open('/opt/shared/scripts/prediction_db.json'));"
                 "circular=[p['prediction_id'] for p in d['predictions'] if p.get('ghost_url','').rstrip('/')=='/predictions'.rstrip('/') or p.get('ghost_url','').endswith('/predictions/')];"
                 "print('CIRCULAR:'+str(len(circular)));"
                 "print(','.join(circular[:5]) if circular else 'none')"
                 "\""],
                capture_output=True, text=True, timeout=15
            )
            out = result.stdout.strip()
            lines = out.splitlines()
            count_line = next((l for l in lines if l.startswith("CIRCULAR:")), "CIRCULAR:?")
            count = int(count_line.split(":")[1]) if ":" in count_line else -1
            if count == 0:
                self.check("VPS: prediction_db 循環リンク(/predictions/)ゼロ確認", "PASS",
                           "循環リンクなし ✓")
            elif count > 0:
                ids_line = lines[1] if len(lines) > 1 else ""
                self.check("VPS: prediction_db 循環リンク(/predictions/)ゼロ確認", "FAIL",
                           f"{count} 件の循環リンクあり: {ids_line}", "ERROR")
            else:
                self.check("VPS: prediction_db 循環リンク(/predictions/)ゼロ確認", "WARN",
                           f"確認結果不明: {out}", "WARNING")
        except Exception as e:
            self.check("VPS: prediction_db 循環リンク(/predictions/)ゼロ確認", "WARN",
                       f"SSH 失敗: {e}", "WARNING")

    # ─── メイン ───────────────────────────────────────────

    def run(self):
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        if not self.json_output:
            print(f"\n{c('bold', '=== AI OS Doctor Report ===')} {ts}")
            print(f"{c('blue', 'Repo:')} {REPO_ROOT}\n")

            print(c('bold', "[Policy Files]"))
        self.check_policy_files()

        if not self.json_output:
            print(c('bold', "\n[Settings]"))
        self.check_settings_files()

        if not self.json_output:
            print(c('bold', "\n[Doctrine]"))
        self.check_doctrine_files()
        self.check_north_star()

        if not self.json_output:
            print(c('bold', "\n[Three-Layer Constitution]"))
        self.check_three_layer_constitution()

        if not self.json_output:
            print(c('bold', "\n[Hooks]"))
        self.check_hooks()

        if not self.json_output:
            print(c('bold', "\n[Scripts]"))
        self.check_scripts()

        if not self.json_output:
            print(c('bold', "\n[AI Civilization OS]"))
        self.check_civilization_os()

        if not self.json_output:
            print(c('bold', "\n[Retired Refs (local)]"))
        self.check_retired_refs()

        if not self.json_output:
            print(c('bold', "\n[Guard Scripts]"))
        self.check_guard_scripts()

        if not self.json_output:
            print(c('bold', "\n[Research Scripts]"))
        self.check_research_scripts()

        if not self.json_output:
            print(c('bold', "\n[State Files]"))
        self.check_state_files()

        if not self.json_output:
            print(c('bold', "\n[Memory Layer Integrity]"))
        self.check_memory_layer_integrity()

        if not self.json_output:
            print(c('bold', "\n[State Integrity]"))
        self.check_state_integrity()

        if not self.json_output:
            print(c('bold', "\n[Model Fixation Check]"))
        self.check_model_fixation_in_principles()

        if not self.json_output:
            print(c('bold', "\n[Runtime Packet]"))
        self.check_runtime_packet()

        if self.include_vps:
            if not self.json_output:
                print(c('bold', "\n[VPS Checks]"))
            self.check_vps_services()
            self.check_vps_retired_artifact()
            self.check_vps_tombstone()
            self.check_vps_neo_reading_path()
            self.check_vps_prediction_links()

        # ─── Summary ───────────────────────────────────────
        total = len(self.results)
        passed = sum(1 for r in self.results if r["status"] == "PASS")

        if self.json_output:
            output = {
                "timestamp": ts,
                "repo": str(REPO_ROOT),
                "summary": {
                    "total": total,
                    "passed": passed,
                    "warnings": self.warnings,
                    "errors": self.errors,
                    "exit_code": 2 if self.errors > 0 else (1 if self.warnings > 0 else 0)
                },
                "results": self.results
            }
            print(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            print(f"\n{'─'*50}")
            if self.errors > 0:
                print(c('red', f"[FAIL] error: {self.errors}, warn: {self.warnings} / {total} checks"))
            elif self.warnings > 0:
                print(c('yellow', f"[WARN] warn: {self.warnings} / {total} checks (PASS: {passed})"))
            else:
                print(c('green', f"[ALL PASS] {passed}/{total} checks"))
            print()

        return 2 if self.errors > 0 else (1 if self.warnings > 0 else 0)


def main():
    parser = argparse.ArgumentParser(description="AI OS Doctor — 全体健全性チェック")
    parser.add_argument("--vps", action="store_true", help="VPS SSH チェックを含める")
    parser.add_argument("--verbose", action="store_true", help="詳細ログ")
    parser.add_argument("--json", action="store_true", help="JSON 形式で出力")
    args = parser.parse_args()

    doc = Doctor(verbose=args.verbose, include_vps=args.vps, json_output=args.json)
    sys.exit(doc.run())


if __name__ == "__main__":
    main()
