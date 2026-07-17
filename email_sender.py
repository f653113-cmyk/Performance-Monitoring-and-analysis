"""
Email Sender - Per-Installation Reports
Sends per-site reports via Gmail SMTP
"""

import smtplib
import logging
import json
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmailSender:
    def __init__(self, gmail_address, gmail_password):
        self.gmail_address = gmail_address
        self.gmail_password = gmail_password
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587

    def send_report(self, recipients, subject, html_body, attachments=None):
        """Send email report"""
        if not html_body:
            logger.info("Empty report body - skipping email")
            return False

        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = self.gmail_address
            msg['To'] = ', '.join(recipients) if isinstance(recipients, list) else recipients
            msg['Subject'] = subject

            msg.attach(MIMEText(html_body, 'html'))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.gmail_address, self.gmail_password)
                server.send_message(msg)

            logger.info(f"Email sent to {recipients}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def create_per_site_report_html(self, analysis_data, report_type='full'):
        """Create beautiful HTML email body with per-site sections"""
        sites = analysis_data.get('sites', [])

        if report_type == 'alert':
            has_anomalies = any(site.get('anomalies', []) for site in sites)
            if not has_anomalies:
                logger.info("No anomalies detected - skipping alert email")
                return None

        total_sites = len(sites)
        sites_with_issues = len([s for s in sites if s.get('anomalies', [])])
        total_production = sum(s.get('kpis', {}).get('total_production_kwh', 0) for s in sites)
        avg_efficiency = sum(s.get('kpis', {}).get('avg_efficiency_pct', 0) for s in sites) / total_sites if total_sites > 0 else 0

        report_label = "ALERT REPORT" if report_type == 'alert' else "MONTHLY REPORT"
        report_color = "#e74c3c" if report_type == 'alert' else "#27ae60"

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', sans-serif;
            background: #f5f7fa;
            color: #2c3e50;
            line-height: 1.6;
        }}
        .wrapper {{ max-width: 900px; margin: 0 auto; }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 30px;
            text-align: center;
            border-radius: 8px 8px 0 0;
        }}
        .header h1 {{
            font-size: 32px;
            margin-bottom: 8px;
            font-weight: 700;
        }}
        .report-badge {{
            display: inline-block;
            background: {report_color};
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            margin-top: 8px;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            padding: 30px;
            background: white;
            border-bottom: 1px solid #e0e6ed;
        }}
        .summary-card {{
            padding: 20px;
            background: #f8fafb;
            border-radius: 6px;
            border-left: 4px solid #667eea;
        }}
        .summary-label {{
            font-size: 12px;
            color: #7f8fa3;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-weight: 600;
            margin-bottom: 8px;
        }}
        .summary-value {{
            font-size: 28px;
            font-weight: 700;
            color: #2c3e50;
        }}
        .site-card {{
            background: white;
            border: 1px solid #e0e6ed;
            border-radius: 8px;
            padding: 24px;
            margin: 16px 30px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}
        .site-name {{
            font-size: 18px;
            font-weight: 700;
            color: #2c3e50;
            margin-bottom: 16px;
        }}
        .kpi-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 16px;
            margin-bottom: 20px;
        }}
        .kpi-box {{
            background: white;
            padding: 16px;
            border-radius: 6px;
            border: 1px solid #e0e6ed;
            text-align: center;
        }}
        .kpi-label {{
            font-size: 11px;
            color: #7f8fa3;
            text-transform: uppercase;
            letter-spacing: 0.3px;
            font-weight: 600;
            margin-bottom: 8px;
        }}
        .kpi-value {{
            font-size: 24px;
            font-weight: 700;
            color: #2c3e50;
        }}
        .footer {{
            background: #2c3e50;
            color: white;
            text-align: center;
            padding: 30px;
            font-size: 12px;
            border-radius: 0 0 8px 8px;
        }}
    </style>
</head>
<body>
    <div class="wrapper">
        <div class="header">
            <h1>⚡ Solar Monitoring Report</h1>
            <div class="report-badge">{report_label}</div>
            <p>Generated: {datetime.now().strftime("%B %d, %Y at %H:%M UTC")}</p>
        </div>

        <div class="summary-grid">
            <div class="summary-card">
                <div class="summary-label">Sites with Issues</div>
                <div class="summary-value">{sites_with_issues}</div>
            </div>
            <div class="summary-card">
                <div class="summary-label">Total Production</div>
                <div class="summary-value">{total_production:.1f} kWh</div>
            </div>
            <div class="summary-card">
                <div class="summary-label">Avg Efficiency</div>
                <div class="summary-value">{avg_efficiency:.1f}%</div>
            </div>
            <div class="summary-card">
                <div class="summary-label">Total Sites</div>
                <div class="summary-value">{total_sites}</div>
            </div>
        </div>
"""

        for site in sites:
            site_name = site.get('name', 'Unknown')
            site_id = site.get('site_id', 'Unknown')
            kpis = site.get('kpis', {})
            anomalies = site.get('anomalies', [])

            production = kpis.get('total_production_kwh', 0)
            efficiency = kpis.get('avg_efficiency_pct', 0)
            peak_power = kpis.get('peak_power_w', 0)
            avg_soc = kpis.get('avg_battery_soc_pct', 0)

            html += f"""
        <div class="site-card">
            <div class="site-name">📍 {site_name} (ID: {site_id})</div>

            <div class="kpi-grid">
                <div class="kpi-box">
                    <div class="kpi-label">Production</div>
                    <div class="kpi-value">{production:.1f} kWh</div>
                </div>
                <div class="kpi-box">
                    <div class="kpi-label">Efficiency</div>
                    <div class="kpi-value">{efficiency:.1f}%</div>
                </div>
                <div class="kpi-box">
                    <div class="kpi-label">Peak Power</div>
                    <div class="kpi-value">{peak_power:.0f} W</div>
                </div>
            </div>

            <div class="kpi-grid">
                <div class="kpi-box">
                    <div class="kpi-label">Avg Load</div>
                    <div class="kpi-value">{kpis.get('avg_load_pct', 0):.1f}%</div>
                </div>
                <div class="kpi-box">
                    <div class="kpi-label">Avg Battery SOC</div>
                    <div class="kpi-value">{avg_soc:.1f}%</div>
                </div>
                <div class="kpi-box">
                    <div class="kpi-label">Min Battery SOC</div>
                    <div class="kpi-value">{kpis.get('min_battery_soc_pct', 0):.1f}%</div>
                </div>
            </div>
"""

            if anomalies:
                html += """
            <div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid #e0e6ed;">
                <h3 style="color: #e74c3c; font-size: 14px; margin-bottom: 12px;">⚠️ Detected Issues</h3>
"""
                for anomaly in anomalies:
                    severity = anomaly.get('severity', 'WARNING')
                    atype = anomaly.get('type', 'UNKNOWN')
                    message = anomaly.get('message', 'N/A')
                    timestamp = anomaly.get('timestamp', 'Unknown')
                    html += f"<p style=\"font-size: 13px; color: #2c3e50; margin-bottom: 8px;\"><strong>{atype}:</strong> {message} ({timestamp})</p>"
                html += "</div>"
            else:
                html += """
            <div style="margin-top: 20px; padding: 12px; background: #d5f4e6; border-radius: 4px; color: #27ae60; font-weight: 600;">
                ✅ All Systems Healthy
            </div>
"""

            html += "</div>"

        html += """
        <div class="footer">
            <p>This is an automated report from your Solar Monitoring System.</p>
            <p>All times are in UTC. Data updated daily at 00:00 UTC.</p>
        </div>
    </div>
</body>
</html>
"""

        return html

def main(analysis_file='data/analysis.json', gmail_user=None, gmail_pass=None, recipients=None, report_type='full'):
    """Main execution"""
    if not all([gmail_user, gmail_pass, recipients]):
        logger.error("Missing email credentials or recipients")
        return False

    try:
        with open(analysis_file, 'r') as f:
            analysis = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load analysis file: {e}")
        return False

    sender = EmailSender(gmail_user, gmail_pass)
    html_body = sender.create_per_site_report_html(analysis, report_type=report_type)

    if html_body:
        subject = f"Solar Monitoring {report_type.upper()} Report - {datetime.now().strftime('%Y-%m-%d')}"
        return sender.send_report(recipients, subject, html_body)

    return False

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 3:
        recipients = sys.argv[4:] if len(sys.argv) > 4 else []
        report_type = 'full'
        if len(sys.argv) > 4 and sys.argv[4] in ['alert', 'full']:
            report_type = sys.argv[4]
            recipients = sys.argv[5:]
        main(sys.argv[1], sys.argv[2], sys.argv[3], recipients, report_type)
    else:
        logger.error("Usage: python email_sender.py <analysis_file> <gmail_user> <gmail_pass> [alert|full] <recipient1> [recipient2...]")
