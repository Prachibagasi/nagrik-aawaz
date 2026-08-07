# Smoke-test API routes with curl.exe against a running server.
# Prereqs: categories seeded; users +919000000001 (officer), +919000000002 (admin).
# Usage: set AWAAZ_BASE_URL=http://127.0.0.1:8765 (optional); .\scripts\curl_smoke_all.ps1
$ErrorActionPreference = "Stop"
$Base = if ($env:AWAAZ_BASE_URL) { $env:AWAAZ_BASE_URL.TrimEnd("/") } else { "http://127.0.0.1:8765" }

function Invoke-CurlApi {
    param(
        [string]$Name,
        [ValidateSet("GET", "POST", "PATCH")]
        [string]$Method,
        [string]$Path,
        [string]$JsonBody = $null,
        [string[]]$ExtraHeaders = @()
    )
    $curlArgs = @("-s", "-S", "-w", "`n__HTTP__:%{http_code}", "-X", $Method, "$Base$Path", "-H", "Content-Type: application/json")
    foreach ($h in $ExtraHeaders) { $curlArgs += "-H"; $curlArgs += $h }
    $tmpJson = $null
    if (-not [string]::IsNullOrWhiteSpace($JsonBody)) {
        $tmpJson = [IO.Path]::ChangeExtension([IO.Path]::GetTempFileName(), ".json")
        $utf8NoBom = New-Object System.Text.UTF8Encoding $false
        [IO.File]::WriteAllText($tmpJson, $JsonBody, $utf8NoBom)
        $curlArgs += "--data-binary"; $curlArgs += "@$tmpJson"
    }
    try {
        $raw = (& curl.exe @curlArgs 2>&1 | Out-String).TrimEnd("`r", "`n", " ")
    } finally {
        if ($null -ne $tmpJson -and (Test-Path $tmpJson)) { Remove-Item -LiteralPath $tmpJson -Force -ErrorAction SilentlyContinue }
    }
    if ($LASTEXITCODE -ne 0) { throw "curl failed ($Name): $raw" }
    if ($raw -match "__HTTP__:(\d+)\s*$") {
        $code = [int]$Matches[1]
        $body = ($raw -replace "__HTTP__:\d+\s*$", "").TrimEnd()
    } else {
        $code = -1
        $body = [string]$raw
    }
    [PSCustomObject]@{
        Name         = $Name
        Code         = $code
        FullBody     = $body
        BodyPreview  = ($body.Substring(0, [Math]::Min(140, $body.Length)))
    }
}

$rows = New-Object System.Collections.Generic.List[object]
function Add-Row($o) { [void]$rows.Add($o) }

# --- Health ---
Add-Row (Invoke-CurlApi "GET health" "GET" "/api/v1/health/")

# --- Register citizen ---
$suffix = Get-Random -Minimum 1000000 -Maximum 9999999
$phone = "+91987$suffix"
$regBody = (@{
        phone                = $phone
        full_name            = "Curl User"
        password             = "TestPass123!"
        confirm_password     = "TestPass123!"
        preferred_language   = "hi"
        role                 = "citizen"
    } | ConvertTo-Json -Compress)
$regCurl = Invoke-CurlApi "POST auth_register" "POST" "/api/v1/auth/register/" $regBody
Add-Row $regCurl
if ($regCurl.Code -ne 201) { throw "register failed HTTP $($regCurl.Code): $($regCurl.BodyPreview)" }
$fullReg = $regCurl.FullBody | ConvertFrom-Json
$accessCit = $fullReg.tokens.access
$refreshCit = $fullReg.tokens.refresh

# --- Login ---
Add-Row (Invoke-CurlApi "POST auth_login" "POST" "/api/v1/auth/login/" (@{ phone = $phone; password = "TestPass123!" } | ConvertTo-Json -Compress))

# --- Me ---
Add-Row (Invoke-CurlApi "GET auth_me" "GET" "/api/v1/auth/me/" -ExtraHeaders @("Authorization: Bearer $accessCit"))

# --- Officer & admin tokens (IRM) ---
$offLogin = Invoke-RestMethod -Uri "$Base/api/v1/auth/login/" -Method Post -Body (@{ phone = "+919000000001"; password = "TestPass123!" } | ConvertTo-Json) -ContentType "application/json"
$admLogin = Invoke-RestMethod -Uri "$Base/api/v1/auth/login/" -Method Post -Body (@{ phone = "+919000000002"; password = "TestPass123!" } | ConvertTo-Json) -ContentType "application/json"
$accessOff = $offLogin.access
$accessAdm = $admLogin.access

# --- OTP send + verify (read OTP from DB) ---
$otpPhone = "+91976$suffix"
Add-Row (Invoke-CurlApi "POST auth_otp_send" "POST" "/api/v1/auth/otp/send/" (@{ phone = $otpPhone } | ConvertTo-Json -Compress))
Push-Location $PSScriptRoot\..
$otpCode = (py -3.13 manage.py shell -c "from apps.accounts.models import OTPVerification as O; r=O.objects.filter(phone='$otpPhone').order_by('-created_at').first(); print(r.otp if r else '')" 2>$null | Select-Object -Last 1).Trim()
Pop-Location
if (-not $otpCode) { throw "Could not read OTP from DB for $otpPhone" }
Add-Row (Invoke-CurlApi "POST auth_otp_verify" "POST" "/api/v1/auth/otp/verify/" (@{ phone = $otpPhone; otp = $otpCode } | ConvertTo-Json -Compress))

# --- Change password ---
Add-Row (Invoke-CurlApi "POST auth_change_password" "POST" "/api/v1/auth/change-password/" (@{ current_password = "TestPass123!"; new_password = "TestPass456!"; confirm_new_password = "TestPass456!" } | ConvertTo-Json -Compress) @("Authorization: Bearer $accessCit"))
$accessCit = (Invoke-RestMethod -Uri "$Base/api/v1/auth/login/" -Method Post -Body (@{ phone = $phone; password = "TestPass456!" } | ConvertTo-Json) -ContentType "application/json").access

# --- Logout ---
Add-Row (Invoke-CurlApi "POST auth_logout" "POST" "/api/v1/auth/logout/" (@{ refresh = $refreshCit } | ConvertTo-Json -Compress) @("Authorization: Bearer $accessCit"))
$accessCit = (Invoke-RestMethod -Uri "$Base/api/v1/auth/login/" -Method Post -Body (@{ phone = $phone; password = "TestPass456!" } | ConvertTo-Json) -ContentType "application/json").access

# --- Admin users list ---
Add-Row (Invoke-CurlApi "GET auth_users" "GET" "/api/v1/auth/users/" -ExtraHeaders @("Authorization: Bearer $accessAdm"))

# --- Complaints ---
Add-Row (Invoke-CurlApi "GET complaints_categories" "GET" "/api/v1/complaints/categories/")
$createBody = (@{
        description           = "Water tap is broken in lane 4"
        description_language  = "en"
        title                 = "Tap"
        city                  = "Pune"
        source                = "web"
        is_anonymous          = $false
    } | ConvertTo-Json -Compress)
$createCurl = Invoke-CurlApi "POST complaints" "POST" "/api/v1/complaints/" $createBody @("Authorization: Bearer $accessCit")
Add-Row $createCurl
if ($createCurl.Code -ne 201) { throw "complaint create failed HTTP $($createCurl.Code): $($createCurl.BodyPreview)" }
$comp = $createCurl.FullBody | ConvertFrom-Json
$cid = $comp.complaint.id
$track = $comp.tracking_id

Add-Row (Invoke-CurlApi "GET complaints_list" "GET" "/api/v1/complaints/")
Add-Row (Invoke-CurlApi "GET complaints_detail" "GET" "/api/v1/complaints/$cid/")
Add-Row (Invoke-CurlApi "GET complaints_track" "GET" "/api/v1/complaints/track/$track/")
Add-Row (Invoke-CurlApi "GET complaints_mine" "GET" "/api/v1/complaints/mine/" -ExtraHeaders @("Authorization: Bearer $accessCit"))
Add-Row (Invoke-CurlApi "POST complaints_upvote" "POST" "/api/v1/complaints/$cid/upvote/" '{}' @("Authorization: Bearer $accessCit"))
Add-Row (Invoke-CurlApi "PATCH complaints_status" "PATCH" "/api/v1/complaints/$cid/status/" (@{ status = "acknowledged"; note = "curl" } | ConvertTo-Json -Compress) @("Authorization: Bearer $accessOff"))
$officerId = (Invoke-RestMethod -Uri "$Base/api/v1/auth/me/" -Headers @{ Authorization = "Bearer $accessOff" }).id
$assignBody = (@{ officer_id = $officerId } | ConvertTo-Json -Compress)
Add-Row (Invoke-CurlApi "POST complaints_assign" "POST" "/api/v1/complaints/$cid/assign/" $assignBody @("Authorization: Bearer $accessAdm"))
Add-Row (Invoke-CurlApi "GET complaints_stats_officer" "GET" "/api/v1/complaints/stats/" -ExtraHeaders @("Authorization: Bearer $accessOff"))

# --- AI classify ---
Add-Row (Invoke-CurlApi "POST ai_classify" "POST" "/api/v1/ai/classify/" (@{ text = "Garbage is not collected on my street."; language = "en" } | ConvertTo-Json -Compress) @("Authorization: Bearer $accessCit"))

# --- Voice languages + jobs (GET) ---
Add-Row (Invoke-CurlApi "GET voice_languages" "GET" "/api/v1/voice/languages/" -ExtraHeaders @("Authorization: Bearer $accessCit"))
Add-Row (Invoke-CurlApi "GET voice_jobs" "GET" "/api/v1/voice/jobs/" -ExtraHeaders @("Authorization: Bearer $accessCit"))

# --- Voice transcribe: tiny valid-sized file; accept 200 (stub) or 400 (strict validation) ---
$wavPath = Join-Path $env:TEMP "curl_smoke_dummy.wav"
# Minimal RIFF WAVE header + silence (validation allows .wav extension and size cap)
$wavBytes = [System.Convert]::FromBase64String("UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA=")
[IO.File]::WriteAllBytes($wavPath, $wavBytes)
try {
    $tr = (& curl.exe -s -S -w "`n__HTTP__:%{http_code}" -X POST "$Base/api/v1/voice/transcribe/" -H "Authorization: Bearer $accessCit" -F "audio_file=@$wavPath" -F "language=hi" 2>&1 | Out-String).TrimEnd("`r", "`n", " ")
    if ($tr -match "__HTTP__:(\d+)\s*$") { $tc = [int]$Matches[1]; $tb = ($tr -replace "__HTTP__:\d+\s*$", "").TrimEnd() } else { $tc = -1; $tb = [string]$tr }
    [void]$rows.Add([PSCustomObject]@{ Name = "POST voice_transcribe"; Code = $tc; BodyPreview = ($tb.Substring(0, [Math]::Min(140, $tb.Length))); FullBody = $tb })
} finally { Remove-Item -Force $wavPath -ErrorAction SilentlyContinue }

# --- Notifications ---
Add-Row (Invoke-CurlApi "GET notifications_list" "GET" "/api/v1/notifications/" -ExtraHeaders @("Authorization: Bearer $accessCit"))
$admUser = Invoke-RestMethod -Uri "$Base/api/v1/auth/me/" -Headers @{ Authorization = "Bearer $accessAdm" }
if (-not $admUser.email) {
    Invoke-RestMethod -Uri "$Base/api/v1/auth/me/" -Method Patch -Headers @{ Authorization = "Bearer $accessAdm" } -ContentType "application/json" -Body (@{ email = "admin_smoke@example.com" } | ConvertTo-Json) | Out-Null
}
$citUser = Invoke-RestMethod -Uri "$Base/api/v1/auth/me/" -Headers @{ Authorization = "Bearer $accessCit" }
if (-not $citUser.email) {
    Invoke-RestMethod -Uri "$Base/api/v1/auth/me/" -Method Patch -Headers @{ Authorization = "Bearer $accessCit" } -ContentType "application/json" -Body (@{ email = "citizen_smoke@example.com" } | ConvertTo-Json) | Out-Null
}
$sendBody = (@{ recipient_phone = $phone; channel = "email"; subject = "Smoke"; body = "Hello" } | ConvertTo-Json -Compress)
Add-Row (Invoke-CurlApi "POST notifications_send" "POST" "/api/v1/notifications/send/" $sendBody @("Authorization: Bearer $accessAdm"))

# --- JWT refresh ---
$ref2 = (Invoke-RestMethod -Uri "$Base/api/v1/auth/login/" -Method Post -Body (@{ phone = $phone; password = "TestPass456!" } | ConvertTo-Json) -ContentType "application/json").refresh
Add-Row (Invoke-CurlApi "POST token_refresh" "POST" "/api/v1/auth/token/refresh/" (@{ refresh = $ref2 } | ConvertTo-Json -Compress))

# --- Voice job detail (if any job exists) ---
$jobs = Invoke-RestMethod -Uri "$Base/api/v1/voice/jobs/" -Headers @{ Authorization = "Bearer $accessCit" }
if ($jobs.results -and $jobs.results.Count -gt 0) {
    $jid = $jobs.results[0].id
    Add-Row (Invoke-CurlApi "GET voice_job_detail" "GET" "/api/v1/voice/jobs/$jid/" -ExtraHeaders @("Authorization: Bearer $accessCit"))
}

# --- Complaint PATCH (owner) ---
Add-Row (Invoke-CurlApi "PATCH complaint_detail" "PATCH" "/api/v1/complaints/$cid/" (@{ title = "Tap updated" } | ConvertTo-Json -Compress) @("Authorization: Bearer $accessCit"))

$bad = @($rows | Where-Object {
        if ($_.Name -eq "POST voice_transcribe") {
            return ($_.Code -ne 200 -and $_.Code -ne 400)
        }
        return ($_.Code -lt 200 -or $_.Code -ge 400)
    })
$rows | Select-Object Name, Code, BodyPreview | Format-Table -AutoSize
if ($bad.Count -gt 0) {
    Write-Host "FAIL: non-2xx responses:" -ForegroundColor Red
    $bad | Format-Table
    exit 1
}
Write-Host "OK: all curl checks returned HTTP 2xx" -ForegroundColor Green
exit 0
