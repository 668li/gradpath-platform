<#
.SYNOPSIS
    GradPath 本地开发环境启动脚本 (PowerShell 版,适用于 Windows)

.DESCRIPTION
    1. 检查 8001 / 3000 / 8080 端口是否被占用
    2. 用 docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d 启动
    3. 等待各服务 health check 通过
    4. 输出访问 URL

.PARAMETER Services
    可选:仅启动指定服务 (如 backend / frontend),默认全部启动

.PARAMETER SkipPortCheck
    跳过端口占用检查

.EXAMPLE
    .\scripts\start-dev.ps1
    .\scripts\start-dev.ps1 -Services backend
    .\scripts\start-dev.ps1 -SkipPortCheck
#>
[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Services,

    [switch]$SkipPortCheck
)

$ErrorActionPreference = "Stop"

# ---- 切换到项目根目录 ----
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot

$ComposeFiles = @("-f", "docker-compose.yml", "-f", "docker-compose.dev.yml")

# ---- 日志辅助 ----
function Write-Log    { param([string]$Msg) Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $Msg" -ForegroundColor Cyan }
function Write-Ok     { param([string]$Msg) Write-Host "[$(Get-Date -Format 'HH:mm:ss')] ✅ $Msg" -ForegroundColor Green }
function Write-Warn2  { param([string]$Msg) Write-Host "[$(Get-Date -Format 'HH:mm:ss')] ⚠️ $Msg" -ForegroundColor Yellow }
function Write-Err2   { param([string]$Msg) Write-Host "[$(Get-Date -Format 'HH:mm:ss')] ❌ $Msg" -ForegroundColor Red }

# ---- 依赖检查 ----
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Err2 "未找到 docker 命令,请先安装 Docker Desktop"
    exit 1
}
$composeVersion = docker compose version 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Err2 "docker compose v2 不可用,请升级 Docker Desktop 或安装 compose 插件"
    exit 1
}

# ---- 端口检查 ----
function Test-PortFree {
    param([int]$Port, [string]$Name)
    $conns = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($conns) {
        $procIds = $conns | Select-Object -ExpandProperty OwningProcess -Unique
        Write-Err2 "端口 $Port ($Name) 已被占用:"
        foreach ($pid in $procIds) {
            $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
            if ($proc) {
                Write-Host "  - PID $pid ($($proc.ProcessName))" -ForegroundColor Yellow
            } else {
                Write-Host "  - PID $pid (系统/已退出)" -ForegroundColor Yellow
            }
        }
        Write-Host "如确认无冲突,可用 -SkipPortCheck 跳过检查" -ForegroundColor Yellow
        return $false
    }
    Write-Ok "端口 $Port ($Name) 空闲"
    return $true
}

if (-not $SkipPortCheck) {
    Write-Log "检查端口占用..."
    if (-not (Test-PortFree 8001 "GradPath backend")) { exit 1 }
    if (-not (Test-PortFree 3000 "GradPath frontend")) { exit 1 }
    if (-not (Test-PortFree 8080 "nginx dev 入口")) { exit 1 }
} else {
    Write-Warn2 "已跳过端口检查"
}

# ---- 启动 docker compose ----
Write-Log "启动 docker compose (dev override)..."
if ($Services) {
    Write-Log "  服务参数: $($Services -join ' ')"
    $upArgs = @("compose") + $ComposeFiles + @("up", "-d") + $Services
} else {
    Write-Log "  服务参数: <全部>"
    $upArgs = @("compose") + $ComposeFiles + @("up", "-d")
}

& docker @upArgs
if ($LASTEXITCODE -ne 0) {
    Write-Err2 "docker compose 启动失败"
    exit 1
}

# ---- 等待 health check ----
function Wait-Healthy {
    param([string]$Service, [int]$Timeout = 180)
    $elapsed = 0
    while ($elapsed -lt $Timeout) {
        $json = docker compose @ComposeFiles ps $Service --format json 2>$null | Out-String
        if ($json) {
            try {
                # docker compose ps --format json 输出可能是多行 JSON 或单行
                $lines = $json -split "`n" | Where-Object { $_.Trim() }
                foreach ($line in $lines) {
                    $obj = $line | ConvertFrom-Json -ErrorAction Stop
                    $health = $obj.Health
                    $state  = $obj.State
                    if ($health -eq "healthy") {
                        Write-Ok "$Service 健康"
                        return $true
                    }
                    if ([string]::IsNullOrEmpty($health) -and $state -eq "running") {
                        Write-Ok "$Service 已运行 (无 healthcheck)"
                        return $true
                    }
                }
            } catch {
                # JSON 解析失败,继续等待
            }
        }
        Start-Sleep -Seconds 5
        $elapsed += 5
        Write-Host ("  ⏳ {0} 等待中 ({1}s/{2}s)" -f $Service, $elapsed, $Timeout) -NoNewline -ForegroundColor DarkGray
        Write-Host "`r" -NoNewline
    }
    Write-Host ""
    Write-Err2 "$Service 健康检查超时 (${Timeout}s),最近日志:"
    docker compose @ComposeFiles logs --tail=30 $Service
    return $false
}

Write-Log "等待服务健康..."
if ($Services) {
    $waitServices = $Services
} else {
    $waitServices = @("backend", "frontend")
}

$failed = $false
foreach ($svc in $waitServices) {
    if (-not (Wait-Healthy $svc 180)) {
        $failed = $true
    }
}

if ($failed) {
    Write-Err2 "部分服务未就绪,请查看日志: docker compose $ComposeFiles logs"
    exit 1
}

# ---- 输出访问地址 ----
Write-Host ""
Write-Ok "GradPath 开发环境已就绪 🎉"
Write-Host ""
Write-Host "📡 访问地址 (均绑定 127.0.0.1,不暴露外网):" -ForegroundColor Cyan
Write-Host "   前端 (Next.js dev):    http://localhost:3000"
Write-Host "   后端 API (FastAPI):    http://localhost:8001/docs"
Write-Host "   nginx 反向代理入口:    http://localhost:8080"
Write-Host "   flower 监控:           http://localhost:5555/flower"
Write-Host "   n8n 工作流:            http://localhost:5678"
Write-Host ""
Write-Host "🔧 常用命令:" -ForegroundColor Cyan
Write-Host "   查看日志:  docker compose $ComposeFiles logs -f"
Write-Host "   停止服务:  docker compose $ComposeFiles down"
Write-Host "   查看状态:  docker compose $ComposeFiles ps"
Write-Host ""
