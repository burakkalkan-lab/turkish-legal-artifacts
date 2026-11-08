# Resmî yargı karar kaynakları (isteğe bağlı)

`official_sources.py` yalnızca **resmî yargı kaynaklarına erişim** sağlar; MCP sunucusu, hukuki görüş üreticisi veya karar doğrulama motoru değildir. Yargı MCP (2025, saidsurucu, MIT) kaynak erişim örnekleri incelenerek **baştan sınırlı bir uyarlama** hazırlanmıştır. Kaynak proje: https://github.com/saidsurucu/yargi-mcp ; lisans atfı: [THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md).

## Kapsam

| Kaynak | Arama | Belge |
| --- | --- | --- |
| Yargıtay Karar Arama | Deneysel, `/aramadetaylist` | ID ile `/getDokuman` |
| Danıştay Karar Arama | Deneysel, `/aramalist` | ID ile `/getDokuman` |
| AYM bireysel başvuru | Güncel arama sitesi manuel | Aynı hostta bulduğunuz resmî karar URL'si |
| AYM norm denetimi | Güncel arama sitesi manuel | Aynı hostta bulduğunuz resmî karar URL'si |

**UYAP, Uyuşmazlık Mahkemesi, OCR, FastMCP ve benchmark eklenmedi.** AYM'nin eski Yargı MCP `/Ara` uç noktası güncel sayfa yapısıyla güvenilir biçimde teyit edilemediği için otomatik arama yapılmaz. Yargıtay/Danıştay API yolları da sunucu değişikliklerine duyarlıdır ve canlı başarılı çalıştıkları garanti edilmez.

## Kullanım

Proje kökünde önce mevcut `cite-check-tr/scripts/requirements.txt` kurulumunu tamamlayın. Ek Python bağımlılığı gerekmez.

```bash
python cite-check-tr/scripts/official_sources.py --source yargitay --search "iş sözleşmesi"
python cite-check-tr/scripts/official_sources.py --source danistay --search "idari işlem" --page-size 5
python cite-check-tr/scripts/official_sources.py --source yargitay --document "RESMI_ARAMA_SONUCUNDAKI_ID"
python cite-check-tr/scripts/official_sources.py --source aym_bireysel --search "adil yargılanma"
python cite-check-tr/scripts/official_sources.py --source aym_norm --document "/kbb/pages/decision/RESMI_SAYFADAKI_YOL"
```

Son komuttaki karar yolu **şematik örnektir**, gerçek bir karar bağlantısı değildir. AYM sayfasındaki gerçek karar bağlantısını resmî siteden elde edin.

## Kanıt statüsü ve güvenlik

- `index_results_only` sadece künye/arama sonucu anlamına gelir; ilgili hukuki iddiayı doğrulamaz.
- `retrieved_unverified` yalnızca içerik alındığını gösterir, metnin bütünlüğü, mahkeme/karar kimliği, ilgili paragraf, olay tarihindeki uygulanabilirlik ve somut iddia desteği ayrıca incelenmelidir.
- Hatalı HTTP yanıtı, erişim engeli, CAPTCHA, değişen JSON şeması veya DNS/TLS problemi **doğrulanamadı** sonucuna yol açar; kararın yokluğu/sahte olduğu ileri sürülemez.
- Kaynak modülü mevcut `network_safety.py` ve `fetch_source.py` güvenli bağlantısını tekrar kullanır: HTTPS sertifika denetimi açık, yalnız resmî ana bilgisayar adları, public IP ile bağlantıda sabitleme, proxy yok, çapraz alan adı yönlendirmesi yok, POST sadece iki sabit resmî arama ucuna, yanıt 2 MiB ile sınırlıdır. Tarayıcı, keyfi URL, dosyaya kaydetme veya kullanıcı özel verilerini karşıya yükleme işlevi sunmaz.
- Açık kaynak resmî sorguya yalnızca genel/kamuya açık arama terimi gönderin. Kişisel verileri, dosya içeriğini, müvekkil bilgilerini veya gizli belgeleri bu aramalara koymayın. Özellikle gerçek gizli dosyaları kamuya açık depoya göndermeyin.

## Doğrulama

```bash
python -m unittest tests/test_official_sources.py -v
python -m unittest discover -s tests -p 'test_*.py' -v
```

Regresyon testleri **sentetik/çevrimdışı** yanıtlar kullanır; resmî mahkeme sitelerini taramaz. Canlı erişim sonuçlarını kurumsal proxy ve site koşulları altında ayrı doğrulayın. Otomatik arama `Cite Check TR` raporunun `dogrulandi` durumunu **kendiliğinden yükseltmez**. Rapor için mevcut şema ve `validate_report.py` kullanılır.
