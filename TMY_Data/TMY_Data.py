from dataclasses import dataclass
import polars as pl

from TMY_Data.get_tmy_data import get_processed_tmy_data
from Load_Profile.Load import Load


@dataclass
class TMY_Data:
    latitude: float = 54.60283612642
    longitude: float = -5.9324865926
    interpolation_time_interval: str = "1h"
    data_file_path: str = None
    tmy_data_df: pl.DataFrame = None
    load: 'Load' = None
    load_profile_df: pl.DataFrame = None
    bucket_period_seconds: float = None


    def __post_init__(self):
        if self.data_file_path is None:
            self.data_file_path = (
                f"TMY_Data/Data/{self.latitude:.2f}_{self.longitude:.2f}_tmy_data.parquet"
                )

        self.tmy_data_df = get_processed_tmy_data(
            data_file_path=self.data_file_path,
            latitude=self.latitude,
            longitude=self.longitude,
            interpolation_time_interval=self.interpolation_time_interval
            )

        if self.load is None:
            self.load = Load(
                daily_electric=9.91,
                profile="Domestic",
                country="UK",
                interpolation_time_interval=self.interpolation_time_interval,
                )

        if self.load_profile_df is None:
            self.load_profile_df = self.load.interopolated_load_profile

        self.tmy_data_df = self.tmy_data_df.join(self.load_profile_df, on="Datetime")
        self.bucket_period_seconds = self.tmy_data_df.with_columns(
            (pl.col("Datetime").diff())
            )["Datetime"][1].total_seconds()
