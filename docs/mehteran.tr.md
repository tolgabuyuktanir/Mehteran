# Mehteran: kullanım kılavuzu

[English](mehteran.md) · [README'ye dön](../README.tr.md)

Mehteran, yapay zekâ iş akışlarını bu bilgisayarda çalıştırır. Bir iş akışı bir YAML dosyasıdır: düğümlerden oluşan bir çizge (belge oku, modele sor, metinleri birleştir, bir kişiye onaylat, rapor kaydet). Modeller, çeviri uygulamasının zaten kullandığı komut satırı araçlarıyla çağrılır (Claude Code, Codex, Antigravity CLI, Gemini CLI). Mehteran'ın kendi anahtarı ya da hesabı yoktur.

Çeviri uygulaması Mehteran arayüzünün bir parçasıdır: İş akışları sekmesindeki "Kitap çevirisi" kartı çeviri uygulamasını bütün özellikleriyle, Mehteran'ın kendi sayfasında açar (aşağıya bakın). Çeviri uygulamasının Python kodu değişmez; `./translate ui` kendi başına çalışmayı sürdürür.

## Başlatma

| | macOS / Linux | Windows |
|---|---|---|
| Web arayüzü (çift tıklama) | `Open Mehteran.command` | `Open Mehteran.bat` |
| Web arayüzü | `./mehter ui` | `mehter ui` |
| Komut satırı | `./mehter <komut>` | `mehter <komut>` |

Arayüz `http://127.0.0.1:8766/` adresinde açılır. Arayüz çalışırken kod değişirse (bir güncelleme) sayfa bunu bir uyarıyla söyler: sunucunun terminal penceresini kapatıp yeniden başlatın. Port doluyken `mehter ui` ikinci kez başlatılırsa, çalışan sunucu eskiyse aynı şeyi söyler. Terminal penceresi açık kaldıkça çalışır. Başlatıcı çeviri uygulamasınınki gibi çalışır (`scripts/start.sh`, `scripts/start.cmd`): Python 3.11 veya üstünü kullanır, bilgisayarda yoksa ayrı bir Python (uv) kurar ve `ui` öncesinde kod klasörünün git kopyasını günceller (`python -m pipeline update`, çeviri uygulamasının kendi güncelleme adımı).

Dil düğmesi (bir bayrak ve dilin adı) sağ üsttedir: 18 arayüz dili vardır, "Diller" bölümüne bakın. Komut satırında komuttan önce `--lang <kod>` (`tr`, `en`, `de`, `ar`...) yazın.

## Web arayüzü

Arayüz, çeviri uygulamasınınkiyle aynı tasarımdadır ve üç sekmesi vardır: İş akışları, Çalıştırmalar, Kurulum. Önceki sürümlerin adresleri (`#templates`, `#workflow/...`, `#runs/new/...`) karşılık gelen ekranı açmayı sürdürür. Araçlar hazır değilken ilk ekran Kurulum'dur, hazırsa en son kullanılan sekme; sol üstteki Mehteran adı da oraya götürür.

- **İslami kitap çevirisi** (İş akışları kitaplığının en üstündeki, kitap simgeli sabit kart; adresi `#workflows/translation[/books|workflow|prompts]`, eski `#translation...` adresleri oraya gider): çeviri uygulamasının kendisi, bütün özellikleriyle: Kitaplar, çeviri akışı ve talimatları, "← Akışlar" bağlantısının yanında bölümler olarak. Kart bir iş akışının kartı gibidir (simge, rozetler, ad, açıklama, yıldız, ana düğme); kaç kitap olduğunu ve kaçının çevrilmekte olduğunu gösterir. Yıldızı onu favori yapar (`library.json` içinde `app:translation`, `PUT /api/templates/app/translation/favorite`). Kurulum sekmesi Mehteran'ın Kurulum sekmesidir: ona giden her bağlantı onu açar. Dil düğmesi ikisini birlikte değiştirir. Nasıl çalıştığı: aşağıda "Kitap çevirisi".
- **İş akışları**: kitaplık ve görsel düzenleyici. Kitaplık her iş akışı için bir kart gösterir (önce sizinkiler, sonra kategoriye göre); büyük-küçük harfe ve aksanlara (Türkçe olanlar da: "sozlesme", "Sözleşme"yi bulur) bakmayan bir arama ve kategori süzgeci vardır. Bir kart; açıklamayı, çizimi, girdileri ve sonuçları, YAML metnini ve şu işlemleri içeren bir panel açar: "Çalıştır", "Düzenle" (düzenleyiciyi açar; hazır bir şablon kaydedilmemiş kendi kopyanız olarak açılır), "Çoğalt" (yeni bir kimlikle kendi kopyanız; geldiği şablonu ve sürümü `based_on` içinde kaydeder; hazır şablonun sonraki bir güncellemesi onu hiç değiştirmez), "YAML olarak indir", "Sil" (yalnızca sizin iş akışlarınız). Sizin iş akışlarınızın orada bir YAML düzenleyicisi de vardır; "İçe aktar" bir iş akışı dosyası ekler; "Yeni iş akışı" boş bir tane başlatır.
- **Çalıştırmalar**: solda çalıştırma geçmişi, sağda bir çalıştırma: akışı canlı (düzenleyicinin tuvali, salt okunur; her kutu durumunun rengiyle), her düğüm için bir ilerleme satırı, indirilecek sonuçlar ve seçili düğümün paneli: çıktıları (okuyucuda okuyun ya da indirin), modele gönderilen istem, onayla ya da reddet, yeniden dene. Liste, iş akışı çalıştırmalarının altında kitap çevirisinin her kitabının son çalıştırmasını da gösterir (`GET /api/translation/runs`; her kitabın `work/run.json` dosyasından okunur); tıklayınca kitaplar açılır. Çalışan her şeyin listede bir durdurma düğmesi (■) vardır. "Devam ettir" başarısız, iptal edilmiş ya da yarıda kalmış bir çalıştırmayı sürdürür; "İptal et" durdurur; "Yeniden çalıştır" aynı iş akışıyla çalıştırma penceresini açar.
- **Kurulum**: çeviri uygulamasının Kurulum sekmesindeki araç kartlarının aynısı, aynı kodla (`pipeline.tools`, `pipeline.runtime`): kurulu ve oturum durumu, "Eksikleri kur" (çeviri akışının ve şablonların kullandığı araçlar ve PDF okuyucu), her araç için kurma düğmesi, oturum açma yolları (hesap; Codex ve Gemini için API anahtarı da), "Dene", son kullanım sınırı ve bir başlangıç kutusu. Her kart aracı kimin kullandığını söyler (Çeviri, şablonlar). Araçlar çeviri uygulamasınınkiyle aynı `<kod klasörü>/.runtime` içine kurulur; ikisi tek kurulumu paylaşır. Çeviri uygulamasının `config.toml` dosyasında tanımlı olmayan bir araç gösterilir, ama kullanılamaz. Her kart "Gerekli" (bir şablonun ya da çevirinin kullandığı araçlar ve PDF okuyucu) ya da "İsteğe bağlı" olarak işaretlidir. Altlarında "Yerel araçlar" (hepsi isteğe bağlı): Ollama kartı (durum; sürümü, kaynağı ve klasörü söyleyen bir onaydan sonra kurulum; İptal düğmesiyle kurulum günlüğü), modelleri (kurulu olanlar ve Sil; boyutu, belleği ve dilleriyle önerilenler, bu bilgisayar için büyük olana uyarı; adıyla başka bir model; ilerlemesi ve İptal düğmesiyle aynı anda bir indirme) Tesseract OCR kartı (onaydan sonra kurulum, eklenecek diller) ve Typst, Pandoc, konuşmayı metne çevirme (modelleriyle) ve qpdf kartları (sürümü, indirme boyutunu, kaynağı ve klasörü söyleyen bir onaydan sonra kurulum; İptal düğmesiyle kurulum günlüğü). Yerel modeller, model seçilen her yerde "yerel" olarak işaretlidir.

Bir çalıştırma, çalıştırma penceresinde başlar (bir karttaki, bir iş akışının panelindeki ya da düzenleyicideki "Çalıştır"): iş akışının bütün girdileri (dosya girdisi bir yükleme alır, model girdisi ayarlı araçları modelleri ve düşünme düzeyleriyle sunar); "Çalıştırmayı başlat" çalıştırmayı Çalıştırmalar sekmesinde açar.

### Kitap çevirisi

Kitap çevirisi, çeviri uygulamasının kendi arayüzüdür ve Mehteran'ın sayfasının içindedir: `pipeline/ui/app.js` (`/tr/app.js` olarak sunulur; aynı dosya, kopya değil) Kitaplar, çeviri akışı ve talimatlar bölümlerini Akışlar sekmesinde çizer (`TranslationUI.mount`); Mehteran'ın dilini, oturum anahtarını ve mesaj satırını kullanır. Kurulum bağlantıları Mehteran'ın Kurulum sekmesini açar.

İstekleri Mehteran'ın kendi sunucusundaki `/api/tr/...` adreslerine gider (`mehteran/translation.py`). `mehter ui` başlarken çeviri projesini bir kez, `./translate ui` gibi yükler (`pipeline.web.App(Project.load(...))`); ikinci bir sunucu açmaz. `/api/tr/<yol>` isteğini çeviri uygulamasının kendi istek işleyicisi (`pipeline.web.make_handler`) `/api/<yol>` olarak yanıtlar: aynı yollar, denetimler, parça parça okunan yüklemeler (en çok 300 MB), indirmeler ve hata kodları. Önce Mehteran'ın adres ve oturum anahtarı denetimleri yapılır; çeviri uygulaması Mehteran'ın oturum anahtarını kullanır. Proje yüklenemezse kitap çevirisi görünümü ve terminal nedenini söyler; Mehteran'ın geri kalanı çalışır. `./translate ui` (port 8765) aynı anda çalışabilir: bir kitabın çalıştırması, programlar arasında kitap başına kilitlenir.

Çeviri akışının çizimi ("Çeviri akışı"; Mehteran'da ve `./translate ui` içinde) yakınlaştırılabilir: −, + ve yakınlık düzeyi (tıklayınca %100), "Sığdır", Ctrl/⌘ + tekerlek ya da dokunmatik yüzeyde iki parmak, boş yeri sürükleyerek kaydırma. Seçilen yakınlık tarayıcıda saklanır ve çizim her yenilendiğinde geri konur; seçilmemişse çizim tuvale sığar, en az %85 büyüklükte. "Tam ekran" çizime ve seçili adımın paneline bütün pencereyi verir (Esc ile çıkılır; orada yeni adımlar adımlar arasındaki "+" ile eklenir). Adımlar daha büyük çizilir: belirgin numara, model adlarının tamamı, belirgin seçili adım; teslimden önceki "+ Adım ekle", "+" düğmesinin ne yaptığını söyler. Geniş pencerede seçili adımın paneli çizimin yanında, dar pencerede altındadır. Adım seçme, model değiştirme, sürükleme, adım ekleme, silme, sıralama ve kaydetme eskisi gibi çalışır.

`mehter ui` çalışırken çeviri uygulamasının kodu (`pipeline/*.py`, `pipeline/ui/*`) değişirse sayfa, Mehteran'ın kendi kodundaki gibi "sunucuyu yeniden başlatın" uyarısını gösterir.

## Diller

Bütün diller tek bir listededir: `mehteran/languages.json` (dil kaydı). Bir kayıtta dilin kodu, kendi adı, İngilizce adı, bayrağının ülke kodu ve yazı yönü vardır: `{"code": "ar", "native": "العربية", "english": "Arabic", "flag": "sa", "dir": "rtl", "ui": true}`. Mehteran sayfası, kitap çevirisinin arayüzü ve iş akışları bu listeyi kullanır (`mehteran/languages.py`, `GET /api/languages`). Çeviri uygulamasının varsayılan listesindeki (`config.default.toml`, `[languages]`) her dil bu listede vardır; bir test bunu denetler.

- **Arayüz dilleri** (`"ui": true`): Türkçe, English, العربية, Deutsch, Français, Español, Português, Italiano, Русский, فارسی, اردو, Bahasa Indonesia, Bahasa Melayu, Azərbaycanca, Bosanski, Shqip, 简体中文, 日本語. Sağ üstteki dil düğmesiyle seçilir: bayraklı bir liste ve bir arama alanı açılır (dilin adını herhangi bir dilde ya da kodunu yazın). Klavye çalışır: Enter, Boşluk ya da ↓ listeyi açar, ↑ ↓ gezdirir, Enter seçer, Esc kapatır. Seçim tarayıcıda saklanır. Arapça, Farsça ve Urduca sayfayı sağdan sola çevirir (`<html dir="rtl">`); iş akışı çizimi, kod ve günlükler soldan sağa kalır.
- **Tam ve kısmi diller**: Türkçe ve İngilizcede her metin vardır. Başka bir dilde metinlerin yalnızca bir bölümü olabilir; o dilde olmayan metin İngilizce gösterilir (sayfada da sunucu mesajlarında da). Çeviri uygulamasının kendi sunucu mesajları (`pipeline/i18n.py`) Türkçe ya da İngilizcedir: başka bir arayüz dili onları İngilizce alır.
- **Bayraklar**: bayrak bir ülkenindir, dil değildir: bayrak yalnızca satırı bulmaya yardım eder, yanında her zaman dilin kendi adı yazar. Bayraklar bu programın SVG dosyalarıdır (`mehteran/ui/flags/<ülke>.svg`, flag-icons 7.2.3, MIT; lisans o klasördedir), çünkü emoji bayraklar Windows'ta görünmez. İnternetten hiçbir şey yüklenmez.
- **Bir iş akışının çıktı dili**: `language` türündeki bir girdi, kayıttaki bütün dilleri aynı bayraklı listede sunar. Bütün seçenekleri dil kodu olan (ve kimliğinde `lang` geçen) bir `choice` girdisi de bayraklı liste olarak görünür, yalnızca kendi seçenekleriyle. Çalıştırma penceresi, iş akışı arayüz dilini sunuyorsa o dille açılır; sunmuyorsa iş akışının varsayılanıyla.

### Metinler nerede

| Metinler | Türkçe ve İngilizce | Öteki diller |
|---|---|---|
| Mehteran sayfası (`mehteran/ui/*.js` içinde `S("anahtar")`) | `mehteran/locales/tr.json`, `en.json`: `"ui"` | `mehteran/locales/<kod>.json`: `"ui"` |
| Sunucu ve komut satırı mesajları (`i18n.t("anahtar")`) | aynı dosyalar: `"messages"` | aynı dosyalar: `"messages"` |
| Kitap çevirisinin arayüzü | `pipeline/ui/app.js` içindeki `I18N` (kendi sayfasında yalnızca o dosya vardır) | `pipeline/ui/locales/<kod>.json` (`{anahtar: metin}`; Mehteran bunları `/tr/locales/<kod>.json` olarak sunar ve `TranslationUI.mount` / `setLang` ile verir) |

- `mehteran/i18n.py` içine `MESSAGES.update({...})` ya da `UI.update({"anahtar": {"tr": ..., "en": ...}})` olarak eklenen bir metin çalışmaya devam eder: yüklenen metinlerle birleştirilir ve o anahtarın öteki dillerini silmez. `python3 -m mehteran.i18n_tools absorb` böyle blokları dil dosyalarına taşır (`i18n.py` dosyasını başka kimse düzenlemiyorken çalıştırın).
- Sunucu dil dosyalarını başlarken okur: bir değişiklikten sonra yeniden başlatın (sayfa bunu söyler).
- Bir metin, İngilizce metindeki `{ad}` yer tutucularını korur; kitap çevirisi arayüzünün bir metni HTML etiketlerini de korur.

```text
python3 -m mehteran.i18n_tools coverage              her dilde kaç metin var
python3 -m mehteran.i18n_tools missing de            Almancada eksik anahtarlar, İngilizce metinleriyle
python3 -m mehteran.i18n_tools missing de --json     aynısı, {"ui": {...}, "messages": {...}, "translation": {...}} olarak
python3 -m mehteran.i18n_tools merge de bitti.json   bu biçimdeki çevrilmiş bir dosyayı dil dosyalarına ekler
python3 -m mehteran.i18n_tools validate [de]         tr ve en tam mı, anahtarlar biliniyor mu, yer tutucular ve etiketler aynı mı
```

Yeni bir arayüz dili: `mehteran/languages.json` içindeki kaydına `"ui": true` yazın; sonra `missing <kod> --json`, değerleri çevirin, `merge`, `validate`.

## Yerel modeller (Ollama) ve metin tanıma (OCR)

İsteğe bağlıdırlar ve yalnızca siz isteyince kurulurlar (Kurulum sekmesi ya da aşağıdaki komutlar); arkalarından anlatılan Typst, Pandoc, konuşmayı metne çevirme (whisper.cpp ve ffmpeg) ve qpdf de öyle. Bilgisayarda zaten olan (PATH üzerindeki) her araç bulunur ve kullanılır; Mehteran'ın `.runtime` içindeki kendi kopyası önce gelir. Diğer araçlarla aynı `<kod klasörü>/.runtime` klasörüne gider; yönetici izni gerekmez.

**Ollama** modelleri bu bilgisayarda çalıştırır; hiçbir yere bir şey gönderilmez. Mehteran kendine ait bir `ollama` sağlayıcısı ekler (çeviri uygulamasının `config.toml` dosyası değişmez; oradaki bir `[providers.ollama]` önceliklidir). Bir adım onu `ollama/<model>` olarak kullanır, örneğin `ollama/gemma3:4b`; çalıştırma formu kurulu modelleri sunar. Mehteran, Ollama'nın `127.0.0.1` (port 11434) üzerindeki HTTP arayüzünü kendi sistem istemiyle ve diğer modellerdeki veri etiketleriyle, aynı ayrı süreçte çağırır; iptal ve süre sınırı aynı çalışır.

- Zaten çalışan bir Ollama olduğu gibi kullanılır. Yoksa sistemdeki `ollama` (PATH, macOS uygulaması, Windows kurulumu), o da yoksa Mehteran'ın kurduğu. Bir çalıştırma ya da indirme gerektirince Mehteran `ollama serve` komutunu 127.0.0.1 üzerinde başlatır; Mehteran kapanınca, yalnızca onu Mehteran başlattıysa durdurur (günlüğü: `<veri>/jobs/ollama-serve.log`).
- Kurulum: Ollama 0.40.16, GitHub sürümünün resmî arşivi (`ollama-darwin.tgz`, `ollama-linux-amd64.tar.zst` / `-arm64`, `ollama-windows-amd64.zip` / `-arm64`); `mehteran/ollama.py` içinde yazılı SHA-256 özetleriyle denetlenir (sürümün `sha256sum.txt` dosyasından; GitHub'ın kendi özetleriyle aynı). Hiçbir kurulum betiği çalıştırılmaz. Linux'ta arşivi açmak için Python 3.14 ya da `zstd` programı gerekir.
- Modeller: kurulu olanlar (ad, boyut, tarih), önerilenler listesi (diskteki boyut, gereken bellek, diller, not; etiketler Ollama kayıt deposunda denetlendi), ilerlemesi görünen ve iptal edilebilen indirme (bir seferde bir tane), silme. İndirmeden önce bellek azsa uyarır, disk yetmiyorsa (zorlanmadıkça) reddeder. Modeller Ollama'nın kendi klasöründe kalır (`~/.ollama/models` ya da `OLLAMA_MODELS`).
- Ayarlar: `<veri>/configurations/providers.toml` dosyasında `[providers.ollama]` altında `model` (varsayılan model) ve `options` (`num_ctx`, `temperature`, `top_p`, `seed`). Mehteran varsayılan olarak 8192 jetonluk bağlam ister: Ollama'nın kendi varsayılanı küçüktür ve bir belgeyi sessizce keser.

**Tesseract OCR** taranmış PDF'leri ve resimleri okur. Bir PDF sayfası Poppler'ın `pdftoppm` programıyla resme çevrilir (300 dpi), sonra Tesseract okur.

- Kurulum: eksikse Poppler (ve micromamba) çeviri uygulamasının kurucusuyla; Tesseract 5.5.4 conda-forge'dan (micromamba her paketi denetler) `.runtime/tesseract` içine (yaklaşık 460 MB: paket, aralarında `tur`, `eng`, `ara`, `fas` olan 125 dilin verisini kendisi getirir); yalnızca hâlâ eksik bir dil varsa `eng`, `tur`, `ara`, `fas` dil verileri `tesseract-ocr/tessdata_fast` deposunun 4.1.0 etiketinden, her biri `mehteran/ocr.py` içinde yazılı SHA-256 özetiyle denetlenerek, `.runtime/tessdata` içine. Kurulu bir Tesseract (örneğin Homebrew'unki) da kendi dilleriyle kullanılır. Osmanlıca için Tesseract modeli yoktur (`ota` bulunmuyor); Arap harfleri için `ara` ya da `fas` kullanın.
- Daha fazla dil, Kurulum sekmesinde sunulur ve yalnızca seçilince indirilir: `deu`, `fra`, `spa`, `ita`, `por`, `nld`, `rus`, `ell`, `aze`, `kmr` (Kurmancî), `urd`, `heb`, `hin`, `chi_sim`, `jpn`, `kor` (tessdata_fast 4.1.0, her biri SHA-256 özetiyle denetlenir; özetler etiketin git blob özetleriyle de karşılaştırıldı). conda-forge'un Tesseract'ı bunların çoğunu zaten getirir; yalnızca eksik olanlar indirilir. Seçim yapılmazsa `ocr-languages` eskisi gibi `eng tur ara fas` kurar.
- `document.extract`, `ocr` alır: `auto` (varsayılan: yalnızca bir PDF'in metin katmanı neredeyse olmayan sayfaları ve resimler), `always`, `never`; ve `ocr_languages` (`tur+eng`; boşsa kurulu olduğu ölçüde Türkçe ve İngilizce). Dosya girdileri resim de alır: `png`, `jpg`, `jpeg`, `tif`, `tiff`. Sınırlar: dosya başına 500 sayfa, sayfa başına 180 saniye; iptal çalışan programı durdurur. Tesseract yoksa, bazı sayfalarında metin katmanı olan bir PDF eskisi gibi okunur; tamamen taranmış olan, neyin kurulacağını söyleyen bir mesajla başarısız olur.

**Typst**, `document.export` adımının PDF'ini yapar (`formats: [pdf]`).

- Kurulum: Typst 0.15.1, GitHub'daki resmî sürüm arşivi (macOS arm64/x64, Linux x64/arm64, Windows x64/arm64; 14–22 MB) `.runtime/typst` içine; Arap harfleri için Amiri 1.003 yazı tipi (SIL Open Font License, 1 MB, `aliftype/amiri`) `.runtime/typst/fonts` içine. Her arşiv `mehteran/typst.py` içinde yazılı SHA-256 özetiyle denetlenir (özetler indirilen dosyalardan hesaplandı; GitHub'ın kendi özetleriyle aynı).
- Markdown, Typst biçimine çevrilir: başlıklar, paragraflar (Word ve HTML dışa aktarımındaki gibi satır sonu korunur), madde ve numaralı listeler (iç içe), alıntılar, kod blokları, tablolar (sütun hizalarıyla), yatay çizgiler, kalın, italik, üstü çizili, satır içi kod, `http(s)`/`mailto` bağlantıları ve dipnotlar (`[^n]` ve `[^n]: metin` satırı). Metnin her parçası Typst dosyasına bir dize olarak yazılır; metindeki hiçbir karakter Typst biçimlendirmesi ya da kodu gibi çalışamaz. Sayfa A4'tür, sayfa numaralıdır. Yazı tipleri: Libertinus Serif (Typst'in içinde; Türkçeyi karşılar) ve Arap harfleri için Amiri; soldan sağa bir belgedeki çoğunlukla Arapça bir paragraf sağdan sola dizilir; `lang` dili belirler (sağdan sola bir dil bütün belgeyi sağdan sola yapar). Başka yazılar (Çince, Japonca, İbranice...) bilgisayarda varsa onun yazı tipleriyle çıkar. LaTeX formülleri PDF'te metin olarak kalır (denklem için Pandoc ile Word kullanın).
- Typst yoksa `pdf` biçimli bir iş akışı hiçbir şey yazmadan "PDF için Typst gerekli. Kurulum sekmesinden Typst'i kurun." mesajıyla durur.

**Pandoc** (isteğe bağlı) belgeleri dönüştürür. Mehteran'ın kendi Word dönüştürücüsü varsayılan olarak kalır.

- Kurulum: Pandoc 3.14, GitHub'daki resmî sürüm arşivi (macOS arm64/x64, Linux x64/arm64, Windows x64; 27–44 MB, açılınca yaklaşık 190 MB; ARM Windows x64 sürümünü kullanır), `mehteran/pandoc.py` içindeki SHA-256 özetleriyle denetlenerek `.runtime/pandoc` içine. Pandoc her zaman `--sandbox` ile çalışır: bir belge ona başka dosya okutamaz, ağdan bir şey indirtemez.
- `document.export`: `formats: [epub]` Pandoc ister. `converter`: `auto` (varsayılan: Mehteran'ın kendi Word dosyası; Pandoc kuruluysa ve metinde LaTeX formülü, `$...$` ya da `$$...$$`, varsa Pandoc'unki: formüller gerçek Word denklemi olur), `builtin`, `pandoc` (her Word dosyası Pandoc ile). Tek başına `$5` formül sayılmaz.
- `document.extract`, `.odt` ve `.rtf` dosyalarını Pandoc ile okur (Markdown olarak; tablolar Markdown tablosu olur). EPUB ve Word girdisi eskisi gibi Pandoc'suz okunur.

**Konuşmayı metne çevirme** (whisper.cpp ve ffmpeg), ses ve video dosyalarındaki konuşmayı bu bilgisayarda yazıya döker.

- Kurulum: sabit sürümlü conda-forge paketleri `whisper.cpp=1.9.3` (yaklaşık 13 MB indirme) ve yalnızca bilgisayarda ffmpeg yoksa `ffmpeg=9.0.2` (sisteme göre kütüphaneleriyle yaklaşık 80–170 MB), `.runtime/speech` içine; micromamba her paketi denetler. conda-forge ikisini de macOS (arm64, x64), Linux (x64, arm64) ve Windows x64 için yapar; ARM Windows için yoktur. Ardından `base` modeli.
- Modeller: Hugging Face'teki resmî `ggerganov/whisper.cpp` deposunun çok dilli ggml modelleri, sabit `5359861c` sürümünden, her biri `mehteran/speech.py` içindeki SHA-256 özetiyle denetlenerek (özetler indirilen dosyalardan hesaplandı; deponun LFS özetleriyle aynı) `.runtime/whisper-models` içine: `tiny` (78 MB), `base` (148 MB), `small` (488 MB), `large-v3-turbo-q5_0` (574 MB, en doğrusu), `medium` (1,5 GB).
- `document.extract` şunları okur: `mp3`, `wav`, `m4a`, `ogg`, `opus`, `flac`, `aac`, `mp4`, `webm`, `mov`, `mkv`; ffmpeg 16 kHz tek kanallı WAV yapar, whisper.cpp metni yazar. Gelişmiş ayarlar: `speech_model` (`auto`: base, small, large-v3-turbo-q5_0, medium, tiny sırasıyla ilk kurulu olan; ya da bunlardan biri) ve `speech_language` (`auto` dili kendisi bulur; `tr`, `en`, `ar`, `fa`, `ur`, `de`, `fr`, `es`, `it`, `ru`, `az`, `nl`, `pt`, `zh`, `ja`). İptal çalışan programı durdurur. Araçlar ya da model yoksa adım neyin kurulacağını söyleyen bir mesajla başarısız olur.

**qpdf** bozuk PDF'leri onarır, parolasız açılan PDF'lerin şifrelemesini kaldırır. `document.extract` bir PDF'i okuyamazsa (pdftotext başarısız olursa) qpdf'e onarılmış bir kopya yazdırır ve onu okur; qpdf yoksa ilk hata geçerlidir. Kurulum: sabit sürümlü conda-forge paketi `qpdf=12.4.2` (yaklaşık 6 MB indirme) `.runtime/qpdf` içine.

conda-forge kurulumları (konuşmayı metne çevirme, qpdf) micromamba ister; yoksa çeviri uygulamasının kurucusu onu önce Poppler ile birlikte kurar (onay penceresi bunu söyler).

**Önerilen Ollama modelleri** arasında bir resim okuyan model (`qwen2.5vl:7b`, 6,0 GB) ve bir gömme (embedding) modeli (`bge-m3:567m`, 1,2 GB) de vardır, öyle etiketlidir. Mehteran'ın adımları henüz modele resim göndermez; gömme modeli de bir adımın modeli olamaz: ileride kullanılmak üzere listelenirler.

```
./mehter install-local ollama                     Ollama'yı kurar (sabit sürüm, denetlenmiş)
./mehter install-local ocr [tur eng ara fas]      Tesseract OCR ve dil verilerini kurar
./mehter install-local ocr-languages tur ara jpn  dil verisi ekler
./mehter install-local typst                      Typst'i ve Amiri yazı tipini kurar
./mehter install-local pandoc                     Pandoc'u kurar
./mehter install-local speech [base]              whisper.cpp'yi (gerekirse ffmpeg'i) ve modelleri kurar
./mehter install-local speech-models small tiny   konuşma modeli ekler
./mehter install-local qpdf                       qpdf'i kurar
```

Kurulum sekmesinin API'si ve JSON biçimleri İngilizce kılavuzdadır: [Local models and OCR](mehteran.md#local-models-ollama-and-text-recognition-ocr).

## Kullanım, bir adımın modelini değiştirme, canlı günlük

- **Kullanım** (`GET /api/usage`): Mehteran her model çağrısını sayar (sağlayıcı, model, süre, sonuç: `ok`, `failed`, `quota`, `aborted`; sınırda ne zamana kadar). Sağlayıcı başına toplamlar, bugün / son 5 saat / son 7 gün pencereleri, model başına sayılar, son kullanım sınırı ve sıfırlanma zamanı. `tool_reported` yalnızca aracın kendi yazdığıdır, bilinmiyorsa `null`: Codex oturum günlüklerindeki sınırlar (5 saatlik ve haftalık pencerenin yüzdesi, sıfırlanma zamanı; Mehteran'ın kendi Codex çağrıları `--ephemeral` olduğu için değer son etkileşimli kullanımdandır), Claude Code'un yalnızca istenince (`POST /api/usage/probe/<sağlayıcı>`, en küçük modelle tek kelimelik bir çağrı) okunan `rate_limit_event` bilgisi. Gemini CLI, Antigravity CLI ve Ollama sınır bildirmez. Çeviri uygulamasının `.jobs/quota.json` kaydı ve Kurulum sekmesindeki son model denemesinin sınırı da gösterilir. Kimlik bilgisi dosyası okunmaz.
- **Model değiştirme** (`POST /api/runs/<çalıştırma>/nodes/<düğüm>/switch` `{provider: "gemini/<model>"}`): kullanım sınırı bekleyen, başarısız, iptal edilmiş ya da yarıda kalmış bir yapay zekâ adımı için. Bekleyen adım beklemeyi hemen bırakır ve yeni modelle yeniden çalışır; diğerleri yeniden denenir; bir döngü bitmiş parçalarını korur. Olay günlüğüne "Model değiştirildi: eski → yeni" yazılır. İsteğe bağlı `fallback_provider` (düğümde, `retries` yanında): adımın modeli kullanım sınırına takılınca beklemeden ona geçilir; o da takılırsa beklenir.
- **Canlı günlük** (`GET /api/runs/<çalıştırma>/log?node=<düğüm>&offset=<bayt>` → `{text, offset, size, done, status}`): her düğüm çalışırken `nodes/<düğüm>/log.txt` dosyasına yazar (denemeler, model çağrıları ve cevapları, 30 saniyede bir "hâlâ çalışıyor", beklemeler, model değişiklikleri, döngü parçaları). Gizli anahtara benzeyenler maskelenir; günlük en çok 2 MB'tır. Ollama'nın cevabı yazıldıkça akar; komut satırı araçlarının cevabı çeviri uygulamasının sağlayıcı kodu araç bitince döndüğü için çağrı bitince görünür.
- **Etkinlik** (`GET /api/activity`): süren ve bekleyen çalıştırmalar, çalışan düğümleri, geçen süre, bekleme nedeni; çeviri uygulamasının şu anda çevirdiği kitaplar. JSON biçimleri İngilizce kılavuzda.

**Arayüzde** (`mehteran/ui/live.js`): Kurulum'daki her yapay zekâ aracı kartında "Kullanım" bölümü (Mehteran'ın kendi sayımları: bugün, son 5 saat, son 7 gün; son kullanım sınırı ve açılmasına kalan süre; aracın kendi bildirdiği sınırlar, bildirmiyorsa "bilinmiyor"; Claude Code için çok kısa tek bir model çağrısı yapan "Kullanımı kontrol et"). Çalıştırma formunda ve model seçiminde aracın yanında kısa bir kullanım ipucu ("5 saat: %54"; sınıra yakınken uyarı renginde). Çalıştırma sayfasında genel ilerleme çubuğu, geçen süreler, denemeler, bekleme nedenleri ve seçili (ya da çalışan) adımın canlı günlüğü (sona kendiliğinden kayar; yukarı kaydırınca durur; "Kopyala"). Kullanım sınırı bekleyen, hata veren, iptal edilen ya da yarıda kalan adımda "Bekle" (varsayılan) ve "Başka modelle devam et". Düzenleyicide model alan adımların gelişmiş ayarlarında "Yedek model" (boşsa kapalı). Üst çubukta şu an çalışanlar ("2 çalışıyor"); tıklayınca çalıştırmalar ve çevrilen kitaplar, her birinin durdurma düğmesiyle (■) listelenir. Kitaplıkta yıldızla favoriler (`<veri>/configurations/library.json`), kitap çevirisinin hemen altında "Favoriler" bölümü ve "★ Favoriler" süzgeci, "Son kullanılanlar"; çalıştırma formu her iş akışının son değerlerini bu tarayıcıda hatırlar (dosyalar ve anahtar/parola gibi adlandırılanlar hariç): "Geçen seferki gibi". "/" arama kutusuna gider.

## Komut satırı

```
./mehter templates                               şablonları listeler
./mehter validate akisim.yaml                    bir iş akışı dosyasını denetler; sorunların hepsini listeler
./mehter run document-comparison \
    --input first=eski.docx --input second=yeni.docx \
    --input analyst_model=claude/opus@high --input language=tr
./mehter run multi-document-comparison \
    --input documents=a.pdf --input documents=b.docx --input documents=c.md
./mehter runs                                    çalıştırma geçmişi
./mehter resume <çalıştırma> [--node <id>]       bir çalıştırmayı sürdürür ya da başarısız bir düğümü yeniden dener
./mehter cancel <çalıştırma>                     bir çalıştırmayı durdurur
./mehter approve <çalıştırma> <düğüm> [--comment ...]   bekleyen bir onay düğümünü onaylar (reject: reddeder)
```

`run`, bir şablon kimliği (`builtin:<id>`, `user:<id>` ya da yalnızca id) veya bir `.yaml` dosyasının yolunu alır. `multiple: true` olan bir girdi, her dosya için bir kez `--input <id>=<dosya>` alır. Çalıştırma bitene kadar her düğümün durumunu gösterir. Ctrl+C çalıştırmayı iptal eder. Çıkış kodu: 0 bitti, 3 onay bekliyor, aksi hâlde 1.

## Hazır şablonlar

Altı kategoride 36 hazır şablon. Her biri Şablonlar sekmesinde anlatılır (ne yaptığı, girdileri, akışı).

| Kategori | Şablonlar |
|---|---|
| **Araştırma** (`research`) | `abstract-title-improvement` (Özet ve başlık iyileştirme), `academic-paper-review` (Akademik makale değerlendirmesi), `grant-proposal-review` (Proje önerisi değerlendirmesi), `literature-synthesis` (Literatür sentezi), `research-question-critique` (Araştırma sorusu ve hipotez eleştirisi), `reviewer-response-letter` (Hakemlere cevap mektubu), `study-guide-questions` (Ders notu ve sınav soruları), `thesis-chapter-feedback` (Tez bölümü geri bildirimi) |
| **Belgeler** (`documents`) | `chapter-summaries` (Uzun belge, bölüm bölüm özet; döngü), `document-comparison` (Belge karşılaştırma), `document-consistency-check` (Belge içi tutarlılık denetimi), `meeting-minutes-actions` (Toplantı tutanağı ve aksiyonlar), `multi-document-comparison` (Çok belgeli karşılaştırma; birden çok dosya ve döngü), `multi-length-summary` (Farklı uzunluklarda özet), `policy-gap-analysis` (Politika boşluk analizi), `requirements-review` (Gereksinim belgesi incelemesi) |
| **Hukuk** (`legal`) | `contract-risk-review` (Sözleşme risk incelemesi), `nda-review` (Gizlilik sözleşmesi (NDA) kontrolü), `regulatory-compliance-checklist` (Mevzuata uyum kontrol listesi), `terms-plain-language` (Kullanım koşulları ve gizlilik politikası, sade dille) |
| **İş** (`business`) | `business-plan-critique` (İş planı ve sunum eleştirisi), `expense-anomaly-review` (Fatura ve harcama tutarsızlık notları), `financial-period-comparison` (İki dönemin finansal karşılaştırması), `financial-report-analysis` (Finansal rapor analizi), `request-triage` (Talep ve şikâyet önceliklendirme; koşul), `rfp-compliance-matrix` (İhale şartnamesi uyum matrisi) |
| **Veri** (`data`) | `data-analysis-plan` (Veri analizi planı ve yorum), `dataset-documentation-review` (Veri seti belgelendirme incelemesi), `spreadsheet-analysis` (Tablo (CSV / Excel) analizi), `survey-response-themes` (Anket açık uçlu yanıt temaları) |
| **Yazı** (`writing`) | `cv-job-fit` (Özgeçmiş ve iş ilanı uyumu), `plain-language-rewrite` (Sade dille yeniden yazım), `proofreading-change-list` (Düzelti ve değişiklik listesi), `style-guide-review` (Yazım kılavuzuna göre editoryal değerlendirme), `tone-audience-adaptation` (Ton ve okura uyarlama), `translation-quality-review` (Çeviri kalite değerlendirmesi) |

## Veriler nerede

Mehteran verilerini kod klasörünün dışında tutar:

| Sistem | Klasör |
|---|---|
| macOS | `~/Library/Application Support/Mehteran` |
| Windows | `%LOCALAPPDATA%\Mehteran` |
| Linux | `$XDG_DATA_HOME/mehteran`, yoksa `~/.local/share/mehteran` |

`MEHTERAN_HOME` ortam değişkeni bu klasörün yerine geçer. Alt klasörler:

- `templates/`: sizin şablonlarınız (her biri bir `<id>.yaml`).
- `executions/<çalıştırma>/`: her çalıştırma için bir klasör: `workflow.yaml` (dondurulmuş kopya), `inputs/` (yüklenen dosyalar; birden çok dosya alan bir girdide her dosya `inputs/<id>/<n>/` içinde), `nodes/<düğüm>/` (her düğümün çıktıları, her model çağrısının istemi; bir döngü her parçanın istemini ve cevabını `nodes/<düğüm>/parts/` içinde tutar).
- `databases/mehteran.sqlite3`: her çalıştırmanın ve düğümün durumu (SQLite, WAL kipi).
- `configurations/`: Kurulum sekmesinin sakladıkları: `models.json` (araçlardan okunan model listeleri; `config.toml` modellerinin yanında sunulur) ve `quota.json` (bir model denemesinin karşılaştığı son kullanım sınırı).
- `jobs/`: Kurulum sekmesinden başlatılan kurulumların günlükleri.
- `workflows/`: sonraki sürümler için ayrıldı; şimdilik boş.

Araçlar, çeviri uygulamasının `config.toml` dosyasından gelir (`[providers.*]`); Mehteran bu dosyayı yalnızca okur, hiç yazmaz. Oturumları araçlar kendi klasörlerinde tutar (çeviri uygulamasındaki gibi). `MEHTERAN_CONFIG`, aynı bölümleri içeren başka bir TOML dosyasını gösterebilir.

## Bir çalıştırma nasıl işler

- Bir düğüm, kendisine bağlı bütün düğümler bitince başlar. Birbirine bağlı olmayan düğümler aynı anda çalışır (bir çalıştırmada en çok 4).
- Her düğümün bir tekrar deneme sayısı ve deneme başına bir süre sınırı vardır. Süre sınırı ya da iptal, model çağrısını başlattığı araçla birlikte durdurur.
- Model, istemi boş bir geçici klasörde stdin üzerinden, çeviri uygulamasının sağlayıcı koduyla (`pipeline.providers.run`) alır. Mehteran her çağrıyı bir kez dener; tekrar denemeleri motor sayar.
- Kullanım sınırları: bir araç kullanım ya da hız sınırı bildirince (çeviri uygulamasının kodu, `pipeline.providers`, bunu tanır) düğüm başarısız olmaz. "Kullanım sınırı bekleniyor" (`waiting_quota`) gösterir, olay günlüğü ne zamana kadar beklendiğini yazar ve sınır kalkınca yeniden dener: aracın söylediği zamanda, yoksa `config.toml` dosyasındaki `quota_wait_minutes` (`[general]`) sonra. Bekleme başarısız bir deneme sayılmaz. Bekleme toplamda `quota_max_hours` süresinden uzun sürecekse düğüm başarısız olur. İptal beklemeyi hemen bitirir.
- Bir çalıştırmada aynı anda en çok 4 model çağrısı çalışır; döngü parçalarınınkiler de buna dahildir.
- Koşullar: bir `condition` düğümü yalnızca seçtiği dalın çıkışını (`true` ya da `false`) verir. Öteki çıkışa bağlı düğümler ve yalnızca onlara bağlı olan her şey atlanır. Bir birleştirme düğümü (`text.merge`, `document.export`), bağlantılarından en az biri seçilen bir daldan geliyorsa çalışır; atlanan dalın çıktısı orada boş metindir. Diğer düğümler ancak bütün bağlantıları seçilmiş dallardan geliyorsa çalışır. Atlanan bir dal çalıştırmayı başarısız yapmaz; başarısız bir düğüm ise ardından gelen her şeyi yine atlar ve çalıştırma başarısız olur.
- Döngüler: bir `ai.map` düğümü bir metni parçalara böler ve modeli her parça için bir kez, paralel olarak çağırır. Her cevap isteminin bir özetiyle (hash) saklanır: yeniden deneme ya da sürdürme yalnızca cevabı olmayan parçaları sorar. Düğümün süre sınırı bütün düğüme değil, her model çağrısına uygulanır; tekrar denemeler düğüme uygulanır (biten parçalar denemeler arasında korunur).
- Çalıştırma; iş akışının dondurulmuş bir kopyasını, çözülmüş model adlarını (`claude/opus@high`) ve araç ayarlarını saklar. Sürdürme ve yeniden deneme bu kopyaları kullanır, güncel şablonu değil.
- Sürdürme: biten düğümler korunur; yalnızca diğerleri çalışır. Programı kapanmış (terminal kapatılmış, çökmüş) bir çalıştırma "yarıda kaldı" olarak görünür ve sürdürülebilir.
- Bir onay düğümü, bir kişi onaylayana ya da reddedene kadar kendi dalını durdurur. Bu sırada açık kalması gereken bir program yoktur; onay arayüzden ya da komut satırından, yeniden başlatmadan sonra da verilebilir.
- Bir çalıştırmayı aynı anda yalnızca bir program yürütür (çalıştırma klasöründe bir kilit dosyası).
- Her dilde mesajlar: Mehteran kendi mesajlarını (olay günlüğü, düğüm ve çalıştırma hataları) mesaj anahtarı ve değerleriyle saklar ve okuyanın dilinde gösterir (arayüzün dil seçimi, komut satırının `--lang` değeri). `GET /api/runs/<çalıştırma>` içindeki bir olay `{time, node_id, kind, message, text, key, params}` biçimindedir: `message` ve `text` isteğin dilindeki aynı metindir; `key` ve `params` saklanan mesajdır (iç içe bir mesaj `{"$key": ..., "params": {...}}`), eski çalıştırmalarda ve bir aracın yazdığı metinde `null` olur ve metin saklandığı gibi gösterilir. Bir düğümün (ve çalıştırma listesinde bir çalıştırmanın) `error` alanı isteğin dilindedir; yanında aynı biçimde `error_key` ve `error_params` vardır. Veritabanı yeni sütunları kendisi ekler; eski satırlar metinlerini korur.

## İş akışı dosyası başvurusu (schema_version 1)

Örnek dosya ve alanların tam listesi İngilizce kılavuzdadır: [Workflow file reference](mehteran.md#workflow-file-reference-schema_version-1). Özet:

- Üst düzey: `schema_version: 1`, `id`, `name`, `description`, `version`, `category`, `based_on`, `inputs`, `nodes`, `connections`, `outputs`, `layout`. `name`, `description` ve etiketler bir metin ya da `{tr, en}` eşlemesidir.
- `layout` (isteğe bağlı) görsel düzenleyicinin yazdığı yerleşimdir: her düğüm için kutusunun tuvaldeki konumu, piksel olarak (`extract: {x: 0, y: 0}`). Yalnızca iş akışının düğüm kimlikleri, her biri tam olarak `x` ve `y` ile, −100000 ile 100000 arasında tam sayılar. Motor onu yok sayar. Yoksa düzenleyici kutuları akış sırasına göre kendiliğinden yerleştirir.
- Girdi türleri: `file` (`formats`: `pdf`, `docx`, `epub`, `md`, `txt`, `csv`, `tsv`, `xlsx` OCR ile okunan resimler `png`, `jpg`, `jpeg`, `tif`, `tiff`, Pandoc ile okunan `odt`, `rtf` ve konuşması metne çevrilen ses ve video dosyaları `mp3`, `wav`, `m4a`, `ogg`, `opus`, `flac`, `aac`, `mp4`, `webm`, `mov`, `mkv`; `multiple: true` ile 1–20 dosya, toplam en çok 500 MB), `text` (`multiline`), `choice` (`options`), `provider` (araç, isteğe bağlı model ve düşünme düzeyi), `language` (kayıttaki bir dilin kodu; "Çıktı dili" bölümüne bakın). `required: false` yazılmadıkça zorunludur.
- Tablolar: CSV, TSV ya da Excel (.xlsx) dosyası Markdown tablolarına okunur; ilk satır başlıktır. CSV ayırıcısı `,`, `;`, sekme ya da `|` olabilir (kendiliğinden bulunur); kodlama UTF-8, değilse Windows Türkçe (cp1254). Bir .xlsx dosyasının görünen her sayfası `## <sayfa adı>` altında bir tablodur; tarih biçimli sayılar tarih olur (`2024-01-31`). Sınırlar (kesildiği yerde metin bunu söyler): tablo başına 1.000 satır ve 40 sütun, hücre başına 300 karakter, 20 sayfa, dosya başına 500.000 karakter.
- Düğüm türleri: `document.extract` (`file`, `max_chars` dosya başına, `ocr`: `auto`, `always`, `never`, `ocr_languages`, `speech_model`, `speech_language`; isteğe bağlı bir dosya girdisi boş bırakılmışsa metni boştur; birden çok dosyada her dosya `<document name="<dosya>" index="<n>">` ile `</document>` arasındadır), `ai.cli` (`provider`, `prompt`), `text.merge` (`template`), `approval` (`show`, `instructions`), `document.export` (`source`, `title`, `lang`, `formats`: `md`, `docx`, `html`, `pdf`, `epub`; `filename`, `converter`: `auto`, `builtin`, `pandoc`; Markdown tabloları Word, HTML ve PDF'te gerçek tablo olur), `condition` (`value`, `operator`: `contains`, `not_contains`, `equals`, `regex`, `is_yes`, `empty`; `match`, `is_yes` ve `empty` dışında gerekli; `case_sensitive`; çıktısı yalnızca seçilen dal: `true` ya da `false`), `ai.map` (`source`, `split`: `headings`, `paragraphs`, `chunks`, `files`; `chunk_chars`, `max_items` en çok 200, `provider`, `prompt`, `heading`; çıktısı `text`). Her düğüm `retries` (0–10) ve `timeout` (saniye) alabilir; onay düğümü almaz. Örnekler İngilizce kılavuzda.
- Yalnızca talimat: bir adım yalnızca bir talimat ve bir modelden oluşabilir; bağlantılar hangi metinler üzerinde çalışacağını söyler. Talimat hiçbir veri adlandırmıyorsa (`{{nodes.*}}` ya da dosya girdisi yoksa) bağlı adımların metinleri bağlantı sırasıyla, her biri adımının başlığıyla ve veri etiketleri arasında talimatın arkasına eklenir; iş akışında `language` girdisi varsa ve talimat onu kullanmıyorsa sona "Write the answer in <dil>." satırı eklenir. Verisini adlandıran adımlar (bütün hazır şablonlar böyledir) tam olarak eskisi gibi çalışır. `template` olmayan `text.merge` ve `source` olmayan `document.export`, bağlı metinleri sırayla (birden çoksa `## <başlık>` altında, atlanan dallar olmadan) birleştirir; `source` olmayan `ai.map` bağlı metni böler ve `{{item.text}}` yoksa her parçayı talimatın arkasına veri olarak ekler; `show` olmayan `approval` bağlı metni gösterir; `file` olmayan `document.extract` iş akışının tek dosya girdisini okur. `condition` için `operator: ai`: model (`provider`), bağlı metin veri olarak verilerek `question` sorusuna evet ya da hayır der (ilk kelime: yes/evet/e/doğru → `true`, no/hayır/h/yanlış/değil → `false`); belirsizse bir kez daha sorulur, yine belirsizse düğüm başarısız olur. Editörün sade panelinde gösterilen alanlar `GET /api/node-types` içinde `basic: true` ile işaretlidir (`ai.cli`/`ai.map`: `prompt`, `provider`; `condition`: `question`, `provider`; `document.export`: `formats`; `approval`: `instructions`); yeni bir koşul `initial_config` ile (`operator: ai`) başlar. Örnek YAML İngilizce kılavuzda.
- Koşuldan çıkan bir bağlantı dalını yazmalıdır (`from: gate.true`). `is_yes`, metnin ilk kelimesi yes, y, true, evet, e ya da doğru ise doğrudur. İşlecin adı `yes` değildir: YAML yalın `yes` kelimesini true olarak okur.
- Döngü isteminde `{{item.text}}` (parçanın metni), `{{item.title}}` (başlığı ya da dosya adı), `{{item.index}}` (sırası) ve `{{item.count}}` (parça sayısı) kullanılır; metin ve başlık, düğüm çıktıları gibi veri etiketleri arasına konur. `{{item.*}}` yalnızca bir `ai.map` düğümünün isteminde kullanılabilir. Parça sayısı `max_items` değerini aşarsa düğüm açık bir mesajla başarısız olur.
- Yer tutucular: `{{inputs.<id>}}` ve `{{nodes.<id>.<çıktı>}}`. Bir düğüm başka bir düğümün çıktısını yalnızca bir bağlantı (`from: <düğüm>.<çıktı>`, `to: <düğüm>`) onları birleştiriyorsa kullanabilir. Değiştirme tek geçişte yapılır: eklenen metin (bir belge, bir yanıt) yeniden taranmaz. `ai.cli` isteminde her düğüm çıktısı `<data source="...">` ve `</data>` etiketleri arasına konur; istem, bu etiketlerin içeriğinin talimat değil veri olduğunu söyleyen bir notla başlar.
- Denetim şunları reddeder: her düzeyde bilinmeyen anahtarlar, tekrarlanan kimlikler ya da anahtarlar, olmayan düğüm veya çıktılara bağlantılar, döngüler, bilinmeyen düğüm türleri, çözülemeyen ya da bağlantısı olmayan yer tutucular ve kimlik bilgisine benzeyen her şey (`api_key`, `token`, `password` gibi anahtarlar ya da API anahtarına benzeyen değerler). Sorunların hepsi, dosyadaki yerleriyle birlikte bir kerede listelenir.

### Çıktı dili (şablon yazarları için)

Bir iş akışının yazacağı dil için `language` türünde bir girdi kullanın: `- {id: language, type: language, label: {tr: Rapor dili, en: Report language}}`.

- Çalıştırma penceresi bu girdiyi kayıttaki bütün dillerle bayraklı liste olarak gösterir ve çalıştıranın arayüz diliyle açar. `default` yazmayın: `default: en` ile bir Türk kullanıcı, değiştirmedikçe İngilizce belge alır. (Tek bir dille başlaması gereken bir iş akışında `default: <kod>` yazılabilir.)
- Değeri dil kodudur (`tr`, `en`, `ar`, `uz`...). `document.export` adımına `lang: "{{inputs.language}}"` olarak verin. Girdinin kimliği `language` ise ve bir talimat `{{inputs.language}}` kullanmıyorsa, o talimata "Write the answer in <dilin İngilizce adı>." satırı eklenir; talimata ayrıca dil cümlesi yazmak gerekmez.
- Komut satırından ya da API'den değer verilmeden (ve varsayılan olmadan) başlatılan bir çalıştırma mesaj dilini kullanır (`--lang`, `X-Lang`).
- `language` girdisinde `options` kullanılamaz. Yalnızca bazı dilleri sunmak için seçenekleri dil kodu olan bir `choice` girdisi bırakın (`options: [tr, en, ar]`, kimliği `language`): bayraklı liste olarak o seçeneklerle görünür ve arayüz dili seçenekler arasındaysa onunla açılır.
- Bir iş akışının etiketleri ve açıklamaları `{tr, en}` eşlemesi olarak kalır; başka bir arayüz dili İngilizce metni gösterir.

## Güvenlik

- Arayüz yalnızca `127.0.0.1` adresini dinler. İstekler `127.0.0.1:<port>` ya da `localhost:<port>` adresine gönderilmelidir.
- Her başlatmada yeni bir oturum anahtarı oluşur; her API isteği bunu taşımalıdır (sabit sürede karşılaştırılır).
- Boyut sınırları: JSON isteği için 2 MB, yükleme için 300 MB, birden çok dosya alan bir girdi için 20 dosya ve toplam 500 MB. Yüklenen dosyanın adı güvenli bir yalın ada indirgenir.
- Bir .xlsx dosyası çeviri uygulamasının korumalı XML okuyucusuyla okunur: varlık (entity) tanımı olan ya da açılınca 100 MB'ı aşan bir parça okunmaz.
- Her dosya erişimi veri klasörünün içinde çözülür; dışına çıkan bir yol reddedilir. Word ve HTML sonuçları yalnızca indirilir, arayüzün içinde gösterilmez.
- Yanıtlar `X-Content-Type-Options: nosniff`, `Cache-Control: no-store` ve sıkı bir Content-Security-Policy taşır (satır içi betik ve stil yok, çerçeve yok). Başka hiçbir sayfa Mehteran'ı çerçevede gösteremez.

## Çeviri uygulamasıyla sınır

Mehteran çeviri uygulamasının Python kodunu değiştirmez. Şu dosyaların hiçbirini değiştirmez: `pipeline/*.py`, `prompts/`, `config.default.toml`, `config.toml`, `scripts/start.sh`, `scripts/start.cmd`, `translate`, `translate.cmd`, `Open Interface.*`, `books/`. Çeviri uygulamasının arayüzü (`pipeline/ui/`) ortaktır: `app.js` kendini hem kendi sayfasına hem Mehteran'ın sayfasına yerleştirir (`TranslationUI.mount`); `style.css` kendi kurallarını `.tr-app` altında tutar. Mehteran'ın stil dosyası `pipeline/ui/style.css` dosyasının temel kurallarının bir kopyasıyla başlar; sayfa, kitap çevirisi için `pipeline/ui/style.css` dosyasını ondan önce yükler.

Mehteran `pipeline` paketinin şu parçalarını içe aktarır ve yalnızca okur ya da çağırır:

| Modül | Ne için |
|---|---|
| `pipeline.providers.run` | her model çağrısı (`mehteran/worker.py` içinde) |
| `pipeline.core.Project`, `pipeline.core.ROOT` | sağlayıcı çağrısının ayar nesnesi; `config.toml` dosyasının yeri |
| `pipeline.documents.read_blocks` | PDF, Word, EPUB, Markdown ve metin dosyalarının metni |
| `pipeline.documents.segment`, `split_long`, `_parse_xml`, `_zip_read` | uzunluğa göre bölünen döngü parçaları; .xlsx dosyasını güvenle okuma |
| `pipeline.export.to_docx`, `to_html`, `inlines` | Word ve HTML raporları (`mehteran/tables.py` tabloları ekler) |
| `pipeline.providers.QuotaError` | bir aracın bildirdiği kullanım sınırı (worker iletir, motor bekler) |
| `pipeline.system` | süreç grupları, bir süreç ağacını durdurma, çalıştırma kilidi |
| `pipeline.tools` | kurulu araçları bulma; durumları, oturumları ve model listeleri (Kurulum sekmesi) |
| `pipeline.runtime.install_tool` | bir aracı `.runtime` içine kurma (`mehter install`, Kurulum sekmesi başlatır) |
| `pipeline.i18n` | `pipeline.tools` mesajları aynı dilde (Türkçe ya da İngilizce; öteki arayüz dillerinde İngilizce) |
| `pipeline.web` | Kitap çevirisinin API'si (`App` sınıfı ve `/api/tr/...` için istek işleyicisi) |
| `pipeline.stages` | çeviri akışının hangi araçları kullandığı (Kurulum) |

Mehteran iş akışları için `Project` nesnesini okunan ayarlardan kendisi oluşturur ve `Project.load()` çağırmaz; çünkü o, `config.toml` dosyasını ve talimatları güncelleyebilir. Kitap çevirisi istisnadır: o çeviri uygulamasının kendisidir, projesini `./translate ui` gibi yükler (`pipeline.web.App(Project.load(...))`). Mehteran'ın kurulum komutu (`mehter install <araç>`) da iş akışlarıyla aynı nedenle projeyi yüklemeden `pipeline.runtime` modülünü doğrudan çağırır. Başlatıcının güncelleme adımı, `scripts/start.sh` dosyasındaki gibi çeviri uygulamasının kendisidir (`python -m pipeline update`).

## Bu dilimde olmayanlar

Bilerek dışarıda bırakılanlar: eklentiler ve eklenti kaydı, iş akışlarını yapay zekâyla oluşturma, arayüzden herhangi bir komut satırı aracını kaydetme, kabuk ya da Python kodu çalıştıran düğümler, zamanlama ve kullanıcılar arası paylaşım. PDF raporu: çeviri uygulaması PDF'i HTML sayfasını tarayıcıda yazdırarak yapar (bir PDF yazıcısı yoktur); bu yüzden Mehteran HTML (PDF olarak yazdırılabilir) ve Word verir.

## Geliştirme

- Testler: `python3 -m unittest discover tests` (Mehteran testleri `tests/test_mehteran_*.py` dosyalarıdır; sahte araç `tests/mehteran_fake_llm.py` ile çalışır, `MEHTERAN_HOME` değişkenini geçici bir klasöre ayarlar ve ağa bağlanmaz).
- Kod: `mehteran/` (yalnızca standart kitaplık). YAML: PyYAML 6.0.2, saf Python, `mehteran/_vendor/yaml/` içinde (MIT lisansı orada); yalnızca güvenli yükleyici ve güvenli yazıcı ile kullanılır.
- Yeni bir düğüm türü: `mehteran/nodes.py` dosyasına başlığı, açıklaması ve etiketli ayar alanlarıyla bir `NodeType` ekleyin (`register(...)`). Şema ve motor onu kendiliğinden tanır. `GET /api/node-types`, düzenleyicinin formları için her türü anlatır (başlık, açıklama, çıktılar, ayar alanları: tür, seçenekler, varsayılan, yardım metni; biçimi İngilizce kılavuzda).
- Arayüz: `mehteran/ui/` (saf JavaScript, derleme adımı yok): `app.js` (sekmeler, kitap çevirisi, kitaplık, çalıştırma penceresi, Çalıştırmalar, Kurulum), `editor.js` (görsel düzenleyici), `canvas.js` (tuval; çalıştırma izleme de kullanır). Kitap çevirisinin arayüzü çeviri uygulamasının `pipeline/ui/app.js` ve `style.css` dosyalarıdır; `/tr/app.js` ve `/tr/style.css` olarak sunulur (`mehteran/translation.py`). Her öğe DOM çağrıları ve metin düğümleriyle yapılır, hiçbir zaman HTML metninden değil.
