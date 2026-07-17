"""
Solar System Data Analyzer
Calculates KPIs, detects anomalies, generates insights
"""

import json
import logging
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SolarAnalyzer:
    def __init__(self, thresholds=None):
        self.thresholds = thresholds or {
            'efficiency_warning': 85,
            'efficiency_critical': 75,
            'load_warning': 85,
            'load_critical': 100,
            'battery_low': 20,
            'battery_critical': 10,
            'voltage_deviation': 10,
        }

    def analyze_all_sites(self, raw_data):
        """Analyze all sites and generate KPIs"""
        logger.info("Starting data analysis...")

        analysis = {
            'timestamp': datetime.now().isoformat(),
            'sites': [],
            'summary': {},
            'anomalies': []
        }

        for site in raw_data.get('installations', []):
            logger.info(f"Analyzing {site.get('name', 'Unknown')}")

            site_analysis = self.analyze_site(site)
            if site_analysis:
                analysis['sites'].append(site_analysis)
                analysis['anomalies'].extend(site_analysis['anomalies'])

        analysis['summary'] = self.calculate_summary(analysis['sites'])
        logger.info(f"Analysis complete. Found {len(analysis['anomalies'])} anomalies")
        return analysis

    def analyze_site(self, site_data):
        """Analyze single site"""
        try:
            site_name = site_data.get('name', 'Unknown')
            mppt_data = site_data.get('mppt', {}).get('records', {}).get('data', {})
            inv_data = site_data.get('inverter', {}).get('records', {}).get('data', {})
            bat_data = site_data.get('battery', {}).get('records', {}).get('data', {})

            pv_power = self._extract_values(mppt_data.get('PVP', []))
            pv_voltage = self._extract_values(mppt_data.get('PVV0', []))
            inv_power = self._extract_values(inv_data.get('OP1', []))
            battery_soc = self._extract_values(bat_data.get('SOC', []))

            kpis = {
                'total_production_kwh': sum(pv_power) / 1000 if pv_power else 0,
                'avg_efficiency_pct': self._calculate_efficiency(pv_power, inv_power),
                'peak_power_w': max(pv_power) if pv_power else 0,
                'avg_load_pct': self._calculate_load(inv_power),
                'avg_battery_soc_pct': np.mean(battery_soc) if battery_soc else 0,
                'min_battery_soc_pct': min(battery_soc) if battery_soc else 0,
                'pv_voltage_max_v': max(pv_voltage) if pv_voltage else 0,
            }

            anomalies = self._detect_anomalies(site_name, kpis)

            return {
                'name': site_name,
                'site_id': site_data.get('site_id'),
                'kpis': kpis,
                'anomalies': anomalies
            }

        except Exception as e:
            logger.error(f"Error analyzing site: {e}")
            return None

    def _extract_values(self, data_list):
        """Extract numeric values from data points"""
        values = []
        for point in data_list:
            if isinstance(point, (list, tuple)) and len(point) > 1:
                val = point[1]
                if isinstance(val, (int, float)) and val != 0:
                    values.append(val)
        return values

    def _calculate_efficiency(self, pv_power, inv_power):
        """Calculate system efficiency"""
        if not pv_power or sum(pv_power) == 0:
            return 0
        total_in = sum(pv_power)
        total_out = sum(inv_power) if inv_power else 0
        if total_in > 0:
            return round((total_out / total_in) * 100, 1)
        return 0

    def _calculate_load(self, inv_power):
        """Calculate average inverter load"""
        nonzero = [p for p in inv_power if p > 0]
        if nonzero:
            return round(np.mean(nonzero), 1)
        return 0

    def _detect_anomalies(self, site_name, kpis):
        """Detect anomalies based on KPIs"""
        anomalies = []
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        eff = kpis['avg_efficiency_pct']
        if eff < self.thresholds['efficiency_critical']:
            anomalies.append({
                'type': 'LOW_EFFICIENCY_CRITICAL',
                'severity': 'CRITICAL',
                'message': f"Efficiency critically low at {eff}%",
                'site': site_name,
                'timestamp': f"🕐 {timestamp} UTC"
            })
        elif eff < self.thresholds['efficiency_warning']:
            anomalies.append({
                'type': 'LOW_EFFICIENCY',
                'severity': 'WARNING',
                'message': f"Efficiency low at {eff}%",
                'site': site_name,
                'timestamp': f"🕐 {timestamp} UTC"
            })

        min_soc = kpis['min_battery_soc_pct']
        if min_soc < self.thresholds['battery_critical']:
            anomalies.append({
                'type': 'BATTERY_CRITICAL',
                'severity': 'CRITICAL',
                'message': f"Battery SOC critically low at {min_soc}%",
                'site': site_name,
                'timestamp': f"🕐 {timestamp} UTC"
            })
        elif min_soc < self.thresholds['battery_low']:
            anomalies.append({
                'type': 'BATTERY_LOW',
                'severity': 'WARNING',
                'message': f"Battery SOC low at {min_soc}%",
                'site': site_name,
                'timestamp': f"🕐 {timestamp} UTC"
            })

        pv_voltage = kpis['pv_voltage_max_v']
        if pv_voltage > 500:
            anomalies.append({
                'type': 'OVERVOLTAGE',
                'severity': 'WARNING',
                'message': f"PV voltage high at {pv_voltage}V",
                'site': site_name,
                'timestamp': f"🕐 {timestamp} UTC"
            })

        return anomalies

    def calculate_summary(self, sites):
        """Calculate overall summary statistics"""
        if not sites:
            return {}

        total_production = sum(s['kpis']['total_production_kwh'] for s in sites)
        avg_efficiency = np.mean([s['kpis']['avg_efficiency_pct'] for s in sites if s['kpis']['avg_efficiency_pct'] > 0])
        avg_soc = np.mean([s['kpis']['avg_battery_soc_pct'] for s in sites])

        return {
            'total_sites': len(sites),
            'total_production_kwh': round(total_production, 2),
            'avg_efficiency_pct': round(avg_efficiency, 1),
            'avg_battery_soc_pct': round(avg_soc, 1),
            'top_performer': max(sites, key=lambda x: x['kpis']['total_production_kwh'])['name'],
        }

def main(data_file='data/data.json'):
    """Main execution"""
    with open(data_file, 'r') as f:
        raw_data = json.load(f)

    analyzer = SolarAnalyzer()
    analysis = analyzer.analyze_all_sites(raw_data)

    Path('data').mkdir(exist_ok=True)
    with open('data/analysis.json', 'w') as f:
        json.dump(analysis, f, indent=2)

    logger.info("Analysis saved to data/analysis.json")
    return analysis

if __name__ == "__main__":
    main()
