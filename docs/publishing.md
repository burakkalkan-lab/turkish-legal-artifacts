# GitHub'da paylaşma

Bu belge depo sahibinin yayınlama adımlarını açıklar. Hazırlanan dosyalar kendiliğinden GitHub'a yüklenmez.

1. GitHub'da `burakkalkan-lab` hesabınız altında `turkish-legal-artifacts` adlı bir depo oluşturun. Herkesin erişebilmesi için görünürlüğü **Public** seçin. Bu paket README, MIT lisansı ve .gitignore içerdiğinden başlangıçta bunları ayrıca oluşturmaya gerek yoktur.
2. ZIP içindeki `turkish-legal-artifacts/` klasörünün **içeriğini depo köküne** yükleyin. `.github/` ve `.gitignore` gizli dosyalarını da dahil edin. Depoda README'nin doğrudan görünmesi gerekir.
3. Actions sekmesindeki `Cite Check TR tests` iş akışını kontrol edin. İlk çalıştırma tamamlanmadan GitHub testlerinin geçtiğini duyurmayın.
4. Uygunsa Settings → Security bölümünde Private Vulnerability Reporting'i etkinleştirin.
5. Tests yeşil olduktan sonra `v0.2.7` etiketiyle GitHub Release oluşturup dağıtım ZIP'ini ekleyin. Sürümü deneysel olarak belirtin.

Git ile yükleme için, proje kökünde aşağıdaki komutları kendi depo adresinizle kullanın:

```bash
git init -b main
git add .
git diff --cached --stat
git commit -m "Prepare v0.2.7 public release"
git remote add origin https://github.com/burakkalkan-lab/turkish-legal-artifacts.git
git push -u origin main
```

Commit öncesi dosya listesini kontrol edin (`git config core.hooksPath .githooks` ile kancaları açarsanız `pre-commit` bunu otomatik yapar). `evidence/`, sanal ortamlar ve kişisel belgeler yüklenmemeli. ZIP'i yalnız başına depoya koymak yerine kaynak dosyalarını yükleyin; böylece kod ve belgeler okunabilir, CI çalışabilir.

Tarayıcıdan yüklemede depo sayfasındaki **Add file → Upload files** seçeneğini kullanın. Telefonda klasör veya gizli dosya seçimi desteklenmiyorsa bilgisayardan Git ile yükleyin. Yükleme sonrası `.github/workflows/tests.yml` dosyasının depoda bulunduğunu kontrol edin.

Depoyu oluşturup yükledikten sonra paylaşacağınız adres: `https://github.com/burakkalkan-lab/turkish-legal-artifacts`. Bu bağlantı, depo oluşturulup Public yapılmadan başkaları için çalışmayabilir. Kullanıcılar README'deki kurulum adımlarını izler; GitHub'a yüklemek tek başına çalışan bir web uygulaması oluşturmaz.

## Önerilen açıklama

> Türk hukuku atıflarının kaynak destekli incelenmesi için deneysel AI becerisi ve Python yardımcıları. Hukuki görüş veya otomatik doğruluk garantisi vermez.

## Yayın notu — v0.2.7

- Git kontrolleri çalışma dosyası yerine gerçek index/commit içeriklerini okur.
- Pre-push, gönderilen uçların erişilebilir bütün geçmişini denetler.
- İzlenen dosyalar ignore edilse bile çıktı olarak kullanılamaz.
- İnsan denetimi şartı korunur; nihai inceleme yetkili hukukçuya aittir.

Yüklemeden önce `python tools/check_repo_hygiene.py --tree` çalıştırın. Git kullanırken `git config core.hooksPath .githooks` ile kancaları etkinleştirin. Kancalar tarayıcıdan yüklemelerde çalışmaz. [Güvenlik kapsamı ve sınırlar](../SECURITY.md) ile [test sonuçlarını](testing.md) okuyun.
