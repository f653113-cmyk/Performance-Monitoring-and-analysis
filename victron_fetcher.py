"""
Victron VRM Data Fetcher
Automatically fetches data from all Victron installations
"""

import requests
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VictronFetcher:
    def __init__(self, api_token):
        self.token = api_token
        self.base_url = "https://vrmapi.victronenergy.com/v2"
        self.session = requests.Session()
        self.session.headers["X-Authorization"] = f"Token {self.token}"

    def get_all_installations(self):
        """Fetch all installations from Victron account"""
        try:
            url = f"{self.base_url}/installations?access_token={self.token}"
            logger.info(f"DEBUG: Fetching from {url[:60]}...")
            response = requests.get(url)
            logger.info(f"DEBUG: Response status: {response.status_code}")
            if response.status_code != 200:
                logger.info(f"DEBUG: Response text: {response.text}")
            response.raise_for_status()
            return response.json()['records']
        except Exception as e:
            logger.error(f"Failed to fetch installations: {e}")
            try:
                logger.info("Trying with Authorization header...")
                url = f"{self.base_url}/installations"
                response = self.session.get(url)
                logger.info(f"DEBUG: Header method response: {response.status_code}")
                response.raise_for_status()
                return response.json()['records']
            except Exception as e2:
                logger.error(f"Both methods failed: {e2}")
                return []

    def get_site_data(self, site_id, days_back=30):
        """Fetch MPPT, Inverter, Battery data for a site"""
        try:
            end_time = int(datetime.now().timestamp())
            start_time = int((datetime.now() - timedelta(days=days_back)).timestamp())

            data = {
                'site_id': site_id,
                'mppt': self._fetch_mppt(site_id, start_time, end_time),
                'inverter': self._fetch_inverter(site_id, start_time, end_time),
                'battery': self._fetch_battery(site_id, start_time, end_time),
            }
            return data
        except Exception as e:
            logger.error(f"Failed to fetch site {site_id} data: {e}")
            return None

    def _fetch_mppt(self, site_id, start, end):
        """Fetch MPPT data"""
        url = (f"{self.base_url}/installations/{site_id}/widgets/Graph"
               f"?attributeCodes[]=PVV0&attributeCodes[]=PVV1&attributeCodes[]=PVV2"
               f"&attributeCodes[]=PVV3&attributeCodes[]=PVI&attributeCodes[]=PVP"
               f"&attributeCodes[]=ScV&attributeCodes[]=ScI&attributeCodes[]=ScW"
               f"&instance=279&start={start}&end={end}")
        response = self.session.get(url)
        return response.json() if response.status_code == 200 else {}

    def _fetch_inverter(self, site_id, start, end):
        """Fetch Inverter data"""
        url = (f"{self.base_url}/installations/{site_id}/widgets/Graph"
               f"?attributeCodes[]=CV&attributeCodes[]=CI"
               f"&attributeCodes[]=OV1&attributeCodes[]=OI1&attributeCodes[]=OP1"
               f"&attributeCodes[]=OV2&attributeCodes[]=OI2&attributeCodes[]=OP2"
               f"&attributeCodes[]=OV3&attributeCodes[]=OI3&attributeCodes[]=OP3"
               f"&attributeCodes[]=OF&attributeCodes[]=t9"
               f"&instance=276&start={start}&end={end}&useMinMax=1")
        response = self.session.get(url)
        return response.json() if response.status_code == 200 else {}

    def _fetch_battery(self, site_id, start, end):
        """Fetch Battery data"""
        url = (f"{self.base_url}/installations/{site_id}/widgets/Graph"
               f"?attributeCodes[]=SOC&attributeCodes[]=V&attributeCodes[]=I"
               f"&attributeCodes[]=H11"
               f"&instance=512&start={start}&end={end}&interval=15mins")
        response = self.session.get(url)
        return response.json() if response.status_code == 200 else {}

    def fetch_all_data(self, days_back=30):
        """Fetch data for all installations"""
        logger.info("Starting data fetch from Victron API...")

        installations = self.get_all_installations()
        logger.info(f"Found {len(installations)} installations")

        all_data = {
            'timestamp': datetime.now().isoformat(),
            'installations': []
        }

        for site in installations:
            logger.info(f"Fetching data for {site['name']} (ID: {site['id']})")
            site_data = self.get_site_data(site['id'], days_back)
            if site_data:
                site_data['name'] = site['name']
                all_data['installations'].append(site_data)

        logger.info(f"Successfully fetched data for {len(all_data['installations'])} sites")
        return all_data

def main(api_token, output_file='data.json'):
    """Main execution"""
    fetcher = VictronFetcher(api_token)
    data = fetcher.fetch_all_data(days_back=30)

    # Save to file
    Path('data').mkdir(exist_ok=True)
    with open(f'data/{output_file}', 'w') as f:
        json.dump(data, f, indent=2)

    logger.info(f"Data saved to data/{output_file}")
    return data

if __name__ == "__main__":
    import sys
    import os
    token = os.environ.get('VRM_API_TOKEN')
    if token:
        main(token)
    else:
        print("Usage: set VRM_API_TOKEN environment variable first")
