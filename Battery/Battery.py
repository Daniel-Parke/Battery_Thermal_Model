from dataclasses import dataclass
from typing import List



@dataclass
class Battery:
    battery_length: float = 0.9
    battery_width: float = 0.6
    battery_height: float = 0.3
    battery_heat_capacity: float = 1000.0
    battery_mass_kg: float = 36.0
    battery_losses_perc: float = 0.03
    battery_emissivity: float = 0.9
    battery_transfer_array: List[int] = (0, 1, 1, 1, 1, 1)
    heater_threshold_temp_c: float = 5.0
    heater_power_w: float = 30.0
    heater_time_minutes: float = 5.0
    heater_battery_transfer: float = 0.8

    def __post_init__(self):
        pass
