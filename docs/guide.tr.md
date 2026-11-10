# Çeviri Pipeline'ı: kullanım kılavuzu

[English](guide.md) · [README'ye dön](../README.tr.md)

Uygulamanın nasıl başlatılacağı [README](../README.tr.md) dosyasındadır. Bu kılavuz arayüzü ayrıntılı olarak, komut satırını, iş akışını, klasörleri, ayarları ve sınırları anlatır.

## Web arayüzü (önerilen)

Arayüzü açmak için `Open Interface.command` (macOS) veya `Open Interface.bat` (Windows) dosyasına çift tıklayın. Terminalden: `./translate ui` (Windows: `translate ui`).

Tarayıcıda `http://127.0.0.1:8765/` açılır. Terminal penceresi açık kaldıkça arayüz çalışır.

Önceden kurulması gereken bir şey yoktur ([Başlarken](../README.tr.md#başlarken) bölümüne bakın). Arayüzün dört sekmesi vardır:

| Sekme | Ne yapılır |
|---|---|
| Kurulum | Claude Code, Codex, Antigravity CLI, Gemini CLI ve PDF okuyucuyu kurar. Araçlarda oturum açar. "Dene" düğmesi aracın yanıt verdiğini denetler. Hangi adımı hangi aracın yaptığını gösterir. |
| İş akışı | İş akışının adımlarını ve modellerini sürükle-bırakla kurar (aşağıya bakın). |
| Kitaplar | Kitap ekler. Türkçe kaynağı ve referans tercümeleri yükler. Hedef dili seçip çeviriyi başlatır veya durdurur. İlerlemeyi ve günlüğü gösterir. Çeviriyi ve raporu okur; Markdown, Word, PDF veya HTML olarak dışa aktarır. |
| Talimatlar | Modellere verilen talimatları düzenler. Değiştirilmiş bir talimatı varsayılana döndürür. |

Oturum açma yöntemleri:

- Claude: "Claude hesabıyla" düğmesi bir terminal penceresi açar. Tarayıcıda oturum açın.
- Codex (ChatGPT): "ChatGPT hesabıyla" düğmesi bir terminal penceresi açar. Alternatif: OpenAI API anahtarı.
- Antigravity (Gemini modelleri): "Google hesabıyla" düğmesi bir terminal penceresi açar. Antigravity tarayıcıda Google girişini başlatır; giriş bitince `/exit` yazın. Ardından "Dene" düğmesiyle kontrol edin. Antigravity bazı Claude modellerini de sunar; varsayılanı bir Gemini modelidir. Antigravity her çağrıyı bir konuşma olarak saklar; pipeline kendi açtıklarını siler.
- Gemini CLI: Google 18 Haziran 2026'dan beri burada yalnızca API anahtarlarını ve şirket (Google Cloud) hesaplarını kabul ediyor, kişisel hesapları kabul etmiyor. "Google hesabıyla" düğmesi bir terminal penceresi açar. Gemini açılınca Google ile oturum açın, sonra `/quit` yazın. Ardından "Dene" düğmesiyle hesabın kabul edildiğini kontrol edin. Alternatif: https://aistudio.google.com/apikey adresinden alınan bir API anahtarı (`~/.gemini/.env` dosyasına kaydedilir).

Oturumu açtıktan sonra "Durumu yenile" düğmesine basın.

Güvenlik: arayüz yalnızca bu bilgisayardan erişilebilir (`127.0.0.1`). Her açılışta yeni bir oturum anahtarı üretilir; başka bir web sitesi bu sunucuya komut gönderemez. Yüklenen dosyaların içeriği denetlenir; en büyük dosya boyutu 300 MB'tır.

Arayüz kitabı `./translate run` komutuyla çalıştırır. Arayüz kapansa da başlatılmış çeviri sürer. Arayüz yeniden açıldığında çalışan çeviriyi görür ve durdurabilir.

## Referans tercümeler

Referans, aynı kitabın başka bir dile daha önce yapılmış, yayımlanmış tercümesidir; örneğin Norveççe çeviri için Danca ve İsveççe tercümeler. Zorunlu değildir.

- Çeviriden önce uygulama her Türkçe bölümün her referanstaki karşılığını bulur ("hizalama" adımı). Karşılık pasajlar ilk tercüme, sözlük, kaynak kontrolü ve uygula adımlarının modellerine verilir. Modeller oradan terimlerin, özel adların, saygı ifadelerinin ve zor cümlelerin nasıl karşılandığını görür.
- Esas her zaman Türkçe kaynaktır: talimatlar, referans kaynaktan farklıysa, bir pasajı eksikse veya hatalıysa kaynağa uyulmasını söyler.
- Her referansı diliyle birlikte yükleyin. Uygulama dosyayı hemen kontrol eder ve şu durumlarda uyarır: dosya Türkçe görünüyorsa, harfleri seçilen dile uymuyorsa, Arapça ibareleri ve numaraları Türkçe kaynakta yoksa (büyük ihtimalle başka bir kitap), veya kaynaktan çok kısa ya da çok uzunsa. Uyarı referansın altında ve kapalı "Referans tercümeler" adımında görünür; referans yine de kullanılabilir.
- Hizalamanın bir referansta bulamadığı bölümler o referansın altında listelenir; bu bölümler o referans olmadan çevrilir.

## İş akışı sekmesi: hangi model hangi adımı yapar

İş akışı soldan sağa oklarla bağlanmış kutular olarak çizilir: hazırlık, ilk tercüme, ondan sonraki adımlar ve insan editör. Her adım en son metin üzerinde çalışır. İstediğiniz kadar adımı istediğiniz sırayla ekleyebilirsiniz:

| Adım | Ne yapar |
|---|---|
| Tashih | En çok 4 model metni kaynakla paralel karşılaştırır ve bulgu yazar. Metin değişmez. |
| Uygula | Son metinden bu yana yazılan bütün bulguları (tashih, rapor yazan özel adım, kontrol noktası) kaynağa göre tartar, haklı olanları uygular. |
| Kaynak kontrolü | Metni kaynakla baştan karşılaştırır ve düzeltir. |
| Özel adım | Talimatını sizin yazdığınız adım (adımın panelinde; Türkçe yazılabilir). Ya bulgu yazar (tashih gibi) ya da metni düzeltir (kaynak kontrolü gibi). |
| Kontrol noktası | Bir model metinde kalan ciddi (kritik veya önemli) sorunları arar. Böyle sorunu olan bölüm, seçtiğiniz önceki adıma, belirlediğiniz sayıda (1–5) kereye kadar geri gönderilir; kontrol noktasının bulguları sonraki "Uygula"da işlenir. Sınır dolunca bölüm rapora işaretlenip devam eder. |
| Tashih turu | Kısayol: Tashih ve Uygula adımlarını birlikte ekler. |

- Adım ekleme: soldan bir okun üzerine sürükleyin veya oktaki + düğmesine basın. Karta tıklarsanız sona eklenir.
- Sırayı değiştirme: kutuyu başka bir okun üzerine sürükleyin. Hazırlık ve ilk tercüme başta kalır; modelleri değiştirilebilir.
- Bir kutuya tıklayınca ayarlarını ve modellerini altta seçersiniz. Bulgu yazan adım en çok 4 model alır (açılıp kapatılır); diğerleri tek model alır. Soldaki model kartını kutudaki role de bırakabilirsiniz. Panelde "Öne al", "Sonraya al" ve "Adımı sil" düğmeleri de vardır.
- Kutunun modellerinin altında her modelin **düşünme seviyesini** seçin (düşük … en yüksek; Claude Code ve Codex en yükseğe kadar, Antigravity yükseğe kadar; Gemini CLI'da seviye seçeneği yoktur). "Varsayılan seviye" seçimi araca bırakır. Yüksek seviye daha dikkatli ama daha yavaş çalışır ve kotayı daha çok harcar. `config.toml` dosyasında seviye adın sonuna yazılır: `claude/opus@high`.
- Kontrol noktasının yayı bölümleri nereye geri gönderdiğini gösterir. Kontrol noktaları iç içe geçemez: bir kontrol noktası, kendinden önceki kontrol noktasını aşarak geri gönderemez. Her geri gönderme aradaki adımları o bölüm için yeniden çalıştırır; kota ve süre harcar.
- Kırmızı işaretli kutu çalışamaz; örneğin hiçbir "Uygula" adımının kullanmadığı bulgular veya hedefi seçilmemiş kontrol noktası. Düzeltilene kadar iş akışı kaydedilmez. Kutudaki "!" yalnızca uyarıdır; örneğin bir model kendi yazdığı metni tashih ediyorsa.
- Model listeleri araçların kendisinden okunur (Claude'un model adları, Codex'in tuttuğu liste, `agy models`, `gemini --list-models`). Başka bir modeli aracının altına adıyla ekleyin; "Dene" kısa bir istek göndererek aracın yanıt verdiğini denetler.
- Her değişiklik hemen `config.toml` dosyasına (`[stages]` ve `[nodes]`; özel adımların talimatları `prompts/custom/` altına) kaydedilir ve sonra başlatılan çalıştırmalarda geçerli olur. "Şemadaki dağılım" "Tercüme ve Tashih İş Akışı" şemasındaki akışı geri getirir. Sıra değişince bitmiş bölümler kendiliğinden yeniden yapılmaz; Kitaplar ekranı yeniden üretilmesi gereken bölümleri gösterir. Durdurulan çalıştırma, döngünün içindeyken bile kaldığı yerden sürer.

## Dışa aktarma

Pipeline Markdown yazar (`output/<dil>.md`, `output/<dil>.report.md`). Kitaplar sekmesinden her birini dışa aktarabilirsiniz:

- Word (.docx): başlıklar Word başlığı, dipnotlar gerçek Word dipnotu olur. Metin iki yana yaslanır ve otomatik hecelenir; her ana bölüm yeni sayfada başlar; altbilgide sayfa numarası vardır. Metin içindeki Arapça parçalar sağdan sola yazılır, yalnızca Arapçadan oluşan paragraflar (âyet, hadîs) ortalanır. Arapça, Farsça, Urduca gibi hedef dillerde bütün belge sağdan soladır.
- PDF: bilgisayarda Chrome veya Edge varsa doğrudan PDF dosyası üretilir (Windows'ta Edge her zaman vardır). Kitap dizgisiyle basılır: iki yana yaslı ve hecelenmiş metin, paragraf girintisi, sayfa numarası, her ana bölüm yeni sayfada, dipnotlar bölüm sonunda. Tarayıcı bulunamazsa yazdırmaya hazır bir sayfa açılır; yazdırma penceresinde "PDF olarak kaydet" seçin.
- HTML ve Markdown. İtalik ve kalın yazı bütün biçimlerde korunur.

**Kitabın biçimi.** Dışa aktarma bağlantılarının yanındaki **Biçim ayarları**'na tıklayın. Ayarlar bütün kitaplara uygulanır; rapor her zaman standart A4 biçimiyle çıkar.

- **Sayfa ve yazı:** sayfa boyutu (A4, A5, B5, 13,5 × 21 cm, 16 × 24 cm, Letter), üst, alt ve yan kenar boşlukları, yazı tipi, Arapça yazı tipi, punto, satır aralığı (Word'deki gibi: 1 tek satır), iki yana yaslı paragraflar, her ana bölümün yeni sayfada başlaması. `config.toml` dosyasında `[export]` altında saklanır. Yazı tipi kurulu olmalıdır: PDF bu bilgisayardaki yazı tipleriyle oluşturulur, Word dosyası açıldığı bilgisayardakileri kullanır.
- **Word şablonu:** yayınevinizin `.docx` veya `.dotx` şablonunu yükleyin. Kitabın Word dosyası şablonun stillerini, sayfa boyutunu, kenar boşluklarını, üst ve alt bilgilerini alır; şablondaki metin kullanılmaz. Word'ün yerleşik "Başlık 1–3", "Alıntı", "Madde İşareti", "Dipnot Metni" ve "Dipnot Başvurusu" stilleri kullanılır; Word bunlara Türkçe ad vermiş olsa da bulunur. Şablonda olmayan stiller eklenir. Şablon yüklüyken yukarıdaki ayarlar yalnızca PDF ve HTML'ye uygulanır. Makro içeren dosyalar kabul edilmez. Şablon `export/word-template.docx` olarak saklanır.

## Uzun kitaplar, kullanım sınırları ve uyku

- Başlamadan önce Kitaplar sekmesi kaç bölümün işleneceğini, araç başına kaç model çağrısı gerektiğini ve tahmini süreyi gösterir. Çeviri sürerken şu anki adımı, geçen süreyi, kalan çağrıları ve kalan süreyi gösterir; kalan süre çalıştırmanın ölçülen hızıyla hesaplanır.
- Bir araç kullanım sınırına (kota) ulaşınca çeviri durmaz. O araca giden bütün istekler sınır açılana kadar bekler, sonra kendiliğinden devam eder. Araç sınırın ne zaman açılacağını söylemezse `quota_wait_minutes` (varsayılan 30) dakika beklenip yeniden denenir; `quota_max_hours` (varsayılan 24) saat sonunda bekleme bırakılır. Bekleme ve bitiş saati Kitaplar ve Kurulum sekmelerinde gösterilir.
- Çeviri sürerken bilgisayar uyanık tutulur (`keep_awake`; macOS, Windows ve systemd bulunan Linux). Dizüstü bilgisayarda kapağı açık ve bilgisayarı prize takılı tutun: kapak kapanınca bilgisayar yine uyur ve çeviri durur. Devam etmek için "Başlat" düğmesine yeniden basın.
- Referans tercümede bulunamayan bölümler, ilgili referansın altında listelenir.

## Komut satırı

Mesajlar Türkçe veya İngilizcedir: `--lang tr` veya `--lang en` kullanın; varsayılan dil `config.toml` dosyasındaki `[general] language` ayarıdır.

Windows'ta `./translate` yerine `translate` yazın.

```sh
./translate setup                       # araçları denetler
./translate new <kitap>                 # kitap klasörü oluşturur
./translate run <kitap> <dil>           # çevirir
./translate status [kitap]              # ilerlemeyi gösterir
./translate ui                          # web arayüzünü başlatır
./translate package                     # paylaşmak için dist/translation-pipeline.zip dosyasını yazar
```

`package` yalnızca uygulamayı paketler. Kitaplar, çeviriler, kurulu araçlar (`.runtime`) ve günlükler zip'e girmez. Klasörü elle sıkıştırmak yerine bu komutu kullanın.

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
| hazırlık | `align` | Her Türkçe bölümün referans tercümedeki karşılığını bulur. | Antigravity (Gemini) |
| hazırlık | `glossary` | Dinî terimleri ve özel adları çıkarır, `glossary/<dil>.tsv` dosyasına yalnızca yeni terimleri ekler. | Claude |
| 1 | `translate` | İlk tercüme: Türkçe kaynak, referans pasajlar ve sözlükle çevirir. | ChatGPT |
| 2 | `review1` | Tashih: tercümeyi Türkçe kaynakla cümle cümle karşılaştırır ve bulguları yazar. | Antigravity (Gemini) |
| 3 | `revise1` | Her bulguyu Türkçe kaynağa göre tartar. Haklı bulguları uygular, diğerlerini gerekçesiyle reddeder. | ChatGPT |
| 4 | `source_check` | Önceki adımlara güvenmeden metni Türkçe kaynakla baştan karşılaştırır ve bulduğu hataları düzeltir. | Claude |
| 5a, 5b | `review2` | İkinci bağımsız tashih: iki model birbirinden habersiz, paralel olarak bulgu raporu yazar. | ChatGPT ve Antigravity (Gemini) |
| 6 | `reconcile` | İki raporu Türkçe kaynağa göre uzlaştırır ve son metni üretir. | Claude |
| teslim | `assemble` | Bölümleri birleştirir, mekanik denetimleri yapar ve raporu yazar. | yok |
| 7 | | İnsan tercüman kitabı ve raporu teslim alır. Ardından insan editör okur. | insan |

Bu sıranın gerekçesi: metni değiştiren her adımı, o değişikliği yapmamış bir model denetler. ChatGPT'nin tercümesini Gemini tashih eder. Claude'un 4. adımdaki düzeltmelerini ChatGPT ve Gemini denetler.

Bir modelin döndürdüğü her metin (1., 3., 4. ve 6. adım), sonraki adım kullanmadan önce bir tamlık kapısından geçer: kaynakla aynı paragrafları ve dipnot işaretlerini içermelidir; bir düzeltme metni belirgin kısaltmamalıdır; uzun bir paragraf metninin büyük bölümünü kaybetmemelidir. Reddedilen cevap yeniden istenir (en çok 3 kez); yine eksikse bölüm hata olarak işaretlenir ve sonraki adıma geçmez. Tamamlanmamış bölümler çıktıda görünür bir `[[EKSİK BÖLÜM …]]` satırıyla yer alır ve raporda listelenir.

Tashihçiler (2. ve 5. adım) okuma kanıtı vermek zorundadır: her paragrafın son üç kelimesini geri yazarlar. Kanıt metinle uyuşmazsa cevap reddedilir ve yeniden istenir. Böylece "sorun yok" cevabı, metne bakılmadığını gizleyemez. Tashihleri uygulayan model (3. ve 6. adım) her bulgu için karar vermek zorundadır. Rapordaki "Tashihçi denetimi" bölümü her tashihçinin kaç bölümde bulgu yazmadığını ve bulgu yazmadığı hâlde sonradan ciddi hata çıkan bölümleri gösterir.

Bir bölüm üretildikten sonra sözlük, referanslar veya talimatlar değişirse pipeline bunu fark eder. Bölüm kendiliğinden yeniden üretilmez; rapor ve arayüz hangi bölümlerin hangi adımdan itibaren eski girdilerle durduğunu söyler. Arayüzdeki "Yeniden üretmeye hazırla" düğmesi formu doldurur; komut satırında `--redo <adım> --segments <bölümler>` kullanın.

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
export/word-template.docx  yayınevinin Word şablonu (yüklendiyse)
glossary/<dil>.tsv      dil başına terim sözlüğü; elle düzenlenir, bütün kitaplarda ortaktır
books/<kitap>/
  source/               Türkçe kitap (tek dosya)
  references/           mevcut tercümeler: da.docx, sv.epub ...
  work/                 ara dosyalar; pipeline üretir
  output/               <dil>.md ve <dil>.report.md
  logs/                 her çalıştırmanın günlüğü
pipeline/               kod (pipeline/i18n.py: mesajlar; pipeline/ui/: web arayüzü)
```

Desteklenen dosya türleri: `.docx`, `.epub`, `.md`, `.txt`, `.pdf`. Mümkünse `.docx` veya `.epub` verin: bunlardan başlıklar (yayınevinin kendi başlık biçimleri dahil), dipnotlar, italik, kalın ve numaralı maddeler eksiksiz okunur. PDF, kelimelerin sayfadaki yeri ve punto büyüklüğüyle okunur: sayfa başlıkları ve numaraları atılır; sayfa altındaki küçük puntolu dipnotlar ve metindeki üst simge dipnot numaraları dipnota çevrilir; paragraflar girinti ve satır aralığından, başlıklar puntodan tanınır; sayfadan taşan paragraf birleştirilir. Arapça ve Farsça metin, PDF'in kendi gliflerinden harekeleriyle birlikte okuma sırasına konur; tekrar eden Besmele sayfa başlığı sanılmaz. PDF'in hangi harfler olduğunu bildirmediği bir glif (bazı fontlar bir bitişiğin harflerini yazmaz) pdftotext'in okuduğu gibi kalır; âyet ve hadîsleri önizlemede kontrol edin. Taranmış (resim) PDF okunmaz; önce OCR gerekir. Çeviriden önce Kitaplar ekranındaki "Metni böl ve önizle" düğmesiyle metnin nasıl okunduğunu kontrol edin; PDF okumak için PDF okuyucu (Poppler'ın `pdftotext` programı) gerekir; Kurulum sekmesi bunu `.runtime/poppler` klasörüne kurar (komut satırında: `./translate install pdf`).

## Ayarlar

`config.toml` dosyasında:

- `[stages]`: her aşamanın aracı ve modeli; `araç` veya `araç/model` biçiminde. İş akışı sekmesi bu bölümü düzenler.
- `[providers.*]`: araçların komutları. `model` boş ise aracın varsayılan modeli kullanılır.
- `[languages]`: dil kodları. Yeni bir dil için bir satır ekleyin, örnek: `tg = "Tajik"`. Modeller İngilizce adı görür.
- `[general]`: arayüz dili, bölüm boyutu, paralel istek sayısı, zaman aşımı, kullanım sınırı beklemesi, uyanık tutma.

Çeviri kuralları `prompts/translate.md` dosyasındadır. Örnek: âyet ve hadislerin çevrilme biçimi, Arapça ibarelerin korunması, açıklama eklenmemesi. Yayın ilkeleriniz farklıysa bu dosyayı düzenleyin. Diğer talimatlar: `review.md` (Tashih), `revise.md` (Uygula), `source_check.md` (Kaynak kontrolü), `custom_report.md` ve `custom_rewrite.md` (özel adımlar; adımın kendi talimatı `{{instructions}}` yerine konur), `gate.md` (Kontrol noktası).

## Sınırlar

- Çıktı Markdown'dır; dışa aktarma Word, PDF ve HTML verir. Başlıklar, dipnotlar, italik, kalın ve numaralı maddeler korunur. Kaynaktaki tablolar, resimler ve renkler korunmaz. Matbaa dizgisi ayrıca yapılır.
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
