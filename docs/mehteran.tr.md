# Mehteran: kullanım kılavuzu

[English](mehteran.md) · [README'ye dön](../README.tr.md)

Mehteran, yapay zekâ iş akışlarını bu bilgisayarda çalıştırır. Bir iş akışı bir YAML dosyasıdır: düğümlerden oluşan bir çizge (belge oku, modele sor, metinleri birleştir, bir kişiye onaylat, rapor kaydet). Modeller, çeviri uygulamasının zaten kullandığı komut satırı araçlarıyla çağrılır (Claude Code, Codex, Antigravity CLI, Gemini CLI). Mehteran'ın kendi anahtarı ya da hesabı yoktur.

Kitap çevirisi için bağımsız `./translate ui` uygulamasını kullanın.

## Başlatma

| | macOS / Linux | Windows |
|---|---|---|
| Web arayüzü (çift tıklama) | `Open Mehteran.command` | `Open Mehteran.bat` |
| Web arayüzü | `./mehter ui` | `mehter ui` |
| Komut satırı | `./mehter <komut>` | `mehter <komut>` |
| npm ile (Node.js 18+): ilk çalıştırmada `~/Mehteran` klasörüne (ya da `MEHTERAN_DIR`) kurar | `npx mehteran [<komut>]` | `npx mehteran [<komut>]` |

Arayüz `http://127.0.0.1:8766/` adresinde açılır. Arayüz çalışırken kod değişirse (bir güncelleme) sayfa bunu bir uyarıyla söyler: sunucunun terminal penceresini kapatıp yeniden başlatın. Port doluyken `mehter ui` ikinci kez başlatılırsa, çalışan sunucu eskiyse aynı şeyi söyler. Terminal penceresi açık kaldıkça çalışır. Başlatıcı çeviri uygulamasınınki gibi çalışır (`scripts/start.sh`, `scripts/start.cmd`): Python 3.11 veya üstünü kullanır, bilgisayarda yoksa ayrı bir Python (uv) kurar ve `ui` öncesinde kod klasörünün git kopyasını günceller (`python -m pipeline update`, çeviri uygulamasının kendi güncelleme adımı).

Dil düğmesi (bir bayrak ve dilin adı) sağ üsttedir: 18 arayüz dili vardır, "Diller" bölümüne bakın. Komut satırında komuttan önce `--lang <kod>` (`tr`, `en`, `de`, `ar`...) yazın.

## Web arayüzü

Arayüz, çeviri uygulamasınınkiyle aynı tasarımdadır ve üç sekmesi vardır: İş akışları, Çalıştırmalar, Kurulum. Önceki sürümlerin adresleri (`#templates`, `#workflow/...`, `#runs/new/...`) karşılık gelen ekranı açmayı sürdürür. Araçlar hazır değilken ilk ekran Kurulum'dur, hazırsa en son kullanılan sekme; sol üstteki Mehteran adı da oraya götürür.

- Kitap çevirisini mevcut kitaplarınızla kullanmak için proje klasöründe `./translate ui` çalıştırın. Çeviriyi Mehteran içinde de açmak isterseniz veri klasöründeki `configurations/engine.toml` dosyasına `embed_book_translation = true` yazıp Mehteran’ı yeniden başlatın.
- **İş akışları**: kitaplık ve görsel düzenleyici. Kitaplığın iki görünümü vardır. "Akışlarım" (kendi iş akışınız, favoriniz ya da çalıştırmanız olduktan sonra ilk görünüm) kendi iş akışlarınızı, taslakları, favorileri, son çalıştırdıklarınızı gösterir. "Şablonlar" bir "Buradan başlayın" grubu (yaklaşık 20 genel şablon) ve sonra kategori başına bir grup gösterir. Her kart bir çalıştırmanın ne istediğini söyler, örneğin "1 belge · 2 model çağrısı" (bir seçim tek dalı seçiyorsa "en çok"); büyük-küçük harfe ve aksanlara (Türkçe olanlar da: "sozlesme", "Sözleşme"yi bulur) bakmayan bir arama ve kategori süzgeci vardır. Her kartta yıldız (favori), "Düzenle" ve "Aç" düğmeleri vardır. "Aç" ya da kartın kendisi, iş akışının sayfasını açar (`#workflows/<kaynak>/<kimlik>/<run|steps|runs>`; önceki sürümlerin `about` adresi `steps` bölümünü açar). Sayfa kitap çevirisininki gibidir: "← İş akışları", iş akışının simgesi ve adı ve üç bölüm. **Çalıştır**, sayfanın içindeki çalıştırma formudur (aşağıya bakın). **Çalıştırmalar** bu iş akışının çalıştırmalarını listeler. **Talimatlar** adımları sade sözlerle ve numaralı listeler; bir yapay zekâ adımı talimatını gösterir (üç satır, sonra "devamı"). Kendi iş akışınızda "Talimatı düzenle" talimatı yerinde değiştirip kaydeder. Altında: "Görsel düzenleyicide aç" ve katlı olarak çizim ile YAML (sizin iş akışlarınızda orada bir YAML düzenleyicisi vardır). Bölümlerin yanında favori yıldızı ve "⋯" bulunur: "Görsel düzenleyicide aç" (hazır bir şablon kaydedilmemiş kendi kopyanız olarak açılır), "Çoğalt" (ilk boş `<kimlik>-copy` adıyla kendi kopyanız; geldiği şablonu ve sürümü `based_on` içinde kaydeder; hazır şablonun sonraki bir güncellemesi onu hiç değiştirmez), "YAML olarak indir", "Paylaş" ve "Sil" (yalnızca sizin iş akışlarınız). "İçe aktar" bir iş akışı dosyası ekler; "Yeni iş akışı" boş bir tane başlatır.
- **Çalıştırmalar**: geçmişte bir kaydı arayıp seçtiğinizde ayrıntısı açılır. Çalıştırmalar bağlantısıyla listeye dönebilirsiniz. Ayrıntıda akışı canlı (düzenleyicinin tuvali, salt okunur; her kutu durumunun rengiyle), her düğüm için bir ilerleme satırı, sonuçlar (biçimli okuyun, başka bir çalıştırmayla karşılaştırın, düzenleyip dışa aktarın: aşağıda "Bir çalıştırmanın sonuçları") ve seçili düğümün paneli: çıktıları (okuyucuda okuyun ya da indirin), modele gönderilen istem, onayla ya da reddet, yeniden dene. Liste, iş akışı çalıştırmalarının altında kitap çevirisinin her kitabının son çalıştırmasını da gösterir (`GET /api/translation/runs`; her kitabın `work/run.json` dosyasından okunur); tıklayınca kitaplar açılır. Çalışan her şeyin listede bir durdurma düğmesi (■) vardır. "Devam ettir" başarısız, iptal edilmiş ya da yarıda kalmış bir çalıştırmayı sürdürür; "İptal et" durdurur; "Yeniden çalıştır" aynı iş akışının Çalıştır bölümünü açar.
- **Kurulum**: çeviri uygulamasının Kurulum sekmesindeki araç kartlarının aynısı, aynı kodla (`pipeline.tools`, `pipeline.runtime`): kurulu ve oturum durumu, "Eksikleri kur" (çeviri akışının ve şablonların kullandığı araçlar ve PDF okuyucu), her araç için kurma düğmesi, oturum açma yolları (hesap; Codex ve Gemini için API anahtarı da), "Dene", son kullanım sınırı ve bir başlangıç kutusu. Her kart aracı kimin kullandığını söyler (Çeviri, şablonlar). Araçlar çeviri uygulamasınınkiyle aynı `<kod klasörü>/.runtime` içine kurulur; ikisi tek kurulumu paylaşır. Her yapay zekâ aracı kartı ücretlendirmesini de gösterir (abonelik, ücretsiz hesap, yerel ya da API anahtarı (ücretli); aşağıdaki "İş akışlarının yapay zekâ araçları" bölümüne bakın). Kartların altındaki "İş akışlarının yapay zekâ araçları" paneli (açık gelir) bir araç tablosuyla başlar: durum, ücretlendirme, kalan kullanım, aynı anda yapılacak çağrı sayısı ve "API anahtarına izin ver (ücretli)". Tablonun altında `auto` için model sırası ve şu anki otomatik seçim vardır. "Video servisleri" sekmenin son bölümüdür. Her kart "Gerekli" (bir şablonun ya da çevirinin kullandığı araçlar ve PDF okuyucu) ya da "İsteğe bağlı" olarak işaretlidir. Altlarında "Yerel araçlar" (hepsi isteğe bağlı): Ollama kartı (durum; sürümü, kaynağı ve klasörü söyleyen bir onaydan sonra kurulum; İptal düğmesiyle kurulum günlüğü), modelleri (kurulu olanlar ve Sil; boyutu, belleği ve dilleriyle önerilenler, bu bilgisayar için büyük olana uyarı; adıyla başka bir model; ilerlemesi ve İptal düğmesiyle aynı anda bir indirme) Tesseract OCR kartı (onaydan sonra kurulum, eklenecek diller) ve Typst, Pandoc, konuşmayı metne çevirme (modelleriyle) ve qpdf kartları (sürümü, indirme boyutunu, kaynağı ve klasörü söyleyen bir onaydan sonra kurulum; İptal düğmesiyle kurulum günlüğü). Yerel modeller, model seçilen her yerde "yerel" olarak işaretlidir. Hazır bir araç yalnızca adını, tek bir durum satırını ve "Dene"yi gösterir; gerisi "Ayrıntılar" altındadır. "Arka planda çalıştır", "Yerel araçlar" ve "Video servisleri" başlıklarının altında katlı durur; "İş akışlarının yapay zekâ araçları" açık gelir. Mehteran çalışırken güncellendiyse bir uyarı bunu söyler; uyarıdaki "Yeniden başlat" sunucuyu yeni kodla yeniden başlatır ve sayfayı yeniler (bir çalıştırma ya da taslak sürerken reddedilir; bu düğmeden önce başlatılmış bir sunucu bir kez elle yeniden başlatılır).

Bir çalıştırma, iş akışı sayfasının Çalıştır bölümünde başlar (bir karttaki "Aç", düzenleyicideki "Çalıştır", bir çalıştırmadaki "Yeniden çalıştır": form o çalıştırmanın değerleriyle açılır, dosyalar hariç). Bölüm tek sütundur: "N adım · Talimatları gör", açıklama, girdiler (dosya girdisi bir yükleme alır), sonra katlı "Seçenekler": model girdileri, "Tüm adımlar için model" ve "Yalnızca bu bilgisayardaki modeller" (modeller kendiliğinden seçilir; açılınca bir model girdisi ayarlı araçları model ve düşünme düzeyi listeleriyle sunar), "Sonuçları şu klasöre de kaydet" ve zamanlama (dosya isteyen bir iş akışında gösterilmez). En sonda: "Çalıştırmayı başlat" ve çalıştırmanın neyi çağıracağını söyleyen bir satır ("Çağrı sayısı: 4 · Claude Code"); tahminin tamamı "Ayrıntılar" altındadır. "Çalıştırmayı başlat" çalıştırmayı Çalıştırmalar sekmesinde açar.

**Çalıştır bölümündeki tahmin.** Çalıştır bölümü, düğmelerin üstünde, çalıştırmanın model çağrılarını başlamadan önce gösterir (`POST /api/templates/<source>/<id>/estimate {values}`; `mehteran/estimate.py`). Sayım yalnızca iş akışından ve seçilen modellerden yapılır; hiçbir dosya okunmaz, hiçbir model çağrılmaz.

- "Çağrı sayısı": her adımın bir kez çalıştığı tek geçiş. Bir yapay zekâ adımı (`ai.cli`) 1 çağrıdır. Modele soran bir koşul (`operator: ai`) 1 çağrıdır. Bir döngü (`ai.map`) her parça için 1 çağrı yapar; parça sayısı metne bağlıdır, bu yüzden pencere "her parça için 1 (en çok N parça)" der; N, adımın `max_items` değeridir.
- "Yeniden denemelerle en çok": üst sınır. Her adım bütün denemelerini kullanır (`retries` + 1), her döngü en çok parça sayısına ulaşır ve her `ai` koşulu iki kez sorar (yanıt açık bir evet ya da hayır değilse yeniden sorar). Kullanım sınırı beklemesi bir çağrıyı deneme harcamadan yineler; üst sınır bunu içermez.
- Her model için bir satır: araç, model adı, çağrıları ve aracın şu anki kullanımı (kullanım ipucuyla aynı veri: aracın bildirdiği değer, yoksa Mehteran'ın son 5 saatteki kendi sayımı). Formda başka bir model seçtiğinizde satır değişir.
- "Koşula bağlı adım": böyle bir adım yalnızca kendi dalı seçilirse çalışır; çalıştırma daha az çağrı yapabilir.
- Araçlar bir çağrının kullanım sınırından ne kadar harcadığını bildirmez. Bu yüzden pencere çalıştırma başına yüzde göstermez.

Kitap çevirisinin kendi arayüzünde kendi tahmini vardır.

**İlk açılış karşılaması.** Bir şey çalıştırana kadar İş akışları sekmesi, kitaplığın üstünde "Ne yapmak istiyorsunuz?" panelini gösterir; her seçenek bir karttır: bir belgeyle çalış (`document-explainer` şablonunun Çalıştır bölümünü açar), yaz ya da yanıtla (kitaplığı yalnızca altı yazı iş akışıyla gösterir), veri inceleme, eğitim ve sınav, araştırma ve inceleme (her biri kitaplığı o kategoriye süzer). Her kart, seçeneğin gerektirdiği yapay zekâ aracını Kurulum sekmesinin verisindeki durumuyla (`GET /api/tools`) gösterir. Araç kurulu değilse kartta "Kur" düğmesi, oturum açılmamışsa "Oturum aç" düğmesi (Kurulum sekmesindeki hesapla oturum açma) bulunur. İkisi de Kurulum sekmesinin kendi adreslerini çağırır. API anahtarı ve ayrıntılar Kurulum sekmesinde kalır; kart oraya bağlantı verir. `GET /api/welcome` yanıtı: `{show, choices: [{id, action, category, templates, providers}]}`. Panel, ilk iş akışı çalıştırmasından ya da kitap çevirisinden sonra, ya da "Bir daha gösterme"den sonra (`PUT /api/welcome {"dismissed": true}`) bir daha gösterilmez. Sunucu bunu tarayıcıda değil, `<veri>/configurations/library.json` dosyasında tutar (`welcome_closed`: `used` ya da `dismissed`): tarayıcının deposu tek bir adrese ve porta aittir; bu seçim ise her tarayıcı ve port için geçerli olmalıdır.

### İş akışı kurma: başlangıçlar, "Anlat, oluşturayım", uyarılar, "Bu adımı dene"

- **Yeni iş akışı** yalnızca adı sorar. Kimlik addan üretilir ("Haftalık İş Raporu", `haftalik-is-raporu` olur; harfler kitaplık aramasındaki gibi sadeleştirilir; kimlik doluysa sonuna sayı eklenir). O pencerede "Gelişmiş ayarlar" altında başka bir kimlik yazabilirsiniz.
- **Boş tuval** üç başlangıç sunar: "Belge oku → Yapay zekâ → Kaydet", "Yazdığım metin → Yapay zekâ → Kaydet" ve "Anlat, oluşturayım". Bir başlangıç; adımları, bağlantılarını ve çalıştırma formunun girdilerini (dosya ya da metin, model, cevabın dili) tek adımda ekler; "Geri al" boş tuvali geri getirir. İlk adımdan önce hiçbir şey sorun olarak gösterilmez.
- **Bir adımın modeli** tek bir listedir: çalıştırma formunun model girdileri, otomatik seçimler ve araçlar. "Ayrıntılar" altında: aracın modeli ve düşünme seviyesi (her biri bir listeden), yazılı değer (listelerde olmayan bir ad için) ve "Bu modeli dene".
- **Palet** adım türlerini listeler; katlıyken (1680 pikselden dar pencerede var olan bir iş akışı) onu açan tek bir "+ Adım ekle" düğmesidir.
- **Adım ekleme** (palette tıklama): yeni adım, seçili adıma, seçili adım yoksa en son eklenen adıma bağlanır (o adım metin veriyorsa) ve onun sağına yerleşir. Tuvale sürüklenip bırakılan adım yalnızca seçili adıma bağlanır. Model alan bir adım, çalıştırma formunun model girdisini kullanır (yoksa oluşturulur). Bunların hepsi tek bir "Geri al" adımıdır.
- **Sorunlar ve uyarılar** adımı başlığıyla, alanı etiketiyle anar; tıklayınca o alan açılır. Sorun çalıştırmayı engeller. Uyarı engellemez: iş akışı denetimden geçer ama büyük olasılıkla istediğinizi yapmaz. Uyarılar şunlardır: kendisine hiçbir şey bağlı olmayan ve talimatı çalıştırma formundaki bir alanı kullanmayan adım; sonucu kullanılmayan adım; kaydetme adımı da sonucu da olmayan iş akışı. Çalıştır bölümü de uyarıları gösterir. Hazır şablonların hiçbirinde uyarı yoktur (`tests/test_mehteran_drafting.py`).
- **İki dilli metinler**: ad, açıklama ve etiketler için arayüz dilinde tek alan vardır. Öteki dilin metni (Türkçe ya da İngilizce) "Gelişmiş ayarlar" altındadır; oraya bir şey yazana kadar aynı metin kullanılır.
- **Kütüphanede "Anlat, oluşturayım"**: İş akışları sekmesinin en üstündeki kutu. Ne yapmak istediğinizi yazın (ya da kısa örneklerden birine tıklayın) ve "İş akışını kur"u seçin. Model, kurulu araçlarınızın otomatik seçimidir; kutu adını yazar. İş, kutunun içinde "Durdur" düğmeli tek bir satır olarak görünür (günlük "Ayrıntılar" altında). Model iş akışını, her yapay zekâ adımının talimatıyla birlikte yazar (çağrılar aşağıdakiyle aynıdır). Denetimden geçen taslak hemen iş akışlarınıza kaydedilir ve sayfası Çalıştır bölümünde **"Şunu kurdum"** kartıyla açılır: adımlar ve talimatları ("Talimatı düzenle" birini yerinde değiştirir), "Değiştir: …" (tek cümle, örneğin "daha kısa yazsın": model iş akışını mevcut dosyasından ve bu cümleden yeniden yazar; denetimden geçen sonuç onun yerini alır, geçmezse iş akışı olduğu gibi kalır), "Tamam, böyle kalsın" (kartı kapatır) ve "Sil". Siz başlatana kadar hiçbir şey çalışmaz. Denetimden geçmeyen taslak, sorunlarıyla birlikte düzenleyicide açılır.
- **Boş tuvalde "Anlat, oluşturayım"**: iş akışının ne yapacağını yazın, modeli seçin; o model ilk taslağı yazar. Bu tek bir model çağrısıdır; cevap denetimden geçmezse sorun listesiyle bir düzeltme çağrısı daha yapılır. Taslak düzenleyicide kaydedilmemiş bir iş akışı olarak ve şu notla açılır: "<model> hazırladı. Her adımın talimatını kontrol edin, sonra çalıştırın." Kendiliğinden kaydedilmez ve çalıştırılmaz. Yine de denetimden geçmeyen taslak, sorunlarıyla birlikte YAML sekmesinde açılır. Taslak her zaman çalıştırma formunun model girdisini kullanır, bir `language` girdisi içerir ve yalnızca talimat biçiminde yazılır. Yazdıklarınız, her adımın istemi gibi, seçtiğiniz modelin aracına gönderilir.
- **"Bu adımı dene"** (bir yapay zekâ adımının talimatının ya da modele soran bir koşulun sorusunun altında) yalnızca o adımı, kaydedilmemiş değişikliklerinizle çalıştırır. Önceki adımların metinleri, bu iş akışının o adımları bitmiş son çalıştırmasından (panel hangi çalıştırma olduğunu söyler) ya da yapıştırdığınız bir örnek metinden gelir. Panel modeli, aracının kullanımını ve ardından cevabı gösterir. Tek bir model çağrısıdır; kullanım sayfasına sayılır; hiçbir şey kaydedilmez ve kaynak çalıştırma değişmez.

Nasıl çalışır: `mehteran/drafting.py`. Taslak isteminde düğüm türlerinin kayıt defterinden üretilen özeti (`nodes.REGISTRY`; `GET /api/node-types` ile aynı veri), kurallar, iki örnek dosya ve veri etiketleri arasında sizin anlatımınız bulunur. İki özellik de sunucunun işleridir (`POST /api/editor/draft`, `POST /api/editor/try`; durum ve canlı günlük `POST /api/editor/jobs/<id>`, durdurma `POST /api/editor/jobs/<id>/cancel`); model çağrısı, bir çalıştırmanın adımı gibi kendi sürecinde yapılır, bu yüzden "Durdur" aracı da sonlandırır. Uyarıları `schema.warnings()` üretir.

### Kitap çevirisi

Kitap çevirisi, çeviri uygulamasının kendi arayüzüdür ve Mehteran'ın sayfasının içindedir: `pipeline/ui/app.js` (`/tr/app.js` olarak sunulur; aynı dosya, kopya değil) Kitaplar, çeviri akışı ve talimatlar bölümlerini Akışlar sekmesinde çizer (`TranslationUI.mount`); Mehteran'ın dilini, oturum anahtarını ve mesaj satırını kullanır. Kurulum bağlantıları Mehteran'ın Kurulum sekmesini açar.

İstekleri Mehteran'ın kendi sunucusundaki `/api/tr/...` adreslerine gider (`mehteran/translation.py`). `embed_book_translation = true` ayarı açıksa Mehteran, açılışta çeviri projesini bir kez, `./translate ui` gibi yükler (`pipeline.web.App(Project.load(...))`); ikinci bir sunucu açmaz. `/api/tr/<yol>` isteğini çeviri uygulamasının kendi istek işleyicisi (`pipeline.web.make_handler`) `/api/<yol>` olarak yanıtlar: aynı yollar, denetimler, parça parça okunan yüklemeler (en çok 300 MB), indirmeler ve hata kodları. Önce Mehteran'ın adres ve oturum anahtarı denetimleri yapılır; çeviri uygulaması Mehteran'ın oturum anahtarını kullanır. Proje yüklenemezse kitap çevirisi görünümü ve terminal nedenini söyler; Mehteran'ın geri kalanı çalışır. `./translate ui` (port 8765) aynı anda çalışabilir: bir kitabın çalıştırması, programlar arasında kitap başına kilitlenir.

Çeviri akışının çizimi ("Çeviri akışı"; Mehteran'da ve `./translate ui` içinde) yakınlaştırılabilir: −, + ve yakınlık düzeyi (tıklayınca %100), "Sığdır", Ctrl/⌘ + tekerlek ya da dokunmatik yüzeyde iki parmak, boş yeri sürükleyerek kaydırma. Seçilen yakınlık tarayıcıda saklanır ve çizim her yenilendiğinde geri konur; seçilmemişse çizim tuvale sığar, en az %85 büyüklükte. "Tam ekran" çizime ve seçili adımın paneline bütün pencereyi verir (Esc ile çıkılır; orada yeni adımlar adımlar arasındaki "+" ile eklenir). Adımlar daha büyük çizilir: belirgin numara, model adlarının tamamı, belirgin seçili adım; teslimden önceki "+ Adım ekle", "+" düğmesinin ne yaptığını söyler. Geniş pencerede seçili adımın paneli çizimin yanında, dar pencerede altındadır. Adım seçme, model değiştirme, sürükleme, adım ekleme, silme, sıralama ve kaydetme eskisi gibi çalışır.

`mehter ui` çalışırken çeviri uygulamasının kodu (`pipeline/*.py`, `pipeline/ui/*`) değişirse sayfa, Mehteran'ın kendi kodundaki gibi "sunucuyu yeniden başlatın" uyarısını gösterir.

### Bir çalıştırmanın sonuçları: okuma, karşılaştırma, düzenleme, dışa aktarma

- **Okuma**: çalıştırma bitince ilk metin sonucu sonuçlar kutusunda biçimli olarak ve "Tamamını aç" (okuyucu) düğmesiyle gösterilir; üstünde iş akışının kaydettiği her dosya için bir indirme vardır ("↓ Word", "↓ Markdown", …). Diğer Markdown sonuçlarının her biri için bir düğme vardır (adı okuyucuyu açar, "↓" indirir); bir adımın çıktıları da aynı okuyucuda açılır. `.md` sonucu biçimli gösterilir: başlıklar, paragraflar, kalın, italik, üstü çizili, madde ve numaralı listeler, alıntılar, kod, GFM tabloları, bağlantılar ve yatay çizgiler. "Biçimli / Düz metin" görünümü değiştirir; tarayıcı seçimi hatırlar. Paragraf içindeki satır sonu, dışa aktarılan belgelerdeki gibi korunur. Her blok kendi yönünü bulur (`dir="auto"`): arayüz dili ne olursa olsun Arapça bir paragraf sağdan sola, İngilizce bir paragraf soldan sağa okunur; liste, alıntı ve tablo, metnindeki ilk harfin yönünü alır. Bağlantı yalnızca `http` ya da `https` adresini yeni sekmede açar (`rel="noopener noreferrer"`); başka bir adresin yalnızca metni kalır. Sonuçtaki ham HTML metin olarak kalır. Gösterici `mehteran/ui/markdown.js` dosyasıdır: sayfayı yalnızca DOM çağrıları ve metin düğümleriyle kurar (HTML dizesi yok).
- **Karşılaştırma** (bitmiş bir çalıştırma, sonuçlar kutusunda "⇄ Karşılaştır"): çalıştırmanın sonucu, aynı iş akışının bitmiş başka bir çalıştırmasının aynı sonucunun (aynı çıktı kimliği) yanında gösterilir (aynı şablon; şablonsuz bir çalıştırmada aynı iş akışı kimliği). Öteki çalıştırmayı, birden çok sonuç varsa sonucu seçin. Farklı paragraflar vurgulanır ("Farklı paragrafları vurgula"; biçimli görünümde). Dar pencerede iki sonuç alt alta durur.
- **Düzenleme** (okuyucuda "✎ Düzenle"): solda metin, sağda biçimli önizlemesi (dar pencerede yalnızca metin). "Kaydet" düzenlenmiş sürümü çalıştırmanın yanına `<çalıştırma>/edited/<düğüm>.<ad>.md` olarak yazar; özgün çıktı hiç değişmez. Okuyucu bundan sonra "Özgün" ve "Düzenlenmiş" sürümleri (önce düzenlenmişi) ve son düzenleme saatini gösterir. Kaydedilmemiş değişiklikler Esc ya da "Kapat" ile sorulmadan kaybolmaz. Yalnızca bir adımın Markdown çıktıları (`nodes/<düğüm>/<ad>.md`) düzenlenebilir, en çok 1 MB.
- **Dışa aktarma** (düzenlenmiş bir sürüm, "Düzenlenmişi dışa aktar"): Markdown, Word, HTML, PDF ya da EPUB; dışa aktarma adımının kendi koduyla yapılır (`nodes.export_document`, `document.export` düğümünün kodu): Word Mehteran'ın dönüştürücüsüyle (Pandoc kuruluysa ve metinde formül varsa Pandoc ile), PDF Typst ile, EPUB Pandoc ile. Başlık iş akışının adıdır; dil, çalıştırmanın ilk `language` girdisidir (yoksa İngilizce). Dosya `<çalıştırma>/edited/<düğüm>.<ad>.<biçim>` olarak kaydedilir ve indirilir. Aracı kurulu olmayan bir biçim, neyin kurulacağını söyler ("PDF için Typst gerekli. Kurulum sekmesinden Typst'i kurun.").

API (her çalıştırma yolu gibi oturum anahtarıyla; `<çıktı>`, özgün çıktının çalıştırma klasöründeki yoludur, örneğin `nodes/report/text.md`):

- `GET /api/runs/<çalıştırma>/edits/<çıktı>` → `{path, exists, text, modified, limit}`.
- `PUT /api/runs/<çalıştırma>/edits/<çıktı>` `{text}` → `{path, exists, size, modified}`. UTF-8 olarak 1 MB'tan büyük metin: 413.
- `POST /api/runs/<çalıştırma>/edits/<çıktı>` `{format}` → `{path, size}`. Bilinmeyen biçim: 400; henüz kaydedilmemiş: 404; eksik araç: neyin kurulacağını söyleyen 400.
- Bir adımın Markdown çıktısı olmayan, çalıştırma klasörünün dışına çıkan bir yol ya da başka bir yere bağlantı olan bir `edited` klasörü: 404. Düzenlenmiş dosyalar çalıştırmanın dosyalarıdır: "Tüm dosyalar" listesinde görünür, ötekiler gibi indirilir.

### Çalıştırma geçmişi, toplu çalıştırma, klasöre kaydetme, paylaşma

- **Liste** (Çalıştırmalar sekmesi): bir arama alanı (iş akışının adında, çalıştırmanın adında ve notunda, ana girdisinde, kimliğinde ve durumunda arar; büyük/küçük harf ve aksanlar yok sayılır) ve her iş akışı için bir grup; grubun başlığına tıklayınca grup katlanır (tarayıcı bunu hatırlar). Kitap çevirilerinin kendi grubu vardır. Her satır çalıştırmanın ana girdisini gösterir: ilk dosyasının adını, yoksa ilk metin ya da adres girdisinin ilk 40 karakterini. Ad verdiğiniz bir çalıştırma o adı gösterir.
- **Ad ve not** (çalıştırmanın sayfasında "✎ Adlandır"): bir ad (en çok 120 karakter) ve bir not (en çok 2000). Ad, listede ve sayfada iş akışının adının yerine geçer; not başlığın altında ve satırın ipucunda görünür. `PUT /api/runs/<çalıştırma>/label {label, note}`; boş metin onu kaldırır.
- **Sil** (bitmiş bir çalıştırmanın sayfasında "Sil"): onay penceresi çalıştırma klasörünün boyutunu söyler. Çalıştırmanın satırları ve `executions/<çalıştırma>` klasörü silinir; model çağrılarının kullanım kayıtları kalır. Sırada bekleyen, çalışan ya da onay bekleyen, ya da kilidini (`executions/<çalıştırma>/.lock`) başka bir sürecin tuttuğu bir çalıştırma silinmez: önce durdurun. Yalnızca veri klasörünün içindeki yollar silinir; çalıştırma klasöründeki bir bağlantı (link) izlenmez, yalnızca bağlantının kendisi silinir. `DELETE /api/runs/<çalıştırma>` (`{"dry_run": true}`: yalnızca `{size, deletable}`).
- **Eski çalıştırmaları sil…** (arama alanının altında): 30, 90 ya da 365 günden eski. Pencere önce kaç bitmiş çalıştırma ve kaç bayt olduğunu söyler; çalışanlar korunur. `POST /api/runs/cleanup {days, dry_run}`.
- **Bitmiş bir çalıştırmanın sayfası**: çizim, adımlar ve canlı günlük tek satıra katlanır ("4/4 adım · 1 dk · akışı göster"); yer sonuçlara kalır. Başarıyla bitmeyen bir çalıştırma açık kalır (adımları orada yeniden denenir).
- **Her dosya için ayrı çalıştır** (Çalıştır bölümünde, tek dosyalık bir girdinin altında): en çok 50 dosya seçin; her biri, öteki girdiler aynı kalarak sıraya alınmış bir çalıştırma olur. Liste onları ilerlemesiyle tek bir toplu çalıştırma satırı olarak gösterir ("2/5 bitti"); açınca çalıştırmalar görünür. Bir toplu çalıştırmanın en çok 2 çalıştırması aynı anda çalışır (sağlayıcı başına bir sınır henüz yok); ötekiler "sırada" bekler. Penceredeki tahmin, çağrıları dosya sayısıyla çarparak gösterir. `POST /api/runs`, `"batch": {"input": "<dosya girdisi>", "files": [<yükleme kimlikleri>]}` ile `{batch, ids, id}` döndürür. Bir toplu çalıştırmanın sıradaki çalıştırmaları sunucu yeniden başlayınca yeniden başlatılır.
- **Sonuçları şu klasöre de kaydet** (Çalıştır bölümünde, toplu çalıştırmada da): bir klasörün tam yolunu yazın. Sunucu denetler: var olan, yazılabilir bir klasörün mutlak yolu olmalı; bir sistem klasörü (`/`, `/etc`, `/usr`, `/System`, `/Library`, `~/Library`, `C:\Windows`, `Program Files`...), Mehteran'ın kendi klasörü ya da veri klasörü olmamalı. Bir klasör ilk kez kullanılırken pencere onay ister; sonra klasör bu iş akışı için hatırlanır (`<veri>/configurations/output_folders.json`). Sonuçlar yalnızca çalıştırma başarıyla bitince kopyalanır: iş akışının sonuçları (sonuç tanımlamamışsa adımlarının kaydettiği dosyalar). Hiçbir dosyanın üzerine yazılmaz: var olan bir ada " (2)", " (3)"... eklenir. Toplu çalıştırmanın bir çalıştırması dosyasının adını başa koyar ("fatura-3 - rapor.docx"). Çalıştırmanın sayfası dosyaların nereye gittiğini ya da neden kaydedilemediğini söyler. `GET /api/output-folders/<kaynak>/<kimlik>`, `POST /api/output-folders/check {path}` → `{path, problem, confirmed}`; `POST /api/runs`, `output_dir` ve `output_confirmed` alır.
- **Paylaş** (bir iş akışının sayfasında "⋯", "Paylaş"): `<kimlik>.mehteran.yaml` dosyasını indirir: iş akışı dosyası, yazdığınız isteğe bağlı bir adla `author` ve hazır bir şablonsa `based_on: builtin:<kimlik>@<sürüm>`. `GET /api/templates/<kaynak>/<kimlik>/share?author=<ad>`.
- **Önizlemeyle içe aktarma**: "İçe aktar" (YAML'ı yapıştırın ya da bir dosya seçin) ya da kütüphaneye bırakılan bir `.yaml` dosyası önce bir önizleme açar: açıklama, yazar, çizim, girdiler, iş akışının burada nelere ihtiyaç duyduğu (her model, aracı ve aracın kurulu ve oturumu açık olup olmadığı; Typst ya da Tesseract gibi yerel araçlar; web sayfası okuyup okumadığı), modellere göndereceği bütün talimatlar ve sorunları. "Akışlarıma ekle" onu içe aktarır; kimliği kullanılıyorsa yeni bir kimlik ister. Denetim, her içe aktarmada olduğu gibi kimlik bilgilerini reddeder. `POST /api/templates/preview {yaml}`, `POST /api/templates/import {yaml, id}`.
- **Kullanım kılavuzu** (alt bilgideki "Kılavuz") bir Markdown sonucu gibi biçimli gösterilir.

## Diller

Bütün diller tek bir listededir: `mehteran/languages.json` (dil kaydı). Bir kayıtta dilin kodu, kendi adı, İngilizce adı, bayrağının ülke kodu ve yazı yönü vardır: `{"code": "ar", "native": "العربية", "english": "Arabic", "flag": "sa", "dir": "rtl", "ui": true}`. Mehteran sayfası, kitap çevirisinin arayüzü ve iş akışları bu listeyi kullanır (`mehteran/languages.py`, `GET /api/languages`). Çeviri uygulamasının varsayılan listesindeki (`config.default.toml`, `[languages]`) her dil bu listede vardır; bir test bunu denetler.

- **Arayüz dilleri** (`"ui": true`): Türkçe, English, العربية, Deutsch, Français, Español, Português, Italiano, Русский, فارسی, اردو, Bahasa Indonesia, Bahasa Melayu, Azərbaycanca, Bosanski, Shqip, 简体中文, 日本語. Sağ üstteki dil düğmesiyle seçilir: bayraklı bir liste ve bir arama alanı açılır (dilin adını herhangi bir dilde ya da kodunu yazın). Klavye çalışır: Enter, Boşluk ya da ↓ listeyi açar, ↑ ↓ gezdirir, Enter seçer, Esc kapatır. Seçim tarayıcıda saklanır. Arapça, Farsça ve Urduca sayfayı sağdan sola çevirir (`<html dir="rtl">`); iş akışı çizimi, kod ve günlükler soldan sağa kalır.
- **Tam ve kısmi diller**: Türkçe ve İngilizcede her metin vardır. Başka bir dilde metinlerin yalnızca bir bölümü olabilir; o dilde olmayan metin İngilizce gösterilir (sayfada da sunucu mesajlarında da). Çeviri uygulamasının kendi sunucu mesajları (`pipeline/i18n.py`) Türkçe ya da İngilizcedir: başka bir arayüz dili onları İngilizce alır.
- **Bayraklar**: bayrak bir ülkenindir, dil değildir: bayrak yalnızca satırı bulmaya yardım eder, yanında her zaman dilin kendi adı yazar. Bayraklar bu programın SVG dosyalarıdır (`mehteran/ui/flags/<ülke>.svg`, flag-icons 7.2.3, MIT; lisans o klasördedir), çünkü emoji bayraklar Windows'ta görünmez. İnternetten hiçbir şey yüklenmez.
- **Bir iş akışının çıktı dili**: `language` türündeki bir girdi, kayıttaki bütün dilleri aynı bayraklı listede sunar. Bütün seçenekleri dil kodu olan (ve kimliğinde `lang` geçen) bir `choice` girdisi de bayraklı liste olarak görünür, yalnızca kendi seçenekleriyle. Çalıştır bölümü, iş akışı arayüz dilini sunuyorsa o dille açılır; sunmuyorsa iş akışının varsayılanıyla.

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

**Ollama** modelleri bu bilgisayarda çalıştırır; hiçbir yere bir şey gönderilmez. Mehteran onu kendi `ollama` bağdaştırıcısıyla çağırır (çeviri uygulamasının `config.toml` dosyası değişmez). Bir adım onu `ollama/<model>` olarak kullanır, örneğin `ollama/gemma3:4b`; çalıştırma formu kurulu modelleri sunar. Mehteran, Ollama'nın `127.0.0.1` (port 11434) üzerindeki HTTP arayüzünü kendi sistem istemiyle ve diğer modellerdeki veri etiketleriyle, aynı ayrı süreçte çağırır; iptal ve süre sınırı aynı çalışır.

- Zaten çalışan bir Ollama olduğu gibi kullanılır. Yoksa sistemdeki `ollama` (PATH, macOS uygulaması, Windows kurulumu), o da yoksa Mehteran'ın kurduğu. Bir çalıştırma ya da indirme gerektirince Mehteran `ollama serve` komutunu 127.0.0.1 üzerinde başlatır; Mehteran kapanınca, yalnızca onu Mehteran başlattıysa durdurur (günlüğü: `<veri>/jobs/ollama-serve.log`).
- Kurulum: Ollama 0.40.16, GitHub sürümünün resmî arşivi (`ollama-darwin.tgz`, `ollama-linux-amd64.tar.zst` / `-arm64`, `ollama-windows-amd64.zip` / `-arm64`); `mehteran/ollama.py` içinde yazılı SHA-256 özetleriyle denetlenir (sürümün `sha256sum.txt` dosyasından; GitHub'ın kendi özetleriyle aynı). Hiçbir kurulum betiği çalıştırılmaz. Linux'ta arşivi açmak için Python 3.14 ya da `zstd` programı gerekir.
- Modeller: kurulu olanlar (ad, boyut, tarih), önerilenler listesi (diskteki boyut, gereken bellek, diller, not; etiketler Ollama kayıt deposunda denetlendi), ilerlemesi görünen ve iptal edilebilen indirme (bir seferde bir tane), silme. İndirmeden önce bellek azsa uyarır, disk yetmiyorsa (zorlanmadıkça) reddeder. Modeller Ollama'nın kendi klasöründe kalır (`~/.ollama/models` ya da `OLLAMA_MODELS`).
- Ayarlar: `<veri>/configurations/providers.toml` dosyasında `[providers.ollama]` altında `model` (varsayılan model) ve `options` (`num_ctx`, `temperature`, `top_p`, `seed`). Mehteran her çağrının bağlamını (`num_ctx`) kendisi boyutlandırır: istem artı cevap payı, en az 8192 jeton, en çok modelin üst sınırı (`/api/show`) ve belleğin izin verdiği değer (GB başına 1024 jeton, 4096 ile 131072 arası). `options` içindeki `num_ctx` önceliklidir. İstem yine de tüm bağlamı doldurursa (`prompt_eval_count`, `num_ctx` değerinin altında değilse), adım kesilmiş metinle cevap vermek yerine "belge bu model için çok uzun" hatasıyla durur: bir döngü adımı ya da daha büyük bağlamlı bir model kullanın.

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
./mehter install-local browser                    ajan adımlarının tarayıcısını kurar (Playwright MCP)
./mehter browser-signin [url]                     oturum açmak için Chrome'u ajan adımlarının profiliyle açar
```

Kurulum sekmesinin API'si:

| Yol | Cevap |
|---|---|
| `GET /api/local-tools` | `{tools: [ollama, ocr, typst, pandoc, speech, qpdf], pull}` (aşağıda) |
| `POST /api/local-tools/(ollama\|ocr\|typst\|pandoc\|speech\|qpdf)/install` | kurulum işini başlatır; `{message}` |
| `POST /api/local-tools/ocr-languages/install` `{languages: [..]}` | dil verisi ekler |
| `POST /api/local-tools/speech-models/install` `{models: [..]}` | konuşma modeli ekler; bilinmeyen bir ad için 400 |
| `POST /api/local-tools/(ollama\|ocr\|ocr-languages\|typst\|pandoc\|speech\|speech-models\|qpdf)/cancel` | o işi durdurur; `{cancelled}` |
| `GET /api/ollama/models` | `{running, installed: [{name, size, modified}], recommended: [{name, size, ram, languages, notes: {tr, en}, installed}], memory, disk_free}` (kuruluysa Ollama'yı başlatır) |
| `POST /api/ollama/pull` `{name, force?}` | `{started, warnings}`; disk çok doluysa ya da bir indirme sürüyorsa `problems` ile 409 |
| `GET /api/ollama/pull` | `{name, status, completed, total, percent, done, error, cancelled, started}` |
| `POST /api/ollama/pull/cancel` | `{cancelled}` |
| `POST /api/ollama/delete` `{name}` | `{ok}` |

`ollama`: `{id, name, installed, source ("system" | "mehteran" | null), path, version, running, started_by_mehteran, url, pinned_version, size, install_dir, models_dir, disk_free, memory, job}`. `ocr`: `{id, name, installed, source, path, version, pinned_version, pdftoppm, size, languages, available_languages: [{code, size, installed}], job, languages_job}`. `typst`, `pandoc`, `speech`, `qpdf`: `{id, name, installed, source, path, version, pinned_version, size, download_size, install_dir, disk_free, job}`; `typst` ayrıca `arabic_font` ekler; `speech` ayrıca `ffmpeg` (yolu ya da null), `ffmpeg_source`, `ffmpeg_version`, `poppler_first`, `models`, `available_models: [{name, size, installed}]`, `models_job` ekler; `qpdf` ayrıca `poppler_first` ekler (true: önce micromamba ve Poppler gelir). Önerilen bir modelin `kind` alanı olabilir: `"vision"` ya da `"embedding"`. Bir `job` ya `null` ya da `/api/tools` içindeki gibi `{running, code, log}` olur. Boyutlar bayt cinsindendir.

## İş akışlarının yapay zekâ araçları (sağlayıcılar)

Mehteran yapay zekâ araçlarını kendi bağdaştırıcılarıyla çağırır; her araç için `mehteran/providers/` içinde bir modül vardır: `claude` (Claude Code), `codex` (Codex CLI; eski ad `chatgpt` de çalışır), `antigravity` (Antigravity CLI), `gemini` (Gemini CLI) ve `ollama` (yerel modeller). Her bağdaştırıcı aracın komutunu ve Mehteran'ın kendi güvenli bayraklarını, tarafsız sistem istemini, cevabın ve kullanım sınırının nasıl okunduğunu, metnin nereye gittiğini, ücretlendirme türünü, bağlam boyutunu ve varsayılan aynı anda çağrı sayısını bilir. Kitap çevirisi kendi komutlarını `config.toml` içinde tutar; onlar değişmez.

| Araç | Gösterilen ücretlendirme | Metnin gittiği yer | Mehteran'ın eklediği bayraklar |
|---|---|---|---|
| Claude Code | abonelik (`claude auth status` Mehteran'ın aktardığı bir `apiKeySource` gösterirse API anahtarı) | Anthropic | `-p --safe-mode --tools "" --no-session-persistence --strict-mcp-config --output-format stream-json --verbose --system-prompt …`; asla `--bare` (API anahtarı gerektirir) |
| Codex CLI | abonelik (`codex login status` öyle derse API anahtarı) | OpenAI | `exec --sandbox read-only --ephemeral --ignore-user-config --skip-git-repo-check --color never -o <dosya>` |
| Antigravity CLI | ücretsiz hesap | Google | `--input-format stream-json --output-format stream-json --disable-slash-commands` |
| Gemini CLI | API anahtarı (ücretli): kişisel Google hesapları ücretsiz CLI oturumunu kaybetti; ücretsiz Google yolu Antigravity CLI'dır | Google | `-p … -o json --skip-trust` |
| Ollama | yerel (`…:cloud` / `…-cloud` model: Ollama Cloud, yerel değil) | bu bilgisayar | 127.0.0.1 üzerindeki Ollama HTTP arayüzü |
| Yerel sunucu (`openai-local`) | yerel | bu bilgisayar | `stream: true` ile `POST <adres>/chat/completions` (LM Studio, llama.cpp'nin llama-server'ı, vLLM) |

**Yerel sunucu.** Kurulum → "Yerel sunucu (OpenAI uyumlu)": sunucunun adresi (yalnızca `http(s)://127.0.0.1|localhost|[::1]:<port>/…`), bir model (ya da sunucunun `GET <adres>/models` listesindeki ilki), "Kaydet" ve "Dene". Mehteran onu standart kitaplıkla (`urllib`), vekil sunucu kullanmadan ve yönlendirme izlemeden çağırır; böylece metin bu yoldan bilgisayardan çıkamaz. Cevap canlı günlüğe akar. Yerel sayılır (`auto:local`, gizlilik: yerel). Bir adım onu `openai-local/<model>` olarak kullanır; içinde `/` olan bir model adı yazılamaz. Ayarlar: `[providers.openai-local] url = "http://127.0.0.1:1234/v1"`, `model = "…"`.

Claude bayrakları `claude --help` (2.1.316) ile denetlendi. Codex bayrakları Codex CLI başvurusundan alındı (bunun yazıldığı bilgisayarda Codex kurulu değildi). Antigravity CLI'da `--sandbox` ve `--mode plan` var; Mehteran onları eklemez: düz bir cevabı değiştirmediklerini denetlemek gerçek bir model çağrısı ister, plan kipi de istenen metin yerine bir planla cevap verebilir. Her çağrı boş bir geçici klasörde çalışır ve hiçbir araç istemez.

**Ücretlendirme koruması.** İşçi sürecin ortamında `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, `CODEX_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, `GOOGLE_API_KEY` bulunmaz; böylece bir araç yanlışlıkla bir API hesabını ücretlendiremez. Bir araç için "API anahtarına izin ver (ücretli)" (Kurulum) o araca kendi değişkenlerini geri verir. Seçim her çalıştırmayla saklanır. Bir aracın kendisinin sakladığı anahtar (Codex'te API anahtarıyla oturum, `~/.gemini/.env`) bir ortam değişkeni değildir: Kurulum sekmesi o zaman "API anahtarı (ücretli)" gösterir.

**`auto`.** Model `auto`, `auto:fast`, `auto:strong` ya da `auto:local` olabilir (şablonların varsayılanı `auto`). Bir çalıştırma başlarken Mehteran kullanıcının model sırasını alır (Kurulum: "Model sırası", ↑ ↓ ve ✕ ile; sıra yoksa kurulu ve oturum açılmış araçlar Claude Code, Codex, Antigravity, Ollama sırasıyla) ve yalnızca kurulu, oturum açılmış ve API anahtarıyla ücretlendirmeyen araçları tutar. `auto` ilkini alır; `auto:fast` aracın hızlı modelini (Claude: `haiku`) ya da düşük düşünme düzeyini; `auto:strong` güçlü modelini (Claude: `opus`) ya da yüksek düzeyi; `auto:local` yalnızca bu bilgisayardaki bir modeli. Kullanım sınırı henüz kalkmamış bir sağlayıcı sona gider. Seçim ve öteki adaylar çalıştırmayla saklanır (`provider_cfg.auto`). Çalıştırma formu "Otomatik: <model> · <kullanım>" gösterir ve bunun yerine bir araç seçmenize izin verir; varsayılan aracı burada çalışamayan bir şablon `auto` ile açılır.

**Çalıştırmalar arası kullanım sınırları.** Her çağrıdan önce, son kullanım sınırı henüz kalkmamış bir sağlayıcı (tüm çalıştırmaların `calls` tablosu ve çeviri uygulamasının `.jobs/quota.json` dosyası) çağrı yapılmadan engelli sayılır. Bir `auto` adımı o zaman adaylarındaki sıradaki modele geçer; hepsi engelliyse en erken kalkan sınıra kadar bekler. Sabit modelli bir adım eskisi gibi bekler. Bir adım kendi sınırını bu yolla saymaz (onu kendisi bekler; devam ettirme yeniden dener).

**Aynı anda çağrılar.** Her aracın, bir Mehteran programının tüm çalıştırmaları boyunca aynı anda çağrı sınırı vardır (varsayılanlar: Claude Code ve Codex 2, Antigravity 1, Ollama 1; Kurulum: "Aynı anda"). Bu, çalıştırma başına 4 çağrı sınırına eklenir.

**Gizlilik: yerel.** `privacy: local` (en üst düzey anahtar) içeren bir iş akışı ya da "Yalnızca bu bilgisayardaki modeller" ile başlatılan bir çalıştırma yalnızca yerel modelleri kabul eder: `auto`, `auto:local` olur, başka her model çalıştırma başlamadan reddedilir. Çalıştırma formundaki tahmin her adımı metninin gittiği yerle listeler ("Gönderildiği yer: Anthropic", "Bu bilgisayarda kalır (Ollama)") ve gizlilik: yerel seçeneğinin reddedeceği adımları işaretler.

**Tüm adımlar için model.** Çalıştır bölümündeki "Tüm adımlar için model" seçeneği, iş akışı ve model alanları ne derse desin, iş akışının tüm model adımlarını tek bir araçla (ya da "Otomatik" ile: model sırası) çalıştırır; adımların yedek modelleri de onu kullanır ve iş akışının kendi model alanları gizlenir. Yapay zekâ araçlarından yalnızca birine sahip olan kişi içindir: Claude için yazılmış bir iş akışı yalnızca Codex ile çalışır. Tahmin seçilen modeli gösterir. Gizlilik: yerel yine geçerlidir. Bulunmayan bir aracı adlandıran çalıştırma bunu söyler ve bu seçeneği gösterir. API: `POST /api/runs` ve tahminde (`POST /api/templates/<kaynak>/<id>/estimate`) `every_step`; komut satırı: `mehter run <iş akışı> --every-step codex`.

**Ayar dosyası** `<veri>/configurations/providers.toml` (Kurulum sekmesi yazar; gizli bilgi yok):

```
order = ["claude", "codex/gpt-5.5@high", "ollama/qwen3:8b"]
[providers.claude]
api_key = false
concurrency = 2
[providers.ollama]
model = "gemma3:4b"
options = {num_ctx = 8192}
```

API: `GET /api/providers` → `{providers: [{name, label, vendor, local, adapter, installed, signed_in, billing, default_billing, api_key_allowed, key_dropped, problem, concurrency, in_use, blocked_until, models}], order, order_is_default, auto: {auto|auto:fast|auto:strong|auto:local: {name, vendor, local}|null}}`; `PUT /api/providers {order?: [model], providers?: {ad: {api_key?, concurrency?}}}`. `POST /api/runs` ve tahmin `privacy: "local"` alır.

## Kullanım, bir adımın modelini değiştirme, canlı günlük

**Kullanım** (`GET /api/usage`). Mehteran her model çağrısını sayar (`calls` tablosu: sağlayıcı, model, başlangıç, saniye, sonuç `ok` / `failed` / `quota` / `aborted`, bir sınırda ne zamana kadar). Sağlayıcı başına:

```
{generated, providers: [{provider, tool ("claude"|"codex"|"gemini"|"antigravity"|"ollama"|null), configured,
  calls, ok, failed, quota, aborted, seconds, last_call,
  windows: {today|5h|7d: {calls, ok, failed, quota, aborted, seconds}}, models: {<model>: {...aynı sayılar}},
  last_quota: {at, until, message}|null, resets_at (until, gelecekte olduğu sürece)|null,
  tool_reported: {...}|null, translation_quota: <çeviri uygulamasının .jobs/quota.json kaydı>|null,
  setup_quota: <Kurulum'daki son model denemesinin sınırı>|null}]}
```

`tool_reported` yalnızca bir aracın kendi yazdığıdır; `null` bilinmiyor demektir:

- Codex: oturum günlükleri (`~/.codex/sessions/**/rollout-*.jsonl`, `$CODEX_HOME`) kullanım sınırlarını tutar; en yeni kayıt: `{source: "codex-session-log", observed_at, plan, limit_reached, windows: [{name: "primary"|"secondary", used_percent, window_minutes, resets_at, expired}]}` (primary: 5 saatlik pencere, secondary: haftalık pencere; `expired`: pencere o zamandan beri sıfırlandı). Mehteran'ın kendi Codex çağrıları `--ephemeral` olduğu için oturum günlüğü yazmaz; değer son etkileşimli Codex kullanımından gelir. Kimlik bilgisi dosyası okunmaz.
- Claude Code: yazdırma kipinde `/usage` komutuna hesaptan, model çağrısı yapmadan cevap verir. Son cevap 5 dakikadan eskiyse Mehteran arka planda yeniden sorar (`GET /api/usage` bunu başlatır ve `refreshing: true` der). `POST /api/usage/probe/<sağlayıcı>` (yalnızca bir Claude sağlayıcısı) hemen sorar: `{source: "claude-usage-command", observed_at, windows: [{name: "five_hour"|"seven_day"|"seven_day_model", model (tek bir modelin haftalık penceresi), utilization (0–1), resets_at}]}`. Her iş akışı çağrısı da değeri stream-json çıktısındaki `rate_limit_event` olayından günceller (`source: "claude-rate-limit-event"`). `/usage` komutunu bilmeyen bir Claude Code'a, yalnızca bu istek geldiğinde, en küçük modelle tek kelimelik bir çağrı yapılır.
- Gemini CLI, Antigravity CLI, Ollama: sınır bildirmez (`null`).

**Bir adımın modelini değiştirme** (`POST /api/runs/<çalıştırma>/nodes/<düğüm>/switch` `{provider: "gemini/<model>"}` → `{ok}`): kullanım sınırı bekleyen, başarısız, iptal edilmiş ya da yarıda kalmış bir yapay zekâ adımı için. Sağlayıcı yapılandırılmış olmalıdır. Olay günlüğüne "Model değiştirildi: eski → yeni" yazılır (anahtar `event_switched`). Bekleyen bir adım beklemeyi hemen bırakır ve yeni modelle yeniden çalışır; diğerleri yeniden denenir. Bir döngü elindeki parçaları korur (bir parçanın cevabı modele göre değil, istemine göre saklanır). Değiştirmemek, eskisi gibi beklemek demektir. Çalıştırma yeni modeli saklar (çalıştırmanın `providers` alanı).

Bir adım bir yedek model adlandırabilir (yazılmadıkça kapalı): `retries` yanında `fallback_provider: gemini/gemini-2.5-pro` (ya da bir `provider` girdisi, `"{{inputs.backup}}"`). Adımın modeli kullanım sınırı bildirince adım beklemeden hemen ona geçer (olay anahtarı `event_switched_auto`); yedek de sınır bildirirse adım bekler. Yalnızca yapay zekâ adımları (ve model soran koşullar) bunu alır; denetim diğerlerini ve sağlayıcı adı olmayan adları reddeder.

**Canlı günlük** (`GET /api/runs/<çalıştırma>/log?node=<düğüm>&offset=<bayt>` → `{text, offset, size, done, status}`): her düğüm çalışırken `nodes/<düğüm>/log.txt` dosyasına yazar: denemeler, her model çağrısı (ve cevabı), 30 saniyede bir "hâlâ çalışıyor" satırı, kullanım sınırı beklemeleri, model değişiklikleri, döngü parçaları. `offset` 0'dan okuyun, sonra dönen `offset` değerinden devam edin; düğüm bittiğinde ve her şey okunduğunda `done` true olur. Cevap başına en çok 64 KB, günlük başına 2 MB; açık gizli anahtarlar (`sk-…`, `Bearer …`, Google ve GitHub anahtarları) maskelenir. Günlük, çalıştırmanın dilinde yazılır.

Neler akar: Ollama'nın cevabı model yazdıkça günlüğe akar. Komut satırı araçları (Claude Code, Codex, Gemini CLI, Antigravity) Mehteran'ın bağdaştırıcılarıyla (`mehteran/providers/base.py` `run`) çağrılır; `on_output` geri çağrısı aracın standart çıktısındaki her satırı geldiği anda verir, işçi süreç de onu günlüğe yazar (`mehteran/toolstream.py`). Çağrının döndürdüğü cevap onsuz olanla aynıdır. Kullanıcının `config.toml` dosyasına eklediği bir sağlayıcı `pipeline.providers.run` ile çalışır ve cevabını sonunda gösterir. Bir araç canlı olarak yalnızca çalışırken standart çıktıya yazdığını gösterir:

- Antigravity CLI (`--output-format stream-json`): JSON olayları metne çevrilir: yazıldıkça cevabın metni ve başarısız bir sonucun hata satırı.
- Claude Code (`--output-format stream-json --verbose`, Mehteran'ın bağdaştırıcısı): her mesaj geldikçe asistanın metni ve her araç kullanımı kısa bir satır olarak (`· tool: Read`); ham JSON asla gösterilmez. `rate_limit_event` bilgisi kullanım sayfası için saklanır.
- Codex (`codex exec ... -o <dosya>`): son mesajını sonunda standart çıktıya yazar; ilerlemesi standart hataya gider ve canlı gösterilmez. Cevap sonda görünür.
- Gemini CLI (`-o json`): sonunda tek bir JSON belgesi yazar; canlı bir şey gösterilmez, cevap sonda görünür.

Bu arada günlük, çağrıyı ve "hâlâ çalışıyor" satırlarını gösterir. Akan metin bütün satırlar hâlinde yazılır (uzun bir satır sondan bir önceki kelimesine kadar), böylece gizli anahtarlar bütün olarak maskelenir; bir döngünün parçaları etiketleriyle (`part 3: `) bütün satırlar yazar. Akan metin zaten cevapla bitiyorsa cevap ikinci kez yazılmaz.

**Etkinlik** (`GET /api/activity` → `{runs: [...], translation: [...], time}`), üst çubuktaki gösterge için yeterince ucuz: süren, sırada bekleyen ya da bekleyen her çalıştırma `{id, workflow_name, status, started, elapsed, done, total, waiting_quota, nodes: [{id, status, started, elapsed, attempts, waiting_reason, progress}]}` (yalnızca çalışan ya da bekleyen düğümler) ve çeviri uygulamasının şu anda çevirdiği her kitap `{book, state ("running"|"waiting_quota"), stage, started, elapsed, quota}` (kitabın `run.json` dosyası, yalnızca okunur).

**Arayüzde** (`mehteran/ui/live.js`):

- Kalan kullanım: arayüz her pencereden ne kadar kaldığını gösterir (yüzde 100 eksi aracın bildirdiği kullanılan pay); bir çubuk ve sıfırlanmaya kalan süreyle. Üç yerde görünür: her sekmede üst çubuktaki gösterge ("Kalan · Claude %27 · Codex %7": araç başına en az kalan pay; listesi her pencereyi gösterir ve "Yenile" düğmesi vardır), Kurulum'daki her hazır yapay zekâ aracı kartı ve "İş akışlarının yapay zekâ araçları" panelinin "Kalan kullanım" sütunu. Araçlar belirteç (token) sayısı değil, yüzde bildirir. Hiçbir şey bildirmeyen araç için bu söylenir; Mehteran o zaman kendi çağrı sayımını gösterir.
- Kurulum: her yapay zekâ aracı kartının "Ayrıntılar" bölümünde bir "Kullanım" kısmı vardır: Mehteran'ın kendi sayımları (bugün, son 5 saat, son 7 gün: çağrılar, hatalar, kullanım sınırları, süre), açılmasına kalan süreyle son kullanım sınırı ve kalan kullanım. Claude Code kartında "Kullanımı kontrol et" düğmesi vardır (`POST /api/usage/probe/<sağlayıcı>`).
- Çalıştırma formu ve bir adımın model seçimi aracın yanında kısa bir kullanım ipucu gösterir ("5 saat: %54"); sınıra yakınken uyarı rengindedir.
- Çalıştırma sayfası: genel ilerleme çubuğu, geçen süreler, her adımın denemeleri ve bekleme nedeni ve seçili adımın (yoksa şu an çalışan adımın) canlı günlüğü: eş aralıklı yazı, sona kendiliğinden kayar, yukarı kaydırınca durur ("Duraklatıldı · sona git"), "Kopyala". Kullanım sınırı bekleyen, başarısız, iptal edilmiş ya da yarıda kalmış bir adım "Bekle" (varsayılan) ve "Başka modelle devam et" seçeneklerini sunar (yapılandırılmış her model, kullanım ipucuyla); adımın paneli model değişikliklerini listeler.
- Düzenleyici: model alan bir adımın gelişmiş ayarlarında "Yedek model" (boşsa kapalı).
- Üst çubuk şu an çalışanları gösterir ("2 çalışıyor"; bir şey kullanım sınırı beklerken uyarı renginde). Tıklayınca çalıştırmalar ve çevrilen kitaplar listelenir; her biri bir bağlantıdır ve bir durdurma düğmesi (■) vardır. Bir şey çalışırken 4 saniyede bir, yoksa 20 saniyede bir sorar; pencere gizliyken daha seyrek sorar.
- Kitaplık: her karttaki ve iş akışı sayfasında bölümlerin yanındaki yıldız bir favoriyi işaretler (`<veri>/configurations/library.json` içinde saklanır; `PUT /api/templates/<kaynak>/<id>/favorite {on}`; listedeki `favorite` işareti). "Favoriler" kitap çevirisinin hemen altında gelir ve bir "★ Favoriler" süzgeci vardır. "Son kullanılanlar" son çalıştırmaların iş akışlarını listeler; her birinde iş akışının sayfasını açan bir "Aç" düğmesi vardır. Çalıştırma formu her iş akışının son değerlerini bu tarayıcıda hatırlar (modeller, seçimler, metinler; dosyalar ve anahtar ya da parola gibi adlandırılan hiçbir şey hatırlanmaz): "Geçen seferki gibi" bunları doldurur. "/" imleci arama kutusuna koyar.

## Komut satırı

Sosyal medya videosu akışını aşağıdaki komutla başlatın. Web arayüzü, CLI ve zamanlayıcı aynı iş akışı motorunu kullanır. CLI senaryo onayında çalıştırma kimliğini, ses onayında önizleme dosyasının yolunu ve tamamlandığında ZIP yolunu gösterir.

Kurulum → Video servisleri bölümünde OpenAI ve ElevenLabs API anahtarlarını kaydedin. Kayıtlı anahtarları değiştirmek için yeni değerleri girin veya Kayıtlı anahtarı kaldır düğmesini kullanın. Başlatma ortamındaki `OPENAI_API_KEY` ve `ELEVENLABS_API_KEY` değerleri, yerel kayıt yoksa kullanılır. Varsayılan senaryo modeli Claude Code ile Opus’tur. Türkçe telaffuzu iyileştirmek için ElevenLabs hesabınızda erişebildiğiniz Türkçe bir sesin kimliğini aynı ekranda girebilirsiniz. Ortam değişkeni olarak `MEHTERAN_VIDEO_VOICE_ID` de kullanılabilir.

```sh
./mehter run builtin:topic-video-series --input "topics=Zeytin ağacı nasıl büyür?" --input language=tr
./mehter approve RUN_ID review
./mehter approve RUN_ID listen
```


```
./mehter templates                               şablonları listeler
./mehter validate akisim.yaml                    bir iş akışı dosyasını denetler; sorunların hepsini listeler
./mehter run document-comparison \
    --input documents=eski.docx --input documents=yeni.docx \
    --input model=claude/opus@high --input language=tr
./mehter run document-comparison \
    --input mode=set --input documents=a.pdf --input documents=b.docx --input documents=c.md
./mehter runs                                    çalıştırma geçmişi
./mehter resume <çalıştırma> [--node <id>]       bir çalıştırmayı sürdürür ya da başarısız bir düğümü yeniden dener
./mehter cancel <çalıştırma>                     bir çalıştırmayı durdurur
./mehter approve <çalıştırma> <düğüm> [--comment ...]   bekleyen bir onay düğümünü onaylar (reject: reddeder)
./mehter schedules                               zamanlanmış çalıştırmalar
./mehter background on|off|status                Mehteran'ı oturum açılınca arka planda başlatır
```

`run`, bir şablon kimliği (`builtin:<id>`, `user:<id>` ya da yalnızca id) veya bir `.yaml` dosyasının yolunu alır. `multiple: true` olan bir girdi, her dosya için bir kez `--input <id>=<dosya>` alır. `--every-step <model>` tüm adımları tek bir modelle çalıştırır (`codex`, `claude/opus@high`, `auto`). Çalıştırma bitene kadar her düğümün durumunu gösterir. Ctrl+C çalıştırmayı iptal eder. Çıkış kodu: 0 bitti, 3 onay bekliyor, aksi hâlde 1.

## Hazır şablonlar

10 kategoride 77 hazır şablon. Her biri Şablonlar görünümünde anlatılır (ne yaptığı, girdileri, akışı). Addın yanındaki yıldız, "Buradan başlayın" grubundaki şablonları gösterir (`tier: core` alanı). Sınav şablonları (SAT, AP, LGS, YKS) `exams` kategorisindedir; `education` genel çalışma ve öğretim içindir.

Bazı eski şablonlar başkalarıyla birleştirildi. Eski kimlikler çalışmaya devam eder (çalıştırmalar, favoriler ve `mehter run` kabul eder): `multi-document-comparison` → `document-comparison`; `chapter-summaries` → `document-summary`; `multi-length-summary` → `document-summary`; `terms-plain-language` → `plain-language-rewrite`; `proofreading-change-list` → `writing-polish`; `abstract-title-improvement` → `writing-polish`; `sat-math-practice-set` → `exam-practice-set`; `sat-reading-writing-practice` → `exam-practice-set`; `lgs-yks-practice` → `exam-practice-set`; `ap-mcq-from-notes` → `ap-question-generator`; `ap-frq-generator` → `ap-question-generator`; `policy-gap-analysis` → `regulatory-compliance-checklist`; `client-follow-up-email` → `email-reply-draft`.

| Kategori | Şablonlar |
|---|---|
| **Araştırma** (`research`) | `academic-paper-review` (Akademik makale değerlendirmesi), `grant-proposal-review` (Proje önerisi değerlendirmesi), `literature-synthesis` (Literatür sentezi), `research-question-critique` (Araştırma sorusu ve hipotez eleştirisi), `reviewer-response-letter` (Hakemlere cevap mektubu), `thesis-chapter-feedback` (Tez bölümü geri bildirimi) |
| **Belgeler** (`documents`) | `ask-your-documents` (Belgelerinize soru sorun*), `document-comparison` (Belge karşılaştırma*), `document-consistency-check` (Belge içi tutarlılık denetimi), `document-explainer` (Belgeyi herkes için anlaşılır anlat*), `document-summary` (Belge özeti*), `meeting-minutes-actions` (Toplantı tutanağı ve aksiyonlar*), `pdf-to-slide-outline` (Uzun belgeden sunum taslağı*), `recording-to-notes` (Toplantı / ders kaydından not*), `requirements-review` (Gereksinim belgesi incelemesi) |
| **Eğitim** (`education`) | `answer-key-verification` (Cevap anahtarı doğrulama), `differentiated-worksheet` (Üç düzeyli çalışma kâğıdı), `essay-rubric-grader` (Essay / kompozisyon değerlendirme (rubrikle)), `exam-from-lecture-notes` (Ders notundan A/B sınav), `flashcards` (Ezber kartları (Anki)*), `lesson-plan` (Ders planı), `mistake-explainer` (Yanlış yapılan soruların açıklaması), `parent-letter` (Veli mektubu), `question-variants-from-references` (Referans sorulardan yeni soru varyantları), `report-card-comments` (Karne yorumları), `scenario-generator` (Senaryo, vaka ve problem üretici), `study-guide-questions` (Ders notu ve sınav soruları), `weekly-study-plan` (Haftalık çalışma planı) |
| **Hukuk** (`legal`) | `contract-risk-review` (Sözleşme risk incelemesi*), `nda-review` (Gizlilik sözleşmesi (NDA) kontrolü), `regulatory-compliance-checklist` (Mevzuata uyum kontrol listesi) |
| **İnternetten araştırma** (`web`) | `ai-news-bulletin` (Yapay zekâ haber bülteni), `economy-news-bulletin` (Ekonomi haber bülteni), `listing-search` (Ev ya da araba ilanı bul), `research-to-x-post` (Araştır ve X paylaşımı hazırla), `stay-search` (Konaklama bul (otel)) |
| **İş** (`business`) | `business-plan-critique` (İş planı ve sunum eleştirisi), `customer-feedback-insights` (Müşteri yorumlarından içgörü*), `expense-anomaly-review` (Fatura ve harcama tutarsızlık notları), `financial-period-comparison` (İki dönemin finansal karşılaştırması), `financial-report-analysis` (Finansal rapor analizi), `job-posting-writer` (İş ilanı yazıcı), `proposal-from-brief` (Müşteri brifinden teklif*), `receipts-to-expense-table` (Fiş ve faturalardan gider tablosu*), `request-triage` (Talep ve şikâyet önceliklendirme), `review-reply-drafts` (Müşteri yorumlarına yanıt), `rfp-compliance-matrix` (İhale şartnamesi uyum matrisi), `weekly-report-from-notes` (Notlardan haftalık rapor) |
| **Sınavlar** (`exams`) | `ap-frq-grader` (AP FRQ değerlendirme (çift puanlama)), `ap-question-generator` (AP soru üretici (çoktan seçmeli ve serbest cevaplı)), `exam-practice-set` (Sınav alıştırma seti (SAT, LGS, YKS)), `sat-math-solver` (SAT Matematik: soru çözümü ve çift kontrol), `sat-practice-scoring` (SAT deneme sonucu: puanlama ve çalışma planı) |
| **Veri** (`data`) | `data-analysis-plan` (Veri analizi planı ve yorum), `dataset-documentation-review` (Veri seti belgelendirme incelemesi), `spreadsheet-analysis` (Tablo (CSV / Excel) analizi*), `sql-query-writer` (Sorudan SQL sorgusu), `survey-response-themes` (Anket açık uçlu yanıt temaları) |
| **Yazı** (`writing`) | `cv-and-cover-letter` (Özgeçmiş ve ön yazı (ilana göre)*), `cv-job-fit` (Özgeçmiş ve iş ilanı uyumu), `document-translation-glossary` (Belge çevirisi (sözlük ve tutarlılık denetimiyle)), `email-reply-draft` (E-posta yanıt taslağı*), `official-letter-writer` (Dilekçe ve resmî mektup yazıcı*), `plain-language-rewrite` (Sade dille yazım*), `product-description-seo` (Ürün açıklaması ve SEO metni), `social-media-posts` (Makale ya da rapordan sosyal medya paylaşımları*), `style-guide-review` (Yazım kılavuzuna göre editoryal değerlendirme), `tone-audience-adaptation` (Ton ve okura uyarlama), `translation-quality-review` (Çeviri kalite değerlendirmesi), `writing-polish` (Metin düzeltme ve özet iyileştirme*) |
| **Yazılım** (`developers`) | `bug-report-triage` (Hata bildirimi sınıflandırma), `changelog-from-commits` (Commit'lerden değişiklik günlüğü), `code-review` (Kod incelemesi*), `log-or-stacktrace-explainer` (Günlük ve hata izi açıklayıcı), `pr-description` (Pull request açıklaması), `readme-from-code` (Koddan README), `test-cases-from-code` (Koddan test senaryoları) |

## Tarayıcı ajanı adımları

**Tarayıcı ajanı** adımı (`ai.agent`), bir modelin Google Chrome'da siteleri açmasını, okumasını ve bir onaydan sonra form doldurmasını sağlar. Araç alan tek adım türüdür; öteki model adımları yalnızca metin alır ve metin verir.

Kurulum, bir kez:

1. Node.js'i (nodejs.org) ve Google Chrome'u kurun.
2. Kurulum sekmesi → "Ajan adımları için tarayıcı" → Kur. Bu, Playwright MCP 0.0.84'ü (Microsoft) `mehteran/browser_mcp/package-lock.json` kilit dosyasından (tam sürümler ve sha512 sağlamaları) `npm ci --ignore-scripts` ile `<kod klasörü>/.runtime/browser-mcp` altına kurar. Tarayıcı indirilmez: sizin Chrome'unuzu kullanır. Komut satırı: `mehter install-local browser`.
3. Oturum gerektiren siteler için (örneğin X) "Oturum açmak için tarayıcıyı aç" düğmesini kullanın (komut satırı: `mehter browser-signin https://x.com/login`). Chrome, Mehteran'ın kendi profiliyle (`<veri>/browser/profile`) açılır. Oturum açın, sonra pencereyi kapatın: Chrome aynı profili aynı anda iki kez kullanamaz. Ajan adımları bu profili ve oturumlarını kullanır; kendi Chrome profiliniz hiç kullanılmaz.

Bir adım nasıl çalışır:

- Yalnızca Claude Code ile (Kurulum sekmesinde oturum açılmış). `auto` model Claude Code'u seçer; başka bir model ya da başka bir araçla "Tüm adımlar için model" seçeneği çalıştırmayı başlamadan reddeder. Codex ve öteki araçlar henüz ajan adımı çalıştıramaz.
- Claude Code `--restricted --strict-mcp-config --mcp-config <tarayıcı> --tools "" --permission-mode dontAsk --allowedTools <adımın araçları>` ile başlar: kabuk yok, dosya araçları yok, başka MCP sunucusu yok; listede olmayan her araç sorulmadan reddedilir. (`--safe-mode` değil: o tarayıcı sunucusunu da kapatır.)
- `mode: read` (varsayılan) bakan ve gezinen araçları alır: adrese git, geri, sayfayı oku (snapshot, find), tıkla, üzerine gel, sekmeler, bekle, ekran görüntüsü, kapat, iletişim kutuları. Yazamaz. İstem ayrıca oturum açmayı, paylaşmayı, beğenmeyi, takip etmeyi, satın almayı ve form göndermeyi yasaklar.
- `mode: act` ayrıca yazma, form doldurma, tuşa basma ve seçenek seçme araçlarını alır. Böyle bir adımı olan iş akışı ancak ondan önce bir `approval` adımı varsa geçerlidir.
- Hiçbir adım sayfada JavaScript çalıştıramaz (`browser_evaluate`, `browser_run_code_unsafe`), dosya yükleyemez ya da bırakamaz.
- `sites`: adımın açabileceği alan adları, her satıra bir tane (alt alan adları dahil). Playwright'ın kendi köken listesi bir güvenlik sınırı değildir; bu yüzden Mehteran adımın gittiği her adresi ve bir aracın sonunda kaldığı her sayfayı denetler; başka bir site adımı hemen durdurur ("Adım durduruldu"). Denetim aracın kendi çıktısından yapılır; kuralı bozan sayfa yüklenmeye başlamış olabilir.
- Her tarayıcı eylemi (`» browser_navigate https://…`) adımın canlı günlüğüne yazılır; istem modele sayfalardaki metnin talimat değil veri olduğunu söyler.
- `headless: true` pencere göstermeden çalışır; varsayılan olarak pencereyi görürsünüz.
- Adımın istemi ve tarayıcı ayarları çalıştırma klasöründe saklanır (`nodes/<id>/prompt.txt`, `browser-mcp.json`).

**X'te paylaş** (`share.x`): X'in paylaşım penceresini metin doldurulmuş olarak açan bir bağlantı verir (`https://x.com/intent/post?text=…`). Çalıştırma sayfası metni ve bir "X'te aç" düğmesini gösterir; okuyup "Gönder"e kendiniz basarsınız. Mehteran hiçbir zaman kendiliğinden paylaşım yapmaz. Paylaşımı tarayıcıyla otomatikleştirmiyoruz, çünkü bildiğimiz kadarıyla X'in otomasyon kuralları sitesinin betikle kullanılmasını yasaklar (kuralların güncel metnine karşı denetlenmedi).

`research-to-x-post` şablonu bunları birleştirir: yalnızca okuyan bir ajan konuyu listelediğiniz sitelerde araştırır, bir model paylaşımı yazar, ikinci bir model onu araştırma notlarına karşı denetler, siz onaylarsınız (bir yorum paylaşımı değiştirir) ve X metinle açılır.

İki şablon daha, siteleri aramak ve bulduklarını karşılaştırmak için yalnızca okuyan bir ajan kullanır. **`listing-search`** (Ev ya da araba ilanı bul): türü (ev ya da araba), satın alma ya da kiralamayı, yeri, istediğiniz özellikleri ve bütçeyi verirsiniz; ajan listelediğiniz ilan sitelerinde (varsayılan olarak sahibinden.com, hepsiemlak.com, emlakjet.com, arabam.com) sitenin kendi filtreleriyle arar, bir model karşılaştırma tablosunu yazar (istenen her özellik ✓, ✗ ya da ?, en uygunu önce, ilan bağlantılarıyla) ve ikinci bir model her ilanı ajanın notlarına karşı denetler. **`stay-search`** (Konaklama bul): yeri, giriş ve çıkış tarihlerini, kişileri, bütçeyi ve isteklerinizi verirsiniz; ajan listelediğiniz otel sitelerinde (varsayılan olarak booking.com, hotels.com, etstur.com, trivago.com.tr) bu tarihler ve kişiler için arar; karşılaştırma toplam ve gecelik fiyatı, puanı, kahvaltıyı ve iptal koşullarını verir. İkisi de tarayıcıyı pencere açmadan çalıştırır. İkisi de rezervasyon yapmaz, oturum açmaz, kimseyle iletişime geçmez; fiyatlar aramanın yapıldığı andakidir. Oturum açmayı isteyen, captcha gösteren ya da ajanı engelleyen bir site raporda adıyla yazılır; oraya kendiniz bakabilirsiniz. Tarayıcı ajanı olan bir iş akışı her şeyi bu bilgisayarda tutamaz: "Yalnızca bu bilgisayardaki modeller" kutusu kapalıdır ve nedenini yazar; "Tüm adımlar için model"de başka bir araç seçmek ajanı Claude Code'da bırakır.

## Zamanlanmış çalıştırmalar ve arka planda çalışma

**Bir çalıştırmayı zamanlamak.** Bir iş akışının çalıştırma penceresinde girdileri doldurun ve "Şimdi değil, zamanlayarak çalıştır"ı seçin. Sonra günleri ve bir saati (yerel saat) ya da "Birkaç saatte bir"i (1 ile 168 arası) seçip "Zamanlamayı kaydet"e basın. Girdiler, model seçimleri, "yalnızca bu bilgisayardaki modeller" ve "sonuçları bir klasöre de kaydet" zamanlamayla birlikte saklanır.

- Zamanlamalar Çalıştırmalar sekmesinde, "Zamanlanmış" grubundadır: kural, sonraki zaman ve son çalıştırmanın durumu. Her birinde Duraklat/Sürdür, "Şimdi çalıştır" ve Sil vardır. Bir zamanlamaya tıklamak son çalıştırmasını açar.
- Her çalıştırma iş akışını o anki hâliyle kullanır. Değiştirilen bir şablon sonraki çalıştırmadan itibaren geçerlidir. Bir çalıştırma başlayamazsa (örneğin silinmiş bir şablon ya da eksik bir girdi), zamanlama nedenini gösterir.
- Dosya isteyen bir iş akışı zamanlanamaz, çünkü zamanlama yalnızca metin değerlerini saklar.
- Mehteran kapalıyken geçen zamanlar, Mehteran yeniden açılınca tek bir çalıştırma başlatır; kaçan her zaman için ayrı çalıştırma başlamaz.
- Bir zamanlamanın son çalıştırması hâlâ sırada bekliyor ya da çalışıyorsa, o zaman atlanır. Onay bekleyen bir çalıştırma sonrakini engellemez.
- Onay adımları sizi bekler. Zamanlanmış bir çalıştırma onay beklediğinde, hazır olduğunda ya da tamamlanamadığında bir masaüstü bildirimi gelir (macOS: Bildirim Merkezi; Linux: `notify-send`; Windows: henüz bildirim yok).
- Zamanlamalar `<veri>/configurations/schedules.json` dosyasında saklanır. Komut satırı: `mehter schedules`.

**Arka planda çalıştırmak.** Çalıştırmalar yalnızca Mehteran açıkken başlar. Kurulum sekmesi → "Arka planda çalıştır" → Aç (komut satırı: `mehter background on`). Mehteran bundan sonra bilgisayarda oturum açtığınızda, pencere açmadan ve tarayıcıyı açmadan başlar. İstediğiniz zaman `http://127.0.0.1:8766/` adresinden ya da `./mehter ui` ile açabilirsiniz.

- macOS: bir LaunchAgent, `~/Library/LaunchAgents/com.mehteran.ui.plist`. Linux: bir systemd kullanıcı hizmeti, `~/.config/systemd/user/mehteran.service`. Windows: Başlangıç klasöründe bir betik (Windows'ta denenmedi).
- Hizmet, bu Mehteran'ın Python'uyla `python -m mehteran ui --no-browser` çalıştırır. Yapay zekâ araçlarını bulabilmesi için açıldığı andaki `PATH` değerini alır. Başka hiçbir değişken kopyalanmaz: API anahtarları hizmet dosyasına hiç girmez. Sonradan bir aracı yeni bir klasöre kurarsanız arka planı kapatıp yeniden açın.
- Mehteran bir terminalde zaten açıksa, arka plan sunucusu bekler ve siz onu kapattıktan sonra yaklaşık 30 saniye içinde devralır.
- Çıktısı `<veri>/logs/background.log` dosyasına yazılır.
- Kapat, arka plan sunucusunu durdurur ve hizmet dosyasını siler. Kullandığınız sayfayı o sunuyorsa sayfa çalışmaz hâle gelir; süren çalıştırmalar durur ve sonra sürdürülebilir.
- Kod güncellendikten sonra arka plan sunucusu yeniden başlayana kadar eski kodu kullanır (oturumu kapatıp açın ya da arka planı kapatıp yeniden açın).

## Veriler nerede

Mehteran verilerini kod klasörünün dışında tutar:

| Sistem | Klasör |
|---|---|
| macOS | `~/Library/Application Support/Mehteran` |
| Windows | `%LOCALAPPDATA%\Mehteran` |
| Linux | `$XDG_DATA_HOME/mehteran`, yoksa `~/.local/share/mehteran` |

`MEHTERAN_HOME` ortam değişkeni bu klasörün yerine geçer. Alt klasörler:

- `templates/`: sizin şablonlarınız (her biri bir `<id>.yaml`).
- `executions/<çalıştırma>/`: her çalıştırma için bir klasör: `workflow.yaml` (dondurulmuş kopya), `inputs/` (yüklenen dosyalar; birden çok dosya alan bir girdide her dosya `inputs/<id>/<n>/` içinde), `nodes/<düğüm>/` (her düğümün çıktıları, her model çağrısının istemi; bir döngü her parçanın istemini ve cevabını `nodes/<düğüm>/parts/` içinde tutar), `edited/` (sonuçların düzenlenmiş sürümleri ve dışa aktarımları; yalnızca kullanıcı bir sonucu düzenlerse).
- `databases/mehteran.sqlite3`: her çalıştırmanın ve düğümün durumu (SQLite, WAL kipi).
- `configurations/`: Kurulum sekmesinin sakladıkları: `providers.toml` (model sırası, aynı anda çağrı sayısı, "API anahtarı (ücretli)", Ollama modeli ve seçenekleri; gizli bilgi yok), `models.json` (araçlardan okunan model listeleri), `quota.json` (bir model denemesinin karşılaştığı son kullanım sınırı) ve `usage.json` (Claude Code'un sınırları hakkında son bildirdiği).
- `jobs/`: Kurulum sekmesinden başlatılan kurulumların günlükleri.
- `workflows/`: sonraki sürümler için ayrıldı; şimdilik boş.

İş akışları Mehteran'ın kendi bağdaştırıcılarını kullanır (`mehteran/providers/`, "İş akışlarının yapay zekâ araçları" bölümüne bakın). Çeviri uygulamasının `config.toml` dosyası yalnızca okunur: `[general]` süreleri ve sınırları, ve kullanıcının başka bir adla eklediği `[providers.*]` bölümleri. Oradaki `claude`, `chatgpt`, `antigravity` ve `gemini` bölümleri yalnızca kitap çevirisine aittir. Oturumları araçlar kendi klasörlerinde tutar (çeviri uygulamasındaki gibi). `MEHTERAN_CONFIG`, `[providers.*]` bölümleri olan başka bir TOML dosyasını gösterebilir; orada bir sağlayıcı aynı adlı bağdaştırıcıdan önceliklidir (testler sahte bir araç için kullanır).

## Bir çalıştırma nasıl işler

- Bir düğüm, kendisine bağlı bütün düğümler bitince başlar. Birbirine bağlı olmayan düğümler aynı anda çalışır (bir çalıştırmada en çok 4).
- Her düğümün bir tekrar deneme sayısı ve deneme başına bir süre sınırı vardır. Süre sınırı ya da iptal, model çağrısını başlattığı araçla birlikte durdurur.
- Model, istemi boş bir geçici klasörde stdin üzerinden, Mehteran'ın o araç için bağdaştırıcısıyla (`mehteran/providers/base.py`) ve bir hesabı ücretlendirecek API anahtarları olmadan alır. Kullanıcının `config.toml` dosyasına eklediği bir sağlayıcı çeviri uygulamasının çağrısıyla (`pipeline.providers.run`) çalışır. Mehteran her çağrıyı bir kez dener; tekrar denemeleri motor sayar.
- Kullanım sınırları: bir araç kullanım ya da hız sınırı bildirince (bağdaştırıcının kendi bildirimi, örneğin Claude Code'un `rate_limit_event` olayı, ya da `pipeline.providers.is_quota_message` işlevinin tanıdığı sınır mesajları) düğüm başarısız olmaz. Bir `auto` adımı önce sıradaki modele geçer; başka bir çalıştırmanın daha önce gördüğü bir sınır çağrı yapılmadan bilinir ("İş akışlarının yapay zekâ araçları" bölümüne bakın). "Kullanım sınırı bekleniyor" (`waiting_quota`) gösterir, olay günlüğü ne zamana kadar beklendiğini yazar ve sınır kalkınca yeniden dener: aracın söylediği zamanda, yoksa `config.toml` dosyasındaki `quota_wait_minutes` (`[general]`) sonra. Bekleme başarısız bir deneme sayılmaz. Bekleme toplamda `quota_max_hours` süresinden uzun sürecekse düğüm başarısız olur. İptal beklemeyi hemen bitirir.
- Bir çalıştırmada aynı anda en çok 4 model çağrısı çalışır; döngü parçalarınınkiler de buna dahildir.
- Koşullar: bir `condition` düğümü yalnızca seçtiği dalın çıkışını (`true` ya da `false`) verir. Öteki çıkışa bağlı düğümler ve yalnızca onlara bağlı olan her şey atlanır. Bir birleştirme düğümü (`text.merge`, `document.export`), bağlantılarından en az biri seçilen bir daldan geliyorsa çalışır; atlanan dalın çıktısı orada boş metindir. Diğer düğümler ancak bütün bağlantıları seçilmiş dallardan geliyorsa çalışır. Atlanan bir dal çalıştırmayı başarısız yapmaz; başarısız bir düğüm ise ardından gelen her şeyi yine atlar ve çalıştırma başarısız olur.
- Döngüler: bir `ai.map` düğümü bir metni parçalara böler ve modeli her parça için bir kez, paralel olarak çağırır. Her cevap isteminin bir özetiyle (hash) saklanır: yeniden deneme ya da sürdürme yalnızca cevabı olmayan parçaları sorar. Düğümün süre sınırı bütün düğüme değil, her model çağrısına uygulanır; tekrar denemeler düğüme uygulanır (biten parçalar denemeler arasında korunur).
- Çalıştırma; iş akışının dondurulmuş bir kopyasını, çözülmüş model adlarını (`claude/opus@high`) ve araç ayarlarını saklar. Sürdürme ve yeniden deneme bu kopyaları kullanır, güncel şablonu değil.
- Sürdürme: biten düğümler korunur; yalnızca diğerleri çalışır. Programı kapanmış (terminal kapatılmış, çökmüş) bir çalıştırma "yarıda kaldı" olarak görünür ve sürdürülebilir.
- Bir onay düğümü, bir kişi onaylayana ya da reddedene kadar kendi dalını durdurur. Bu sırada açık kalması gereken bir program yoktur; onay arayüzden ya da komut satırından, yeniden başlatmadan sonra da verilebilir.
- Bir çalıştırmayı aynı anda yalnızca bir program yürütür (çalıştırma klasöründe bir kilit dosyası).
- Uyanık tutma: ilk çalıştırmadan itibaren Mehteran sistemden uyumamasını ister (`pipeline.system.keep_awake`: macOS'ta `caffeinate`, Windows'ta yürütme durumu, Linux'ta `systemd-inhibit`). Bu, Mehteran kapanana kadar sürer; kullanım sınırı için bekleyen bir çalıştırma da bilgisayarı uyanık tutar.
- Açılışta sürdürme (isteğe bağlı): `<veri>/configurations/engine.toml` içinde `resume_interrupted = true` varsa `mehter ui`, önceki program kapanırken çalışan ya da kullanım sınırını bekleyen çalıştırmaları sürdürür (iptal edilmiş, başarısız ya da bitmiş olanları ve başka bir programın yürüttüğünü değil). Dondurulmuş ayarlarıyla devam ederler. Varsayılan olarak kapalıdır.
- Boş girdi: metni boş olan bir `document.export` adımı "kaydedilecek metin boş" diyerek başarısız olur ve dosya yazmaz. Veri alan (bağlantı, `{{nodes.*}}` başvurusu ya da dosya girdisi) ama hepsi boş olan bir `ai.cli` adımı, model çağrılmadan başarısız olur. Hiç verisi olmayan adım yalnızca bir yönergedir ("bir haiku yaz") ve yazıldığı gibi çalışır; düzenleyicinin `schema.warnings()` uyarıları bunu bildirir.
- Kullanım sınırını bildiren bir döngü parçası, henüz başlamamış parçaları durdurur; bekleme (ya da model değişimi) sonrası döngü yalnızca cevabı olmayan parçaları sorar. Parça başlıkları ("Bölüm 1") çıktının dilini izler: iş akışının `language` girdisi varsa o, yoksa çalıştırmanın dili.
- Başarısız bir adımın `error` alanı aracın tam metnidir; `error_summary` (`GET /api/runs/<run>`, düğüm başına) onun son anlamlı satırıdır (iz kaydı satırı değil). Çalıştırma ekranı özeti gösterir, tam metni "Ayrıntılar" altında tutar.
- Her dilde mesajlar: Mehteran kendi mesajlarını (olay günlüğü, düğüm ve çalıştırma hataları) mesaj anahtarı ve değerleriyle saklar ve okuyanın dilinde gösterir (arayüzün dil seçimi, komut satırının `--lang` değeri). `GET /api/runs/<çalıştırma>` içindeki bir olay `{time, node_id, kind, message, text, key, params}` biçimindedir: `message` ve `text` isteğin dilindeki aynı metindir; `key` ve `params` saklanan mesajdır (iç içe bir mesaj `{"$key": ..., "params": {...}}`), eski çalıştırmalarda ve bir aracın yazdığı metinde `null` olur ve metin saklandığı gibi gösterilir. Bir düğümün (ve çalıştırma listesinde bir çalıştırmanın) `error` alanı isteğin dilindedir; yanında aynı biçimde `error_key` ve `error_params` vardır. Veritabanı yeni sütunları kendisi ekler; eski satırlar metinlerini korur.

## İş akışı dosyası başvurusu (schema_version 1)

```yaml
schema_version: 1
id: my-review                 # küçük harf, rakam, "-" ve "_"; en çok 64
author: Ayşe Yılmaz           # isteğe bağlı, en çok 80 karakter: dosyayı paylaşan ("Paylaş"); based_on da öyle
name: {tr: İnceleme, en: Review}   # bir metin ya da {tr, en} eşlemesi (description ve etiketler için de aynı)
description: İş akışının ne yaptığı.
version: "1.0"
category: research
inputs:
  - {id: paper, type: file, label: {tr: Makale, en: Paper}, formats: [pdf, docx, epub, md, txt]}
  - {id: sources, type: file, multiple: true, required: false, formats: [pdf, md, csv, xlsx]}   # birden çok dosya
  - {id: language, type: language}   # çıktı dili: bayraklı listeden seçilen herhangi bir dil (aşağıya bakın)
  - {id: model, type: provider, default: auto}
  - {id: note, type: text, multiline: true, required: false, default: ""}
nodes:
  - id: extract
    type: document.extract
    config: {file: "{{inputs.paper}}"}
  - id: review
    type: ai.cli
    retries: 2                 # ek denemeler (0–10)
    timeout: 900               # deneme başına saniye
    config:
      provider: "{{inputs.model}}"   # ya da sabit bir ad: claude, claude/opus, claude/opus@high
      prompt: |
        Review this paper. Write in {{inputs.language}}.
        {{nodes.extract.text}}
  - id: save
    type: document.export
    config: {source: "{{nodes.review.text}}", title: Review, lang: "{{inputs.language}}", formats: [md, docx, html]}
connections:
  - {from: extract.text, to: review}
  - {from: review.text, to: save}
outputs:
  - {id: report, from: save.docx, label: Report}
layout:                        # isteğe bağlı: düzenleyicinin her düğümü çizdiği yer
  extract: {x: 0, y: 0}
  review: {x: 324, y: 0}
  save: {x: 648, y: 0}
```

Üst düzey alanlar: `schema_version: 1`, `id`, `name`, `description`, `version`, `category`, `tier` (isteğe bağlı; `core`: "Buradan başlayın" grubu), `based_on`, `author`, `inputs`, `nodes`, `connections`, `outputs`, `layout`.

`layout` alanını görsel düzenleyici yazar: her düğüm için kutusunun tuvaldeki konumu, piksel olarak. Yalnızca iş akışının düğüm kimlikleri, her biri tam olarak `x` ve `y` ile, −100000 ile 100000 arasında tam sayılar. Motor onu yok sayar. Yoksa düzenleyici kutuları akış sırasına göre kendiliğinden yerleştirir.

Girdi türleri: `file` (bir yükleme; `formats` türleri sınırlar: `pdf`, `docx`, `epub`, `md`, `txt`, `csv`, `tsv`, `xlsx`, resimler `png`, `jpg`, `jpeg`, `tif`, `tiff` (OCR ile okunur), `odt`, `rtf` (Pandoc ile okunur) ve ses ve video `mp3`, `wav`, `m4a`, `ogg`, `opus`, `flac`, `aac`, `mp4`, `webm`, `mov`, `mkv` (konuşma metne çevrilir); `multiple: true` 1–20 dosya alır, toplam en çok 500 MB), `text` (`multiline`), `choice` (`options`: metinler ya da `{value, label}`), `provider` (bir araç, isteğe bağlı model ve düşünme düzeyiyle), `language` (kayıttaki bir dilin kodu; "Çıktı dili" bölümüne bakın), `url` (`document.extract` adımının okuduğu bir web sayfası ya da haber akışı; aşağıya bakın; `multiple: true` her satıra bir tane olmak üzere en çok 30 adres alır, boş satırları ve `#` ile başlayan satırları atlar). `required: false` yazılmadıkça girdiler zorunludur.

Web sayfaları: `file` ayarı bir `url` girdisi olan (ya da `file` ayarı olmadan iş akışının tek dosya ya da adres girdisini okuyan) bir `document.extract` adımı o adresteki sayfayı okur. Yalnızca `http` ve `https`; adreste kullanıcı adı ya da parola olamaz. Önce sunucu adı çözülür: çözüldüğü her adres herkese açık olmalıdır. Bu bilgisayarın (`127.0.0.1`, `::1`), yerel ağın (`10.x`, `172.16–31.x`, `192.168.x`, `fc00::/7`), bağlantı-yerel (`169.254.x`, `fe80::`), çoklu yayın ve ayrılmış adresler reddedilir; bağlantı denetlenen adrese kurulur. En çok 3 yönlendirme, her biri aynı biçimde denetlenir; vekil sunucu (proxy) kullanılmaz; 10 saniye; en çok 5 MB. HTML sayfası okunur metne çevrilir (başlık, ara başlıklar, paragraflar, listeler; betik, stil, gezinme ve formlar çıkarılır); düz metin olduğu gibi kalır; PDF yüklenmiş bir PDF gibi okunur. JavaScript çalıştırılmaz: metnini tarayıcıda kuran bir sayfa az metin verir ya da hiç vermez. Kod: `mehteran/urlfetch.py`.

Haber akışları: bir RSS (0.9x, 1.0, 2.0) ya da Atom akışı (türünden ya da sunucu onu HTML veya metin diye bildirdiğinde başlangıcından tanınır) öğelerinin listesine çevrilir; en yenisi önce, en çok 50 öğe: akışın başlığı, sonra her öğenin başlığı, UTC olarak yayın tarihi, bağlantısı ve en çok 600 karakterlik özeti. Adımın `max_age_days` ayarı (`{{inputs.days}}` gibi bir yer tutucu olabilir) yalnızca son günlerin öğelerini tutar; tarihi olmayan öğe tutulur. Öğelerden önceki bir satır kaç öğenin hangi dönem için tutulduğunu söyler. DTD (`<!DOCTYPE>`, `<!ENTITY>`) içeren akış, nerede olursa olsun ve hangi kodlamada olursa olsun reddedilir: hiçbir varlık açılmaz, dışarıdan bir şey yüklenmez. Birden çok adreste her metin `<document name="<adres>" index="<n>">` ile `</document>` arasındadır (`split: files` ayarlı bir `ai.map` her parçada bir adres alır); okunamayan adres yerinde not edilir, adım yalnızca hiçbir adres okunamazsa başarısız olur.

Tablolar: CSV, TSV ya da Excel (.xlsx) dosyası Markdown tablolarına okunur; ilk satır başlıktır. CSV ayırıcısı `,`, `;`, sekme ya da `|` olabilir (kendiliğinden bulunur); kodlama UTF-8, değilse Windows Türkçe (cp1254). Bir .xlsx dosyasının görünen her sayfası `## <sayfa adı>` altında bir tablodur; tarih biçimli sayılar tarih olur (`2024-01-31`). Sınırlar (kesildiği yerde metin bunu söyler): tablo başına 1.000 satır ve 40 sütun, hücre başına 300 karakter, 20 sayfa, dosya başına 500.000 karakter.

Düğüm türleri:

| Tür | Ayarlar (`config`) | Çıktılar | Varsayılan yeniden deneme / zaman aşımı |
|---|---|---|---|
| `document.extract` | `file` (tam olarak bir dosya yer tutucusu), `max_chars` (dosya başına), `max_age_days` (akışlar), `ocr` (`auto`, `always`, `never`), `ocr_languages`, `speech_model`, `speech_language` | `text` (isteğe bağlı bir dosya girdisi boş bırakılmışsa boş; birden çok dosyada her dosya `<document name="<dosya>" index="<n>">` ile `</document>` arasında) | 0 / 3600 sn |
| `ai.cli` | `provider`, `prompt`, `output` (`text` ya da `json`), `json_schema` (isteğe bağlı, `json` ile) | `text` (`json` ile: cevap, düzenli girintili JSON olarak) | 2 / `config.toml` içindeki `timeout` |
| `condition` | `value` (sınanacak metin; varsayılan: bağlı metin), `operator` (`ai`, `contains`, `not_contains`, `equals`, `regex`, `is_yes`, `empty`; varsayılan `contains`), `question` ve `provider` (`ai` için), `match` (`ai`, `is_yes` ve `empty` dışında), `case_sensitive` (varsayılan false), `pass` (dalın taşıdığı metin; varsayılan: `value`) | `true` ya da `false`: yalnızca seçilen dal, `pass` ya da `value` metnini taşır | 0 / 60 sn |
| `ai.map` | `source`, `split` (`headings`, `paragraphs`, `chunks`, `files`), `chunk_chars` (500–200000, varsayılan 12000), `max_items` (1–200, varsayılan 50), `provider`, `prompt` (`{{item.text}}`, `{{item.title}}`, `{{item.index}}`, `{{item.count}}` kullanabilir), `heading` (varsayılan true) | `text`: cevaplar sırayla, her biri `## <parça başlığı>` altında | 2 / `config.toml` içindeki `timeout`, model çağrısı başına |
| `text.merge` | `template` | `text` | 0 / 60 sn |
| `approval` | `show` (onaylanacak metin), `instructions` | `text`, `comment` | yok (bir kişiyi bekler) |
| `ai.agent` | `provider` (Claude Code), `prompt`, `sites` (her satıra bir alan adı), `mode` (`read`, `act`; `act` öncesinde bir onay gerektirir), `headless` | `text` (modelin raporu) | 0 / 1800 sn |
| `share.x` | `text` (varsayılan: bağlı metin) | `text`, `url` (X'in doldurulmuş paylaşım penceresi) | 0 / 60 sn |
| `document.export` | `source`, `title`, `lang`, `formats` (`md`, `docx`, `html`, `pdf`, `epub`, `eml`, `json`, `csv`), `filename`, `converter` (`auto`, `builtin`, `pandoc`) | biçim başına bir dosya; Markdown tabloları Word, HTML ve PDF'te gerçek tablo olur; bağlantılar (`[metin](https://…)`, `<https://…>`) HTML, PDF ve e-postada bağlantı, Word'de "metin (adres)" olur | 0 / 300 sn |

- `output: json` (bir yapay zekâ adımı): istem yalnızca JSON ister, `json_schema` verilmişse şemayı da ekler (bir JSON Schema nesnesi; olmayan bir metni denetim reddeder). Cevap JSON olarak okunur (```` ```json ```` bloğunun içinden de). JSON değilse ya da şemaya uymuyorsa (`type`, `enum`, `const`, `required`, `properties`, `additionalProperties: false`, `items`, `minItems`, `maxItems`, `minLength`, `maxLength`, `minimum`, `maximum`), model hatayla bir kez daha sorulur. İkinci yanlış cevap denemeyi o hatayla başarısız kılar. Çalıştırmanın okuyucusu sonucu düzenli girintili gösterir. Tahmin böyle bir adım için deneme başına 2 çağrı sayar.
- `eml`: bir e-posta programının düzenleyip göndermek için açtığı taslak (`X-Unsent: 1`): başlık konu olur, metin düz metin ve HTML olarak; gönderen yok, alıcı yok. Mehteran hiçbir zaman e-posta göndermez.
- `json`, `csv`: metin JSON ise (```` ```json ```` bloğunda da) ya da bir Markdown tablosu içeriyorsa. `json`: JSON'un kendisi ya da ilk tablo, nesne listesi olarak. `csv`: ilk tablo ya da nesne veya liste listesi olan JSON; Excel için BOM'lu UTF-8. `=`, `+`, `-` ya da `@` ile başlayan ve sayı olmayan bir hücrenin başına `'` konur, böylece tablo programı onu formül olarak çalıştırmaz. İkisi de yoksa adım hiçbir şey yazmadan başarısız olur. Bir sonucun düzenlenmiş sürümü de bu biçimlere aktarılabilir.

### Çıktı dili (şablon yazarları için)

Bir iş akışının yazacağı dil için `language` türünde bir girdi kullanın: `- {id: language, type: language, label: {tr: Rapor dili, en: Report language}}`.

- Çalıştır bölümü bu girdiyi kayıttaki bütün dillerle bayraklı liste olarak gösterir ve çalıştıranın arayüz diliyle açar. `default` yazmayın: `default: en` ile bir Türk kullanıcı, değiştirmedikçe İngilizce belge alır. (Tek bir dille başlaması gereken bir iş akışında `default: <kod>` yazılabilir.)
- Değeri dil kodudur (`tr`, `en`, `ar`, `uz`...). `document.export` adımına `lang: "{{inputs.language}}"` olarak verin. Girdinin kimliği `language` ise ve bir talimat `{{inputs.language}}` kullanmıyorsa, o talimata "Write the answer in <dilin İngilizce adı>." satırı eklenir; talimata ayrıca dil cümlesi yazmak gerekmez. Kodu kendisi adlandıran bir talimatın ("the language with the code "{{inputs.language}}"") sonuna "The language code "sq" means Albanian." satırı eklenir; küçük bir modelin kodu bilmesi gerekmez.
- Komut satırından ya da API'den değer verilmeden (ve varsayılan olmadan) başlatılan bir çalıştırma mesaj dilini kullanır (`--lang`, `X-Lang`).
- `language` girdisinde `options` kullanılamaz. Yalnızca bazı dilleri sunmak için seçenekleri dil kodu olan bir `choice` girdisi bırakın (`options: [tr, en, ar]`, kimliği `language`): bayraklı liste olarak o seçeneklerle görünür ve arayüz dili seçenekler arasındaysa onunla açılır.
- Bir iş akışının etiketleri ve açıklamaları `{tr, en}` eşlemesi olarak kalır; başka bir arayüz dili İngilizce metni gösterir.

### Yalnızca talimat verilen adımlar

Bir talimatta girdiyi, yapılacak işi ve beklediğiniz çıktıyı belirtin. Örneğin: “Toplantı notlarından her kararı ayrı satıra çıkar. Karar, sorumlu ve tarih sütunlarını kullan. Notlarda sorumlu veya tarih yoksa ilgili hücreye ‘Belirtilmemiş’ yaz.” Örnek bir toplantı notuyla **Bu adımı dene** seçeneğini kullanarak eksik tarihlerin nasıl gösterildiğini kontrol edebilirsiniz.

Bir adım yalnızca bir talimat ve bir modelden oluşabilir; bağlantılar hangi metinler üzerinde çalışacağını söyler. Düzenleyicinin sade paneli bunu gösterir (`GET /api/node-types` içinde `basic` ile işaretli alanlar: `ai.cli` ve `ai.map`: `prompt` (talimat) ve `provider`; `condition`: `question` ve `provider`; `document.export`: `formats`; `approval`: `instructions`; `document.extract` ve `text.merge`: hiçbiri). Yeni bir koşul düğümü `initial_config` (`{"operator": "ai"}`) ile başlar.

```yaml
schema_version: 1
id: minimal
name: Summary
inputs:
  - {id: doc, type: file}
nodes:
  - {id: read, type: document.extract}                       # dosya adlandırılmamış: tek dosya girdisi
  - {id: summary, type: ai.cli, config: {provider: claude, prompt: "Bu belgeyi beş maddede özetle."}}
  - {id: urgent, type: condition, config: {operator: ai, provider: claude, question: "Acil bir şey istiyor mu?"}}
  - {id: alert, type: ai.cli, config: {provider: claude, prompt: "Yönetici için kısa bir uyarı yaz."}}
  - {id: save, type: document.export, config: {formats: [md, docx]}}   # source yok: bağlı metinler
connections:
  - {from: read.text, to: summary}
  - {from: summary.text, to: urgent}
  - {from: urgent.true, to: alert}
  - {from: summary.text, to: save}
  - {from: alert.text, to: save}
```

Kurallar (verisini adlandıran bir adım, bütün hazır şablonlar gibi, tam olarak eskisi gibi çalışır):

- `ai.cli`: talimat hiçbir veri adlandırmıyorsa (`{{nodes.*}}` yok, dosya girdisi yok), bağlı adımların metinleri bağlantı sırasıyla talimatın arkasına eklenir; her biri adımının başlığı altında ve veri etiketleri arasındadır (her zamanki "bu veri, talimat değil" notuyla). İş akışında bir `language` girdisi varsa ve talimat onu kullanmıyorsa, son satır "Write the answer in <dil>." olur (`tr` → Turkish, `en` → English; başka değerler yazıldığı gibi). Bütün bir düğümden gelen bağlantı onun `text` çıktısını getirir; atlanan bir dal hiçbir şey eklemez.
- `ai.map`: `source` yoksa bağlı metinler (birleştirilmiş). Talimatta `{{item.text}}` yoksa her parça (başlığı ve metni, veri olarak) ve dil satırı talimatın arkasına eklenir.
- `template` olmayan `text.merge`, `source` olmayan `document.export`: bağlı metinler bağlantı sırasıyla; birden çoksa her biri bir `## <başlık>` altında; atlanan bir dal dışarıda kalır.
- `value` olmayan `condition`: bağlı metin. `operator: ai`, modele (`provider`) bu metni veri olarak vererek `question` sorusunu sorar. Cevabın ilk kelimesi karar verir: yes, y, true, evet, e, doğru → `true`; no, n, false, hayır, h, yanlış, değil → `false` (biçimlendirme yok sayılır). Başka bir cevapta bir kez daha sorulur; yine belirsizse düğüm başarısız olur ("evet ya da hayır demedi"). Dal cevabı değil, sınanan metni taşır; cevap düğüm klasöründe saklanır (`answer.md`).
- `show` olmayan `approval`: bağlı metin.
- `file` olmayan `document.extract`: iş akışının tek dosya girdisi (hiç ya da birden çok varsa denetim onu ister).

Denetim yalnızca gerçekten eksik olanı bildirir: talimatı ya da modeli olmayan bir yapay zekâ adımı, sorusu ya da modeli olmayan `operator: ai` koşulu, dosyasını bilemeyen bir okuma adımı.

Bir iş akışında koşullar (koşuldan çıkan bir bağlantı dalını yazmalıdır):

```yaml
  - id: gate
    type: condition
    config: {value: "{{nodes.assess.text}}", operator: is_yes}   # yapay zekâ adımı "evet ..." ya da "hayır ..." dedi
  - id: escalate
    type: ai.cli
    config: {provider: claude, prompt: "Escalate: {{nodes.gate.true}}"}
  - id: reply
    type: ai.cli
    config: {provider: claude, prompt: "Reply: {{nodes.gate.false}}"}
  - id: report
    type: text.merge                      # birleşme: seçilen dalın metnini alır
    config: {template: "{{nodes.escalate.text}}{{nodes.reply.text}}"}
connections:
  - {from: assess.text, to: gate}
  - {from: gate.true, to: escalate}
  - {from: gate.false, to: reply}
  - {from: escalate.text, to: report}
  - {from: reply.text, to: report}
```

`is_yes`, metnin ilk kelimesi yes, y, true, evet, e ya da doğru ise doğrudur (büyük/küçük harf ve biçimlendirme yok sayılır). `equals` iki uçtaki boşlukları yok sayar. `regex` Python söz dizimini kullanır ve `match` yer tutucu içermiyorsa denetlenir. İşlecin adı `yes` değildir: YAML yalın `yes` kelimesini true olarak okur.

Bir döngü:

```yaml
  - id: chapters
    type: ai.map
    config:
      source: "{{nodes.extract.text}}"
      split: headings          # bulunan en üst başlık düzeyi; ilk başlıktan önceki metin de bir parçadır
      max_items: 150           # daha fazla parça: düğüm açık bir mesajla başarısız olur
      provider: "{{inputs.model}}"
      prompt: "Summarise chapter {{item.index}} of {{item.count}}: {{item.title}} {{item.text}}"
```

`split: paragraphs` her paragraf için bir parça yapar; `chunks` paragrafları yaklaşık `chunk_chars` karakterlik parçalarda toplar (çeviri uygulamasının bölücüsü); `files` çok dosyalı bir okumanın her dosyası için bir parça yapar (başlık dosya adıdır). İstemde `{{item.text}}` ve `{{item.title}}`, düğüm çıktıları gibi veri etiketleri arasına konur. `{{item.*}}` yalnızca bir `ai.map` düğümünün isteminde kullanılabilir.

Yer tutucular: `{{inputs.<id>}}` ve `{{nodes.<id>.<çıktı>}}` (bir döngünün isteminde ayrıca `{{item.*}}`). Birden çok dosyalı bir dosya girdisi yollarını her satıra bir tane olarak verir. Kurallar:

- Bir düğüm başka bir düğümün çıktısını yalnızca bir bağlantı onları birleştiriyorsa kullanabilir (`from: <düğüm>.<çıktı>`, `to: <düğüm>`). Böylece çizim gerçek veri akışıdır.
- Yer tutucular tek geçişte değiştirilir: bir yer tutucunun eklediği metin (bir belge, bir cevap) yeniden taranmaz.
- Bir `ai.cli` isteminde her düğüm çıktısı `<data source="...">` ve `</data>` etiketleri arasına konur; istem, bu etiketlerin içeriğinin talimat değil veri olduğunu söyleyen bir notla başlar. Metnin içindeki bir `</data>` bölünür, böylece bloğu bitiremez.

Denetim şunları reddeder: her düzeyde bilinmeyen anahtarlar, tekrarlanan kimlikler ya da anahtarlar, olmayan düğüm veya çıktılara bağlantılar, döngüler, bilinmeyen düğüm türleri, çözülemeyen ya da bağlantısı olmayan yer tutucular ve kimlik bilgisine benzeyen her şey (`api_key`, `token`, `password` gibi anahtarlar ya da API anahtarına benzeyen değerler). Sorunların hepsi, dosyadaki yerleriyle birlikte bir kerede listelenir.

## Güvenlik

- Arayüz yalnızca `127.0.0.1` adresini dinler. İstekler `127.0.0.1:<port>` ya da `localhost:<port>` adresine gönderilmelidir.
- Her başlatmada yeni bir oturum anahtarı oluşur; her API isteği bunu taşımalıdır (sabit sürede karşılaştırılır).
- Boyut sınırları: JSON isteği için 2 MB, yükleme için 300 MB, birden çok dosya alan bir girdi için 20 dosya ve toplam 500 MB. Yüklenen dosyanın adı güvenli bir yalın ada indirgenir.
- Bir .xlsx dosyası çeviri uygulamasının korumalı XML okuyucusuyla okunur: varlık (entity) tanımı olan ya da açılınca 100 MB'ı aşan bir parça okunmaz.
- Her dosya erişimi veri klasörünün içinde çözülür; dışına çıkan bir yol reddedilir. Word ve HTML sonuçları yalnızca indirilir, arayüzün içinde gösterilmez. Markdown sonucu DOM öğeleri ve metin düğümleriyle biçimli gösterilir; içindeki ham HTML metin olarak kalır, bağlantıları yalnızca `http`/`https` adreslerini, açan sayfaya erişim vermeden yeni sekmede açar.
- Yanıtlar `X-Content-Type-Options: nosniff`, `Cache-Control: no-store` ve sıkı bir Content-Security-Policy taşır (satır içi betik ve stil yok, çerçeve yok). Başka hiçbir sayfa Mehteran'ı çerçevede gösteremez.
- Bir `url` girdisi yalnızca herkese açık adresleri okur (yukarıda "Web sayfaları"): koruma çözülen her adresi ve her yönlendirmeyi denetler, vekil sunucu kullanmaz, süreyi ve boyutu sınırlar.
- Sonuçları klasöre kaydetme yalnızca kullanıcının yazıp onayladığı bir klasöre yazar; hiçbir zaman bir sistem klasörüne ya da Mehteran'ın klasörlerine yazmaz, var olan bir dosyanın üzerine yazmaz. Bir çalıştırmayı silmek yalnızca veri klasörünün içindeki klasörünü siler; bir süreç çalıştırmayı yürütürken asla silmez.

## Çeviri uygulamasıyla sınır

Mehteran çeviri uygulamasının Python kodunu değiştirmez. Şu dosyaların hiçbirini değiştirmez: `pipeline/*.py`, `prompts/`, `config.default.toml`, `config.toml`, `scripts/start.sh`, `scripts/start.cmd`, `translate`, `translate.cmd`, `Open Interface.*`, `books/`. Çeviri uygulamasının arayüzü (`pipeline/ui/`) ortaktır: `app.js` kendini hem kendi sayfasına hem Mehteran'ın sayfasına yerleştirir (`TranslationUI.mount`); `style.css` kendi kurallarını `.tr-app` altında tutar. Mehteran'ın stil dosyası `pipeline/ui/style.css` dosyasının temel kurallarının bir kopyasıyla başlar; sayfa, kitap çevirisi için `pipeline/ui/style.css` dosyasını ondan önce yükler.

Mehteran `pipeline` paketinin şu parçalarını içe aktarır ve yalnızca okur ya da çağırır:

| Modül | Ne için |
|---|---|
| `pipeline.providers.run` | kullanıcının `config.toml` dosyasına eklediği bir sağlayıcının model çağrısı (`mehteran/worker.py` içinde) |
| `pipeline.providers.is_quota_message`, `quota_wait_seconds`, `ACCOUNT_REFUSED`, `parse_json`, `_stream_json_answer` | bir aracın cevabını ve kullanım sınırını okumak (Mehteran'ın bağdaştırıcıları, saf işlevler olarak) |
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

Bilerek dışarıda bırakılanlar: eklentiler ve eklenti kaydı, arayüzden herhangi bir komut satırı aracını kaydetme, kabuk ya da Python kodu çalıştıran düğümler, zamanlama ve iş akışlarını paylaşmak için çevrimiçi bir yer (paylaşım bir dosyadır: "Paylaş" ve "İçe aktar").

## Geliştirme

- Testler: `python3 -m unittest discover tests` (Mehteran testleri `tests/test_mehteran_*.py` dosyalarıdır; sahte araç `tests/mehteran_fake_llm.py` ile çalışır, `MEHTERAN_HOME` değişkenini geçici bir klasöre ayarlar ve ağa bağlanmaz).
- Kod: `mehteran/` (yalnızca standart kitaplık). YAML: PyYAML 6.0.2, saf Python, `mehteran/_vendor/yaml/` içinde (MIT lisansı orada); yalnızca güvenli yükleyici ve güvenli yazıcı ile kullanılır.
- Yeni bir düğüm türü: `mehteran/nodes.py` dosyasına başlığı, açıklaması ve etiketli ayar alanlarıyla bir `NodeType` ekleyin (`register(...)`). Şema ve motor onu kendiliğinden tanır. `GET /api/node-types`, düzenleyicinin formları için her türü anlatır : `[{type, label, description, outputs: [{name, kind}], outputs_from (document.export için "formats", yoksa null), joins, branches, takes_retries, default_retries, default_timeout, timeout_per_call, config: [{name, kind (template | localized | int | bool | choice | formats | id), widget ("area", "provider" ya da ""), required, default, label, help, options: [{value, label}], min, max (yalnızca int), item_fields ({{item.*}} alan alanlar)}]}]`; başlıklar ve yardım metinleri `{tr, en}` biçimindedir.
- Arayüz: `mehteran/ui/` (saf JavaScript, derleme adımı yok): `app.js` (sekmeler, kitap çevirisi, kitaplık, Çalıştır bölümü, Çalıştırmalar, Kurulum), `editor.js` (görsel düzenleyici), `canvas.js` (tuval; çalıştırma izleme de kullanır). Kitap çevirisinin arayüzü çeviri uygulamasının `pipeline/ui/app.js` ve `style.css` dosyalarıdır; `/tr/app.js` ve `/tr/style.css` olarak sunulur (`mehteran/translation.py`). Her öğe DOM çağrıları ve metin düğümleriyle yapılır, hiçbir zaman HTML metninden değil.
