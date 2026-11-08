# Katkı rehberi

- Hukuki doğrulama adımlarında **resmî kaynak, erişim tarihi, sürüm ve kanıt** kullanın.
- Sentetik örnekler tercih edin; gerçek müvekkil verisi, TCKN, telefon, adres, e-posta, dava dosyası veya erişim bilgisi göndermeyin.
- Yeni bir 'doğrulandı' kategorisi eklerken **kimlik ile içeriğin ayrı ispatını** ve yanlış pozitif riskini açıklayın.
- Mevzuat tarihsel incelemelerinde **olay tarihi–yürürlük–geçiş maddeleri** kontrolünü atlamayın.
- Resmî kararları toplu olarak depoya kopyalamayın; lisans, robots.txt, erişim koşulları ve veri korumaya dikkat edin.
- En az üç test: (1) doğrulanamayan sentetik atıf, (2) kimliği bulunan ama iddia desteği bulunmayan karar, (3) yürürlük tarihi belirsiz madde.
- Değişiklik açıklamasını CHANGELOG.md dosyasına ekleyin.
- Lisans metni ve atıf korunmalı.
- Commit öncesi `git config core.hooksPath .githooks` ile kancaları açın; elle de çalıştırabilirsiniz: `python tools/check_repo_hygiene.py --staged`. Kanıt (`evidence/`), indirilmiş kaynak, `.env`, anahtar ve geçerli TCKN içeren dosyalar engellenir.
- Güvenlik denetimlerini (ağ politikası, IP sabitleme, çıktı koruması, GitHub/paste engel listesi) zayıflatan değişiklikler reddedilir.

Kurulum: [docs/getting-started.md](docs/getting-started.md). Test komutları ve kapsam: [docs/testing.md](docs/testing.md). Hata bildirimine anonim/sentetik örnek, komut, sürüm ve beklenen/gerçek sonucu ekleyin.
