import numpy as np
import polars as pl

from numba import njit

from Battery.battery_model_functions import calculate_heat_transfer_areas


def calculate_convective_resistance(
    heat_transfer_coefficient: float, area_m2: float
) -> float:
    """
    Calculate the convective thermal resistance.

    Args:
        heat_transfer_coefficient (float): Convective heat transfer coefficient in W/m²·K.
        area_m2 (float): Area of the surface in contact with the air in square meters (m²).

    Returns:
        float: Convective thermal resistance in K/W.
    """
    convective_resistance = 1 / (heat_transfer_coefficient * area_m2)  # R = 1 / (h * A)
    return convective_resistance


def calculate_conductive_resistance(
    thickness_m: float, thermal_conductivity: float, area_m2: float
) -> float:
    """
    Calculate the conductive thermal resistance.

    Args:
        thickness_m (float): Thickness of the material in meters (m).
        thermal_conductivity (float): Thermal conductivity of the material in W/m·K.
        area_m2 (float): Area of the material in square meters (m²).

    Returns:
        float: Conductive thermal resistance in K/W.
    """
    conductive_resistance = thickness_m / (
        thermal_conductivity * area_m2
    )  # R = d / (k * A)
    return conductive_resistance


def calculate_composite_conductive_resistance(
    materials: list[tuple[float, float]], area_m2: float
) -> float:
    """
    Calculate the total conductive thermal resistance for a composite wall.

    Args:
        materials (list[tuple[float, float]]): A list of materials, where each material is represented as:
            - (thickness_m, thermal_conductivity)
        area_m2 (float): Cross-sectional area of the wall in square meters (m²).

    Returns:
        float: Total conductive thermal resistance in K/W.
    """
    total_resistance = 0.0

    for thickness_m, thermal_conductivity, _, _, _ in materials:
        # Calculate resistance for each layer
        resistance = thickness_m / (thermal_conductivity * area_m2)
        total_resistance += resistance

    return total_resistance


@njit
def calculate_heat_energy_flow(
    internal_temperature: float, external_temperature: float, thermal_resistance: float, duration_seconds: float
) -> float:
    """
    Calculate the heat energy flow between two regions over a specified time duration.

    Args:
        internal_temperature (float): Temperature of the inner region in °C.
        external_temperature (float): Temperature of the outer region in °C.
        thermal_resistance (float): Thermal resistance between the regions in K/W.
        duration_seconds (float): Time duration for the energy transfer in seconds.

    Returns:
        float: Heat energy flow in Joules (J).
    """
    delta_temperature = internal_temperature - external_temperature 
    power_watts = delta_temperature / thermal_resistance
    heat_energy_joules = power_watts * duration_seconds
    return heat_energy_joules


@njit
def calculate_inner_radiative_heat_flow(
    surface_area_inner: float,
    surface_area_outer: float,
    emissivity_inner: float,
    emissivity_outer: float,
    temperature_inner_c: float,
    temperature_outer_c: float,
    duration_seconds: float
) -> float:
    """
    Calculate radiative heat transfer between the inner box and the inner container walls.

    Args:
        surface_area_inner (float): Surface area of the inner box (m²).
        surface_area_outer (float): Surface area of the inner container walls (m²).
        emissivity_inner (float): Emissivity of the inner box surface (0 to 1).
        emissivity_outer (float): Emissivity of the container wall surface (0 to 1).
        temperature_inner_c (float): Temperature of the inner box (Celsius).
        temperature_outer_c (float): Temperature of the inner container walls (Celsius).
        duration_seconds (float): Duration for the energy transfer in seconds.

    Returns:
        float: Total heat transfer in Joules (J).
    """
    # Stefan-Boltzmann constant
    stefan_boltzmann_constant = 5.67e-8

    # Convert temperatures to Kelvin
    temperature_inner_k = temperature_inner_c + 273.15
    temperature_outer_k = temperature_outer_c + 273.15

    # Effective emissivity
    effective_emissivity = 1 / (
        (1 / emissivity_inner)
        + (surface_area_inner / surface_area_outer)
        * (1 / emissivity_outer - 1)
    )

    # Radiative power (W)
    power_watts = (
        stefan_boltzmann_constant
        * effective_emissivity
        * surface_area_inner
        * (temperature_inner_k**4 - temperature_outer_k**4)
    )

    # Total heat transfer over the duration (J)
    heat_energy_joules = power_watts * duration_seconds
    return heat_energy_joules


@njit
def calculate_outer_radiative_heat_flow(
    surface_area: float,
    emissivity: float,
    temperature_inner_c: float,
    temperature_outer_c: float,
    duration_seconds: float
) -> float:
    """
    Calculate radiative heat loss using Stefan-Boltzmann law over a time duration.

    Args:
        surface_area (float): Surface area in square meters (m²).
        emissivity (float): Emissivity of the surface (0 to 1).
        temperature_inner_c (float): Temperature of the emitting surface in Celcius (C).
        temperature_outer_c (float): Temperature of the receiving surface in Celcius (C).
        duration_seconds (float): Time duration for the energy transfer in seconds.

    Returns:
        float: Radiative heat transfer in Joules (J).
    """
    # Define constants and convert Celcius to Kelvin
    stefan_boltzmann_constant = 5.67e-8  # W/m²·K⁴
    temperature_inner_k = temperature_inner_c + 273.15  # Convert to Kelvin
    temperature_outer_k = temperature_outer_c + 273.15  # Convert to Kelvin

    power_watts = (
        stefan_boltzmann_constant
        * emissivity
        * surface_area
        * (temperature_inner_k**4 - temperature_outer_k**4)
    )
    heat_energy_joules = power_watts * duration_seconds  # Q = P * t
    return heat_energy_joules


@njit
def calculate_air_heat_capacity(temperature: float, relative_humidity: float) -> float:
    """
    Calculate the specific heat capacity of moist air based on temperature and relative humidity.

    Parameters:
    - temperature: Air temperature in °C
    - relative_humidity: Relative humidity as a percentage (0 to 100)

    Returns:
    - Heat capacity of air in J/(kg·K)
    """
    # Constants
    cp_dry_air = 1005  # J/(kg·K), specific heat capacity of dry air
    cp_water_vapor = 1860  # J/(kg·K), specific heat capacity of water vapor

    # Saturation vapor pressure of water (in hPa), using approximation
    es = 6.112 * (np.exp((17.67 * temperature) / (temperature + 243.5)))

    # Actual vapor pressure (in hPa)
    e = (relative_humidity / 100) * es

    # Mixing ratio of water vapor (kg water vapor per kg dry air)
    mixing_ratio = (
        0.622 * e / (1013.25 - e)
    )  # 1013.25 hPa is standard atmospheric pressure

    # Heat capacity of moist air
    cp_moist_air = cp_dry_air + mixing_ratio * cp_water_vapor

    return cp_moist_air


@njit
def calculate_battery_energy_losses(
    battery_power_w: float, loss_percentage: float, duration_seconds: float = 60
) -> float:
    """
    Calculate the heat energy loss from the battery due to inefficiency.

    Args:
        battery_power_w (float): Total power of the battery in Watts (W).
        loss_percentage (float): Fraction of energy lost (e.g., 0.03 for 3%).

    Returns:
        float: Heat energy loss in Joules (J) over a 1-minute period.
    """
    # Energy loss in Watts (W)
    energy_loss_w = battery_power_w * loss_percentage  # Q_loss = P * loss_percentage

    # Convert energy loss to Joules over a 1-minute period
    energy_loss_j = energy_loss_w * duration_seconds  # Q = W * time (seconds)

    return energy_loss_j


@njit
def calculate_energy_input(power_w: float, duration_seconds: float = 60) -> float:
    """
    Calculate the heat energy input from the heater.

    Args:
        heater_power_w (float): Power of the heater in Watts (W).
        duration_seconds (float): Duration the heater is on in seconds (default is 60).

    Returns:
        float: Heat energy input in Joules (J).
    """
    # Calculate energy input in Joules
    heater_energy_j = power_w * duration_seconds  # Q = P * t

    return heater_energy_j


@njit
def calc_change_in_temperature_c(
    initial_temp: float, heat_energy: float, heat_capacity: float, mass: float
) -> float:
    """
    Calculate the change in temperature given heat energy.

    Args:
        initial_temp (float): Initial temperature in °C.
        heat_energy (float): Heat energy input/output in Joules (J).
        heat_capacity (float): Specific heat capacity of the material in J/kg·K.
        mass (float): Mass of the material in kilograms (kg).

    Returns:
        float: New temperature in °C after applying heat energy.
    """
    delta_temp = heat_energy / (heat_capacity * mass)  # ΔT = Q / (m * c)
    new_temp = initial_temp + delta_temp
    return new_temp


def calculate_battery_box_parameters(
    battery_length: float,
    battery_width: float,
    battery_height: float,
    box_length: float,
    box_width: float,
    box_height: float,
    battery_transfer_array: list[int],
    box_transfer_array: list[int],
    material_list: list[tuple[float, float, float, float]],  # (thickness, thermal_conductivity, heat_capacity, density)
):
    """
    Preprocess dimensions, heat transfer areas, and resistances required for the energy model.

    Args:
        battery_length (float): Length of the battery in meters.
        battery_width (float): Width of the battery in meters.
        battery_height (float): Height of the battery in meters.
        box_length (float): Length of the box in meters.
        box_width (float): Width of the box in meters.
        box_height (float): Height of the box in meters.
        battery_transfer_array (list[int]): Array indicating battery transfer surfaces.
        box_transfer_array (list[int]): Array indicating box transfer surfaces.
        material_list (list[tuple]): List of material properties (thickness, conductivity, heat_capacity, density).

    Returns:
        dict: Dictionary containing precalculated values for areas, resistances, and heat capacities.
    """

    # Heat transfer areas
    if not battery_transfer_array:
        battery_transfer_array = [0, 1, 1, 1, 1, 1]
    if not box_transfer_array:
        box_transfer_array = [0, 1, 1, 1, 1, 1]

    # Calculate heat transfer areas
    (
        battery_conductive_area,
        battery_convective_area,
        air_convective_area,
        box_conductive_area,
        box_convective_area,
    ) = calculate_heat_transfer_areas(
        battery_length=battery_length,
        battery_width=battery_width,
        battery_height=battery_height,
        box_length=box_length,
        box_width=box_width,
        box_height=box_height,
        battery_transfer_array=battery_transfer_array,
        box_transfer_array=box_transfer_array,
    )
    total_box_area = box_conductive_area + box_convective_area
    total_battery_area = battery_conductive_area + battery_convective_area


    # Calculate resistances for each surface area required
    # Composite wall material properties, outer material presented first
    outer_material_thermal_conductivity = material_list[0][0]  # W/m·K
    outer_material_layer_thickness = material_list[0][1]  # m (1 cm for each layer)
    outer_material_heat_capacity = material_list[0][2]  # j/kgC (Material Heat Capacity)
    outer_material_density = material_list[0][3]  # kg/m3 (Material density)

    if material_list[1]:
        inner_material_thermal_conductivity = material_list[1][0]  # W/m·K
        inner_material_layer_thickness = material_list[1][1]  # m (1 cm for each layer)
        inner_material_heat_capacity = material_list[1][2]  # j/kgC (Material Heat Capacity)
        inner_material_density = material_list[1][3]  # kg/m3 (Material density)
    else:
        outer_material_layer_thickness = (outer_material_layer_thickness / 2)
        inner_material_thermal_conductivity = outer_material_thermal_conductivity
        inner_material_layer_thickness = outer_material_layer_thickness
        inner_material_heat_capacity = outer_material_heat_capacity
        inner_material_density = outer_material_density


    box_wall_mass_kg = ((total_box_area/2 * inner_material_density * inner_material_layer_thickness) 
                        + (total_box_area/2 * outer_material_density) * outer_material_layer_thickness)
    box_heat_capacity = (inner_material_heat_capacity + outer_material_heat_capacity) / 2

    # Calculate heat transfer resistances for all surfaces
    battery_conductive_resistance = calculate_conductive_resistance(
        inner_material_layer_thickness, inner_material_thermal_conductivity, battery_conductive_area
        )
    battery_convective_resistance = calculate_convective_resistance(5, battery_convective_area)
    box_inner_convective_resistance = calculate_convective_resistance(5, air_convective_area)
    box_composite_conductive_resistance = calculate_composite_conductive_resistance(material_list, total_box_area)
    box_outer_conductive_resistance = calculate_conductive_resistance(
        outer_material_layer_thickness, outer_material_thermal_conductivity, box_conductive_area
        )
    box_outer_convective_resistance = calculate_convective_resistance(5, box_convective_area)

    # Deubgging Print Statements
    # print(f"Battery -> Air Convective Area: {battery_convective_area:.2f} m²")
    # print(f"Battery -> Box Inner Conductive Area: {battery_conductive_area:.2f} m²")
    # print(f"Battery -> Air Convective Resistance: {battery_convective_resistance:.2f} K/W")
    # print(f"Battery -> Box Inner Conductive Resistance: {battery_conductive_resistance:.2f} K/W")
    # print("*****************************************************")
    # print(f"Air -> Box Inner Convective Area: {air_convective_area:.2f} m²")
    # print(f"Air -> Box Inner Convective Resistance: {box_inner_convective_resistance:.2f} K/W")
    # print("*****************************************************")
    # print(f"Box Inner -> Box Outer Conductive Area: {total_box_area:.2f} m²")
    # print(f"Box Inner -> Box Outer Conductive Resistance: {box_composite_conductive_resistance:.2f} K/W")
    # print("*****************************************************")
    # print(f"Box -> Environment Conductive Area: {box_conductive_area:.2f} m²")
    # print(f"Box -> Environment Convective Area: {box_convective_area:.2f} m²")
    # print(f"Box -> Environment Conductive Resistance: {box_outer_conductive_resistance:.2f} K/W")
    # print(f"Box -> Environment Convective Resistance: {box_outer_convective_resistance:.2f} K/W")
    

    return (box_wall_mass_kg, box_heat_capacity, battery_conductive_resistance, 
            battery_convective_resistance, box_inner_convective_resistance, box_composite_conductive_resistance,
            box_outer_conductive_resistance, box_outer_convective_resistance,
            total_box_area, total_battery_area)


# -------------------------------------------------------------------------- #
# ------------------------- HEAT ENERGY FLOW MODEL ------------------------- #
# -------------------------------------------------------------------------- #
def calculate_net_energy_flows(
    tmy_data_df: pl.DataFrame,
    box_length: float = 1.0,
    box_width: float = 0.7,
    box_height: float = 0.4,
    battery_length: float = 0.9,
    battery_width: float = 0.6,
    battery_height: float = 0.3,
    battery_heat_capacity: float = 1000.0,
    battery_mass_kg: float = 36.0,
    battery_losses_perc: float = 0.03,
    heater_threshold_temp_c: float = 5.0,
    use_heater: bool = True,
    heater_power_w: float = 30.0,
    heater_time_minutes: float = 5.0,
    heater_battery_transfer: float = 0.8,
    battery_transfer_array: list[int] = None,
    box_transfer_array: list[int] = None,
    material_list: list[tuple[float, float, float, float]] = None,
    bucket_period_seconds: float = 60.0,
    battery_emissivity: float = 0.9,
    box_inner_emissivity: float = 0.9,
    box_outer_emissivity: float = 0.9,
    battery_throughput_losses: float = 0.03,
) -> pl.DataFrame:
    """
    Calculate net energy flows in a system over time using Typical Meteorological Year (TMY) data.

    The function models the temperature changes and energy exchanges between a battery, 
    its surrounding air, and a box that encloses the battery. It also simulates the 
    effects of external temperature, humidity, and a heater on the system.

    Args:
        tmy_data_df (pl.DataFrame): Input data containing time-series ambient temperature 
                                    and humidity data in a Polars DataFrame.
        box_length, box_width, box_height (float): Dimensions of the enclosing box in meters.
        battery_length, battery_width, battery_height (float): Dimensions of the battery in meters.
        battery_heat_capacity (float): Heat capacity of the battery in J/(kg·K).
        battery_mass_kg (float): Mass of the battery in kilograms.
        battery_losses_perc (float): Percentage of energy losses due to battery inefficiency (e.g., 0.03 for 3%).
        heater_threshold_temp_c (float): Temperature in degrees Celsius below which the heater activates.
        heater_power_w (float): Power of the heater in watts.
        heater_time_minutes (float): Minimum duration in minutes that the heater remains active once triggered.
        heater_battery_transfer (float): Fraction of heater energy transferred to the battery.
        battery_transfer_array, box_transfer_array (list[int]): Arrays defining transfer resistances for the battery and box.
        material_list (list[tuple]): Material properties for walls, such as conductivity and specific heat.
        bucket_period_seconds (float): Time step duration in seconds for the simulation.

    Returns:
        pl.DataFrame: Polars DataFrame containing time-series data of calculated temperatures 
                      and energy flows for the battery, air, and box system.
    """

    # Calculate thermal resistances and mass properties for the box and battery
    (
        box_wall_mass_kg, box_heat_capacity, battery_conductive_resistance, 
        battery_convective_resistance, box_inner_convective_resistance, box_composite_conductive_resistance,
        box_outer_conductive_resistance, box_outer_convective_resistance,
        total_box_area, total_battery_area
        ) = calculate_battery_box_parameters(
        battery_length = battery_length,
        battery_width = battery_width,
        battery_height = battery_height,
        box_length = box_length,
        box_width = box_width,
        box_height = box_height,
        battery_transfer_array = battery_transfer_array,
        box_transfer_array = box_transfer_array,
        material_list = material_list,
    )

    # PRE CALCULATE BATTERY NET ENERGY WITH LOAD LOSSES AS THESE ARE PREDETERMINED

    # Initialize Model Variables
    heater_power_j = heater_power_w * bucket_period_seconds
    initial_temperature = tmy_data_df["Ambient_Temperature_C"][0]
    battery_temp = initial_temperature
    box_temp = initial_temperature

    # Define default columns and their initial values, create temperature and energy tracking columns
    default_columns = {
        "Battery_Temp_C": battery_temp,
        "Box_Inner_Temp_C": box_temp,
        "Box_Outer_Temp_C": box_temp,
        "Battery_Heater_Input_J": 0.0,
        "Battery_Cond_to_Box_Inner_Energy_J": 0.0,
        "Battery_Conv_to_Box_Inner_Energy_J": 0.0,
        "Battery_Radi_to_Box_Inner_Energy_J": 0.0,
        "Heater_to_Battery_Energy_J": 0.0,
        "Heater_to_Box_Inner_Energy_J": 0.0,
        "Box_Inner_Net_Energy_J": 0.0,
        "Box_Inner_Cond_to_Battery_Energy_J": 0.0,
        "Box_Inner_Conv_to_Battery_Energy_J": 0.0,
        "Box_Inner_Radi_to_Battery_Energy_J": 0.0,
        "Box_Inner_to_Box_Outer_Energy_J": 0.0,
        "Box_Outer_Net_Energy_J": 0.0,
        "Box_Outer_to_Box_Inner_Energy_J": 0.0,
        "Box_Outer_Cond_to_Environment_Energy_J": 0.0,
        "Box_Outer_Conv_to_Environment_Energy_J": 0.0,
        "Box_Outer_Radi_to_Environment_Energy_J": 0.0,
        "Box_Outer_Cond_from_Environment_Energy_J": 0.0,
        "Box_Outer_Conv_from_Environment_Energy_J": 0.0,
        "Box_Radi_Conv_from_Environment_Energy_J": 0.0,
    }

    # Dynamically add columns to DataFrame based on default columns above
    model_df = tmy_data_df.with_columns(
        [pl.lit(value).alias(name) for name, value in default_columns.items()]
    )

    if "Energy_Use_kWh" in model_df.columns:
        model_df = model_df.with_columns(
            (pl.col("Energy_Use_kWh")
             * 3_600_000
             * battery_losses_perc)
             .alias("Battery_Losses_Input_J") # Convert kWh to J
        )

    # Dynamically create arrays from default columns in DataFrame
    arrays = {
        name: np.array(model_df.select(name).to_series(), dtype=np.float64)
        for name in default_columns.keys()
    }

    # Original Arrays from DataFrame
    datetime_temp = np.array(model_df.select("Datetime").to_series())
    amb_temp = np.array(model_df.select("Ambient_Temperature_C").to_series())
    humidity = np.array(model_df.select("Relative_Humidity_Perc").to_series())

    # Specific arrays for each column
    battery_temp = arrays["Battery_Temp_C"]
    box_inner_temp = arrays["Box_Inner_Temp_C"]
    box_outer_temp = arrays["Box_Outer_Temp_C"]

    battery_heater_input = arrays["Battery_Heater_Input_J"]
    battery_losses_input = np.array(model_df.select("Battery_Losses_Input_J").to_series())
    battery_net_energy = np.array(model_df.select("Battery_Losses_Input_J").to_series())

    battery_cond_to_box_inner_energy = arrays["Battery_Cond_to_Box_Inner_Energy_J"]
    battery_conv_to_box_inner_energy = arrays["Battery_Conv_to_Box_Inner_Energy_J"]
    battery_radi_to_box_inner_energy = arrays["Battery_Radi_to_Box_Inner_Energy_J"]

    heater_to_battery_energy = arrays["Heater_to_Battery_Energy_J"]
    heater_to_box_inner_energy = arrays["Heater_to_Box_Inner_Energy_J"]

    box_inner_net_energy = arrays["Box_Inner_Net_Energy_J"]
    box_inner_cond_to_battery_energy = arrays["Box_Inner_Cond_to_Battery_Energy_J"]
    box_inner_conv_to_battery_energy = arrays["Box_Inner_Conv_to_Battery_Energy_J"]
    box_inner_radi_to_battery_energy = arrays["Box_Inner_Radi_to_Battery_Energy_J"]
    box_inner_to_box_outer_energy = arrays["Box_Inner_to_Box_Outer_Energy_J"]

    box_outer_net_energy = arrays["Box_Outer_Net_Energy_J"]
    box_outer_to_box_inner_energy = arrays["Box_Outer_to_Box_Inner_Energy_J"]
    box_outer_cond_to_environment_energy = arrays["Box_Outer_Cond_to_Environment_Energy_J"]
    box_outer_conv_to_environment_energy = arrays["Box_Outer_Conv_to_Environment_Energy_J"]
    box_outer_radi_to_environment_energy = arrays["Box_Outer_Radi_to_Environment_Energy_J"]
    box_outer_cond_from_environment_energy = arrays["Box_Outer_Cond_from_Environment_Energy_J"]
    box_outer_conv_from_environment_energy = arrays["Box_Outer_Conv_from_Environment_Energy_J"]
    box_outer_radi_from_environment_energy = arrays["Box_Radi_Conv_from_Environment_Energy_J"]

    (
        datetime_temp,
        amb_temp,
        humidity,
        battery_temp,
        box_inner_temp,
        box_outer_temp,
        battery_heater_input,
        battery_losses_input,
        battery_net_energy,
        battery_cond_to_box_inner_energy,
        battery_conv_to_box_inner_energy,
        battery_radi_to_box_inner_energy,
        heater_to_battery_energy,
        heater_to_box_inner_energy,
        box_inner_net_energy,
        box_inner_cond_to_battery_energy,
        box_inner_conv_to_battery_energy,
        box_inner_radi_to_battery_energy,
        box_inner_to_box_outer_energy,
        box_outer_net_energy,
        box_outer_to_box_inner_energy,
        box_outer_cond_to_environment_energy,
        box_outer_conv_to_environment_energy,
        box_outer_radi_to_environment_energy,
        box_outer_cond_from_environment_energy,
        box_outer_conv_from_environment_energy,
        box_outer_radi_from_environment_energy,
    ) = jit_battery_energy_flow_model(
        # Model Arrays
        datetime_temp,
        amb_temp,
        humidity,
        battery_temp,
        box_inner_temp,
        box_outer_temp,
        battery_heater_input,
        battery_losses_input,
        battery_net_energy,
        battery_cond_to_box_inner_energy,
        battery_conv_to_box_inner_energy,
        battery_radi_to_box_inner_energy,
        heater_to_battery_energy,
        heater_to_box_inner_energy,
        box_inner_net_energy,
        box_inner_cond_to_battery_energy,
        box_inner_conv_to_battery_energy,
        box_inner_radi_to_battery_energy,
        box_inner_to_box_outer_energy,
        box_outer_net_energy,
        box_outer_to_box_inner_energy,
        box_outer_cond_to_environment_energy,
        box_outer_conv_to_environment_energy,
        box_outer_radi_to_environment_energy,
        box_outer_cond_from_environment_energy,
        box_outer_conv_from_environment_energy,
        box_outer_radi_from_environment_energy,
        # Model Variables
        bucket_period_seconds,
        battery_mass_kg,
        battery_heat_capacity,
        total_battery_area,
        box_wall_mass_kg,
        box_heat_capacity,
        total_box_area,
        battery_conductive_resistance,
        battery_convective_resistance,
        box_composite_conductive_resistance,
        box_outer_conductive_resistance,
        box_outer_convective_resistance,
        heater_threshold_temp_c,
        use_heater,
        heater_power_j,
        heater_battery_transfer,
        heater_time_minutes,
        battery_emissivity,
        box_inner_emissivity,
        box_outer_emissivity,
        battery_throughput_losses,
    )

    # Remake the output DataFrame from the model results
    model_results_df = (
        pl.DataFrame(
            {
                "Datetime" : datetime_temp,
                "Ambient_Temperature_C" : amb_temp,
                "Relative_Humidity_Perc" : humidity,
                "Battery_Temp_C": battery_temp,
                "Box_Inner_Temp_C": box_inner_temp,
                "Box_Outer_Temp_C": box_outer_temp,
                "Battery_Heater_Input_J": battery_heater_input,
                "Battery_Losses_Input_J": battery_losses_input,
                "Battery_Net_Energy_J": battery_net_energy,
                "Battery_Cond_to_Box_Inner_Energy_J": battery_cond_to_box_inner_energy,
                "Battery_Conv_to_Box_Inner_Energy_J": battery_conv_to_box_inner_energy,
                "Battery_Radi_to_Box_Inner_Energy_J": battery_radi_to_box_inner_energy,
                "Heater_to_Battery_Energy_J": heater_to_battery_energy,
                "Heater_to_Wall_Energy_J": heater_to_box_inner_energy,
                "Box_Inner_Net_Energy_J": box_inner_net_energy,
                "Box_Inner_Cond_to_Battery_Energy_J": box_inner_cond_to_battery_energy,
                "Box_Inner_Conv_to_Battery_Energy_J": box_inner_conv_to_battery_energy,
                "Box_Inner_Radi_to_Battery_Energy_J": box_inner_radi_to_battery_energy,
                "Box_Inner_to_Box_Outer_Energy_J": box_inner_to_box_outer_energy,
                "Box_Outer_Net_Energy_J": box_outer_net_energy,
                "Box_Outer_to_Box_Inner_Energy_J": box_outer_to_box_inner_energy,
                "Box_Outer_Cond_to_Environment_Energy_J": box_outer_cond_to_environment_energy,
                "Box_Outer_Conv_to_Environment_Energy_J": box_outer_conv_to_environment_energy,
                "Box_Outer_Radi_to_Environment_Energy_J": box_outer_radi_to_environment_energy,
                "Box_Outer_Cond_from_Environment_Energy_J": box_outer_cond_from_environment_energy,
                "Box_Outer_Conv_from_Environment_Energy_J": box_outer_conv_from_environment_energy,
                "Box_Outer_Radi_from_Environment_Energy_J": box_outer_radi_from_environment_energy,
            }
        )
    )

    return model_results_df


@njit
def jit_battery_energy_flow_model(
    # Model Arrays
    datetime_temp: np.ndarray,
    amb_temp: np.ndarray,
    humidity: np.ndarray,
    battery_temp: np.ndarray,
    box_inner_temp: np.ndarray,
    box_outer_temp: np.ndarray,
    battery_heater_input: np.ndarray,
    battery_losses_input: np.ndarray,
    battery_net_energy: np.ndarray,
    battery_cond_to_box_inner_energy: np.ndarray,
    battery_conv_to_box_inner_energy: np.ndarray,
    battery_radi_to_box_inner_energy: np.ndarray,
    heater_to_battery_energy: np.ndarray,
    heater_to_box_inner_energy: np.ndarray,
    box_inner_net_energy: np.ndarray,
    box_inner_cond_to_battery_energy: np.ndarray,
    box_inner_conv_to_battery_energy: np.ndarray,
    box_inner_radi_to_battery_energy: np.ndarray,
    box_inner_to_box_outer_energy: np.ndarray,
    box_outer_net_energy: np.ndarray,
    box_outer_to_box_inner_energy: np.ndarray,
    box_outer_cond_to_environment_energy: np.ndarray,
    box_outer_conv_to_environment_energy: np.ndarray,
    box_outer_radi_to_environment_energy: np.ndarray,
    box_outer_cond_from_environment_energy: np.ndarray,
    box_outer_conv_from_environment_energy: np.ndarray,
    box_outer_radi_from_environment_energy: np.ndarray,

    # Model Parameters
    bucket_period_seconds: float,
    battery_mass_kg: float,
    battery_heat_capacity: float,
    total_battery_area: float,
    box_wall_mass_kg: float,
    box_heat_capacity: float,
    total_box_area: float,
    battery_conductive_resistance: float,
    battery_convective_resistance: float,
    box_composite_conductive_resistance: float,
    box_outer_conductive_resistance: float,
    box_outer_convective_resistance: float,
    heater_threshold_temp_c: float,
    use_heater: bool,
    heater_power_j: float,
    heater_battery_transfer: float,
    heater_time_minutes: int,
    battery_emissivity: float,
    box_inner_emissivity: float,
    box_outer_emissivity: float,
    battery_throughput_losses: float,
):

    # MODEL VARIABLES THAT NEED INITIALISED FROM ARRAYS FOR FIRST VALUE
    battery_temp_c = battery_temp[0]
    box_inner_temp_c = box_inner_temp[0]
    box_outer_temp_c = box_outer_temp[0]

    # Heater counter to simulate being on for a minimum period of time
    heater_on = False
    heater_counter = 0

    # Iterative calculation
    for i in range(len(datetime_temp)):
        # Check if heater is on, and ensure it is on for 30 minutes:
        if heater_on:
            if heater_counter < heater_time_minutes:
                heater_counter += 1
            else:
                heater_on = False
                heater_counter = 0

        # Need to calculate net energy flows into air, battery, box inner and outer wall, and environment
        # Temperature should be updated each time a flow is calculated to ensure next calculation is accurate

        # Calculate net energy flow from heater pad if threshold temperature triggered
        # (1) Calculate net energy flow into battery from throughput losses converted into heat (3%)
        # (2) If heater is on, the only conductive energy flow from battery to walls are the 20% losses from heating pad
        if box_inner_temp_c <= heater_threshold_temp_c and use_heater:
            heater_on = True
            heater_counter = 0

        if use_heater and heater_on:
            heater_battery_energy_j = heater_power_j * heater_battery_transfer
            heater_wall_energy_j = heater_power_j * (1-heater_battery_transfer)

            battery_heater_input[i] += heater_power_j
            battery_losses_input[i] += heater_power_j * battery_throughput_losses 
            battery_losses_input_energy_j = battery_losses_input[i]
            battery_total_heating_losses_energy_j = battery_losses_input_energy_j + heater_battery_energy_j

            battery_net_energy[i] += battery_total_heating_losses_energy_j
            box_inner_net_energy[i] += heater_wall_energy_j         # (2)
            heater_to_battery_energy[i] += heater_battery_energy_j
            heater_to_box_inner_energy[i] += heater_wall_energy_j

            battery_temp_c = calc_change_in_temperature_c(
                battery_temp_c, battery_total_heating_losses_energy_j, battery_heat_capacity, battery_mass_kg
                )
            box_inner_temp_c = calc_change_in_temperature_c(
                box_inner_temp_c, heater_wall_energy_j, box_heat_capacity, box_wall_mass_kg
                )
            
            heater_counter += 1

        # Calculate net energy flows from battery to air, and inner wall. Add 20% heating loss to inner wall if applicable
        # If heating pad is not on, standard conduction formula for battery to walls apply

        # If heater not on, calculate conductive energy flow to inner wall from battery
        if box_inner_temp_c > heater_threshold_temp_c:
            battery_cond_energy_flow_to_inner_wall_j = calculate_heat_energy_flow(
                battery_temp_c, box_inner_temp_c, battery_conductive_resistance, bucket_period_seconds
                )
            
            # Subtract so that Energy Flow is positive to indicate energy flowing away
            battery_cond_to_box_inner_energy[i] += battery_cond_energy_flow_to_inner_wall_j
            battery_net_energy[i] += -battery_cond_energy_flow_to_inner_wall_j

            box_inner_cond_to_battery_energy[i] += -battery_cond_energy_flow_to_inner_wall_j
            box_inner_net_energy[i] += battery_cond_energy_flow_to_inner_wall_j

            battery_temp_c = calc_change_in_temperature_c(
                battery_temp_c, -battery_cond_energy_flow_to_inner_wall_j, battery_heat_capacity, battery_mass_kg
                )
            box_inner_temp_c = calc_change_in_temperature_c(
                box_inner_temp_c, battery_cond_energy_flow_to_inner_wall_j, box_heat_capacity, box_wall_mass_kg
                )

        # Calculate convective energy flow to inner wall from battery
        battery_conv_energy_flow_to_inner_wall_j = calculate_heat_energy_flow(
                battery_temp_c, box_inner_temp_c, battery_convective_resistance, bucket_period_seconds
                )
        
        battery_temp_c = calc_change_in_temperature_c(
                battery_temp_c, -battery_conv_energy_flow_to_inner_wall_j, battery_heat_capacity, battery_mass_kg
                )
        box_inner_temp_c = calc_change_in_temperature_c(
            box_inner_temp_c, battery_conv_energy_flow_to_inner_wall_j, box_heat_capacity, box_wall_mass_kg
            )

        # Subtract so that Energy Flow is positive to indicate energy flowing away
        battery_conv_to_box_inner_energy[i] += battery_conv_energy_flow_to_inner_wall_j
        battery_net_energy[i] += -battery_conv_energy_flow_to_inner_wall_j

        box_inner_conv_to_battery_energy[i] += -battery_conv_energy_flow_to_inner_wall_j
        box_inner_net_energy[i] += battery_conv_energy_flow_to_inner_wall_j


        # Calculate Radiative energy exchange between battery and inner walls
        battery_radiative_energy_flow_to_inner_wall_j = calculate_inner_radiative_heat_flow(
            total_battery_area, total_box_area, battery_emissivity, box_inner_emissivity, battery_temp_c, box_inner_temp_c, bucket_period_seconds
        )

        battery_temp_c = calc_change_in_temperature_c(
                battery_temp_c, -battery_radiative_energy_flow_to_inner_wall_j, battery_heat_capacity, battery_mass_kg
                )
        box_inner_temp_c = calc_change_in_temperature_c(
            box_inner_temp_c, battery_radiative_energy_flow_to_inner_wall_j, box_heat_capacity, box_wall_mass_kg
            )

        # Subtract so that Energy Flow is positive to indicate energy flowing away
        battery_radi_to_box_inner_energy[i] += battery_radiative_energy_flow_to_inner_wall_j
        battery_net_energy[i] += -battery_radiative_energy_flow_to_inner_wall_j

        box_inner_radi_to_battery_energy[i] += -battery_radiative_energy_flow_to_inner_wall_j
        box_inner_net_energy[i] += battery_radiative_energy_flow_to_inner_wall_j


        # Calculate energy flow from inner wall to outer wall based on delta between temperatures and resistances
        # From this net change in energy update the inner and outer wall temperatures.
        inner_wall_cond_energy_flow_to_outer_wall_j = calculate_heat_energy_flow(
            box_inner_temp_c, box_outer_temp_c, box_composite_conductive_resistance, bucket_period_seconds
            )
        
        # Subtract so that Energy Flow is positive to indicate energy flowing away
        box_inner_to_box_outer_energy[i] += inner_wall_cond_energy_flow_to_outer_wall_j
        box_inner_net_energy[i] += -inner_wall_cond_energy_flow_to_outer_wall_j

        box_outer_to_box_inner_energy[i] += -inner_wall_cond_energy_flow_to_outer_wall_j
        box_outer_net_energy[i] += inner_wall_cond_energy_flow_to_outer_wall_j

        box_inner_temp_c = calc_change_in_temperature_c(
            box_inner_temp_c, -inner_wall_cond_energy_flow_to_outer_wall_j, box_heat_capacity, box_wall_mass_kg
            )
        box_outer_temp_c = calc_change_in_temperature_c(
            box_outer_temp_c, inner_wall_cond_energy_flow_to_outer_wall_j, box_heat_capacity, box_wall_mass_kg
            )


        # Then calculate the heat energy loss to the environment from the outer wall, and update the temperature of outer wall
        ambient_temperature = amb_temp[i]
        outer_wall_conv_energy_flow_to_environment_j = calculate_heat_energy_flow(
                box_outer_temp_c, ambient_temperature, box_outer_convective_resistance, bucket_period_seconds
                )
        outer_wall_cond_energy_flow_to_environment_j = calculate_heat_energy_flow(
                box_outer_temp_c, ambient_temperature, box_outer_conductive_resistance, bucket_period_seconds
                )
        outer_wall_radi_energy_flow_to_environment_j = calculate_outer_radiative_heat_flow(
            total_box_area, box_outer_emissivity, box_outer_temp_c, ambient_temperature, bucket_period_seconds
        )
        outer_wall_total_flow_to_environment_j = (
            outer_wall_conv_energy_flow_to_environment_j 
            + outer_wall_cond_energy_flow_to_environment_j
            + outer_wall_radi_energy_flow_to_environment_j
            )
        
        box_outer_temp_c = calc_change_in_temperature_c(
                box_outer_temp_c, -outer_wall_total_flow_to_environment_j, box_heat_capacity, box_wall_mass_kg
                )

        # Subtract so that Energy Flow is positive to indicate energy flowing away
        box_outer_conv_to_environment_energy[i] += outer_wall_conv_energy_flow_to_environment_j
        box_outer_conv_from_environment_energy[i] += -outer_wall_conv_energy_flow_to_environment_j
        box_outer_cond_to_environment_energy[i] += outer_wall_cond_energy_flow_to_environment_j
        box_outer_cond_from_environment_energy[i] += -outer_wall_cond_energy_flow_to_environment_j
        box_outer_radi_to_environment_energy[i] += outer_wall_radi_energy_flow_to_environment_j
        box_outer_radi_from_environment_energy[i] += -outer_wall_radi_energy_flow_to_environment_j
        box_outer_net_energy[i] += outer_wall_total_flow_to_environment_j


        # Loop through the process for each row.

        battery_temp[i] = battery_temp_c
        box_inner_temp[i] = box_inner_temp_c
        box_outer_temp[i] = box_outer_temp_c

    return (
        datetime_temp,
        amb_temp,
        humidity,
        battery_temp,
        box_inner_temp,
        box_outer_temp,
        battery_heater_input,
        battery_losses_input,
        battery_net_energy,
        battery_cond_to_box_inner_energy,
        battery_conv_to_box_inner_energy,
        battery_radi_to_box_inner_energy,
        heater_to_battery_energy,
        heater_to_box_inner_energy,
        box_inner_net_energy,
        box_inner_cond_to_battery_energy,
        box_inner_conv_to_battery_energy,
        box_inner_radi_to_battery_energy,
        box_inner_to_box_outer_energy,
        box_outer_net_energy,
        box_outer_to_box_inner_energy,
        box_outer_cond_to_environment_energy,
        box_outer_conv_to_environment_energy,
        box_outer_radi_to_environment_energy,
        box_outer_cond_from_environment_energy,
        box_outer_conv_from_environment_energy,
        box_outer_radi_from_environment_energy,
    )
