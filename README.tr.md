<p align="center"><img src="docs/assets/icon.svg" width="88" alt="Mehteran"></p>

<h1 align="center">Mehteran</h1>

<p align="center"><b>Kendi bilgisayarınızda, zaten sahip olduğunuz yapay zekâ abonelikleriyle iş akışları.</b></p>

<p align="center"><a href="README.md">English</a> · <a href="https://tolgabuyuktanir.github.io/Mehteran/?lang=tr">Web sitesi</a> · <a href="https://tolgabuyuktanir.github.io/Mehteran/docs.html?lang=tr">Belgeler</a> · <a href="docs/mehteran.tr.md">Ayrıntılı başvuru</a></p>

![Mehteran iş akışı kütüphanesi](docs/assets/screens/tr-library.png)

**Bir iş akışı deneyin.** Toplantı notlarınızı **Toplantı tutanağı ve aksiyonlar** akışına verin. Akış özeti ve aksiyon listesini hazırlar, incelemenizi bekler ve sonucu Word, HTML ya da Markdown olarak kaydeder.

[İlk iş akışınızı çalıştırın](https://tolgabuyuktanir.github.io/Mehteran/docs.html?lang=tr#tr-calistir) · [Kendi akışınızı oluşturun](https://tolgabuyuktanir.github.io/Mehteran/docs.html?lang=tr#tr-olustur)

Mehteran, zaten kullandığınız yapay zekâ araçlarını tekrar tekrar kullanılabilen iş akışlarına dönüştürür. Bir iş akışı belgeyi okur, modele sorar, cevabı kontrol eder, bir kişinin onayını alır ve sonucu Word ya da PDF olarak kaydeder. Mehteran yapay zekâyı aboneliklerinizin komut satırı araçlarıyla (Claude Code, Codex, Antigravity CLI) ya da bu bilgisayardaki modellerle (Ollama, LM Studio, llama.cpp) çağırır. Kendi anahtarı ve hesabı yoktur; zaten ödediğinizin üstüne ek bir ücret çıkarmaz.

macOS, Windows ve Linux'ta, 18 arayüz dilinde çalışır.

## Neden Mehteran

- **Ek fatura yok.** Mehteran her model çağrısından API anahtarlarını çıkarır; böylece bir araç yanlışlıkla bir API hesabına ücret yazamaz. Ücretli bir API anahtarı yalnızca o araç için izin verirseniz kullanılır.
- **Dosyalarınız sizde kalır.** Arayüz yalnızca `127.0.0.1` üzerinde çalışır. Çalıştırmalar, sonuçlar ve ayarlar diskinizdeki klasörlerdir. "Yalnızca yerel" işaretli bir iş akışı bilgisayardan hiçbir metin göndermez.
- **10 kategoride 78 hazır şablon:** internetten araştırma, belgeler, yazı, iş, hukuk, eğitim, sınavlar, araştırma, veri ve yazılım.
- **Anlatın, kurulsun:** ne istediğinizi bir cümleyle yazın; kurulu araçlarınız iş akışını kurar, kaydeder ve her adımın talimatını gösterir, düzenleyebilirsiniz. Ya da adımları bir tuvale çizin (yapay zekâ adımları, koşullar, döngüler, kişi onayları). "Bu adımı dene" tek bir adımı tek başına çalıştırır.
- **Sizin için sitelerde arar:** ev ya da araba ilanı, tarihlerinize uygun otel; bağlantılarıyla tek bir tabloda karşılaştırılır. Bunu yalnızca okuyan bir tarayıcı pencere açmadan yapar; rezervasyon yapmaz, kimseyle iletişime geçmez.
- **Gerçek belgeler girer, çıkar.** PDF, Word, EPUB, Excel, web sayfaları, taranmış belgeler (OCR) ve ses kayıtlarını (konuşmayı yazıya çevirme) okur. Markdown, Word, HTML, PDF, EPUB, e-posta taslağı, JSON ve CSV olarak kaydeder.
- **Kullanım sınırları çalıştırmayı bozmaz.** Adım sınırın sıfırlanmasını bekler ya da model sıranızdaki bir sonraki modelle devam eder.
- **Her çalıştırma saklanır:** canlı izleyin, durdurup devam ettirin, iki çalıştırmayı karşılaştırın, bir sonucu düzenleyip dışa aktarın.

## Başlarken

Önceden hiçbir şey kurmanız gerekmez. İnternet bağlantısı yeterlidir.

1. Bu GitHub sayfasında **Code** düğmesine, sonra **Download ZIP**'e tıklayın. Zip dosyasını bir klasöre açın (örnek: `Belgeler/Mehteran`).
2. Arayüzü başlatın:
   - **macOS:** `Open Mehteran.command` dosyasına sağ tıklayın, **Aç**'ı seçin, açılan uyarıda yine **Aç**'a basın. macOS bunu internetten indirilen dosyalar için yalnızca ilk seferde sorar.
     "Gerekli erişim izinleriniz yok" uyarısı çıkarsa: Terminal'i açın, `sh ` yazıp (sonunda boşluk) `Open Mehteran.command` dosyasını Terminal penceresine sürükleyin ve Enter'a basın.
   - **Windows:** `Open Mehteran.bat` dosyasına çift tıklayın. "Windows bilgisayarınızı korudu" uyarısı çıkarsa **Ek bilgi**'ye, sonra **Yine de çalıştır**'a basın.
   - **Linux:** terminalde `./mehter ui` komutunu çalıştırın.
3. İlk açılışta, bilgisayarda uygun bir Python (3.11 ya da üstü) yoksa Mehteran kendine ayrı bir Python kurar (bir-iki dakika). Sonra arayüz tarayıcıda `http://127.0.0.1:8766/` adresinde açılır. Terminal penceresi açık kaldıkça çalışır.
4. **Kurulum** sekmesinde istediğiniz yapay zekâ araçlarını kurun ve oturum açın. Sonra **İş akışları** sekmesinde bir iş akışını açıp çalıştırın.

Sonraki seferlerde aynı şekilde başlatın (ilk seferden sonra çift tıklamak yeterlidir).

### npm ile

Bilgisayarda Node.js 18 ya da daha yenisi varsa (Claude Code, Codex ve Gemini CLI onunla kurulur) tek komut yeterlidir:

```
npx mehteran
```

İlk çalıştırma npm sürümündeki kaynak kodu `~/Mehteran` klasörüne kurar ve arayüzü açar. Kurulum için `tar` gerekir. Sonraki seferlerde yine `npx mehteran` yazın. Her komut aynı şekilde çalışır: `npx mehteran templates`, `./mehter templates` ile aynıdır. Başka bir klasör için `MEHTERAN_DIR` değişkenini ayarlayın.

## Yapay zekâ araçları

| Araç | Nasıl ödenir | Metin nereye gider |
|---|---|---|
| Claude Code | Abonelik (Claude Pro / Max) | Anthropic |
| Codex CLI | Abonelik (ücretli bir ChatGPT planı) | OpenAI |
| Antigravity CLI | Ücretsiz Google hesabı | Google |
| Ollama | Yerel | Bu bilgisayarda kalır |
| LM Studio, llama.cpp, vLLM (OpenAI uyumlu yerel sunucu) | Yerel | Bu bilgisayarda kalır |
| Gemini CLI | API anahtarı (ücretli) | Google |

En az birine ihtiyacınız var. Kurulum sekmesi araçları kurar, oturum açmanızı sağlar ve her aracın kullanım sınırından ne kadar kaldığını gösterir (her sekmede üst çubukta da görünür). Bir adımın modeli `auto` ise Mehteran, model sıranızda kurulu, oturumu açık ve API anahtarıyla ücretlendirilmeyen ilk aracı seçer.

İsteğe bağlı yerel araçlar (Ollama, Tesseract OCR, PDF için Typst, Pandoc, konuşmayı yazıya çevirmek için whisper.cpp, qpdf) yalnızca siz isteyince kurulur; sabitlenmiş sürümlerdir ve SHA-256 özetleriyle doğrulanır.

## İsteğe bağlı kitap çevirisi

Mehteran kitap çevirisini varsayılan olarak ayrı bir bölümde göstermez. Mevcut kitaplarınız, ayarlarınız ve çeviri geçmişiniz bağımsız uygulamada kullanılabilir.

Bağımsız çeviri uygulamasını macOS’ta `Open Interface.command`, Windows’ta `Open Interface.bat` veya Linux’ta `./translate ui` ile başlatın. `http://127.0.0.1:8765/` adresini açın. Kitapları, modelleri ve talimatları kurmak için [çeviri kılavuzunu](docs/guide.tr.md) izleyin.

## Çalıştırma dosyalarını saklama

Çalıştırmalar ekranındaki çöp kutusundan bir çalıştırmayı geri yükleyebilirsiniz. Eski çalıştırmaları temizleme işlemi dosyaları kalıcı olarak siler. Temizlik bölümünde Mehteran verilerinin boyutunu ve boş disk alanını görebilirsiniz.

Otomatik bakım istiyorsanız veri klasöründeki `configurations/engine.toml` dosyasına şu seçenekleri ekleyebilirsiniz. Otomatik silme varsayılan olarak kapalıdır.

```toml
retain_runs_days = 90
retain_usage_days = 365
max_run_storage_gib = 10
```

Bakım arayüz açıldığında ve açık kaldığı sürece günde bir çalışır. `retain_runs_days` tamamlanmış eski çalıştırmaları çöp kutusundakiler dahil kalıcı olarak siler. `retain_usage_days` eski kullanım kayıtlarını temizler. Depolama sınırı yeni çalıştırmaların kabulünde denetlenir. Devam eden işlerin yazabileceği çıktı boyutunu sınırlamaz.

## Güncellemeler

Uygulamayı git ile aldıysanız (`git clone` veya `gh repo clone`), arayüz her açılışta GitHub'dan kendini günceller. İnternet veya GitHub girişi yoksa olduğu gibi açılır.

Yeni npm sürümünü kurmak için `MEHTERAN_DIR` ile yeni bir klasör seçin. Mevcut klasörler, kitaplar ve ayarlar erişilebilir kalsın diye yeniden kullanılır.

Zip dosyası indirdiyseniz yeni zip'i indirin. Mehteran'ın iş akışları ve çalıştırmaları kod klasörünün dışında saklanır; oldukları yerde kalırlar. Kitap çevirisi için eski klasördeki şunları yenisine taşıyın: `books/`, `glossary/`, `config.toml` ve `prompts/` klasörünün içindeki `.md` dosyaları (ve `prompts/custom/`).

Codex, Node.js ve PDF okuyucu uygulamanın kendi klasörüne (`.runtime/`) kurulur. Claude Code, Antigravity CLI ve ayrı Python (uv) kullanıcı klasörünüze (`~/.local/bin`; Windows'ta `%LOCALAPPDATA%` altına) kurulur. Uygulamayı silmek için klasörünü ve Mehteran'ın veri klasörünü silin (bkz. belgeler).

## Belgeler

- [Web sitesi](https://tolgabuyuktanir.github.io/Mehteran/?lang=tr) ve [belgeler](https://tolgabuyuktanir.github.io/Mehteran/docs.html?lang=tr): kurulum, yapay zekâ araçlarını bağlama, iş akışı çalıştırma ve oluşturma, yerel modeller, iş akışı dosyası, sorun giderme.
- [Mehteran ayrıntılı başvuru](docs/mehteran.tr.md): her ekran, ayar, API yolu ve sınır.
- [İslami kitap çevirisi kullanım kılavuzu](docs/guide.tr.md).

## Geliştirme

- Kod: `mehteran/` (Mehteran) ve `pipeline/` (kitap çevirisi), yalnızca Python standart kütüphanesi; arayüz derleme adımı olmayan düz JavaScript'tir.
- Testler: `python3 -m unittest discover tests`. Sahte bir yapay zekâ aracı kullanır, ağa bağlanmaz.
- npm paketi (`npx mehteran`) `npm/` klasöründedir. Yeni sürüm için `npm/package.json` içindeki sürümü artırın ve değişiklikleri commit edin. `npm pack` mevcut commit’i arşivleyip pakete koyar. Paketi kontrol ettikten sonra yayımlayın.
- Web sitesi `docs/` içindeki statik HTML'dir (`index.html`, `docs.html`, `assets/`); başka sunuculardan hiçbir şey yüklemez.

## Lisans

MIT. Ayrıntılar: [LICENSE](LICENSE).
