# Cite Check TR — Hukuki atıf benchmark'ı (ön sürüm 0.1)

Gerçek resmî kaynaklara dayalı, yeniden yazılmış 9 vaka içerir. Müvekkil verisi içermez. İlk yayımlanan metin ile güncel konsolide mevzuat **aynı şey değildir**.

**DURUM: PROVISIONAL — BAĞIMSIZ HUKUKÇU İNCELEMESİ BEKLİYOR.** Sonuçlar hukukî doğruluk başarı oranı, sertifikasyon veya bilimsel geçerlik iddiası değildir.

## Dosyalar

- cases.json: Modelin görebileceği kısa vaka, kaynak bağlantısı ve talimatlar; beklenen sonuç bulunmaz.
- gold.json: Ön değerlendirmeyle belirlenen beklenen sonuçlar. Modele göstermeyin.
- ../../tools/evaluate_benchmark.py: Modelin tam v0.2.7 JSON raporlarını yapı kontrolünden geçirip sınıf uyumunu puanlar. LLM veya internete kendisi bağlanmaz.

## Kullanım

1. docs/getting-started.md içindeki requirements bağımlılıklarını kurun.
2. cases.json içindeki her vaka için text ve prompt'u ayrı model oturumuna verin; uygun resmî kaynağa gerçekten erişilip erişilmediğini ayrıca kontrol edin.
3. Her vakanın **tam v0.2.7 JSON raporunu** predictions dizisinde, {"id":"LCT-001","report":{...}} şeklinde kaydedin. Tüm 9 kimlik birer kez bulunmalı; her raporda tek bulgu olmalı.
4. Depo DIŞINDA, kişisel veri içermeyen tahmin dosyasını değerlendirin:

    python tools/evaluate_benchmark.py --predictions /path/to/predictions.json

İsteğe bağlı --output bir özet üretir; ham müvekkil verisi veya kanıt dosyalarını yayımlamayın.

## Metrikler ve sınırlar

- accuracy: Doğru sınıflandırılan vaka oranı.
- macro_f1: Dört sınıfın F1 değerlerinin eşit ağırlıklı ortalaması.
- confusion_matrix: Beklenen sınıf (satır) × tahmin edilen sınıf (sütun).
- unsupported_verified_count: Beklenen sonuç dogrulandi değilken modelin dogrulandi dediği vaka sayısı.
- unsupported_verified_fraction: dogrulandi tahminleri içindeki söz konusu yanlış kesinliklerin payı; hiç dogrulandi tahmini yoksa null döner.

Yapısal şema denetimi, açılmış gibi gösterilen URL'nin gerçekten açıldığını, kaynak metninin sahih olduğunu veya model yorumunun hukuken doğru olduğunu **kanıtlamaz**. Çevrimdışı modelin dogrulanamadi demesi erişim sınırından kaynaklanabilir; internet erişimi ile hukukî muhakeme başarısı ayrı raporlanmalıdır.

## Hukukçu onayı protokolü

Etiketleri yayımlanmış doğrulanmış benchmark olarak sunmadan önce iki bağımsız yetkili hukukçu incelemesi, uyuşmazlıkta üçüncü hakem, delil URL'si, ilgili madde/paragraf, erişim ve olay tarihi, tarihsel yürürlük/geçiş hükmü denetimi gerekir. Sonuçlar ve gerekçe kamuya açıkça belgelenmelidir.

## Başvuru kaynakları

- 6098 (2011 ilk yayımlanma): https://resmigazete.gov.tr/eskiler/2011/02/20110204-1.htm
- 4857 (2003 ilk yayımlanma): https://www.resmigazete.gov.tr/eskiler/2003/06/20030610.htm
- 6698 (2016 TBMM kabul metni): https://cdn.tbmm.gov.tr/KKBSPublicFile/D26/Y1/T1/KanunMetni/49b3460d-3d92-413d-9a12-555cfa749b1f.html
- KVKK 2022/662 karar özeti: https://www.kvkk.gov.tr/Icerik/7399/2022-662

Arama sonucunda bulunamayan kararın sahte olduğu varsayılmaz. Resmî kanun metinleri üzerindeki telif ve veri yeniden kullanım koşulları ayrı değerlendirilir.
