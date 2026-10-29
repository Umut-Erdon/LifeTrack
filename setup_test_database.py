"""Create and initialize the isolated SQL Server database used by tests."""
from __future__ import annotations

import pyodbc

from database import DATABASE, ODBC_DRIVER, SERVER, connect_db

TEST_DATABASE = "LifeTrack_Test"


def main() -> None:
    if TEST_DATABASE.casefold() == DATABASE.casefold():
        raise RuntimeError("Test veritabanı adı ana veritabanıyla aynı olamaz.")

    master_connection_string = (
        f"DRIVER={{{ODBC_DRIVER}}};SERVER={SERVER};DATABASE=master;"
        "Trusted_Connection=yes;Encrypt=yes;TrustServerCertificate=yes;"
    )
    connection = pyodbc.connect(master_connection_string, timeout=10, autocommit=True)
    try:
        connection.cursor().execute(
            "IF DB_ID(N'LifeTrack_Test') IS NULL CREATE DATABASE [LifeTrack_Test]"
        )
    finally:
        connection.close()

    test_connection = connect_db(database=TEST_DATABASE)
    test_connection.close()
    print("LifeTrack_Test veritabanı hazır. Ana LifeTrack veritabanına dokunulmadı.")


if __name__ == "__main__":
    main()
