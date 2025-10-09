# Setup script for Windows (PowerShell)
# Autonomous App-Building Platform

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Autonomous App Builder - Setup Script" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Check prerequisites
Write-Host "Checking prerequisites..." -ForegroundColor Yellow

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Python not found. Please install Python 3.11+" -ForegroundColor Red
    exit 1
}

# Check Node.js
try {
    $nodeVersion = node --version 2>&1
    Write-Host "✓ Node.js found: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Node.js not found. Please install Node.js 18+" -ForegroundColor Red
    exit 1
}

# Check Docker
try {
    $dockerVersion = docker --version 2>&1
    Write-Host "✓ Docker found: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "⚠ Docker not found. Install Docker for full functionality" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Setting up project..." -ForegroundColor Yellow

# Create .env file if it doesn't exist
if (-not (Test-Path ".env")) {
    Write-Host "Creating .env file..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "✓ .env file created" -ForegroundColor Green
    Write-Host "⚠ Please edit .env and add your GOOGLE_API_KEY (Gemini)" -ForegroundColor Yellow
} else {
    Write-Host "✓ .env file exists" -ForegroundColor Green
}

# Install Python dependencies
Write-Host ""
Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Python dependencies installed" -ForegroundColor Green
} else {
    Write-Host "✗ Failed to install Python dependencies" -ForegroundColor Red
    exit 1
}

# Install Coordinator dependencies
Write-Host ""
Write-Host "Installing Coordinator dependencies..." -ForegroundColor Yellow
Set-Location coordinator
pip install -r requirements.txt
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Coordinator dependencies installed" -ForegroundColor Green
} else {
    Write-Host "✗ Failed to install Coordinator dependencies" -ForegroundColor Red
    exit 1
}
Set-Location ..

# Create generated directory
if (-not (Test-Path "generated")) {
    New-Item -ItemType Directory -Path "generated" | Out-Null
    Write-Host "✓ Generated apps directory created" -ForegroundColor Green
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Setup Complete!" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Edit .env and add your GOOGLE_API_KEY (Gemini)"
Write-Host "2. Start the platform:"
Write-Host "   - With Docker: docker-compose up"
Write-Host "   - Without Docker: python coordinator/main.py"
Write-Host ""
Write-Host "3. Open the UI: http://localhost:5000/ui"
Write-Host ""
Write-Host "For more information, see README.md" -ForegroundColor Cyan
