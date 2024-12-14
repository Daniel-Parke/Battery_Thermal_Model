import logging

import polars as pl
import numpy as np

from datetime import datetime
from pathlib import Path

# Set base Path for appending later
base_dir = Path(__file__).parent.parent


def calc_load_profile(
    daily_demand: float = 9.91,
    daily_std: float = 0.2,
    hourly_std: float = 0.1,
    profile: str = "Domestic",
    country: str = "UK",
) -> pl.DataFrame:
    """
    Function to calculate an annual load profile with hourly variability.
    """
    # Set Load Profile CSV Path
    load_profile_path = (
        base_dir
        / "demand"
        / "load_profiles"
        / f"{country}_{profile}_load_profile_hourly.csv"
    )

    # Try to read in an existing load profile based on the inputs
    try:
        load_data = pl.read_csv(load_profile_path, dtypes={"Datetime": pl.Datetime})

    # If the file cannot be found generate a new load profile
    except FileNotFoundError:
        logging.info(
            f"Unable to find load profile with chosen input parameters, generating new profile"
        )
        # Create a new date range for the load profile
        load_data = pl.DataFrame(
            {
                "Datetime": pl.datetime_range(
                    start=datetime(2025, 1, 1, 0, 0, 0),
                    end=datetime(2025, 12, 31, 23, 0, 0),
                    interval="1h",
                    eager=True,
                )
            }
        )
        # Generate a primary load profile with constant energy use per hour
        load_data = load_data.with_columns(
            pl.lit(daily_demand / 365).alias("Energy_Use_kWh_Base")
        )

    # Ensure 'Datetime' is of Datetime type
    load_data = load_data.with_columns(
        pl.col("Datetime").cast(pl.Datetime("ns")).alias("Datetime")
    )

    # Create two extra columns to store the daily and hourly perturbation
    load_data = load_data.with_columns(
        [
            pl.lit(0).alias("Energy_Use_kWh"),
            pl.lit(0).alias("Variability_Factor"),
        ]
    )

    # Scale energy use relative to base profile, original profile represents 9.91kWh daily use
    scale_factor = daily_demand / (load_data["Energy_Use_kWh_Base"].sum() / 365)
    load_data = load_data.with_columns(
        (pl.col("Energy_Use_kWh_Base") * scale_factor).alias("Energy_Use_kWh_Base")
    )

    # Generate daily perturbation values for each day
    load_data = load_data.with_columns(
        pl.col("Datetime").dt.truncate("1d").alias("Date")
    )
    dates = load_data.select("Date").unique()
    number_of_days = dates.height

    daily_deviation_values = np.random.normal(0, daily_std, size=number_of_days)
    daily_deviation_df = pl.DataFrame(
        {"Date": dates["Date"], "Daily_Deviation": daily_deviation_values}
    )

    # Map daily perturbation values to each hour of the corresponding day
    load_data = load_data.join(daily_deviation_df, on="Date", how="left")

    # Generate hourly perturbation values
    hourly_deviation_values = np.random.normal(0, hourly_std, size=load_data.height)
    load_data = load_data.with_columns(
        pl.Series(name="Hourly_Deviation", values=hourly_deviation_values)
    )

    load_data = load_data.with_columns(
        (1 + pl.col("Daily_Deviation") + pl.col("Hourly_Deviation")).alias(
            "Variability_Factor"
        )
    )

    # Apply the combined perturbation to the primary load
    load_data = load_data.with_columns(
        (pl.col("Energy_Use_kWh_Base") * pl.col("Variability_Factor")).alias(
            "Energy_Use_kWh"
        )
    )

    # Drop the extra columns to leave only the adjusted load
    load_data = load_data.drop(["Daily_Deviation", "Hourly_Deviation", "Date"])

    return load_data


# Model annual load profile incorporating variability, save these values to daily and annual demand values.
def initialise_load(self):
    """
    Function to initialise the load profile and set the daily and annual electricity values.
    [Docstring remains the same]
    """
    # Calculate Load Profile and return dataframe
    if self.load_profile_path is not None:
        lp_data = pl.read_csv(
            self.load_profile_path,
            dtypes={"Datetime": pl.Datetime},  # Ensure 'Datetime' is read as Datetime
        )
        self.load_profile = convert_to_hourly(lp_data)

    if self.load_profile is None:
        self.load_profile = calc_load_profile(
            daily_demand=self.daily_electric,
            daily_std=self.daily_variablity,
            hourly_std=self.timestep_variability,
            profile=self.profile,
            country=self.country,
        )

    # Set new daily and annual values to reflect variability calculations updating values
    self.daily_electric = round(self.load_profile["Energy_Use_kWh"].sum() / 365, 3)
    self.annual_electric = self.daily_electric * 365

    self.interopolated_load_profile = interpolate_load_profile(
        self.load_profile,
        self.interpolation_time_interval,
        )

    logging.info(
        f"Load Profile Generated: Daily Electricity Use: {self.daily_electric}kWh, "
        f"Annual Electricity Use: {self.annual_electric}kWh, Daily Variability: {self.daily_variablity*100}%, "
        f"Hourly Variability: {self.timestep_variability*100}% "
    )
    logging.info("*******************")


def drop_leap_days(data: pl.DataFrame) -> pl.DataFrame:
    """
    Function to drop leap days from a polars DataFrame.
    [Docstring remains the same]
    """
    if "Date" in data.columns:
        date_col = "Date"
    elif "Datetime" in data.columns:
        date_col = "Datetime"
    else:
        raise ValueError("Data must have 'Date' or 'Datetime' column")

    data = data.filter(
        ~((pl.col(date_col).dt.month() == 2) & (pl.col(date_col).dt.day() == 29))
    )
    return data


# Converts 30 min smart meter data into hourly series
def convert_to_hourly(data: pl.DataFrame) -> pl.DataFrame:
    """
    Converts a dataframe with 30-minute smart meter data into hourly values.
    [Docstring remains the same]
    """
    columns = data.columns[1:]
    column_pairs = list(zip(columns[::2], columns[1::2]))

    exprs = []
    for idx, (col1, col2) in enumerate(column_pairs):
        expr = ((pl.col(col1) + pl.col(col2)) / 2).alias(f"Hour {idx}")
        exprs.append(expr)

    data_hourly = data.select([pl.col("Date"), *exprs])
    data_hourly = data_hourly.with_columns(pl.col("Date").str.to_date().alias("Date"))
    data_hourly = drop_leap_days(data_hourly)

    # Melt the DataFrame to go from wide to long format
    melted_data = data_hourly.melt(
        id_vars=["Date"],
        variable_name="Hour",
        value_name="Energy_Use_kWh",
    )

    # Extract the 'Hour' number and create 'Datetime' column
    melted_data = melted_data.with_columns(
        [
            pl.col("Hour").str.extract(r"Hour (\d+)", 1).cast(pl.Int32()).alias("Hour"),
            (
                pl.col("Date").cast(pl.Datetime("ns"))
                + pl.duration(hours=pl.col("Hour"))
            ).alias("Datetime"),
        ]
    )

    # Arrange dataframe into annual values instead of chronological
    melted_data = melted_data.with_columns(
        pl.col("Datetime").dt.strftime("%m-%d").alias("Month_Day")
    )
    melted_data = melted_data.sort("Month_Day")
    melted_data = melted_data.drop(["Month_Day", "Date", "Hour"])

    return melted_data


def interpolate_load_profile(
        load_profile_df: pl.DataFrame,
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
    load_profile_df = load_profile_df.with_columns(datetime_range_1h.alias("Datetime"))

    # Perform left join
    load_profile_df = testy_dates_df.join(
        load_profile_df, on="Datetime", how="left"
    )

    # Select the first row
    first_row = load_profile_df.head(1)

    # Update the 'Time' value to '2026-01-01 00:00:00'
    new_row = first_row.with_columns(
        pl.lit(datetime(2026, 1, 1, 0, 0, 0)).alias("Datetime")
    )

    # Append the new row to the DataFrame
    load_profile_df = load_profile_df.vstack(new_row)

    if interpolation_time_interval == "1h":
        energy_division_factor = 1
    elif interpolation_time_interval == "1m":
        energy_division_factor = 60
    elif interpolation_time_interval == "1s":
        energy_division_factor = 3600
    else:
        energy_division_factor = 60

    # Interpolate the DataFrame
    load_profile_df = load_profile_df.interpolate().filter(
        pl.col("Datetime").dt.year() != 2026
    ).with_columns(
        # Divide by energy_division_factor account for time conversion
        pl.col("Energy_Use_kWh_Base") / energy_division_factor,
        pl.col("Energy_Use_kWh") / energy_division_factor,
    )

    return load_profile_df
