param(
    [string]$Name = "金嘉俊",
    [string]$StudentId = "B23080229"
)


Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "=== 课程设计打包脚本 ===" -ForegroundColor Cyan
Write-Host "姓名: $Name" -ForegroundColor Yellow
Write-Host "学号: $StudentId" -ForegroundColor Yellow
Write-Host ""

$submitDir = "${StudentId}_${Name}_课程设计"
$zipFile = "$submitDir.zip"

Write-Host "[1/9] 清理旧文件..." -ForegroundColor Yellow
if (Test-Path $submitDir) { Remove-Item $submitDir -Recurse -Force }
if (Test-Path $zipFile) { Remove-Item $zipFile -Force }
Write-Host ""

Write-Host "[2/9] 创建目录结构..." -ForegroundColor Yellow
$dirs = @(
    "llm", "eval", "tools",
    "data\evidence", "data\predictions",
    "lab-docker", "results", "report"
)
foreach ($d in $dirs) {
    New-Item -ItemType Directory -Path "$submitDir\$d" -Force | Out-Null
}
Write-Host ""

Write-Host "[3/9] 复制源代码..." -ForegroundColor Yellow
$srcDirs = @("llm", "eval", "tools")
foreach ($dir in $srcDirs) {
    if (!(Test-Path $dir)) {
        throw "[ERROR] 源目录不存在: $dir"
    }
    Copy-Item -Path $dir -Destination "$submitDir\" -Recurse -Force
    Write-Host "  [OK] $dir/"
}
Write-Host ""

Write-Host "[4/9] 复制数据文件..." -ForegroundColor Yellow
$evidenceFile = "data\evidence\combined_evidence_mm.csv"
if (!(Test-Path $evidenceFile)) {
    throw "[ERROR] 证据文件不存在: $evidenceFile"
}
Copy-Item $evidenceFile "$submitDir\data\evidence\" -Force
Write-Host "  [OK] combined_evidence_mm.csv"

$coreFiles = @(
    "mix_tfidf_lr_full.jsonl",
    "mix_llmonly_full.jsonl",
    "mix_rag_noself_full.jsonl",
    "mix_phishllm_mm_full.jsonl",
    "mix_qwen_mm_full.jsonl"
)

foreach ($f in $coreFiles) {
    $src = "data\predictions\$f"
    if (!(Test-Path $src)) {
        throw "[ERROR] 预测文件不存在: $src"
    }
    Copy-Item $src "$submitDir\data\predictions\" -Force
    Write-Host "  [OK] $f"
}
Write-Host ""

Write-Host "[5/9] 复制靶场文件..." -ForegroundColor Yellow
if (Test-Path "lab-docker") {
    Copy-Item -Path "lab-docker" -Destination "$submitDir\" -Recurse -Force
    Write-Host "  [OK] lab-docker/"
} else {
    Write-Host "  [WARN] lab-docker/ 不存在" -ForegroundColor DarkYellow
}
Write-Host ""

Write-Host "[6/9] 复制结果文件..." -ForegroundColor Yellow
$requiredResults = @(
    "summary_table.txt",
    "Figure1_Performance_AllMethods.png",
    "Figure2_Recall_F1_AllMethods.png",
    "Figure3_Latency_AllMethods.png",
    "Figure4_Multimodal_Fair_Comparison.png"
)

foreach ($res in $requiredResults) {
    $src = "results\$res"
    if (Test-Path $src) {
        Copy-Item $src "$submitDir\results\" -Force
        Write-Host "  [OK] $res"
    } else {
        Write-Host "  [WARN] 结果文件不存在: $src" -ForegroundColor DarkYellow
    }
}
Write-Host ""

Write-Host "[7/9] 复制脚本和文档..." -ForegroundColor Yellow
$requiredScripts = @(
    "demo.ps1",
    "requirements.txt",
    "README.md"
)

foreach ($s in $requiredScripts) {
    if (!(Test-Path $s)) {
        throw "[ERROR] 脚本文件不存在: $s"
    }
    Copy-Item $s "$submitDir\" -Force
    Write-Host "  [OK] $s"
}
Write-Host ""

Write-Host "[8/9] 清理临时文件..." -ForegroundColor Yellow
Get-ChildItem $submitDir -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem $submitDir -Recurse -File -Include "*.pyc", "*.pyo" | Remove-Item -Force -ErrorAction SilentlyContinue
Write-Host "  清理完成" -ForegroundColor Green
Write-Host ""

Write-Host "[9/9] 开始压缩..." -ForegroundColor Yellow
Compress-Archive -Path $submitDir -DestinationPath $zipFile -Force

$zipSize = [math]::Round((Get-Item $zipFile).Length / 1MB, 2)
Write-Host ""
Write-Host "打包完成：$zipFile ($zipSize MB)" -ForegroundColor Green
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "提交自检清单" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$checkItems = @(
    "$submitDir\requirements.txt",
    "$submitDir\README.md",
    "$submitDir\lab-docker\site\phish\outlook\qr_login.html",
    "$submitDir\lab-docker\site\phish\iframe_phish.html"
)

$allOk = $true
foreach ($item in $checkItems) {
    if (Test-Path $item) {
        Write-Host "  [OK] $item" -ForegroundColor Green
    } else {
        Write-Host "  [MISSING] $item" -ForegroundColor Red
        $allOk = $false
    }
}

Write-Host ""
Write-Host "注意：请手动将课程设计报告放入 $submitDir\report\ 目录" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
if ($allOk) {
    Write-Host "自检通过！" -ForegroundColor Green
} else {
    Write-Host "自检失败，请检查缺失文件" -ForegroundColor Red
}
Write-Host "========================================" -ForegroundColor Cyan
