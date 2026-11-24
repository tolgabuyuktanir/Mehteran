# Roadmap

[Türkçe](#yol-haritası)

These are improvements that are planned but not started. Anyone can take one. Before you start, open an issue that names the item, so that two people do not do the same work. [CONTRIBUTING.md](CONTRIBUTING.md) explains how to work on the code.

## Easier to use

- **Describe a workflow by voice.** A 🎤 button in the "Describe it, I will build it" box. The browser records the voice; Mehteran's own speech-to-text tool (whisper.cpp, under "Local tools") writes it down on this computer; the text goes into the box for the user to read and correct. Nothing leaves the computer and no AI usage is spent. If the tool is not installed, the button offers to install it.
- **Updates for zip copies.** A copy downloaded as a zip file never updates itself. Show "A new version is available" with a one-click download in the interface.
- **Template defaults in the interface language.** Some text fields have an English default even in another language (for example "Who will read it" in "Explain a document in plain language": "a person with no legal or technical background"). Give these defaults a text per language, as the labels have.
- **Sign-in without a terminal window.** When Mehteran cannot open a terminal window (for example on some Linux desktops), Setup asks the user to run a command. Offer a way that needs no command.
- **The sample document in more languages.** "Try with a sample document" has a Turkish and an English sample (`mehteran/ui/sample-tr.md`, `sample-en.md`). Other interface languages get the English one.

## Translations

- **Review by native speakers.** The interface has 18 languages. The 16 other than English and Turkish were translated with AI tools and nobody who speaks them has read them yet. Corrections are welcome, also small ones: edit `mehteran/locales/<language>.json`.
- **Template names and fields** are in English and Turkish only. Other languages show the English text.

## Website and documentation

- **New screenshots.** The app screenshots on the website and in the README (`docs/assets/screens/`) show the old colors and the old Setup tab.

## AI tools

- **Audio and video input through Gemini.** Gemini models understand audio. Check whether the Antigravity or Gemini command-line tool accepts an audio file, and if so, offer it as a second way to write down speech.

---

# Yol haritası

Planlanan ama henüz başlanmamış iyileştirmeler. İsteyen herkes birini üstlenebilir. Başlamadan önce maddeyi adıyla anan bir issue açın; böylece iki kişi aynı işi yapmaz. Kod üzerinde nasıl çalışılacağı [CONTRIBUTING.tr.md](CONTRIBUTING.tr.md) dosyasında anlatılıyor.

## Daha kolay kullanım

- **İş akışını sesle anlatmak.** "Anlat, oluşturayım" kutusunda bir 🎤 düğmesi. Tarayıcı sesi kaydeder; Mehteran'ın kendi konuşmayı yazıya dökme aracı ("Yerel araçlar" altındaki whisper.cpp) sesi bu bilgisayarda yazıya döker; metin kullanıcının okuyup düzeltmesi için kutuya gelir. Hiçbir şey bilgisayardan çıkmaz ve yapay zekâ kullanım hakkından harcanmaz. Araç kurulu değilse düğme kurmayı önerir.
- **ZIP kopyaları için güncelleme.** ZIP olarak indirilen bir kopya kendini hiç güncellemez. Arayüzde "Yeni sürüm var" mesajı ve tek tıkla indirme gösterilmeli.
- **Şablon varsayılanları arayüz dilinde.** Bazı metin alanlarının varsayılanı başka bir dilde de İngilizce (örneğin "Belgeyi herkes için anlaşılır anlat"taki "Kim okuyacak": "a person with no legal or technical background"). Bu varsayılanlara da etiketler gibi her dil için bir metin verin.
- **Terminal penceresi olmadan giriş.** Mehteran bir terminal penceresi açamadığında (örneğin bazı Linux masaüstlerinde) Kurulum kullanıcıdan bir komut çalıştırmasını ister. Komut gerektirmeyen bir yol sunun.
- **Örnek belge başka dillerde.** "Örnek belgeyle deneyin"in Türkçe ve İngilizce örneği var (`mehteran/ui/sample-tr.md`, `sample-en.md`). Diğer arayüz dilleri İngilizcesini alır.

## Çeviriler

- **Anadili konuşanların gözden geçirmesi.** Arayüz 18 dilde. İngilizce ve Türkçe dışındaki 16 dil yapay zekâ araçlarıyla çevrildi ve o dilleri konuşan biri henüz okumadı. Küçük düzeltmeler de memnuniyetle karşılanır: `mehteran/locales/<dil>.json` dosyasını düzenleyin.
- **Şablon adları ve alanları** yalnızca İngilizce ve Türkçe. Diğer diller İngilizce metni gösterir.

## Web sitesi ve belgeler

- **Yeni ekran görüntüleri.** Web sitesindeki ve README'deki uygulama ekran görüntüleri (`docs/assets/screens/`) eski renkleri ve eski Kurulum sekmesini gösteriyor.

## Yapay zekâ araçları

- **Gemini üzerinden ses ve video girişi.** Gemini modelleri sesi anlayabiliyor. Antigravity ya da Gemini komut satırı aracının ses dosyası kabul edip etmediğini denetleyin; ediyorsa sesi yazıya dökmenin ikinci bir yolu olarak sunun.
