# Çeviri Pipeline'ı

[English](README.md)

Türkçe İslami kitapları yeni dillere çevirir. Çeviride Türkçe kaynak esas alınır. Aynı kitabın yakın dillerdeki mevcut tercümeleri referans olarak kullanılır. ChatGPT, Gemini ve Claude sırayla tercüme, tashih ve kaynak kontrolü yapar. Sonunda kitap ve insan tercüman için bir rapor üretilir.

macOS, Windows ve Linux'ta, Türkçe ve İngilizce çalışır (arayüzde TR / EN düğmesi).

## Başlarken

Önceden hiçbir şey kurmanız gerekmez. İnternet bağlantısı yeterlidir.

1. Uygulamayı indirin: GitHub sayfasında **Code** düğmesine, sonra **Download ZIP**'e tıklayın. Zip dosyasını bir klasöre açın (örnek: Belgeler/Tercüme).
2. Arayüzü başlatın:
   - **macOS:** `Open Interface.command` dosyasına sağ tıklayın, **Aç**'ı seçin, açılan uyarıda yine **Aç**'a basın. macOS bunu internetten indirilen dosyalar için yalnızca ilk seferde sorar.
     "Gerekli erişim izinleriniz yok" uyarısı çıkarsa: Terminal'i açın, `sh ` yazıp (sonunda boşluk) `Open Interface.command` dosyasını Terminal penceresine sürükleyin ve Enter'a basın.
   - **Windows:** `Open Interface.bat` dosyasına çift tıklayın. "Windows bilgisayarınızı korudu" uyarısı çıkarsa **Ek bilgi**'ye, sonra **Yine de çalıştır**'a basın.
   - **Linux:** terminalde `./translate ui` komutunu çalıştırın.
3. İlk açılışta, bilgisayarda uygun bir Python yoksa uygulama kendine ayrı bir Python kurar (bir-iki dakika). Sonra arayüz tarayıcıda `http://127.0.0.1:8765/` adresinde açılır. Terminal penceresi açık kaldıkça arayüz çalışır.
4. **Kurulum** sekmesindeki **Başlarken** listesini izleyin. Gerisi arayüzden yapılır: yapay zekâ araçlarını (Claude Code, Codex, Gemini CLI) kurar, bu araçlarda oturum açar ve ilk kitabınızı eklersiniz.

Sonraki seferlerde arayüzü aynı şekilde başlatın (ilk seferden sonra çift tıklamak yeterlidir).

## Gerekenler

- **Hesaplar:** oturumu arayüz açar ama abonelikler sizde olmalıdır: Claude Pro/Max aboneliği (veya Anthropic Console), ücretli bir ChatGPT planı (veya OpenAI API anahtarı), ve Gemini kullanılacaksa Gemini CLI'nin kabul ettiği bir Google hesabı (veya Gemini API anahtarı). Google, ücretsiz kişisel hesapları Gemini CLI'de artık kabul etmiyor. Hazır iş akışı üç aracı da kullanır; araçlardan birinin hesabı yoksa **İş akışı** sekmesinde o aracın adımlarına başka bir model atayın.
- **PDF kitaplar:** PDF kaynak okumak için `pdftotext` programı (Poppler) gerekir; arayüz bunu kurmaz. Eksikse arayüz söyler ve nasıl kurulacağını gösterir. `.docx` veya `.epub` kaynak için ek bir şey gerekmez ve bunlar daha eksiksiz okunur.
- **PDF olarak dışa aktarma:** Chrome veya Edge gerekir (Windows'ta Edge her zaman vardır). Bunlar yoksa yazdırmaya hazır bir sayfa açılır; yazdırma penceresinde "PDF olarak kaydet" seçin.

Uygulamanın kurduğu her şey kendi klasöründe durur (`.runtime/`, yaklaşık 0,7 GB). Uygulamayı silmek için klasörü silmeniz yeterlidir. Claude Code ve ayrı Python (uv) kullanıcı klasörünüze (`~/.local/bin`) kurulur.

## Daha fazlası

[Kullanım kılavuzu](docs/guide.tr.md); arayüzü ayrıntılı olarak, iş akışını, dışa aktarma biçimini, komut satırını, klasörleri, ayarları, sınırları ve geliştirmeyi anlatır.
