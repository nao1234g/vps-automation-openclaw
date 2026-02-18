# ============================================
# NEO Token Sync - ローカル → VPS 自動トークン転送
# ============================================
# Windows タスクスケジューラで6時間ごとに実行
# ローカルPCのClaude認証トークンをVPSにコピーし、NEOサービスを再起動
#
# 設定方法:
#   schtasks /create /tn "NEO Token Sync" /tr "powershell -ExecutionPolicy Bypass -File '%USERPROFILE%\OneDrive\デスクトップ\vps-automation-openclaw\scripts\sync-neo-token.ps1'" /sc hourly /mo 6 /st 00:00 /ru "%USERNAME%" /f
#
# 手動実行:
#   powershell -ExecutionPolicy Bypass -File .\scripts\sync-neo-token.ps1
# ============================================

$VPS_HOST = "root@163.44.124.123"
$LOCAL_CRED = "$env:USERPROFILE\.claude\.credentials.json"
$REMOTE_CRED = "/root/.claude/.credentials.json"
$LOG_FILE = "$env:USERPROFILE\.claude\neo-token-sync.log"

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$timestamp] $Message"
    Write-Host $line
    Add-Content -Path $LOG_FILE -Value $line -ErrorAction SilentlyContinue
}

# ログファイルのサイズ管理（1MB超えたらローテーション）
if (Test-Path $LOG_FILE) {
    $size = (Get-Item $LOG_FILE).Length
    if ($size -gt 1MB) {
        $backup = "$LOG_FILE.old"
        if (Test-Path $backup) { Remove-Item $backup -Force }
        Rename-Item $LOG_FILE $backup -Force
    }
}

Write-Log "=== NEO Token Sync Start ==="

# 1. ローカルトークンの存在確認
if (-not (Test-Path $LOCAL_CRED)) {
    Write-Log "ERROR: Local credentials not found: $LOCAL_CRED"
    exit 1
}

# 2. ローカルトークンの有効期限チェック
try {
    $json = Get-Content $LOCAL_CRED -Raw | ConvertFrom-Json
    $expiresAt = $json.claudeAiOauth.expiresAt
    $nowMs = [long]([DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds())
    $remainHours = [math]::Round(($expiresAt - $nowMs) / 3600000, 1)

    if ($remainHours -lt 0) {
        Write-Log "WARNING: Local token EXPIRED ($remainHours hours ago). Skipping sync."
        Write-Log "Run 'claude' locally to refresh token, then retry."
        exit 1
    }

    Write-Log "Local token valid for $remainHours hours"
} catch {
    Write-Log "ERROR: Failed to parse credentials: $_"
    exit 1
}

# 3. VPSへSCP転送
Write-Log "Copying token to VPS..."
$scpResult = scp -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o BatchMode=yes $LOCAL_CRED "${VPS_HOST}:${REMOTE_CRED}" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Log "ERROR: SCP failed: $scpResult"
    exit 1
}
Write-Log "Token copied to VPS successfully"

# 4. VPS上でトークン確認 + NEOサービス管理
Write-Log "Checking NEO services on VPS..."
$sshResult = ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o BatchMode=yes $VPS_HOST "bash /opt/scripts/check-neo-token.sh; N1=`$(systemctl is-active neo-telegram); N2=`$(systemctl is-active neo2-telegram); echo NEO-ONE:`$N1 NEO-TWO:`$N2; if [ `$N1 != active ]; then systemctl restart neo-telegram; echo NEO-ONE-restarted; fi; if [ `$N2 != active ]; then systemctl restart neo2-telegram; echo NEO-TWO-restarted; fi" 2>&1

Write-Log $sshResult
Write-Log "=== NEO Token Sync Complete ==="
