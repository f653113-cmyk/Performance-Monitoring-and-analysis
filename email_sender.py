"""
Email Sender - Per-Installation Reports
Sends per-site reports via Gmail SMTP
"""

import smtplib
import logging
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
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
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.gmail_address
            msg['To'] = ', '.join(recipients) if isinstance(recipients, list) else recipients
            msg['Subject'] = subject

            # Add HTML body
            msg.attach(MIMEText(html_body, 'html'))

            # Add attachments
            if attachments:
                for attachment_path in attachments:
                    if Path(attachment_path).exists():
                        self._attach_file(msg, attachment_path)

            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.gmail_address, self.gmail_password)
                server.send_message(msg)

            logger.info(f"Email sent to {recipients}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def _attach_file(self, msg, filepath):
        """Attach file to email"""
        try:
            attachment = open(filepath, 'rb')
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename= {Path(filepath).name}')
            msg.attach(part)
            attachment.close()
        except Exception as e:
            logger.error(f"Failed to attach {filepath}: {e}")

    def create_per_site_report_html(self, analysis_data, report_type='full'):
        """Create beautiful Tableau-level HTML email body with per-site sections"""
        sites = analysis_data.get('sites', [])

        # For alerts, check if any site has anomalies
        if report_type == 'alert':
            has_anomalies = any(site.get('anomalies', []) for site in sites)
            if not has_anomalies:
                logger.info("No anomalies detected - skipping alert email")
                return None

        # Count metrics
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
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
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
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                }}
                .header h1 {{
                    font-size: 32px;
                    margin-bottom: 8px;
                    font-weight: 700;
                    letter-spacing: -0.5px;
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
                    letter-spacing: 0.5px;
                }}
                .timestamp {{
                    color: rgba(255,255,255,0.8);
                    font-size: 13px;
                    margin-top: 12px;
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
                .summary-card.alert {{ border-left-color: #e74c3c; }}
                .summary-card.success {{ border-left-color: #27ae60; }}
                .summary-card.warning {{ border-left-color: #f39c12; }}
                .sites-container {{ padding: 30px; background: white; }}
                .site-card {{
                    background: linear-gradient(to bottom, #fafbfc 0%, #f8f9fa 100%);
                    border: 1px solid #e0e6ed;
                    border-radius: 8px;
                    padding: 24px;
                    margin-bottom: 24px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
                    transition: all 0.2s ease;
                }}
                .site-card:hover {{ box-shadow: 0 4px 12px rgba(0,0,0,0.08); }}
                .site-header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 20px;
                    padding-bottom: 16px;
                    border-bottom: 2px solid #e0e6ed;
                }}
                .site-name {{
                    font-size: 18px;
                    font-weight: 700;
                    color: #2c3e50;
                }}
                .site-id {{
                    font-size: 12px;
                    color: #7f8fa3;
                    background: #e8eef5;
                    padding: 4px 12px;
                    border-radius: 12px;
                }}
                .kpi-grid {{
                    display: grid;
                    grid-template-columns: 1fr 1fr 1fr;
                    gap: 16px;
                    margin-bottom: 20px;
             