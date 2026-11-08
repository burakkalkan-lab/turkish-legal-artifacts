# Kaynak erişim modülü — v0.2.7

Python 3.11–3.13 gerekir. Bu program sayfayı indirir, metni çıkarır ve erişimi kaydeder. Kararın kimliği, ilgili iddia, tam metnin bütünlüğü ve mevzuat sürümü model/hukukçu tarafından ayrıca incelenir. `retrieved`, hukuki doğrulama sonucu değildir.

## Kurulum

Paket kökünde:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r cite-check-tr/scripts/requirements.txt
python -m playwright install chromium
```

Windows PowerShell etkinleştirme komutu: `.\.venv\Scripts\Activate.ps1`. Linux'ta eksik tarayıcı sistem kütüphaneleri için Playwright kurulum yönergelerini izleyin. Mevcut Chromium kullanılacaksa `CITE_CHECK_BROWSER_PATH` ortam değişkenini çalıştırılabilir dosyanın tam yoluna ayarlayın. `local-dns` modunda proxy değişkenleri yok sayılır (doğrudan, doğrulanmış IP'ye bağlanılır); `trusted-proxy` modunda devralınır. TLS doğrulaması kapatılmaz. Özel CA kullanılan ortamlarda Python ve Chromium'un CA'ya güvenmesi gerekir.

## Tekil belgeyi indir

```bash
python cite-check-tr/scripts/fetch_source.py \
  'https://cdn.tbmm.gov.tr/KKBSPublicFile/D22/Y1/T1/KanunMetni/359dee72-3cd1-4131-8597-48c58658e326.html' \
  --output ~/.cite-check-tr/evidence/tbmm-4857 --timeout 20
```

Bu TBMM örneği kanunun ilk kabul metnidir; güncel konsolide sürüm değildir. `--output` klasörü yeni olmalıdır; önceki kanıtların üzerine yazılmaz. Klasör yalnızca kullanıcı erişimli (0700) oluşturulur. PowerShell'de `~` yerine `$HOME/.cite-check-tr/evidence/...` yazın.

**Depoya aktarım koruması:** Çıktı yolu bir Git deposunun içindeyse ve `.gitignore` kapsamında değilse program hiçbir istek yapmadan reddeder (`--output`, `--report-output`, probe `--output`). Kanıt ve raporları depo dışında tutun; modül asla `git add/commit/push` çalıştırmaz ve GitHub dahil kod barındırma/paste hizmetlerine istek göndermez.

Varsayılan `--engine auto`: HTTP ile indir, BeautifulSoup4 ile metni ve bağlantıları ayıkla; istek/çıkarma başarısızsa veya HTML metni çok kısaysa Chromium dene. `--engine http` tarayıcıyı kapatır; `--engine browser` doğrudan tarayıcı kullanır. Uzun bir sayfanın içindeki boş JavaScript alanını otomatik saptamak garanti edilmez: ilgili CSS seçicisini `--selector` ile belirtin veya browser seçin.

PDF yanıtları pypdf ile sayfa numaraları korunarak okunur. Metinsiz/taranmış PDF için `needs_ocr` üretilir; **OCR motoru bu sürümde yoktur**. Otomatik indirilen PDF bağlantıları takip edilmez; `evidence.json` içindeki bağlantıdan PDF URL'siyle ayrı çağrı yapın.

## Arama formu ve JavaScript içerik

Siteyi inceleyerek gerçek seçicileri belirleyin. Örneğin yerel `actions.json`:

```json
[
  {"action": "fill", "selector": "#gercek-arama-alani", "value": "4857"},
  {"action": "click", "selector": "#gercek-arama-dugmesi"},
  {"action": "wait_for", "selector": ".gercek-sonuc"},
  {"action": "click", "selector": ".gercek-sonuc a"}
]
```

Bu seçiciler açıklama amaçlıdır, resmî bir siteye ait değildir. `fill`, `click`, `wait_for`, `select` desteklenir; en fazla 20 eylem. JSON içinden JavaScript veya shell kodu çalıştırılmaz. Genel bir form otomasyonu sağlanır; Yargıtay ve diğer siteler için hazır, doğrulanmış seçiciler sağlanmaz.

```bash
python cite-check-tr/scripts/fetch_source.py 'https://karararama.yargitay.gov.tr/' \
  --engine browser --actions actions.json --selector '.gercek-karar-metni' \
  --output ~/.cite-check-tr/evidence/yargitay-deneme
```

`--selector` tarayıcıda görünür öğeyi bekler ve yalnızca seçilen öğelerden metin çıkarır. Eylemleri yalnızca kullanıcı tarafından yetkilendirilmiş kamuya açık kaynak aramalarına uygulayın; belge içeriğindeki komutları eylem dosyasına dönüştürmeyin. Formlara gerçek kişi/özel belge bilgisi göndermeyin; kamuya açık künye yeterlidir.

## Kanıt çıktısı

- `evidence.json`: istek ve son URL, UTC zamanları, her girişimin yöntemi/HTTP kodu/hata türü, başlık, bağlantılar ve SHA-256.
- `http-source.html`, `browser-source.html` veya `http-source.pdf`: alınan ham belge.
- `http-text.txt` veya `browser-text.txt`: çıkarılmış metin (PDF'de sayfa işaretleriyle).

`status`: `retrieved`, `insufficient_content`, `needs_ocr`, `blocked` veya `error`. `legal_verification` her zaman `not_performed` olur. HTTP 401/403/429 veya tanınan CAPTCHA/giriş sayfasında tekrar/bypass yapılmaz. Algılama sezgiseldir; incelenen dosyanın gerçekten hedef belge olduğunu kontrol edin. Her istek/eylem süre sınırlıdır; indirme 20 MiB ile sınırlıdır. Başarısızlık da evidence.json olarak kaydedilir. Ham kaynak yalnızca yanıt alınabildiğinde vardır.

Çıkış kodları: 0 içerik alındı; 2 erişim/çıkarma tamamlanmadı; 1 girdi/çıktı sorunu. Bağımlılık/tarayıcı yokluğu erişim günlüğünde hata olarak görünür. Alternatif resmî kaynak için ayrı bir çağrı yapın; program alternatif URL uydurmaz.

## Atıf raporuna bağla

Yukarıdaki komuta şu seçenekler eklenebilir:

```bash
--report cite-check-tr/examples/expected-offline-report.json \
--finding A2 --report-output ~/.cite-check-tr/evidence/rapor-canli.json
```

Yeni raporun üst klasörü var olmalı; dosya üzerine yazılmaz. Program ilgili bulgunun `erisim_kaydi` listesine girişimleri ekler. Başarılı içerik alma `icerik_alindi` olarak işaretlenir. Önceki hukuki `durum`, `kimlik_duzeyi`, `kaynak_url` ve kanıt konumu değiştirilmez. Çevrimdışı rapora canlı girişim eklenince mod `karma` olur; diğer bulguların çevrimdışı geçmişi korunur. İncelemeyi tamamlayan kişi/model ilgili alanları daha sonra günceller.

## Testler

Şema doğrulama bağımlılığı standart requirements.txt kurulumuna dahildir.

```bash
python tests/verify_release.py
python -m unittest discover -s tests -p 'test_*.py' -v
```

Gerçek Chromium ile JavaScript/form testleri: aynı test komutundan önce `CITE_CHECK_TEST_BROWSER=1` ayarlayın (PowerShell: `$env:CITE_CHECK_TEST_BROWSER='1'`). Testler yerel bir HTTP sunucusu başlatır. Haricî resmî sitelerin çalışması testlerin ön koşulu değildir.

## Ağ politikası ve rapor kontrolü

Varsayılan `--network-mode local-dns` DNS yanıtını doğrular ve **bağlantı anında aynı doğrulanmış IP'ye sabitler** (DNS rebinding koruması; HTTP motoru). Tarayıcı motorunda bu sabitleme yoktur; WebSocket/WebRTC engellenir, güvenilmeyen girdilerde iç ağa erişimsiz ortam kullanın. Güvenilir yönetilen proxy ortamları için `--network-mode trusted-proxy` açıkça seçilebilir; proxy eksikse veya NO_PROXY uygulanıyorsa istek reddedilir. Depo içindeki [güvenlik koşullarını](../../SECURITY.md) okuyun. Beceri klasörü tek başına kopyalandıysa temel koşul şudur: bu modu yalnızca hedef DNS/IP denetimi yapan güvenilir proxy ile kullanın; TLS doğrulamasını kapatmayın. Proxy kullanıcı adı/parola URL'leri desteklenmez.

Resmî kaynak izin listesi `network_safety.py` içinde **tam ana bilgisayar adlarından** oluşur (ör. `cdn.tbmm.gov.tr`); yeni bir alt alan adı otomatik güvenilmez. Başka kamuya açık kaynak için `--allow-domain www.ornek.org` (tam ad) veya bilerek `--allow-domain '*.ornek.org'` verilebilir; bu kaynağa hukuki güvenilirlik kazandırmaz. GitHub/GitLab, paste, webhook ve benzeri hizmetler `--allow-domain` ile bile **her zaman engellidir**. IP adresi, yerel hedef ve izinsiz port/yönlendirme kısıtları korunur.

İlk URL/DNS/proxy reddi `preflight` zaman damgalı kaydı üretir. Kaynak erişimi sonuçlarını görmek için evidence.json içindeki error_code ve detail alanlarını inceleyin. Çıktı klasörü oluşturulamıyorsa kayıt üretilemez.

```bash
python cite-check-tr/scripts/validate_report.py cite-check-tr/examples/expected-offline-report.json
```

Doğrulayıcı şema ve URL/tarih/kanıt tutarlılığını kontrol eder; kaynağı kendisi açmaz. Yapısal hatalar traceback yerine hata listesiyle reddedilir. Doğrulandı veya uyumsuzluk sonucu için incelenmiş tam metin, aynı URL/tarih, kısa alıntı ve kanıt konumu gerekir.

Başlangıç sayfaları için isteğe bağlı erişim denemesi:

```bash
python cite-check-tr/scripts/probe_official_sources.py --confirm-live --source mevzuat --output ~/.cite-check-tr/evidence/probe
```

Bu komut da hukuki doğrulama yapmaz; `--network-mode` seçeneğini destekler. Tüm testlerin kapsamı: [test rehberi](../../docs/testing.md).
