from Battery.Battery_Model import Battery_Model, Load, TMY_Data, Battery, Container

def main():
    # Set Location details and desired time interval
    latitude = 54.60283612642
    longitude = -5.9324865926
    interpolation_time_interval = "1m"

    load = Load(
        daily_electric=9.91,
        profile = "Domestic",
        country = "UK",
        interpolation_time_interval=interpolation_time_interval
    )

    tmy_data = TMY_Data(
        latitude=latitude,
        longitude=longitude,
        interpolation_time_interval=interpolation_time_interval,
        load=load
    )

    battery = Battery(
        battery_length = 0.9,
        battery_width = 0.6,
        battery_height = 0.3,
        battery_heat_capacity = 1000.0,
        battery_mass_kg = 36.0,
        battery_losses_perc = 0.03,
        battery_emissivity = 0.9,
        battery_transfer_array = [0, 1, 1, 1, 1, 1],
        heater_threshold_temp_c = 5.0,
        heater_power_w = 30.0,
        heater_time_minutes = 5.0,
        heater_battery_transfer = 0.8
    )

    box = Container(
        box_length = 1.0,
        box_width = 0.7,
        box_height = 0.4,
        inner_material = "Polystyrene",
        outer_material = "Wood",
        inner_material_thickness_m = 0.01,
        outer_material_thickness_m = 0.01,
        box_transfer_array = (0, 1, 1, 1, 1, 1)
    )

    battery_model = Battery_Model(
        tmy_data=tmy_data,
        battery=battery,
        box=box
    )

    model_df = battery_model.model_df

    save_file_path = "Data/Battery_Thermal_Model_TEST"
    model_df.write_csv(f"{save_file_path}.csv")

if __name__ == '__main__':
    main()
