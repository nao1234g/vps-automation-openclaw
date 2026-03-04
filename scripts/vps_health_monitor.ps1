# G4: vps_health_monitor.ps1
# VPS health check every 5 min. Telegram alert after 3 consecutive failures.
# Setup: Run scripts/setup_vps_monitor.py to register Task Scheduler.

$VPS_IP = "163.44.124.123"
$VPS_PORT = 22
$CONFIG_FILE = "$env:USERPROFILE\.claude\vps_monitor_config.json"
$STATE_FILE = "$env:TEMP\vps_health_state.json"
$MAX_FAILURES = 3

function Get-Config {
    if (Test-Path $CONFIG_FILE) {
        try { return Get-Content $CONFIG_FILE -Raw | ConvertFrom-Json }
        catch {}
    }
    return $null
}

function Get-State {
    if (Test-Path $STATE_FILE) {
        try { return Get-Content $STATE_FILE -Raw | ConvertFrom-Json }
        catch {}
    }
    return [PSCustomObject]@{
        failure_count = 0
        last_success = ""
        last_failure = ""
        alert_sent_at = ""
        consecutive_fail_start = ""
    }
}

function Save-State($s) {
    $s | ConvertTo-Json | Out-File $STATE_FILE -Encoding UTF8
}

function Send-Alert($token, $chatId, $text) {
    try {
        $enc = [System.Text.Encoding]::UTF8
        $body = '{"chat_id":"' + $chatId + '","text":"' + $text.Replace('"','\"').Replace("`n",'\n') + '"}'
        $bytes = $enc.GetBytes($body)
        $url = "https://api.telegram.org/bot" + $token + "/sendMessage"
        $req = [System.Net.WebRequest]::Create($url)
        $req.Method = "POST"
        $req.ContentType = "application/json"
        $req.Timeout = 10000
        $stream = $req.GetRequestStream()
        $stream.Write($bytes, 0, $bytes.Length)
        $stream.Close()
        $resp = $req.GetResponse()
        $resp.Close()
        return $true
    } catch {
        return $false
    }
}

function Test-VPSAlive {
    try {
        $p = New-Object System.Net.NetworkInformation.Ping
        $r = $p.Send($VPS_IP, 5000)
        return ($r.Status -eq "Success")
    } catch {
        return $false
    }
}

function Test-VPSPort {
    try {
        $tc = New-Object System.Net.Sockets.TcpClient
        $ar = $tc.BeginConnect($VPS_IP, $VPS_PORT, $null, $null)
        $ok = $ar.AsyncWaitHandle.WaitOne(5000, $false)
        if ($ok) { $tc.EndConnect($ar) }
        $tc.Close()
        return $ok
    } catch {
        return $false
    }
}

# === Main ===
$now = Get-Date
$ts = $now.ToString("yyyy-MM-dd HH:mm:ss")
$state = Get-State
$config = Get-Config

$icmp = Test-VPSAlive
$tcp = Test-VPSPort
$alive = $icmp -or $tcp

if ($alive) {
    if ($state.failure_count -gt 0) {
        Write-Host "[$ts] VPS recovered (was down $($state.failure_count) checks)"
        if ($config -and ($state.failure_count -ge $MAX_FAILURES)) {
            $downMin = $state.failure_count * 5
            $txt = "G4 VPS Recovered`nIP: $VPS_IP`nTime: $ts`nWas down: approx $downMin min"
            Send-Alert $config.bot_token $config.chat_id $txt | Out-Null
        }
    } else {
        Write-Host "[$ts] VPS OK"
    }
    $state.failure_count = 0
    $state.last_success = $now.ToString("o")
    $state.alert_sent_at = ""
    $state.consecutive_fail_start = ""
} else {
    $state.failure_count++
    $state.last_failure = $now.ToString("o")
    if ($state.failure_count -eq 1) {
        $state.consecutive_fail_start = $now.ToString("o")
    }
    Write-Host "[$ts] VPS UNREACHABLE (count=$($state.failure_count) icmp=$icmp tcp=$tcp)"

    if ($state.failure_count -ge $MAX_FAILURES) {
        $canAlert = $true
        if ($state.alert_sent_at -ne "") {
            try {
                $lastAlert = [datetime]::Parse($state.alert_sent_at)
                if (($now - $lastAlert).TotalMinutes -lt 30) { $canAlert = $false }
            } catch {}
        }
        if ($canAlert -and $config) {
            $downMin = $state.failure_count * 5
            $startStr = ""
            if ($state.consecutive_fail_start -ne "") {
                try { $startStr = [datetime]::Parse($state.consecutive_fail_start).ToString("HH:mm") } catch {}
            }
            $txt = "G4 VPS EMERGENCY: Unreachable`nIP: $VPS_IP`nDown: $($state.failure_count) checks (~$downMin min)`nStarted: $startStr`nNow: $ts`nPlease check immediately!"
            $sent = Send-Alert $config.bot_token $config.chat_id $txt
            if ($sent) {
                Write-Host "[$ts] Telegram alert sent"
                $state.alert_sent_at = $now.ToString("o")
            }
        }
    }
}

Save-State $state
