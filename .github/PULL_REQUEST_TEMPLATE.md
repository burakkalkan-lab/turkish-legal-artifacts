## Değişiklik

<!-- Ne değişti ve neden? CHANGELOG.md güncellendi mi? -->

## Gönderim öncesi kontrol

- [ ] Gerçek müvekkil verisi, TCKN, kişisel veri, API anahtarı/token veya kanıt dosyası (`evidence/`) eklemedim.
- [ ] `python tools/check_repo_hygiene.py --staged` ve `python -m unittest discover -s tests -p 'test_*.py'` başarılı.
- [ ] Güvenlik denetimlerini (ağ politikası, çıktı koruması) zayıflatmadım.
