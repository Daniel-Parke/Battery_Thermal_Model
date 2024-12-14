from Battery.battery_thermal_model import calculate_net_energy_flows
from Load_Profile.Load import Load
from TMY_Data.TMY_Data import TMY_Data
from Battery.Battery import Battery
from Container.Container import Container

from dataclasses import dataclass
from typing import List

import polars as pl


@dataclass
class Battery_Model:
    tmy_data: 'TMY_Data'
    battery: 'Battery'
    box: 'Container'
    model_df: pl.DataFrame = None


    def __post_init__(self):
        self.model_df = calculate_net_energy_flows(
            tmy_data_df = self.tmy_data.tmy_data_df,
            box_length = self.box.box_length,
            box_width = self.box.box_width,
            box_height = self.box.box_height,
            battery_length = self.battery.battery_length,
            battery_width = self.battery.battery_width,
            battery_height = self.battery.battery_height,
            battery_heat_capacity = self.battery.battery_heat_capacity,
            battery_mass_kg = self.battery.battery_mass_kg,
            battery_losses_perc = self.battery.battery_losses_perc,
            heater_threshold_temp_c = self.battery.heater_threshold_temp_c,
            heater_power_w = self.battery.heater_power_w,
            heater_time_minutes = self.battery.heater_time_minutes,
            heater_battery_transfer = self.battery.heater_battery_transfer,
            battery_transfer_array = self.battery.battery_transfer_array,
            box_transfer_array = self.box.box_transfer_array,
            material_list = self.box.material_list,
            bucket_period_seconds = self.tmy_data.bucket_period_seconds,
            battery_emissivity=self.battery.battery_emissivity,
            box_inner_emissivity=self.box.inner_material_params[4],
            box_outer_emissivity=self.box.outer_material_params[4],
            battery_throughput_losses=self.battery.battery_losses_perc,
            )
