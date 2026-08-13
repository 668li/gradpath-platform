<#
.SYNOPSIS
  GradPath Schema 同步工具包装脚本 (Windows PowerShell)

.DESCRIPTION
  从项目根目录直接调用 backend 容器内的 scripts/sync_schema.py，
  无需手动 docker exec。容器名可通过环境变量 GRADPATH_BACKEND_CONTAINER 覆盖。

.EXAMPLE
  .\scripts\sync-schema.ps1 -Check            # 检测不一致（默认）
  .\scripts\sync-schema.ps1 -Generate         # 生成 ALTER TABLE SQL
  .\scripts\sync-schema.ps1 -Apply            # 执行 ALTER TABLE ADD COLUMN
  .\scripts\sync-schema.ps1 -DryRun           # 显示会执行什么，但不实际执行
  .\scripts\sync-schema.ps1                    # 默认等同 -Check
#>

[CmdletBinding()]
param(
    [switch]$Check,
    [switch]$Generate,
    [switch]$Apply,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

$Container = if ($env:GRADPATH_BACKEND_CONTAINER) { $env:GRADPATH_BACKEND_CONTAINER } else { 'gradpath-backend-1' }
$ScriptPath = '/app/scripts/sync_schema.py'

# 拼接传给容器的参数（与 Python argparse 互斥组对齐）
$PyArgs = @()
if ($Check)      { $PyArgs += '--check' }
elseif ($Generate) { $PyArgs += '--generate' }
elseif ($Apply)    { $PyArgs += '--apply' }
elseif ($DryRun)   { $PyArgs += '--dry-run' }

Write-Host "[$Container] python $ScriptPath $($PyArgs -join ' ')" -ForegroundColor DarkGray
docker exec $Container python $ScriptPath @PyArgs
exit $LASTEXITCODE
