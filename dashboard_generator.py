"""
Dashboard Generator - Per-Installation Dashboards
Creates individual dashboards for each Victron installation
"""

import json
import logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DashboardGenerator:
    def __init__(self):
        self.site_dashboard_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Solar Monitoring Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', sans-serif;
            background: #f5f7fa;
            padding: 30px 20px;
            min-height: 100vh;
            color: #2c3e50;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 50px 40px;
            border-radius: 12px;
            margin-bottom: 40px;
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.2);
            text-align: center;
        }}
        .header h1 {{
            color: white;
            margin-bottom: 12px;
            font-size: 2.8em;
            font-weight: 700;
            letter-spacing: -1px;
        }}
        .site-info {{
            color: rgba(255,255,255,0.9);
            font-size: 1.2em;
            margin-bottom: 12px;
            font-weight: 500;
        }}
        .site-info strong {{
            font-weight: 700;
            color: #fff;
        }}
        .header p {{
            color: rgba(255,255,255,0.8);
            font-size: 0.95em;
            margin-top: 15px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        .card {{
            background: white;
            border-radius: 10px;
            padding: 28px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            border-left: 5px solid #667eea;
            transition: all 0.3s ease;
        }}
        .card:hover {{
            box-shadow: 0 8px 24px rgba(0,0,0,0.12);
            transform: translateY(-2px);
        }}
        .card.critical {{
            border-left-color: #e74c3c;
        }}
        .card.warning {{
            border-left-color: #f39c12;
        }}
        .card.success {{
            border-left-color: #27ae60;
        }}
        .card h3 {{
            color: #7f8fa3;
            margin-bottom: 14px;
            font-size: 0.8em;
            text-transform: uppercase;
            letter-spacing: 1.2px;
            font-weight: 700;
        }}
        .card .value {{
            font-size: 2.8em;
            font-weight: 700;
            color: #667eea;
            line-height: 1;
        }}
        .card.critical .value {{
            color: #e74c3c;
        }}
        .card.warning .value {{
            color: #f39c12;
        }}
        .card.success .value {{
            color: #27ae60;
        }}
        .card .unit {{
            font-size: 0.45em;
            color: #95a5a6;
            font-weight: 500;
            margin-left: 6px;
        }}
        .details-section {{
            background: white;
            border-radius: 10px;
            padding: 32px;
            margin-bottom: 40px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}
        .details-section h2 {{
            color: #2c3e50;
            margin-bottom: 24px;
            font-size: 1.4em;
            font-weight: 700;
            letter-spacing: -0.5px;
        }}
        .metrics-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        .metrics-table td {{
            padding: 14px 0;
            border-bottom: 1px solid #e8ecf1;
        }}
        .metrics-table tr:last-child td {{
            border-bottom: none;
        }}
        .metrics-table .label {{
            color: #7f8fa3;
            font-weight: 500;
            width: 50%;
            font-size: 13px;
        }}
        .metrics-table .value {{
            color: #2c3e50;
            font-weight: 700;
            text-align: right;
            font-size: 15px;
        }}
        .anomalies {{
            background: white;
            border-radius: 10px;
            padding: 32px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            margin-bottom: 30px;
        }}
        .anomalies h2 {{
            color: #e74c3c;
            margin-bottom: 24px;
            font-size: 1.3em;
            font-weight: 700;
            letter-spacing: -0.5px;
        }}
        .anomaly-item {{
            padding: 16px;
            margin-bottom: 12px;
            border-radius: 6px;
            border-left: 4px solid #999;
            background: #f8f9fa;
        }}
        .anomaly-item.critical {{
            background: #fdeef0;
            border-left-color: #e74c3c;
        }}
        .anomaly-item.warning {{
            background: #fef9f0;
            border-left-color: #f39c12;
        }}
        .anomaly-type {{
            font-weight: 700;
            margin-bottom: 6px;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.3px;
            color: #e74c3c;
        }}
        .anomaly-item.warning .anomaly-type {{ color: #f39c12; }}
        .anomaly-message {{
            color: #2c3e50;
            margin-bottom: 6px;
            font-size: 13px;
            font-weight: 500;
        }}
        .anomaly-timestamp {{
            color: #95a5a6;
            font-size: 11px;
        }}
        .footer {{
            text-align: center;
            color: #95a5a6;
            margin-top: 40px;
            padding: 30px 20px;
            font-size: 12px;
            border-top: 1px solid #e8ecf1;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚡ Solar Monitoring Dashboard</h1>
            <div class="site-info">Installation: <strong>{site_name}</strong> (ID: {site_id})</div>
            <p>Generated: {timestamp}</p>
        </div>

        <!-- KPI Cards -->
        <div class="grid">
            {kpi_cards}
        </div>

        <!-- Detailed Metrics -->
        <div class="details-section">
            <h2>System Performance Metrics</h2>
            <table class="metrics-table">
                {metrics_rows}
            </table>
        </div>

        <!-- Anomalies -->
        {anomalies_section}

        <div class="footer">
            <p>Automated Solar Monitoring System | All times in UTC</p>
        </div>
    </div>

</body>
</html>
        """

    def generate_dashboards(self, analysis_data):
        """Generate per-site dashboards"""
        logger.info("Generating per-site dashboards...")

        Path('reports').mkdir(exist_ok=True)
        dashboard_files = []

        sites = analysis_data.get('sites', [])

        for site in sites:
            site_name = site.get('name', 'Unknown')
            site_id = site.get('site_id', 'Unknown')
            kpis = site.get('kpis', {})
            anomalies = site.get('anomalies', [])

            logger.info(f"Generating dashboard for {site_name} (ID: {site_id})")

            # Generate KPI cards
            kpi_cards = self._generate_kpi_cards(kpis, anomalies)

            # Generate metrics table
            metrics_rows = self._generate_metrics_rows(kpis)

            # Generate anomalies section
            anomalies_section = self._generate_anomalies_section(anomalies)

            # Generate HTML
            html = self.site_dashboard_template.format(
                site_name=site_name,
                site_id=site_id,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
                kpi_cards=kpi_cards,
                metrics_rows=metrics_rows,
                anomalies_section=anomalies_section
            )

            # Save dashboard
            dashboard_path = f'reports/dashboard_site_{site_id}.html'
            with open(dashboard_path, 'w') as f:
                f.write(html)

            logger.info(f"Dashboard saved to {dashboard_path}")
            dashboard_files.append(dashboard_path)

        return dashboard_files

    def _generate_kpi_cards(self, kpis, anomalies):
        """Generate KPI cards for a site"""
        html = ""

        # Production
        production = kpis.get('total_production_kwh', 0)
        html += f"""
        <div class="card success">
            <h3>Total Production</h3>
            <div class="value">{production:.2f}<span class="unit">kWh</span></div>
        </div>
        """

        # Efficiency
        eff = kpis.get('avg_efficiency_pct', 0)
        card_class = "card critical" if eff < 75 else "card warning" if eff < 85 else "card success"
        html += f"""
        <div class="{card_class}">
            <h3>Avg Efficiency</h3>
            <div class="value">{eff:.1f}<span class="unit">%</span></div>
        </div>
        """

        # Peak Power
        peak = kpis.get('peak_power_w', 0)
        html += f"""
        <div class="card success">
            <h3>Peak Power</h3>
            <div class="value">{peak:.0f}<span class="unit">W</span></div>
        </div>
        """

        # Battery SOC
        soc = kpis.get('avg_battery_soc_pct', 0)
        card_class = "card critical" if soc < 20 else "card warning" if soc < 50 else "card success"
        html += f"""
        <div class="{card_class}">
            <h3>Avg Battery SOC</h3>
            <div class="value">{soc:.1f}<span class="unit">%</span></div>
        </div>
        """

        # Min Battery
        min_soc = kpis.get('min_battery_soc_pct', 0)
        card_class = "card critical" if min_soc < 10 else "card warning" if min_soc < 20 else "card success"
        html += f"""
        <div class="{card_class}">
            <h3>Min Battery SOC</h3>
            <div class="value">{min_soc:.1f}<span class="unit">%</span></div>
        </div>
        """

        # Anomalies
        anomaly_count = len(anomalies)
        card_class = "card critical" if anomaly_count > 0 else "card success"
        html += f"""
        <div class="{card_class}">
            <h3>Anomalies Detected</h3>
            <div class="value">{anomaly_count}</div>
        </div>
        """

        return html

    def _generate_metrics_rows(self, kpis):
        """Generate detailed metrics table rows"""
        html = ""

        metrics = [
          