<#
.SYNOPSIS
    GradPath 冒烟测试 - PowerShell 版本
.DESCRIPTION
    启动服务后自动验证关键路径,5 秒内反馈。
    验证: 后端健康 / 后端登录 API / 前端根路径重定向 / 前端登录页 / 前端代理 API / 前端 dashboard
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\scripts\smoke_test.ps1
#>

# 配置
$BACKEND_URL    = "http://localhost:8001"
$FRONTEND_URL   = "http://localhost:4001"
$TEST_EMAIL     = "test-185651@example.com"
$TEST_PASSWORD  = "Test12345678!"
$TIMEOUT_SEC    = 10

# 兼容 PowerShell 5.1 / 7+
$ErrorActionPreference = "Continue"
$ProgressPreference    = "SilentlyContinue"  # 关闭进度条,避免 Invoke-WebRequest 卡顿

# 计数器
$script:passCount = 0
$script:failCount = 0
$script:failures  = @()
$script:backendToken  = $null
$script:frontendToken = $null

function Write-Pass([string]$msg) {
    Write-Host "[PASS] $msg" -ForegroundColor Green
    $script:passCount++
}

function Write-Fail([string]$msg, [string]$name = "") {
    Write-Host "[FAIL] $msg" -ForegroundColor Red
    $script:failCount++
    if ($name) { $script:failures += $name } else { $script:failures += $msg }
}

function Write-Info([string]$msg) {
    Write-Host "[INFO] $msg" -ForegroundColor Cyan
}

function Get-Truncated([string]$s, [int]$len = 200) {
    if (-not $s) { return "" }
    if ($s.Length -le $len) { return $s }
    return $s.Substring(0, $len) + "..."
}

# 统一的 HTTP 请求封装,处理重定向与异常
function Invoke-Http {
    param(
        [Parameter(Mandatory=$true)][string]$Method,
        [Parameter(Mandatory=$true)][string]$Url,
        [string]$Body = $null,
        [hashtable]$Headers = @{},
        [int]$MaxRedirection = -1,
        [string]$CookieName = $null,
        [string]$CookieValue = $null
    )
    $params = @{
        Uri               = $Url
        Method            = $Method
        TimeoutSec        = $TIMEOUT_SEC
        UseBasicParsing   = $true
        Headers           = $Headers
        ErrorAction       = "Stop"
    }
    if ($MaxRedirection -ge 0) {
        $params.MaximumRedirection = $MaxRedirection
    }
    if ($Body) {
        $params.ContentType = "application/json"
        $params.Body        = $Body
    }
    # 用 WebSession 管理 cookie,绕过 PS 对 Cookie 头的 reserved 限制
    if ($CookieName -and $CookieValue) {
        $session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
        $cookie = New-Object System.Net.Cookie($CookieName, $CookieValue, "/", "localhost")
        $session.Cookies.Add($cookie)
        $params.WebSession = $session
    }
    try {
        $resp = Invoke-WebRequest @params
        return [pscustomobject]@{
            Status  = [int]$resp.StatusCode
            Body    = $resp.Content
            Headers = $resp.Headers
        }
    } catch {
        # PowerShell 5.1: 4xx/5xx/3xx 重定向超限都会抛异常
        $ex = $_.Exception
        if ($ex -is [System.Net.WebException] -and $ex.Response) {
            $status = [int]$ex.Response.StatusCode
            $bodyStr = ""
            try {
                $stream = $ex.Response.GetResponseStream()
                $reader = New-Object System.IO.StreamReader($stream)
                $bodyStr = $reader.ReadToEnd()
            } catch {}
            $hdrs = @{}
            try {
                foreach ($k in $ex.Response.Headers.AllKeys) {
                    $hdrs[$k] = $ex.Response.Headers[$k]
                }
            } catch {}
            return [pscustomobject]@{
                Status  = $status
                Body    = $bodyStr
                Headers = $hdrs
            }
        }
        elseif ($ex -is [Microsoft.PowerShell.Commands.HttpResponseException]) {
            # PS 7+ 异常
            $status = [int]$ex.Response.StatusCode
            $bodyStr = ""
            try {
                $reader = New-Object System.IO.StreamReader($ex.Response.Content.ReadAsStream())
                $bodyStr = $reader.ReadToEnd()
            } catch {
                try { $bodyStr = $ex.Response.Content.ReadAsStringAsync().Result } catch {}
            }
            $hdrs = @{}
            try { foreach ($k in $ex.Response.Headers.Keys) { $hdrs[$k] = $ex.Response.Headers[$k] } } catch {}
            return [pscustomobject]@{
                Status  = $status
                Body    = $bodyStr
                Headers = $hdrs
            }
        }
        # 其他异常: 网络错误/超时
        throw $_
    }
}

function Get-Header([hashtable]$Headers, [string]$Name) {
    if (-not $Headers) { return $null }
    foreach ($k in $Headers.Keys) {
        if ($k -ieq $Name) { return $Headers[$k] }
    }
    return $null
}

function Get-JsonField([string]$json, [string]$field) {
    try {
        $obj = $json | ConvertFrom-Json
        return $obj.$field
    } catch { return $null }
}

# ========== Test 1: 后端健康 ==========
Write-Info "Test 1/6: 后端健康检查 $BACKEND_URL/health"
try {
    $r = Invoke-Http -Method GET -Url "$BACKEND_URL/health"
    $status = Get-JsonField $r.Body "status"
    $database = Get-JsonField $r.Body "database"
    if ($r.Status -eq 200 -and $status -eq "ok" -and $database -eq "connected") {
        Write-Pass "HTTP 200, status=ok, database=connected"
    } else {
        Write-Fail "期望 200/status=ok/database=connected, 实际 status=$($r.Status), body=$(Get-Truncated $r.Body 200)" "Test 1: 后端健康"
    }
} catch {
    Write-Fail "异常: $($_.Exception.Message)" "Test 1: 后端健康"
}

# ========== Test 2: 后端登录 API ==========
Write-Info "Test 2/6: 后端登录 API POST $BACKEND_URL/api/auth/login"
try {
    $bodyJson = @{ email = $TEST_EMAIL; password = $TEST_PASSWORD } | ConvertTo-Json -Compress
    $r = Invoke-Http -Method POST -Url "$BACKEND_URL/api/auth/login" -Body $bodyJson
    $token = Get-JsonField $r.Body "access_token"
    if ($r.Status -eq 200 -and $token) {
        $preview = $token.Substring(0, [Math]::Min(20, $token.Length))
        Write-Pass "HTTP 200, access_token=$preview..."
        $script:backendToken = $token
    } else {
        Write-Fail "期望 200/含 access_token, 实际 status=$($r.Status), body=$(Get-Truncated $r.Body 200)" "Test 2: 后端登录 API"
    }
} catch {
    Write-Fail "异常: $($_.Exception.Message)" "Test 2: 后端登录 API"
}

# ========== Test 3: 前端根路径 307 重定向 ==========
Write-Info "Test 3/6: 前端根路径 $FRONTEND_URL/ (期望 307 -> /login)"
try {
    $r = Invoke-Http -Method GET -Url "$FRONTEND_URL/" -MaxRedirection 0
    $loc = Get-Header $r.Headers "Location"
    if ($r.Status -eq 307 -and $loc -match "/login") {
        Write-Pass "HTTP 307, Location=$loc"
    } else {
        Write-Fail "期望 307 + Location 含 /login, 实际 status=$($r.Status), Location=$loc" "Test 3: 前端根路径重定向"
    }
} catch {
    Write-Fail "异常: $($_.Exception.Message)" "Test 3: 前端根路径重定向"
}

# ========== Test 4: 前端登录页 ==========
Write-Info "Test 4/6: 前端登录页 $FRONTEND_URL/login (期望 200 + '登录 GradPath')"
try {
    $r = Invoke-Http -Method GET -Url "$FRONTEND_URL/login" -MaxRedirection 0
    if ($r.Status -eq 200 -and $r.Body -match "登录 GradPath") {
        Write-Pass "HTTP 200, HTML 包含 '登录 GradPath'"
    } else {
        Write-Fail "期望 200 + 含 '登录 GradPath', 实际 status=$($r.Status), body 长度=$(($r.Body | Measure-Object -Character).Characters)" "Test 4: 前端登录页"
    }
} catch {
    Write-Fail "异常: $($_.Exception.Message)" "Test 4: 前端登录页"
}

# ========== Test 5: 前端代理 API ==========
Write-Info "Test 5/6: 前端代理 API POST $FRONTEND_URL/api/auth/login"
try {
    $bodyJson = @{ email = $TEST_EMAIL; password = $TEST_PASSWORD } | ConvertTo-Json -Compress
    $r = Invoke-Http -Method POST -Url "$FRONTEND_URL/api/auth/login" -Body $bodyJson
    $token = Get-JsonField $r.Body "access_token"
    if ($r.Status -eq 200 -and $token) {
        $preview = $token.Substring(0, [Math]::Min(20, $token.Length))
        Write-Pass "HTTP 200, access_token=$preview..."
        $script:frontendToken = $token
    } else {
        Write-Fail "期望 200/含 access_token, 实际 status=$($r.Status), body=$(Get-Truncated $r.Body 200)" "Test 5: 前端代理 API"
    }
} catch {
    Write-Fail "异常: $($_.Exception.Message)" "Test 5: 前端代理 API"
}

# ========== Test 6: 前端 dashboard (带 cookie) ==========
Write-Info "Test 6/6: 前端 dashboard $FRONTEND_URL/dashboard (带 cookie, 期望 200 + '看板'/'dashboard')"
$token = $script:frontendToken
if (-not $token) { $token = $script:backendToken }
if (-not $token) {
    Write-Fail "无可用 token (前置登录测试失败)" "Test 6: 前端 dashboard"
} else {
    try {
        $r = Invoke-Http -Method GET -Url "$FRONTEND_URL/dashboard" -MaxRedirection 0 -CookieName "gradpath_token" -CookieValue $token
        $matched = $false
        if ($r.Body -match "看板" -or $r.Body -match "(?i)dashboard") { $matched = $true }
        if ($r.Status -eq 200 -and $matched) {
            Write-Pass "HTTP 200, HTML 包含 '看板'/'dashboard'"
        } else {
            Write-Fail "期望 200 + HTML 含 '看板'/'dashboard', 实际 status=$($r.Status), body 长度=$(($r.Body | Measure-Object -Character).Characters)" "Test 6: 前端 dashboard"
        }
    } catch {
        Write-Fail "异常: $($_.Exception.Message)" "Test 6: 前端 dashboard"
    }
}

# ========== 总结 ==========
$total = $script:passCount + $script:failCount
Write-Host ""
Write-Host "========================================" -ForegroundColor Yellow
if ($script:failCount -eq 0) {
    Write-Host ("Summary: {0}/{1} passed - ALL GREEN" -f $script:passCount, $total) -ForegroundColor Green
} else {
    Write-Host ("Summary: {0}/{1} passed" -f $script:passCount, $total) -ForegroundColor Red
    Write-Host "Failed tests:" -ForegroundColor Red
    foreach ($f in $script:failures) {
        Write-Host "  - $f" -ForegroundColor Red
    }
}
Write-Host "========================================" -ForegroundColor Yellow

if ($script:failCount -gt 0) { exit 1 } else { exit 0 }
