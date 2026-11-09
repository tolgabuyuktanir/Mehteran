# Çeviri Pipeline'ı

[English](README.md)

Türkçe İslami kitapları yeni dillere çevirir. Çeviride Türkçe kaynak esas alınır. Aynı kitabın yakın dillerdeki mevcut tercümeleri referans olarak kullanılır. ChatGPT, Gemini ve Claude sırayla tercüme, tashih ve kaynak kontrolü yapar. Sonunda kitap ve insan tercüman için bir rapor üretilir.

Örnek: Norveççe çeviri için Türkçe kitap kaynak, Danca ve İsveççe tercümeler referans olur.

macOS, Windows ve Linux'ta çalışır. Uygulama Türkçe ve İngilizce kullanılabilir. Web arayüzünde TR / EN düğmesi vardır. Komut satırında `--lang tr` veya `--lang en` kullanın; varsayılan dil `config.toml` dosyasındaki `[general] language` ayarıdır.

## Başlarken (yeni kullanıcılar için)

Önceden hiçbir şey kurmanız gerekmez. İnternet bağlantısı yeterlidir.

1. Uygulamayı indirin ve zip dosyasını bir klasöre açın (örnek: Belgeler/Tercüme).
2. Uygulamayı açın:
   - **macOS:** `Open Interface.command` dosyasına sağ tıklayın, **Aç**'ı seçin, açılan uyarıda yine **Aç**'a basın. Bu yalnızca ilk seferde gerekir; macOS internetten indirilen dosyaları böyle sorar.
     "Gerekli erişim izinleriniz yok" uyarısı çıkarsa: Terminal'i açın, `sh ` yazıp (sonunda boşluk) `Open Interface.command` dosyasını Terminal penceresine sürükleyin ve Enter'a basın.
   - **Windows:** `Open Interface.bat` dosyasına çift tıklayın. "Windows bilgisayarınızı korudu" uyarısı çıkarsa **Ek bilgi**'ye, sonra **Yine de çalıştır**'a basın.
3. İlk açılışta, bilgisayarda uygun bir Python yoksa uygulama kendine ayrı bir Python kurar (bir-iki dakika). Sonra tarayıcıda arayüz açılır.
4. **Kurulum** sekmesindeki **Başlarken** listesini izleyin:
   - **Eksikleri kur:** Claude Code, Codex ve Gemini kurulur. Gerekirse Node.js de uygulamanın kendi klasörüne kurulur. Yönetici izni gerekmez.
   - Her aracın kartındaki "… hesabıyla" düğmesiyle oturum açın. Kartta gereken abonelik ve adımlar yazar.
   - **Kitaplar** sekmesinde ilk kitabınızı ekleyin.

Üç araç da kurulur: Claude Code, Codex ve Gemini CLI. Gereken hesaplar, iş akışında kullandığınız araçlara göre değişir: Claude Pro/Max aboneliği (veya Anthropic Console), ücretli bir ChatGPT planı (veya OpenAI API anahtarı), ve Gemini kullanılacaksa Gemini CLI'nin kabul ettiği bir Google hesabı (veya Gemini API anahtarı). Google, ücretsiz kişisel hesapları Gemini CLI'de artık kabul etmiyor. Hazır iş akışı üç aracı da kullanır. Araçlardan birinin hesabı yoksa o aracın adımları çalışmaz; **İş akışı** sekmesinde bu adımlara başka bir model atayın. Hangi adımda hangi aracın kullanılacağını **İş akışı** sekmesinden değiştirebilirsiniz.

Uygulamanın kurduğu her şey kendi klasöründe durur (`.runtime/`, yaklaşık 0,7 GB). Uygulamayı silmek için klasörü silmeniz yeterlidir. Claude Code ve ayrı Python (uv) kullanıcı klasörünüze (`~/.local/bin`) kurulur.

## Web arayüzü (önerilen)

Arayüzü açmak için `Open Interface.command` (macOS) veya `Open Interface.bat` (Windows) dosyasına çift tıklayın. Terminalden: `./translate ui` (Windows: `translate ui`).

Tarayıcıda `http://127.0.0.1:8765/` açılır. Terminal penceresi açık kaldıkça arayüz çalışır.

Önceden kurulması gereken bir şey yoktur (yukarıdaki "Başlarken" bölümüne bakın). Arayüzün dört sekmesi vardır:

| Sekme | Ne yapılır |
|---|---|
| Kurulum | Claude Code, Codex ve Gemini CLI'ı kurar. Her birinde oturum açar. "Dene" düğmesi aracın yanıt verdiğini denetler. Hangi adımı hangi aracın yaptığını gösterir. |
| İş akışı | Her adıma sürükle-bırakla araç ve model atar (aşağıya bakın). |
| Kitaplar | Kitap ekler. Türkçe kaynağı ve referans tercümeleri yükler. Hedef dili seçip çeviriyi başlatır veya durdurur. İlerlemeyi ve günlüğü gösterir. Çeviriyi ve raporu okur; Markdown, Word, PDF veya HTML olarak dışa aktarır. |
| Talimatlar | Modellere verilen talimatları düzenler. Değiştirilmiş bir talimatı varsayılana döndürür. |

Oturum açma yöntemleri:

- Claude: "Claude hesabıyla" düğmesi bir terminal penceresi açar. Tarayıcıda oturum açın.
- Codex (ChatGPT): "ChatGPT hesabıyla" düğmesi bir terminal penceresi açar. Alternatif: OpenAI API anahtarı.
- Gemini: "Google hesabıyla" düğmesi bir terminal penceresi açar. Gemini açılınca Google ile oturum açın, sonra `/quit` yazın. Ardından "Dene" düğmesiyle hesabın kabul edildiğini kontrol edin. Alternatif: https://aistudio.google.com/apikey adresinden alınan bir API anahtarı (`~/.gemini/.env` dosyasına kaydedilir).

Oturumu açtıktan sonra "Durumu yenile" düğmesine basın.

Güvenlik: arayüz yalnızca bu bilgisayardan erişilebilir (`127.0.0.1`). Her açılışta yeni bir oturum anahtarı üretilir; başka bir web sitesi bu sunucuya komut gönderemez. Yüklenen dosyaların içeriği denetlenir; en büyük dosya boyutu 300 MB'tır.

Arayüz kitabı `./translate run` komutuyla çalıştırır. Arayüz kapansa da başlatılmış çeviri sürer. Arayüz yeniden açıldığında çalışan çeviriyi görür ve durdurabilir.

## İş akışı sekmesi: hangi model hangi adımı yapar

Adımlar sabittir; her adım bir öncekinin sonucunu kullanır. Her adımı hangi aracın ve modelin yapacağını siz seçersiniz:

- Soldaki model kartını adımın üzerine sürükleyip bırakın veya adımdaki listeden seçin.
- İki tashih adımına en çok 4 model atanabilir; bu modeller paralel ve birbirinden bağımsız çalışır.
- Bir aracın altına adını yazarak model ekleyin (örnek: `opus`; Gemini için "Model listesini getir"). "Dene" kısa bir istek gönderir; model adının geçerli olduğunu ve aracın yanıt verdiğini denetler.
- Bir model kendi işini denetleyecek şekilde atanırsa sayfa uyarır; örneğin tercümeyi yapan model tashihi de yapıyorsa. Bunlar uyarıdır; yine de kaydedebilirsiniz.
- "Şemadaki dağılım" düğmesi "Tercüme ve Tashih İş Akışı" şemasındaki dağılımı geri getirir. "Kaydet", `config.toml` dosyasındaki `[stages]` bölümüne yazar; sonra başlatılan çalıştırmalarda geçerli olur.

Adım eklemek, silmek veya sırasını değiştirmek bilerek kapalıdır: adımlar birbirine bağlıdır (uzlaştırma iki tashih raporu ister) ve sonucun güvenilirliği, her değişikliği başka bir modelin denetlemesine dayanır.

## Dışa aktarma

Pipeline Markdown yazar (`output/<dil>.md`, `output/<dil>.report.md`). Kitaplar sekmesinden her birini dışa aktarabilirsiniz:

- Word (.docx): başlıklar Word başlığı, dipnotlar gerçek Word dipnotu olur; Arapça, Farsça, Urduca gibi dillerde sağdan sola düzen kullanılır.
- PDF: yazdırmaya hazır bir sayfa açılır; yazdırma penceresinde "PDF olarak kaydet" seçin. Tarayıcının yazı tipleri kullanıldığı için her alfabe doğru basılır.
- HTML ve Markdown.

## Uzun kitaplar, kullanım sınırları ve uyku

- Başlamadan önce Kitaplar sekmesi kaç bölümün işleneceğini, araç başına kaç model çağrısı gerektiğini ve tahmini süreyi gösterir. Çeviri sürerken şu anki adımı, geçen süreyi, kalan çağrıları ve kalan süreyi gösterir; kalan süre çalıştırmanın ölçülen hızıyla hesaplanır.
- Bir araç kullanım sınırına (kota) ulaşınca çeviri durmaz. O araca giden bütün istekler sınır açılana kadar bekler, sonra kendiliğinden devam eder. Araç sınırın ne zaman açılacağını söylemezse `quota_wait_minutes` (varsayılan 30) dakika beklenip yeniden denenir; `quota_max_hours` (varsayılan 24) saat sonunda bekleme bırakılır. Bekleme ve bitiş saati Kitaplar ve Kurulum sekmelerinde gösterilir.
- Çeviri sürerken bilgisayar uyanık tutulur (`keep_awake`; macOS, Windows ve systemd bulunan Linux). Dizüstü bilgisayarda kapağı açık ve bilgisayarı prize takılı tutun: kapak kapanınca bilgisayar yine uyur ve çeviri durur. Devam etmek için "Başlat" düğmesine yeniden basın.
- Referans tercümede bulunamayan bölümler, ilgili referansın altında listelenir.

## Komut satırı

Windows'ta `./translate` yerine `translate` yazın.

```sh
./translate setup                       # araçları denetler
./translate new <kitap>                 # kitap klasörü oluşturur
./translate run <kitap> <dil>           # çevirir
./translate status [kitap]              # ilerlemeyi gösterir
./translate ui                          # web arayüzünü başlatır
```

`run` seçenekleri:

| Seçenek | Anlamı |
|---|---|
| `--refs da,sv` | Yalnızca bu referans dilleri kullanır. Varsayılan: `references/` içindeki bütün diller. |
| `--segments 1-3` | Yalnızca bu bölümleri işler. `1-5,9` biçimi de geçerlidir. |
| `--until glossary` | Bu aşamadan sonra durur. |
| `--redo translate` | Seçili bölümlerde bu aşamanın ve sonraki aşamaların çıktısını siler ve yeniden üretir. |
| `--parallel 5` | Aynı anda çalışan istek sayısı. |

`run` kaldığı yerden devam eder. Bir hata veya kullanım sınırı işi durdurursa aynı komutu yeniden çalıştırın. Tamamlanan bölümler yeniden üretilmez.

## Önerilen çalışma biçimi

Bütün kitabı çevirmeden önce sözlüğü ve birkaç bölümü gözden geçirin.

1. Yalnızca sözlüğü çıkarın: `./translate run ilmihal no --until glossary`
2. `glossary/no.tsv` dosyasını açın ve terim karşılıklarını düzeltin. Bu dosya o dildeki bütün kitaplarda ortaktır.
3. İlk üç bölümü deneme olarak çevirin ve çıktıyı okuyun: `./translate run ilmihal no --segments 1-3`
4. Sonuç uygunsa bütün kitabı çalıştırın: `./translate run ilmihal no`
5. Kitabı ve `output/no.report.md` raporunu insan tercümana teslim edin. Tercümandan sonra kitabı bir insan editör okur.

Sözlüğü sonradan değiştirirseniz çeviriyi yenileyin: `./translate run ilmihal no --redo translate`

## İş akışı

Her bölüm şu adımlardan sırayla geçer. Numaralar "Tercüme ve Tashih İş Akışı" şemasındaki adımlardır.

| Adım | Aşama | Ne yapar | Varsayılan araç |
|---|---|---|---|
| hazırlık | `prepare` | Kaynağı ve referansları metne çevirir. Kaynağı yaklaşık 6000 karakterlik bölümlere ayırır. | yok |
| hazırlık | `align` | Her Türkçe bölümün referans tercümedeki karşılığını bulur. | Gemini |
| hazırlık | `glossary` | Dinî terimleri ve özel adları çıkarır, `glossary/<dil>.tsv` dosyasına yalnızca yeni terimleri ekler. | Claude |
| 1 | `translate` | İlk tercüme: Türkçe kaynak, referans pasajlar ve sözlükle çevirir. | ChatGPT |
| 2 | `review1` | Tashih: tercümeyi Türkçe kaynakla cümle cümle karşılaştırır ve bulguları yazar. | Gemini |
| 3 | `revise1` | Her bulguyu Türkçe kaynağa göre tartar. Haklı bulguları uygular, diğerlerini gerekçesiyle reddeder. | ChatGPT |
| 4 | `source_check` | Önceki adımlara güvenmeden metni Türkçe kaynakla baştan karşılaştırır ve bulduğu hataları düzeltir. | Claude |
| 5a, 5b | `review2` | İkinci bağımsız tashih: iki model birbirinden habersiz, paralel olarak bulgu raporu yazar. | ChatGPT ve Gemini |
| 6 | `reconcile` | İki raporu Türkçe kaynağa göre uzlaştırır ve son metni üretir. | Claude |
| teslim | `assemble` | Bölümleri birleştirir, mekanik denetimleri yapar ve raporu yazar. | yok |
| 7 | | İnsan tercüman kitabı ve raporu teslim alır. Ardından insan editör okur. | insan |

Bu sıranın gerekçesi: metni değiştiren her adımı, o değişikliği yapmamış bir model denetler. ChatGPT'nin tercümesini Gemini tashih eder. Claude'un 4. adımdaki düzeltmelerini ChatGPT ve Gemini denetler.

Bir modelin döndürdüğü her metin (1., 3., 4. ve 6. adım), sonraki adım kullanmadan önce bir tamlık kapısından geçer: kaynakla aynı paragrafları ve dipnot işaretlerini içermelidir; bir düzeltme metni belirgin kısaltmamalıdır; uzun bir paragraf metninin büyük bölümünü kaybetmemelidir. Reddedilen cevap yeniden istenir (en çok 3 kez); yine eksikse bölüm hata olarak işaretlenir ve sonraki adıma geçmez. Tamamlanmamış bölümler çıktıda görünür bir `[[EKSİK BÖLÜM …]]` satırıyla yer alır ve raporda listelenir.

Mekanik denetimler yapay zekâ kullanmaz. Şunları kaynakla karşılaştırır: Arap harfli ibareler, sayılar, dipnot işaretleri ve metinleri, paragraf ve başlık sayısı, paragraf başına cümle sayısı, çeviri uzunluğu.

Rapor şunları listeler: mekanik uyarılar, bütün kritik bulgular, kabul edilmeyen önemli bulgular ve referansı bulunamayan bölümler. Modeller açıklamalarını, çalıştırmanın arayüz dilinde yazar. Bütün bulgular ve kararlar `work/<dil>/` altındaki `revise1`, `source_check` ve `reconcile` klasörlerinde, bölüm başına bir `.json` dosyasındadır. Her adımın metni de aynı klasörlerde durur; bir cümlenin hangi adımda değiştiğini buradan izleyebilirsiniz.

## Klasör yapısı

```
Open Interface.command  web arayüzünü başlatır (macOS, çift tıklama)
Open Interface.bat      web arayüzünü başlatır (Windows, çift tıklama)
translate, translate.cmd  komut satırı başlatıcısı (macOS/Linux, Windows)
config.toml             hangi aşamayı hangi araç ve model yapar, dil kodları
prompts/                modellere verilen talimatlar (çeviri kuralları buradadır)
prompts/defaults/       talimatların ilk hâli; "Varsayılana dön" bunu kullanır
glossary/<dil>.tsv      dil başına terim sözlüğü; elle düzenlenir, bütün kitaplarda ortaktır
books/<kitap>/
  source/               Türkçe kitap (tek dosya)
  references/           mevcut tercümeler: da.docx, sv.epub ...
  work/                 ara dosyalar; pipeline üretir
  output/               <dil>.md ve <dil>.report.md
  logs/                 her çalıştırmanın günlüğü
pipeline/               kod (pipeline/i18n.py: mesajlar; pipeline/ui/: web arayüzü)
```

Desteklenen dosya türleri: `.docx`, `.epub`, `.md`, `.txt`, `.pdf`. Mümkünse `.docx` veya `.epub` verin. PDF'ten paragraf sınırları ve dipnotlar güvenilir biçimde çıkmaz; PDF okumak için `pdftotext` programı (Poppler veya Xpdf) gerekir, arayüz bunu yükleme sırasında denetler.

## Ayarlar

`config.toml` dosyasında:

- `[stages]`: her aşamanın aracı ve modeli; `araç` veya `araç/model` biçiminde. İş akışı sekmesi bu bölümü düzenler.
- `[providers.*]`: araçların komutları. `model` boş ise aracın varsayılan modeli kullanılır.
- `[languages]`: dil kodları. Yeni bir dil için bir satır ekleyin, örnek: `tg = "Tajik"`. Modeller İngilizce adı görür.
- `[general]`: arayüz dili, bölüm boyutu, paralel istek sayısı, zaman aşımı, kullanım sınırı beklemesi, uyanık tutma.

Çeviri kuralları `prompts/translate.md` dosyasındadır. Örnek: âyet ve hadislerin çevrilme biçimi, Arapça ibarelerin korunması, açıklama eklenmemesi. Yayın ilkeleriniz farklıysa bu dosyayı düzenleyin. Diğer talimatlar: `review.md` (2. ve 5. adım), `revise.md` (3. ve 6. adım), `source_check.md` (4. adım).

## Sınırlar

- Çıktı Markdown'dır; dışa aktarma Word, PDF ve HTML verir. Başlıklar ve dipnotlar korunur. Kaynaktaki kalın, italik ve tablo gibi biçimler korunmaz. Dizgi ayrıca yapılır.
- Windows desteği yazıldı ama yalnızca macOS'ta denendi; henüz bir Windows bilgisayarda çalıştırılmadı.
- Kaynak dosya ilk çalıştırmadan sonra değişirse pipeline durur. Yeni kaynakla başlamak için arayüzde "Çalışmayı sıfırla" düğmesine basın veya `books/<kitap>/work/` klasörünü silin.
- Referans tercüme Türkçe kitaptan çok farklı düzenlenmişse bazı bölümlerin referansı bulunamaz. Bu bölümler referanssız çevrilir ve raporda listelenir.
- Yapay zekâ tashihi insan kontrolünün yerini tutmaz. Yayından önce kitabı insan tercüman ve insan editör okumalıdır.

## Geliştirme

Kod, yorumlar ve adlar İngilizcedir. Kullanıcının gördüğü metinler iki dillidir:

- Python mesajları: `pipeline/i18n.py` (`MESSAGES`; her anahtar için bir `tr` ve bir `en` metni)
- Web arayüzü metinleri: `pipeline/ui/app.js` dosyasının başındaki `I18N` sözlüğü

Yeni bir mesajın iki dilde de yazılması gerekir. Bir test, her mesajın iki dilde ve aynı yer tutucularla tanımlı olduğunu denetler.

```sh
python3 -m unittest discover -s tests
```

Testler gerçek yapay zekâ çağrısı yapmaz; sahte bir araç kullanır (`tests/fake_llm.py`).
