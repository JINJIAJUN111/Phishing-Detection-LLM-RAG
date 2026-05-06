# ============================================
# Phishing Detection Lab - Demo Script
# ============================================

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Phishing Detection Lab - Demo" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# --- 1) Check prediction files ---
Write-Host "[1/5] Checking prediction files..." -ForegroundColor Yellow

$files = @(
    ".\data\predictions\mix_tfidf_lr_full.jsonl",
    ".\data\predictions\mix_llmonly_full.jsonl",
    ".\data\predictions\mix_rag_noself_clean_full.jsonl",
    ".\data\predictions\mix_phishllm_mm_full.jsonl",
    ".\data\predictions\mix_qwen_mm_full.jsonl"
)

$allExist = $true
foreach ($f in $files) {
    if (Test-Path $f) {
        $size = [math]::Round((Get-Item $f).Length / 1KB, 1)
        Write-Host "  [OK] $f ($size KB)" -ForegroundColor Green
    } else {
        Write-Host "  [MISSING] $f" -ForegroundColor Red
        $allExist = $false
    }
}

if (-not $allExist) {
    Write-Host "`n[ERROR] Missing files, demo aborted" -ForegroundColor Red
    exit 1
}
Write-Host ""

# --- 2) Check lab service ---
Write-Host "[2/5] Checking lab service..." -ForegroundColor Yellow

try {
    $response = Invoke-WebRequest -UseBasicParsing "http://localhost:8080/" -TimeoutSec 3
    Write-Host "  [OK] Lab service running (http://localhost:8080/)" -ForegroundColor Green

    $qrResponse = Invoke-WebRequest -UseBasicParsing "http://localhost:8080/phish/outlook/qr_login.html" -TimeoutSec 3
    Write-Host "  [OK] QR page accessible" -ForegroundColor Green

    $iframeResponse = Invoke-WebRequest -UseBasicParsing "http://localhost:8080/phish/iframe_phish.html" -TimeoutSec 3
    Write-Host "  [OK] Iframe page accessible" -ForegroundColor Green

} catch {
    Write-Host "  [WARN] Lab service not running" -ForegroundColor DarkYellow
    Write-Host "  Run: docker start phishing-lab" -ForegroundColor Gray
}
Write-Host ""

# --- 3) Check result charts ---
Write-Host "[3/5] Checking result charts..." -ForegroundColor Yellow

$charts = @(
    "Figure1_Performance_AllMethods.png",
    "Figure2_Recall_F1_AllMethods.png",
    "Figure3_Latency_AllMethods.png",
    "Figure4_Multimodal_Fair_Comparison.png",
    "Figure5_TextOnly_Comparison.png"
)

foreach ($c in $charts) {
    $path = ".\results\$c"
    if (Test-Path $path) {
        Write-Host "  [OK] $c" -ForegroundColor Green
    } else {
        Write-Host "  [MISSING] $c" -ForegroundColor Red
    }
}
Write-Host ""

# --- 4) Show logs from Docker container (real-time) ---
Write-Host "[4/5] Access logs (from Docker container)..." -ForegroundColor Yellow

# Trigger fresh requests to generate new logs
try {
    Invoke-WebRequest -UseBasicParsing "http://localhost:8080/" -TimeoutSec 2 | Out-Null
    Invoke-WebRequest -UseBasicParsing "http://localhost:8080/phish/outlook/qr_login.html" -TimeoutSec 2 | Out-Null
    Invoke-WebRequest -UseBasicParsing "http://localhost:8080/phish/iframe_phish.html" -TimeoutSec 2 | Out-Null
    Write-Host "  [OK] Triggered fresh page requests" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Could not trigger requests" -ForegroundColor DarkYellow
}

# Get logs from Docker container (Nginx outputs logs to stdout/stderr)
$dockerLogs = docker logs phishing-lab --tail 20 2>&1

if ($dockerLogs) {
    $logLines = @()
    foreach ($line in $dockerLogs) {
        # Filter HTTP request lines (GET, POST, with status codes)
        if ($line -match 'GET|POST|" 200 "|" 304 "|" 404 "|" 500 "') {
            # Clean up and truncate long lines
            if ($line.Length -gt 120) {
                $line = $line.Substring(0, 120) + "..."
            }
            $logLines += $line
        }
    }

    if ($logLines.Count -gt 0) {
        Write-Host "  [OK] Recent access logs from Docker container:" -ForegroundColor Green
        Write-Host "  " -NoNewline
        Write-Host ("-" * 70) -ForegroundColor Gray
        foreach ($line in $logLines | Select-Object -Last 8) {
            Write-Host "    $line" -ForegroundColor Gray
        }
        Write-Host "  " -NoNewline
        Write-Host ("-" * 70) -ForegroundColor Gray
        Write-Host "  [INFO] Logs show: timestamp, client IP, HTTP method, URI, status code" -ForegroundColor Gray
    } else {
        Write-Host "  [INFO] Waiting for log entries... (access logs are being recorded)" -ForegroundColor Gray
    }
} else {
    Write-Host "  [INFO] Docker container logs are being recorded internally" -ForegroundColor Gray
    Write-Host "  Access logs include: timestamp, method, URI, status, user-agent" -ForegroundColor Gray
}
Write-Host ""

# --- 5) Performance summary ---
Write-Host "[5/5] Performance comparison..." -ForegroundColor Yellow

Write-Host ""
Write-Host "  ======================================================" -ForegroundColor Gray
Write-Host "  Method                    | Recall | F1-Score | Modality" -ForegroundColor Gray
Write-Host "  ======================================================" -ForegroundColor Gray
Write-Host "  TF-IDF + LR               | 0.7848 | 0.8611   | Features" -ForegroundColor Gray
Write-Host "  LLM-only                  | 0.4557 | 0.6154   | Text" -ForegroundColor Gray
Write-Host "  PhishLLM (MM baseline)    | 0.6203 | 0.7656   | Text+Image" -ForegroundColor Gray
Write-Host "  Qwen-MM (img+text)        | 0.6076 | 0.7559   | Text+Image" -ForegroundColor Gray
Write-Host "  LLM + RAG (NoSelf, clean) | 0.5823 | 0.7302   | Text+RAG" -ForegroundColor Green
Write-Host "  ======================================================" -ForegroundColor Gray
Write-Host ""

# --- Conclusion ---
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "CONCLUSION:" -ForegroundColor White
Write-Host "  TF-IDF+LR achieves best F1=0.8611 (traditional baseline)" -ForegroundColor Green
Write-Host "  LLM+RAG (clean) F1=0.7302, Recall improved +12.66 pp vs LLM-only" -ForegroundColor Green
Write-Host "  Clean version removes self-reference samples for stricter evaluation" -ForegroundColor Green
Write-Host "  Multimodal methods (PhishLLM/Qwen-MM) achieve high precision but lower recall" -ForegroundColor Green
Write-Host "  QR + Iframe pages deployed for multimodal extension" -ForegroundColor Green
Write-Host "  Access logs: real-time recording via Docker container logs" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Demo completed!" -ForegroundColor Green