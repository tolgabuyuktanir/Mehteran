"use strict";

// ---------- interface texts (Turkish and English) ----------
const I18N = {
  tr: {
    app_title: "Tercüme Masası",
    app_subtitle: "Tercüme ve tashih iş akışı",
    tab_setup: "Kurulum", tab_books: "Kitaplar", tab_prompts: "Talimatlar",
    setup_title: "Kurulum ve oturum",
    setup_intro: "Bu sayfada iki şey yapılır, her bilgisayarda bir kez: \"Eksikleri kur\" iş akışının kullandığı araçları ve PDF okuyucuyu kurar; sonra her araçta kendi hesabınızla oturum açarsınız. Kullanılmayan araçlar gerekmez.",
    refresh_status: "Durumu yenile",
    flow_title: "Hangi adımı hangi araç yapar",
    loading: "Yükleniyor…",
    installed: "Kurulu", not_installed: "Kurulu değil",
    signed_in: "Oturum açık", not_signed_in: "Oturum açılmamış",
    install: "Kur", installing: "Kuruluyor…",
    with_google: "Google hesabıyla", with_chatgpt: "ChatGPT hesabıyla", with_claude: "Claude hesabıyla",
    with_key: "API anahtarıyla", api_key: "API anahtarı", save: "Kaydet",
    test: "Dene", testing: "Deneniyor…",
    used_in: "Kullanıldığı adımlar: {stages}", not_used: "Şu anki iş akışında kullanılmıyor; oturum açmak gerekmez.",
    run_command: "Oturum açmak için bir terminalde şunu çalıştırın: {command}",
    human_step: "Teslim", human_who: "İnsan tercüman, insan editör",
    new_book: "Yeni kitap", new_book_placeholder: "örnek: ilmihal", add: "Ekle",
    no_books: "Henüz kitap yok.", running: "Çalışıyor",
    pick_book: "Soldan bir kitap seçin veya yeni bir kitap ekleyin.",
    source_intro: "Tek dosya: .docx, .epub, .md, .txt veya .pdf. En iyi sonuç .docx ve .epub ile alınır.",
    prepared: "Hazırlandı · {count} bölüm", not_prepared: "Henüz hazırlanmadı",
    reset_hint: "Kaynağı değiştirmek için çalışmayı sıfırlayın. Bütün dillerdeki ara çıktılar silinir.",
    reset_work: "Çalışmayı sıfırla",
    refs_intro: "Referans, bu kitabın başka bir dile daha önce yapılmış, yayımlanmış tercümesidir. Zorunlu değildir; yoksa \"Referanssız devam et\" ile geçin.",
    refs_how: "Ne işe yarar: uygulama her Türkçe bölümün referanstaki karşılığını bulur ve modellere yardımcı metin olarak verir. Modeller oradan terimlerin, özel adların ve zor cümlelerin nasıl karşılandığını görür. Esas her zaman Türkçe kaynaktır: referanstaki bir fark, eksik veya hata çeviriye geçmez.",
    refs_which: "Hangi tercümeler: hedef dile yakın dillerdeki tercümeler en çok yardım eder (Norveççe için Danca ve İsveççe). Dosyayı yüklerken dilini seçin. Türkçe kitabı veya başka bir kitabı yüklemeyin; uygulama yüklenen dosyayı kontrol eder ve şüpheli bir şey görürse uyarır.",
    refs_more: "Referans ne işe yarar, hangisini yüklemeliyim?",
    no_refs: "Referans yok. Referans olmadan da çeviri yapılır, ama yakın dillerdeki tercümeler doğruluğu artırır.",
    aligned: "Hizalanan: {done}/{total}", delete: "Sil",
    add_language: "Listede olmayan bir dil ekle",
    language_code: "kod (örnek: tg)", language_name: "İngilizce adı (örnek: Tajik)", add_language_btn: "Dili ekle",
    upload: "Yükle", choose_language: "Dil seçin…", reference_language: "Referansın dili",
    run_intro: "Çalıştırma kaldığı yerden devam eder. Durdurup yeniden başlatırsanız tamamlanan bölümler yeniden işlenmez.",
    target_language: "Hedef dil", segments: "Bölümler (boşsa hepsi)", segments_placeholder: "örnek: 1-3",
    use_refs: "Kullanılacak referanslar",
    advanced: "Gelişmiş seçenekler", until: "Bu adımdan sonra dur", redo: "Yeniden üret (bu adım ve sonrası silinir)",
    first_book_hint: "İlk kitapta önerilen sıra: önce \"Sözlük\" adımında durun, <code>glossary/&lt;dil&gt;.tsv</code> dosyasını gözden geçirin; sonra 1-3. bölümleri deneyin; uygunsa bütün kitabı çalıştırın.",
    start: "Başlat", stop: "Durdur",
    read_translation: "Çeviriyi oku", read_report: "Raporu oku", download: "İndir",
    log: "Günlük", timeline_title: "Günlükten ilerleme", timeline_failed: "{count} hata", not_run_yet: "Henüz çalıştırılmadı.",
    translation: "Çeviri", report: "Rapor", close: "Kapat",
    pick_file: "Önce bir dosya seçin.", pick_ref_language: "Önce referansın dilini seçin.",
    uploaded: "Yüklendi.", upload_failed: "Yükleme başarısız.", output_unreadable: "Çıktı okunamadı.",
    confirm_delete_ref: "Bu referans tercüme ve hizalaması silinsin mi?",
    confirm_reset: "Bu kitabın bütün ara çıktıları (bütün dillerde) silinecek. Çıktı klasöründeki son kitaplar kalır. Devam edilsin mi?",
    confirm_redo: "Seçili bölümlerde \"{stage}\" ve sonraki adımların çıktısı silinip yeniden üretilecek. Devam edilsin mi?",
    prompts_intro: "Modellere verilen yönergeler. Kendi kurallarınızı \"Yayın ilkeleri\" belgesine yazın; o belge bütün adımlarda geçerlidir. Adım talimatlarını yalnızca bir adımın işleyişini değiştirmek istediğinizde düzenleyin.",
    changed: "değiştirildi", restore_default: "Varsayılana dön",
    required_placeholders: "Zorunlu yer tutucular: pipeline buralara kaynak metni, çeviriyi, sözlüğü ve diğer girdileri koyar",
    prompts_note: "Adım talimatları İngilizcedir, çünkü modeller İngilizce talimatı daha tutarlı uygular. Cevap biçimini (JSON, etiketler) değiştirmeyin; pipeline cevabı bu biçimle okur. Yayın kurallarınızı buraya değil \"Yayın ilkeleri\" belgesine yazın.",
    confirm_discard: "Kaydedilmemiş değişiklikler kaybolacak. Devam edilsin mi?",
    confirm_restore: "Yaptığınız değişiklikler silinip varsayılan talimat geri yüklenecek. Devam edilsin mi?",
    request_failed: "İstek başarısız ({status})",
    stage_prepare: "Hazırlık", stage_align: "Hizalama", stage_glossary: "Sözlük", stage_translate: "İlk tercüme",
    stage_review: "Tashih", stage_apply: "Uygula", stage_source_check: "Kaynak kontrolü",
    stage_assemble: "Birleştirme",
    flow_align: "Hazırlık · hizalama", flow_glossary: "Hazırlık · sözlük", flow_translate: "İlk tercüme",
    flow_review: "Tashih", flow_apply: "Bulguları uygula",
    flow_source_check: "Baştan kaynak kontrolü",
    quota_now: "Kullanım sınırında · {time} saatinde kendiliğinden yeniden denenecek",
    quota_last: "Son kullanım sınırı uyarısı: {time}",
    unaligned: "Referansta bulunamayan bölümler: {segments}. Bu bölümler bu referans olmadan çevrilir.",
    estimate_title: "Başlamadan önce",
    estimate_segments: "{selected} bölüm işlenecek (kitapta {total} bölüm)",
    estimate_guess: "Kitap henüz hazırlanmadığı için bölüm sayısı kaynak dosyadan tahmin edildi.",
    estimate_calls: "Gereken model çağrısı: {calls}",
    estimate_time: "Tahmini süre: {time}. Gerçek süre modellerin hızına ve kullanım sınırlarına göre değişir.",
    estimate_nothing: "Seçilen bölümlerde yapılacak iş kalmadı.",
    estimate_redo: "Seçilen bölümlerde seçili adım ve sonrası yeniden üretilecek. Bu çağrılar burada sayılmaz.",
    quota_note: "Uzun kitaplarda aboneliklerin kullanım sınırları (kota) dolabilir. Sınır dolunca çeviri durmaz: o araca giden istekler bekletilir ve sınır açılınca kendiliğinden devam eder. Bu durum aşağıda ve Kurulum sekmesinde gösterilir.",
    awake_note: "Çeviri sürerken bilgisayar uyanık tutulur. Dizüstü bilgisayarda kapağı kapatmayın ve bilgisayarı prize takılı tutun; kapak kapanınca bilgisayar yine uyur ve çeviri durur.",
    awake_off: "Uyanık tutma kapalı (config.toml: keep_awake) veya bu bilgisayarda desteklenmiyor. Çeviri sürerken bilgisayarın uykuya geçmemesini siz sağlayın.",
    state_running: "Çalışıyor", state_waiting_quota: "Kullanım sınırı bekleniyor", state_finished: "Tamamlandı",
    state_failed: "Hata ile durdu", state_stopped: "Durduruldu", state_interrupted: "Yarıda kesildi",
    hint_failed: "Hataları giderip \"Başlat\" düğmesine basın; tamamlanan bölümler korunur, kaldığı yerden devam eder.",
    hint_stopped: "\"Başlat\" düğmesine basınca kaldığı yerden devam eder.",
    hint_interrupted: "Çalıştırma kayıt bırakmadan kapandı. Bilgisayar uyumuş, kapanmış veya arayüzün terminal penceresi kapatılmış olabilir. \"Başlat\" düğmesine basınca kaldığı yerden devam eder.",
    current_stage: "Şu anki adım: {stage} · {done}/{total}",
    stage_failures: "{count} hata",
    elapsed: "Geçen süre: {time}",
    remaining: "Kalan: {calls} model çağrısı · tahmini {time}",
    quota_history: "Bu çalıştırmada kullanım sınırına {count} kez ulaşıldı.",
    awake_on: "Bilgisayar uyanık tutuluyor.",
    failures_title: "Hata alan işler (son {count})",
    run_target: "{language} çevirisi · başlangıç {time}",
    hours_minutes: "{h} sa {m} dk", minutes_only: "{m} dk", less_than_minute: "1 dakikadan az",
    start_title: "Başlarken",
    start_intro: "Uygulamayı ilk kez kullanıyorsanız bu adımları sırayla tamamlayın. Kurulum yönetici izni gerektirmez; gereken her şey (Node.js dahil) uygulamanın kendi klasörüne kurulur.",
    step_install: "Araçları kurun", step_install_done: "{done}/{total} araç kurulu",
    install_missing: "Eksikleri kur", installing_all: "Kuruluyor… (birkaç dakika sürebilir)",
    step_signin: "Kullanılan araçlarda oturum açın", step_signin_done: "{done}/{total} araçta oturum açık",
    step_signin_hint: "Aşağıdaki kartlarda her araç için \"… hesabıyla\" düğmesine basın.",
    step_book: "İlk kitabınızı ekleyin", step_book_done: "{count} kitap", go_books: "Kitaplara git",
    all_done: "Hazırsınız. Kitaplar sekmesinden çeviri başlatabilirsiniz.",
    watching_signin: "Oturum açmanız bekleniyor; durum birkaç saniyede bir kendiliğinden yenileniyor.",
    tab_workflow: "İş akışı", edit_workflow: "İş akışını düzenle",
    workflow_title: "İş akışı",
    workflow_intro: "Adımlar soldan sağa birbirine bağlı kutulardır; her adım bir öncekinin metni üzerinde çalışır. Soldaki adım türlerini iki kutu arasındaki oka sürükleyin veya oktaki + düğmesine basın; istediğiniz kadar adım ekleyebilirsiniz. Tashih ve rapor yazan özel adımlar bulgu yazar, \u201cUygula\u201d bulguları metne işler. \u201cKontrol noktası\u201d ciddi sorun kalan bölümü seçtiğiniz önceki adıma geri gönderir. Kutuları sürükleyerek sırayı değiştirin; bir kutuya tıklayınca ayarlarını ve modellerini altta seçersiniz. Değişiklikler kendiliğinden kaydedilir.",
    canvas_label: "İş akışı şeması", node_prep: "Hazırlık", prep_mark: "H",
    role_align: "Hizalama", role_glossary: "Sözlük", role_translate: "Tercüme eden", role_check: "Kontrol eden",
    insert_here: "Buraya adım ekle", drag_to_move: "Sırayı değiştirmek için sürükleyin",
    move_earlier: "Öne al", move_later: "Sonraya al", pick_one: "bir model",
    min_one_model: "Bu rolde en az bir model kalmalı.",
    node_locked: "Her çeviri hazırlık ve ilk tercümeyle başlar; bu adımların yeri sabittir, modelleri değiştirilebilir.",
    palette_steps: "Adımlar", palette_steps_hint: "Sürükleyip iki kutu arasındaki oka bırakın; tıklarsanız sona eklenir.",
   
    palette_models: "Modeller", palette_models_hint: "Bir model kartını kutudaki role sürükleyebilirsiniz. \u201cTest\u201d modelin cevap verdiğini dener.",
    visit_n: "{n}. geçiş", flow_custom: "Özel adım", flow_gate: "Kontrol noktası", stage_custom: "Özel adım", stage_gate: "Kontrol noktası",
    node_review: "Tashih", role_gate: "Kontrol eden", role_editor: "Düzelten",
    step_desc_node_review: "Tashihçiler metni Türkçe kaynakla cümle cümle karşılaştırır ve birbirinden habersiz bulgu raporu yazar. Metin değişmez; bulguları sonraki \u201cUygula\u201d adımı işler.",
    step_desc_node_apply: "Son metinden bu yana yazılan bütün bulguları (tashih, özel adım ve kontrol noktası raporları) kaynağa göre tartar, haklı olanları metne uygular.",
    step_desc_node_source_check: "Önceki adımlara güvenmeden metni kaynakla baştan karşılaştırır ve düzeltir.",
    step_desc_node_gate: "Metinde kalan ciddi (kritik veya önemli) sorunları arar. Sorun bulursa o bölümü seçtiğiniz önceki adıma geri gönderir; bulguları sonraki \u201cUygula\u201d adımında işlenir. Sınır dolunca bölüm rapora işaretlenip devam eder.",
    step_desc_custom_report: "Sizin yazdığınız talimata göre metni inceler ve bulgu raporu yazar; bulguları sonraki \u201cUygula\u201d adımı işler.",
    step_desc_custom_rewrite: "Sizin yazdığınız talimata göre metni düzeltir ve yaptığı değişiklikleri kaydeder.",
    problem_custom_title: "Bu özel adımın bir adı olmalı.",
    problem_unapplied: "Bu adımın bulguları uygulanmıyor: ondan sonra, metni değiştiren başka bir adımdan önce bir \u201cUygula\u201d adımı koyun.",
    problem_gate_target: "Bu kontrol noktasının geri göndereceği adımı seçin (kendinden önceki ve önceki kontrol noktasından sonraki bir adım).",
    flow_has_problems: "İş akışında düzeltilmesi gereken {count} sorun var (kırmızı işaretli kutular). Düzeltilene kadar değişiklikler kaydedilmez.",
    not_saved_problems: "Kaydedilmedi: kırmızı işaretli kutuları düzeltin",
    gate_note: "↺ {step} adımına, en çok {max} kez", loop_label: "↺ en çok {max} kez",
    type_round: "Tashih turu", type_review: "Tashih", type_apply: "Uygula", type_source_check: "Kaynak kontrolü", type_custom: "Özel adım", type_gate: "Kontrol noktası",
    type_hint_round: "Tashih ve onu uygulayan adım birlikte.", type_hint_review: "Tashihçiler bulgu yazar, metin değişmez.",
    type_hint_apply: "Önceki bulguları metne işler.", type_hint_source_check: "Metni kaynakla baştan karşılaştırıp düzeltir.",
    type_hint_custom: "Talimatını sizin yazdığınız adım.", type_hint_gate: "Ciddi sorun kalan bölümü geri gönderir.",
    mode_report: "Rapor yazar", mode_rewrite: "Metni düzeltir", custom_title: "Adımın adı", custom_mode: "Ne yapar",
    custom_instructions: "Talimat", custom_instructions_hint: " — Türkçe yazabilirsiniz. Örnek: \u201cHadis kaynak gösterimlerini (Buhârî, Müslim…) kontrol et.\u201d",
    custom_default_title: "Özel adım",
    gate_back_to: "Sorun bulursa şu adıma geri gönder", gate_choose: "Adım seçin…", gate_max: "En çok kaç kez geri göndersin",
    gate_help: "Her geri gönderme o bölüm için aradaki adımları yeniden çalıştırır (kota ve süre harcar). Kontrol noktaları iç içe geçemez: geri gönderme önceki kontrol noktasını aşamaz.",
   
    remove_step: "Adımı sil",
    confirm_remove_step: "\"{step}\" adımı iş akışından çıkarılsın mı? Daha önce çevrilmiş kitaplardaki çıktısı silinmez.",
    reviewers_label: "Tashihçiler", applier_label: "Bulguları uygulayan", max_steps: "En çok {count} adım eklenebilir.",
    flow_changed_note: "Adım ekleyip çıkarmak daha önce çevrilmiş bölümleri değiştirmez. Kitap ekranı, yeni sıraya göre yeniden üretilmesi gereken bölümleri gösterir.",
    unsaved: "Kaydedilmedi", preset: "Şemadaki dağılım",
    effort_title: "Düşünme seviyesi: yüksek seviye daha dikkatli ama daha yavaş çalışır ve kotayı daha çok harcar.",
    effort_default: "Varsayılan seviye", effort_low: "düşük", effort_medium: "orta", effort_high: "yüksek",
    effort_xhigh: "çok yüksek", effort_max: "en yüksek", effort_none: "bu araçta seviye seçilemez",
    default_model: "varsayılan model", add_model_placeholder: "model adı (örnek: opus)", add_other_model: "Listede olmayan bir model ekle",
    models_loading: "Model listesi okunuyor…", models_none: "Model listesi okunamadı. Araç kurulu olmalı ve en az bir kez çalışmış olmalı.",
    remove: "Kaldır", parallel_tag: "paralel · en çok 4 model",
    step_desc_align: "Her Türkçe bölümün referans tercümedeki karşılığını bulur. Referans yoksa atlanır.",
    step_desc_glossary: "Dinî terimleri ve özel adları çıkarır; dil başına ortak sözlüğe yeni terimleri ekler.",
    step_desc_translate: "Türkçe kaynak, referans pasajlar ve sözlükle ilk tercümeyi yapar.",
    step_desc_review: "Tashihçiler metni Türkçe kaynakla cümle cümle karşılaştırır ve birbirinden habersiz bulgu raporu yazar. Ardından bir model bulguları kaynağa göre tartar ve haklı olanları uygular.",
    step_desc_source_check: "Önceki adımlara güvenmeden metni kaynakla baştan karşılaştırır ve düzeltir.",
    step_desc_human: "Çeviri ve rapor insan tercümana teslim edilir; ardından insan editör okur.",
    warn_self_review: "{step}: {model} kendi yazdığı metni tashih ediyor. Tashihe başka bir model koyun.",
    warn_self_check: "{step}: {model} metni bir önceki adımda kendisi yazdı. Bağımsız bir model daha güvenilir olur.",
    info_same_provider: "{step}: bütün tashihçiler metni yazan modelle aynı şirketin. Farklı bir şirketin modeli hataları daha iyi yakalar.",
    warn_no_check: "Tercümeden sonra hiçbir denetim adımı yok. Çeviri tashih edilmeden teslim edilecek.",
    cannot_remove_used: "Bu model bir adımda kullanılıyor; önce adımdan kaldırın.",
    model_name_invalid: "Model adı harf veya rakamla başlamalı; yalnızca harf, rakam ve . _ : - içerebilir.",
    upload_bad_type: "Bu dosya türü desteklenmiyor. Desteklenenler: .docx, .epub, .md, .txt, .pdf",
    upload_bad_size: "Dosya boş veya çok büyük (en çok 300 MB).",
    max_reviewers: "Bu adıma en çok 4 model atanabilir.",
   
    export_label: "Dışa aktar", fmt_md: "Markdown", fmt_docx: "Word", fmt_pdf: "PDF", fmt_html: "HTML",
    layout_open: "Biçim ayarları", layout_title: "Dışa aktarma biçimi",
    layout_intro: "Kitabın Word, PDF ve HTML çıktısının görünümü. Bütün kitaplara uygulanır. Rapor her zaman standart A4 biçimiyle çıkar.",
    layout_template: "Word şablonu", layout_template_remove: "Şablonu kaldır",
    layout_template_none: "Şablon yok. Word dosyası aşağıdaki ayarlarla oluşturulur.",
    layout_template_set: "Yüklü şablon: {name}. Word dosyası bu şablonun stillerini, sayfa boyutunu, kenar boşluklarını, üst ve alt bilgilerini kullanır. Şablondaki metin kullanılmaz.",
    layout_template_hint: "Yayınevinizin .docx veya .dotx şablonunu yükleyin. Word'deki \"Başlık 1–3\", \"Alıntı\", \"Madde İşareti\" ve \"Dipnot Metni\" stilleri kullanılır; şablonda olmayanlar eklenir.",
    layout_settings: "Sayfa ve yazı",
    layout_scope_all: "Word, PDF ve HTML'ye uygulanır.",
    layout_scope_pdf: "PDF ve HTML'ye uygulanır. Word dosyası şablonu kullanır.",
    layout_page_size: "Sayfa boyutu", layout_font_size: "Punto", layout_line_spacing: "Satır aralığı",
    layout_margin_top: "Üst boşluk (cm)", layout_margin_bottom: "Alt boşluk (cm)", layout_margin_side: "Yan boşluklar (cm)",
    layout_font: "Yazı tipi", layout_arabic_font: "Arapça yazı tipi", layout_automatic: "Otomatik",
    layout_justify: "Paragrafları iki yana yasla", layout_chapter_new_page: "Her ana bölüm yeni sayfada başlasın",
    layout_fonts_note: "Yazı tipi bilgisayarda kurulu olmalı. PDF bu bilgisayardaki yazı tipleriyle oluşturulur; Word dosyası açıldığı bilgisayardakileri kullanır. Satır aralığı Word'deki gibidir: 1 tek satır, 1,15 Word'ün varsayılanı.",
    layout_defaults: "Varsayılan değerler", layout_pick_file: "Önce bir Word dosyası seçin.", layout_confirm_remove: "Word şablonu kaldırılsın mı?",
    page_A4: "A4 (21 × 29,7 cm)", page_A5: "A5 (14,8 × 21 cm)", page_B5: "B5 (17,6 × 25 cm)", "page_13.5x21": "13,5 × 21 cm",
    page_16x24: "16 × 24 cm", page_Letter: "Letter (21,6 × 27,9 cm)",
    pdf_hint: "PDF: açılan sayfada yazdırma penceresinden \"PDF olarak kaydet\" seçin.",
    step_install_hint: "İş akışının kullandığı araçlar (Claude Code, Codex, Antigravity) ve PDF okuyucu bu bilgisayara kurulur. Gerekirse Node.js de uygulamanın klasörüne indirilir. Yönetici izni gerekmez.",
    pdf_uses: "PDF kitapları okur. .docx ve .epub kitaplar için gerekmez.",
    first_book_title: "İlk kitabınızı ekleyin",
    first_book_intro: "Kitaba kısa bir ad verin. Sonra Türkçe kaynağı ve varsa yakın dillerdeki tercümeleri yükleyeceksiniz.",
    create_book: "Kitabı oluştur",
    step_source: "Türkçe kaynak", step_refs: "Referans tercümeler", step_run: "Çeviri", step_result: "Sonuç",
    locked_refs: "Önce Türkçe kaynağı yükleyin.", locked_run: "Önce kaynak ve referans adımlarını tamamlayın.",
    locked_result: "Çeviri bitince burada okuyup indirebilirsiniz.",
    summary_source_empty: "Kaynak dosyayı yükleyin", summary_source: "{file} · {count} bölüm",
    summary_refs_check: "kontrol edin: {languages}", summary_refs_none: "Referans kullanılmıyor", summary_refs_optional: "İsteğe bağlı, doğruluğu artırır",
    summary_running: "{language} · {stage} · {done}/{total}",
    summary_run_more: "Başka bir dile çevirmek için açın", summary_run_ready: "Hedef dili seçip başlatın",
    continue: "Devam et", skip_refs: "Referanssız devam et",
    progress_details: "Adım adım ilerleme",
    review_row: "{reviewer}: {issues} bulgu · {segments} bölümün {empty} tanesinde bulgu yok",
    review_quiet: "Çoğu bölümde hiç bulgu yazmadı. Birkaç bölümü elle kontrol edin.",
    review_missed: "{count} bölümde bulgu yazmadı ama sonradan bu bölümlerde ciddi hata bulundu: {segments}",
    review_attention: "Tashihçi uyarısı",
    stale_title: "Girdileri değişen bölümler",
    stale_intro: "Bu bölümler üretildikten sonra sözlük, referans veya talimat değişti. Eski girdilerle duruyorlar; siz istemeden yeniden üretilmezler.",
    stale_row: "{stage} adımından itibaren: bölüm {segments}", stale_fill: "Yeniden üretmeye hazırla",
    stale_filled: "Form dolduruldu. Yeniden üretmek için Başlat'a basın.",
    preview_hint: "Çeviriden önce metnin doğru okunduğunu kontrol edin. PDF'te özellikle dipnotlara, başlıklara ve Arapça âyetlere bakın.",
    preview_prepare: "Metni böl ve önizle", preview_open: "Bölünmüş metni gör", preview_title: "kaynak önizleme · {count} bölüm",
    saving: "Kaydediliyor…", saved_now: "Kaydedildi ✓",
    confirm_preset: "Adımlar ve modeller şemadaki hâline (Gemini, ChatGPT, Claude) döndürülecek. Devam edilsin mi?",
    recover_title: "{model} hata verdi ({stages})",
    recover_account: "{model} bu hesapla kullanılamıyor.",
    recover_intro: "Çeviri durdu. Başka bir modelle devam edilsin mi? Seçtiğiniz model, iş akışında {model} kullanan bütün adımlara konur. Tamamlanan bölümler korunur.",
    recover_with: "Yerine", recover_go: "Bu modelle devam et", recover_retry: "Aynı modelle tekrar dene",
    decide_quota_title: "{model} kullanım sınırına ulaştı",
    decide_quota_body: "Çeviri bekliyor; {time} saatinde {tool} ile kendiliğinden devam edecek. Beklemek istemiyorsanız başka bir modelle devam edin ya da çeviriyi durdurun.",
    decide_error_running: "Diğer bölümler sürüyor, ama bu bölümler tamamlanmayacak. Başka bir modelle devam edebilir, böyle sürdürebilir ya da çeviriyi durdurabilirsiniz.",
    decide_wait: "Beklesin", decide_keep: "Böyle devam etsin", decide_stop: "Durdur",
    recover_switching: "Çeviri durduruluyor, ardından yeni modelle başlayacak…",
    stop_timeout: "Çeviri durdurulamadı. Biraz sonra tekrar deneyin.",
    recover_done: "İş akışı güncellendi: {from} yerine {to}. Çeviri kaldığı yerden devam ediyor.",
    prompt_title_rules: "Yayın ilkeleri", prompt_title_translate: "İlk tercüme", prompt_title_review: "Tashih raporu",
    prompt_title_revise: "Bulguları uygulama", prompt_title_source_check: "Baştan kaynak kontrolü", prompt_title_custom_report: "Özel adım: rapor yazan", prompt_title_custom_rewrite: "Özel adım: metni düzelten", prompt_title_gate: "Kontrol noktası",
    prompt_title_glossary: "Terim sözlüğü", prompt_title_align: "Referans hizalama",
    all_steps: "Bütün adımlar",
    step_prompts: "Adım talimatları", step_prompts_hint: "İleri düzey. Her adımın görevini ve cevap biçimini tanımlar.",
    rules_intro: "Yayınevinizin kuralları. Bu belgenin tamamı bütün adımlarda modellere verilir ve önceliklidir. Türkçe yazabilirsiniz. Kuralları kısa ve kesin yazın: her madde tek bir şey söylesin; \"genellikle\", \"mümkünse\" gibi belirsiz sözlerden kaçının.",
    prompt_used_in: "Kullanıldığı adımlar: {steps}", prompt_unused: "Şu anki iş akışında bu talimatı kullanan adım yok.", not_in_flow: "İş akışında yok",
    prompt_custom_note: "Her özel adımın kendi görevi İş akışı sekmesinde, o adımın panelinde yazılır ve bu talimattaki {{instructions}} yerine konur. Burada bütün özel adımların ortak çerçevesi ve cevap biçimi var.",
    ph_instructions: "özel adımın İş akışı sekmesinde yazılan görevi",
    prompts_apply: "Değişiklik, kaydettikten sonra işlenen bölümlerde geçerli olur. Daha önce işlenen bölümler, Kitaplar ekranında \"girdileri değişen bölümler\" olarak gösterilir ve oradan yeniden üretilebilir.",
    ph_target_lang: "hedef dilin adı", ph_source: "Türkçe kaynak bölüm", ph_translation: "denetlenen veya düzeltilen çeviri",
    ph_glossary: "bu bölümde geçen sözlük terimleri", ph_references: "referans tercümelerdeki karşılık pasajlar",
    ph_ref_langs: "referans dillerin adları", ph_context: "önceki bölümün sonu (yalnızca bağlam için)",
    ph_issues: "tashih bulguları (JSON)", ph_note_lang: "modelin açıklamaları yazacağı dil (arayüz dili)",
    ph_rules: "Yayın ilkeleri belgesi", ph_segment: "hizalanacak Türkçe bölüm", ph_window: "referanstan numaralı paragraflar",
    ph_ref_lang: "referansın dili",
    setup_banner: "Araçlar henüz hazır değil. Çeviri başlatmadan önce kurulumu tamamlayın.", go_setup: "Kuruluma git",
  },
  en: {
    app_title: "Translation Desk",
    app_subtitle: "Translation and review workflow",
    tab_setup: "Setup", tab_books: "Books", tab_prompts: "Instructions",
    setup_title: "Setup and sign-in",
    setup_intro: "Two things are done here, once on each computer: \"Install missing tools\" installs the tools of the workflow and the PDF reader; then you sign in to each tool with your own account. Tools that the workflow does not use are not needed.",
    refresh_status: "Refresh status",
    flow_title: "Which tool does which step",
    loading: "Loading…",
    installed: "Installed", not_installed: "Not installed",
    signed_in: "Signed in", not_signed_in: "Not signed in",
    install: "Install", installing: "Installing…",
    with_google: "With Google account", with_chatgpt: "With ChatGPT account", with_claude: "With Claude account",
    with_key: "With API key", api_key: "API key", save: "Save",
    test: "Test", testing: "Testing…",
    used_in: "Used in: {stages}", not_used: "Not used in the current workflow; no sign-in is needed.",
    run_command: "To sign in, run this in a terminal: {command}",
    human_step: "Delivery", human_who: "Human translator, human editor",
    new_book: "New book", new_book_placeholder: "for example: ilmihal", add: "Add",
    no_books: "No books yet.", running: "Running",
    pick_book: "Select a book on the left, or add a new book.",
    source_intro: "One file: .docx, .epub, .md, .txt or .pdf. The best results come from .docx and .epub.",
    prepared: "Prepared · {count} segments", not_prepared: "Not prepared yet",
    reset_hint: "To change the source, reset the work. The intermediate output of all languages is deleted.",
    reset_work: "Reset work",
    refs_intro: "A reference is an earlier, published translation of this book into another language. It is optional; without one, click \"Continue without references\".",
    refs_how: "What it does: the application finds the match of each Turkish segment in the reference and gives it to the models as a help text. From it the models see how terms, names and difficult sentences were handled. The Turkish source always decides: a difference, a gap or an error in the reference does not pass into the translation.",
    refs_which: "Which translations: translations into languages close to the target language help most (Danish and Swedish for Norwegian). Select the language of the file when you upload it. Do not upload the Turkish book or another book; the application checks the uploaded file and warns when something looks wrong.",
    refs_more: "What does a reference do, which one should I upload?",
    no_refs: "No references. The translation works without them, but translations in related languages improve accuracy.",
    aligned: "Aligned: {done}/{total}", delete: "Delete",
    add_language: "Add a language that is not in the list",
    language_code: "code (for example: tg)", language_name: "English name (for example: Tajik)", add_language_btn: "Add language",
    upload: "Upload", choose_language: "Select a language…", reference_language: "Language of the reference",
    run_intro: "A run continues where it stopped. If you stop it and start it again, finished segments are not processed again.",
    target_language: "Target language", segments: "Segments (empty for all)", segments_placeholder: "for example: 1-3",
    use_refs: "References to use",
    advanced: "Advanced options", until: "Stop after this step", redo: "Produce again (this step and later ones are deleted)",
    first_book_hint: "Recommended order for the first book: stop after the \"Glossary\" step and review <code>glossary/&lt;lang&gt;.tsv</code>; then try segments 1-3; if the result is good, run the whole book.",
    start: "Start", stop: "Stop",
    read_translation: "Read translation", read_report: "Read report", download: "Download",
    log: "Log", timeline_title: "Progress from the log", timeline_failed: "{count} failed", not_run_yet: "Not run yet.",
    translation: "Translation", report: "Report", close: "Close",
    pick_file: "Select a file first.", pick_ref_language: "Select the language of the reference first.",
    uploaded: "Uploaded.", upload_failed: "Upload failed.", output_unreadable: "Cannot read the output.",
    confirm_delete_ref: "Delete this reference translation and its alignment?",
    confirm_reset: "All intermediate output of this book (in all languages) will be deleted. The final books in the output folder stay. Continue?",
    confirm_redo: "For the selected segments, the output of \"{stage}\" and of the later steps will be deleted and produced again. Continue?",
    prompts_intro: "The instructions given to the models. Write your own rules in the \"Publishing rules\" document; it applies to every step. Edit a step instruction only when you want to change how that step works.",
    changed: "changed", restore_default: "Restore default",
    required_placeholders: "Required placeholders: the pipeline puts the source text, the translation, the glossary and the other inputs there",
    prompts_note: "The step instructions are in English, because the models follow English instructions more consistently. Do not change the answer format (JSON, tags); the pipeline reads the answer in this format. Write your publishing rules in the \"Publishing rules\" document, not here.",
    confirm_discard: "Unsaved changes will be lost. Continue?",
    confirm_restore: "Your changes will be deleted and the default instructions restored. Continue?",
    request_failed: "Request failed ({status})",
    stage_prepare: "Preparation", stage_align: "Alignment", stage_glossary: "Glossary", stage_translate: "First translation",
    stage_review: "Review", stage_apply: "Apply", stage_source_check: "Source check",
    stage_assemble: "Assembly",
    flow_align: "Preparation · alignment", flow_glossary: "Preparation · glossary", flow_translate: "First translation",
    flow_review: "Review", flow_apply: "Apply the findings",
    flow_source_check: "Source check from the start",
    quota_now: "At its usage limit · tries again by itself at {time}",
    quota_last: "Last usage-limit warning: {time}",
    unaligned: "Segments not found in the reference: {segments}. These segments are translated without this reference.",
    estimate_title: "Before you start",
    estimate_segments: "{selected} segments will be processed (the book has {total})",
    estimate_guess: "The book is not prepared yet, so the number of segments is estimated from the source file.",
    estimate_calls: "Model calls needed: {calls}",
    estimate_time: "Estimated time: {time}. The real time depends on the speed of the models and on the usage limits.",
    estimate_nothing: "Nothing is left to do for the selected segments.",
    estimate_redo: "For the selected segments, the chosen step and the later ones will be produced again. These calls are not counted here.",
    quota_note: "For long books, the usage limits (quotas) of the subscriptions can run out. The translation does not stop then: requests to that tool wait, and continue by themselves when the limit resets. You see this below and on the Setup tab.",
    awake_note: "The computer is kept awake while the translation runs. On a laptop, keep the lid open and the computer plugged in; when the lid closes, the computer still sleeps and the translation stops.",
    awake_off: "Keeping awake is turned off (config.toml: keep_awake) or not supported on this computer. Make sure the computer does not sleep while the translation runs.",
    state_running: "Running", state_waiting_quota: "Waiting for a usage limit", state_finished: "Finished",
    state_failed: "Stopped with errors", state_stopped: "Stopped", state_interrupted: "Interrupted",
    hint_failed: "Fix the errors, then click \"Start\"; finished segments are kept and the run continues where it stopped.",
    hint_stopped: "Click \"Start\" to continue where it stopped.",
    hint_interrupted: "The run ended without a record. The computer may have slept or shut down, or the interface's terminal window was closed. Click \"Start\" to continue where it stopped.",
    current_stage: "Current step: {stage} · {done}/{total}",
    stage_failures: "{count} errors",
    elapsed: "Elapsed: {time}",
    remaining: "Remaining: {calls} model calls · about {time}",
    quota_history: "The usage limit was reached {count} times in this run.",
    awake_on: "The computer is kept awake.",
    failures_title: "Failed tasks (last {count})",
    run_target: "{language} translation · started {time}",
    hours_minutes: "{h} h {m} min", minutes_only: "{m} min", less_than_minute: "less than a minute",
    start_title: "Getting started",
    start_intro: "If you use the application for the first time, complete these steps in order. Installation needs no administrator rights; everything it needs (Node.js included) goes into the application's own folder.",
    step_install: "Install the tools", step_install_done: "{done}/{total} tools installed",
    install_missing: "Install missing tools", installing_all: "Installing… (this can take a few minutes)",
    step_signin: "Sign in to the tools in use", step_signin_done: "signed in to {done}/{total} tools",
    step_signin_hint: "Use the \"With … account\" button of each tool on the cards below.",
    step_book: "Add your first book", step_book_done: "{count} books", go_books: "Go to Books",
    all_done: "You are ready. Start a translation from the Books tab.",
    watching_signin: "Waiting for you to sign in; the status refreshes by itself every few seconds.",
    tab_workflow: "Workflow", edit_workflow: "Edit workflow",
    workflow_title: "Workflow",
    workflow_intro: "The steps are boxes joined from left to right; each step works on the text of the step before it. Drag a step type from the left onto an arrow between two boxes, or press the + on an arrow; add as many steps as you like. Reviews and reporting custom steps write findings; \u201cApply\u201d puts the findings into the text. A \u201cCheckpoint\u201d sends a segment with serious problems back to an earlier step you choose. Drag the boxes to change the order; click a box to set its options and models below. Changes are saved automatically.",
    canvas_label: "Workflow diagram", node_prep: "Preparation", prep_mark: "P",
    role_align: "Alignment", role_glossary: "Glossary", role_translate: "Translator", role_check: "Checker",
    insert_here: "Add a step here", drag_to_move: "Drag to change the order",
    move_earlier: "Move earlier", move_later: "Move later", pick_one: "one model",
    min_one_model: "This role needs at least one model.",
    node_locked: "Every translation starts with preparation and the first translation; these steps stay in place, their models can be changed.",
    palette_steps: "Steps", palette_steps_hint: "Drag onto the arrow between two boxes; a click adds it at the end.",
   
    palette_models: "Models", palette_models_hint: "You can drag a model card onto a role in a box. \u201cTest\u201d checks that the model answers.",
    visit_n: "visit {n}", flow_custom: "Custom step", flow_gate: "Checkpoint", stage_custom: "Custom step", stage_gate: "Checkpoint",
    node_review: "Review", role_gate: "Checker", role_editor: "Editor",
    step_desc_node_review: "The reviewers compare the text with the Turkish source sentence by sentence and write findings reports without seeing each other's. The text is unchanged; the next \u201cApply\u201d step works on the findings.",
    step_desc_node_apply: "Weighs all findings written since the last text (reviews, custom steps and checkpoints) against the source and applies the correct ones.",
    step_desc_node_source_check: "Compares the text with the source again from the start, without relying on the steps before, and corrects it.",
    step_desc_node_gate: "Looks for serious (critical or major) problems that remain. When it finds one, it sends the segment back to the earlier step you choose; its findings are applied in the next \u201cApply\u201d step. At the limit, the segment is marked in the report and goes on.",
    step_desc_custom_report: "Examines the text by your instructions and writes a findings report; the next \u201cApply\u201d step works on the findings.",
    step_desc_custom_rewrite: "Corrects the text by your instructions and records its changes.",
    problem_custom_title: "This custom step needs a name.",
    problem_unapplied: "The findings of this step are not applied: put an \u201cApply\u201d step after it, before any other step that changes the text.",
    problem_gate_target: "Choose the step this checkpoint sends back to (one before it, after the checkpoint before it).",
    flow_has_problems: "The workflow has {count} problems to fix (boxes marked red). Changes are not saved until they are fixed.",
    not_saved_problems: "Not saved: fix the boxes marked red",
    gate_note: "↺ to {step}, at most {max} times", loop_label: "↺ at most {max} times",
    type_round: "Review round", type_review: "Review", type_apply: "Apply", type_source_check: "Source check", type_custom: "Custom step", type_gate: "Checkpoint",
    type_hint_round: "A review and the step that applies it.", type_hint_review: "Reviewers report findings; the text is unchanged.",
    type_hint_apply: "Applies the findings before it.", type_hint_source_check: "Compares with the source again and corrects.",
    type_hint_custom: "A step with your own instructions.", type_hint_gate: "Sends a segment with serious problems back.",
    mode_report: "Reports findings", mode_rewrite: "Corrects the text", custom_title: "Name of the step", custom_mode: "What it does",
    custom_instructions: "Instructions", custom_instructions_hint: " — you can write in Turkish. Example: \u201cCheck the hadith references (Bukhari, Muslim…).\u201d",
    custom_default_title: "Custom step",
    gate_back_to: "When it finds problems, send back to", gate_choose: "Choose a step…", gate_max: "At most how many times",
    gate_help: "Each time it sends back, the steps in between run again for that segment (this uses quota and time). Checkpoints cannot overlap: sending back cannot go past the checkpoint before.",
   
    remove_step: "Remove step",
    confirm_remove_step: "Remove the step \"{step}\" from the workflow? Its output in books translated earlier is not deleted.",
    reviewers_label: "Reviewers", applier_label: "Applies the findings", max_steps: "At most {count} steps can be added.",
    flow_changed_note: "Adding or removing steps does not change segments translated earlier. The book screen shows the segments to produce again for the new order.",
    unsaved: "Not saved", preset: "Diagram assignment",
    effort_title: "Thinking level: a higher level works more carefully but more slowly, and uses more of the quota.",
    effort_default: "Default level", effort_low: "low", effort_medium: "medium", effort_high: "high",
    effort_xhigh: "extra high", effort_max: "maximum", effort_none: "this tool has no level option",
    default_model: "default model", add_model_placeholder: "model name (for example: opus)", add_other_model: "Add a model that is not in the list",
    models_loading: "Reading the model list…", models_none: "Cannot read the model list. The tool must be installed and must have run at least once.",
    remove: "Remove", parallel_tag: "parallel · up to 4 models",
    step_desc_align: "Finds each Turkish segment in the reference translations. Skipped when there is no reference.",
    step_desc_glossary: "Extracts religious terms and proper names; adds new terms to the shared glossary of the language.",
    step_desc_translate: "Makes the first translation with the Turkish source, the reference passages and the glossary.",
    step_desc_review: "The reviewers compare the text with the Turkish source sentence by sentence and write findings reports without seeing each other. Then one model weighs the findings against the source and applies the correct ones.",
    step_desc_source_check: "Compares the text with the source from the start, without relying on earlier steps, and corrects it.",
    step_desc_human: "The translation and the report go to the human translator; then a human editor reads it.",
    warn_self_review: "{step}: {model} reviews a text that it wrote. Put a different model on the review.",
    warn_self_check: "{step}: {model} wrote the text in the step before. An independent model is more reliable.",
    info_same_provider: "{step}: all reviewers are from the same company as the model that wrote the text. A model from a different company catches errors better.",
    warn_no_check: "There is no checking step after the translation. The translation will be delivered without review.",
    cannot_remove_used: "This model is used in a step; remove it from the step first.",
    model_name_invalid: "A model name must start with a letter or digit and can contain only letters, digits and . _ : -",
    upload_bad_type: "This file type is not supported. Supported: .docx, .epub, .md, .txt, .pdf",
    upload_bad_size: "The file is empty or too large (at most 300 MB).",
    max_reviewers: "This step takes at most 4 models.",
   
    export_label: "Export", fmt_md: "Markdown", fmt_docx: "Word", fmt_pdf: "PDF", fmt_html: "HTML",
    layout_open: "Layout settings", layout_title: "Export layout",
    layout_intro: "How the Word, PDF and HTML files of a book look. It applies to all books. The report always has the standard A4 layout.",
    layout_template: "Word template", layout_template_remove: "Remove the template",
    layout_template_none: "No template. The Word file is made with the settings below.",
    layout_template_set: "Uploaded template: {name}. The Word file uses the styles, page size, margins, headers and footers of this template. The text of the template is not used.",
    layout_template_hint: "Upload the .docx or .dotx template of your publishing house. The Word styles \"Heading 1–3\", \"Quote\", \"List Bullet\" and \"Footnote Text\" are used; the ones that the template lacks are added.",
    layout_settings: "Page and type",
    layout_scope_all: "Applies to Word, PDF and HTML.",
    layout_scope_pdf: "Applies to PDF and HTML. The Word file uses the template.",
    layout_page_size: "Page size", layout_font_size: "Font size (pt)", layout_line_spacing: "Line spacing",
    layout_margin_top: "Top margin (cm)", layout_margin_bottom: "Bottom margin (cm)", layout_margin_side: "Side margins (cm)",
    layout_font: "Font", layout_arabic_font: "Arabic font", layout_automatic: "Automatic",
    layout_justify: "Justify the paragraphs", layout_chapter_new_page: "Start each top-level chapter on a new page",
    layout_fonts_note: "The font must be installed. The PDF is made with the fonts of this computer; a Word file uses the fonts of the computer that opens it. Line spacing is as in Word: 1 is single, 1.15 is the Word default.",
    layout_defaults: "Default values", layout_pick_file: "Select a Word file first.", layout_confirm_remove: "Remove the Word template?",
    page_A4: "A4 (21 × 29.7 cm)", page_A5: "A5 (14.8 × 21 cm)", page_B5: "B5 (17.6 × 25 cm)", "page_13.5x21": "13.5 × 21 cm",
    page_16x24: "16 × 24 cm", page_Letter: "Letter (21.6 × 27.9 cm)",
    pdf_hint: "PDF: in the page that opens, choose \"Save as PDF\" in the print dialog.",
    step_install_hint: "The tools of the workflow (Claude Code, Codex, Antigravity) and the PDF reader are installed on this computer. If needed, Node.js is downloaded into the application's folder. No administrator rights are needed.",
    pdf_uses: "Reads PDF books. Not needed for .docx and .epub books.",
    first_book_title: "Add your first book",
    first_book_intro: "Give the book a short name. Then you upload the Turkish source and, if you have them, translations in related languages.",
    create_book: "Create book",
    step_source: "Turkish source", step_refs: "Reference translations", step_run: "Translation", step_result: "Result",
    locked_refs: "Upload the Turkish source first.", locked_run: "Complete the source and reference steps first.",
    locked_result: "When the translation is finished, you read and download it here.",
    summary_source_empty: "Upload the source file", summary_source: "{file} · {count} segments",
    summary_refs_check: "please check: {languages}", summary_refs_none: "No references used", summary_refs_optional: "Optional, improves accuracy",
    summary_running: "{language} · {stage} · {done}/{total}",
    summary_run_more: "Open to translate into another language", summary_run_ready: "Choose the target language and start",
    continue: "Continue", skip_refs: "Continue without references",
    progress_details: "Progress step by step",
    review_row: "{reviewer}: {issues} findings · no findings in {empty} of {segments} segments",
    review_quiet: "Wrote no findings in most segments. Check a few segments by hand.",
    review_missed: "Wrote no findings in {count} segments, but serious errors were found in them later: {segments}",
    review_attention: "Reviewer warning",
    stale_title: "Segments with changed inputs",
    stale_intro: "The glossary, the references or the instructions changed after these segments were produced. They still use the old inputs; they are produced again only when you ask for it.",
    stale_row: "From the {stage} step: segments {segments}", stale_fill: "Prepare to produce again",
    stale_filled: "The form is filled. Click Start to produce the segments again.",
    preview_hint: "Before you translate, check that the text is read correctly. In a PDF, look in particular at the footnotes, the headings and the Arabic âyat.",
    preview_prepare: "Split the text and preview", preview_open: "Show the split text", preview_title: "source preview · {count} segments",
    saving: "Saving…", saved_now: "Saved ✓",
    confirm_preset: "The steps and the models will go back to the diagram (Gemini, ChatGPT, Claude). Continue?",
    recover_title: "{model} failed ({stages})",
    recover_account: "{model} cannot be used with this account.",
    recover_intro: "The translation stopped. Continue with another model? The model you choose replaces {model} in every step of the workflow. Finished segments are kept.",
    recover_with: "Instead", recover_go: "Continue with this model", recover_retry: "Try the same model again",
    decide_quota_title: "{model} reached its usage limit",
    decide_quota_body: "The translation is waiting; it continues with {tool} by itself at {time}. If you do not want to wait, continue with another model or stop the translation.",
    decide_error_running: "The other segments go on, but these segments will not be finished. You can continue with another model, let it go on, or stop the translation.",
    decide_wait: "Let it wait", decide_keep: "Let it go on", decide_stop: "Stop",
    recover_switching: "Stopping the translation; it then starts with the new model…",
    stop_timeout: "The translation could not be stopped. Try again in a moment.",
    recover_done: "Workflow updated: {to} instead of {from}. The translation continues where it stopped.",
    prompt_title_rules: "Publishing rules", prompt_title_translate: "First translation", prompt_title_review: "Review report",
    prompt_title_revise: "Applying the findings", prompt_title_source_check: "Source check from the start", prompt_title_custom_report: "Custom step: reporting", prompt_title_custom_rewrite: "Custom step: correcting", prompt_title_gate: "Checkpoint",
    prompt_title_glossary: "Terminology glossary", prompt_title_align: "Reference alignment",
    all_steps: "All steps",
    step_prompts: "Step instructions", step_prompts_hint: "Advanced. They define the task and the answer format of each step.",
    rules_intro: "The rules of your publishing house. This whole document is given to the models in every step and takes priority. You can write it in Turkish. Write short, exact rules: each item says one thing; avoid vague words such as \"usually\" or \"if possible\".",
    prompt_used_in: "Used in: {steps}", prompt_unused: "No step of the current workflow uses this instruction.", not_in_flow: "Not in the workflow",
    prompt_custom_note: "The task of each custom step is written in the Workflow tab, in the panel of that step, and replaces {{instructions}} in this instruction. This instruction holds the common frame and the answer format of all custom steps.",
    ph_instructions: "the task of the custom step, written in the Workflow tab",
    prompts_apply: "A change applies to the segments processed after you save it. Segments processed earlier are shown on the Books screen as \"segments with changed inputs\", and you can produce them again from there.",
    ph_target_lang: "name of the target language", ph_source: "the Turkish source segment", ph_translation: "the translation that is checked or corrected",
    ph_glossary: "the glossary terms that occur in this segment", ph_references: "the matching passages of the reference translations",
    ph_ref_langs: "names of the reference languages", ph_context: "end of the previous segment (context only)",
    ph_issues: "the review findings (JSON)", ph_note_lang: "language of the model's explanations (the interface language)",
    ph_rules: "the Publishing rules document", ph_segment: "the Turkish segment to align", ph_window: "numbered paragraphs from the reference",
    ph_ref_lang: "language of the reference",
    setup_banner: "The tools are not ready yet. Complete the setup before you start a translation.", go_setup: "Go to Setup",
  },
};

const LANGS = ["tr", "en"];
let uiLang = (() => {
  try {
    const saved = localStorage.getItem("ui-lang");
    if (LANGS.includes(saved)) return saved;
  } catch { /* storage unavailable */ }
  return (navigator.language || "").toLowerCase().startsWith("tr") ? "tr" : "en";
})();

function L(key, vars = {}) {
  const text = I18N[uiLang][key] ?? I18N.en[key] ?? key;
  return text.replace(/\{(\w+)\}/g, (_, name) => (name in vars ? vars[name] : `{${name}}`));
}

// ---------- helpers ----------
const $ = (sel, root = document) => root.querySelector(sel);
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

function languageName(code) {
  try {
    const name = new Intl.DisplayNames([uiLang], { type: "language" }).of(code);
    if (name && name !== code) return name.charAt(0).toLocaleUpperCase(uiLang) + name.slice(1);
  } catch { /* unknown code */ }
  return (state.settings && state.settings.languages[code]) || code;
}

async function api(method, path, body) {
  const opts = { method, headers: { "X-Token": window.TOKEN, "X-Lang": uiLang } };
  if (body !== undefined) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  let res = await fetch(path, opts);
  if (res.status === 403 && await refreshToken()) {
    opts.headers["X-Token"] = window.TOKEN;
    res = await fetch(path, opts);
  }
  let data = {};
  try { data = await res.json(); } catch { /* empty answer */ }
  if (!res.ok) throw new Error(data.error || L("request_failed", { status: res.status }));
  return data;
}

// After the interface was restarted, the page of the earlier start has an old session key. The page reads the
// new key from its own address (the same origin), so that the work on the page goes on without a reload.
async function refreshToken() {
  try {
    const html = await (await fetch("/", { cache: "no-store" })).text();
    const m = html.match(/window\.TOKEN = "([^"]+)"/);
    if (!m || m[1] === window.TOKEN) return false;
    window.TOKEN = m[1];
    return true;
  } catch { return false; }
}

let toastTimer;
function toast(message, bad = false) {
  const el = $("#toast");
  el.textContent = message;
  el.className = "toast" + (bad ? " bad" : "");
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (el.hidden = true), bad ? 8000 : 4000);
}

async function act(button, fn) {
  if (button) button.disabled = true;
  try {
    const r = await fn();
    if (r && r.message) toast(r.message);
    return r;
  } catch (e) {
    toast(e.message, true);
  } finally {
    if (button) button.disabled = false;
  }
}

const PROVIDER_NAMES = { claude: "Claude", chatgpt: "ChatGPT", antigravity: "Antigravity", gemini: "Gemini" };
const providerName = (p) => PROVIDER_NAMES[p] || p;
// An assignment is "provider", "provider/model", either with "@effort" (the thinking level: "claude/opus@high").
const baseOf = (name) => String(name).split("@")[0];
const effortOf = (name) => String(name).split("@")[1] || "";
const providerOf = (name) => baseOf(name).split("/")[0];
const modelOf = (name) => baseOf(name).split("/").slice(1).join("/");
const providerEfforts = (provider) => state.settings?.providers?.[provider]?.efforts || [];
// The company that made a model: Antigravity runs Gemini models by default, and some Claude and GPT models.
function makerOf(name) {
  const provider = providerOf(name), model = modelOf(name);
  if (provider === "antigravity") return model.startsWith("claude") ? "claude" : model.startsWith("gpt") ? "chatgpt" : "gemini";
  return provider;
}
function modelLabel(name) {
  const provider = providerOf(name);
  const fallback = state.settings?.providers?.[provider]?.default_model;
  const effort = effortOf(name);
  return `${providerName(provider)} · ${modelOf(name) || fallback || L("default_model")}${effort ? ` · ${L("effort_" + effort)}` : ""}`;
}

function fmtTime(epoch) {
  const d = new Date(epoch * 1000);
  const time = d.toLocaleTimeString(uiLang, { hour: "2-digit", minute: "2-digit" });
  return d.toDateString() === new Date().toDateString() ? time : `${d.toLocaleDateString(uiLang)} ${time}`;
}

function fmtDuration(seconds) {
  const minutes = Math.round(seconds / 60);
  if (minutes < 1) return L("less_than_minute");
  const h = Math.floor(minutes / 60), m = minutes % 60;
  return h ? L("hours_minutes", { h, m }) : L("minutes_only", { m });
}

const callsText = (calls) => Object.entries(calls).filter(([, n]) => n)
  .map(([name, n]) => `${modelLabel(name)}: ${n.toLocaleString(uiLang)}`).join(" · ");
// The nodes of the workflow: the first translation, then the nodes of the flow, which the Workflow tab edits.
// A node can run again for a segment that a checkpoint sent back; that visit has a folder like "review1.2".
const nodeOf = (stage) => String(stage).split(".")[0];
function stageKind(stage) {
  const s = nodeOf(stage);
  if (s.startsWith("review")) return "review";
  if (s.startsWith("revise") || s.startsWith("apply") || s === "reconcile") return "apply";
  return ["source_check", "custom", "gate"].find((k) => s.startsWith(k)) || s;
}
const currentFlow = () => state.flow || state.settings?.flow || [];
const assignments = () => state.board || state.settings?.stages || {};
const nodeOptions = () => state.nodes || state.settings?.nodes || {};
// "report" (writes findings), "text" (writes a new text) or "gate" (a checkpoint).
function nodeRole(stage) {
  const k = stageKind(stage);
  if (k === "review") return "report";
  if (k === "custom") return nodeOptions()[nodeOf(stage)]?.mode === "report" ? "report" : "text";
  return k === "gate" ? "gate" : "text";
}
// The numbered steps: 1 is the first translation, then the nodes of the flow in order.
const numberedSteps = () => ["translate", ...currentFlow()];
function stageName(stage, long = false) {
  const node = nodeOf(stage);
  const visit = String(stage).includes(".") ? Number(String(stage).split(".")[1]) : 0;
  const kind = stageKind(stage);
  const n = numberedSteps().indexOf(node);
  const label = kind === "custom" ? nodeOptions()[node]?.title || L("flow_custom") : L((long ? "flow_" : "stage_") + kind);
  return (n >= 0 ? `${n + 1} · ` : "") + label + (visit ? ` (${L("visit_n", { n: visit })})` : "");
}
// The text that a node works on: the text of the last node before it that writes a text.
function textInput(stage) {
  const order = numberedSteps();
  return order.slice(0, order.indexOf(nodeOf(stage))).filter((s) => s === "translate" || nodeRole(s) === "text").pop();
}
const state = { settings: null, books: [], current: null, poll: null, prompts: [], prompt: null, toolPoll: null, tab: "setup",
  openStep: {}, skipRefs: new Set(), toolsReady: null, dismissed: new Set(), recoverChoice: {} };

// ---------- language and tabs ----------
function applyStaticTexts() {
  document.documentElement.lang = uiLang;
  document.title = L("app_title");
  document.querySelectorAll("[data-i18n]").forEach((el) => (el.textContent = L(el.dataset.i18n)));
  document.querySelectorAll("[data-i18n-html]").forEach((el) => (el.innerHTML = L(el.dataset.i18nHtml)));  // fixed texts from I18N only
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => (el.placeholder = L(el.dataset.i18nPlaceholder)));
  document.querySelectorAll("[data-ui-lang]").forEach((b) => b.classList.toggle("active", b.dataset.uiLang === uiLang));
}

document.querySelectorAll("[data-ui-lang]").forEach((b) => b.addEventListener("click", () => {
  uiLang = b.dataset.uiLang;
  try { localStorage.setItem("ui-lang", uiLang); } catch { /* storage unavailable */ }
  applyStaticTexts();
  if (state.tab === "workflow" && state.board) return renderBoard();
  if (state.tab === "prompts" && promptDirty()) return;  // keep the text that is being edited
  showTab(state.tab);
}));

function showTab(name) {
  if (state.tab === "prompts" && name !== "prompts" && promptDirty() && !confirm(L("confirm_discard"))) return;
  state.tab = name;
  document.querySelectorAll(".tab").forEach((t) => {
    t.classList.toggle("active", t.dataset.tab === name);
    t.setAttribute("aria-selected", String(t.dataset.tab === name));
  });
  document.querySelectorAll(".panel").forEach((p) => (p.hidden = p.id !== name));
  history.replaceState(null, "", "#" + name);
  if (name === "setup") loadTools();
  if (name === "workflow") loadBoard();
  if (name === "books") loadBooks();
  if (name === "prompts") loadPrompts();
}
document.querySelectorAll(".tab").forEach((t) => t.addEventListener("click", () => showTab(t.dataset.tab)));
document.querySelectorAll("[data-goto]").forEach((b) => b.addEventListener("click", () => showTab(b.dataset.goto)));

// ---------- setup ----------
async function loadTools() {
  clearTimeout(state.toolPoll);
  if (!$("#tools").children.length) $("#tools").innerHTML = `<p class="muted">${esc(L("loading"))}</p>`;
  let data;
  try {
    [data, state.settings] = await Promise.all([api("GET", "/api/tools"), api("GET", "/api/settings")]);
  } catch (e) {
    if (state.toolsBusy && state.tab === "setup") state.toolPoll = setTimeout(loadTools, 5000);  // keep watching an install
    else toast(e.message, true);
    return;
  }
  $("#onboarding").innerHTML = onboardingHtml(data);
  setToolsReady(toolsReady(data));
  $("#tools").innerHTML = data.tools.map((tool) => toolCard(tool, data.terminal)).join("");
  renderFlow();
  state.toolsBusy = data.tools.some((tool) => tool.job && tool.job.running) || Boolean(data.all_job && data.all_job.running);
  // Keep refreshing while something installs, and for two minutes after a sign-in window was opened.
  const watchingSignIn = state.signInUntil && Date.now() < state.signInUntil && data.tools.some((tool) => tool.installed && !tool.signed_in);
  if (state.toolsBusy) state.toolPoll = setTimeout(loadTools, 2500);
  else if (watchingSignIn) state.toolPoll = setTimeout(loadTools, 4000);
}

function onboardingHtml(data) {
  const required = data.tools.filter((tool) => tool.required);  // the workflow's tools and the PDF reader
  const total = required.length;
  const installed = required.filter((tool) => tool.installed).length;
  const needed = neededTools(data);
  const signedIn = needed.filter((tool) => tool.signed_in).length;
  const job = data.all_job;
  const installing = Boolean(job && job.running);
  const steps = [
    { done: installed === total && !installing, title: L("step_install"), detail: L("step_install_done", { done: installed, total }),
      body: `<p class="small muted">${esc(L("step_install_hint"))}</p>
        <div class="row"><button type="button" class="btn primary" data-act="install-missing" ${installing ? "disabled" : ""}>${esc(L(installing ? "installing_all" : "install_missing"))}</button></div>
        ${job ? `<pre class="log">${esc(job.log.slice(-4000))}</pre>` : ""}` },
    { done: signedIn === needed.length, title: L("step_signin"), detail: L("step_signin_done", { done: signedIn, total: needed.length }),
      body: `<p class="small muted">${esc(L(state.signInUntil && Date.now() < state.signInUntil ? "watching_signin" : "step_signin_hint"))}</p>` },
    { done: data.books > 0, title: L("step_book"), detail: L("step_book_done", { count: data.books }),
      body: `<div class="row"><button type="button" class="btn primary" data-goto-tab="books">${esc(L("go_books"))}</button></div>` },
  ];
  const current = steps.findIndex((st) => !st.done);
  if (current === -1) {
    return `<div class="ready-line"><span class="jnode done" aria-hidden="true">✓</span><div><b>${esc(L("all_done"))}</b></div>
      <button type="button" class="btn primary" data-goto-tab="books">${esc(L("go_books"))}</button></div>`;
  }
  return `<h3>${esc(L("start_title"))}</h3>
    <p class="muted">${esc(L("start_intro"))}</p>
    <ol class="onboard">${steps.map((st, i) => `
      <li class="onboard-step ${st.done ? "done" : ""} ${i === current ? "current" : ""} ${i > current ? "later" : ""}">
        <span class="check" aria-hidden="true">${st.done ? "✓" : i + 1}</span>
        <div class="stack"><div><b>${esc(st.title)}</b> <span class="muted small">${esc(st.detail)}</span></div>
          ${i === current ? st.body : ""}</div>
      </li>`).join("")}</ol>`;
}

$("#onboarding").addEventListener("click", async (ev) => {
  const b = ev.target.closest("button");
  if (!b) return;
  if (b.dataset.gotoTab) return showTab(b.dataset.gotoTab);
  if (b.dataset.act === "install-missing") {
    await act(b, () => api("POST", "/api/tools/install-missing"));
    loadTools();
  }
});

function toolCard(tool, terminal) {
  const installed = tool.installed
    ? `<span class="badge good">${esc(L("installed"))}</span>`
    : `<span class="badge bad">${esc(L("not_installed"))}</span>`;
  const signIn = !tool.installed || !tool.provider ? "" : tool.signed_in
    ? `<span class="badge good">${esc(L("signed_in"))}${tool.sign_in_info ? " · " + esc(tool.sign_in_info) : ""}</span>`
    : `<span class="badge warn">${esc(L("not_signed_in"))}</span>`;
  const job = tool.job;
  const running = job && job.running;
  const actions = [];
  if (!tool.installed || (job && !running && job.code !== 0)) {
    actions.push(`<button type="button" class="btn primary" data-act="install" data-id="${esc(tool.id)}" ${running ? "disabled" : ""}>${esc(L(running ? "installing" : "install"))}</button>`);
  }
  if (tool.installed && tool.provider) {
    const main = tool.signed_in ? "" : "primary";
    if (tool.id === "gemini") {
      actions.push(`<button type="button" class="btn ${main}" data-act="login" data-method="google" data-id="${esc(tool.id)}">${esc(L("with_google"))}</button>`);
    } else {
      const label = { codex: "with_chatgpt", antigravity: "with_google" }[tool.id] || "with_claude";
      actions.push(`<button type="button" class="btn ${main}" data-act="login" data-method="terminal" data-id="${esc(tool.id)}" ${terminal ? "" : "disabled"}>${esc(L(label))}</button>`);
    }
    if (["codex", "gemini"].includes(tool.id)) actions.push(`<button type="button" class="btn" data-act="key" data-id="${esc(tool.id)}">${esc(L("with_key"))}</button>`);
    if (tool.signed_in) actions.push(`<button type="button" class="btn" data-act="test" data-id="${esc(tool.id)}">${esc(L("test"))}</button>`);
  }
  const uses = !tool.provider ? L("pdf_uses") : tool.stages.length ? L("used_in", { stages: tool.stages.map((s) => stageName(s)).join(", ") }) : L("not_used");
  return `
    <article class="card tool" data-id="${esc(tool.id)}">
      <div class="tool-head"><h3>${esc(tool.name)}</h3><span class="muted small">${esc(tool.version)}</span></div>
      <div class="badges">${installed}${signIn}</div>
      <div class="uses">${esc(uses)}</div>
      <div class="small muted">${esc(tool.requirements)}</div>
      ${tool.installed && !tool.signed_in && tool.sign_in_help ? `<div class="small">${esc(tool.sign_in_help)}</div>` : ""}
      ${quotaLine(tool.quota)}
      ${!terminal && tool.installed && !tool.signed_in ? `<p class="small muted">${esc(L("run_command", { command: tool.login_command }))}</p>` : ""}
      <form class="keyform" data-id="${esc(tool.id)}" hidden>
        <input type="password" placeholder="${esc(L("api_key"))}" autocomplete="off" required>
        <button type="submit" class="btn primary">${esc(L("save"))}</button>
      </form>
      ${job ? `<pre class="log">${esc(job.log.slice(-4000))}</pre>` : ""}
      <div class="actions">${actions.join("")}</div>
    </article>`;
}

function quotaLine(quota) {
  if (!quota || !quota.since) return "";
  const active = quota.until > Date.now() / 1000 && !(quota.cleared > quota.since);
  return active
    ? `<div class="notice warn small">${esc(L("quota_now", { time: fmtTime(quota.until) }))}</div>`
    : `<div class="small muted">${esc(L("quota_last", { time: fmtTime(quota.since) }))}</div>`;
}

$("#tools").addEventListener("click", async (ev) => {
  const b = ev.target.closest("button[data-act]");
  if (!b) return;
  const id = encodeURIComponent(b.dataset.id);
  if (b.dataset.act === "install") {
    await act(b, () => api("POST", `/api/tools/${id}/install`));
    loadTools();
  } else if (b.dataset.act === "login") {
    const r = await act(b, () => api("POST", `/api/tools/${id}/login`, { method: b.dataset.method }));
    if (r) state.signInUntil = Date.now() + 2 * 60 * 1000;
    loadTools();
  } else if (b.dataset.act === "key") {
    const form = b.closest(".tool").querySelector(".keyform");
    form.hidden = !form.hidden;
    if (!form.hidden) $("input", form).focus();
  } else if (b.dataset.act === "test") {
    b.textContent = L("testing");
    await act(b, () => api("POST", `/api/tools/${id}/test`));
    b.textContent = L("test");
  }
});
$("#tools").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const form = ev.target;
  const input = $("input", form);
  await act($("button", form), () => api("POST", `/api/tools/${encodeURIComponent(form.dataset.id)}/login`, { method: "key", key: input.value }));
  input.value = "";
  loadTools();
});
$("#tools-refresh").addEventListener("click", loadTools);

function renderFlow() {
  if (!state.settings) return;
  const stages = state.settings.stages;
  const step = (stage) => {
    const providers = stages[stage] || [];
    return `<div class="step ${providers.length === 1 ? esc(providerOf(providers[0])) : ""}"><b>${esc(stageName(stage, true))}</b>${providers.map((p) => esc(modelLabel(p))).join(" + ")}</div>`;
  };
  $("#flow").innerHTML = ["align", "glossary", ...numberedSteps()].map(step).join("")
    + `<div class="step human"><b>${numberedSteps().length + 1} · ${esc(L("human_step"))}</b>${esc(L("human_who"))}</div>`;
}

// All tools are installed. A sign-in is required only for the tools that the workflow uses.
const neededTools = (data) => data.tools.filter((tool) => tool.stages.length);
const toolsReady = (data) => data.tools.every((tool) => !tool.required || tool.installed) && neededTools(data).every((tool) => tool.signed_in);

function setToolsReady(ready) {
  state.toolsReady = ready;
  try { localStorage.setItem("setup-ready", ready ? "1" : ""); } catch { /* storage unavailable */ }
  $("#setup-banner").hidden = ready;
}

// ---------- books ----------
async function loadBooks(soft = false) {
  clearTimeout(state.poll);
  try {
    [state.books, state.settings] = await Promise.all([api("GET", "/api/books"), api("GET", "/api/settings")]);
  } catch (e) {
    // While a run is being watched, a failed request (sleep, network) must not end the refresh: try again.
    if (soft && state.tab === "books") state.poll = setTimeout(() => loadBooks(true), 5000);
    else toast(e.message, true);
    return;
  }
  if (!state.current && state.books.length) state.current = state.books[0].name;
  renderBookList();
  const book = state.books.find((b) => b.name === state.current);
  const root = $("#book");
  if (soft && book && root.dataset.book === book.name && root.dataset.sig === bookSignature(book)) {
    // Only the live parts change: the form keeps its values, open sections and chosen files.
    const parts = { refs: refsHtml, live: liveHtml, results: resultsHtml };
    for (const [role, html] of Object.entries(parts)) {
      const el = $(`[data-role="${role}"]`, root);
      // A drop-down that the user is choosing from is not replaced under the pointer.
      if (el && !(el.contains(document.activeElement) && document.activeElement.tagName === "SELECT")) el.innerHTML = html(book);
    }
    return loadLog(book);
  }
  renderBook();
}

const bookSignature = (b) => JSON.stringify([b.running, b.prepared, b.source, b.references, b.outputs, b.run?.state,
  Object.keys(b.status.languages), state.skipRefs.has(b.name)]);

function renderBookList() {
  $(".books").classList.toggle("no-books", !state.books.length);
  $("#book-list").innerHTML = state.books.length
    ? state.books.map((b) => `<li><button type="button" data-book="${esc(b.name)}" class="${b.name === state.current ? "active" : ""}">
        <span>${esc(b.name)}</span>${b.running ? `<span class="dot" title="${esc(L("running"))}"></span>` : ""}</button></li>`).join("")
    : `<li class="muted small">${esc(L("no_books"))}</li>`;
}
$("#book-list").addEventListener("click", (ev) => {
  const b = ev.target.closest("button[data-book]");
  if (!b) return;
  state.current = b.dataset.book;
  renderBookList();
  renderBook();
});
$("#new-book").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const input = $("#new-book-name");
  const r = await act($("button", ev.target), () => api("POST", "/api/books", { name: input.value }));
  if (r) { input.value = ""; state.current = r.name; loadBooks(); }
});

function langOptions(exclude = [], selected = "") {
  const options = Object.keys(state.settings.languages)
    .filter((code) => !exclude.includes(code))
    .map((code) => [code, languageName(code)])
    .sort((a, b) => a[1].localeCompare(b[1], uiLang));
  return `<option value="">${esc(L("choose_language"))}</option>` + options
    .map(([code, name]) => `<option value="${esc(code)}" ${code === selected ? "selected" : ""}>${esc(name)} (${esc(code)})</option>`)
    .join("");
}

// The book screen is a path of four steps. Only one step is open: the next thing to do, or the step the user opened.
// Finished steps show a one-line summary; steps that cannot start yet are locked and say what comes first.
function bookSteps(book) {
  const hasSource = book.source.length > 0;
  const started = Boolean(book.run) || Object.keys(book.status.languages).length > 0;
  const refsDone = hasSource && (book.references.length > 0 || state.skipRefs.has(book.name) || started);
  const hasOutput = book.outputs.length > 0;
  const steps = [
    { id: "source", done: hasSource, locked: false },
    { id: "refs", done: refsDone, locked: !hasSource },
    { id: "run", done: hasOutput && !book.running, locked: !refsDone },
    { id: "result", done: false, locked: !hasOutput },
  ];
  // A failed run stays open: it shows what went wrong and how to continue.
  const current = book.running || book.run?.state === "failed" ? "run" : (steps.find((s) => !s.done && !s.locked) || steps[3]).id;
  return { steps, current };
}

function renderBook(keepOpen = false) {
  clearTimeout(state.poll);
  const book = state.books.find((b) => b.name === state.current);
  const root = $("#book");
  if (!book) {
    root.dataset.book = "";
    root.innerHTML = state.books.length ? `<div class="empty">${esc(L("pick_book"))}</div>` : firstBookHtml();
    return;
  }
  const keep = root.dataset.book === book.name ? readRunForm() : null;
  if (!keepOpen) delete state.openStep[book.name];
  root.dataset.book = book.name;
  root.dataset.sig = bookSignature(book);

  const { steps, current } = bookSteps(book);
  const open = state.openStep[book.name] || current;
  const body = { source: sourceStepHtml, refs: refsStepHtml, run: (b) => runStepHtml(b, keep), result: resultStepHtml };
  root.innerHTML = `
    <div class="book-title">
      <h2>${esc(book.name)}</h2>
      ${book.running ? `<span class="badge good">${esc(L("running"))}</span>` : ""}
    </div>
    <ol class="journey">${steps.map((s, i) => {
      const isOpen = s.id === open && !s.locked;
      const doubtful = s.id === "refs" && book.references.some((r) => r.warnings?.length);
      const cls = [s.done ? "done" : "", s.id === current ? "current" : "", s.locked ? "locked" : "", isOpen ? "open" : "",
        doubtful ? "doubtful" : ""].join(" ");
      return `<li class="jstep ${cls}" data-step="${s.id}">
          <span class="jnode" aria-hidden="true">${doubtful ? "!" : s.done ? "✓" : i + 1}</span>
          <div class="jcard">
            <button type="button" class="jhead" data-act="open-step" data-step="${s.id}" ${s.locked ? "disabled" : ""} aria-expanded="${isOpen}">
              <span class="jtitle">${esc(L("step_" + s.id))}</span>
              <span class="jsummary">${esc(stepSummary(book, s))}</span>
            </button>
            ${isOpen ? `<div class="jbody">${body[s.id](book)}</div>` : ""}
          </div>
        </li>`;
    }).join("")}</ol>
    <details class="logbox">
      <summary>${esc(L("log"))} <span class="muted small" data-role="log-file"></span></summary>
      <pre class="log" data-role="log">${esc(L("loading"))}</pre>
    </details>
    <section class="timeline" data-role="timeline" hidden></section>`;
  loadLog(book);
  if (open === "run" && !book.running) loadEstimate(book);
}

function firstBookHtml() {
  return `<section class="welcome">
      <h2>${esc(L("first_book_title"))}</h2>
      <p>${esc(L("first_book_intro"))}</p>
      <form id="first-book" class="row">
        <input name="name" placeholder="${esc(L("new_book_placeholder"))}" aria-label="${esc(L("new_book"))}" required>
        <button type="submit" class="btn primary">${esc(L("create_book"))}</button>
      </form>
    </section>`;
}

function stepSummary(book, step) {
  const status = book.status;
  if (step.locked) return L("locked_" + step.id);
  switch (step.id) {
    case "source":
      if (!book.source.length) return L("summary_source_empty");
      return book.prepared ? L("summary_source", { file: book.source[0], count: status.segments }) : book.source[0];
    case "refs": {
      if (!book.references.length) return L(step.done ? "summary_refs_none" : "summary_refs_optional");
      const doubtful = book.references.filter((r) => r.warnings?.length).map((r) => languageName(r.lang));
      const names = book.references.map((r) => languageName(r.lang)).join(", ");
      return doubtful.length ? `${names} · ⚠ ${L("summary_refs_check", { languages: doubtful.join(", ") })}` : names;
    }
    case "run":
      if (book.running && book.run) {
        const st = book.run.stages?.[book.run.stage];
        return L("summary_running", { language: languageName(book.run.target), stage: book.run.stage ? stageName(book.run.stage) : "…", done: st?.done ?? 0, total: st?.total ?? 0 });
      }
      if (book.run && ["failed", "stopped", "interrupted", "waiting_quota"].includes(book.run.state)) return L("state_" + book.run.state);
      return book.outputs.length ? L("summary_run_more") : L("summary_run_ready");
    case "result":
      return book.outputs.map(languageName).join(", ");
  }
  return "";
}

function sourceStepHtml(book) {
  const status = book.status;
  const file = book.source.length
    ? `<div class="file-row"><span class="file-name">${esc(book.source.join(", "))}</span>
         ${book.prepared ? `<span class="badge good">${esc(L("prepared", { count: status.segments }))}</span>` : `<span class="badge">${esc(L("not_prepared"))}</span>`}</div>`
    : "";
  const action = book.prepared
    ? `<div class="row"><span class="muted small">${esc(L("reset_hint"))}</span>
        <button type="button" class="btn small danger" data-act="reset" ${book.running ? "disabled" : ""}>${esc(L("reset_work"))}</button></div>`
    : uploader("source");
  const preview = book.source.length ? `<div class="row preview-row"><span class="muted small">${esc(L("preview_hint"))}</span>
      <button type="button" class="btn small" data-act="preview">${esc(L(book.prepared ? "preview_open" : "preview_prepare"))}</button></div>` : "";
  return `<p class="muted">${esc(L("source_intro"))}</p>${file}${preview}${action}
    ${book.source.length && !book.prepared ? `<div class="row next"><button type="button" class="btn primary" data-act="open-step" data-step="refs">${esc(L("continue"))}</button></div>` : ""}`;
}

function refsStepHtml(book) {
  return `<p>${esc(L("refs_intro"))}</p>
    <details class="refs-help"><summary>${esc(L("refs_more"))}</summary>
      <p class="small">${esc(L("refs_how"))}</p><p class="small">${esc(L("refs_which"))}</p></details>
    <div data-role="refs">${refsHtml(book)}</div>
    ${uploader("references", `<select data-role="ref-lang" aria-label="${esc(L("reference_language"))}">${langOptions(["tr"])}</select>`)}
    <details>
      <summary>${esc(L("add_language"))}</summary>
      <form class="row" data-form="language">
        <input name="code" placeholder="${esc(L("language_code"))}" maxlength="12" required style="max-width:160px">
        <input name="name" placeholder="${esc(L("language_name"))}" required>
        <button type="submit" class="btn">${esc(L("add_language_btn"))}</button>
      </form>
    </details>
    <div class="row next">
      <button type="button" class="btn primary" data-act="refs-done">${esc(L(book.references.length ? "continue" : "skip_refs"))}</button>
    </div>`;
}

function refsHtml(book) {
  const status = book.status;
  return book.references.length
    ? book.references.map((r) => `
        <div class="file-row">
          <span><b>${esc(languageName(r.lang))}</b> <span class="muted small">${esc(r.file)}</span></span>
          <span class="row">
            ${status.segments ? `<span class="badge ${status.alignment[r.lang]?.aligned ? "good" : ""}">${esc(L("aligned", { done: status.alignment[r.lang]?.aligned || 0, total: status.segments }))}</span>` : ""}
            <button type="button" class="btn small danger" data-act="delete-ref" data-lang="${esc(r.lang)}" ${book.running ? "disabled" : ""}>${esc(L("delete"))}</button>
          </span>
        </div>
        ${(r.warnings || []).map((w) => `<div class="notice warn small">${esc(w)}</div>`).join("")}
        ${status.alignment[r.lang]?.missing?.length
          ? `<div class="notice warn small">${esc(L("unaligned", { segments: status.alignment[r.lang].missing.map(Number).join(", ") }))}</div>` : ""}`).join("")
    : `<p class="muted small">${esc(L("no_refs"))}</p>`;
}

function runStepHtml(book, keep) {
  if (book.running) {
    return `<div data-role="live">${liveHtml(book)}</div>
      <div class="row next"><button type="button" class="btn danger" data-act="stop">${esc(L("stop"))}</button></div>`;
  }
  return `<div data-role="live">${liveHtml(book)}</div>
    <p class="muted">${esc(L("run_intro"))}</p>
    <form data-form="run">
      <div class="run-grid">
        <div class="stack"><label for="run-lang">${esc(L("target_language"))}</label><select id="run-lang" name="lang" required>${langOptions(["tr"], keep?.lang || "")}</select></div>
        <div class="stack"><label for="run-segments">${esc(L("segments"))}</label><input id="run-segments" name="segments" placeholder="${esc(L("segments_placeholder"))}" value="${esc(keep?.segments || "")}"></div>
      </div>
      ${book.references.length ? `<fieldset class="stack plain"><legend>${esc(L("use_refs"))}</legend>
        <div class="checks">${book.references.map((r) => `
          <label><input type="checkbox" name="ref" value="${esc(r.lang)}" ${!keep || keep.refs.includes(r.lang) ? "checked" : ""}> ${esc(languageName(r.lang))}</label>`).join("")}</div>
      </fieldset>` : ""}
      <details data-role="advanced" ${keep?.advanced ? "open" : ""}>
        <summary>${esc(L("advanced"))}</summary>
        <div class="run-grid">
          <div class="stack"><label for="run-until">${esc(L("until"))}</label>
            <select id="run-until" name="until">${state.settings.stage_order.map((s) => `<option value="${esc(s)}" ${s === (keep?.until || "assemble") ? "selected" : ""}>${esc(stageName(s))}</option>`).join("")}</select></div>
          <div class="stack"><label for="run-redo">${esc(L("redo"))}</label>
            <select id="run-redo" name="redo"><option value="">—</option>${state.settings.stage_order.slice(1, -1).map((s) => `<option value="${esc(s)}" ${s === keep?.redo ? "selected" : ""}>${esc(stageName(s))}</option>`).join("")}</select></div>
        </div>
        <p class="muted small">${L("first_book_hint")}</p>
      </details>
      <div class="estimate" data-role="estimate"></div>
      <div class="row next"><button type="submit" class="btn primary">${esc(L("start"))}</button></div>
    </form>`;
}

function resultStepHtml(book) {
  return `<div data-role="results">${resultsHtml(book)}</div>`;
}

function resultsHtml(book) {
  return book.outputs.map((lang) => `
    <div class="result">
      <div class="row result-head">
        <h3>${esc(languageName(lang))}</h3>
        <span class="row">
          <button type="button" class="btn small primary" data-act="read" data-lang="${esc(lang)}" data-kind="translation">${esc(L("read_translation"))}</button>
          <button type="button" class="btn small" data-act="read" data-lang="${esc(lang)}" data-kind="report">${esc(L("read_report"))}</button>
        </span>
      </div>
      ${exportLinks(book.name, lang)}
      ${reviewWarnings(book.status.languages[lang])}
      <details><summary>${esc(L("progress_details"))}</summary>${railHtml(book, lang)}</details>
    </div>`).join("");
}

// Live part of the run step: the run status and the path of the stages for the language being translated.
function liveHtml(book) {
  const lang = book.run?.target;
  const showRail = book.running && lang && book.status.languages[lang];
  return `${runPanel(book)}${showRail ? railHtml(book, lang) : ""}`;
}

function railHtml(book, lang) {
  const info = book.status.languages[lang];
  if (!info) return "";
  const active = book.running && book.run?.target === lang ? book.run.stage : null;
  return `<ol class="rail">${Object.entries(info.stages).map(([stage, [n, m]]) => {
    const done = m > 0 && n >= m;
    const cls = done ? "done" : stage === active ? "active" : n ? "partial" : "";
    const providers = state.settings.stages[stage] || [];
    const reviews = (info.reviews || []).filter((r) => r.stage === stage);
    return `<li class="rail-step ${cls}">
        <span class="node" aria-hidden="true"></span>
        <div class="rail-body">
          <div class="rail-head"><span>${esc(stageName(stage))}</span><span class="muted small">${providers.map((p) => esc(modelLabel(p))).join(" + ")}</span><span class="count">${n}/${m}</span></div>
          <div class="track"><div class="fill" style="width:${m ? Math.round((100 * n) / m) : 0}%"></div></div>
          ${reviews.map((r) => reviewLine(r)).join("")}
        </div>
      </li>`;
  }).join("")}</ol>`;
}

function reviewLine(r, withStage = false) {
  const flagged = r.quiet || r.missed.length;
  return `<div class="review-line ${flagged ? "warn-text" : "muted"}">
      ${withStage ? `<b>${esc(stageName(r.stage))}</b> · ` : ""}${esc(L("review_row", { reviewer: modelLabel(r.reviewer), issues: r.issues, empty: r.empty, segments: r.segments }))}
      ${r.quiet ? `<div>${esc(L("review_quiet"))}</div>` : ""}
      ${r.missed.length ? `<div>${esc(L("review_missed", { count: r.missed.length, segments: r.missed.map(Number).join(", ") }))}</div>` : ""}
    </div>`;
}

function reviewWarnings(info) {
  const flagged = (info?.reviews || []).filter((r) => r.quiet || r.missed.length);
  if (!flagged.length) return "";
  return `<div class="notice warn small"><b>${esc(L("review_attention"))}</b>${flagged.map((r) => reviewLine(r, true)).join("")}</div>`;
}

function runPanel(book) {
  const run = book.run;
  if (!run) return "";
  const runState = run.state;
  const tone = { running: "good", waiting_quota: "warn", finished: "good", failed: "bad", stopped: "", interrupted: "warn" }[runState] ?? "";
  const lines = [];
  const end = run.finished || run.now;
  if (book.running && run.stage && run.stages[run.stage]) {
    const st = run.stages[run.stage];
    lines.push(`<div>${esc(L("current_stage", { stage: stageName(run.stage), done: st.done, total: st.total }))}${st.failed ? ` <span class="badge bad">${esc(L("stage_failures", { count: st.failed }))}</span>` : ""}</div>`);
  }
  lines.push(`<div class="muted small">${esc(L("elapsed", { time: fmtDuration(end - run.started) }))}</div>`);
  if (book.running && run.remaining) {
    lines.push(`<div>${esc(L("remaining", { calls: run.remaining.total_calls.toLocaleString(uiLang), time: fmtDuration(run.remaining.seconds) }))}</div>`);
    if (run.remaining.total_calls) lines.push(`<div class="muted small">${esc(callsText(run.remaining.calls))}</div>`);
  }
  if ((run.quota_events || []).length) lines.push(`<div class="muted small">${esc(L("quota_history", { count: run.quota_events.length }))}</div>`);
  if (book.running) lines.push(`<div class="small ${run.awake ? "muted" : "warn-text"}">${esc(L(run.awake ? "awake_on" : "awake_off"))}</div>`);
  if (run.error) lines.push(`<div class="notice bad">${esc(run.error)}</div>`);
  lines.push(decisionHtml(book));
  if (!book.running && ["failed", "stopped", "interrupted"].includes(runState)) lines.push(`<p class="small">${esc(L("hint_" + runState))}</p>`);
  const failures = run.failures || [];
  if (failures.length) {
    const shown = failures.slice(-10);
    lines.push(`<details ${runState === "failed" ? "open" : ""}><summary>${esc(L("failures_title", { count: shown.length }))}</summary>
      <ul class="failures">${shown.map((f) => `<li><b>${esc(stageName(f.stage))} · ${esc(f.task)}</b> — ${esc(f.error)}</li>`).join("")}</ul></details>`);
  }
  return `<div class="run-panel">
      <div class="row run-panel-head">
        <span>${esc(L("run_target", { language: languageName(run.target), time: fmtTime(run.started) }))}</span>
        <span class="badge ${tone}">${esc(L("state_" + runState))}</span>
      </div>
      <div class="stack">${lines.join("")}</div>
    </div>`;
}

// The models whose calls failed in a run, with their steps. A review task is named "<segment> (<model>)".
function failedModels(run) {
  const out = new Map();
  for (const f of run.failures || []) {
    const m = nodeRole(f.stage) !== "text" ? /\(([^()]+)\)\s*$/.exec(f.task) : null;
    const name = m ? m[1] : (state.settings?.stages[f.stage] || [])[0];
    if (!name) continue;
    const item = out.get(name) || { name, stages: new Set(), account: false };
    item.stages.add(f.stage);
    item.account ||= /IneligibleTierError|no longer supported/i.test(f.error);
    out.set(name, item);
  }
  return [...out.values()];
}

// A model reached its usage limit or failed: the user decides whether the translation goes on, and how.
//   while it runs: continue with another model, let it go on (wait for the limit / leave the failed segments), or stop;
//   after it failed: continue with another model, or try the same model again.
function decisionHtml(book) {
  const run = book.run;
  const running = book.running;
  if (!running && run.state !== "failed") return "";
  const used = new Set(Object.values(state.settings?.stages || {}).flat());
  const items = Object.entries(running ? run.quota || {} : {}).map(([name, q]) => ({ name, quota: q, whole: true, stages: new Set() }));
  for (const f of failedModels(run)) {
    if (!items.some((i) => i.name === f.name)) items.push({ ...f, whole: f.account });
  }
  return items.filter((f) => used.has(f.name) && !state.dismissed.has(`${book.name}:${run.started}:${f.name}`)).map((f) => {
    const provider = providerOf(f.name);
    // A usage limit or a refused account applies to the whole tool: none of its models can be used.
    const skip = f.whole ? [provider, ...providerModels(provider).map((m) => `${provider}/${m}`)] : [f.name];
    const chosen = state.recoverChoice[f.name];
    const choice = chosen && !skip.includes(chosen) ? chosen : Object.keys(state.settings.providers).find((p) => p !== provider) || "";
    const model = modelLabel(f.name), tool = providerName(provider);
    const title = f.quota ? L("decide_quota_title", { model })
      : L("recover_title", { model, stages: [...f.stages].map((s) => stageName(s)).join(", ") });
    const body = f.quota ? L("decide_quota_body", { time: fmtTime(f.quota.until), tool })
      : (f.account ? `${L("recover_account", { model: tool })} ` : "") + L(running ? "decide_error_running" : "recover_intro", { model: f.whole ? tool : model });
    const keep = running
      ? `<button type="button" class="btn small" data-act="keep" data-name="${esc(f.name)}">${esc(L(f.quota ? "decide_wait" : "decide_keep"))}</button>
         <button type="button" class="btn small danger" data-act="stop">${esc(L("decide_stop"))}</button>`
      : f.account ? "" : `<button type="button" class="btn small" data-act="retry">${esc(L("recover_retry"))}</button>`;
    return `<div class="notice warn recover" data-from="${esc(f.name)}" data-whole="${f.whole ? 1 : 0}">
        <b>${esc(title)}</b>
        <div>${esc(body)}</div>
        ${f.quota?.message ? `<div class="small muted">${esc(f.quota.message)}</div>` : ""}
        <div class="row recover-actions">
          <label class="small">${esc(L("recover_with"))} <select data-role="recover-to">${modelOptions(choice, skip)}</select></label>
          <button type="button" class="btn primary small" data-act="recover">${esc(L("recover_go"))}</button>
          ${keep}
        </div>
      </div>`;
  }).join("");
}

// Waits until a stopped run has ended (its lock is free), so that it can be started again.
async function waitStopped(book) {
  for (let i = 0; i < 120; i++) {
    if (!(await api("GET", `/api/books/${encodeURIComponent(book)}/log`)).running) return;
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error(L("stop_timeout"));
}

// Starts the book again with the settings of its last run; finished segments are kept.
function restartRun(book) {
  const run = state.books.find((x) => x.name === book).run;
  return api("POST", `/api/books/${encodeURIComponent(book)}/run`,
    { lang: run.target, references: run.refs, segments: run.segments || "",
      until: state.settings.stage_order.includes(run.until) ? run.until : "assemble" });
}

// "0001", "0002", "0003", "0007" → "1-3,7" (the form of the segments field)
function segmentRanges(ids) {
  const out = [];
  for (const n of ids.map(Number)) {
    const last = out[out.length - 1];
    if (last && n === last[1] + 1) last[1] = n; else out.push([n, n]);
  }
  return out.map(([a, b]) => (a === b ? `${a}` : `${a}-${b}`)).join(",");
}

// Finished segments whose glossary rows, references or instructions changed after they were produced.
function staleHtml(stale) {
  const rows = Object.entries(stale || {});
  if (!rows.length) return "";
  return `<div class="notice warn small"><b>${esc(L("stale_title"))}</b>
      <div>${esc(L("stale_intro"))}</div>
      ${rows.map(([stage, ids]) => `<div class="row stale-row"><span>${esc(L("stale_row", { stage: stageName(stage), segments: segmentRanges(ids) }))}</span>
        <button type="button" class="btn small" data-act="fill-redo" data-stage="${esc(stage)}" data-segments="${esc(segmentRanges(ids))}">${esc(L("stale_fill"))}</button></div>`).join("")}
    </div>`;
}

let estimateTimer;
function loadEstimate(book) {
  clearTimeout(estimateTimer);
  estimateTimer = setTimeout(async () => {
    const box = $('[data-role="estimate"]');
    const form = readRunForm();
    if (!box || !form) return;
    if (!form.lang || !book.source.length) { box.innerHTML = ""; return; }
    let plan;
    try {
      plan = await api("POST", `/api/books/${encodeURIComponent(book.name)}/estimate`, { lang: form.lang, references: form.refs, segments: form.segments });
    } catch (e) { box.innerHTML = `<div class="notice bad small">${esc(e.message)}</div>`; return; }
    if (state.current !== book.name) return;
    box.innerHTML = `<div class="notice ${plan.total_calls > 300 ? "warn" : ""} estimate-box">
        <b>${esc(L("estimate_title"))}</b>
        <div>${esc(L("estimate_segments", { selected: plan.selected, total: plan.segments }))}${plan.prepared ? "" : ` <span class="muted small">(${esc(L("estimate_guess"))})</span>`}</div>
        ${plan.total_calls ? `
          <div>${esc(L("estimate_calls", { calls: callsText(plan.calls) }))}</div>
          <div>${esc(L("estimate_time", { time: fmtDuration(plan.seconds) }))}</div>
          <div class="small">${esc(L("quota_note"))}</div>
          <div class="small">${esc(L(state.settings.keep_awake ? "awake_note" : "awake_off"))}</div>` : `<div>${esc(L(form.redo ? "estimate_redo" : "estimate_nothing"))}</div>`}
      </div>${staleHtml(plan.stale)}`;
  }, 300);
}

const exportUrl = (book, lang, kind, fmt) =>
  `/api/books/${encodeURIComponent(book)}/export/${encodeURIComponent(lang)}/${kind}/${fmt}?token=${encodeURIComponent(window.TOKEN)}&lang=${uiLang}`;

function exportLinks(book, lang) {
  const links = (kind, formats) => formats.map((fmt) =>
    `<a href="${esc(exportUrl(book, lang, kind, fmt))}" ${fmt === "pdf" ? 'target="_blank" rel="noopener"' : ""}>${esc(L("fmt_" + fmt))}</a>`).join(" · ");
  return `<div class="exports" title="${esc(L("pdf_hint"))}">
      <span class="muted">${esc(L("export_label"))}:</span>
      <span>${esc(L("translation"))}: ${links("translation", ["md", "docx", "pdf", "html"])}</span>
      <span>${esc(L("report"))}: ${links("report", ["md", "docx", "pdf"])}</span>
      <button type="button" class="link" data-act="layout">${esc(L("layout_open"))}</button>
    </div>`;
}

// ---------- export layout ----------
const LAYOUT_DEFAULTS = { page_size: "A4", margin_top: 2.5, margin_bottom: 2.5, margin_side: 2.5, font: "", arabic_font: "",
  font_size: 12, line_spacing: 1.15, justify: true, chapter_new_page: true };

function fillLayout(values, template) {
  const form = $("#layout-form");
  form.page_size.innerHTML = state.settings.page_sizes.map((s) => `<option value="${esc(s)}">${esc(L("page_" + s))}</option>`).join("");
  for (const [key, value] of Object.entries(values)) {
    if (!form[key]) continue;
    if (form[key].type === "checkbox") form[key].checked = value;
    else form[key].value = value;
  }
  $('[data-role="template-state"]').textContent = template ? L("layout_template_set", { name: template }) : `${L("layout_template_none")} ${L("layout_template_hint")}`;
  $('[data-act="template-remove"]').hidden = !template;
  $('[data-role="layout-scope"]').textContent = L(template ? "layout_scope_pdf" : "layout_scope_all");
}

async function openLayout() {
  try { state.settings = await api("GET", "/api/settings"); } catch (e) { return toast(e.message, true); }
  fillLayout(state.settings.export, state.settings.word_template);
  $("#layout").showModal();
}

$("#layout-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const form = ev.target;
  const body = {};
  for (const key of Object.keys(LAYOUT_DEFAULTS)) {
    const el = form[key];
    body[key] = el.type === "checkbox" ? el.checked : el.type === "number" ? Number(el.value) : el.value;
  }
  const r = await act(form.querySelector('[type="submit"]'), () => api("PUT", "/api/export", body));
  if (r) $("#layout").close();
});

$("#layout").addEventListener("click", async (ev) => {
  const b = ev.target.closest("button[data-act]");
  if (!b) return;
  if (b.dataset.act === "layout-close") return $("#layout").close();
  if (b.dataset.act === "layout-defaults") return fillLayout(LAYOUT_DEFAULTS, state.settings.word_template);
  if (b.dataset.act === "template-remove") {
    if (!confirm(L("layout_confirm_remove"))) return;
    if (await act(b, () => api("DELETE", "/api/export/template"))) openLayout();
    return;
  }
  if (b.dataset.act === "template-upload") {
    const file = $("#layout-template").files[0];
    if (!file) return toast(L("layout_pick_file"), true);
    await refreshToken();
    const r = await act(b, async () => {
      const res = await fetch(`/api/export/template?file=${encodeURIComponent(file.name)}`,
        { method: "PUT", headers: { "X-Token": window.TOKEN, "X-Lang": uiLang }, body: file });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error || L("upload_failed"));
      return data;
    });
    if (r) { $("#layout-template").value = ""; openLayout(); }
  }
});

function uploader(kind, extra = "") {
  return `<div class="uploader" data-kind="${kind}">
      ${extra}
      <input type="file" accept=".docx,.epub,.md,.txt,.pdf">
      <button type="button" class="btn" data-act="upload">${esc(L("upload"))}</button>
      <progress max="100" value="0" hidden></progress>
    </div>`;
}

function readRunForm() {
  const f = $('form[data-form="run"]');
  if (!f) return null;
  return {
    lang: f.elements.lang.value, segments: f.elements.segments.value, until: f.elements.until.value,
    redo: f.elements.redo.value, advanced: $('[data-role="advanced"]', f)?.open,
    refs: [...f.querySelectorAll('input[name="ref"]:checked')].map((i) => i.value),
  };
}

const outputUrl = (book, lang, kind, download) =>
  `/api/books/${encodeURIComponent(book)}/output/${encodeURIComponent(lang)}/${kind}?token=${encodeURIComponent(window.TOKEN)}&lang=${uiLang}${download ? "&download=1" : ""}`;

// The steps of the last run as bars, read from the log: done (green), failed (red), still to do (grey).
function renderTimeline(steps) {
  const box = $('[data-role="timeline"]');
  if (!box) return;
  box.hidden = !steps.length;
  if (!steps.length) return;
  box.innerHTML = `<h3>${esc(L("timeline_title"))}</h3>
    <ol class="tl">${steps.map((s) => {
      const pct = (n) => (s.total ? (100 * n) / s.total : 0);
      const state = s.failed ? "failed" : s.done >= s.total ? "done" : "";
      return `<li class="tl-row ${state}">
          <span class="tl-name">${esc(stageName(s.stage))}</span>
          <div class="track" role="img" aria-label="${s.done}/${s.total}">
            <div class="fill" style="width:${pct(s.done)}%"></div><div class="fill failed" style="width:${pct(s.failed)}%"></div>
          </div>
          <span class="tl-count">${s.done}/${s.total}${s.failed ? ` <span class="badge bad">${esc(L("timeline_failed", { count: s.failed }))}</span>` : ""}</span>
        </li>`;
    }).join("")}</ol>`;
}

async function loadLog(book) {
  let data;
  try { data = await api("GET", `/api/books/${encodeURIComponent(book.name)}/log`); } catch {
    if (book.running && state.current === book.name) state.poll = setTimeout(() => loadLog(book), 5000);
    return;
  }
  if (state.current !== book.name) return;
  const pre = $('[data-role="log"]');
  if (!pre) return;
  const atBottom = pre.scrollHeight - pre.scrollTop - pre.clientHeight < 40;
  pre.textContent = data.log || L("not_run_yet");
  if (atBottom) pre.scrollTop = pre.scrollHeight;
  $('[data-role="log-file"]').textContent = data.file;
  renderTimeline(data.timeline || []);
  if (data.running || book.running) {
    state.poll = setTimeout(() => {
      if (data.running !== book.running || !data.running) return loadBooks(true);
      // While running: refresh the log often and the progress less often.
      book._ticks = (book._ticks || 0) + 1;
      if (book._ticks % 4 === 0) return loadBooks(true);
      loadLog(book);
    }, 2500);
  }
}

async function upload(container, book) {
  const file = $('input[type="file"]', container).files[0];
  if (!file) return toast(L("pick_file"), true);
  const ext = (file.name.match(/\.[^.]+$/) || [""])[0].toLowerCase();
  if (![".docx", ".epub", ".md", ".txt", ".pdf"].includes(ext)) return toast(L("upload_bad_type"), true);
  if (file.size > 300 * 1024 * 1024 || !file.size) return toast(L("upload_bad_size"), true);
  const kind = container.dataset.kind;
  let path = `/api/books/${encodeURIComponent(book)}/${kind}`;
  if (kind === "references") {
    const lang = $('[data-role="ref-lang"]', container).value;
    if (!lang) return toast(L("pick_ref_language"), true);
    path += "/" + encodeURIComponent(lang);
  }
  const bar = $("progress", container);
  const button = $('[data-act="upload"]', container);
  const xhr = new XMLHttpRequest();
  await refreshToken();  // the interface may have been restarted since the page was opened
  xhr.open("PUT", `${path}?file=${encodeURIComponent(file.name)}`);
  xhr.setRequestHeader("X-Token", window.TOKEN);
  xhr.setRequestHeader("X-Lang", uiLang);
  xhr.upload.onprogress = (e) => { bar.hidden = false; bar.value = e.lengthComputable ? (100 * e.loaded) / e.total : 50; };
  xhr.onloadend = () => {
    button.disabled = false;
    bar.hidden = true;
    let data = {};
    try { data = JSON.parse(xhr.responseText); } catch { /* empty */ }
    if (xhr.status === 200) { toast(data.message || L("uploaded")); loadBooks(); }
    else toast(data.error || L("upload_failed"), true);
  };
  button.disabled = true;
  xhr.send(file);
}

$("#book").addEventListener("click", async (ev) => {
  const b = ev.target.closest("[data-act]");
  if (!b) return;
  const book = state.current;
  const base = `/api/books/${encodeURIComponent(book)}`;
  switch (b.dataset.act) {
    case "upload":
      return upload(b.closest(".uploader"), book);
    case "delete-ref":
      if (!confirm(L("confirm_delete_ref"))) return;
      await act(b, () => api("DELETE", `${base}/references/${encodeURIComponent(b.dataset.lang)}`));
      return loadBooks();
    case "reset":
      if (!confirm(L("confirm_reset"))) return;
      await act(b, () => api("POST", `${base}/reset`));
      return loadBooks();
    case "stop":
      await act(b, () => api("POST", `${base}/stop`));
      return setTimeout(loadBooks, 800);
    case "read":
      return openOutput(book, b.dataset.lang, b.dataset.kind);
    case "layout":
      return openLayout();
    case "preview":
      return openPreview(b, book);
    case "open-step": {
      const open = state.openStep[book] || bookSteps(state.books.find((x) => x.name === book)).current;
      state.openStep[book] = b.dataset.step === open && b.classList.contains("jhead") ? "none" : b.dataset.step;
      return renderBook(true);
    }
    case "fill-redo": {
      // Fills the form; nothing is deleted until the user clicks Start and confirms.
      const f = $('form[data-form="run"]');
      f.elements.segments.value = b.dataset.segments;
      f.elements.redo.value = b.dataset.stage;
      $('[data-role="advanced"]', f).open = true;
      loadEstimate(state.books.find((x) => x.name === book));
      return toast(L("stale_filled"));
    }
    case "refs-done":
      state.skipRefs.add(book);
      return renderBook();
    case "recover": {
      // Replaces the failed model in every step of the workflow (all models of the tool when it refused the account).
      const box = b.closest(".recover");
      const from = box.dataset.from, to = $("select", box).value, whole = box.dataset.whole === "1";
      const replace = (n) => (whole ? providerOf(n) === providerOf(from) : n === from);
      const r = await act(b, async () => {
        if (state.books.find((x) => x.name === book)?.running) {
          // The run is stopped first; finished segments are kept, the calls in progress are made again.
          toast(L("recover_switching"));
          await api("POST", `${base}/stop`);
          await waitStopped(book);
        }
        const s = await api("GET", "/api/settings");
        const stages = Object.fromEntries(Object.entries(s.stages).map(([st, names]) => [st, [...new Set(names.map((n) => (replace(n) ? to : n)))]]));
        await api("PUT", "/api/stages", { stages, flow: s.flow });
        state.settings = await api("GET", "/api/settings");
        state.board = state.flow = null;  // the Workflow tab reads the new assignment when it opens
        await restartRun(book);
        return { message: L("recover_done", { from: modelLabel(from), to: modelLabel(to) }) };
      });
      if (r) loadBooks();
      return;
    }
    case "retry":
      if (await act(b, () => restartRun(book))) loadBooks();
      return;
    case "keep":
      state.dismissed.add(`${book}:${state.books.find((x) => x.name === book).run.started}:${b.dataset.name}`);
      return renderBook(true);
  }
});

$("#book").addEventListener("change", (ev) => {
  if (ev.target.dataset.role === "recover-to") state.recoverChoice[ev.target.closest(".recover").dataset.from] = ev.target.value;
  if (!ev.target.closest('form[data-form="run"]')) return;
  const book = state.books.find((b) => b.name === state.current);
  if (book && !book.running) loadEstimate(book);
});
$("#book").addEventListener("input", (ev) => {
  if (ev.target.name !== "segments") return;
  const book = state.books.find((b) => b.name === state.current);
  if (book && !book.running) loadEstimate(book);
});

$("#book").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const f = ev.target;
  if (f.id === "first-book") {
    const r = await act($("button", f), () => api("POST", "/api/books", { name: f.elements.name.value }));
    if (r) { state.current = r.name; loadBooks(); }
    return;
  }
  if (f.dataset.form === "language") {
    const r = await act($("button", f), () => api("POST", "/api/languages", { code: f.elements.code.value, name: f.elements.name.value }));
    if (r) loadBooks();
    return;
  }
  if (f.dataset.form === "run") {
    const form = readRunForm();
    const redo = f.elements.redo.value;
    if (redo && !confirm(L("confirm_redo", { stage: stageName(redo) }))) return;
    const body = { lang: form.lang, references: form.refs, segments: form.segments, until: form.until, redo };
    const r = await act($('button[type="submit"]', f), () => api("POST", `/api/books/${encodeURIComponent(state.current)}/run`, body));
    if (r) loadBooks();
  }
});

async function openOutput(book, lang, kind) {
  try {
    const res = await fetch(outputUrl(book, lang, kind, false));
    if (!res.ok) throw new Error(L("output_unreadable"));
    $("#reader-title").textContent = `${book} · ${languageName(lang)} · ${L(kind)}`;
    $("#reader-text").textContent = await res.text();
    $("#reader-download").href = exportUrl(book, lang, kind, "md");
    $("#reader-download").hidden = false;
    $("#reader").showModal();
  } catch (e) { toast(e.message, true); }
}
// The source as the pipeline reads it. The first call prepares the book (it splits the text; no model is called).
async function openPreview(button, book) {
  const r = await act(button, () => api("POST", `/api/books/${encodeURIComponent(book)}/preview`));
  if (!r) return;
  $("#reader-title").textContent = `${book} · ${L("preview_title", { count: r.segments })}`;
  $("#reader-text").textContent = r.text;
  $("#reader-download").hidden = true;
  $("#reader").showModal();
  loadBooks(true);
}
$("#reader-close").addEventListener("click", () => $("#reader").close());

// ---------- workflow board ----------
const PRESET_FLOW = ["review1", "revise1", "source_check", "review2", "reconcile"];
const PRESET = { align: ["antigravity"], glossary: ["claude"], translate: ["chatgpt"], review1: ["antigravity"], revise1: ["chatgpt"],
                 source_check: ["claude"], review2: ["chatgpt", "antigravity"], reconcile: ["claude"] };
const MODEL_RE = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,79}$/;

async function loadBoard() {
  try { state.settings = await api("GET", "/api/settings"); } catch (e) { return toast(e.message, true); }
  state.board = JSON.parse(JSON.stringify(state.settings.stages));
  state.flow = [...state.settings.flow];
  state.nodes = JSON.parse(JSON.stringify(state.settings.nodes || {}));
  state.instructions = { ...(state.settings.instructions || {}) };
  state.palette = {};
  state.auto = state.auto || {};  // the models that each tool offers, read from the tool
  for (const [provider, info] of Object.entries(state.settings.providers)) state.palette[provider] = [...info.models];
  for (const names of Object.values(state.board)) {
    for (const name of names) {
      const provider = providerOf(name), model = modelOf(name);
      if (model && state.palette[provider] && !state.palette[provider].includes(model)) state.palette[provider].push(model);
    }
  }
  renderBoard();
  loadModels();
}

// The model lists come from the tools themselves. The board works before they arrive.
async function loadModels() {
  await Promise.all(Object.entries(state.settings.providers).map(async ([provider, info]) => {
    if (!info.tool) return;
    try { state.auto[provider] = (await api("GET", `/api/tools/${encodeURIComponent(info.tool)}/models`)).models; } catch { /* keeps the last list */ }
  }));
  state.modelsLoaded = true;
  if (state.tab === "workflow" && state.board) renderBoard();
}

// The tool's own models first, then the models that the user added by name.
const providerModels = (provider) => [...new Set([...(state.auto?.[provider] || []),
  ...(state.palette?.[provider] || state.settings?.providers[provider]?.models || [])])];

function allNames() {
  return Object.keys(state.palette).flatMap((provider) => [provider, ...providerModels(provider).map((m) => `${provider}/${m}`)]);
}

// Who wrote the text that a step works on.
const writerOf = (stage) => (state.board[textInput(stage)] || [])[0];

function boardWarnings(b) {
  const out = [];
  for (const step of state.flow) {
    const writer = writerOf(step);
    if (!writer || !b[step] || stageKind(step) === "apply") continue;
    const name = stageName(step);
    if (nodeRole(step) === "report") {
      if (b[step].some((n) => baseOf(n) === baseOf(writer))) out.push(["warn", L("warn_self_review", { step: name, model: modelLabel(writer) }), step]);
      else if (b[step].every((n) => makerOf(n) === makerOf(writer))) out.push(["", L("info_same_provider", { step: name }), step]);
    } else if (baseOf(b[step][0]) === baseOf(writer)) {
      out.push(["warn", L("warn_self_check", { step: name, model: modelLabel(writer) }), step]);
    }
  }
  if (!state.flow.length) out.push(["warn", L("warn_no_check")]);
  return out;
}

// One group per tool; each lists the tool's default and its models.
function modelOptions(selected, skip = []) {
  return Object.keys(state.palette || state.settings.providers).map((provider) => {
    const items = [provider, ...providerModels(provider).map((m) => `${provider}/${m}`)].filter((n) => !skip.includes(n))
      .map((n) => `<option value="${esc(n)}" ${n === selected ? "selected" : ""}>${esc(modelLabel(n))}</option>`).join("");
    return items ? `<optgroup label="${esc(providerName(provider))}">${items}</optgroup>` : "";
  }).join("");
}

// ---------- the canvas: the steps as nodes from left to right ----------
// Preparation and the first translation start every workflow; any number of nodes follows them. A reporting node
// writes findings, an apply node applies the findings reported since the last text, a checkpoint can send a
// segment back to an earlier node (drawn as an arc above the nodes).
const FIXED_NODES = ["prep", "translate", "human"];
const STEP_TYPES = [  // the palette: kind, mark
  ["round", "✎"], ["review", "?"], ["apply", "✓"], ["source_check", "⇆"], ["custom", "★"], ["gate", "↺"]];
const ROLE_KEYS = { align: "role_align", glossary: "role_glossary", translate: "role_translate", source_check: "role_check",
                    review: "reviewers_label", apply: "applier_label", gate: "role_gate" };
const isReporting = (stage) => nodeRole(stage) === "report";
const roleLabel = (stage) => (stageKind(stage) === "custom" ? L(isReporting(stage) ? "reviewers_label" : "role_editor")
  : L(ROLE_KEYS[stageKind(stage)]));
const nodeKind = (node) => (node === "prep" || node === "human" ? node : stageKind(node));
const KIND_MARK = Object.fromEntries(STEP_TYPES);

function nodeRoles(node) {
  if (node === "prep") return ["align", "glossary"];
  return node === "human" ? [] : [node];
}

function nodeTitle(node) {
  if (node === "prep") return L("node_prep");
  if (node === "human") return L("human_step");
  if (node === "translate") return L("flow_translate");
  const kind = stageKind(node);
  if (kind === "custom") return state.nodes[node]?.title || L("flow_custom");
  return L(kind === "review" ? "node_review" : "flow_" + kind);
}

// The mark in the node: its step number, a letter for preparation.
function nodeMark(node) {
  if (node === "prep") return L("prep_mark");
  if (node === "human") return "✓";
  return String(numberedSteps().indexOf(node) + 1);
}

function nodeDescription(node) {
  if (node === "prep") return `${L("step_desc_align")} ${L("step_desc_glossary")}`;
  if (node === "human" || node === "translate") return L("step_desc_" + node);
  const kind = stageKind(node);
  if (kind === "custom") return L(isReporting(node) ? "step_desc_custom_report" : "step_desc_custom_rewrite");
  return L("step_desc_node_" + kind);
}

// The problems that keep a flow from running (the server checks the same): {node: message}.
function flowProblems() {
  const out = {};
  let pending = null;
  let lastGate = -1;
  state.flow.forEach((node, i) => {
    const kind = stageKind(node);
    const role = nodeRole(node);
    if (kind === "custom" && !(state.nodes[node]?.title || "").trim()) out[node] = L("problem_custom_title");
    if (role === "report") pending = pending || node;
    else if (role === "text") {
      if (pending && kind !== "apply") out[pending] = L("problem_unapplied");
      pending = null;
    } else {
      const back = state.nodes[node]?.back_to;
      if (!state.flow.slice(lastGate + 1, i).includes(back)) out[node] = L("problem_gate_target");
      lastGate = i;
    }
  });
  if (pending) out[pending] = L("problem_unapplied");
  return out;
}

const chipsHtml = (stage) => (state.board[stage] || [])
  .map((n) => `<span class="mchip ${esc(providerOf(n))}" title="${esc(modelLabel(n))}">${esc(modelLabel(n))}</span>`).join("");

function nodeHtml(node, index) {
  const problem = state.problems[node];
  const warns = state.warn[node] || [];
  const selected = state.selected === node;
  const movable = index !== undefined;
  const kind = nodeKind(node);
  const roles = nodeRoles(node).map((stage) => `
      <div class="node-role" data-stage="${stage}"><span class="role">${esc(roleLabel(stage))}</span>${chipsHtml(stage)}</div>`).join("");
  const extra = kind === "gate" && state.nodes[node]?.back_to
    ? `<div class="node-note">${esc(L("gate_note", { step: stageName(state.nodes[node].back_to), max: state.nodes[node].max }))}</div>`
    : kind === "custom" ? `<div class="node-note">${esc(L(isReporting(node) ? "mode_report" : "mode_rewrite"))}</div>` : "";
  const flag = problem ? `<span class="node-warn bad" title="${esc(problem)}" aria-label="${esc(problem)}">!</span>`
    : warns.length ? `<span class="node-warn" title="${esc(warns.join(" "))}" aria-label="${esc(warns.join(" "))}">!</span>` : "";
  return `<div class="node kind-${kind}${selected ? " selected" : ""}${problem ? " invalid" : ""}" data-node="${node}" tabindex="0"
      role="button" aria-pressed="${selected}" ${movable ? `data-index="${index}" draggable="true" title="${esc(L("drag_to_move"))}"` : ""}>
      <div class="node-head">
        <span class="node-glyph">${esc(nodeMark(node))}</span>
        <b><span class="node-kind">${esc(KIND_MARK[kind] || "")}</span> ${esc(nodeTitle(node))}</b>${flag}
      </div>${extra}${roles}
    </div>`;
}

// An arrow between two nodes. After the first translation each arrow is a place where a node can be put.
function edgeHtml(at) {
  if (at === null) return `<div class="edge" aria-hidden="true"></div>`;
  const full = state.flow.length >= state.settings.max_flow_steps;
  const open = state.addAt === at;
  const menu = open ? `<div class="edge-menu" role="menu">${STEP_TYPES.map(([kind, mark]) =>
    `<button type="button" role="menuitem" data-act="insert" data-kind="${kind}" data-at="${at}"><span aria-hidden="true">${mark}</span> ${esc(L("type_" + kind))}</button>`).join("")}
    </div>` : "";
  return `<div class="edge slot" data-at="${at}">${full ? "" : `<button type="button" class="edge-add" data-act="edge-add"
      data-at="${at}" aria-label="${esc(L("insert_here"))}" title="${esc(L("insert_here"))}" aria-expanded="${open}">+</button>`}${menu}</div>`;
}

// The arcs of the checkpoints: from the checkpoint back to the node it sends segments to.
function drawLoops(track) {
  track.querySelector(".loops")?.remove();
  const gates = state.flow.filter((n) => stageKind(n) === "gate" && state.flow.includes(state.nodes[n]?.back_to));
  track.classList.toggle("has-loops", gates.length > 0);
  if (!gates.length) return;
  const box = track.getBoundingClientRect();
  const zoom = Number(track.style.zoom) || 1;
  const at = (node) => {
    const r = track.querySelector(`.node[data-node="${node}"]`).getBoundingClientRect();
    return { x: (r.left + r.width / 2 - box.left) / zoom, top: (r.top - box.top) / zoom };
  };
  const paths = gates.map((gate, i) => {
    const from = at(gate), to = at(state.nodes[gate].back_to);
    const lift = 16 + 10 * (i % 3);
    const y = Math.min(from.top, to.top);
    return `<path d="M ${from.x} ${from.top} C ${from.x} ${y - lift}, ${to.x} ${y - lift}, ${to.x} ${to.top}" marker-end="url(#loop-arrow)"/>
      <text x="${(from.x + to.x) / 2}" y="${y - lift + 1}">${esc(L("loop_label", { max: state.nodes[gate].max }))}</text>`;
  }).join("");
  track.insertAdjacentHTML("afterbegin", `<svg class="loops" aria-hidden="true" width="${box.width / zoom}" height="${box.height / zoom}">
    <defs><marker id="loop-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
    <path d="M0,0 L10,5 L0,10 z"/></marker></defs>${paths}</svg>`);
}

// The models a role can take: one row of buttons per tool. A reporting node takes up to 4 models; the
// other roles take one.
function rolePicker(stage) {
  const many = isReporting(stage);
  const chosen = state.board[stage] || [];
  const rows = Object.keys(state.palette).map((provider) => {
    const fallback = state.settings.providers[provider]?.default_model;
    const names = [provider, ...providerModels(provider).map((m) => `${provider}/${m}`)];
    const buttons = names.map((n) => `<button type="button" class="pick" data-act="pick" data-stage="${stage}" data-name="${esc(n)}"
        aria-pressed="${chosen.some((c) => baseOf(c) === n)}">${esc(modelOf(n) || (fallback ? `${L("default_model")} (${fallback})` : L("default_model")))}</button>`).join("");
    return `<div class="pick-row"><span class="pick-provider ${esc(provider)}">${esc(providerName(provider))}</span>
        <div class="pick-chips">${buttons}</div></div>`;
  }).join("");
  // The thinking level of each chosen model; a tool without such an option says so.
  const levels = chosen.map((c) => {
    const efforts = providerEfforts(providerOf(c));
    const label = esc(modelLabel(baseOf(c)));
    if (!efforts.length) return `<div class="effort-row"><span>${label}</span><span class="muted small">${esc(L("effort_none"))}</span></div>`;
    const options = ["", ...efforts].map((e) => `<option value="${e}" ${e === effortOf(c) ? "selected" : ""}>${esc(L(e ? "effort_" + e : "effort_default"))}</option>`).join("");
    return `<label class="effort-row"><span>${label}</span><select data-act="effort" data-stage="${stage}" data-name="${esc(c)}">${options}</select></label>`;
  }).join("");
  return `<fieldset class="role-pick"><legend>${esc(roleLabel(stage))}
      <span class="parallel-tag">${esc(L(many ? "parallel_tag" : "pick_one"))}</span></legend>${rows}
      <div class="efforts"><p class="muted small">${esc(L("effort_title"))}</p>${levels}</div></fieldset>`;
}

// The settings of a custom node (name, what it does, its instructions) and of a checkpoint (where it sends back).
function nodeSettings(node) {
  const kind = stageKind(node);
  const opts = state.nodes[node] || {};
  if (kind === "custom") {
    return `<div class="node-settings">
        <label>${esc(L("custom_title"))}<input data-field="title" maxlength="60" value="${esc(opts.title || "")}"></label>
        <fieldset class="plain"><legend>${esc(L("custom_mode"))}</legend><div class="row">
          <label class="radio"><input type="radio" name="mode" data-field="mode" value="report" ${opts.mode === "report" ? "checked" : ""}> ${esc(L("mode_report"))}</label>
          <label class="radio"><input type="radio" name="mode" data-field="mode" value="rewrite" ${opts.mode !== "report" ? "checked" : ""}> ${esc(L("mode_rewrite"))}</label>
        </div></fieldset>
        <label>${esc(L("custom_instructions"))}<span class="muted small">${esc(L("custom_instructions_hint"))}</span>
          <textarea data-field="instructions" rows="7" maxlength="20000">${esc(state.instructions[node] || "")}</textarea></label>
      </div>`;
  }
  if (kind === "gate") {
    const i = state.flow.indexOf(node);
    const lastGate = state.flow.slice(0, i).map((n, k) => (stageKind(n) === "gate" ? k : -1)).reduce((a, b) => Math.max(a, b), -1);
    const targets = state.flow.slice(lastGate + 1, i);
    const options = targets.map((n) => `<option value="${n}" ${n === opts.back_to ? "selected" : ""}>${esc(stageName(n))}</option>`).join("");
    return `<div class="node-settings">
        <label>${esc(L("gate_back_to"))}<select data-field="back_to">
          ${opts.back_to && targets.includes(opts.back_to) ? "" : `<option value="">${esc(L("gate_choose"))}</option>`}${options}</select></label>
        <label>${esc(L("gate_max"))}<select data-field="max">${Array.from({ length: state.settings.max_loops }, (_, k) => k + 1)
          .map((n) => `<option value="${n}" ${n === opts.max ? "selected" : ""}>${n}</option>`).join("")}</select></label>
        <p class="muted small">${esc(L("gate_help"))}</p>
      </div>`;
  }
  return "";
}

function renderInspector() {
  const node = state.selected;
  const i = state.flow.indexOf(node);
  const tools = i >= 0 ? `<div class="row">
      <button type="button" class="btn small" data-act="move" data-dir="-1" ${i === 0 ? "disabled" : ""}>← ${esc(L("move_earlier"))}</button>
      <button type="button" class="btn small" data-act="move" data-dir="1" ${i === state.flow.length - 1 ? "disabled" : ""}>${esc(L("move_later"))} →</button>
      <button type="button" class="btn small danger" data-act="remove-step">${esc(L("remove_step"))}</button>
    </div>` : "";
  const notes = [state.problems[node] && `<div class="notice bad">${esc(state.problems[node])}</div>`,
    ...(state.warn[node] || []).map((text) => `<div class="notice warn">${esc(text)}</div>`)].filter(Boolean).join("");
  const fixed = node === "prep" || node === "translate" ? `<p class="muted small">${esc(L("node_locked"))}</p>` : "";
  $("#inspector").innerHTML = `
    <div class="inspector-head">
      <div><h3>${esc(node === "human" ? nodeTitle(node) : `${nodeMark(node)} · ${nodeTitle(node)}`)}</h3>
        <p class="muted small">${esc(nodeDescription(node))}</p>${fixed}</div>
      ${tools}
    </div>${notes}${i >= 0 ? nodeSettings(node) : ""}${nodeRoles(node).map(rolePicker).join("")}`;
}

function renderPalette() {
  const used = new Set(Object.values(state.board).flat());
  const stepType = ([kind, mark]) => `
    <div class="step-type ${kind}" role="button" tabindex="0" draggable="true" data-kind="${kind}" title="${esc(L("palette_steps_hint"))}">
      <span class="glyph" aria-hidden="true">${mark}</span>
      <span><b>${esc(L("type_" + kind))}</b><span class="small">${esc(L("type_hint_" + kind))}</span></span>
    </div>`;
  const full = state.flow.length >= state.settings.max_flow_steps;
  const steps = `<section class="card palette-group steps-group">
      <h3>${esc(L("palette_steps"))}</h3>
      ${STEP_TYPES.map(stepType).join("")}
      <p class="muted small">${esc(full ? L("max_steps", { count: state.settings.max_flow_steps }) : L("palette_steps_hint"))}</p>
      <p class="muted small">${esc(L("flow_changed_note"))}</p>
    </section>
    <div><h3 class="palette-title">${esc(L("palette_models"))}</h3><p class="muted small">${esc(L("palette_models_hint"))}</p></div>`;
  $("#palette").innerHTML = steps + Object.keys(state.palette).map((provider) => {
    const auto = state.auto[provider] || [];
    const card = (name, custom) => `
      <div class="model-card ${esc(provider)}" draggable="true" data-name="${esc(name)}">
        <span>${esc(modelOf(name) || L("default_model"))}${!modelOf(name) && state.settings.providers[provider]?.default_model ? ` <span class="muted small">(${esc(state.settings.providers[provider].default_model)})</span>` : ""}</span>
        <span class="tools">
          <button type="button" class="icon-btn" data-act="test-model" data-name="${esc(name)}">${esc(L("test"))}</button>
          ${custom ? `<button type="button" class="icon-btn" data-act="remove-model" data-name="${esc(name)}" aria-label="${esc(L("remove"))}" ${used.has(name) ? 'disabled title="' + esc(L("cannot_remove_used")) + '"' : ""}>×</button>` : ""}
        </span>
      </div>`;
    return `<section class="card palette-group ${esc(provider)}">
        <h3>${esc(providerName(provider))}</h3>
        ${card(provider, false)}
        ${providerModels(provider).map((m) => card(`${provider}/${m}`, !auto.includes(m))).join("")}
        ${auto.length ? "" : `<p class="muted small">${esc(L(state.modelsLoaded ? "models_none" : "models_loading"))}</p>`}
        <details>
          <summary>${esc(L("add_other_model"))}</summary>
          <form class="add-model" data-provider="${esc(provider)}">
            <input placeholder="${esc(L("add_model_placeholder"))}" aria-label="${esc(L("add_model_placeholder"))}">
            <button type="submit" class="btn small">${esc(L("add"))}</button>
          </form>
        </details>
      </section>`;
  }).join("");
}

// The element that has the focus, found again after the board is drawn anew.
function focusKey(el) {
  if (!el?.dataset || !el.closest?.("#workflow")) return null;
  if (el.dataset.node) return `.node[data-node="${el.dataset.node}"]`;
  if (el.dataset.field) return `[data-field="${el.dataset.field}"]${el.type === "radio" ? `[value="${CSS.escape(el.value)}"]` : ""}`;
  if (!el.dataset.act && !el.dataset.kind) return null;
  return ["act", "stage", "name", "at", "kind", "dir"].filter((k) => el.dataset[k] !== undefined)
    .map((k) => `[data-${k}="${CSS.escape(el.dataset[k])}"]`).join("");
}

// keepPanel: the panel below stays as it is (the user is typing in it).
function renderBoard(keepPanel = false) {
  const focus = keepPanel ? null : focusKey(document.activeElement);
  if (!state.selected || !(FIXED_NODES.includes(state.selected) || state.flow.includes(state.selected))) state.selected = "translate";
  state.problems = flowProblems();
  state.warn = {};
  for (const [, text, step] of boardWarnings(state.board)) if (step) (state.warn[step] ||= []).push(text);
  renderPalette();
  const canvas = $("#canvas");
  const scroll = canvas.scrollLeft;
  canvas.setAttribute("aria-label", L("canvas_label"));
  canvas.innerHTML = `<div class="canvas-track">${[nodeHtml("prep"), edgeHtml(null), nodeHtml("translate"), edgeHtml(0),
    ...state.flow.flatMap((step, i) => [nodeHtml(step, i), edgeHtml(i + 1)]), nodeHtml("human")].join("")}</div>`;
  // A long workflow is drawn smaller to fit (down to 80 %); beyond that the canvas scrolls sideways.
  const track = $(".canvas-track", canvas);
  track.classList.toggle("has-loops", state.flow.some((n) => stageKind(n) === "gate"));
  track.style.zoom = Math.max(0.8, Math.min(1, (canvas.clientWidth - 40) / track.scrollWidth));
  drawLoops(track);
  canvas.scrollLeft = scroll;
  if (state.reveal) {
    state.reveal = false;
    $(`.node[data-node="${state.selected}"]`, canvas)?.scrollIntoView({ block: "nearest", inline: "nearest" });
  }
  // A step's warnings are on its node and in the panel below; here only those of the whole workflow.
  const problems = Object.keys(state.problems).length;
  $("#board-warnings").innerHTML = (problems ? `<div class="notice bad">${esc(L("flow_has_problems", { count: problems }))}</div>` : "")
    + boardWarnings(state.board).filter(([, , step]) => !step).map(([tone, text]) => `<div class="notice ${tone}">${esc(text)}</div>`).join("");
  if (keepPanel) return;
  renderInspector();
  if (focus) document.querySelector(`#workflow ${focus}`)?.focus({ preventScroll: true });
}

function selectNode(node) {
  state.selected = node;
  state.reveal = true;
  state.addAt = null;
  renderBoard();
}

// A model dropped on a role: a reporting node takes it as one more model, any other role is replaced.
function assign(stage, name) {
  const current = state.board[stage] || [];
  if (isReporting(stage)) {
    if (current.some((n) => baseOf(n) === baseOf(name))) return;
    if (current.length >= state.settings.max_reporters) return toast(L("max_reviewers"), true);
    state.board[stage] = [...current, name];
  } else {
    if (current.length === 1 && baseOf(current[0]) === baseOf(name)) return;  // the same model keeps its level
    state.board[stage] = [name];
  }
  changed();
}

// A model button in the inspector: a model of a reporting node is switched on or off, any other role takes it.
function pick(stage, name) {
  const current = state.board[stage] || [];
  const on = current.find((n) => baseOf(n) === name);
  if (!isReporting(stage) || !on) return assign(stage, name);
  if (current.length === 1) return toast(L("min_one_model"), true);
  state.board[stage] = current.filter((n) => n !== on);
  changed();
}

// The thinking level of a chosen model: "" = the tool's default.
function setEffort(stage, name, effort) {
  const next = baseOf(name) + (effort ? "@" + effort : "");
  state.board[stage] = (state.board[stage] || []).map((n) => (n === name ? next : n));
  changed();
}

function newId(prefix) {
  const taken = new Set(state.flow);
  for (let n = 1; ; n++) {
    const id = prefix === "source_check" && n === 1 ? "source_check" : `${prefix}${n}`;
    // An apply node never takes the old folder names of the first two review rounds.
    if (!taken.has(id) && !(prefix === "apply" && (taken.has(`revise${n}`)))) return id;
  }
}

// A new node. Its model: a reporting or checking node gets a model of another company than the one that wrote
// the text; an apply node gets the model that wrote the text. A review round puts in a review and an apply node.
function addStep(kind, at = state.flow.length) {
  const count = kind === "round" ? 2 : 1;
  if (state.flow.length + count > state.settings.max_flow_steps) return toast(L("max_steps", { count: state.settings.max_flow_steps }), true);
  const ids = kind === "round" ? [newId("review")] : [newId(kind)];
  state.flow.splice(at, 0, ids[0]);
  if (kind === "round") {
    ids.push(newId("apply"));
    state.flow.splice(at + 1, 0, ids[1]);
  }
  if (kind === "custom") {
    state.nodes[ids[0]] = { title: L("custom_default_title"), mode: "report" };
    state.instructions[ids[0]] = "";
  }
  if (kind === "gate") {
    const i = state.flow.indexOf(ids[0]);
    const lastGate = state.flow.slice(0, i).map((n, k) => (stageKind(n) === "gate" ? k : -1)).reduce((a, b) => Math.max(a, b), -1);
    state.nodes[ids[0]] = { back_to: state.flow.slice(lastGate + 1, i).find((n) => nodeRole(n) === "report") || state.flow[lastGate + 1] || null, max: 2 };
    if (state.nodes[ids[0]].back_to === ids[0]) state.nodes[ids[0]].back_to = null;
  }
  for (const id of ids) {
    const writer = writerOf(id) || Object.keys(state.palette)[0];
    const other = Object.keys(state.palette).find((p) => makerOf(p) !== makerOf(writer)) || writer;
    state.board[id] = [stageKind(id) === "apply" ? writer : other];
  }
  state.selected = ids[0];
  state.reveal = true;
  state.addAt = null;
  changed();
}

function removeStep(index) {
  const step = state.flow[index];
  if (!confirm(L("confirm_remove_step", { step: nodeTitle(step) }))) return;
  state.flow.splice(index, 1);
  delete state.board[step];
  delete state.nodes[step];
  delete state.instructions[step];
  for (const options of Object.values(state.nodes)) if (options.back_to === step) options.back_to = null;
  state.selected = state.flow[Math.min(index, state.flow.length - 1)] || "translate";
  changed();
}

// Moves a node to a place between the nodes: place 0 is right after the first translation.
function moveStep(from, at) {
  if (from < 0 || at < 0 || at > state.flow.length || at === from || at === from + 1) return;  // same place
  const [step] = state.flow.splice(from, 1);
  state.flow.splice(at > from ? at - 1 : at, 0, step);
  changed();
}

// Every change on the board is saved at once; there is no separate save step.
let saveTimer;
function changed(keepPanel = false) {
  renderBoard(keepPanel);
  clearTimeout(saveTimer);
  saveTimer = setTimeout(saveBoard, 250);
}
async function saveBoard() {
  const status = $("#board-status");
  status.textContent = L("saving");
  status.className = "muted small";
  if (Object.keys(state.problems || {}).length) {
    status.textContent = L("not_saved_problems");
    status.className = "warn-text small";
    return;
  }
  const stages = Object.fromEntries(["align", "glossary", ...numberedSteps()].map((s) => [s, state.board[s]]));
  const nodes = Object.fromEntries(state.flow.filter((n) => state.nodes[n]).map((n) => [n, state.nodes[n]]));
  const instructions = Object.fromEntries(state.flow.filter((n) => stageKind(n) === "custom").map((n) => [n, state.instructions[n] || ""]));
  try {
    await api("PUT", "/api/stages", { stages, flow: state.flow, nodes, instructions, models: customModels() });
    status.textContent = L("saved_now");
    status.className = "good-text small";
    state.settings = await api("GET", "/api/settings");
  } catch (e) {
    status.textContent = e.message;
    status.className = "warn-text small";
    toast(e.message, true);
  }
}

// Drag and drop: a step node is moved, a step type from the palette is put in, a model card is dropped on a role.
let dragging = null;  // { index } | { kind } | { model }

function endDrag() {
  dragging = null;
  const canvas = $("#canvas");
  canvas.classList.remove("dragging-step");
  canvas.querySelectorAll(".over, .dragging").forEach((el) => el.classList.remove("over", "dragging"));
}

// The place between the nodes under the pointer: on an arrow, or on the near half of a node.
function dropPlace(ev) {
  const edge = ev.target.closest(".edge.slot");
  if (edge) return Number(edge.dataset.at);
  const node = ev.target.closest(".node");
  if (!node) return null;
  const box = node.getBoundingClientRect();
  const after = ev.clientX > box.left + box.width / 2;
  if (node.dataset.index !== undefined) return Number(node.dataset.index) + (after ? 1 : 0);
  return node.dataset.node === "human" ? state.flow.length : 0;
}

$("#palette").addEventListener("dragstart", (ev) => {
  const type = ev.target.closest(".step-type");
  const card = ev.target.closest(".model-card");
  if (type) {
    if (state.flow.length >= state.settings.max_flow_steps) return ev.preventDefault();
    dragging = { kind: type.dataset.kind };
    ev.dataTransfer.effectAllowed = "copy";
    ev.dataTransfer.setData("text/plain", type.dataset.kind);
    $("#canvas").classList.add("dragging-step");
  } else if (card) {
    dragging = { model: card.dataset.name };
    ev.dataTransfer.effectAllowed = "copy";
    ev.dataTransfer.setData("text/plain", card.dataset.name);
  }
});
$("#canvas").addEventListener("dragstart", (ev) => {
  const node = ev.target.closest(".node[data-index]");
  if (!node) return;
  dragging = { index: Number(node.dataset.index) };
  ev.dataTransfer.effectAllowed = "move";
  ev.dataTransfer.setData("text/plain", node.dataset.node);
  node.classList.add("dragging");
  $("#canvas").classList.add("dragging-step");
});
document.addEventListener("dragend", endDrag);
$("#canvas").addEventListener("dragover", (ev) => {
  if (!dragging) return;
  const canvas = $("#canvas");
  canvas.querySelectorAll(".over").forEach((el) => el.classList.remove("over"));
  if (dragging.model) {
    const role = ev.target.closest(".node-role");
    if (!role) return;
    ev.preventDefault();
    role.classList.add("over");
    return;
  }
  const at = dropPlace(ev);
  if (at === null) return;
  ev.preventDefault();
  ev.dataTransfer.dropEffect = dragging.kind ? "copy" : "move";
  canvas.querySelector(`.edge.slot[data-at="${at}"]`)?.classList.add("over");
});
$("#canvas").addEventListener("drop", (ev) => {
  if (!dragging) return;
  ev.preventDefault();
  const drag = dragging;
  const role = ev.target.closest(".node-role");
  const at = dropPlace(ev);
  endDrag();
  if (drag.model) {
    if (role && allNames().includes(drag.model)) assign(role.dataset.stage, drag.model);
  } else if (at !== null) {
    if (drag.kind) addStep(drag.kind, at);
    else moveStep(drag.index, at);
  }
});

$("#canvas").addEventListener("click", (ev) => {
  const b = ev.target.closest("button[data-act]");
  if (b?.dataset.act === "edge-add") {
    const at = Number(b.dataset.at);
    state.addAt = state.addAt === at ? null : at;
    renderBoard();
    if (state.addAt !== null) $(`#canvas .edge-menu button`)?.focus();
    return;
  }
  if (b?.dataset.act === "insert") return addStep(b.dataset.kind, Number(b.dataset.at));
  const node = ev.target.closest(".node");
  if (node) return selectNode(node.dataset.node);
  if (state.addAt !== null && state.addAt !== undefined) {
    state.addAt = null;
    renderBoard();
  }
});
$("#canvas").addEventListener("keydown", (ev) => {
  if (ev.key === "Escape" && state.addAt !== null && state.addAt !== undefined) {
    const at = state.addAt;
    state.addAt = null;
    renderBoard();
    $(`#canvas .edge-add[data-at="${at}"]`)?.focus();
    return;
  }
  const node = ev.target.closest(".node");
  if (node && ev.target === node && (ev.key === "Enter" || ev.key === " ")) {
    ev.preventDefault();
    selectNode(node.dataset.node);
  }
});
$("#inspector").addEventListener("click", (ev) => {
  const b = ev.target.closest("button[data-act]");
  if (!b) return;
  const index = state.flow.indexOf(state.selected);
  if (b.dataset.act === "pick") pick(b.dataset.stage, b.dataset.name);
  else if (b.dataset.act === "move") moveStep(index, Number(b.dataset.dir) < 0 ? index - 1 : index + 2);
  else if (b.dataset.act === "remove-step") removeStep(index);
});
// The fields of a custom node or a checkpoint. Text is saved after a pause in typing, without drawing the panel anew.
let typing;
$("#inspector").addEventListener("input", (ev) => {
  const field = ev.target.dataset?.field;
  const node = state.selected;
  if (!field || !state.flow.includes(node)) return;
  if (field === "instructions") state.instructions[node] = ev.target.value;
  else if (field === "title") state.nodes[node].title = ev.target.value;
  else return;
  clearTimeout(typing);
  typing = setTimeout(() => changed(true), 600);
});
$("#inspector").addEventListener("change", (ev) => {
  if (ev.target.dataset?.act === "effort") return setEffort(ev.target.dataset.stage, ev.target.dataset.name, ev.target.value);
  const field = ev.target.dataset?.field;
  const node = state.selected;
  if (!field || !state.flow.includes(node) || field === "instructions" || field === "title") return;
  const value = ev.target.value;
  state.nodes[node][field] = field === "max" ? Number(value) : value || null;
  changed();
});

// A step type from the palette can also be clicked (or chosen with the keyboard): it is put at the end.
$("#palette").addEventListener("keydown", (ev) => {
  const type = ev.target.closest(".step-type");
  if (type && (ev.key === "Enter" || ev.key === " ")) {
    ev.preventDefault();
    addStep(type.dataset.kind);
  }
});
$("#palette").addEventListener("submit", (ev) => {
  ev.preventDefault();
  const form = ev.target;
  const input = $("input", form);
  const model = input.value.trim();
  if (!MODEL_RE.test(model)) return toast(L("model_name_invalid"), true);
  const list = state.palette[form.dataset.provider];
  if (!list.includes(model)) list.push(model);
  input.value = "";
  changed();
});
$("#palette").addEventListener("click", async (ev) => {
  const type = ev.target.closest(".step-type");
  if (type) return addStep(type.dataset.kind);
  const b = ev.target.closest("button[data-act]");
  if (!b) return;
  if (b.dataset.act === "remove-model") {
    const name = b.dataset.name;
    if (Object.values(state.board).flat().includes(name)) return toast(L("cannot_remove_used"), true);
    const provider = providerOf(name);
    state.palette[provider] = state.palette[provider].filter((m) => m !== modelOf(name));
    changed();
  } else if (b.dataset.act === "test-model") {
    b.textContent = L("testing");
    await act(b, () => api("POST", "/api/models/test", { name: b.dataset.name }));
    b.textContent = L("test");
  }
});
// Only the models that the user added by name are saved; the tools list the others themselves.
const customModels = () => Object.fromEntries(Object.entries(state.palette)
  .map(([provider, models]) => [provider, models.filter((m) => !(state.auto[provider] || []).includes(m))]));
$("#board-preset").addEventListener("click", () => {
  if (!confirm(L("confirm_preset"))) return;
  state.flow = [...PRESET_FLOW];
  state.nodes = {};
  for (const [stage, names] of Object.entries(PRESET)) {
    const available = names.filter((n) => state.palette[n]);
    state.board[stage] = available.length ? [...available] : state.board[stage] || [Object.keys(state.palette)[0]];
  }
  changed();
});
window.addEventListener("beforeunload", (ev) => {
  if (state.tab === "prompts" && promptDirty()) ev.preventDefault();
});

// ---------- prompts ----------
// The publishing rules come first: they are the instructions that users write. The step instructions are technical.
const PLACEHOLDERS = ["target_lang", "source", "translation", "glossary", "references", "ref_langs", "context", "issues",
  "note_lang", "rules", "segment", "window", "ref_lang", "instructions"];

async function loadPrompts() {
  // The settings give the workflow, which numbers and names the steps that use each instruction.
  try {
    [state.prompts, state.settings] = await Promise.all([api("GET", "/api/prompts"), api("GET", "/api/settings")]);
  } catch (e) { return toast(e.message, true); }
  if (!state.prompt || !state.prompts.some((p) => p.name === state.prompt)) state.prompt = state.prompts[0].name;
  renderPrompts();
}

const promptDirty = () => {
  const p = state.prompts.find((x) => x.name === state.prompt);
  const text = $("#prompt textarea");
  return Boolean(p && text && text.value !== p.text);
};

const usedIn = (p) => p.steps.map((s) => stageName(s)).join(", ");

function renderPrompts() {
  const item = (p) => `
    <li><button type="button" data-name="${esc(p.name)}" class="${p.name === state.prompt ? "active" : ""}">
      <span class="pl-title">${esc(L("prompt_title_" + p.name))}${p.changed ? ` <span class="badge warn">${esc(L("changed"))}</span>` : ""}</span>
      <span class="pl-steps">${esc(p.name === "rules" ? L("all_steps") : usedIn(p) || L("not_in_flow"))}</span></button></li>`;
  const rules = state.prompts.filter((p) => p.name === "rules");
  const steps = state.prompts.filter((p) => p.name !== "rules");
  $("#prompt-list").innerHTML = `${rules.map(item).join("")}
    <li class="pl-group">${esc(L("step_prompts"))}<span>${esc(L("step_prompts_hint"))}</span></li>
    ${steps.map(item).join("")}`;

  const p = state.prompts.find((x) => x.name === state.prompt);
  const isRules = p.name === "rules";
  $("#prompt").className = "card prompt-editor";
  $("#prompt").innerHTML = `
    <div class="row prompt-head">
      <div>
        <h3>${esc(L("prompt_title_" + p.name))}</h3>
        <p class="muted small">${esc(isRules ? L("rules_intro") : p.steps.length ? L("prompt_used_in", { steps: usedIn(p) }) : L("prompt_unused"))}</p>
      </div>
      <div class="row">
        <span class="badge warn" data-role="prompt-dirty" hidden>${esc(L("unsaved"))}</span>
        ${p.has_default && p.changed ? `<button type="button" class="btn" data-act="restore">${esc(L("restore_default"))}</button>` : ""}
        <button type="button" class="btn primary" data-act="save" title="Ctrl+S / ⌘S">${esc(L("save"))}</button>
      </div>
    </div>
    ${p.name.startsWith("custom_") ? `<div class="notice small">${esc(L("prompt_custom_note"))}</div>` : ""}
    ${isRules ? "" : `<div class="notice small">${esc(L("prompts_note"))}</div>
      <details class="placeholders"><summary>${esc(L("required_placeholders"))}</summary>
        <dl>${p.required.map((r) => `<dt><code>{{${esc(r)}}}</code></dt><dd>${esc(PLACEHOLDERS.includes(r) ? L("ph_" + r) : "")}</dd>`).join("")}</dl>
      </details>`}
    <textarea spellcheck="${isRules ? "true" : "false"}" class="${isRules ? "rules-text" : ""}" aria-label="${esc(L("prompt_title_" + p.name))}">${esc(p.text)}</textarea>
    <p class="small muted">${esc(L("prompts_apply"))}</p>`;
}

$("#prompt-list").addEventListener("click", (ev) => {
  const b = ev.target.closest("button[data-name]");
  if (!b) return;
  if (promptDirty() && !confirm(L("confirm_discard"))) return;
  state.prompt = b.dataset.name;
  renderPrompts();
});
$("#prompt").addEventListener("input", (ev) => {
  if (ev.target.matches("textarea")) $('[data-role="prompt-dirty"]').hidden = !promptDirty();
});
async function savePrompt(button) {
  const r = await act(button, () => api("PUT", `/api/prompts/${encodeURIComponent(state.prompt)}`, { text: $("#prompt textarea").value }));
  if (r) loadPrompts();
}
$("#prompt").addEventListener("click", async (ev) => {
  const b = ev.target.closest("button[data-act]");
  if (!b) return;
  if (b.dataset.act === "save") return savePrompt(b);
  if (b.dataset.act === "restore") {
    if (!confirm(L("confirm_restore"))) return;
    const r = await act(b, () => api("POST", `/api/prompts/${encodeURIComponent(state.prompt)}/restore`));
    if (r) loadPrompts();
  }
});
document.addEventListener("keydown", (ev) => {
  if (state.tab === "prompts" && (ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === "s") {
    ev.preventDefault();
    savePrompt($('#prompt [data-act="save"]'));
  }
});

// ---------- start ----------
applyStaticTexts();
const startReady = (() => { try { return localStorage.getItem("setup-ready") === "1"; } catch { return false; } })();
showTab(["setup", "workflow", "books", "prompts"].includes(location.hash.slice(1)) ? location.hash.slice(1) : startReady ? "books" : "setup");
if (state.tab !== "setup") {
  api("GET", "/api/tools").then((data) => setToolsReady(toolsReady(data))).catch(() => {});
}
