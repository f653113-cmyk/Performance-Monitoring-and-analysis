# Solar Monitoring System - GitHub Setup Script
# Run this in PowerShell to create and push the repo to GitHub

param(
    [string]$Token = "",
    [string]$Username = "f653113-cmyk",
    [string]$RepoName = "Performance-Monitoring-and-analysis"
)

Write-Host "🌞 Solar Monitoring System - GitHub Setup" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Get current directory
$outputDir = Get-Location
Write-Host "`n📁 Working directory: $outputDir" -ForegroundColor Green

# Check if files exist
if (!(Test-Path "victron_fetcher.py")) {
    Write-Host "Error: Python files not found in current directory" -ForegroundColor Red
    Write-Host "   Make sure you are in the directory with the Python scripts" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Found all required files" -ForegroundColor Green

# Initialize git
Write-Host "`n📦 Initializing Git repository..." -ForegroundColor Cyan
git config --global user.email "automation@solarpv.system"
git config --global user.name "Solar Automation"
git init
git add .
git commit -m "Initial commit: Solar monitoring system"
git branch -M main

# Add remote
$repoUrl = "https://${Username}:${Token}@github.com/${Username}/${RepoName}.git"
git remote add origin $repoUrl

# Push to GitHub
Write-Host "`n🚀 Pushing to GitHub..." -ForegroundColor Cyan
git push -u origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ SUCCESS! Repository created and pushed" -ForegroundColor Green
    Write-Host "`nRepository URL: https://github.com/$Username/$RepoName" -ForegroundColor Green
} else {
    Write-Host "`n⚠️  Push completed with exit code $LASTEXITCODE" -ForegroundColor Yellow
    Write-Host "Check: https://github.com/$Username/$RepoName" -ForegroundColor Yellow
}

Write-Host "`n" -ForegroundColor Cyan
Write-Host "NEXT STEPS:" -ForegroundColor Cyan
Write-Host "==========" -ForegroundColor Cyan
Write-Host "1. Go to: https://github.com/$Username/$RepoName/settings/secrets/actions" -ForegroundColor Yellow
Write-Host "2. Add these secrets:" -ForegroundColor Yellow
Write-Host "   • VRM_API_TOKEN = (your Victron API token)" -ForegroundColor White
Write-Host "   • GMAIL_USER = (your Gmail address)" -ForegroundColor White
Write-Host "   • GMAIL_PASSWORD = (your Gmail app password)" -ForegroundColor White
Write-Host "   • EMAIL_RECIPIENTS = (recipient emails comma-separated)" -ForegroundColor White
Write-Host "`n3. Workflows will run automatically:" -ForegroundColor Yellow
Write-Host "   • Daily at 00:00 UTC" -ForegroundColor White
Write-Host "   • Weekly Monday 08:00 UTC (if anomalies)" -ForegroundColor White
Write-Host "   • Monthly 1st day 09:00 UTC (always)" -ForegroundColor White

Write-Host "`n✅ Setup complete!" -ForegroundColor Green
