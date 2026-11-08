# Türkiye resmî hukuk kaynakları ve arama stratejisi

> Bu liste **erişim rehberidir**, otomatik bir API / veri bağlantısı değildir. Siteye erişim hakları, kullanıcı oturumu, arama yöntemi veya içerik kapsamı değişebilir. Resmî sayfa üzerinde bir arama yapmak ve tam kararı açmak **ayrı aşamalardır**.

| Kaynak | Resmî başlangıç adresi | Kullanım |
|---|---|---|
| Mevzuat Bilgi Sistemi | https://www.mevzuat.gov.tr/ | Kanun ve ikincil mevzuat; madde ve değişiklik kontrolü |
| T.C. Resmî Gazete | https://www.resmigazete.gov.tr/ | Yayımlanma, değişiklik ve yürürlük tarihleri |
| Yargıtay Karar Arama | https://karararama.yargitay.gov.tr/ | Yargıtay kararlarının kimlik ve tam metin araması |
| Danıştay Karar Arama | https://karararama.danistay.gov.tr/ | Danıştay kararlarının kimlik ve tam metin araması |
| AYM Kararlar Bilgi Bankası | https://kararlarbilgibankasi.anayasa.gov.tr/kbb/ | AYM bireysel başvuru ve norm denetimi kararları |
| Kişisel Verileri Koruma Kurumu | https://www.kvkk.gov.tr/ | KVKK ilke/kurul kararları, duyurular, rehberler |

## Kaynak kullanım önceliği

1. **Yetkili birincil kaynak ve tam metin:** Kararı veren mahkemenin/kurumun erişilebilir tam kararı, mevzuatın resmî yayımlanmış metni.
2. **Resmî kayıt/arama sonucu:** Kimliği doğrulamaya yardımcı olabilir ama **somut hukuki iddiayı doğrulamak için tek başına yetmez**.
3. **İkincil kaynak:** Akademik yayın/özel veri tabanı/avukatlık bülteni yalnızca keşif ve karşılaştırma için; resmî tam metin ile eşleştirilmeden kesin doğrulama yapılmaz.

Bu liste **yargı kaynaklarının kendi aralarında normlar hiyerarşisi** anlamına gelmez. Hukuki bağlayıcılık, normlar hiyerarşisi, kararın niteliği ve somut uyuşmazlık ayrıca incelenmelidir.

## Karar arama stratejisi

1. Kararın **mahkemesi + dairesi/kurulu** ile E./K. no. veya AYM başvuru numarasını ayır.
2. Mümkünse tarih ile yeniden ara. Kurum ve daire bilgisi çelişiyorsa işaretle.
3. Arama sonuçlarından **tekil kaydı** aç; mümkünse kararın tam metni ile başlık/karar numarasını karşılaştır.
4. Metinde ilgili ibare/paragrafı bul; **bağlamıyla** oku. Kararın aynı cümleyi kullanması, aynı sonuca ulaştığı anlamına gelmeyebilir.
5. Somut olaya uygulanabilirlikte karar tarihi, yargı kolu, olayın niteliği ve karşıt içtihatları not et.
6. Resmî karara erişemediysen `dogrulanamadi`; arama başarısızlığı **yokluk kanıtı değildir**.

## Mevzuat arama stratejisi

1. Kanun adı/numarası ve **madde/fıkra/bent** numarasını çıkar.
2. Yürürlük ve değişiklik geçmişini, olay ve dava tarihine göre incele.
3. Resmî Gazete yayımlanma ve yürürlüğe giriş tarihlerini gerektiğinde ayrı doğrula.
4. Geçici hükümler ve istisnalar incelenmeden geçmişe uygulanabilirlikte kesin yargıya varma.
5. Mevzuat metninin yalnızca genel anasayfasını açmış olmak, **belirli madde içeriğini doğrulamak değildir**.

## KVKK kararı

- İlke kararı/kurul kararı türünü, karar tarihi ve sayısını doğrula.
- Kurul kararının **özet** olarak yayımlandığı durumlarda tam gerekçe görünmeyebilir; yayımlanan özetten çıkarılamayan savları `uzman_incelemesi` veya `dogrulanamadi` olarak bırak.

## Log alanları

Kaynak türü; kurum; doğrudan kaynak URL'si (varsa); erişim tarihi; hangi alanı doğruladığı; metin içi dayanak; erişim sınırı. Kullanıcı isteği olmadan otomatik toplu tarama yapma.

## Alternatif resmî kaynak

TBMM (https://www.tbmm.gov.tr/) kabul edilen kanun metinleri için kullanılabilir. Aramayla bulunan tekil metni aç; kabul metninin sonraki değişiklikleri içermeyebileceğini kontrol et. Bir kurumun kopyasını güncel konsolide metin sayma.
