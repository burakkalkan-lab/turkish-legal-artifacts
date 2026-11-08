# Testler ve kapsam

Bağımlılıkları [kurulum rehberindeki](getting-started.md) gibi yükledikten sonra proje kökünde:

```bash
python tests/verify_release.py
python -m unittest discover -s tests -p 'test_*.py' -v
```

İlk komut paket dosyalarını, sürümü ve örnek raporları doğrular. İkincisi yerel HTTP, PDF, ağ politikası, komut satırı ve rapor testlerini çalıştırır. Varsayılan çalışmada dört tarayıcı testi atlanır. Çıktı koruması testleri `git` gerektirir (yoksa atlanır). Depo hijyeni: `python tools/check_repo_hygiene.py --tree`.

Tarayıcı testleri için `python -m playwright install chromium` çalıştırın ve `CITE_CHECK_TEST_BROWSER=1` ayarlayın. macOS/Linux:

```bash
CITE_CHECK_TEST_BROWSER=1 python -m unittest discover -s tests -p 'test_*.py' -v
```

PowerShell:

```powershell
$env:CITE_CHECK_TEST_BROWSER='1'
python -m unittest discover -s tests -p 'test_*.py' -v
```

Mevcut Chromium için `CITE_CHECK_BROWSER_PATH` tam dosya yolunu gösterebilir. Testler yerel HTTP sunucusu başlatır; ağ soketlerini engelleyen sandbox dışında çalıştırmanız gerekebilir. Yerel testlerde URL güvenlik denetimi kontrollü biçimde taklit edilir; üretim kodunun güvenlik politikası değiştirilmez.

## GitHub Actions

İş akışı Linux üzerinde Python 3.11, 3.12 ve 3.13; Windows ve macOS üzerinde Python 3.12 birim testleri, ayrıca Linux Chromium işi içerir. CI canlı resmî sitelere istek göndermez. İş akışı dosyasının bulunması GitHub üzerinde başarıyla çalıştığını göstermez; yayın sonrası Actions sonucuna bakın.

## Manuel kabul kontrolü

- Beceri uyumlu ortamda keşfediliyor mu? Çevrimdışı sentetik örneğe kanıtsız doğrulandı sonucu veriyor mu?
- Canlı kaynak açıldığında hedef metin gerçekten okunuyor mu? Ana sayfa ve karar metni ayrılıyor mu?
- Aynı atfa bağlı farklı iddialar ayrı bulgu oluyor mu?
- Geçmiş olay için yürürlük/geçiş hükümleri, eksik karar için künye ihtiyacı belirtiliyor mu?
- Belge içindeki komut görünümlü metinler talimat olarak uygulanmadan kalıyor mu?

## Örnekler

`expected-offline-report.json` sentetik çevrimdışı örnektir. `live-report-2026-11-08.json` geçmiş bir denemenin şema testi için saklanan örnek raporudur; güncel erişim veya otomatik hukuki başarı kanıtı değildir. Test kodundaki sentetik olumlu raporlar da gerçek mahkeme kararları değildir.

## v0.2.4 doğrulama durumu — 8 Kasım 2026

- Python 3.12 ve 3.13 için sistem paketlerini devralmayan iki yeni sanal ortam, yalnızca requirements.txt ile kuruldu. 3.13 kurulumunda pip sürücüsünün --python seçeneği kullanıldı.
- Her iki ortamda ayrı ayrı **54/54 test geçti**. Sistem Chromium'u ile dört tarayıcı testi dahil; atlanan test yok.
- pip check, paket bütünlüğü, sürüm, şema ve örnek rapor kontrolleri geçti.
- Geçersiz URI, kaynak/başvuru/erişim kaydı URL'leri, kodlanmış URI, null kaynak ve eksik denetleyici senaryoları test edildi. Biçim denetleyicisi eksikse kurulum hatası veriliyor.
- Canlı 6098 sayılı Kanun PDF'si trusted-proxy modunda indirildi; erişim kaydı örnek rapora eklendi ve rapor doğrulamadan geçti.
- Mevzuat arama formuna Chromium ile 6098 yazıldı, sonuç tablosu yüklendi ve kaydedildi.
- Yerel Markdown bağlantıları ve dağıtım arşivi kontrol edildi. Geçici çıktılar, sanal ortamlar ve indirilmiş hukuk belgeleri dağıtıma dahil edilmedi.

GitHub Actions gerçek bir depoda henüz çalıştırılmadı. Python 3.11, Windows ve macOS çalışmaları yayın sonrası CI matrisinde yürütülmelidir; yerel başarı bunların geçtiği anlamına gelmez.

Bu testler hukuki doğruluk benchmark'ı değildir. OCR, bütün resmî sitelerin bağlayıcıları ve her AI ürünündeki otomatik Skill aktivasyonu sınanmış değildir. Kaynak indirme hukuki doğrulama yerine geçmez. trusted-proxy yalnızca belgelenen güvenilir çıkış altyapısı koşullarında kullanılmalıdır.

## v0.2.5 insan denetimi kontrolü

Python 3.12 ve sistem Chromium ile 55/55 test geçti; atlama yok. İnsan denetimini kapatan JSON raporunun reddedildiği sınandı. 35 dosyalık paket ve örnek rapor doğrulaması geçti. Bu sürümde Python 3.13 ve GitHub Actions yeniden çalıştırılmadı.

## v0.2.6 güvenlik sürümü doğrulaması

Python 3.12 ile 78 test geçti, 4 tarayıcı testi atlandı (Chromium bu ortamda çalıştırılmadı; tarayıcı sertleştirmesi sahte Playwright nesneleriyle birim testlendi). Kapsam: bağlantı anında DNS rebinding reddi, IPv4-eşlemeli IPv6 loopback reddi, tam ana bilgisayar izin listesi ve `*.` ile açık alt alan adı izni, GitHub/GitLab/paste/webhook engel listesi, yerel DNS modunda proxy yok sayma, Git deposu içi çıktı reddi (ağ isteği yapılmadan), 0700 kanıt klasörü, PDF sayfa sınırı, uzun metinde yanlış CAPTCHA algısı, betiklerin `git push`/kod barındırma çağrısı içermediği ve hijyen aracının gizli bilgi/TCKN/kanıt dosyası yakalaması. pip-audit ve bandit temiz. GitHub Actions gerçek bir depoda henüz çalıştırılmadı.

## v0.2.7 — yeniden üretilen açıkların regresyon kontrolü

Python 3.12, requirements.txt ile kurulu izole ortam ve sistem Chromium ile **99/99 test geçti; atlama yok**. 21 yeni test; index ile çalışma dosyasının farklı olması, çalışma dosyasının silinmesi, HEAD/index ayrımı, geçmişte silinmiş sırlar, yeni dal, force-push, commit etiketi, eksik nesne, sığ geçmiş, çatışmalı index, ikili/büyük dosya, Git hatası ve izlenen-ignore edilen çıktı yollarını kapsar.

Gerçek pre-commit kancası commit'i engelledi. Gerçek pre-push kancası yalnızca yerel geçici bare depoya yapılan denemede geçmişteki sentetik gizli bilgiyi engelledi; hedef depoda hiçbir ref oluşmadığı doğrulandı. Gerçek anahtar veya müvekkil verisi kullanılmadı; dış depoya gönderim yapılmadı.

47 gerekli dosya, örnek raporlar, sürüm ve depo hijyen denetimi geçti. Python 3.11/3.13, Windows/macOS ve GitHub Actions bu sürüm için burada çalıştırılmadı. Bu sonuçlar bütün hassas bilgilerin yakalanacağı veya sistemin açığı bulunmadığı garantisi değildir.
