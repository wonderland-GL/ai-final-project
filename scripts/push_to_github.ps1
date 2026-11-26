#Requires -Version 5.1
<#
.SYNOPSIS
    把 physics-lab-tool 提交并推送到 GitHub。

.DESCRIPTION
    只做本地 Git 操作，不保存、不读取任何 Token。
    认证交给 Git Credential Manager 或 SSH key。

.EXAMPLE
    .\scripts\push_to_github.ps1
    .\scripts\push_to_github.ps1 -RepoUrl "git@github.com:yourname/physics-lab-tool.git"
#>
[CmdletBinding()]
param(
    [string]$RepoUrl = "",
    [string]$CommitMessage = "feat: 实验数据台 v0.1"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Fail($message) {
    Write-Host ""
    Write-Host "✗ $message" -ForegroundColor Red
    exit 1
}

Write-Host "项目目录：$root" -ForegroundColor Cyan

# 1. 检查 git
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Fail "没有检测到 git。请先安装 Git for Windows：https://git-scm.com/download/win"
}

# 2. 拒绝把 .env 带进仓库
if (Test-Path ".env") {
    Fail "发现 .env 文件。请先把它移出项目目录（或改名），再运行本脚本。"
}

# 3. 密钥扫描
$python = $null
if (Get-Command python -ErrorAction SilentlyContinue) { $python = "python" }
elseif (Get-Command py -ErrorAction SilentlyContinue) { $python = "py" }

if ($python) {
    Write-Host "`n[1/5] 扫描疑似密钥..." -ForegroundColor Cyan
    & $python "scripts/check_secrets.py"
    if ($LASTEXITCODE -ne 0) { Fail "密钥扫描未通过，先处理上面的文件。" }
} else {
    Write-Host "`n[1/5] 未找到 python，跳过密钥扫描（风险自负）" -ForegroundColor Yellow
}

# 4. 初始化仓库
if (-not (Test-Path ".git")) {
    Write-Host "[2/5] 初始化 Git 仓库..." -ForegroundColor Cyan
    git init -b main | Out-Null
} else {
    Write-Host "[2/5] 已存在 Git 仓库，跳过 init" -ForegroundColor Cyan
}

# 5. 暂存并检查
Write-Host "[3/5] 暂存文件并检查..." -ForegroundColor Cyan
git add .

$staged = @(git diff --cached --name-only)
if ($staged.Count -eq 0) {
    Write-Host "没有需要提交的改动。" -ForegroundColor Yellow
} else {
    $bad = $staged | Where-Object {
        ($_ -match '^\.env$') -or
        (($_ -match '^(data|reports|models|knowledge)/') -and ($_ -notmatch '\.gitkeep$'))
    }
    if ($bad) {
        git reset | Out-Null
        Write-Host "`n以下文件不应该提交：" -ForegroundColor Red
        $bad | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
        Fail "已取消暂存。请检查 .gitignore 或把这些文件移走。"
    }

    Write-Host "`n将要提交的文件（前 40 个）：" -ForegroundColor Cyan
    $staged | Select-Object -First 40 | ForEach-Object { Write-Host "  $_" }

    Write-Host "[4/5] 提交..." -ForegroundColor Cyan
    git commit -m $CommitMessage | Out-Null
}

# 6. 配置远程并推送
$remotes = @(git remote 2>$null)
$hasRemote = $remotes -contains "origin"

if (-not $hasRemote) {
    if (-not $RepoUrl) {
        Write-Host ""
        Write-Host "还没有配置远程仓库。" -ForegroundColor Yellow
        Write-Host "请先在 GitHub 新建一个 Private 仓库，然后粘贴地址。" -ForegroundColor Yellow
        $RepoUrl = Read-Host "仓库地址（git@github.com:用户名/仓库.git 或 https://github.com/用户名/仓库.git）"
    }
    if (-not $RepoUrl) { Fail "没有提供仓库地址。" }
    git remote add origin $RepoUrl
}

Write-Host "[5/5] 推送到 GitHub..." -ForegroundColor Cyan
git push -u origin main
if ($LASTEXITCODE -ne 0) {
    Fail "推送失败。请检查网络、仓库地址和登录状态（不要在这里输入密码或 Token，交给弹窗）。"
}

Write-Host ""
Write-Host "✓ 完成。打开仓库页面确认：没有 .env、data/、reports/。" -ForegroundColor Green
