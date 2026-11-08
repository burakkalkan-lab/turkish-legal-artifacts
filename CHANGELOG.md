# Değişiklik geçmişi

## v0.2.7 — Git içerik ve çıktı koruması

- Commit öncesi kontrol gerçek index bloblarını, CI HEAD commit ağacını okur; çalışma dosyaları sonucu değiştiremez.
- Pre-push gönderilen commit/etiketlerin erişilebilir tüm geçmişini denetler; sonraki committe silinen gizli bilgi de engellenir.
- Eksik nesne, sığ geçmiş, çatışmalı index, desteklenmeyen nesne/dosya türü ve tarama sınırı aşımında işlem reddedilir.
- Çıktı koruması index ve HEAD tarafından izlenen yolları ve alt dosyaları ignore kuralından önce reddeder.
- Gerçek yerel commit/push kancaları dahil 21 regresyon testi eklendi.


## v0.2.6 — güvenlik sürümü

- **DNS rebinding:** `local-dns` modunda HTTP bağlantısı, bağlantı anında çözümlenip doğrulanan genel IP'ye sabitlenir; yerel DNS modu proxy değişkenlerini yok sayar. IPv4-eşlemeli IPv6 adresleri de denetlenir.
- **İzin listesi:** resmî kaynaklar tam ana bilgisayar adlarıyla sınırlandı (alt alan adları otomatik güvenilmez); `--allow-domain` tam ad ister, alt alan adları için açıkça `*.` gerekir. Doğrulayıcı da aynı listeyi kullanır.
- **GitHub'a aktarım yok:** GitHub/GitLab/Bitbucket/paste/webhook alan adları `--allow-domain` ile bile engellendi; çıktı yolu ignore edilmeyen bir Git deposundaysa (`--output`, `--report-output`, probe) istekten önce reddedilir; kanıt klasörleri 0700; probe varsayılanı depo dışı `~/.cite-check-tr/evidence`. SKILL/PROMPT/gizlilik belgeleri depoya/gist'e gönderimi yasaklar.
- **Depo hijyeni:** `tools/check_repo_hygiene.py` (kanıt dosyası, gizli anahtar, URL içi kimlik bilgisi, TR IBAN, geçerli TCKN), `.githooks/pre-commit` ve `pre-push`, CI `hygiene` işi, sertleştirilmiş `.gitignore`, issue/PR gizlilik şablonları.
- **Tarayıcı:** WebSocket ve WebRTC engellendi; proxy yalnızca `trusted-proxy` modunda kullanılır.
- **PDF/HTML:** PDF 500 sayfa ve 5 milyon karakter sınırı; pypdf alt sürümü yükseltildi (≥6.21.4). CAPTCHA/erişim engeli ifade sezgisi yalnızca kısa sayfalara uygulanır (uzun karar metinlerinde yanlış pozitif giderildi).
- **CI:** GitHub Actions commit SHA'sına sabitlendi, `persist-credentials: false`, zaman aşımları, Dependabot (actions + pip).
- Örnek raporlardan araç izi ifadeleri temizlendi. Testler 55'ten 78'e çıktı.


## v0.2.5

- Yetkili hukukçunun nihai incelemesi rapor ve model talimatlarında açıkça zorunlu tutuldu.
- JSON doğrulayıcı uzman_onayi_gerekli=false değerini reddeder; regresyon testi eklendi.
- İnsan onayının teknik doğrulamadan ayrı olduğu belgelendi.

## v0.2.4 — 2026-11-08

- jsonschema URI biçim kontrolü için format-nongpl bağımlılıkları zorunlu kurulum kapsamına alındı.
- URI/tarih denetleyicisi yoksa doğrulayıcı açık kurulum hatasıyla durur; sessizce başarılı sonuç üretmez.
- Geçersiz URI, kodlanmış URL, null kaynak ve eksik denetleyici için regresyon testleri eklendi.
- GitHub Actions birim test matrisine Windows ve macOS eklendi.

## v0.2.3 — 2026-11-08

- GitHub paylaşımı için README, kurulum, test ve yayın rehberleri düzenlendi; tekrarlar birleştirildi.
- Oturum çıktıları ve tekrarlanan giriş belgeleri kaldırıldı; işlevsel testler korundu.
- jsonschema standart bağımlılıklara eklendi. Ağ ve hukuki doğrulama davranışı değiştirilmedi.

## v0.2.2 — 2026-11-08

- Varsayılan DNS/IP politikası korundu; güvenilir çıkış proxy’leri için açık trusted-proxy modu eklendi. Proxy eksikliği, NO_PROXY ve farklı tarayıcı proxy rotaları reddedilir.
- İlk URL/DNS/proxy reddi artık tarihli preflight kanıt günlüğü üretir.
- Şema hatasında semantik doğrulamaya geçilmez; bozuk alanlar ve URL’ler kontrollü hata verir.
- Regresyon testleri ve canlı HTTP/tarayıcı kabul testleri eklendi.

## v0.2.1 — 2026-11-08

- `dogrulandi`/`uyumsuzluk` için tam metin günlüğü, kanıt alıntısı, kaynak URL/tarih eşleşmesi zorunlu kılındı; JSON şeması güçlendirildi.
- Yeni `validate_report.py` yapı ve çapraz alan denetimi; eksik/uyuşmayan kanıtı reddeden testler eklendi.
- `network_safety.py`: resmî alan adı izin listesi, genel DNS/IP kontrolü, özel/yerel IP ile port sınırlaması, yönlendirme ve tarayıcı alt istekleri denetimi.
- Özel IP'ye yönlendirmeyi ve güvenilmeyen kanıt raporlarını test eden regresyon senaryoları eklendi.
- `SECURITY.md` çalıştırılabilir modül ve kalan riskleri açıklayacak biçimde yeniden yazıldı; `.gitignore` ve GitHub Actions CI tanımları eklendi.
- Üç resmî başlangıç kaynağı için kullanıcı onaylı `probe_official_sources.py` eklendi; erişim sonucu hukuki doğrulama değildir.
- Gerçek Claude/Codex yürütmesi ve resmî site arama formu uçtan uca testi bu sürümde henüz doğrulanmadı.


## v0.2.0 — 2026-11-08

- Çalıştırılabilir HTTP/BeautifulSoup4, Playwright ve PDF erişim modülü eklendi.
- Form eylemleri, CSS içerik seçicisi, ham kaynak/metin/SHA-256 kaydı ve rapora erişim günlüğü ekleme desteklendi.
- `icerik_alindi` erişim sonucu eklendi; indirme hukuki doğrulama sayılmaz.
- Karma raporlarda önceki çevrimdışı bulgular korunabilir; raporun en az bir bulgusunda canlı girişim bulunmalıdır.
- Yerel HTTP, JavaScript, form, PDF ve hata testleri eklendi.

## v0.1.2 — 2026-11-08

- Canlı kaynak denemesi varsayılan oldu; araç keşfi, tekil tam metni açma, resmî alternatif ve erişim hatası kaydı eklendi.
- JSON bulgularına zorunlu erisim_kaydi ve rapora erisim_basarisiz modu eklendi.
- Gerçek araç sonuçlarıyla canlı deneme raporu eklendi; tarihsel metnin güncel metin olmadığı açıklandı.

## v0.1.1 — 2026-11-08

- Her atıfa resmî başvuru kaynağı adı ve bağlantısı eklendi. Başvuru adresi ile incelenen belge kanıtı ayrıldı.
- Rapor şablonu, evrensel prompt, JSON şeması ve çevrimdışı örnek güncellendi. JSON bulgularında iki yeni zorunlu alan vardır.

## v0.1.0 — 2026-11-08

- Platformdan bağımsız `cite-check-tr` Agent Skill oluşturuldu.
- Kaynak delil seviyesi ile atıf iddiası ayrı tutuldu.
- Kaynak yokluğunda zorunlu `doğrulanamadı` yaklaşımı ve `JSON Schema` rapor biçimi eklendi.
- Claude Code, Codex, Claude.ai ve evrensel prompt kullanım yönergeleri eklendi.
- Sentetik çevrimdışı örnek, denetim scripti ve açık kaynak lisansı eklendi.

## Geliştirme dalı — resmî kaynak erişim modülü

- Dört resmî yargı kaynağı için dar kapsamlı `official_sources.py` CLI eklendi. Yargıtay/Danıştay deneysel arama ve belge alma; AYM için manuel arama yönlendirmesi ve güvenli karar URL'si alma.
- Kaynak arama ve içerik alma hukuki doğrulama olarak etiketlenmez. Testler sentetik yanıtlarla yapılır; resmî site erişim sözleşmesi ayrıca kontrol edilmelidir.
- Var olan TLS, IP sabitleme ve izin listesi korunur. Yargı MCP'nin bütünü, benchmark ve ek MCP sunucusu entegre edilmedi.
