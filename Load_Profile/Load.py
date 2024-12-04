from dataclasses import dataclass, field
import polars as pl

from Load_Profile.load_profile import initialise_load

@dataclass
class Load:
    daily_electric: float = 9.91
    daily_variablity: float = 0.15
    timestep_variability: float = 0.1
    profile: str = "Domestic"
    country: str = "UK"
    annual_electric: float = None
    load_profile_path: str = None
    load_profile: pl.DataFrame = field(default=None, init=True)
    interopolated_load_profile: pl.DataFrame = field(default=None, init=True)

    def __post_init__(self):
        """
        Post-initialization method.
        """
        initialise_load(self)