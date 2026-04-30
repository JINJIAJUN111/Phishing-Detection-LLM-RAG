# ============================================
# Phishing Detection Lab - Demo Script
# ============================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "    Phishing Detection Lab - Demo" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# --- 1) Check prediction files ---
Write-Host "[1/4] Checking prediction files..." -ForegroundColor Yellow

$files = @(
    ".\data\predictions\mix_tfidf_lr_full.jsonl",
    ".\data\predictions\mix_llmonly_full.jsonl",
    ".\data\predictions\mix_rag_noself_full.jsonl"
)

$allExist = $true
foreach ($f in $files) {
    if (Test-Path $f) {
        Write-Host "  OK $f" -ForegroundColor Green
    } else {
        Write-Host "  MISSING $f" -ForegroundColor Red
        $allExist = $false
    }
}

if (-not $allExist) {
    Write-Host "`n[ERROR] Missing files, demo aborted" -ForegroundColor Red
    exit 1
}

Write-Host ""

# --- 2) Trigger a POST request to prove lab is alive ---
Write-Host "[2/4] Triggering live POST request..." -ForegroundColor Yellow

try {
    $timestamp = Get-Date -Format "HH:mm:ss"
    $response = Invoke-WebRequest -UseBasicParsing -Method Post "http://localhost:8080/submit" `
        -Body "email=demo%40local.com&password=demo123" -TimeoutSec 3
    Write-Host "  POST /submit SUCCESS! Status: $($response.StatusCode) (Time: $timestamp)" -ForegroundColor Green
} catch {
    Write-Host "  POST /submit FAILED (lab may not be running)" -ForegroundColor DarkYellow
    Write-Host "  Will show existing logs." -ForegroundColor DarkYellow
}
Write-Host ""

# --- 3) Show access logs (focus on recent POST) ---
Write-Host "[3/4] Access logs (showing latest POST requests)..." -ForegroundColor Yellow

$logFile = ".\lab-docker\logs\access.jsonl"
if (Test-Path $logFile) {
    # 优先显示最近3条 POST 请求（证明刚触发的提交已记录）
    Write-Host "  --- Latest POST /submit (proof of live submission) ---" -ForegroundColor Gray
    Get-Content $logFile -Tail 50 | Select-String '"method":"POST"' | Select-Object -Last 3

    Write-Host ""
    Write-Host "  --- Last 8 lines (full log) ---" -ForegroundColor Gray
    Get-Content $logFile -Tail 8
} else {
    Write-Host "  (Log file not found)" -ForegroundColor DarkYellow
}

# 处理 favicon 404 的解释（可选）
Write-Host ""
Write-Host "  Note: favicon.ico 404 is normal (browser auto-request,does not affect experiment)" -ForegroundColor DarkGray

Write-Host ""

# --- 4) Run comparison table ---
Write-Host "[4/4] Performance comparison..." -ForegroundColor Yellow

$pythonPath = ".\.venv\Scripts\python.exe"
$summaryScript = ".\eval\summary_table.py"

if (-not (Test-Path $pythonPath)) {
    Write-Host "  Python not found: $pythonPath" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $summaryScript)) {
    Write-Host "  Script not found: $summaryScript" -ForegroundColor Red
    exit 1
}

& $pythonPath -u $summaryScript

Write-Host ""

# --- 5) Conclusion ---
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "CONCLUSION:" -ForegroundColor White
Write-Host "  Recall: 45.57% -> 81.01% (+35.44 pp)" -ForegroundColor Green
Write-Host "  F1: 0.6154 -> 0.8828" -ForegroundColor Green
Write-Host "  Better than TF-IDF+LR (F1=0.8611)" -ForegroundColor Green
Write-Host "  Latency cost: 1758ms -> 2096ms (+338ms)" -ForegroundColor Gray
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Demo completed!" -ForegroundColor Green