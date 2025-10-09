# Start script for Windows (PowerShell)
# Autonomous App-Building Platform

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Starting Autonomous App Builder" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Check if .env exists
if (-not (Test-Path ".env")) {
    Write-Host "✗ .env file not found. Please run setup.ps1 first" -ForegroundColor Red
    exit 1
}

# Check if GOOGLE_API_KEY is set
$envContent = Get-Content ".env" -Raw
if ($envContent -match "GOOGLE_API_KEY=your-google-api-key-here") {
    Write-Host "⚠ Warning: GOOGLE_API_KEY not configured in .env" -ForegroundColor Yellow
    Write-Host "Please edit .env and add your Google Gemini API key" -ForegroundColor Yellow
    Write-Host ""
}

Write-Host "Starting Coordinator..." -ForegroundColor Yellow
Write-Host ""

# Start the coordinator
Set-Location coordinator
python main.py
