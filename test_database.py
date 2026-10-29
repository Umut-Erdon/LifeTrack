import unittest

from database import (
    calculate_sleep_minutes, connect_db, validate_screen_values, validate_sleep_values,
)

TEST_DATABASE = "LifeTrack_Test"


class DatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conn = connect_db(database=TEST_DATABASE)

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()

    def setUp(self):
        with self.conn:
            self.conn.execute("DELETE FROM dbo.screen_records")
            self.conn.execute("DELETE FROM dbo.sleep_records")

    def test_schema_and_indexes_created(self):
        tables = {r[0] for r in self.conn.execute(
            "SELECT name FROM sys.tables WHERE name IN (N'screen_records', N'sleep_records')"
        ).fetchall()}
        self.assertIn("screen_records", tables)
        self.assertIn("sleep_records", tables)
        indexes = {r[0] for r in self.conn.execute(
            """SELECT i.name FROM sys.indexes i
               JOIN sys.tables t ON t.object_id = i.object_id
               WHERE t.name IN (N'screen_records', N'sleep_records')"""
        ).fetchall()}
        self.assertIn("IX_screen_records_date", indexes)
        self.assertIn("IX_screen_records_date_category", indexes)
        self.assertIn("IX_sleep_records_date", indexes)

    def test_screen_record_validates_and_saves(self):
        values = validate_screen_values(("2026-10-29", "Telefon", "Sosyal medya", "Instagram", 35, "test"))
        with self.conn:
            self.conn.execute(
                """INSERT INTO dbo.screen_records
                   (record_date, device, category, app_name, minutes, note)
                   VALUES (?, ?, ?, ?, ?, ?)""", values
            )
        result = self.conn.execute(
            "SELECT TOP (1) minutes FROM dbo.screen_records WHERE note = ? ORDER BY id DESC", ("test",)
        ).fetchone()
        self.assertEqual(result[0], 35)

    def test_invalid_screen_duration_rejected(self):
        with self.assertRaises(ValueError):
            validate_screen_values(("2026-10-29", "Telefon", "Sosyal medya", "Instagram", 0, ""))

    def test_invalid_category_rejected(self):
        with self.assertRaises(ValueError):
            validate_screen_values(("2026-10-29", "Telefon", "Something", "App", 20, ""))

    def test_overnight_sleep_duration(self):
        self.assertEqual(calculate_sleep_minutes("23:30", "07:30"), 480)
        values = validate_sleep_values(("2026-10-28", "23:30", "07:30", 480, "test"))
        with self.conn:
            self.conn.execute(
                """INSERT INTO dbo.sleep_records
                   (sleep_date, bedtime, wake_time, duration_minutes, note)
                   VALUES (?, ?, ?, ?, ?)""", values
            )
        result = self.conn.execute(
            "SELECT TOP (1) duration_minutes FROM dbo.sleep_records WHERE note = ? ORDER BY id DESC", ("test",)
        ).fetchone()
        self.assertEqual(result[0], 480)

    def test_same_sleep_times_rejected(self):
        with self.assertRaises(ValueError):
            validate_sleep_values(("2026-10-28", "23:30", "23:30", 1440, ""))

    def test_sleep_duration_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            validate_sleep_values(("2026-10-28", "23:30", "07:30", 420, ""))

    def test_schema_initialization_is_repeatable(self):
        second = connect_db(database=TEST_DATABASE)
        try:
            count = second.execute(
                "SELECT COUNT(*) FROM sys.tables WHERE name IN (N'screen_records', N'sleep_records')"
            ).fetchone()[0]
            self.assertEqual(count, 2)
        finally:
            second.close()


if __name__ == "__main__":
    unittest.main()
