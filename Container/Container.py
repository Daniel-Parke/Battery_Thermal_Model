from dataclasses import dataclass
from typing import List, Tuple, Optional
import polars as pl



@dataclass
class Container:
    box_length: float = 1.0
    box_width: float = 0.7
    box_height: float = 0.4
    inner_material: str = "Polystyrene"
    outer_material: str = "Wood"
    inner_material_thickness_m: float = 0.01
    outer_material_thickness_m: float = 0.01
    inner_material_params: Tuple[float, float, float, float, float] = None
    outer_material_params: Tuple[float, float, float, float, float] = None
    material_list: List[Tuple[float, float, float, float, float]] = None
    box_transfer_array: List[int] = (0, 1, 1, 1, 1, 1)

    def __post_init__(self):
        material_list_df = pl.read_csv("Container/data/material_list.csv")
        inner_material_df = material_list_df.filter(material=self.inner_material.lower())
        outer_material_df = material_list_df.filter(material=self.outer_material.lower())

        self.inner_material_params = (
            self.inner_material_thickness_m,
            inner_material_df.select("thermal_conductivity").item(),
            inner_material_df.select("heat_capacity").item(),
            inner_material_df.select("density").item(),
            inner_material_df.select("emissivity").item(),
        )

        self.outer_material_params = (
            self.outer_material_thickness_m,
            outer_material_df.select("thermal_conductivity").item(),
            outer_material_df.select("heat_capacity").item(),
            outer_material_df.select("density").item(),
            outer_material_df.select("emissivity").item(),
        )

        self.material_list = [self.inner_material_params, self.outer_material_params]
