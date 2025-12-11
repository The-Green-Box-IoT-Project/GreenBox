from typing import Optional


class Queries(object):
    """
    Predefined queries to be used with InfluxDBAdapter.
    """

    METRICS = {
        "temperature",
        "humidity",
        "pH",
        "light",
        "light_natural",
        "soil_humidity",
    }

    TIME_RANGES = {
        "last_hour": "time >= now() - interval '1 hour'",
        "last_24_hours": "time >= now() - interval '24 hours'",
        "last_7_days": "time >= now() - interval '7 days'",
        "last_30_days": "time >= now() - interval '30 days'",
    }

    @staticmethod
    def _escape(value: str) -> str:
        """
        Very small helper to escape single quotes in string literals.
        """
        return value.replace("'", "''")

    @classmethod
    def sensor_data(
        cls,
        metric: str,
        *,
        time_range: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        device: Optional[str] = None,
        site: Optional[str] = None,
        limit: int = 100,
        order_desc: bool = True,
    ) -> str:
        """
        Build a SQL query for the requested metric with optional filters.

        :param metric: One of the supported metrics in METRICS.
        :param time_range: Shortcut key from TIME_RANGES (e.g. 'last_hour').
        :param start: Lower bound for the time column (inclusive), ISO timestamp.
        :param end: Upper bound for the time column (inclusive), ISO timestamp.
        :param device: Optional device filter.
        :param site: Optional site filter.
        :param limit: Limit for returned rows.
        :return: Composed SQL query string.
        """
        if metric not in cls.METRICS:
            raise ValueError(f"Unsupported metric '{metric}'")

        conditions = [f"metric = '{metric}'"]

        if time_range is not None:
            try:
                conditions.append(cls.TIME_RANGES[time_range])
            except KeyError as exc:
                raise ValueError(f"Unsupported time range '{time_range}'") from exc

        if start:
            conditions.append(f"time >= '{cls._escape(start)}'")
        if end:
            conditions.append(f"time <= '{cls._escape(end)}'")
        if device:
            conditions.append(f"device = '{cls._escape(device)}'")
        if site:
            conditions.append(f"site = '{cls._escape(site)}'")

        where_clause = " AND ".join(conditions) if conditions else "1 = 1"
        sort_direction = "DESC" if order_desc else "ASC"

        return f"""
        SELECT time, value, site, device, metric
        FROM sensor_data
        WHERE {where_clause}
        ORDER BY time {sort_direction}
        LIMIT {int(limit)};
        """

    TEST_DATA = """
    SELECT time, value, site, device, metric
    FROM sensor_data
    WHERE metric = 'temperature'
    ORDER BY time DESC
    LIMIT 10;
    """
