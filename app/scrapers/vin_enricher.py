import requests
import json
import logging
from typing import Dict, Optional
import time

logger = logging.getLogger(__name__)

class VinEnricher:
    """Enrich vehicle data using VIN APIs and web scraping"""
    
    def __init__(self, config):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': config.USER_AGENT
        })
    
    def enrich_vin_data(self, vin: str) -> Dict:
        """Main method to enrich VIN data from multiple sources"""
        if not vin or len(vin) != 17:
            logger.error(f"Invalid VIN: {vin}")
            return {}
        
        enriched_data = {
            'vin': vin,
            'data_quality_score': 0.0,
            'confidence_score': 0.0
        }
        
        # Try multiple data sources
        sources_tried = []
        
        # 1. Try NHTSA API (free, basic info)
        nhtsa_data = self._get_nhtsa_data(vin)
        if nhtsa_data:
            enriched_data.update(nhtsa_data)
            sources_tried.append('nhtsa')
            enriched_data['data_quality_score'] += 0.3
        
        # 2. Try Vehicle Database API (if API key available)
        if self.config.VIN_API_KEY:
            vehicle_db_data = self._get_vehicle_database_data(vin)
            if vehicle_db_data:
                enriched_data.update(vehicle_db_data)
                sources_tried.append('vehicle_database')
                enriched_data['data_quality_score'] += 0.5
        
        # 3. Try Porsche-specific data scraping
        porsche_data = self._get_porsche_specific_data(vin)
        if porsche_data:
            enriched_data.update(porsche_data)
            sources_tried.append('porsche_scraping')
            enriched_data['data_quality_score'] += 0.3
        
        # 4. Try recall data
        recall_data = self._get_recall_data(vin)
        if recall_data:
            enriched_data.update(recall_data)
            sources_tried.append('recall_api')
            enriched_data['data_quality_score'] += 0.2
        
        # Normalize data quality score
        enriched_data['data_quality_score'] = min(enriched_data['data_quality_score'], 1.0)
        enriched_data['confidence_score'] = enriched_data['data_quality_score']
        enriched_data['data_sources'] = sources_tried
        
        logger.info(f"VIN {vin} enriched from {len(sources_tried)} sources: {sources_tried}")
        
        return enriched_data
    
    def _get_nhtsa_data(self, vin: str) -> Optional[Dict]:
        """Get basic vehicle data from NHTSA API"""
        try:
            url = f"https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVin/{vin}?format=json"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get('Results'):
                nhtsa_info = {}
                
                # Parse NHTSA results
                for result in data['Results']:
                    variable = result.get('Variable', '')
                    value = result.get('Value')
                    
                    if not value or value in ['Not Applicable', 'N/A', '']:
                        continue
                    
                    # Map NHTSA fields to our schema
                    field_mapping = {
                        'Make': 'make',
                        'Model': 'model',
                        'Model Year': 'year',
                        'Trim': 'trim',
                        'Engine Number of Cylinders': 'engine_cylinders',
                        'Engine Power (kW)': 'horsepower_kw',
                        'Plant Country': 'plant_country',
                        'Plant City': 'plant_city',
                        'Plant Company Name': 'plant_company_name',
                        'Transmission Style': 'transmission',
                        'Drive Type': 'drivetrain',
                        'Fuel Type - Primary': 'fuel_type'
                    }
                    
                    if variable in field_mapping:
                        nhtsa_info[field_mapping[variable]] = value
                
                # Convert kW to HP if available
                if 'horsepower_kw' in nhtsa_info:
                    try:
                        kw = float(nhtsa_info['horsepower_kw'])
                        nhtsa_info['horsepower'] = int(kw * 1.34102)  # kW to HP conversion
                        del nhtsa_info['horsepower_kw']
                    except (ValueError, TypeError):
                        del nhtsa_info['horsepower_kw']
                
                nhtsa_info['data_source'] = 'nhtsa'
                return nhtsa_info
                
        except Exception as e:
            logger.error(f"Error getting NHTSA data for VIN {vin}: {str(e)}")
        
        return None
    
    def _get_vehicle_database_data(self, vin: str) -> Optional[Dict]:
        """Get enhanced data from Vehicle Database API"""
        try:
            if not self.config.VIN_API_KEY:
                return None
            
            url = f"{self.config.VIN_API_URL}/decode"
            headers = {
                'Authorization': f'Bearer {self.config.VIN_API_KEY}',
                'Content-Type': 'application/json'
            }
            
            response = self.session.post(
                url,
                json={'vin': vin},
                headers=headers,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                
                enhanced_info = {
                    'msrp': data.get('msrp'),
                    'market_value_estimate': data.get('market_value'),
                    'market_value_source': 'vehicle_database',
                    'optional_equipment': json.dumps(data.get('options', [])),
                    'standard_equipment': json.dumps(data.get('standard_features', [])),
                    'accident_history': data.get('accident_history'),
                    'service_records_count': data.get('service_records', 0),
                    'previous_owners_count': data.get('owners_count', 0),
                    'title_issues': json.dumps(data.get('title_issues', [])),
                    'api_response_raw': json.dumps(data),
                    'data_source': 'vehicle_database'
                }
                
                # Remove None values
                enhanced_info = {k: v for k, v in enhanced_info.items() if v is not None}
                
                return enhanced_info
                
        except Exception as e:
            logger.error(f"Error getting Vehicle Database data for VIN {vin}: {str(e)}")
        
        return None
    
    def _get_porsche_specific_data(self, vin: str) -> Optional[Dict]:
        """Scrape Porsche-specific data from official sources"""
        try:
            # This would involve scraping Porsche's VIN lookup or parts catalog
            # For now, return some Porsche-specific estimates
            
            porsche_info = {}
            
            # Decode some Porsche-specific VIN info
            if len(vin) == 17:
                # Porsche VINs have specific patterns
                model_year_code = vin[9]
                plant_code = vin[10:12]
                
                # Year decoding (simplified)
                year_mapping = {
                    'A': 2010, 'B': 2011, 'C': 2012, 'D': 2013, 'E': 2014,
                    'F': 2015, 'G': 2016, 'H': 2017, 'J': 2018, 'K': 2019,
                    'L': 2020, 'M': 2021, 'N': 2022, 'P': 2023, 'R': 2024
                }
                
                if model_year_code in year_mapping:
                    porsche_info['decoded_year'] = year_mapping[model_year_code]
                
                # Plant mapping (simplified)
                plant_mapping = {
                    'A0': 'Stuttgart-Zuffenhausen',
                    'A1': 'Leipzig',
                    'A2': 'Slovakia'
                }
                
                if plant_code in plant_mapping:
                    porsche_info['porsche_plant'] = plant_mapping[plant_code]
            
            # Add depreciation estimates for Porsche vehicles
            porsche_info['depreciation_rate'] = 0.15  # Porsches typically hold value well
            porsche_info['data_source'] = 'porsche_decoding'
            
            return porsche_info if porsche_info else None
            
        except Exception as e:
            logger.error(f"Error getting Porsche-specific data for VIN {vin}: {str(e)}")
        
        return None
    
    def _get_recall_data(self, vin: str) -> Optional[Dict]:
        """Get recall information for the VIN"""
        try:
            # Use NHTSA recalls API
            url = f"https://api.nhtsa.gov/recalls/recallsByVehicle?make=porsche&vin={vin}"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                recalls = data.get('results', [])
                
                if recalls:
                    open_recalls = []
                    completed_recalls = []
                    
                    for recall in recalls:
                        recall_info = {
                            'recall_id': recall.get('NHTSACampaignNumber'),
                            'component': recall.get('Component'),
                            'summary': recall.get('Summary'),
                            'date': recall.get('ReportReceivedDate')
                        }
                        
                        # For simplicity, assume all are open (would need additional API to check completion)
                        open_recalls.append(recall_info)
                    
                    recall_data = {
                        'recall_count': len(recalls),
                        'open_recalls': json.dumps(open_recalls),
                        'completed_recalls': json.dumps(completed_recalls),
                        'data_source': 'nhtsa_recalls'
                    }
                    
                    return recall_data
                
        except Exception as e:
            logger.error(f"Error getting recall data for VIN {vin}: {str(e)}")
        
        return None
    
    def estimate_market_value(self, vin: str, year: int, model: str, mileage: int) -> Optional[Dict]:
        """Estimate market value based on available data"""
        try:
            # This is a simplified estimation - in practice you'd use KBB, Edmunds, or similar APIs
            
            # Base values for common Porsche models (simplified)
            base_values = {
                '911': {2020: 120000, 2019: 110000, 2018: 100000},
                'Cayenne': {2020: 75000, 2019: 70000, 2018: 65000},
                'Macan': {2020: 60000, 2019: 55000, 2018: 50000},
                'Panamera': {2020: 95000, 2019: 85000, 2018: 75000}
            }
            
            if model in base_values and year in base_values[model]:
                base_value = base_values[model][year]
                
                # Adjust for mileage (rough calculation)
                mileage_adjustment = max(0, (50000 - mileage) * 0.30)  # $0.30 per mile under 50k
                estimated_value = base_value + mileage_adjustment
                
                return {
                    'market_value_estimate': int(estimated_value),
                    'market_value_source': 'internal_estimation',
                    'confidence_score': 0.6  # Lower confidence for internal estimates
                }
                
        except Exception as e:
            logger.error(f"Error estimating market value: {str(e)}")
        
        return None
