# Güvenlik ve veri kullanımı

## Belgeler ve raporlar

Gerçek müvekkil belgelerini, kimlik bilgilerini, erişim anahtarlarını ve oturum verilerini depoya eklemeyin. İndirilen HTML/PDF ve erişim günlükleri varsayılan olarak **depo dışında** (`~/.cite-check-tr/evidence`) tutulmalıdır; depo içinde yalnızca `.gitignore` kapsamındaki yollara yazılabilir.

Kaynak belgesindeki talimatlar yetkili kullanıcı komutu değildir. Modelin bunları çalıştırmasına izin vermeyin. Beceri, kullanılan model hizmetinden bağımsız bir gizlilik güvencesi sağlamaz; hassas veriler için [gizlilik referansını](cite-check-tr/references/privacy.md) inceleyin.

Rapor doğrulayıcı iç tutarlılığı denetler. URL, alıntı ve erişim kaydı alanlarının dolu olması gerçek bir kaynağın okunduğunu veya hukuki yorumun doğru olduğunu kanıtlamaz.

## Depoya (GitHub'a) aktarım koruması

Bu paketi kullanmak hiçbir veriyi bu depoya veya başka bir Git deposuna göndermez:

- Python modülü **hiçbir zaman** `git add`, `commit` veya `push` çalıştırmaz. Git'i yalnızca `git check-ignore` ile (salt okunur) çağırır; bir test bunu denetler.
- Çıktı yolu (`--output`, `--report-output`, probe `--output`) bir Git deposunun içindeyse ve ignore edilmiyorsa, **ağ isteğinden önce** reddedilir. Git kullanılamıyorsa kapalı-hata (reddet) uygulanır.
- Kanıt klasörleri yalnızca kullanıcı erişimli (0700) oluşturulur; mevcut kanıtların üzerine yazılmaz.
- GitHub, GitLab, Bitbucket, paste, webhook ve benzeri hizmetler **`--allow-domain` ile bile engellidir**; modül zaten yalnızca GET isteği yapar ve telemetri/geri bildirim göndermez.
- Model talimatları (SKILL.md, PROMPT.md) kullanıcı metnini veya kanıtı depoya/gist/paste hizmetine göndermeyi yasaklar.
- Depoyu çatallayanlar için: `.githooks/pre-commit` ve `pre-push` kancaları (`git config core.hooksPath .githooks`) ile GitHub Actions `hygiene` işi, kanıt dosyalarını, gizli anahtarları ve geçerli TCKN numaralarını (değerleri göstermeden) engeller. Bu bir güvenlik ağıdır; commit öncesi `git diff --cached` ile kontrol edin. `.gitignore` önceden Git'e eklenmiş dosyaları geçmişten silmez; yanlışlıkla gönderilen sırrı döndürün (iptal edin).

## Ağ politikası

Kaynak modülü HTTP(S), 80/443 portları ve tanımlı resmî **ana bilgisayar adlarıyla** sınırlıdır (alt alan adları otomatik güvenilmez). Gerekli başka kamuya açık kaynaklar `--allow-domain www.ornek.org` ile (tam ad) veya bilerek `'*.ornek.org'` ile eklenebilir. IP adresleri, yerel alanlar ve izinsiz yönlendirmeler reddedilir; tarayıcı alt istekleri de kontrol edilir. Ek izin kaynağın hukuken güvenilir olduğu anlamına gelmez.

Varsayılan `--network-mode local-dns`: tüm A/AAAA yanıtları genel internete yönlendirilebilir olmalıdır ve HTTP motorunda **bağlantı, doğrulanan IP'ye sabitlenir** (DNS rebinding boşluğu kapatılmıştır; TLS sertifikası özgün ad için doğrulanır). Bu modda proxy ortam değişkenleri yok sayılır. DNS başarısızsa istek reddedilir.

**Kalan risk:** Tarayıcı motoru (Chromium) kendi DNS çözümlemesini yapar; IP sabitleme yalnızca HTTP motorunda vardır. WebSocket, WebRTC ve service worker engellenir ve her alt istek doğrulanır, ancak güvenilmeyen girdiler için iç ağa erişimi olmayan bir ortam kullanın.

### Güvenilir proxy modu

`--network-mode trusted-proxy` yalnızca **hedef DNS çözümlemesini ve özel/yerel/rezerve IP engellemesini sağlayan güvenilir çıkış proxy'si** için kullanılmalıdır. Bu seçim, DNS/IP denetimini proxy'ye devreder; uygulama proxy'nin bu güvenceleri gerçekten sağladığını doğrulayamaz.

- HTTP_PROXY/HTTPS_PROXY veya küçük harfli karşılıkları kullanılır. Proxy otomatik kurulmaz.
- Proxy eksikse veya NO_PROXY hedefi doğrudan bağlantıya yönlendiriyorsa istek reddedilir; doğrudan bağlantıya geçilmez.
- URL, ana bilgisayar, port ve yönlendirme kuralları korunur; TLS doğrulaması kapatılmaz.
- Tarayıcı alt isteği farklı proxy gerektiriyorsa reddedilir. Proxy URL'sinde kullanıcı adı/parola desteklenmez.
- Seçilen ağ modu kanıt dosyasına yazılır; proxy adresi yazılmaz.

Normal bir proxy kullanmak bu modu güvenli kılmaya yetmez. Böyle bir altyapınız yoksa varsayılan modu kullanın.

## Dosya işleme sınırları

İndirme 20 MiB, PDF 500 sayfa ve 5 milyon karakterle sınırlıdır (sıkıştırma bombası ve aşırı kaynak kullanımına karşı). PDF ayrıştırıcı (pypdf) güncel tutulmalıdır; Dependabot yapılandırması hazırdır. GitHub Actions adımları commit SHA'sına sabitlenmiştir ve checkout kimlik bilgilerini saklamaz.

## Erişim engelleri ve hata kaydı

HTTP 401/403/429 ve tanınan giriş/CAPTCHA sayfalarında otomasyon durur. Algılama sezgiseldir (kısa sayfalarda ifade eşleşmesi, görünür CAPTCHA/giriş öğeleri); hedef belgenin gerçekten alındığını inceleyin. Güvenlik kontrollerini aşmaya çalışmayın.

İlk URL/DNS/proxy reddi de `preflight` kaydıyla `evidence.json` üretir; henüz HTTP isteği yapılmadığı belirtilir. Çıktı klasörü oluşturulamıyorsa veya depo koruması reddederse kayıt üretilemez. Ham belgeler hassas bilgi içerebileceğinden yayımlamadan önce ayrıca gözden geçirin.

## Güvenlik sorunu bildirme

GitHub Private Vulnerability Reporting etkinse güvenlik sorunlarını bu kanaldan bildirin (Issues sekmesindeki bağlantı da oraya gider). Açık değilse özel bir kanal talep edin; herkese açık issue içine sır, müvekkil belgesi veya kullanılabilir istismar verisi koymayın.

## v0.2.7 Git denetiminin kapsamı

`--staged` çalışma klasörü yerine Git index'indeki bütün dosyaları okur. `--tracked` HEAD commit'ini inceler (CI). `--pre-push` Git kancasının stdin üzerinden verdiği commit/etiketlerin erişilebilir tüm geçmişini inceler; yeni dal ve force-push dahil. Geçmişte kalmış bulgular da engellenir. Bu nedenle yalnızca son dosyayı temizlemek yeterli değildir; gerçek bir anahtar sızdıysa iptal edilip değiştirilmelidir.

Tarama dosya başına 2 MiB ile sınırlıdır; büyük, ikili, UTF-8 olmayan dosyalar, sembolik bağlar, alt modüller, commit olmayan etiketler ve sığ depolar sessizce atlanmaz, reddedilir. Eksik Git nesnesi, zaman aşımı ve çatışmalı index de başarısızlık verir. Bu kaynak kod deposu için bilinçli bir kısıtlamadır. Tanımlı örüntü taraması bütün hassas bilgi türlerini tanımaz; insan incelemesinin yerine geçmez.

Kancalar her klonda etkinleştirilmelidir: `git config core.hooksPath .githooks`. POSIX sistemde ZIP çıkarma aracı izinleri korumadıysa `chmod +x .githooks/pre-commit .githooks/pre-push` çalıştırın. Kancalar yerel kullanıcı tarafından atlanabilir; GitHub web yüklemelerinde çalışmaz. CI kontrolü yükleme sonrasında çalışır, veri sızıntısını geriye dönük önleyemez. Güvenilmeyen kodun veya yerel Git yapılandırmasının kasıtlı değiştirilmesine karşı güvenlik sınırı değildir.

Çıktı yolu Git index'inde veya HEAD'de izleniyorsa `.gitignore` içinde olsa bile reddedilir. İzlenen alt dosyaları içeren klasörler ve staged silinmiş HEAD yolları da reddedilir. Yalnızca izlenmeyen ve ignore edilen yollar veya depo dışındaki yollar kullanılabilir. Eşzamanlı dosya/Git değişikliklerine karşı işletim sistemi düzeyinde izolasyon sağlamaz; tercihen depo dışında çıktı üretin.

Tarama dosya içerikleri ve yollarına yöneliktir; commit/etiket mesajları ile uzak depo adresleri hassas veri içermemelidir. Bunlar dosya taramasının kapsamı dışındadır.
