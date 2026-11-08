# Turkish Legal Artifacts

Türk hukuku metinlerindeki mevzuat ve karar atıflarını kaynaklarıyla incelemek için **Cite Check TR** becerisi ve Python yardımcıları.

**v0.2.7 · Deneysel · MIT**

Bir kanun veya kararın varlığı ile metindeki iddiayı desteklemesi ayrı ayrı değerlendirilir. Kaynağı doğrulanamayan atıflar açıkça belirtilir. Çıktı hukuki görüş veya dava sonucu garantisi değildir.

## Ne yapar?

| Bileşen | İşlev |
|---|---|
| AI becerisi / prompt | Metindeki atıfları ve iddiaları ayırması, kaynaklarla karşılaştırması için modele talimat verir. |
| Kaynak erişim modülü | HTML/PDF indirir, metin çıkarır; gerektiğinde Playwright ile sayfa/form işlemleri yapar. |
| Rapor doğrulayıcı | JSON şemasını, kanıt alanlarını ve URL–tarih tutarlılığını kontrol eder. |

URI ve tarih biçim denetimleri standart kurulumda zorunludur; eksik bağımlılık varsa doğrulayıcı kurulum hatası verir.

Python modülü kendi başına hukuki iddia çıkarımı veya karar doğrulaması yapmaz. AI becerisi için uyumlu bir model ortamı; canlı inceleme için web erişimi gerekir.

## Hızlı başlangıç

Python yardımcıları için **Python 3.11–3.13** kullanın. ZIP'i açın veya bu depoyu klonlayın; proje kökünde:

```bash
python -m venv .venv
```

Ortamı macOS/Linux'ta `source .venv/bin/activate`, Windows PowerShell'de `.\.venv\Scripts\Activate.ps1` ile etkinleştirin. Ardından:

```bash
python -m pip install -r cite-check-tr/scripts/requirements.txt
python cite-check-tr/scripts/validate_report.py cite-check-tr/examples/expected-offline-report.json
```

Bu komut internete çıkmadan örnek raporun biçimini kontrol eder. Başarılı çıktı hukuki doğruluk onayı değildir.

[Kurulum ve iki kullanım yolu](docs/getting-started.md) · [Komut satırı rehberi](cite-check-tr/scripts/README.md)

## Beceriyle dene

`cite-check-tr/` klasörünü alt dosyalarıyla birlikte uyumlu aracın beceri dizinine kopyalayın. Codex proje dizini için örnek: `.agents/skills/cite-check-tr/`.

> Cite Check TR ile bu metindeki atıfları incele. Resmî kaynakları açmayı dene; kaynak kimliğini ve iddia desteğini ayrı değerlendir. Erişemediğin kaynağa doğrulandı deme.

Skill yüklemeyi desteklemeyen ortamlar için [PROMPT.md](cite-check-tr/PROMPT.md) ve ilgili referans dosyaları kullanılabilir. İlk denemeyi [sentetik metinle](cite-check-tr/examples/synthetic-input.txt) yapın. Açıkça çevrimdışı test seçerseniz [beklenen çevrimdışı rapor](cite-check-tr/examples/expected-offline-report.json) biçimini inceleyin.

## Sınırlar

- Resmî sitelerin erişilebilirliği ve form yapıları değişebilir. Hazır, tüm sitelerde çalışan karar arama bağlayıcıları yoktur.
- Taranmış PDF'ler için OCR yoktur; metin çıkarılamadığı raporlanır.
- Güncel mevzuatın geçmiş olaya uygulanabilirliği ayrıca incelenmelidir.
- Örnekler ve testler genel bir hukuki başarı oranı göstermez. Model çıktısı hukukçu denetimi gerektirir.
- Gerçek müvekkil belgelerini yüklemeden önce anonimleştirme ve kullandığınız hizmetin veri koşullarını değerlendirin.

## Belgeler

- [Testler ve bilinen sınırlar](docs/testing.md)
- [Güvenlik ve proxy koşulları](SECURITY.md)
- [Katkı rehberi](CONTRIBUTING.md)
- [GitHub yayınlama adımları](docs/publishing.md)
- [Değişiklik geçmişi](CHANGELOG.md) · [Lisans](LICENSE)

MIT lisansı depodaki özgün içerik içindir; bağlantı verilen hukuk metinlerinin haklarını kapsamaz. Projenin herhangi bir model sağlayıcısı veya kamu kurumuyla kurumsal bağı yoktur.

## İnsan denetimi ve nihai karar

Sistem bir ön inceleme raporu üretir. Kaynak ve iddia karşılaştırmasını, olayın hukuki değerlendirmesini ve çıktının kullanımını yetkili hukukçu nihai olarak denetler. `dogrulandi` bir bulgunun kaynakla desteklendiğini belirtir; hukukçu onayı anlamına gelmez.

JSON raporlarında `uzman_onayi_gerekli` daima `true` olmalıdır; doğrulayıcı `false` değerini reddeder. Bu bir insan onayı kimlik doğrulama sistemi değildir. Hukukçunun kimliği, inceleme tarihi ve kararı kurumun kendi iş akışında ayrıca kayıt altına alınmalıdır.

Public GitHub deposundaki araçlar kurulup kullanılabilir. Python kaynak indirme, HTML/PDF metni çıkarma ve rapor doğrulamada kullanılır. AI becerisi ayrıca uyumlu bir model ortamında çalıştırılır; varsa model/API ücreti bu pakete dahil değildir.

## İsteğe bağlı resmî yargı kaynakları modülü

Yargıtay ve Danıştay karar arama/indirme ile AYM bireysel başvuru ve norm denetimi için güvenli karar bağlantısı okuma desteği, ayrı bir Python aracı olarak sunulur. **Deneysel** API uç noktaları ve AYM manuel arama sınırı için [resmî kaynaklar kullanım rehberini](cite-check-tr/scripts/OFFICIAL_SOURCES.md) okuyun. Bu araç hukuki iddiaları kendiliğinden doğrulamaz ve yeni bir MCP sunucusu kurmaz.
