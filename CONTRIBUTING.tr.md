# Mehteran'a katkı

[English](CONTRIBUTING.md)

Yardımınız için teşekkürler. Hata bildirimleri, çeviri düzeltmeleri, yeni şablonlar ve kod değişiklikleri memnuniyetle karşılanır.

## Başlamadan önce

- Küçük bir düzeltme için (yazım hatası, yanlış çeviri, açık bir hata) doğrudan pull request açın.
- Daha büyük bir değişiklik için (yeni bir özellik, yeni bir adım türü, çalıştırmaların işleyişinde bir değişiklik) önce bir issue açın. Sorunu ve planınızı anlatın; böylece kimse aynı işi iki kez yapmaz.
- Güvenlik sorunları için issue açmayın. [SECURITY.md](SECURITY.md) dosyasına bakın.

Yapacak bir iş mi arıyorsunuz? [ROADMAP.md](ROADMAP.md) maddeleri seviyesiyle (🟢 ilk katkı için iyi, 🟡 orta, 🔴 büyük) ve gereken becerilerle listeler. Birçoğu programlama gerektirmez.

## Mehteran'ı kaynak koddan çalıştırma

Mehteran yalnızca Python 3.11 ya da daha yenisini ister. Kurulacak paket ve derleme adımı yoktur.

```
git clone https://github.com/tolgabuyuktanir/Mehteran.git
cd Mehteran
./mehter ui          # Windows: mehter.cmd ui
```

## Pull request'ten önceki kontroller

CI ilk dört komutu Ubuntu, macOS ve Windows üzerinde çalıştırır. Birim testleri, son komut gibi dil dosyalarını da denetler. Hepsini önce kendi bilgisayarınızda çalıştırın:

```
python3 -m pip install ruff==0.4.10
ruff check mehteran tests
node --test tests/mehteran_markdown_test.mjs
python3 -m unittest discover tests
python3 -m mehteran.i18n_tools validate
```

Testler sahte bir yapay zekâ aracı kullanır ve ağa bağlanmaz. Bir hata düzeltmesi, düzeltme olmadan başarısız olan bir test içermelidir.

## Kod

- Kodu, yorumları, adları ve commit mesajlarını İngilizce yazın.
- Yalnızca Python standart kütüphanesini kullanın. Arayüz `mehteran/ui/` içinde düz JavaScript'tir; çatı (framework) ya da derleme adımı eklemeyin.
- Değişikliğinizin çevresindeki kodun üslubuna uyun. Değişikliği küçük tutun: kimsenin istemediği özellik eklemeyin.
- Başvuru belgesi ([docs/mehteran.md](docs/mehteran.md) ve [docs/mehteran.tr.md](docs/mehteran.tr.md)) her ekranı, ayarı ve API yolunu anlatır. Bunlardan birini değiştirdiğinizde iki dosyayı da güncelleyin.

## Arayüz metinleri ve çeviriler

Arayüz 18 dildedir. Metinler `mehteran/locales/<dil>.json` dosyalarındadır.

- Her yeni metnin İngilizce (`en.json`) ve Türkçe (`tr.json`) sürümü olmalıdır. Diğer diller bir metni boş bırakabilir; Mehteran o zaman İngilizce metni gösterir.
- Çevrilmiş bir metin, İngilizce metindeki `{name}` yer tutucularını korur.
- `python3 -m mehteran.i18n_tools coverage` her dilin ne kadar tamam olduğunu gösterir. `python3 -m mehteran.i18n_tools missing <dil>` eksik metinleri listeler.

**Yardım aranıyor:** İngilizce ve Türkçe dışındaki 16 dil yapay zekâ araçlarıyla çevrildi. Anadili konuşanlar bunları gözden geçirmedi. Bu dillerden birini konuşuyorsanız dosyasındaki metinleri düzeltip pull request açın. Küçük düzeltmeler de memnuniyetle karşılanır.

## Şablonlar

Yerleşik iş akışları `mehteran/templates/*.yaml` içindedir. İş akışı dosyası başvuru belgesinde anlatılır.

- `tier: core` bir şablonu "Buradan başlayın" grubuna koyar. Bu grubu küçük tutun (yaklaşık 20 şablon).
- Bir şablon ücretli API anahtarları istiyorsa, değişen web sitelerinde bir tarayıcı kullanıyorsa ya da dış bir hizmette paylaşım yapıyorsa `tier: experimental` kullanın. Arayüz o zaman "Deneysel" rozetini ve bir uyarı gösterir.
- Bir şablonun adı, açıklaması ve talimatları İngilizce ve Türkçe metin ister.

## Değerlendirme seti

`evals/cases.json` içindeki bir vakanın kullandığı bir şablonun talimatını değiştirdiğinizde, değerlendirme setini değişiklikten önce ve sonra çalıştırıp karşılaştırın:

```
./mehter eval --model claude/haiku --out before
# değişikliği yapın
./mehter eval --model claude/haiku --out after
./mehter eval --compare before/report-<zaman>.json after/report-<zaman>.json
```

Değerlendirme seti sizin yapay zekâ araçlarınızla gerçek model çağrıları yapar, yani kullanım hakkınızdan harcar. CI onu çalıştırmaz. Karşılaştırmanın sonucunu pull request'e ekleyin.

## Lisans

Katkıda bulunarak katkınızın [MIT Lisansı](LICENSE) ile lisanslanmasını kabul etmiş olursunuz.
