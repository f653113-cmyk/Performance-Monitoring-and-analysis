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
        }}
        .metrics-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        .metrics-table td {{
            padding: 14px 0;
            border-bottom: 1px solid #e8ecf1;
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

        <div class="grid">
            {kpi_cards}
        </div>

        <div class="details-section">
            <h2>System Performance Metrics</h2>
            <table class="metrics-table">
                {metrics_rows}
            </table>
        </div>

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

            logger.info(f"Generating dashboard for {site_name} (ID: {site_id})")

            kpi_cards = self._generate_kpi_cards(kpis)
            metrics_rows = self._generate_metrics_rows(kpis)

            html = self.site_dashboard_template.format(
                site_name=site_name,
                site_id=site_id,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
                kpi_cards=kpi_cards,
                metrics_rows=metrics_rows
            )

            dashboard_path = f'reports/dashboard_site_{site_id}.html'
            with open(dashboard_path, 'w') as f:
                f.write(html)

            logger.info(f"Dashboard saved to {dashboard_path}")
            dashboard_files.append(dashboard_path)

        return dashboard_files

    def _generate_kpi_cards(self, kpis):
        """Generate KPI cards for a site"""
        html = ""

        production = kpis.get('total_production_kwh', 0)
        html += f"""
        <div class="card">
            <h3>Total Production</h3>
            <div class="value">{production:.2f} kWh</div>
        </div>
        """

        eff = kpis.get('avg_efficiency_pct', 0)
        html += f"""
        <div class="card">
            <h3>Avg Efficiency</h3>
            <div class="value">{eff:.1f}%</div>
        </div>
        """

        peak = kpis.get('peak_power_w', 0)
        html += f"""
        <div class="card">
            <h3>Peak Power</h3>
            <div class="value">{peak:.0f} W</div>
        </div>
        """

        soc = kpis.get('avg_battery_soc_pct', 0)
        html += f"""
        <div class="card">
            <h3>Avg Battery SOC</h3>
            <div class="value">{soc:.1f}%</div>
        </div>
        """

        return html

    def _generate_metrics_rows(self, kpis):
        """Generate detailed metrics table rows"""
        html = ""

        metrics = [
            ('Total Production', f"{kpis.get('total_production_kwh', 0):.2f} kWh"),
            ('Peak Power Output', f"{kpis.get('peak_power_w', 0):.0f} W"),
            ('Average Efficiency', f"{kpis.get('avg_efficiency_pct', 0):.1f}%"),
            ('Average Load', f"{kpis.get('avg_load_pct', 0):.1f}%"),
            ('Average Battery SOC', f"{kpis.get('avg_battery_soc_pct', 0):.1f}%"),
            ('Minimum Battery SOC', f"{kpis.get('min_battery_soc_pct', 0):.1f}%"),
            ('PV Voltage (Max)', f"{kpis.get('pv_voltage_max_v', 0):.1f} V"),
        ]

        for label, value in metrics:
            html += f"""
            <tr>
                <td class="label">{label}</td>
                <td class="value">{value}</td>
            </tr>
            """

        return html

def main(analysis_file='data/analysis.json'):
    """Main execution"""
    with open(analysis_file, 'r') as f:
        analysis = json.load(f)

    generator = DashboardGenerator()
    dashboard_files = generator.generate_dashboards(analysis)
    return dashboard_files

if __name__ == "__main__":
    main()
