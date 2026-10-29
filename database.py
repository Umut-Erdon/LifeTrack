"""LifeTrack SQL Server connection, schema and input validation."""
from __future__ import annotations

import os
from datetime import date, datetime, timedelta

import pyodbc

SERVER = os.getenv("LIFETRACK_SQL_SERVER", r"DESKTOP-PM8J61P")
DATABASE = os.getenv("LIFETRACK_SQL_DATABASE", "LifeTrack")
ODBC_DRIVER = os.getenv("LIFETRACK_ODBC_DRIVER", "ODBC Driver 17 for SQL Server")

VALID_DEVICES = {"Telefon", "Bilgisayar", "Televizyon", "Tablet", "Diğer"}
VALID_CATEGORIES = {
    "Sosyal medya", "Video / içerik", "Oyun", "İş / eğitim", "İletişim", "Diğer"
}
MAX_SCREEN_MINUTES = 24 * 60
MAX_SLEEP_MINUTES = 18 * 60


def _connection_string(database: str) -> str:
    return (
        f"DRIVER={{{ODBC_DRIVER}}};"
        f"SERVER={SERVER};"
        f"DATABASE={database};"
        "Trusted_Connection=yes;"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
    )


class Row:
    """Small row wrapper supporting both row[0] and row['column_name']."""
    def __init__(self, values, columns):
        self._values = tuple(
            value.isoformat() if isinstance(value, (date, datetime)) else value
            for value in values
        )
        self._mapping = dict(zip(columns, self._values))

    def __getitem__(self, key):
        return self._mapping[key] if isinstance(key, str) else self._values[key]

    def __iter__(self):
        return iter(self._values)

    def __len__(self):
        return len(self._values)


class CursorAdapter:
    def __init__(self, cursor):
        self.cursor = cursor

    @property
    def description(self):
        return self.cursor.description

    @property
    def rowcount(self):
        return self.cursor.rowcount

    def _convert_row(self, row):
        if row is None:
            return None
        columns = [column[0] for column in self.cursor.description]
        return Row(row, columns)

    def fetchone(self):
        return self._convert_row(self.cursor.fetchone())

    def fetchall(self):
        return [self._convert_row(row) for row in self.cursor.fetchall()]


class ConnectionAdapter:
    """Expose the small DB-API surface used by the LifeTrack application."""
    def __init__(self, connection):
        self.connection = connection

    def execute(self, sql, params=()):
        cursor = self.connection.cursor()
        cursor.execute(sql, params)
        return CursorAdapter(cursor)

    def executemany(self, sql, seq_of_params):
        cursor = self.connection.cursor()
        cursor.executemany(sql, seq_of_params)
        return CursorAdapter(cursor)

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

    def close(self):
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.commit() if exc_type is None else self.rollback()
        return False


def _create_schema(conn: ConnectionAdapter) -> None:
    """Create required SQL Server tables and indexes if they do not exist."""
    conn.execute("""
        IF OBJECT_ID(N'dbo.screen_records', N'U') IS NULL
        BEGIN
            CREATE TABLE dbo.screen_records (
                id INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
                record_date DATE NOT NULL,
                device NVARCHAR(30) NOT NULL,
                category NVARCHAR(50) NOT NULL,
                app_name NVARCHAR(120) NOT NULL CONSTRAINT DF_screen_records_app_name DEFAULT N'',
                minutes INT NOT NULL CHECK (minutes BETWEEN 1 AND 1440),
                note NVARCHAR(1000) NOT NULL CONSTRAINT DF_screen_records_note DEFAULT N'',
                created_at DATETIME2 NOT NULL CONSTRAINT DF_screen_records_created_at DEFAULT SYSDATETIME(),
                CHECK (device IN (N'Telefon', N'Bilgisayar', N'Televizyon', N'Tablet', N'Diğer')),
                CHECK (category IN (N'Sosyal medya', N'Video / içerik', N'Oyun', N'İş / eğitim', N'İletişim', N'Diğer'))
            );
        END;

        IF OBJECT_ID(N'dbo.sleep_records', N'U') IS NULL
        BEGIN
            CREATE TABLE dbo.sleep_records (
                id INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
                sleep_date DATE NOT NULL,
                bedtime CHAR(5) NOT NULL,
                wake_time CHAR(5) NOT NULL,
                duration_minutes INT NOT NULL CHECK (duration_minutes BETWEEN 1 AND 1080),
                note NVARCHAR(1000) NOT NULL CONSTRAINT DF_sleep_records_note DEFAULT N'',
                created_at DATETIME2 NOT NULL CONSTRAINT DF_sleep_records_created_at DEFAULT SYSDATETIME()
            );
        END;

        IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_screen_records_date' AND object_id = OBJECT_ID(N'dbo.screen_records'))
            CREATE INDEX IX_screen_records_date ON dbo.screen_records(record_date);
        IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_screen_records_date_category' AND object_id = OBJECT_ID(N'dbo.screen_records'))
            CREATE INDEX IX_screen_records_date_category ON dbo.screen_records(record_date, category);
        IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_sleep_records_date' AND object_id = OBJECT_ID(N'dbo.sleep_records'))
            CREATE INDEX IX_sleep_records_date ON dbo.sleep_records(sleep_date);
    """)
    conn.commit()


def connect_db(database: str | None = None) -> ConnectionAdapter:
    """Connect to the configured SQL Server database (or an explicit SQL DB name)."""
    target_database = database or DATABASE
    try:
        raw_connection = pyodbc.connect(
            _connection_string(target_database), timeout=10, autocommit=False
        )
        conn = ConnectionAdapter(raw_connection)
        _create_schema(conn)
        return conn
    except pyodbc.Error as exc:
        raise RuntimeError(
            "LifeTrack SQL Server bağlantısı başarısız.\n"
            f"Sunucu: {SERVER}\nVeritabanı: {target_database}\n"
            "SQL Server servisini, veritabanının varlığını ve Windows hesabının erişim yetkisini kontrol et.\n"
            f"Ayrıntı: {exc}"
        ) from exc


def _validate_iso_date(value: str, field_name: str) -> None:
    try:
        parsed = date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} geçerli bir tarih olmalı.") from exc
    if parsed.isoformat() != str(value):
        raise ValueError(f"{field_name} YYYY-AA-GG biçiminde olmalı.")


def validate_screen_values(values: tuple) -> tuple:
    """Validate values in screen_records INSERT/UPDATE order."""
    if len(values) != 6:
        raise ValueError("Ekran süresi kaydı eksik veya hatalı.")
    record_date, device, category, app_name, minutes, note = values
    _validate_iso_date(record_date, "Kayıt tarihi")
    if device not in VALID_DEVICES:
        raise ValueError("Listeden geçerli bir cihaz seç.")
    if category not in VALID_CATEGORIES:
        raise ValueError("Listeden geçerli bir kategori seç.")
    app_name, note = str(app_name).strip(), str(note).strip()
    try:
        minutes = int(minutes)
    except (TypeError, ValueError) as exc:
        raise ValueError("Süre dakika cinsinden tam sayı olmalı.") from exc
    if not 1 <= minutes <= MAX_SCREEN_MINUTES:
        raise ValueError("Ekran süresi 1 ile 1440 dakika arasında olmalı.")
    if len(app_name) > 120:
        raise ValueError("Uygulama / etkinlik adı en fazla 120 karakter olabilir.")
    if len(note) > 1000:
        raise ValueError("Not en fazla 1000 karakter olabilir.")
    return record_date, device, category, app_name, minutes, note


def calculate_sleep_minutes(bedtime: str, wake_time: str) -> int:
    try:
        start = datetime.strptime(bedtime, "%H:%M")
        end = datetime.strptime(wake_time, "%H:%M")
    except (TypeError, ValueError) as exc:
        raise ValueError("Yatış ve kalkış saatleri SS:DD biçiminde olmalı.") from exc
    if start == end:
        raise ValueError("Yatış ve kalkış saati aynı olamaz; saatleri kontrol et.")
    if end < start:
        end += timedelta(days=1)
    return int((end - start).total_seconds() // 60)


def validate_sleep_values(values: tuple) -> tuple:
    """Validate values in sleep_records INSERT/UPDATE order."""
    if len(values) != 5:
        raise ValueError("Uyku kaydı eksik veya hatalı.")
    sleep_date, bedtime, wake_time, duration_minutes, note = values
    _validate_iso_date(sleep_date, "Uyku tarihi")
    calculated = calculate_sleep_minutes(bedtime, wake_time)
    if not 1 <= calculated <= MAX_SLEEP_MINUTES:
        raise ValueError("Uyku aralığı 1 dakika ile 18 saat arasında olmalı; saatleri kontrol et.")
    try:
        supplied_duration = int(duration_minutes)
    except (TypeError, ValueError) as exc:
        raise ValueError("Uyku süresi dakika cinsinden tam sayı olmalı.") from exc
    if supplied_duration != calculated:
        raise ValueError("Uyku süresi saatlerle uyuşmuyor. Kaydı yeniden hesaplayıp dene.")
    note = str(note).strip()
    if len(note) > 1000:
        raise ValueError("Not en fazla 1000 karakter olabilir.")
    return sleep_date, bedtime, wake_time, calculated, note
