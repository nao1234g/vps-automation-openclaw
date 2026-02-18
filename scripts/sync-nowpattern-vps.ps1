# ============================================
# Nowpattern Scripts Sync - Local -> VPS
# ============================================
# Nowpattern v3.0 のスクリプト群をVPSに同期する。
# NEO-ONE/TWO が /opt/shared/scripts/ 経由でアクセスできるようにする。
#
# 手動実行:
#   powershell -ExecutionPolicy Bypass -File .\scripts\sync-nowpattern-vps.ps1
# ============================================

$VPS_HOST = "root@163.44.124.123"
$PROJECT_ROOT = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

# --- 同期対象ファイル ---
$FILES = @(
    @{ Local = "$PROJECT_ROOT\scripts\nowpattern_article_builder.py";  Remote = "/opt/shared/scripts/nowpattern_article_builder.py" },
    @{ Local = "$PROJECT_ROOT\scripts\nowpattern_publisher.py";        Remote = "/opt/shared/scripts/nowpattern_publisher.py" },
    @{ Local = "$PROJECT_ROOT\scripts\gen_dynamics_diagram.py";        Remote = "/opt/shared/scripts/gen_dynamics_diagram.py" },
    @{ Local = "$PROJECT_ROOT\scripts\inject_ghost_css.py";             Remote = "/opt/shared/scripts/inject_ghost_css.py" },
    @{ Local = "$PROJECT_ROOT\scripts\nowpattern_article_index.json";  Remote = "/opt/shared/nowpattern_article_index.json" },
    @{ Local = "$PROJECT_ROOT\docs\NEO_INSTRUCTIONS_V2.md";            Remote = "/opt/shared/docs/NEO_INSTRUCTIONS_V2.md" }
)

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] $Message"
}

Write-Log "=== Nowpattern VPS Sync Start ==="

# 1. VPS側ディレクトリ作成
Write-Log "Ensuring remote directories exist..."
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o BatchMode=yes $VPS_HOST "mkdir -p /opt/shared/scripts /opt/shared/docs" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Log "ERROR: SSH connection failed"
    exit 1
}

# 2. ファイル転送
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

# 3. VPS側パーミッション設定
Write-Log "Setting permissions..."
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o BatchMode=yes $VPS_HOST "chmod 664 /opt/shared/scripts/nowpattern_*.py /opt/shared/scripts/gen_dynamics_diagram.py /opt/shared/nowpattern_article_index.json /opt/shared/docs/NEO_INSTRUCTIONS_V2.md 2>/dev/null; chmod 775 /opt/shared/scripts /opt/shared/docs" 2>&1

Write-Log "=== Sync Complete: $successCount / $($FILES.Count) files ==="

# 4. Ghost Custom CSS 投入（オプション: -InjectCSS フラグ）
if ($args -contains "-InjectCSS") {
    Write-Log "Injecting Ghost Custom CSS..."
    ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o BatchMode=yes $VPS_HOST "python3 /opt/shared/scripts/inject_ghost_css.py && systemctl restart ghost-nowpattern" 2>&1
    Write-Log "Ghost CSS injection done"
}
