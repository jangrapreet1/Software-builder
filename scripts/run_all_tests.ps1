param(
    [switch]$E2E = $false,
    [switch]$Fix = $false,
    [switch]$Fake = $false,
    [switch]$NoLint = $false
)

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "  Run Lint + Unit/API Tests (+E2E optional)" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan

# Ensure Python exists
try {
    $py = python --version 2>&1
    Write-Host "[OK] Python: $py" -ForegroundColor Green
} catch {
    Write-Host "[FAIL] Python not found" -ForegroundColor Red
    exit 1
}

# Linting
if (-not $NoLint) {
    if ($Fix) {
        Write-Host "Running black (format)" -ForegroundColor Yellow
        python -m black .
        if ($LASTEXITCODE -ne 0) { Write-Host "[FAIL] black failed" -ForegroundColor Red; exit 1 }

        Write-Host "Running isort (format)" -ForegroundColor Yellow
        python -m isort .
        if ($LASTEXITCODE -ne 0) { Write-Host "[FAIL] isort failed" -ForegroundColor Red; exit 1 }
    } else {
        Write-Host "Running black --check" -ForegroundColor Yellow
        python -m black --check .
        if ($LASTEXITCODE -ne 0) { Write-Host "[FAIL] black check failed" -ForegroundColor Red; exit 1 }

        Write-Host "Running isort --check-only" -ForegroundColor Yellow
        python -m isort --check-only .
        if ($LASTEXITCODE -ne 0) { Write-Host "[FAIL] isort check failed" -ForegroundColor Red; exit 1 }
    }
} else {
    Write-Host "Skipping lint checks (NoLint)" -ForegroundColor Yellow
}

# Unit/API tests
Write-Host "Running pytest" -ForegroundColor Yellow
python -m pytest -q
if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] Unit/API tests failed" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Unit/API tests passed" -ForegroundColor Green

# Optional E2E suite
if ($E2E) {
    Write-Host "--- E2E suite requested ---" -ForegroundColor Yellow

    if (-not $Fake) {
        if (-not (Test-Path ".env")) {
            Write-Host "[WARN] .env not found, E2E requires GOOGLE_API_KEY. Skipping E2E." -ForegroundColor Yellow
            exit 0
        }

        $envContent = Get-Content ".env" -Raw
        if ($envContent -match "GOOGLE_API_KEY=your-google-api-key-here") {
            Write-Host "[WARN] GOOGLE_API_KEY not configured, skipping E2E" -ForegroundColor Yellow
            exit 0
        }
    }

    # Check if coordinator already running
    $healthy = $false
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:5000/health" -UseBasicParsing -TimeoutSec 2
        if ($resp.StatusCode -eq 200) { $healthy = $true }
    } catch { $healthy = $false }

    $serverStarted = $false
    $serverProc = $null

    if (-not $healthy) {
        Write-Host "Starting coordinator for E2E..." -ForegroundColor Yellow
        if ($Fake) {
            Write-Host "Using fake workflow (USE_FAKE_WORKFLOW=1)" -ForegroundColor Yellow
            $env:USE_FAKE_WORKFLOW = "1"
            if (-not $env:GOOGLE_API_KEY) { $env:GOOGLE_API_KEY = "dummy-local-key" }
        }
        $logDir = Join-Path $PSScriptRoot "..\coordinator"
        $outLog = Join-Path $logDir "uvicorn_out.log"
        $errLog = Join-Path $logDir "uvicorn_err.log"
        if (Test-Path $outLog) { Remove-Item $outLog -Force -ErrorAction SilentlyContinue }
        if (Test-Path $errLog) { Remove-Item $errLog -Force -ErrorAction SilentlyContinue }
        $serverProc = Start-Process -FilePath "python" -ArgumentList "-m uvicorn main:app --host 127.0.0.1 --port 5000" -WorkingDirectory "coordinator" -PassThru -WindowStyle Hidden -RedirectStandardOutput $outLog -RedirectStandardError $errLog

        # Wait for health
        for ($i = 0; $i -lt 60; $i++) {
            Start-Sleep -Seconds 2
            try {
                $resp = Invoke-WebRequest -Uri "http://127.0.0.1:5000/health" -UseBasicParsing -TimeoutSec 2
                if ($resp.StatusCode -eq 200) { $healthy = $true; break }
            } catch { }
        }
        if (-not $healthy) {
            Write-Host "[FAIL] Coordinator did not become healthy in time" -ForegroundColor Red
            Write-Host "--- Server stdout (last 100 lines) ---" -ForegroundColor Yellow
            if (Test-Path $outLog) { Get-Content $outLog -Tail 100 }
            Write-Host "--- Server stderr (last 100 lines) ---" -ForegroundColor Yellow
            if (Test-Path $errLog) { Get-Content $errLog -Tail 100 }
            if ($serverProc) { Stop-Process -Id $serverProc.Id -Force -ErrorAction SilentlyContinue }
            exit 1
        }
        $serverStarted = $true
        Write-Host "[OK] Coordinator healthy" -ForegroundColor Green
    } else {
        Write-Host "[OK] Coordinator already running" -ForegroundColor Green
    }

    # Run E2E tests
    Write-Host "Running comprehensive_test.py" -ForegroundColor Yellow
    python comprehensive_test.py
    $e2eCode = $LASTEXITCODE

    if ($serverStarted -and $serverProc) {
        Write-Host "Stopping coordinator" -ForegroundColor Yellow
        Stop-Process -Id $serverProc.Id -Force -ErrorAction SilentlyContinue
    }

    if ($e2eCode -ne 0) {
        Write-Host "[FAIL] E2E suite failed" -ForegroundColor Red
        exit $e2eCode
    }
    Write-Host "[OK] E2E suite passed" -ForegroundColor Green
}

exit 0
