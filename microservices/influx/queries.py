from typing import Optional


class Queries(object):
    """
    Predefined queries to be used with InfluxDBAdapter.
    """

    METRICS = {
        "temperature",
        "humidity",
        "light",
        "soil_humidity",
        "pH",
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
        start: Optional[str] = None,
        end: Optional[str] = None,
        device: Optional[str] = None,
        limit: Optional[int] = None,
        order_desc: bool = True,
    ) -> str:
        """
        Build a SQL query for the requested metric with optional filters.

        :param metric: One of the supported metrics in METRICS.
        :param start: Lower bound for the time column (inclusive), ISO timestamp.
        :param end: Upper bound for the time column (inclusive), ISO timestamp.
        :param device: Optional device filter.
        :param limit: Limit for returned rows. If None, no limit is applied.
        :return: Composed SQL query string.
        """

        conditions = [f"metric = '{metric}'"]

        if start:
            conditions.append(f"time >= '{cls._escape(start)}'")
        if end:
            conditions.append(f"time <= '{cls._escape(end)}'")
        if device:
            conditions.append(f"device = '{cls._escape(device)}'")

        where_clause = " AND ".join(conditions) if conditions else "1 = 1"
        sort_direction = "DESC" if order_desc else "ASC"

        # Se limit è presente (e non è 0 o None), costruisce la stringa, altrimenti stringa vuota
        limit_clause = f"LIMIT {int(limit)}" if limit else ""

        return f"""
        SELECT time, value, site, device, metric
        FROM sensor_data
        WHERE {where_clause}
        ORDER BY time {sort_direction}
        {limit_clause};
        """
    
    # Aggiungi questo metodo alla classe Queries
    @classmethod
    def actuator_detailed(cls, device_id, start=None, end=None):
        """
        Recupera livello, energia e acqua per un attuatore.
        """
        conditions = []
        # Telegraf usa il tag "id" per identificare l'attuatore
        if device_id:
            conditions.append(f"id = '{cls._escape(device_id)}'")
        if start:
            conditions.append(f"time >= '{cls._escape(start)}'")
        if end:
            conditions.append(f"time <= '{cls._escape(end)}'")
            
        where_clause = " AND ".join(conditions) if conditions else "1 = 1"
        
        return f"""
        SELECT time, level, energy_consumption, water_consumption
        FROM actuator_data
        WHERE {where_clause}
        ORDER BY time DESC
        """

    @classmethod
    def actuator_last_level(cls, device_id):
        """
        Recupera l'ultimo livello noto per un attuatore.
        """
        conditions = []
        if device_id:
            conditions.append(f"id = '{cls._escape(device_id)}'")
        where_clause = " AND ".join(conditions) if conditions else "1 = 1"

        return f"""
        SELECT time, level
        FROM actuator_data
        WHERE {where_clause}
        ORDER BY time DESC
        LIMIT 1
        """
