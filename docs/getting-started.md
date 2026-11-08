# Kurulum

İki kullanım yolu birbirinden bağımsızdır: beceri talimatlarını bir AI ortamında kullanabilir veya Python yardımcılarını komut satırından çalıştırabilirsiniz.

## 1. AI becerisi

`cite-check-tr/` klasörünü **assets, examples, references ve scripts dahil** uyumlu aracın beceri dizinine kopyalayın. Codex proje düzeyinde `.agents/skills/cite-check-tr/` yolunu kullanır. Paket kökünden macOS/Linux örneği:

```bash
mkdir -p .agents/skills
cp -R cite-check-tr .agents/skills/cite-check-tr
```

PowerShell:

```powershell
New-Item -ItemType Directory -Force .agents\skills | Out-Null
Copy-Item -Recurse .\cite-check-tr .\.agents\skills\cite-check-tr
```

Hedef klasör önceden varsa yedekleyip yeni sürümle değiştirin; aynı klasörü kendi içine kopyalamayın. Klasörü başka bir projeye yerleştiriyorsanız kaynak/hedef yollarını o projeye göre düzenleyin. Ortamın beceri listesinde `cite-check-tr` göründüğünü kontrol edin; gerekirse oturumu yeniden başlatın.

Codex örneği:

```text
$cite-check-tr Bu metindeki atıfları canlı kaynaklarla denetle; belirsizlikleri açıkça belirt.
```

Diğer Agent Skills uyumlu araçlarda aracın kendi yükleme yönergelerini izleyin. Otomatik aktivasyon her ürün/sürüm için test edilmemiştir. Skill desteği yoksa `cite-check-tr/PROMPT.md` ile `references/` belgelerini ve rapor şablonunu modele verin. İsteğe bağlı JSON için `assets/output-schema.json` dosyasını da sağlayın.

## 2. Python yardımcıları

Python 3.11–3.13 ve pip gerekir. Proje kökünde:

```bash
python -m venv .venv
```

Etkinleştirme:

- macOS/Linux: `source .venv/bin/activate`
- Windows PowerShell: `.\.venv\Scripts\Activate.ps1`

Etkinleştirme çalışmazsa komutlarda doğrudan `.venv/bin/python` veya Windows'ta `.venv\Scripts\python.exe` kullanabilirsiniz.

```bash
python -m pip install -r cite-check-tr/scripts/requirements.txt
python cite-check-tr/scripts/validate_report.py cite-check-tr/examples/expected-offline-report.json
```

Rapor doğrulayıcı URI/tarih denetleyicisi eksikliği bildirirse yukarıdaki requirements.txt kurulumunu tekrar çalıştırın; yalnız `jsonschema` kurmak yeterli değildir.

Tarayıcı otomasyonu kullanacaksanız:

```bash
python -m playwright install chromium
```

Linux'ta gereken sistem kütüphaneleri için Playwright'ın kurulum yönergelerini izleyin. Sistem Chromium'u kullanacaksanız `CITE_CHECK_BROWSER_PATH` değişkenini çalıştırılabilir dosyanın tam yoluna ayarlayın. Normal HTTP/PDF indirme tarayıcı gerektirmez; bu durumda `--engine http` seçin.

## İlk canlı indirme

```bash
python cite-check-tr/scripts/fetch_source.py https://www.mevzuat.gov.tr/MevzuatMetin/1.5.6098.pdf --engine http --output ~/.cite-check-tr/evidence/6098
```

`~/.cite-check-tr/evidence/6098` yeni bir klasör olmalı (PowerShell'de `$HOME/.cite-check-tr/evidence/6098`). Mevcut kanıtın üzerine yazılmaz. Kanıtlar depo dışında tutulur; Git deposu içindeki ignore edilmeyen yollar reddedilir. Başarılı indirme `retrieved` olarak kaydedilir; hukuki doğrulama yapılmış sayılmaz.

Yerel DNS çalışmıyorsa hata kaydını inceleyin. Yalnızca özel/yerel IP hedeflerini denetleyen güvenilir yönetilen proxy ortamlarında `--network-mode trusted-proxy` seçilebilir; otomatik etkinleşmez. [Koşullar](../SECURITY.md).

Depoyu çatallayıp katkı veriyorsanız commit'ten önce koruma kancalarını bir kez açın: `git config core.hooksPath .githooks`. Ayrıntılı seçenekler ve rapora erişim kaydı ekleme: [komut satırı rehberi](../cite-check-tr/scripts/README.md).
