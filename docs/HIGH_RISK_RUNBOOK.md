# HIGH RISK RUNBOOK — 高リスク操作の手順書

> **このファイルの操作は全て Type 1（不可逆）です。実行前に必ず全手順を読み、バックアップを確認してください。**
> 作成日: 2026-03-25
> 目的: Privacy hardening で発見された高リスク項目の手順化（実行はオーナー判断）

---

## 背景

2026-03-25 の調査で以下が判明:

- **GitHub リポジトリは PUBLIC** (`https://github.com/nao1234g/vps-automation-openclaw`)
- **ZONE 0/1 のファイルが git 履歴に存在**（secrets.txt, founder_memory/, brainstorm/, decisions/, intelligence/, .claude/memory/, .claude/state/, docs/*STRATEGY* 等）
- **OneDrive 同期パス上にリポジトリがある**（Microsoft クラウドにも同期されている可能性）

**緊急度順の推奨実行順序:**

```
1. repo private 化           ← 最優先（即座に公開アクセスを遮断）
2. git rm --cached          ← 追跡解除（今後のcommitに含まれない）
3. git history rewrite      ← 履歴からも完全削除
4. OneDrive 除外設定         ← Microsoft クラウドへの同期を制限
5. GitHub secret scanning   ← 継続的な監視
```

---

## 操作1: GitHub リポジトリを Private に変更

**リスク**: 低（いつでも Public に戻せる）
**影響**: 外部からのアクセスが即座に遮断される
**所要時間**: 1分

### 手順

1. ブラウザで `https://github.com/nao1234g/vps-automation-openclaw/settings` にアクセス
2. ページ最下部の **Danger Zone** セクションまでスクロール
3. **Change repository visibility** → **Change visibility** をクリック
4. **Make private** を選択
5. リポジトリ名 `vps-automation-openclaw` を入力して確認

### 確認

```bash
# 200 → 404 に変わることを確認
curl -s -o /dev/null -w "%{http_code}" "https://github.com/nao1234g/vps-automation-openclaw"
```

### 注意事項

- Fork が存在する場合、Fork は独立して Public のまま残る（現在 Forks: 0 なので問題なし）
- GitHub Pages を使用している場合は停止される
- 外部サービス（CI/CD等）からのアクセスが止まる可能性がある

---

## 操作2: ZONE 0/1 ファイルの git 追跡解除（git rm --cached）

**リスク**: 中（ファイルは削除されないが、次の push で他の clone に影響）
**影響**: ローカルファイルは残るが git 追跡から外れる
**所要時間**: 5分

### 前提条件

- 操作1（repo private 化）が完了していること
- `.gitignore` に ZONE 0/1 パスが追加済みであること（Task 1 で完了済み）

### 手順

```bash
# ── Step 1: 現在の追跡状態を確認 ──
git ls-files | grep -E "^(secrets\.txt|founder_memory/|brainstorm/|decisions/|intelligence/|\.claude/memory/|\.claude/state/|\.claude/plans/)" > /tmp/zone01_tracked.txt
cat /tmp/zone01_tracked.txt
# → 追跡解除するファイルの一覧を目視確認

# ── Step 2: バックアップ ──
# ファイル自体は削除されないが、念のため
cp -r founder_memory/ /tmp/backup_founder_memory/
cp -r brainstorm/ /tmp/backup_brainstorm/
cp -r decisions/ /tmp/backup_decisions/
cp -r intelligence/ /tmp/backup_intelligence/
cp secrets.txt /tmp/backup_secrets.txt

# ── Step 3: git 追跡解除（ファイルは残る） ──
git rm --cached secrets.txt
git rm --cached -r founder_memory/
git rm --cached -r brainstorm/
git rm --cached -r decisions/
git rm --cached -r intelligence/
git rm --cached -r .claude/memory/
git rm --cached -r .claude/state/
git rm --cached -r .claude/plans/

# ── Step 4: 戦略ドキュメントも追跡解除 ──
git rm --cached "docs/NOWPATTERN_STRATEGY_2026Q1.md" 2>/dev/null || true
git rm --cached "docs/NOWPATTERN_STRATEGY_2026Q1_v2.md" 2>/dev/null || true
git rm --cached "docs/NOWPATTERN_STRATEGIC_PROPOSALS.md" 2>/dev/null || true

# ── Step 5: 確認 ──
git status
# → "deleted:" と表示されるが、ファイル自体はディスク上に残っている

# ── Step 6: コミット ──
git commit -m "security: remove ZONE 0/1 files from git tracking

Files are preserved locally but no longer tracked by git.
.gitignore already updated to prevent re-addition.
See docs/PRIVACY_POLICY.md for zone classification."

# ── Step 7: 追跡解除が成功したことを確認 ──
git ls-files | grep -E "^(secrets\.txt|founder_memory/|brainstorm/|decisions/|intelligence/|\.claude/memory/|\.claude/state/)" | wc -l
# → 0 であること
```

### 注意事項

- `git rm --cached` はファイルを**ディスクから削除しない**（`--cached` が重要）
- ファイルは git 履歴には**まだ残っている**（操作3 で対処）
- この後 `git push` すると、他の clone で `git pull` した人はこれらのファイルが削除される

---

## 操作3: git 履歴からの完全削除（BFG Repo-Cleaner）

**リスク**: 高（git 履歴が書き換わる。全 clone で force push が必要）
**影響**: 過去のコミットからも ZONE 0/1 ファイルが消える
**所要時間**: 15〜30分

### 前提条件

- 操作1, 2 が完了していること
- 他の開発者がいないこと（現在 Stars: 0, Forks: 0 なので問題なし）

### 方法A: BFG Repo-Cleaner（推奨 — 高速・安全）

```bash
# ── Step 1: BFG をダウンロード ──
# https://rtyley.github.io/bfg-repo-cleaner/ からダウンロード
# Java が必要: java -version で確認

# ── Step 2: リポジトリの完全クローン（--mirror） ──
git clone --mirror https://github.com/nao1234g/vps-automation-openclaw.git repo-mirror.git

# ── Step 3: 削除対象を指定して実行 ──
# secrets.txt を全履歴から削除
java -jar bfg.jar --delete-files secrets.txt repo-mirror.git

# ZONE 0/1 ディレクトリを全履歴から削除
java -jar bfg.jar --delete-folders founder_memory repo-mirror.git
java -jar bfg.jar --delete-folders brainstorm repo-mirror.git
java -jar bfg.jar --delete-folders decisions repo-mirror.git
java -jar bfg.jar --delete-folders intelligence repo-mirror.git

# .claude/memory と .claude/state はディレクトリ内にあるため個別指定
# BFG はフォルダ名でマッチするので注意
java -jar bfg.jar --delete-folders memory --no-blob-protection repo-mirror.git
java -jar bfg.jar --delete-folders state --no-blob-protection repo-mirror.git

# ── Step 4: gc で不要オブジェクトを完全削除 ──
cd repo-mirror.git
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# ── Step 5: force push ──
git push --force
```

### 方法B: git filter-repo（BFG が使えない場合）

```bash
# pip install git-filter-repo

# リポジトリの完全クローン
git clone https://github.com/nao1234g/vps-automation-openclaw.git repo-clean
cd repo-clean

# パスベースで削除
git filter-repo --path secrets.txt --invert-paths
git filter-repo --path founder_memory/ --invert-paths
git filter-repo --path brainstorm/ --invert-paths
git filter-repo --path decisions/ --invert-paths
git filter-repo --path intelligence/ --invert-paths
git filter-repo --path .claude/memory/ --invert-paths
git filter-repo --path .claude/state/ --invert-paths
git filter-repo --path .claude/plans/ --invert-paths
git filter-repo --path docs/NOWPATTERN_STRATEGY_2026Q1.md --invert-paths
git filter-repo --path docs/NOWPATTERN_STRATEGY_2026Q1_v2.md --invert-paths
git filter-repo --path docs/NOWPATTERN_STRATEGIC_PROPOSALS.md --invert-paths

# remote を再設定（filter-repo が削除するため）
git remote add origin https://github.com/nao1234g/vps-automation-openclaw.git

# force push
git push --force --all
git push --force --tags
```

### 確認

```bash
# 履歴に残っていないことを確認
git log --all --diff-filter=A -- secrets.txt
# → 結果が空であること

git log --all --diff-filter=A -- founder_memory/
# → 結果が空であること
```

### 注意事項

- **force push は不可逆**。実行前に mirror clone をバックアップとして保存
- GitHub のキャッシュは最大24時間残る可能性がある
- `secrets.txt` に含まれる SHA-256 ハッシュ自体は元のシークレットではないが、念のため削除推奨
- `.claude/memory/chromadb/chroma.sqlite3` は大きなバイナリ — 履歴に残るとリポジトリサイズに影響

---

## 操作4: OneDrive 同期除外設定

**リスク**: 低（OneDrive の設定変更のみ）
**影響**: 除外したフォルダは Microsoft クラウドから削除される可能性がある
**所要時間**: 5分

### 現状

リポジトリパス: `C:\Users\user\OneDrive\デスクトップ\vps-automation-openclaw`

このパスは OneDrive 同期範囲内にあり、`.claude/memory/`, `.claude/state/` 等が Microsoft クラウドにも同期されている可能性がある。

### 方法A: OneDrive 選択的同期で除外

1. タスクバーの OneDrive アイコンを右クリック → **設定**
2. **アカウント** → **フォルダーの選択**
3. `vps-automation-openclaw` フォルダ全体、または以下のサブフォルダのチェックを外す:
   - `.claude/memory/`
   - `.claude/state/`
   - `.claude/plans/`
   - `founder_memory/`
   - `brainstorm/`
   - `decisions/`
   - `intelligence/`

### 方法B: リポジトリを OneDrive 外に移動（推奨）

```powershell
# OneDrive 外のパスに移動
# 例: C:\Projects\ に移動
mkdir C:\Projects
# OneDrive 同期を一時停止してから:
Move-Item "C:\Users\user\OneDrive\デスクトップ\vps-automation-openclaw" "C:\Projects\vps-automation-openclaw"

# シンボリックリンクを残す（デスクトップからアクセスしたい場合）
New-Item -ItemType SymbolicLink -Path "C:\Users\user\OneDrive\デスクトップ\vps-automation-openclaw" -Target "C:\Projects\vps-automation-openclaw"
```

### 注意事項

- 方法A: OneDrive の「フォルダーの選択」で除外すると、クラウド上のコピーが削除される場合がある。ローカルにバックアップを取ってから操作
- 方法B: VSCode のワークスペースパスが変わるため、設定の更新が必要
- `.claude/` フォルダ内の `settings.local.json` 等はパスに依存する設定がある可能性

---

## 操作5: GitHub Secret Scanning 有効化

**リスク**: なし（読み取り専用の監視機能）
**影響**: コミットに秘密情報が含まれる場合にアラートが出る
**所要時間**: 2分

### 手順

1. `https://github.com/nao1234g/vps-automation-openclaw/settings/security_analysis` にアクセス
2. **Secret scanning** → Enable
3. **Push protection** → Enable（コミット時にブロック）

### 注意事項

- Private リポジトリでは GitHub Advanced Security（有料）が必要な場合がある
- Public リポジトリでは無料で利用可能
- 既存の履歴もスキャンされ、アラートが出る可能性がある

---

## 実行チェックリスト

```
□ 操作1: GitHub repo → Private
    □ Settings > Danger Zone > Change visibility
    □ curl で 404 を確認

□ 操作2: git rm --cached
    □ バックアップ取得
    □ git rm --cached 実行
    □ git commit
    □ git ls-files で追跡解除を確認

□ 操作3: git 履歴書き換え
    □ mirror clone バックアップ
    □ BFG or git-filter-repo 実行
    □ gc + prune
    □ git push --force
    □ 履歴にファイルが残っていないことを確認

□ 操作4: OneDrive 除外
    □ 方法選択（A: 選択的同期 / B: リポジトリ移動）
    □ バックアップ取得
    □ 設定変更
    □ 同期状態を確認

□ 操作5: GitHub Secret Scanning
    □ Secret scanning 有効化
    □ Push protection 有効化
```

---

## FAQ

**Q: secrets.txt の SHA-256 ハッシュは危険？**
A: ハッシュ自体は元の値を復元できないが、レインボーテーブル攻撃の対象になる可能性がある。また「ハッシュが存在する」こと自体がセキュリティ体制の情報漏洩。削除推奨。

**Q: .claude/rules/infrastructure.md に VPS IP が含まれているが？**
A: このファイルは git 追跡されており、Public 時に外部からアクセス可能だった。repo Private 化後は問題ないが、IP アドレスのローテーションも検討可能。

**Q: 操作2 の後すぐに push して大丈夫？**
A: 操作1（Private 化）が完了していれば安全。Private リポジトリへの push は認証済みユーザーのみアクセス可能。

**Q: 操作3 は必須？**
A: 操作1（Private 化）で外部アクセスは遮断される。将来 Public に戻す予定がなければ操作3 は任意。ただし、セキュリティベストプラクティスとしては推奨。

---

*作成: 2026-03-25 Privacy Hardening Phase 3*
