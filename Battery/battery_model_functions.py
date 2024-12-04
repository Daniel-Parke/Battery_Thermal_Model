def calculate_volume(length: float, width: float, height: float) -> float:
    """
    Calculate the volume of an object.

    Args:
        length_m (float): Length of the object in meters (m).
        width_m (float): Width of the object in meters (m).
        height_m (float): Height of the object in meters (m).

    Returns:
        float: Volume in cubic meters (m³).
    """
    volume = length * width * height
    return volume


def calculate_mass(density: float, volume: float) -> float:
    """
    Calculate the mass of a material from its density and volume.

    Args:
        density (float): Density of the material in kg/m³.
        volume (float): Volume of the material in cubic meters (m³).

    Returns:
        float: Mass in kilograms (kg).
    """
    mass = density * volume  # m = ρ * V
    return mass


def calculate_face_areas(
    length: float, width: float, height: float
) -> tuple[float, float, float]:
    """
    Calculate the areas of the faces of a cuboid.

    Parameters:
    - length: Length of the cuboid.
    - width: Width of the cuboid.
    - height: Height of the cuboid.

    Returns:
    - Tuple containing:
      - Top/bottom area (length * width).
      - Side area along height and length (height * length).
      - Side area along height and width (height * width).
    """
    length_width = length * width  # Top/Bottom area
    height_length = height * length  # Height x Length area
    height_width = height * width  # Height x Width area
    return length_width, height_length, height_width


def calculate_heat_transfer_areas(
    battery_length: float,
    battery_width: float,
    battery_height: float,
    box_length: float,
    box_width: float,
    box_height: float,
    battery_transfer_array: list[int],
    box_transfer_array: list[int],
) -> tuple[float, float, float, float]:
    """
    Calculate the conductive and convective areas of the battery and the box.

    Parameters:
    - battery_length: Length of the battery.
    - battery_width: Width of the battery.
    - battery_height: Height of the battery.
    - box_length: Length of the box.
    - box_width: Width of the box.
    - box_height: Height of the box.
    - battery_transfer_array: Array indicating which parts of the battery are in contact with the ground (0)
      or air (1). Format: [Bottom, Top, long_side_1, long_side_2, short_side_1, short_side_2].
    - box_transfer_array: Array indicating how each face of the box interacts with the environment (0 = ground, 1 = air).

    Returns:
    - Tuple containing:
      - Battery conductive area (m²).
      - Battery convective area (m²).
      - Box conductive area (m²).
      - Box convective area (m²).
    """
    # Calculate face areas for the battery and box
    Bat_TopBottom, Bat_HeightLength_Side, Bat_HeightWidth_Side = calculate_face_areas(
        length=battery_length,
        width=battery_width,
        height=battery_height,
    )
    Box_TopBottom, Box_HeightLength_Side, Box_HeightWidth_Side = calculate_face_areas(
        length=box_length,
        width=box_width,
        height=box_height,
    )

    battery_volume = calculate_volume(battery_length, battery_width, battery_height)
    box_volume = calculate_volume(box_length, box_width, box_height)

    # Define areas of the battery and box faces
    battery_face_areas = [
        Bat_TopBottom,  # Bottom face
        Bat_TopBottom,  # Top face
        Bat_HeightLength_Side,  # Long side 1
        Bat_HeightLength_Side,  # Long side 2
        Bat_HeightWidth_Side,  # Short side 1
        Bat_HeightWidth_Side,  # Short side 2
    ]
    box_face_areas = [
        Box_TopBottom,  # Bottom face
        Box_TopBottom,  # Top face
        Box_HeightLength_Side,  # Long side 1
        Box_HeightLength_Side,  # Long side 2
        Box_HeightWidth_Side,  # Short side 1
        Box_HeightWidth_Side,  # Short side 2
    ]

    # Initialize areas for battery and box
    battery_conductive_area_m2 = 0
    battery_convective_area_m2 = 0
    box_conductive_area_m2 = 0
    box_convective_area_m2 = 0
    air_convective_area_m2 = 0

    # If Battery completely fills box then set all walls to touching box
    if battery_volume == box_volume:
        battery_transfer_array = [0, 0, 0, 0, 0, 0] 

    # Calculate battery conductive and convective areas
    for i, transfer_type in enumerate(battery_transfer_array):
        if transfer_type == 0:  # Ground contact
            battery_conductive_area_m2 += battery_face_areas[i]
        elif transfer_type == 1:  # Air contact
            battery_convective_area_m2 += battery_face_areas[i]

    # Calculate box conductive and convective areas
    for i, transfer_type in enumerate(box_transfer_array):
        if transfer_type == 0:  # Ground contact
            box_conductive_area_m2 += box_face_areas[i]
        elif transfer_type == 1:  # Air contact
            box_convective_area_m2 += box_face_areas[i]

    # Calculate air conductive and convective areas
    for i, transfer_type in enumerate(box_transfer_array):
        if transfer_type == 0:  # Ground contact
            if battery_transfer_array[i] == 0:
                air_convective_area_m2 += box_face_areas[i] - battery_face_areas[i]
            elif battery_transfer_array[i] == 1:
                air_convective_area_m2 += box_face_areas[i]

        elif transfer_type == 1:  # Air contact
            if battery_transfer_array[i] == 0:
                air_convective_area_m2 += box_face_areas[i] - battery_face_areas[i]
            elif battery_transfer_array[i] == 1:
                air_convective_area_m2 += box_face_areas[i]

    return (
        battery_conductive_area_m2,
        battery_convective_area_m2,
        air_convective_area_m2,
        box_conductive_area_m2,
        box_convective_area_m2,
    )
