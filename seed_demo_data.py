"""Add clearly labeled demo records to an empty LifeTrack database.

Run: python seed_demo_data.py
This script never adds demo records to a database that already contains records.
"""
from __future__ import annotations

from datetime import date, timedelta

from database import connect_db, calculate_sleep_minutes


def seed_demo_data() -> tuple[int, int]:
    conn = connect_db()
    try:
        screen_count = conn.execute("SELECT COUNT(*) FROM screen_records").fetchone()[0]
        sleep_count = conn.execute("SELECT COUNT(*) FROM sleep_records").fetchone()[0]
        if screen_count or sleep_count:
            raise RuntimeError(
                "Veritabanında zaten kayıt var. Demo verileri mevcut kayıtlarla karışmasın diye eklenmedi. "
                "Denemek için boş bir klasörde yeni LifeTrack kopyası aç."
            )

        today = date.today()
        screen_rows = []
        sleep_rows = []
        # 14 days of fictional data, including today, for useful charts and reports.
        patterns = [
            [("Telefon", "Sosyal medya", "Instagram", 35), ("Bilgisayar", "İş / eğitim", "Kodlama / eğitim", 105), ("Telefon", "İletişim", "Mesajlaşma", 25), ("Telefon", "Video / içerik", "Video izleme", 45)],
            [("Telefon", "Sosyal medya", "Instagram", 50), ("Bilgisayar", "İş / eğitim", "Proje geliştirme", 120), ("Bilgisayar", "Oyun", "Oyun", 55), ("Telefon", "İletişim", "Mesajlaşma", 20)],
            [("Telefon", "Video / içerik", "Kısa videolar", 40), ("Bilgisayar", "İş / eğitim", "Kodlama / eğitim", 90), ("Telefon", "Sosyal medya", "Instagram", 30), ("Televizyon", "Video / içerik", "Dizi / film", 65)],
            [("Telefon", "Sosyal medya", "Instagram", 25), ("Bilgisayar", "İş / eğitim", "Proje geliştirme", 140), ("Telefon", "İletişim", "Mesajlaşma", 30), ("Bilgisayar", "Oyun", "Oyun", 40)],
        ]
        for offset in range(13, -1, -1):
            day = today - timedelta(days=offset)
            for device, category, app_name, base_minutes in patterns[offset % len(patterns)]:
                # Small deterministic variation makes different days visible without random data.
                minutes = base_minutes + ((offset * 7 + len(app_name)) % 16 - 5)
                screen_rows.append((day.isoformat(), device, category, app_name, minutes,
                                    "DEMO VERİSİ — örnek kayıt, gerçek kullanıcı verisi değildir."))

            bedtimes = ["23:20", "00:05", "23:45", "23:10", "00:20", "23:35", "23:55"]
            wake_times = ["07:10", "07:35", "07:20", "06:55", "08:00", "07:15", "07:40"]
            idx = offset % len(bedtimes)
            bedtime, wake_time = bedtimes[idx], wake_times[idx]
            duration = calculate_sleep_minutes(bedtime, wake_time)
            sleep_rows.append((day.isoformat(), bedtime, wake_time, duration,
                               "DEMO VERİSİ — örnek uyku kaydı."))

        with conn:
            conn.executemany(
                "INSERT INTO dbo.screen_records(record_date, device, category, app_name, minutes, note) VALUES(?,?,?,?,?,?)",
                screen_rows,
            )
            conn.executemany(
                "INSERT INTO dbo.sleep_records(sleep_date, bedtime, wake_time, duration_minutes, note) VALUES(?,?,?,?,?)",
                sleep_rows,
            )
        return len(screen_rows), len(sleep_rows)
    finally:
        conn.close()


if __name__ == "__main__":
    try:
        screens, sleeps = seed_demo_data()
        print("Demo verileri başarıyla eklendi.")
        print(f"Ekran kullanımı kaydı: {screens}")
        print(f"Uyku kaydı: {sleeps}")
        print("Bunlar tamamen örnek verilerdir; uygulamayı açıp dashboard ve raporları inceleyebilirsin.")
    except RuntimeError as exc:
        print(f"İşlem yapılmadı: {exc}")
        raise SystemExit(1)
