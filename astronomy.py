"""Astronomical calculation module for 月相羅針 計算PoC v0.6.

This module is intentionally separated from the provisional 月相羅針
classification logic. It converts local Japanese birth times to UTC and
calculates geocentric tropical longitudes of the Sun and Moon with
pyswisseph.

The day-range calculation introduced in PoC v0.2 is retained for cases where the birth time is
unknown. It does not decide the proprietary 月相羅針 classification; it only
returns astronomical values for multiple local times within the birth date.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import swisseph as swe


class AstronomyError(RuntimeError):
    """Raised when an astronomical calculation cannot be completed."""


def normalize_angle(angle: float) -> float:
    """Normalize an angle to the range 0 <= angle < 360 degrees."""
    return float(angle) % 360.0


def _get_timezone(timezone_name: str) -> ZoneInfo:
    """Resolve an IANA time-zone name or raise a user-facing ValueError."""
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError("指定されたタイムゾーンを利用できません。") from exc


def local_datetime_to_utc(
    birth_date: str,
    birth_time: str,
    timezone_name: str,
) -> tuple[datetime, datetime]:
    """Parse local birth date/time and convert it to UTC.

    Parameters are strings from the HTML date/time inputs (YYYY-MM-DD, HH:MM)
    and an IANA time-zone name such as Asia/Tokyo.
    """
    try:
        local_naive = datetime.strptime(
            f"{birth_date} {birth_time}", "%Y-%m-%d %H:%M"
        )
    except ValueError as exc:
        raise ValueError("生年月日または出生時間の形式が正しくありません。") from exc

    tz = _get_timezone(timezone_name)
    local_dt = local_naive.replace(tzinfo=tz)
    utc_dt = local_dt.astimezone(timezone.utc)
    return local_dt, utc_dt


def datetime_utc_to_julian_day(utc_dt: datetime) -> float:
    """Convert a timezone-aware UTC datetime to Julian Day (UT)."""
    if utc_dt.tzinfo is None:
        raise ValueError("UTC日時にはタイムゾーン情報が必要です。")

    utc_dt = utc_dt.astimezone(timezone.utc)
    decimal_hour = (
        utc_dt.hour
        + utc_dt.minute / 60.0
        + utc_dt.second / 3600.0
        + utc_dt.microsecond / 3_600_000_000.0
    )
    return swe.julday(
        utc_dt.year,
        utc_dt.month,
        utc_dt.day,
        decimal_hour,
        swe.GREG_CAL,
    )


def _ephemeris_mode_label(return_flags: int) -> str:
    """Return a human-readable label for the ephemeris actually used."""
    if return_flags & swe.FLG_JPLEPH:
        return "JPL ephemeris via Swiss Ephemeris"
    if return_flags & swe.FLG_SWIEPH:
        return "Swiss Ephemeris"
    if return_flags & swe.FLG_MOSEPH:
        return "Moshier fallback via Swiss Ephemeris"
    return "Swiss Ephemeris / pyswisseph"


def calculate_longitudes(julian_day_ut: float) -> dict[str, float | str]:
    """Calculate geocentric tropical Sun/Moon ecliptic longitudes.

    No sidereal flag and no topocentric flag are set, so the result is the
    default tropical, geocentric ecliptic longitude requested for this PoC.

    FLG_SWIEPH is requested. If external Swiss Ephemeris data files are not
    present, the library may transparently fall back to its Moshier mode; this
    is reported in the returned metadata so the calculation method is visible.
    """
    try:
        requested_flags = swe.FLG_SWIEPH
        sun_data, sun_flags = swe.calc_ut(julian_day_ut, swe.SUN, requested_flags)
        moon_data, moon_flags = swe.calc_ut(julian_day_ut, swe.MOON, requested_flags)
    except Exception as exc:  # pyswisseph can raise several low-level errors
        raise AstronomyError("太陽・月の天体計算に失敗しました。") from exc

    sun_longitude = normalize_angle(sun_data[0])
    moon_longitude = normalize_angle(moon_data[0])
    angle_difference = normalize_angle(moon_longitude - sun_longitude)

    return {
        "sun_longitude": sun_longitude,
        "moon_longitude": moon_longitude,
        "angle_difference": angle_difference,
        "sun_ephemeris_mode": _ephemeris_mode_label(sun_flags),
        "moon_ephemeris_mode": _ephemeris_mode_label(moon_flags),
    }


def calculate_local_datetime_astronomy(local_dt: datetime) -> dict[str, object]:
    """Calculate astronomy for one timezone-aware local datetime."""
    if local_dt.tzinfo is None:
        raise ValueError("現地日時にはタイムゾーン情報が必要です。")

    utc_dt = local_dt.astimezone(timezone.utc)
    julian_day = datetime_utc_to_julian_day(utc_dt)
    values = calculate_longitudes(julian_day)

    return {
        "local_datetime": local_dt,
        "utc_datetime": utc_dt,
        "julian_day": julian_day,
        **values,
    }


def calculate_birth_astronomy(
    birth_date: str,
    birth_time: str,
    timezone_name: str,
) -> dict[str, object]:
    """Run the complete known-birth-time astronomy calculation pipeline."""
    local_dt, _utc_dt = local_datetime_to_utc(
        birth_date=birth_date,
        birth_time=birth_time,
        timezone_name=timezone_name,
    )
    return calculate_local_datetime_astronomy(local_dt)


def calculate_birth_date_astronomy(
    birth_date: str,
    timezone_name: str,
    interval_minutes: int = 30,
) -> dict[str, object]:
    """Calculate multiple astronomy points across a birth date.

    This function is used only when the birth time is unknown. The local date
    is sampled from 00:00:00 through 23:59:59. A 30-minute interval is the
    PoC v0.2 default, and the final 23:59:59 point is always included.

    The returned samples remain purely astronomical data. Classification into
    P01-P08 is intentionally left to ``phase_classifier.py`` so the future
    proprietary 月相羅針 rules can be replaced independently.
    """
    if interval_minutes <= 0 or interval_minutes > 24 * 60:
        raise ValueError("日内計算の間隔は1分以上1440分以下で指定してください。")

    try:
        birth_day = datetime.strptime(birth_date, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("生年月日の形式が正しくありません。") from exc

    tz = _get_timezone(timezone_name)
    start_local = datetime(
        birth_day.year, birth_day.month, birth_day.day, 0, 0, 0, tzinfo=tz
    )
    end_local = datetime(
        birth_day.year, birth_day.month, birth_day.day, 23, 59, 59, tzinfo=tz
    )

    samples: list[dict[str, object]] = []
    current = start_local
    step = timedelta(minutes=interval_minutes)

    while current < end_local:
        samples.append(calculate_local_datetime_astronomy(current))
        current += step

    # Ensure the exact end of the local birth date is always checked.
    samples.append(calculate_local_datetime_astronomy(end_local))

    return {
        "birth_date": birth_date,
        "timezone": timezone_name,
        "start_local_datetime": start_local,
        "end_local_datetime": end_local,
        "interval_minutes": interval_minutes,
        "samples": samples,
        "angle_differences": [
            float(sample["angle_difference"]) for sample in samples
        ],
    }
