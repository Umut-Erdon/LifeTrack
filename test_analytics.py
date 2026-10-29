import unittest
from datetime import date, timedelta

from analytics import (
    build_buckets, get_app_totals, get_bucket_totals, get_category_totals,
    get_period_range, percent_change, previous_period_range, sum_usage,
)
from database import connect_db

TEST_DATABASE = "LifeTrack_Test"


class AnalyticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conn = connect_db(database=TEST_DATABASE)

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()

    def setUp(self):
        with self.conn:
            self.conn.execute("DELETE FROM dbo.screen_records")
            self.conn.executemany(
                """INSERT INTO dbo.screen_records
                   (record_date, device, category, app_name, minutes, note)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                [
                    ("2026-10-27", "Telefon", "Sosyal medya", "Instagram", 60, "test"),
                    ("2026-10-28", "Bilgisayar", "İş / eğitim", "IDE", 120, "test"),
                    ("2026-10-29", "Telefon", "Sosyal medya", "TikTok", 30, "test"),
                    ("2026-10-15", "Televizyon", "Video / içerik", "TV", 90, "test"),
                ],
            )

    def test_period_ranges(self):
        today = date(2026, 10, 29)
        self.assertEqual(get_period_range(0, today)[:2], (date(2026, 10, 23), today))
        self.assertEqual(get_period_range(1, today)[:2], (date(2026, 9, 30), today))
        self.assertEqual(get_period_range(2, today)[:2], (date(2026, 1, 1), today))

    def test_previous_period_has_equal_length_and_is_adjacent(self):
        start, end = date(2026, 10, 23), date(2026, 10, 29)
        previous_start, previous_end = previous_period_range(start, end)
        self.assertEqual((previous_end - previous_start).days, (end - start).days)
        self.assertEqual(previous_end + timedelta(days=1), start)

    def test_buckets_cover_full_period_without_gaps(self):
        start, end = date(2026, 9, 30), date(2026, 10, 29)
        buckets = build_buckets(1, start, end)
        self.assertEqual(buckets[0][1], start)
        self.assertEqual(buckets[-1][2], end)
        self.assertEqual(sum((b - a).days + 1 for _, a, b in buckets), 30)

    def test_category_totals_sorted_and_correct(self):
        totals = get_category_totals(self.conn, date(2026, 10, 1), date(2026, 10, 29))
        self.assertEqual(totals, [("İş / eğitim", 120), ("Sosyal medya", 90), ("Video / içerik", 90)])

    def test_app_totals_sorted_and_limited(self):
        totals = get_app_totals(self.conn, date(2026, 10, 1), date(2026, 10, 29), limit=2)
        self.assertEqual(totals, [("IDE", 120), ("TV", 90)])

    def test_sum_and_bucket_totals(self):
        self.assertEqual(sum_usage(self.conn, date(2026, 10, 27), date(2026, 10, 29)), 210)
        buckets = [("test", date(2026, 10, 27), date(2026, 10, 29))]
        self.assertEqual(get_bucket_totals(self.conn, buckets), [("test", 210)])

    def test_percent_change_handles_zero_baseline(self):
        self.assertIsNone(percent_change(50, 0))
        self.assertEqual(percent_change(150, 100), 50.0)
        self.assertEqual(percent_change(50, 100), -50.0)


if __name__ == "__main__":
    unittest.main()
