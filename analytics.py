"""Pure analytics helpers for LifeTrack reports."""
from __future__ import annotations

from datetime import date, timedelta


def get_period_range(choice: int, today: date) -> tuple[date, date, str]:
    """Return inclusive date range and label for the selected report period."""
    if choice == 0:
        return today - timedelta(days=6), today, "Son 7 gün"
    if choice == 1:
        return today - timedelta(days=29), today, "Son 30 gün"
    if choice == 2:
        return today.replace(month=1, day=1), today, "Bu yıl"
    raise ValueError("Bilinmeyen rapor dönemi seçildi.")


def previous_period_range(start: date, end: date) -> tuple[date, date]:
    """Return the equally long period immediately before start."""
    days = (end - start).days + 1
    previous_end = start - timedelta(days=1)
    return previous_end - timedelta(days=days - 1), previous_end


def build_buckets(choice: int, start: date, end: date) -> list[tuple[str, date, date]]:
    """Build daily, weekly-ish, or monthly buckets without gaps or overlaps."""
    buckets: list[tuple[str, date, date]] = []
    if choice == 0:
        cursor = start
        while cursor <= end:
            buckets.append((cursor.strftime("%d %b"), cursor, cursor))
            cursor += timedelta(days=1)
    elif choice == 1:
        cursor = start
        while cursor <= end:
            bucket_end = min(cursor + timedelta(days=6), end)
            buckets.append((f"{cursor.day:02d}–{bucket_end.day:02d} {bucket_end.strftime('%b')}", cursor, bucket_end))
            cursor = bucket_end + timedelta(days=1)
    elif choice == 2:
        cursor = start.replace(day=1)
        while cursor <= end:
            next_month = date(cursor.year + (cursor.month == 12), cursor.month % 12 + 1, 1)
            bucket_end = min(next_month - timedelta(days=1), end)
            buckets.append((cursor.strftime("%b"), max(cursor, start), bucket_end))
            cursor = next_month
    else:
        raise ValueError("Bilinmeyen rapor dönemi seçildi.")
    return buckets


def sum_usage(conn, start: date, end: date) -> int:
    row = conn.execute(
        "SELECT COALESCE(SUM(minutes), 0) FROM dbo.screen_records WHERE record_date BETWEEN ? AND ?",
        (start.isoformat(), end.isoformat()),
    ).fetchone()
    return int(row[0] or 0)


def get_category_totals(conn, start: date, end: date) -> list[tuple[str, int]]:
    rows = conn.execute(
        """SELECT category, SUM(minutes) AS total FROM dbo.screen_records
           WHERE record_date BETWEEN ? AND ? GROUP BY category ORDER BY total DESC, category ASC""",
        (start.isoformat(), end.isoformat()),
    ).fetchall()
    return [(str(row[0]), int(row[1])) for row in rows]


def get_bucket_totals(conn, buckets: list[tuple[str, date, date]]) -> list[tuple[str, int]]:
    results = []
    for label, start, end in buckets:
        results.append((label, sum_usage(conn, start, end)))
    return results


def percent_change(current: int, previous: int) -> float | None:
    """Percentage change; None means a zero baseline makes it undefined."""
    if previous == 0:
        return None
    return ((current - previous) / previous) * 100.0


def get_app_totals(conn, start: date, end: date, limit: int = 5) -> list[tuple[str, int]]:
    """Return most-used application/activity names for a date range."""
    rows = conn.execute(
        """SELECT TOP (?) app_name, SUM(minutes) AS total FROM dbo.screen_records
           WHERE record_date BETWEEN ? AND ? AND LTRIM(RTRIM(app_name)) <> N''
           GROUP BY app_name ORDER BY total DESC, app_name ASC""",
        (max(1, int(limit)), start.isoformat(), end.isoformat()),
    ).fetchall()
    return [(str(row[0]), int(row[1])) for row in rows]
