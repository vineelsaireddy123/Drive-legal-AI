import json
import os

class RulesDatabase:
    """Loads and provides access to traffic rules from structured JSON database."""
    
    def __init__(self):
        self.base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
        self.national_rules = self._load_json('india_national.json')
        self.state_rules = self._load_json('india_states.json')
        self.global_rules = self._load_json('global_rules.json')
        self.offline_cache = {}
        self._build_cache()
    
    def _load_json(self, filename):
        filepath = os.path.join(self.base_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: {filename} not found. Using empty data.")
            return {}
    
    def _build_cache(self):
        """Build offline cache from loaded data."""
        self.offline_cache = {
            'national': self.national_rules,
            'states': self.state_rules,
            'loaded': True
        }
    
    def get_violation(self, violation_key):
        """Get violation details from national database."""
        violations = self.national_rules.get('violations', {})
        return violations.get(violation_key)
    
    def get_all_violations(self):
        """Get all violation types."""
        return self.national_rules.get('violations', {})
    
    def get_violation_names(self):
        """Get a dict of violation_key -> violation_name."""
        violations = self.national_rules.get('violations', {})
        return {k: v['name'] for k, v in violations.items()}
    
    def get_state_override(self, state_key, violation_key):
        """Get state-specific fine override for a violation."""
        states = self.state_rules.get('states', {})
        uts = self.state_rules.get('union_territories', {})
        
        state_data = states.get(state_key) or uts.get(state_key)
        if state_data:
            return state_data.get('overrides', {}).get(violation_key)
        return None
    
    def get_state_info(self, state_key):
        """Get full state information."""
        states = self.state_rules.get('states', {})
        uts = self.state_rules.get('union_territories', {})
        return states.get(state_key) or uts.get(state_key)
    
    def get_state_from_city(self, city):
        """Map a city name to its state key."""
        city_map = self.state_rules.get('city_to_state_mapping', {})
        return city_map.get(city.lower().strip())
    
    def get_all_states(self):
        """Get list of all states and UTs."""
        states = list(self.state_rules.get('states', {}).keys())
        uts = list(self.state_rules.get('union_territories', {}).keys())
        return states + uts
    
    def get_speed_limits(self, vehicle_type='car', road_type='city'):
        """Get speed limit for a vehicle type on a road type."""
        limits = self.national_rules.get('speed_limits', {})
        road = limits.get(road_type, {})
        return road.get(vehicle_type, road.get('car', 50))
    
    def get_vehicle_types(self):
        """Get all vehicle type mappings."""
        return self.national_rules.get('vehicle_types', {})
    
    def get_general_rules(self):
        """Get general driving rules."""
        return self.national_rules.get('general_rules', {})
    
    def get_emergency_numbers(self):
        """Get emergency contact numbers."""
        return self.national_rules.get('general_rules', {}).get('emergency_numbers', {})
    
    def search_violations(self, query):
        """Search violations by keyword in name or description."""
        query = query.lower().strip()
        results = []
        for key, violation in self.get_all_violations().items():
            name = violation.get('name', '').lower()
            desc = violation.get('description', '').lower()
            if query in name or query in desc or query in key:
                results.append((key, violation))
        return results
    
    def is_data_loaded(self):
        """Check if database is loaded (for offline mode detection)."""
        return bool(self.offline_cache.get('loaded'))
    
    def get_all_state_keys(self):
        """Get list of all state and UT keys."""
        states = list(self.state_rules.get('states', {}).keys())
        uts = list(self.state_rules.get('union_territories', {}).keys())
        return states + uts
    
    def get_state_name(self, state_key):
        """Get the display name for a state key."""
        states = self.state_rules.get('states', {})
        uts = self.state_rules.get('union_territories', {})
        state_data = states.get(state_key) or uts.get(state_key)
        if state_data:
            return state_data.get('name', state_key)
        return None
    
    # --- Global / Multi-Country ---
    def get_all_countries(self):
        """Get dict of country_key -> country_name."""
        countries = self.global_rules.get('countries', {})
        return {k: v.get('name', k) for k, v in countries.items()}
    
    def get_country_data(self, country_key):
        """Get full data for a country."""
        return self.global_rules.get('countries', {}).get(country_key)
    
    def get_country_violations(self, country_key):
        """Get violations for a specific country."""
        country = self.get_country_data(country_key)
        if country:
            return country.get('violations', {})
        return {}
    
    def get_country_violation(self, country_key, violation_key):
        """Get a specific violation from a specific country."""
        violations = self.get_country_violations(country_key)
        return violations.get(violation_key)

