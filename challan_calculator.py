"""
Challan Calculator Engine â€” DriveLegal.ai
Intelligent fine calculation with state overrides and vehicle modifiers.
Covers all 66+ violations from the Motor Vehicles (Amendment) Act, 2019.
"""


class ChallanCalculator:
    """Calculates traffic violation fines with location and vehicle awareness."""

    # Vehicle type modifiers â€“ heavier vehicles attract higher fines
    VEHICLE_MODIFIERS = {
        'two_wheeler': 0.75,
        'auto_rickshaw': 0.85,
        'car': 1.0,
        'taxi': 1.1,
        'bus': 1.5,
        'truck': 1.5,
        'commercial': 1.3,
        'e_rickshaw': 0.8,
    }

    def __init__(self, db=None):
        self.db = db

    # â”€â”€ Single violation â”€â”€
    def calculate(self, violation_key, vehicle_type='car', state_key=None,
                  is_repeat=False, extra_passengers=0, extra_tonnes=0):
        """
        Calculate fine for a single violation.
        Returns dict with fine breakdown, section reference, and penalties.
        """
        if not self.db:
            return {'error': 'Database not loaded'}

        violation = self.db.get_violation(violation_key)
        if not violation:
            return {'error': f'Unknown violation: {violation_key}'}

        # ── Base fine ──
        fine_data = violation.get('fine', 0)
        if isinstance(fine_data, dict):
            if is_repeat:
                fine = fine_data.get('repeat_offense', fine_data.get('first_offense', fine_data.get('first', 0)))
            else:
                fine = fine_data.get('first_offense', fine_data.get('first', fine_data.get('min', 0)))
            # Handle nested vehicle-type fines (e.g. overspeeding)
            if isinstance(fine, dict):
                fine = fine.get(vehicle_type, fine.get('default', 0))
        else:
            fine = fine_data
            if is_repeat:
                fine = int(fine * 2)

        # â”€â”€ Vehicle modifier â”€â”€
        modifier = self.VEHICLE_MODIFIERS.get(vehicle_type, 1.0)
        fine = int(fine * modifier)

        # â”€â”€ State override â”€â”€
        state_fine = None
        state_label = 'National (MV Act 2019)'
        if state_key and self.db:
            override = self.db.get_state_override(state_key, violation_key)
            if override:
                if is_repeat:
                    state_fine = override.get('repeat_offense', override.get('first_offense', fine))
                else:
                    state_fine = override.get('first_offense', fine)
                if isinstance(state_fine, dict):
                    state_fine = state_fine.get(vehicle_type, state_fine.get('default', fine))
                state_fine = int(state_fine * modifier)
                state_label = self.db.get_state_name(state_key) or state_key

        # â”€â”€ Overloading surcharge â”€â”€
        overload_surcharge = 0
        if extra_passengers > 0 and violation_key == 'overloading_passengers':
            overload_surcharge = extra_passengers * 1000 * modifier
        if extra_tonnes > 0 and violation_key == 'overloading_goods':
            overload_surcharge = extra_tonnes * 2000 * modifier

        total_fine = (state_fine if state_fine is not None else fine) + overload_surcharge

        # â”€â”€ Imprisonment check â”€â”€
        imprisonment = violation.get('imprisonment', None)

        return {
            'violation_key': violation_key,
            'violation_name': violation.get('name', violation_key),
            'section': violation.get('section', 'â€”'),
            'national_fine': fine,
            'state_fine': state_fine,
            'state_label': state_label,
            'vehicle_type': vehicle_type,
            'vehicle_modifier': modifier,
            'is_repeat': is_repeat,
            'overload_surcharge': int(overload_surcharge),
            'total_fine': int(total_fine),
            'imprisonment': imprisonment,
            'points': violation.get('points', 0),
        }

    # â”€â”€ Multiple violations â”€â”€
    def calculate_multiple(self, violations_list, vehicle_type='car',
                           state_key=None, is_repeat=False):
        """Calculate fines for a list of violations and return a summary."""
        results = []
        grand_total = 0
        for vk in violations_list:
            r = self.calculate(vk, vehicle_type, state_key, is_repeat)
            if 'error' not in r:
                grand_total += r['total_fine']
            results.append(r)
        return {
            'violations': results,
            'count': len(results),
            'grand_total': grand_total,
            'vehicle_type': vehicle_type,
            'state': state_key or 'national',
            'is_repeat': is_repeat,
        }

    # â”€â”€ Cross-state comparison â”€â”€
    def compare_states(self, violation_key, vehicle_type='car', is_repeat=False):
        """Compare fine for a violation across all states."""
        if not self.db:
            return {'error': 'Database not loaded'}

        national = self.calculate(violation_key, vehicle_type, None, is_repeat)
        if 'error' in national:
            return national

        states = self.db.get_all_state_keys()
        comparison = [{'state': 'National (Default)', 'fine': national['total_fine']}]
        for sk in states:
            r = self.calculate(violation_key, vehicle_type, sk, is_repeat)
            comparison.append({
                'state': r.get('state_label', sk),
                'fine': r['total_fine'],
            })

        comparison.sort(key=lambda x: x['fine'])
        return {
            'violation': national['violation_name'],
            'section': national['section'],
            'vehicle_type': vehicle_type,
            'is_repeat': is_repeat,
            'comparison': comparison,
            'lowest': comparison[0],
            'highest': comparison[-1],
        }

    # â”€â”€ Speed limit info â”€â”€
    def get_speed_limits(self, vehicle_type='car', road_type='highway'):
        """Return speed limits by vehicle type and road type."""
        limits = {
            'highway': {'car': 100, 'two_wheeler': 80, 'bus': 80, 'truck': 60, 'auto_rickshaw': 40},
            'urban': {'car': 50, 'two_wheeler': 40, 'bus': 40, 'truck': 30, 'auto_rickshaw': 30},
            'residential': {'car': 30, 'two_wheeler': 25, 'bus': 25, 'truck': 20, 'auto_rickshaw': 20},
        }
        road_limits = limits.get(road_type, limits['urban'])
        return {
            'vehicle_type': vehicle_type,
            'road_type': road_type,
            'speed_limit_kmh': road_limits.get(vehicle_type, 50),
            'all_limits': road_limits,
        }


