<div align="center">

# LifeTrack

**Ekran kullanımını ve uyku düzenini takip eden, verilerini yerelde tutan Windows masaüstü uygulaması.**

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![PySide6](https://img.shields.io/badge/UI-PySide6-41CD52?logo=qt&logoColor=white)
![SQL Server](https://img.shields.io/badge/Veritaban%C4%B1-SQL%20Server-CC2927?logo=microsoftsqlserver&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D4?logo=windows&logoColor=white)

</div>

---

LifeTrack, dijital alışkanlıklarını ve dinlenme düzenini tek bir yerden görmeni sağlar. Kullanım kayıtlarını elle girebilir ya da otomatik takibi başlatabilir, uyku sürelerini kaydedip dönemsel raporlarla eğilimleri görebilirsin. Veriler bulutta değil, kendi **Microsoft SQL Server** veritabanında saklanır. Proje SQLite kullanmaz.

<!-- Ekran görüntüleri eklemek için:
<p align="center">
  <img src="docs/dashboard.png" width="800" alt="Genel Bakış">
</p>
-->

## İçindekiler

- [Özellikler](#özellikler)
- [Gizlilik](#gizlilik)
- [Gereksinimler](#gereksinimler)
- [Hızlı başlangıç](#hızlı-başlangıç)
- [SQL Server yapılandırması](#sql-server-yapılandırması)
- [Otomatik takip](#otomatik-takip)
- [Testler](#testler)
- [Demo verileri](#demo-verileri)
- [EXE oluşturma](#exe-oluşturma)
- [Proje yapısı](#proje-yapısı)
- [Sorun giderme](#sorun-giderme)

## Özellikler

| Alan | Neler yapabilirsin |
|---|---|
| **Genel Bakış** | Günlük özet kartları, son 7 günlük ekran süresi grafiği, günün notu |
| **Zaman Kayıtları** | Kullanım kaydı ekleme, düzenleme ve silme; cihaz, kategori, uygulama/etkinlik, süre ve not alanları |
| **Uyku Takibi** | Yatış ve kalkış saatinden süreyi otomatik hesaplama, son kayıtların ortalaması |
| **Raporlar ve Öneriler** | Son 7 gün, son 30 gün ve bu yıl dönemleri; önceki eşit uzunluktaki dönemle karşılaştırma; kategori dağılımı ve en çok kullanılan uygulamalar |
| **Otomatik takip** | Sen başlattığında Windows ön plan uygulamasının süresini kaydeder |
| **Arayüz** | Koyu ve açık tema, tek tıkla geçiş, tercih hatırlanır |
| **Veri güvenliği** | Girişlerde doğrulama, tarih alanlarında indeksler |

## Gizlilik

Otomatik takip, kendi isteğinle başlatılan ve istediğin an durdurabildiğin bir özelliktir.

- **Kaydedilen:** yalnızca etkin uygulamanın işlem adı ve süresi
- **Kaydedilmeyen:** pencere başlığı, yazılan metin, web adresi, ekran görüntüsü, klavye içeriği
- 60 saniyeden uzun hareketsizlikte sayaç duraklar
- Tüm veriler senin SQL Server örneğinde kalır

## Gereksinimler

- Windows 10 veya 11
- Python 3.10+ (64-bit önerilir)
- Microsoft SQL Server (SQL Server Express veya Developer yeterlidir)
- [ODBC Driver 17 for SQL Server](https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server)
- Windows hesabının `LifeTrack` veritabanına erişim yetkisi (Windows Authentication kullanılır)

## Hızlı başlangıç

**1. Depoyu klonla**

```powershell
git clone <depo-adresi>
cd LifeTrack_MVP_SQLServer
```

**2. Veritabanını hazırla**

`LifeTrack` veritabanı ve tablolar henüz yoksa bu komutu bir kez çalıştır. Var olan veritabanı ve kayıtlar silinmez.

```powershell
python setup_database.py
```

**3. Sanal ortamı kur ve bağımlılıkları yükle**

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

> PowerShell sanal ortamı etkinleştirmeyi engellerse Komut İstemi'nde `.venv\Scripts\activate.bat` kullanabilirsin.

**4. Uygulamayı başlat**

```powershell
python app.py
```

İstersen `Baslat.bat` dosyasına çift tıklayarak da başlatabilirsin.

## SQL Server yapılandırması

Varsayılan bağlantı ayarları `database.py` içindedir:

| Ayar | Varsayılan |
|---|---|
| Sunucu | `DESKTOP-PM8J61P` |
| Veritabanı | `LifeTrack` |
| Sürücü | `ODBC Driver 17 for SQL Server` |
| Kimlik doğrulama | Windows Authentication |

Farklı bir bilgisayarda çalıştırırken ortam değişkenleriyle değiştirebilirsin:

```powershell
$env:LIFETRACK_SQL_SERVER   = "SUNUCU_ADI\SQLEXPRESS"
$env:LIFETRACK_SQL_DATABASE = "LifeTrack"
$env:LIFETRACK_ODBC_DRIVER  = "ODBC Driver 17 for SQL Server"
```

Uygulama ilk bağlantıda `dbo.screen_records` ve `dbo.sleep_records` tablolarını ve gerekli indeksleri, yoksa oluşturur. Var olan tablolara ve kayıtlara dokunmaz.

## Otomatik takip

1. **Zaman Kayıtları** sayfasını aç.
2. **Takibi başlat** düğmesine bas.
3. İşin bitince **Durdur**'a bas.

Bir dakikadan kısa kalan süreler kayda dönüştürülmez; tam dakikalar `Otomatik takip` notuyla kayıt listesine eklenir. Özellik Windows 10/11 için tasarlanmıştır. Hassas kullanım verisi oluşturabileceği için yalnızca gerektiğinde açık tutmanı öneririz.

## Testler

Testler gerçek `LifeTrack` veritabanına **bağlanmaz**. Ayrı bir `LifeTrack_Test` veritabanı kullanır ve yalnızca bu veritabanındaki tabloları temizler.

```powershell
# 1. Test veritabanını bir kez oluştur (veritabanı oluşturma yetkisi gerekir)
python setup_test_database.py

# 2. Testleri çalıştır
python -m unittest discover -s tests -v
```

> **Önemli:** Testleri çalıştırmadan önce `setup_test_database.py` işleminin başarıyla tamamlandığından emin ol. `LifeTrack_Test` yalnızca otomatik testler içindir; kişisel kayıtlarını buraya girme.

## Demo verileri

`seed_demo_data.py`, yapılandırılmış ana veritabanına örnek kayıtlar ekler. Veritabanında herhangi bir kayıt varsa eklemeyi reddeder.

```powershell
python seed_demo_data.py
```

> **Uyarı:** Gerçek kayıtların bulunduğu veritabanında çalıştırma. Demo için ayrı bir veritabanı oluşturup `LIFETRACK_SQL_DATABASE` ortam değişkenini ona ayarlayabilirsin.

### SQL betiği ile demo verisi

Grafikleri ve raporları dolu görmek istersen `seed_demo_data.sql` betiğini SQL Server Management Studio'da (SSMS) çalıştırabilirsin. Betik son 90 gün için gerçekçi örnek veri üretir:

- Her gün 5 farklı ekran kullanım kaydı (Visual Studio Code, LinkedIn / Kariyer.net, SQL Server araştırması, Instagram, YouTube)
- Her gün 1 uyku kaydı (yatış ve kalkış saatleri süreyle uyumlu)
- Hafta sonları iş / eğitim sürelerini daha kısa tutar

Üretilen tüm kayıtların notu `LifeTrack örnek veri:` ile başlar. Betik her çalıştırmada önce yalnızca bu notlu eski örnek kayıtları siler, sonra yenilerini ekler. Notu farklı olan gerçek kayıtlarına dokunmaz. Örnek verileri tamamen kaldırmak için betiğin ilk bölümündeki iki `DELETE` komutunu tek başına çalıştırman yeterlidir.

> **Not:** Bu betik, `seed_demo_data.py` gibi veritabanının boş olup olmadığını kontrol etmez. Örnek kayıtlar gerçek kayıtlarınla aynı raporlarda görünür, bu yüzden ayrı bir demo veritabanında kullanman daha temiz olur.

## EXE oluşturma

```powershell
python -m pip install pyinstaller
pyinstaller --noconfirm --windowed --name LifeTrack app.py
```

EXE'yi çalıştıracağın bilgisayarda da SQL Server erişimi ve ODBC sürücüsü bulunmalıdır.

## Proje yapısı

```
LifeTrack_MVP_SQLServer/
├── app.py                  # Arayüz ve ana uygulama
├── database.py             # SQL Server bağlantısı, tablo kurulumu, doğrulama
├── analytics.py            # Dönem aralıkları, toplamlar, kıyaslama hesapları
├── automatic_tracker.py    # Ön plan uygulaması tespiti ve sınıflandırma
├── setup_database.py       # Ana veritabanı kurulumu
├── setup_test_database.py  # Test veritabanı kurulumu
├── seed_demo_data.py       # İsteğe bağlı demo verisi
├── Baslat.bat              # Tek tıkla başlatma
├── requirements.txt
└── tests/                  # Birim testleri
```

## Sorun giderme

| Belirti | Olası neden ve çözüm |
|---|---|
| Veritabanına bağlanılamıyor | Sunucu adı `database.py` varsayılanıyla uyuşmuyor olabilir. `LIFETRACK_SQL_SERVER` ortam değişkenini kendi sunucu adına ayarla. |
| `Data source name not found` hatası | ODBC Driver 17 for SQL Server kurulu değil ya da `LIFETRACK_ODBC_DRIVER` yanlış. |
| Giriş reddedildi | Windows hesabının `LifeTrack` veritabanında yetkisi yok. |
| PowerShell `Activate.ps1` çalıştırmıyor | `.venv\Scripts\activate.bat` dosyasını Komut İstemi'nde kullan. |
| "Windows gerekli" uyarısı | Otomatik takip yalnızca Windows 10/11 üzerinde çalışır. |