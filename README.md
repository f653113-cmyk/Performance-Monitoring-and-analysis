# Solar Monitoring System 🌞

Fully automated solar monitoring system for 20+ Victron VRM installations with per-site dashboards, anomaly detection, and email reporting.

## Features

✅ **Automated Daily Data Fetching** - Pulls data from Victron VRM API every day at 00:00 UTC
✅ **Per-Installation Analysis** - Each site analyzed independently for easy incident tracking
✅ **Professional Dashboards** - Tableau-level interactive HTML dashboards
✅ **Smart Alerts** - Weekly emails only when anomalies detected
✅ **Comprehensive Reports** - Monthly reports always sent
✅ **Zero Manual Work** - GitHub Actions handles all scheduling

## Architecture

```
Victron VRM API
    ↓
victron_fetcher.py (Fetch data daily)
    ↓
analyzer.py (Detect anomalies, calculate KPIs)
    ↓
dashboard_generator.py (Create per-site dashboards)
    ↓
email_sender.py (Send reports)
    ↓
GitHub Actions (Schedule everything)
```

## Files

- **victron_fetcher.py** - Fetches data from Victron VRM API
- **analyzer.py** - Analyzes data, detects anomalies, calculates KPIs
- **dashboard_generator.py** - Generates per-installation HTML dashboards
- **email_sender.py** - Creates and sends email reports
- **monitor_all_sites.py** - Master script for multi-site automation
- **sites.json** - Configuration file with all sites
- **.github/workflows/** - GitHub Actions automation workflows

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables in GitHub Secrets:
   - `VRM_API_TOKEN` - Your Victron VRM API token
   - `GMAIL_USER` - Gmail account for sending reports
   - `GMAIL_PASSWORD` - Gmail app password
   - `EMAIL_RECIPIENTS` - Comma-separated recipient emails

## Workflows

### Daily Sync (00:00 UTC)
- Fetches latest data from all sites
- Analyzes performance
- Generates per-site dashboards

### Weekly Alert (Monday 08:00 UTC)
- Sends alert emails ONLY if anomalies detected
- Includes per-site anomaly details

### Monthly Report (1st of month 09:00 UTC)
- Sends comprehensive report regardless of anomalies
- Archives dashboards for 90 days

## Monitoring Parameters

Each site monitors:
- **MPPT Voltages & Currents** - Solar panel input
- **Inverter Performance** - AC output quality
- **Battery SOC (State of Charge)** - Battery health
- **Power Generation Curves** - Production trends
- **System Efficiency** - PV to AC conversion
- **Load Distribution** - Per-phase analysis

## Alert Thresholds

- 🔴 **Critical**: Efficiency < 75%, Battery SOC < 10%
- 🟠 **Warning**: Efficiency < 85%, Battery SOC < 20%
- 🟢 **Healthy**: All metrics normal

## Quick Start

### Local Testing
```bash
# Fetch data
python victron_fetcher.py YOUR_API_TOKEN

# Analyze
python analyzer.py

# Generate dashboards
python dashboard_generator.py

# Send test email
python email_sender.py data/analysis.json your@gmail.com app_password report_type email@recipient.com
```

### GitHub Actions
Push to GitHub → Workflows run automatically on schedule

## Support

All times are in UTC. Dashboards are stored in `reports/` directory and uploaded as GitHub Actions artifacts.
