import httpx
import polars as pl
from pathlib import Path

from datetime import datetime

def get_tmy_data(
    data_file_path: str = None,
    latitude: float = None,
    longitude: float = None,
) -> pl.DataFrame:

    if data_file_path:
        file = Path(data_file_path)
        if file.exists():
            tmy_data = pl.read_parquet(data_file_path)
            return tmy_data
        else:
            if latitude and longitude:
                tmy_data = get_tmy_data_pvgis(
                    latitude=latitude,
                    longitude=longitude,
                )
                return tmy_data
            else:
                return "No Latitude or Longitude values provided"


def get_tmy_data_pvgis(
    latitude: float,
    longitude: float,
    data_file_path: str = None,
):

    tmy_link = f"https://re.jrc.ec.europa.eu/api/tmy?lat={latitude}&lon={longitude}&outputformat=json"

    request = httpx.get(tmy_link).json()["outputs"]["tmy_hourly"]
    response = pl.from_dicts(request)

    if data_file_path is None:
        latitude_save = f"{latitude:.2f}"
        longitude_save = f"{longitude:.2f}"
        data_file_path = f"TMY_Data/Data/{latitude_save}_{longitude_save}_tmy_data.parquet"

    response.write_parquet(data_file_path)
    return response


def interpolate_tmy_dataframe(
        tmy_data_df: pl.DataFrame,
        interpolation_time_interval: str = "1m",
        ) -> pl.DataFrame:
    # Generate datetime ranges
    datetime_range_1m = pl.datetime_range(
        start=datetime(2025, 1, 1, 0, 0, 0),
        end=datetime(2025, 12, 31, 23, 59, 0),
        interval=interpolation_time_interval,
        eager=True,
    )

    datetime_range_1h = pl.datetime_range(
        start=datetime(2025, 1, 1, 0, 0, 0),
        end=datetime(2025, 12, 31, 23, 0, 0),
        interval="1h",
        eager=True,
    )

    # Add the 'Time' column to both DataFrames
    testy_dates_df = pl.DataFrame({"Datetime": datetime_range_1m})
    tmy_data_df = tmy_data_df.with_columns(datetime_range_1h.alias("Datetime"))

    # Perform left join
    tmy_data_df = testy_dates_df.join(tmy_data_df, on="Datetime", how="left").drop(
        "time(UTC)"
    )  # Adjust this column name based on your data

    # Select the first row
    first_row = tmy_data_df.head(1)

    # Update the 'Time' value to '2026-01-01 00:00:00'
    new_row = first_row.with_columns(
        pl.lit(datetime(2026, 1, 1, 0, 0, 0)).alias("Datetime")
    )

    # Append the new row to the DataFrame
    tmy_data_df = tmy_data_df.vstack(new_row)

    # Interpolate the DataFrame
    tmy_data_df = tmy_data_df.interpolate().filter(pl.col("Datetime").dt.year() != 2026)

    return tmy_data_df


def clean_tmy_data(tmy_data_df: pl.DataFrame) -> pl.DataFrame:
    tmy_data_df = (
        tmy_data_df.drop(
            [
                "SP",
                "WD10m",
                "WS10m",
                "IR(h)",
                "G(h)",
                "Gb(n)",
                "Gd(h)",
            ]
        )
        .with_columns(pl.col(pl.Float64).cast(pl.Float32))
        .rename(
            {
                "T2m": "Ambient_Temperature_C",
                "RH": "Relative_Humidity_Perc",
            }
        )
    )
    return tmy_data_df


def get_processed_tmy_data(
        data_file_path: str,
        latitude: float = None,
        longitude: float = None,
        interpolation_time_interval: str = "1m",
        ) -> pl.DataFrame:
    
    # Load TMY DataFrame
    tmy_data_df = get_tmy_data(
        data_file_path=data_file_path,
        latitude=latitude, 
        longitude=longitude
        )

    # Interpolate data from 1hr to 1minute increments
    tmy_data_df = interpolate_tmy_dataframe(
        tmy_data_df=tmy_data_df,
        interpolation_time_interval=interpolation_time_interval,
        )

    # Clean TMY dataframe
    tmy_data_df = clean_tmy_data(tmy_data_df)

    return tmy_data_df
