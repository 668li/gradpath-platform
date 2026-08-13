<#
.SYNOPSIS
    GradPath 预启动健康检查脚本 (PowerShell 版)

.DESCRIPTION
    在启动 dev server 前自动检查 5 个维度，防止反复出现的故障：
    1. Next.js .next 缓存完整性 (middleware-manifest.json)
    2. 后端依赖完整性 (tenacity/redis 模块)
    3. 数据库 Schema 与 SQLAlchemy 模型一致性
    4. 后端 API 路由注册完整性 (>= 65 个模块)
    5. 关键 API 端点可用性 (5 个核心端点返回 200)

.PARAMETER Fix
    自动修复可修复的问题（清理 .next 缓存、安装缺失依赖）

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\scripts\preflight-check.ps1
    powershell -ExecutionPolicy Bypass -File .\scripts\preflight-check.ps1 --fix
#>
[CmdletBinding()]
param(
    [switch]$Fix
)

# 兼容命令行直接传入 --fix
if ($args -contains "--fix") { $Fix = $true }

$ErrorActionPreference = "Continue"
$ProgressPreference    = "SilentlyContinue"

# ---- 切换到项目根目录 ----
$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot

# ---- 配置 ----
$BackendContainer = "gradpath-backend-1"
$BackendUrl       = "http://localhost:8001"
$FrontendNextDir  = Join-Path $ProjectRoot "frontend\.next"
$ManifestFile     = Join-Path $FrontendNextDir "server\middleware-manifest.json"
$TestEmail        = $env:GRADPATH_TEST_EMAIL
if (-not $TestEmail) { $TestEmail = "test-185651@example.com" }
$TestPassword     = $env:GRADPATH_TEST_PASSWORD
if (-not $TestPassword) { $TestPassword = "Test12345678!" }
$MinRouteCount    = 65
$NormalRouteCount = 70

# ---- 计数器 ----
$script:checksPassed = 0

# ---- 颜色辅助 ----
function Write-Header([string]$msg) {
    Write-Host ""
    Write-Host $msg -ForegroundColor Cyan
}
function Write-SubPass([string]$msg) {
    Write-Host "  [PASS] $msg" -ForegroundColor Green
}
function Write-SubFail([string]$msg) {
    Write-Host "  [FAIL] $msg" -ForegroundColor Red
}
function Write-SubWarn([string]$msg) {
    Write-Host "  [WARN] $msg" -ForegroundColor Yellow
}
function Write-Fix([string]$msg) {
    Write-Host "  [FIX]  $msg" -ForegroundColor Magenta
}
function Write-Hint([string]$msg) {
    Write-Host "         $msg" -ForegroundColor Yellow
}

# ========== Check 1: .next 缓存完整性 ==========
Write-Header "[Check 1/5] .next 缓存完整性"
$check1Ok = $false
if (Test-Path $ManifestFile) {
    Write-SubPass "middleware-manifest.json 存在，.next 缓存完整"
    $check1Ok = $true
} else {
    if ($Fix) {
        if (Test-Path $FrontendNextDir) {
            try {
                Remove-Item -Recurse -Force $FrontendNextDir -ErrorAction Stop
                Write-Fix "已清理 .next 缓存 (删除 $FrontendNextDir)"
                Write-SubPass ".next 缓存已清理，Next.js 将在启动时重新构建"
                $check1Ok = $true
            } catch {
                Write-SubFail "清理 .next 缓存失败: $($_.Exception.Message)"
                Write-Hint "手动执行: Remove-Item -Recurse -Force frontend\.next"
            }
        } else {
            Write-Fix ".next 目录不存在（首次启动，无需清理）"
            Write-SubPass ".next 缓存不存在，Next.js 将首次构建"
            $check1Ok = $true
        }
    } else {
        Write-SubFail "middleware-manifest.json 缺失: $ManifestFile"
        Write-SubFail "  (可能导致 hydration 失败 / middleware-manifest.json ENOENT)"
        Write-Hint "修复建议: 重新运行本脚本并加 --fix 参数，或手动执行:"
        Write-Hint "  Remove-Item -Recurse -Force frontend\.next"
    }
}
if ($check1Ok) { $script:checksPassed++ }

# ========== Check 2: 后端依赖完整性 ==========
Write-Header "[Check 2/5] 后端依赖完整性 (tenacity/redis)"
$check2Ok = $false
$depOk = $false
$depSource = ""

# 优先检查容器内 Python
try {
    $depOutput = docker exec $BackendContainer python -c "import tenacity, redis; print('OK')" 2>&1
    if ($LASTEXITCODE -eq 0 -and "$depOutput" -match "OK") {
        $depOk = $true
        $depSource = "容器内"
    }
} catch {}

# 回退到本地 Python
if (-not $depOk) {
    try {
        $depOutput = python -c "import tenacity, redis; print('OK')" 2>&1
        if ($LASTEXITCODE -eq 0 -and "$depOutput" -match "OK") {
            $depOk = $true
            $depSource = "本地"
        }
    } catch {}
}

if ($depOk) {
    Write-SubPass "tenacity 和 redis 模块均可正常导入 ($depSource Python)"
    $check2Ok = $true
} else {
    if ($Fix) {
        Write-Fix "尝试在容器内安装缺失依赖 (tenacity redis)..."
        $installOutput = docker exec $BackendContainer pip install tenacity redis 2>&1
        if ($LASTEXITCODE -eq 0) {
            # 复查
            $recheck = docker exec $BackendContainer python -c "import tenacity, redis; print('OK')" 2>&1
            if ($LASTEXITCODE -eq 0 -and "$recheck" -match "OK") {
                Write-SubPass "缺失依赖已安装 (tenacity, redis)"
                $check2Ok = $true
            } else {
                Write-SubFail "依赖安装后仍无法导入"
                Write-Hint "手动执行: docker exec $BackendContainer pip install tenacity redis"
            }
        } else {
            Write-SubFail "pip install 失败 (容器可能未运行)"
            Write-Hint "手动执行: docker exec $BackendContainer pip install tenacity redis"
        }
    } else {
        Write-SubFail "后端缺少 tenacity 或 redis 模块 (导致多个 API 路由静默跳过)"
        Write-Hint "修复建议: 重新运行本脚本并加 --fix 参数，或手动执行:"
        Write-Hint "  docker exec $BackendContainer pip install tenacity redis"
    }
}
if ($check2Ok) { $script:checksPassed++ }

# ========== Check 3: 数据库 Schema 一致性 ==========
Write-Header "[Check 3/5] 数据库 Schema 一致性"
$check3Ok = $false

$schemaScript = @'
from sqlalchemy import inspect
from app.database import engine, Base
import importlib, pkgutil, app.models
for finder, name, is_pkg in pkgutil.iter_modules(app.models.__path__):
    try:
        importlib.import_module(f'app.models.{name}')
    except Exception:
        pass
insp = inspect(engine)
all_missing = []
for table_name in sorted(set(insp.get_table_names()) & set(Base.metadata.tables.keys())):
    db_cols = {c['name'] for c in insp.get_columns(table_name)}
    model_cols = set(Base.metadata.tables[table_name].columns.keys())
    missing = model_cols - db_cols
    if missing:
        print(f'FAIL: {table_name} 缺失列: {sorted(missing)}')
        all_missing.append((table_name, sorted(missing)))
if not all_missing:
    print('OK: schema 一致')
'@

$schemaOutput = ""
try {
    $schemaOutput = docker exec $BackendContainer python -c $schemaScript 2>&1
    if ($LASTEXITCODE -eq 0 -and "$schemaOutput" -match "OK: schema") {
        Write-SubPass "数据库 Schema 与 SQLAlchemy 模型一致"
        $check3Ok = $true
    } elseif ("$schemaOutput" -match "FAIL:") {
        Write-SubFail "数据库 Schema 与模型不一致 (缺失列):"
        $lines = "$schemaOutput" -split "`n" | Where-Object { $_ -match "FAIL:" }
        foreach ($line in $lines) {
            Write-Host "         $line" -ForegroundColor Red
        }
        Write-Hint "修复建议: 运行 schema 同步脚本:"
        Write-Hint "  .\scripts\sync-schema.ps1"
        Write-Hint "  或手动添加缺失列 (参考 backend/migrations/)"
    } else {
        Write-SubFail "Schema 检查执行失败 (容器可能未运行或数据库未连接)"
        $errLine = ("$schemaOutput" -split "`n" | Select-Object -First 3) -join " "
        if ($errLine) { Write-Hint "错误输出: $errLine" }
        Write-Hint "修复建议: 确认后端容器已启动且数据库已连接"
    }
} catch {
    Write-SubFail "Schema 检查异常: $($_.Exception.Message)"
    Write-Hint "修复建议: 确认 docker 已启动且 $BackendContainer 容器正在运行"
}
if ($check3Ok) { $script:checksPassed++ }

# ========== Check 4: API 路由注册完整性 ==========
Write-Header "[Check 4/5] API 路由注册完整性"
$check4Ok = $false
$routeCount = 0
$logSource = ""
try {
    # 优先搜索最近 5 分钟日志
    $logs = docker logs $BackendContainer --since 5m 2>&1
    $matchLines = $logs | Select-String "已自动注册 (\d+) 个 API 路由模块"
    if (-not $matchLines) {
        # 回退: 搜索全部日志 (后端可能启动超过 5 分钟)
        $logs = docker logs $BackendContainer 2>&1
        $matchLines = $logs | Select-String "已自动注册 (\d+) 个 API 路由模块"
        if ($matchLines) { $logSource = "(来自全部日志)" }
    } else {
        $logSource = "(来自最近 5 分钟日志)"
    }
    if ($matchLines) {
        # 取最后一次匹配
        $lastMatch = $matchLines[-1]
        if ($lastMatch.Matches.Count -gt 0) {
            $routeCount = [int]$lastMatch.Matches[0].Groups[1].Value
        }
    }
    if ($routeCount -ge $MinRouteCount) {
        Write-SubPass "已自动注册 $routeCount 个 API 路由模块 $logSource (>= $MinRouteCount 阈值，正常为 $NormalRouteCount)"
        $check4Ok = $true
    } elseif ($routeCount -gt 0) {
        Write-SubFail "API 路由注册数 $routeCount < $MinRouteCount (正常为 $NormalRouteCount) $logSource"
        Write-Hint "可能有 API 模块导入失败导致静默跳过"
        Write-Hint "修复建议: 查看后端日志定位失败模块:"
        Write-Hint "  docker logs $BackendContainer --tail 100"
    } else {
        Write-SubFail "未在后端日志中找到 '已自动注册 N 个 API 路由模块' 记录"
        Write-Hint "可能原因: 后端容器未启动 / 启动失败 / 日志已被清除"
        Write-Hint "修复建议:"
        Write-Hint "  1. 确认后端运行: docker ps"
        Write-Hint "  2. 查看完整日志: docker logs $BackendContainer --tail 100"
    }
} catch {
    Write-SubFail "获取后端日志异常: $($_.Exception.Message)"
    Write-Hint "修复建议: 确认 docker 已启动且 $BackendContainer 容器正在运行"
}
if ($check4Ok) { $script:checksPassed++ }

# ========== Check 5: 关键 API 端点可用性 ==========
Write-Header "[Check 5/5] 关键 API 端点可用性"
$check5Ok = $false

$endpoints = @(
    "/api/notifications",
    "/api/notifications/unread-count",
    "/api/auth/me",
    "/api/decisions",
    "/api/streaks/stats"
)

# 登录获取 token
$token = $null
$loginOk = $false
try {
    $bodyJson = @{ email = $TestEmail; password = $TestPassword } | ConvertTo-Json -Compress
    $loginResp = Invoke-WebRequest -Uri "$BackendUrl/api/auth/login" -Method POST -Body $bodyJson -ContentType "application/json" -TimeoutSec 10 -UseBasicParsing -ErrorAction Stop
    if ($loginResp.StatusCode -eq 200) {
        $loginObj = $loginResp.Content | ConvertFrom-Json
        $token = $loginObj.access_token
        if ($token) { $loginOk = $true }
    }
} catch {}

if (-not $loginOk) {
    Write-SubFail "登录失败，无法获取 token (测试账号: $TestEmail)"
    Write-Hint "跳过端点检查。修复建议:"
    Write-Hint "  1. 确认后端已启动: docker ps"
    Write-Hint "  2. 确认测试账号存在 (可通过环境变量 GRADPATH_TEST_EMAIL / GRADPATH_TEST_PASSWORD 覆盖)"
    Write-Hint "  3. 查看后端日志: docker logs $BackendContainer --tail 50"
} else {
    # 检查每个端点
    $endpointFailCount = 0
    foreach ($ep in $endpoints) {
        try {
            $resp = Invoke-WebRequest -Uri "$BackendUrl$ep" -Method GET -Headers @{ Authorization = "Bearer $token" } -TimeoutSec 10 -UseBasicParsing -ErrorAction Stop
            if ($resp.StatusCode -eq 200) {
                Write-SubPass "$ep -> 200"
            } else {
                Write-SubFail "$ep -> $($resp.StatusCode)"
                $endpointFailCount++
            }
        } catch {
            $status = 0
            if ($_.Exception.Response) {
                try { $status = [int]$_.Exception.Response.StatusCode } catch {}
            }
            if ($status -gt 0) {
                Write-SubFail "$ep -> $status"
            } else {
                Write-SubFail "$ep -> 连接失败 ($($_.Exception.Message))"
            }
            $endpointFailCount++
        }
    }
    if ($endpointFailCount -eq 0) {
        $check5Ok = $true
    } else {
        Write-SubFail "$endpointFailCount/$($endpoints.Count) 端点不可用"
        Write-Hint "修复建议: 检查失败端点的后端日志和依赖"
        Write-Hint "  docker logs $BackendContainer --tail 50"
    }
}
if ($check5Ok) { $script:checksPassed++ }

# ========== 汇总 ==========
$totalChecks = 5
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
if ($script:checksPassed -eq $totalChecks) {
    Write-Host ("汇总: {0}/{1} 检查通过 - ALL GREEN" -f $script:checksPassed, $totalChecks) -ForegroundColor Green
} else {
    Write-Host ("汇总: {0}/{1} 检查通过" -f $script:checksPassed, $totalChecks) -ForegroundColor Red
    Write-Host ""
    Write-Host "失败项请参考上方 [FAIL] 行及修复建议" -ForegroundColor Yellow
    if (-not $Fix) {
        Write-Host "提示: 加 --fix 参数可自动修复部分问题 (清理 .next 缓存、安装缺失依赖)" -ForegroundColor Yellow
    }
}
Write-Host "========================================" -ForegroundColor Cyan

if ($script:checksPassed -lt $totalChecks) { exit 1 } else { exit 0 }
