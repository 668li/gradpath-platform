# run-all.ps1 — k6 全量压测编排脚本
# 按顺序执行：smoke → load → stress → spike → ai-endpoint
# 结果输出到 tests/performance/results/{yyyyMMdd-HHmmss}/
#
# 用法：
#   .\run-all.ps1
#   .\run-all.ps1 -BaseUrl http://localhost:8000
#   .\run-all.ps1 -SkipSmoke      # 跳过冒烟
#   .\run-all.ps1 -SkipAi         # 跳过 AI（无 LLM_API_KEY 时）
#   .\run-all.ps1 -Only smoke,load  # 只跑指定脚本

[CmdletBinding()]
param(
    [string]$BaseUrl = $env:BASE_URL,
    [switch]$SkipSmoke,
    [switch]$SkipLoad,
    [switch]$SkipStress,
    [switch]$SkipSpike,
    [switch]$SkipAi,
    [string[]]$Only
)

if (-not $BaseUrl) { $BaseUrl = "http://localhost:8000" }
$ErrorActionPreference = "Continue"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$date = Get-Date -Format "yyyyMMdd-HHmmss"
$resultsDir = Join-Path $scriptDir "results\$date"
New-Item -ItemType Directory -Force -Path $resultsDir | Out-Null

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  k6 全量压测开始" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "BASE_URL : $BaseUrl"
Write-Host "结果目录 : $resultsDir"
Write-Host "开始时间 : $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Host ""

# 检查 k6 是否可用
if (-not (Get-Command k6 -ErrorAction SilentlyContinue)) {
    Write-Host "[FATAL] k6 未安装。请先运行: choco install k6" -ForegroundColor Red
    Write-Host "        或从 https://github.com/grafana/k6/releases 下载" -ForegroundColor Red
    exit 1
}

$k6Version = (k6 version 2>&1 | Select-Object -First 1)
Write-Host "k6 版本 : $k6Version" -ForegroundColor DarkGray
Write-Host ""

# 预检：后端是否可达
Write-Host "[预检] 探测后端 $BaseUrl/health ..." -ForegroundColor DarkYellow
try {
    $healthProbe = Invoke-WebRequest -Uri "$BaseUrl/health" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    Write-Host "[预检] 后端可用 (status=$($healthProbe.StatusCode))" -ForegroundColor Green
} catch {
    Write-Host "[预检] 后端不可达：$($_.Exception.Message)" -ForegroundColor Red
    Write-Host "        请先启动后端：cd backend; uvicorn app.main:app --host 0.0.0.0 --port 8000" -ForegroundColor Yellow
    Write-Host "        仍要继续？(Y/N)" -ForegroundColor Yellow
    $confirm = Read-Host
    if ($confirm -ne 'Y' -and $confirm -ne 'y') {
        Write-Host "已取消。" -ForegroundColor Cyan
        exit 1
    }
}
Write-Host ""

# 脚本清单
$scripts = @(
    @{ Name = "smoke";       File = "smoke.js";           Desc = "冒烟测试 (3 VU, 30s)";         Skip = $SkipSmoke },
    @{ Name = "load";        File = "load.js";            Desc = "负载测试 (50→200 VU, 5m)";     Skip = $SkipLoad },
    @{ Name = "stress";      File = "stress.js";          Desc = "极限压测 (→1000 VU, 11m)";     Skip = $SkipStress },
    @{ Name = "spike";       File = "spike.js";           Desc = "突发流量 (500 VU, 1m40s)";     Skip = $SkipSpike },
    @{ Name = "ai-endpoint"; File = "ai-endpoint.js";     Desc = "AI 端点专项 (20 VU, 2m)";      Skip = $SkipAi }
)

$totalStart = Get-Date
$summary = @()

foreach ($s in $scripts) {
    # -Only 过滤
    if ($Only -and $Only.Count -gt 0 -and ($Only -notcontains $s.Name)) {
        Write-Host "[$($s.Name)] 跳过（-Only 未包含）" -ForegroundColor DarkGray
        continue
    }

    # -Skip 开关
    if ($s.Skip) {
        Write-Host "[$($s.Name)] 跳过（-Skip$($s.Name) 开关）" -ForegroundColor DarkGray
        continue
    }

    $scriptPath = Join-Path $scriptDir $s.File
    $jsonOut = Join-Path $resultsDir "$($s.Name).json"
    $logOut = Join-Path $resultsDir "$($s.Name).log"

    Write-Host "============================================" -ForegroundColor Yellow
    Write-Host "  [$($s.Name)] $($s.Desc)" -ForegroundColor Yellow
    Write-Host "============================================" -ForegroundColor Yellow
    Write-Host "脚本 : $scriptPath"
    Write-Host "日志 : $logOut"
    Write-Host "开始 : $(Get-Date -Format 'HH:mm:ss')"

    if (-not (Test-Path $scriptPath)) {
        Write-Host "  [ERROR] 脚本不存在，跳过" -ForegroundColor Red
        $summary += @{ Name = $s.Name; ExitCode = -1; Duration = "N/A" }
        continue
    }

    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    k6 run $scriptPath --out json=$jsonOut -e BASE_URL=$BaseUrl 2>&1 | Tee-Object -FilePath $logOut
    $exitCode = $LASTEXITCODE
    $sw.Stop()

    $duration = "{0:mm\:ss}" -f $sw.Elapsed
    $status = if ($exitCode -eq 0) { "PASS (阈值全通过)" } elseif ($exitCode -eq 1) { "WARN (有阈值失败)" } else { "FAIL (exit=$exitCode)" }
    $color = if ($exitCode -eq 0) { "Green" } elseif ($exitCode -eq 1) { "Yellow" } else { "Red" }

    Write-Host "[$($s.Name)] $status | 耗时 $duration" -ForegroundColor $color
    $summary += @{ Name = $s.Name; ExitCode = $exitCode; Duration = $duration }

    # 脚本间间隔 10s，让后端恢复
    if ($s.Name -ne "ai-endpoint") {
        Write-Host "  间隔 10s 让后端恢复..." -ForegroundColor DarkGray
        Start-Sleep -Seconds 10
    }
    Write-Host ""
}

$totalElapsed = "{0:hh\:mm\:ss}" -f ((Get-Date) - $totalStart)

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  全量压测结束" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "总耗时 : $totalElapsed"
Write-Host "结果目录 : $resultsDir"
Write-Host ""
Write-Host "汇总：" -ForegroundColor White
foreach ($r in $summary) {
    $status = if ($r.ExitCode -eq 0) { "PASS" } elseif ($r.ExitCode -eq 1) { "WARN" } else { "FAIL" }
    $color = if ($r.ExitCode -eq 0) { "Green" } elseif ($r.ExitCode -eq 1) { "Yellow" } else { "Red" }
    Write-Host ("  {0,-12} {1,-6} {2,-8} exit={3}" -f $r.Name, $status, $r.Duration, $r.ExitCode) -ForegroundColor $color
}
Write-Host ""
Write-Host "下一步：查看 $resultsDir 下的 .log 文件，或用 jq 分析 .json：" -ForegroundColor DarkGray
Write-Host "  Get-Content $resultsDir\smoke.log" -ForegroundColor DarkGray
Write-Host '  jq -s ''map(select(.type=="Point")) | group_by(.metric) | map({metric: .[0].metric, count: length})'' smoke.json' -ForegroundColor DarkGray
