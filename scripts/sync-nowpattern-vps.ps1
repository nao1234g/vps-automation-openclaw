# ============================================
# Nowpattern Scripts Sync - Local -> VPS
# ============================================
# Nowpattern v3.0 のスクリプト群をVPSに同期する。
# NEO-ONE/TWO が /opt/shared/scripts/ 経由でアクセスできるようにする。
#
# 安全機能（v2.0 2026-02-22）:
#   - 転送前にVPS版をバックアップ（.bak.YYYYMMDD-HHMMSS）
#   - article_validator.py を同期対象に追加
#   - breaking_pipeline_helper.py を同期対象に追加
#   - ghost_guard.py, post_audit.py は除外（VPS専用スクリプト）
#
# 手動実行:
#   powershell -ExecutionPolicy Bypass -File .\scripts\sync-nowpattern-vps.ps1
#
# オプション:
#   -InjectCSS    Ghost Custom CSSを投入
#   -NoBackup     バックアップをスキップ（非推奨）
# ============================================

$VPS_HOST = "root@163.44.124.123"
$PROJECT_ROOT = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

# --- 同期対象ファイル ---
$FILES = @(
    @{ Local = "$PROJECT_ROOT\scripts\nowpattern_article_builder.py";  Remote = "/opt/shared/scripts/nowpattern_article_builder.py" },
    @{ Local = "$PROJECT_ROOT\scripts\nowpattern_publisher.py";        Remote = "/opt/shared/scripts/nowpattern_publisher.py" },
    @{ Local = "$PROJECT_ROOT\scripts\article_validator.py";           Remote = "/opt/shared/scripts/article_validator.py" },
    @{ Local = "$PROJECT_ROOT\scripts\breaking_pipeline_helper.py";    Remote = "/opt/shared/scripts/breaking_pipeline_helper.py" },
    @{ Local = "$PROJECT_ROOT\scripts\gen_dynamics_diagram.py";        Remote = "/opt/shared/scripts/gen_dynamics_diagram.py" },
    @{ Local = "$PROJECT_ROOT\scripts\inject_ghost_css.py";            Remote = "/opt/shared/scripts/inject_ghost_css.py" },
    @{ Local = "$PROJECT_ROOT\scripts\nowpattern_article_index.json";  Remote = "/opt/shared/nowpattern_article_index.json" },
    @{ Local = "$PROJECT_ROOT\scripts\nowpattern_taxonomy.json";       Remote = "/opt/shared/scripts/nowpattern_taxonomy.json" },
    @{ Local = "$PROJECT_ROOT\scripts\nowpattern-deep-pattern-generate.py"; Remote = "/opt/shared/scripts/nowpattern-deep-pattern-generate.py" },
    @{ Local = "$PROJECT_ROOT\docs\NEO_INSTRUCTIONS_V2.md";            Remote = "/opt/shared/docs/NEO_INSTRUCTIONS_V2.md" },
    @{ Local = "$PROJECT_ROOT\docs\ARTICLE_FORMAT.md";                 Remote = "/opt/shared/docs/ARTICLE_FORMAT.md" },
    @{ Local = "$PROJECT_ROOT\docs\NOWPATTERN_TAXONOMY_v2.md";         Remote = "/opt/shared/docs/NOWPATTERN_TAXONOMY_v2.md" },
    @{ Local = "$PROJECT_ROOT\docs\KNOWN_MISTAKES.md";                Remote = "/opt/shared/docs/KNOWN_MISTAKES.md" },
    @{ Local = "$PROJECT_ROOT\.claude\CLAUDE.md";                     Remote = "/opt/shared/docs/LOCAL_CLAUDE_MD.md" }
)

# --- VPS専用ファイル（同期しない、VPSで直接管理） ---
# ghost_guard.py, nowpattern_post_audit.py, .ghost_publish_key
# これらはVPS上で直接管理され、ローカルから上書きしてはいけない

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] $Message"
}

Write-Log "=== Nowpattern VPS Sync Start (v2.0 - with backup) ==="

# 0. SSH接続確認
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o BatchMode=yes $VPS_HOST "echo OK" 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Log "ERROR: SSH connection failed"
    exit 1
}

# 1. VPS側ディレクトリ作成
Write-Log "Ensuring remote directories exist..."
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o BatchMode=yes $VPS_HOST "mkdir -p /opt/shared/scripts /opt/shared/docs /opt/shared/scripts/backup" 2>&1

# 2. VPS側バックアップ（転送前）
$backupTimestamp = Get-Date -Format "yyyyMMdd-HHmmss"
if ($args -notcontains "-NoBackup") {
    Write-Log "Creating VPS-side backups..."
    $remoteFiles = ($FILES | ForEach-Object { $_.Remote }) -join " "
    ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o BatchMode=yes $VPS_HOST "for f in $remoteFiles; do if [ -f `"`$f`" ]; then cp `"`$f`" `"`$f.bak.$backupTimestamp`"; fi; done" 2>&1
    Write-Log "  Backups created with suffix .bak.$backupTimestamp"
} else {
    Write-Log "  SKIPPING backup (--NoBackup flag)"
}

# 3. ファイル転送
$successCount = 0
foreach ($file in $FILES) {
    if (-not (Test-Path $file.Local)) {
        Write-Log "SKIP: $($file.Local) not found"
        continue
    }
    $name = Split-Path -Leaf $file.Local
    Write-Log "Uploading $name..."
    scp -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o BatchMode=yes $file.Local "${VPS_HOST}:$($file.Remote)" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Log "  OK: $name -> $($file.Remote)"
        $successCount++
    } else {
        Write-Log "  ERROR: Failed to upload $name"
    }
}

# 4. VPS側パーミッション設定
Write-Log "Setting permissions..."
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o BatchMode=yes $VPS_HOST "chmod 664 /opt/shared/scripts/nowpattern_*.py /opt/shared/scripts/nowpattern_*.json /opt/shared/scripts/gen_dynamics_diagram.py /opt/shared/scripts/article_validator.py /opt/shared/scripts/breaking_pipeline_helper.py /opt/shared/nowpattern_article_index.json /opt/shared/docs/*.md 2>/dev/null; chmod 775 /opt/shared/scripts /opt/shared/docs" 2>&1

# 5. VPS専用ファイルの保護確認
Write-Log "Verifying VPS-only files are intact..."
$vpsOnlyCheck = ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o BatchMode=yes $VPS_HOST "ls -la /opt/shared/scripts/ghost_guard.py /opt/shared/scripts/nowpattern_post_audit.py /opt/shared/scripts/.ghost_publish_key 2>/dev/null | wc -l" 2>&1
Write-Log "  VPS-only files found: $vpsOnlyCheck/3"

Write-Log "=== Sync Complete: $successCount / $($FILES.Count) files ==="

# 6. Ghost Custom CSS 投入（オプション: -InjectCSS フラグ）
if ($args -contains "-InjectCSS") {
    Write-Log "Injecting Ghost Custom CSS..."
    ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o BatchMode=yes $VPS_HOST "python3 /opt/shared/scripts/inject_ghost_css.py && systemctl restart ghost-nowpattern" 2>&1
    Write-Log "Ghost CSS injection done"
}
