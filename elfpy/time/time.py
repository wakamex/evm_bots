"""Helper functions for converting time units"""

from dataclasses import dataclass

import numpy as np

import elfpy.types as types


@dataclass
class BlockTime:
    r"""Global time."""

    time_in_years: float = 0
    block_number: float = 0

    @property
    def time_in_seconds(self) -> float:
        """1 year = 31,556,952 seconds"""
        return self.time_in_years * 31_556_952

    def tick(self, delta_years: float) -> None:
        """ticks the time by delta_time amount"""
        self.time_in_years += delta_years


@types.freezable(frozen=True, no_new_attribs=True)
@dataclass
class StretchedTime:
    r"""Stores time in units of days, as well as normalized & stretched variants

    .. todo:: Improve this constructor so that StretchedTime can be constructed from years.
    """
    days: float
    time_stretch: float
    normalizing_constant: float

    @property
    def stretched_time(self):
        r"""Returns days / normalizing_constant / time_stretch"""
        return days_to_time_remaining(self.days, self.time_stretch, normalizing_constant=self.normalizing_constant)

    @property
    def normalized_time(self):
        r"""Format time as normalized days"""
        return norm_days(
            self.days,
            self.normalizing_constant,
        )


def get_years_remaining(market_time: float, mint_time: float, position_duration_years: float) -> float:
    r"""Get the time remaining in years on a token

    Parameters
    ----------
    market_time : float
        Time that has elapsed in the given market, in years
    mint_time : float
        Time at which the token in question was minted, relative to market_time,
        in yearss. Should be less than market_time.
    position_duration_years: float
        Total duration of the token's term, in years

    Returns
    -------
    float
        Time left until token maturity, in years
    """
    if mint_time > market_time:
        raise ValueError(f"elfpy.utils.time.get_years_remaining: ERROR: {mint_time=} must be less than {market_time=}.")
    years_elapsed = market_time - mint_time
    # if we are closing after the position duration has completed, then just set time_remaining to zero
    time_remaining = np.maximum(position_duration_years - years_elapsed, 0)
    return time_remaining


def norm_days(days: float, normalizing_constant: float = 365) -> float:
    r"""Returns days normalized, with a default assumption of a year-long scale

    Parameters
    ----------
    days : float
        Amount of days to normalize
    normalizing_constant : float
        Amount of days to use as a normalization factor. Defaults to 365

    Returns
    -------
    float
        Amount of days provided, converted to fractions of a year
    """
    return days / normalizing_constant


def unnorm_days(normed_days: float, normalizing_constant: float = 365) -> float:
    r"""Returns days from a value between 0 and 1

    Parameters
    ----------
    normed_days : float
        Normalized amount of days, according to a normalizing constant
    normalizing_constant : float
        Amount of days to use as a normalization factor. Defaults to 365

    Returns
    -------
    float
        Amount of days, calculated from the provided parameters
    """
    return normed_days * normalizing_constant


def days_to_time_remaining(days_remaining: float, time_stretch: float = 1, normalizing_constant: float = 365) -> float:
    r"""Converts remaining pool length in days to normalized and stretched time

    Parameters
    ----------
    days_remaining : float
        Time left until term maturity, in days
    time_stretch : float
        Amount of time units (in terms of a normalizing constant) to use for stretching time, for calculations
        Defaults to 1
    normalizing_constant : float
        Amount of days to use as a normalization factor
        Defaults to 365

    Returns
    -------
    float
        Time remaining until term maturity, in normalized and stretched time
    """
    normed_days_remaining = norm_days(days_remaining, normalizing_constant)
    return normed_days_remaining / time_stretch


def time_to_days_remaining(time_remaining: float, time_stretch: float = 1, normalizing_constant: float = 365) -> float:
    r"""Converts normalized and stretched time remaining in pool to days

    Parameters
    ----------
    time_remaining : float
        Time left until term maturity, in normalized and stretched time
    time_stretch : float
        Amount of time units (in terms of a normalizing constant) to use for stretching time, for calculations
        Defaults to 1
    normalizing_constant : float
        Amount of days to use as a normalization factor. Defaults to 365

    Returns
    -------
    float
        Time remaining until term maturity, in days
    """
    normed_days_remaining = time_remaining * time_stretch
    return unnorm_days(normed_days_remaining, normalizing_constant)