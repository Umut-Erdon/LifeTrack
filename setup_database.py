"""Create the configured LifeTrack SQL Server database if missing, then initialize its schema."""
from __future__ import annotations

import pyodbc

from database import DATABASE, ODBC_DRIVER, SERVER, connect_db


def main() -> None:
    master_connection_string = (
        f"DRIVER={{{ODBC_DRIVER}}};SERVER={SERVER};DATABASE=master;"
        "Trusted_Connection=yes;Encrypt=yes;TrustServerCertificate=yes;"
    )
    safe_name = DATABASE.replace("]", "]]" )
    connection = pyodbc.connect(master_connection_string, timeout=10, autocommit=True)
    try:
        connection.cursor().execute(
            f"IF DB_ID(N'{DATABASE.replace(chr(39), chr(39) * 2)}') IS NULL CREATE DATABASE [{safe_name}]"
        )
    finally:
        connection.close()

    app_connection = connect_db()
    app_connection.close()
    print(f"{DATABASE} veritabanı ve tablolar hazır. Var olan kayıtlar silinmedi.")


if __name__ == "__main__":
    main()
