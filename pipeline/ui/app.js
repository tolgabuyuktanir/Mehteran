"use strict";

// ---------- interface texts (Turkish and English) ----------
const I18N = {
  tr: {
    app_title: "Tercüme Masası",
    app_subtitle: "Tercüme ve tashih iş akışı",
    tab_setup: "Kurulum", tab_books: "Kitaplar", tab_prompts: "Talimatlar",
    setup_title: "Kurulum ve oturum",
    setup_intro: "Üç araç da kurulur. Oturum açmak, iş akışında kullanılan araçlar için gerekir. Bu işlem her bilgisayarda bir kez yapılır.",
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
    human_step: "7 · Teslim", human_who: "İnsan tercüman, insan editör",
    new_book: "Yeni kitap", new_book_placeholder: "örnek: ilmihal", add: "Ekle",
    no_books: "Henüz kitap yok.", running: "Çalışıyor",
    pick_book: "Soldan bir kitap seçin veya yeni bir kitap ekleyin.",
    source_intro: "Tek dosya: .docx, .epub, .md, .txt veya .pdf. En iyi sonuç .docx ve .epub ile alınır.",
    prepared: "Hazırlandı · {count} bölüm", not_prepared: "Henüz hazırlanmadı",
    reset_hint: "Kaynağı değiştirmek için çalışmayı sıfırlayın. Bütün dillerdeki ara çıktılar silinir.",
    reset_work: "Çalışmayı sıfırla",
    refs_intro: "Aynı kitabın yakın dillerdeki mevcut tercümeleri. Örnek: Norveççe için Danca ve İsveççe.",
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
    log: "Günlük", not_run_yet: "Henüz çalıştırılmadı.",
    translation: "Çeviri", report: "Rapor", close: "Kapat",
    pick_file: "Önce bir dosya seçin.", pick_ref_language: "Önce referansın dilini seçin.",
    uploaded: "Yüklendi.", upload_failed: "Yükleme başarısız.", output_unreadable: "Çıktı okunamadı.",
    confirm_delete_ref: "Bu referans tercüme ve hizalaması silinsin mi?",
    confirm_reset: "Bu kitabın bütün ara çıktıları (bütün dillerde) silinecek. Çıktı klasöründeki son kitaplar kalır. Devam edilsin mi?",
    confirm_redo: "Seçili bölümlerde \"{stage}\" ve sonraki adımların çıktısı silinip yeniden üretilecek. Devam edilsin mi?",
    prompts_intro: "Modellere verilen yönergeler. Değişiklik, kaydedildikten sonra işlenen bölümlerde geçerli olur. Önceden işlenmiş bölümlere uygulamak için kitap ekranında \"Yeniden üret\" seçeneğini kullanın.",
    changed: "değiştirildi", restore_default: "Varsayılana dön",
    required_placeholders: "Metinde bulunması zorunlu yer tutucular (pipeline buralara kaynak metni, çeviriyi, sözlüğü vb. koyar):",
    prompts_note: "Talimatlar İngilizce yazılmıştır; modeller İngilizce talimatı daha tutarlı uygular. Türkçe ekleme yapabilirsiniz. Yayın ilkelerinize özel kuralları (örneğin âyet meallerinin biçimi, saygı ifadeleri) buraya ekleyin. Modellerin yazdığı açıklamalar, çalıştırmayı başlattığınız arayüz dilinde olur.",
    confirm_discard: "Kaydedilmemiş değişiklikler kaybolacak. Devam edilsin mi?",
    confirm_restore: "Yaptığınız değişiklikler silinip varsayılan talimat geri yüklenecek. Devam edilsin mi?",
    request_failed: "İstek başarısız ({status})",
    stage_prepare: "Hazırlık", stage_align: "Hizalama", stage_glossary: "Sözlük", stage_translate: "1 · İlk tercüme",
    stage_review1: "2 · Tashih", stage_revise1: "3 · Tashihleri uygula", stage_source_check: "4 · Kaynak kontrolü",
    stage_review2: "5 · İkinci tashih", stage_reconcile: "6 · Uzlaştırma", stage_assemble: "Birleştirme",
    flow_align: "Hazırlık · hizalama", flow_glossary: "Hazırlık · sözlük", flow_translate: "1 · İlk tercüme",
    flow_review1: "2 · Tashih", flow_revise1: "3 · Tashihleri uygula", flow_source_check: "4 · Baştan kaynak kontrolü",
    flow_review2: "5 · İkinci bağımsız tashih", flow_reconcile: "6 · İki raporu uzlaştır",
    quota_now: "Kullanım sınırında · {time} saatinde kendiliğinden yeniden denenecek",
    quota_last: "Son kullanım sınırı uyarısı: {time}",
    unaligned: "Referansta bulunamayan bölümler: {segments}. Bu bölümler bu referans olmadan çevrilir.",
    estimate_title: "Başlamadan önce",
    estimate_segments: "{selected} bölüm işlenecek (kitapta {total} bölüm)",
    estimate_guess: "Kitap henüz hazırlanmadığı için bölüm sayısı kaynak dosyadan tahmin edildi.",
    estimate_calls: "Gereken model çağrısı: {calls}",
    estimate_time: "Tahmini süre: {time}. Gerçek süre modellerin hızına ve kullanım sınırlarına göre değişir.",
    estimate_nothing: "Seçilen bölümlerde yapılacak iş kalmadı.",
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
    quota_waiting_line: "{provider} kullanım sınırına ulaştı. {time} saatinde kendiliğinden devam edecek.",
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
    workflow_intro: "Model kartlarını soldan sürükleyip adımların üzerine bırakın veya adımdaki listeden seçin. Adımların sırası sabittir: her adım bir öncekinin sonucunu kullanır. Metni değiştiren her adımı, o değişikliği yapmamış bir modelin denetlemesi önerilir.",
    unsaved: "Kaydedilmedi", preset: "Şemadaki dağılım", revert: "Geri al",
    default_model: "varsayılan model", add_model_placeholder: "model adı (örnek: opus)", fetch_models: "Model listesini getir",
    remove: "Kaldır", choose_model: "Model seç…", add_reviewer: "Tashihçi ekle…", parallel_tag: "paralel · en çok 4 model",
    step_desc_align: "Her Türkçe bölümün referans tercümedeki karşılığını bulur. Referans yoksa atlanır.",
    step_desc_glossary: "Dinî terimleri ve özel adları çıkarır; dil başına ortak sözlüğe yeni terimleri ekler.",
    step_desc_translate: "Türkçe kaynak, referans pasajlar ve sözlükle ilk tercümeyi yapar.",
    step_desc_review1: "Tercümeyi Türkçe kaynakla cümle cümle karşılaştırır ve bulgu raporu yazar.",
    step_desc_revise1: "Tashih bulgularını Türkçe kaynağa göre tartar; haklı olanları uygular.",
    step_desc_source_check: "Önceki adımlara güvenmeden metni kaynakla baştan karşılaştırır ve düzeltir.",
    step_desc_review2: "İkinci bağımsız tashih: modeller birbirinden habersiz bulgu raporu yazar.",
    step_desc_reconcile: "Tashih raporlarını kaynağa göre uzlaştırır ve son metni üretir.",
    step_desc_human: "Çeviri ve rapor insan tercümana teslim edilir; ardından insan editör okur.",
    warn_self_review1: "{model} hem tercüme ediyor hem kendi tercümesini tashih ediyor. Tashihe başka bir model koyun.",
    warn_self_review2: "{model} 4. adımda metni düzeltiyor ve 5. adımda kendi düzeltmesini denetliyor.",
    warn_source_check: "{model} baştan kaynak kontrolünü, metni daha önce yazdığı hâlde yapıyor. Bağımsız bir model daha güvenilir olur.",
    info_same_provider: "\"{step}\" adımındaki bütün modeller tercümeyi yapan modelle aynı şirketin. Farklı bir şirketin modeli hataları daha iyi yakalar.",
    info_one_reviewer: "İkinci tashihte tek model var. Şemada iki bağımsız model öngörülüyor.",
    cannot_remove_used: "Bu model bir adımda kullanılıyor; önce adımdan kaldırın.",
    model_name_invalid: "Model adı harf veya rakamla başlamalı; yalnızca harf, rakam ve . _ : - içerebilir.",
    upload_bad_type: "Bu dosya türü desteklenmiyor. Desteklenenler: .docx, .epub, .md, .txt, .pdf",
    upload_bad_size: "Dosya boş veya çok büyük (en çok 300 MB).",
    models_found: "{count} model bulundu.", max_reviewers: "Bu adıma en çok 4 model atanabilir.",
    confirm_leave_board: "İş akışında kaydedilmemiş değişiklikler var. Sayfadan çıkılsın mı?",
    export_label: "Dışa aktar", fmt_md: "Markdown", fmt_docx: "Word", fmt_pdf: "PDF", fmt_html: "HTML",
    pdf_hint: "PDF: açılan sayfada yazdırma penceresinden \"PDF olarak kaydet\" seçin.",
    step_install_hint: "Claude Code, Codex ve Gemini bu bilgisayara kurulur. Gerekirse Node.js de uygulamanın klasörüne indirilir. Yönetici izni gerekmez.",
    first_book_title: "İlk kitabınızı ekleyin",
    first_book_intro: "Kitaba kısa bir ad verin. Sonra Türkçe kaynağı ve varsa yakın dillerdeki tercümeleri yükleyeceksiniz.",
    create_book: "Kitabı oluştur",
    step_source: "Türkçe kaynak", step_refs: "Referans tercümeler", step_run: "Çeviri", step_result: "Sonuç",
    locked_refs: "Önce Türkçe kaynağı yükleyin.", locked_run: "Önce kaynak ve referans adımlarını tamamlayın.",
    locked_result: "Çeviri bitince burada okuyup indirebilirsiniz.",
    summary_source_empty: "Kaynak dosyayı yükleyin", summary_source: "{file} · {count} bölüm",
    summary_refs_none: "Referans kullanılmıyor", summary_refs_optional: "İsteğe bağlı, doğruluğu artırır",
    summary_running: "{language} · {stage} · {done}/{total}",
    summary_run_more: "Başka bir dile çevirmek için açın", summary_run_ready: "Hedef dili seçip başlatın",
    continue: "Devam et", skip_refs: "Referanssız devam et",
    progress_details: "Adım adım ilerleme",
    review_row: "{reviewer}: {issues} bulgu · {segments} bölümün {empty} tanesinde bulgu yok",
    review_quiet: "Çoğu bölümde hiç bulgu yazmadı. Birkaç bölümü elle kontrol edin.",
    review_missed: "{count} bölümde bulgu yazmadı ama sonradan bu bölümlerde ciddi hata bulundu: {segments}",
    review_attention: "Tashihçi uyarısı",
    setup_banner: "Araçlar henüz hazır değil. Çeviri başlatmadan önce kurulumu tamamlayın.", go_setup: "Kuruluma git",
  },
  en: {
    app_title: "Translation Desk",
    app_subtitle: "Translation and review workflow",
    tab_setup: "Setup", tab_books: "Books", tab_prompts: "Instructions",
    setup_title: "Setup and sign-in",
    setup_intro: "All three tools are installed. You must sign in to the tools that the workflow uses. You do this once on each computer.",
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
    human_step: "7 · Delivery", human_who: "Human translator, human editor",
    new_book: "New book", new_book_placeholder: "for example: ilmihal", add: "Add",
    no_books: "No books yet.", running: "Running",
    pick_book: "Select a book on the left, or add a new book.",
    source_intro: "One file: .docx, .epub, .md, .txt or .pdf. The best results come from .docx and .epub.",
    prepared: "Prepared · {count} segments", not_prepared: "Not prepared yet",
    reset_hint: "To change the source, reset the work. The intermediate output of all languages is deleted.",
    reset_work: "Reset work",
    refs_intro: "Existing translations of the same book in related languages. Example: Danish and Swedish for Norwegian.",
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
    log: "Log", not_run_yet: "Not run yet.",
    translation: "Translation", report: "Report", close: "Close",
    pick_file: "Select a file first.", pick_ref_language: "Select the language of the reference first.",
    uploaded: "Uploaded.", upload_failed: "Upload failed.", output_unreadable: "Cannot read the output.",
    confirm_delete_ref: "Delete this reference translation and its alignment?",
    confirm_reset: "All intermediate output of this book (in all languages) will be deleted. The final books in the output folder stay. Continue?",
    confirm_redo: "For the selected segments, the output of \"{stage}\" and of the later steps will be deleted and produced again. Continue?",
    prompts_intro: "The instructions given to the models. A change applies to the segments processed after you save it. To apply it to segments already processed, use the \"Produce again\" option on the book screen.",
    changed: "changed", restore_default: "Restore default",
    required_placeholders: "Placeholders that the text must contain (the pipeline inserts the source text, the translation, the glossary, etc. there):",
    prompts_note: "The instructions are in English, because the models follow English instructions more consistently. You can add text in Turkish. Add the rules specific to your publishing policy here (for example, the form of Qur'an translations or honorific formulas). The explanations that the models write are in the interface language in which you start the run.",
    confirm_discard: "Unsaved changes will be lost. Continue?",
    confirm_restore: "Your changes will be deleted and the default instructions restored. Continue?",
    request_failed: "Request failed ({status})",
    stage_prepare: "Preparation", stage_align: "Alignment", stage_glossary: "Glossary", stage_translate: "1 · First translation",
    stage_review1: "2 · Review", stage_revise1: "3 · Apply review", stage_source_check: "4 · Source check",
    stage_review2: "5 · Second review", stage_reconcile: "6 · Reconcile", stage_assemble: "Assembly",
    flow_align: "Preparation · alignment", flow_glossary: "Preparation · glossary", flow_translate: "1 · First translation",
    flow_review1: "2 · Review", flow_revise1: "3 · Apply the review", flow_source_check: "4 · Source check from the start",
    flow_review2: "5 · Second independent review", flow_reconcile: "6 · Reconcile the two reports",
    quota_now: "At its usage limit · tries again by itself at {time}",
    quota_last: "Last usage-limit warning: {time}",
    unaligned: "Segments not found in the reference: {segments}. These segments are translated without this reference.",
    estimate_title: "Before you start",
    estimate_segments: "{selected} segments will be processed (the book has {total})",
    estimate_guess: "The book is not prepared yet, so the number of segments is estimated from the source file.",
    estimate_calls: "Model calls needed: {calls}",
    estimate_time: "Estimated time: {time}. The real time depends on the speed of the models and on the usage limits.",
    estimate_nothing: "Nothing is left to do for the selected segments.",
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
    quota_waiting_line: "{provider} reached its usage limit. It continues by itself at {time}.",
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
    workflow_intro: "Drag model cards from the left onto the steps, or choose from the list in a step. The order of the steps is fixed: each step uses the result of the one before. Each step that changes the text should be checked by a model that did not make the change.",
    unsaved: "Not saved", preset: "Diagram assignment", revert: "Revert",
    default_model: "default model", add_model_placeholder: "model name (for example: opus)", fetch_models: "Fetch model list",
    remove: "Remove", choose_model: "Choose a model…", add_reviewer: "Add a reviewer…", parallel_tag: "parallel · up to 4 models",
    step_desc_align: "Finds each Turkish segment in the reference translations. Skipped when there is no reference.",
    step_desc_glossary: "Extracts religious terms and proper names; adds new terms to the shared glossary of the language.",
    step_desc_translate: "Makes the first translation with the Turkish source, the reference passages and the glossary.",
    step_desc_review1: "Compares the translation with the Turkish source sentence by sentence and writes a findings report.",
    step_desc_revise1: "Weighs the review findings against the Turkish source and applies the correct ones.",
    step_desc_source_check: "Compares the text with the source from the start, without relying on earlier steps, and corrects it.",
    step_desc_review2: "Second independent review: the models write findings reports without seeing each other.",
    step_desc_reconcile: "Reconciles the review reports against the source and produces the final text.",
    step_desc_human: "The translation and the report go to the human translator; then a human editor reads it.",
    warn_self_review1: "{model} translates and also reviews its own translation. Put a different model on the review.",
    warn_self_review2: "{model} corrects the text in step 4 and checks its own correction in step 5.",
    warn_source_check: "{model} does the source check although it wrote the text earlier. An independent model is more reliable.",
    info_same_provider: "All models in \"{step}\" are from the same company as the translating model. A model from a different company catches errors better.",
    info_one_reviewer: "The second review has one model. The diagram calls for two independent models.",
    cannot_remove_used: "This model is used in a step; remove it from the step first.",
    model_name_invalid: "A model name must start with a letter or digit and can contain only letters, digits and . _ : -",
    upload_bad_type: "This file type is not supported. Supported: .docx, .epub, .md, .txt, .pdf",
    upload_bad_size: "The file is empty or too large (at most 300 MB).",
    models_found: "{count} models found.", max_reviewers: "This step takes at most 4 models.",
    confirm_leave_board: "The workflow has unsaved changes. Leave the page?",
    export_label: "Export", fmt_md: "Markdown", fmt_docx: "Word", fmt_pdf: "PDF", fmt_html: "HTML",
    pdf_hint: "PDF: in the page that opens, choose \"Save as PDF\" in the print dialog.",
    step_install_hint: "Claude Code, Codex and Gemini are installed on this computer. If needed, Node.js is downloaded into the application's folder. No administrator rights are needed.",
    first_book_title: "Add your first book",
    first_book_intro: "Give the book a short name. Then you upload the Turkish source and, if you have them, translations in related languages.",
    create_book: "Create book",
    step_source: "Turkish source", step_refs: "Reference translations", step_run: "Translation", step_result: "Result",
    locked_refs: "Upload the Turkish source first.", locked_run: "Complete the source and reference steps first.",
    locked_result: "When the translation is finished, you read and download it here.",
    summary_source_empty: "Upload the source file", summary_source: "{file} · {count} segments",
    summary_refs_none: "No references used", summary_refs_optional: "Optional, improves accuracy",
    summary_running: "{language} · {stage} · {done}/{total}",
    summary_run_more: "Open to translate into another language", summary_run_ready: "Choose the target language and start",
    continue: "Continue", skip_refs: "Continue without references",
    progress_details: "Progress step by step",
    review_row: "{reviewer}: {issues} findings · no findings in {empty} of {segments} segments",
    review_quiet: "Wrote no findings in most segments. Check a few segments by hand.",
    review_missed: "Wrote no findings in {count} segments, but serious errors were found in them later: {segments}",
    review_attention: "Reviewer warning",
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
  const res = await fetch(path, opts);
  let data = {};
  try { data = await res.json(); } catch { /* empty answer */ }
  if (!res.ok) throw new Error(data.error || L("request_failed", { status: res.status }));
  return data;
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

const PROVIDER_NAMES = { claude: "Claude", chatgpt: "ChatGPT", gemini: "Gemini" };
const providerName = (p) => PROVIDER_NAMES[p] || p;
const providerOf = (name) => String(name).split("/")[0];
const modelOf = (name) => String(name).split("/").slice(1).join("/");
function modelLabel(name) {
  const provider = providerOf(name);
  const fallback = state.settings?.providers?.[provider]?.default_model;
  return `${providerName(provider)} · ${modelOf(name) || fallback || L("default_model")}`;
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
const stageName = (stage) => L("stage_" + stage);
const state = { settings: null, books: [], current: null, poll: null, prompts: [], prompt: null, toolPoll: null, tab: "setup",
  openStep: {}, skipRefs: new Set(), toolsReady: null };

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
  if (state.tab === "workflow" && state.board) return renderBoard();  // keep unsaved board changes
  showTab(state.tab);
}));

function showTab(name) {
  if (state.tab === "workflow" && name !== "workflow" && state.board && boardDirty() && !confirm(L("confirm_leave_board"))) return;
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
  const total = data.tools.length;
  const installed = data.tools.filter((tool) => tool.installed).length;
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
  const signIn = !tool.installed ? "" : tool.signed_in
    ? `<span class="badge good">${esc(L("signed_in"))}${tool.sign_in_info ? " · " + esc(tool.sign_in_info) : ""}</span>`
    : `<span class="badge warn">${esc(L("not_signed_in"))}</span>`;
  const job = tool.job;
  const running = job && job.running;
  const actions = [];
  if (!tool.installed || (job && !running && job.code !== 0)) {
    actions.push(`<button type="button" class="btn primary" data-act="install" data-id="${esc(tool.id)}" ${running ? "disabled" : ""}>${esc(L(running ? "installing" : "install"))}</button>`);
  }
  if (tool.installed) {
    const main = tool.signed_in ? "" : "primary";
    if (tool.id === "gemini") {
      actions.push(`<button type="button" class="btn ${main}" data-act="login" data-method="google" data-id="${esc(tool.id)}">${esc(L("with_google"))}</button>`);
    } else {
      const label = tool.id === "codex" ? "with_chatgpt" : "with_claude";
      actions.push(`<button type="button" class="btn ${main}" data-act="login" data-method="terminal" data-id="${esc(tool.id)}" ${terminal ? "" : "disabled"}>${esc(L(label))}</button>`);
    }
    if (tool.id !== "claude") actions.push(`<button type="button" class="btn" data-act="key" data-id="${esc(tool.id)}">${esc(L("with_key"))}</button>`);
    if (tool.signed_in) actions.push(`<button type="button" class="btn" data-act="test" data-id="${esc(tool.id)}">${esc(L("test"))}</button>`);
  }
  const uses = tool.stages.length ? L("used_in", { stages: tool.stages.map(stageName).join(", ") }) : L("not_used");
  return `
    <article class="card tool" data-id="${esc(tool.id)}">
      <div class="tool-head"><h3>${esc(tool.name)}</h3><span class="muted small">${esc(tool.version)}</span></div>
      <div class="badges">${installed}${signIn}</div>
      <div class="uses">${esc(uses)}</div>
      <div class="small muted">${esc(tool.requirements)}</div>
      ${tool.installed && !tool.signed_in ? `<div class="small">${esc(tool.sign_in_help)}</div>` : ""}
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
    return `<div class="step ${providers.length === 1 ? esc(providerOf(providers[0])) : ""}"><b>${esc(L("flow_" + stage))}</b>${providers.map((p) => esc(modelLabel(p))).join(" + ")}</div>`;
  };
  $("#flow").innerHTML = ["align", "glossary", "translate", "review1", "revise1", "source_check", "review2", "reconcile"].map(step).join("")
    + `<div class="step human"><b>${esc(L("human_step"))}</b>${esc(L("human_who"))}</div>`;
}

// All tools are installed. A sign-in is required only for the tools that the workflow uses.
const neededTools = (data) => data.tools.filter((tool) => tool.stages.length);
const toolsReady = (data) => data.tools.every((tool) => tool.installed) && neededTools(data).every((tool) => tool.signed_in);

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
      if (el) el.innerHTML = html(book);
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
  const current = book.running ? "run" : (steps.find((s) => !s.done && !s.locked) || steps[3]).id;
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
      const cls = [s.done ? "done" : "", s.id === current ? "current" : "", s.locked ? "locked" : "", isOpen ? "open" : ""].join(" ");
      return `<li class="jstep ${cls}" data-step="${s.id}">
          <span class="jnode" aria-hidden="true">${s.done ? "✓" : i + 1}</span>
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
    </details>`;
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
    case "refs":
      return book.references.length ? book.references.map((r) => languageName(r.lang)).join(", ") : L(step.done ? "summary_refs_none" : "summary_refs_optional");
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
  return `<p class="muted">${esc(L("source_intro"))}</p>${file}${action}
    ${book.source.length && !book.prepared ? `<div class="row next"><button type="button" class="btn primary" data-act="open-step" data-step="refs">${esc(L("continue"))}</button></div>` : ""}`;
}

function refsStepHtml(book) {
  return `<p class="muted">${esc(L("refs_intro"))}</p>
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
  for (const [provider, q] of Object.entries(run.quota || {})) {
    lines.push(`<div class="notice warn">${esc(L("quota_waiting_line", { provider: providerName(provider), time: fmtTime(q.until) }))}${q.message ? `<br><span class="small">${esc(q.message)}</span>` : ""}</div>`);
  }
  if ((run.quota_events || []).length) lines.push(`<div class="muted small">${esc(L("quota_history", { count: run.quota_events.length }))}</div>`);
  if (book.running) lines.push(`<div class="small ${run.awake ? "muted" : "warn-text"}">${esc(L(run.awake ? "awake_on" : "awake_off"))}</div>`);
  if (run.error) lines.push(`<div class="notice bad">${esc(run.error)}</div>`);
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
          <div class="small">${esc(L(state.settings.keep_awake ? "awake_note" : "awake_off"))}</div>` : `<div>${esc(L("estimate_nothing"))}</div>`}
      </div>`;
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
    </div>`;
}

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

function upload(container, book) {
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
    case "open-step": {
      const open = state.openStep[book] || bookSteps(state.books.find((x) => x.name === book)).current;
      state.openStep[book] = b.dataset.step === open && b.classList.contains("jhead") ? "none" : b.dataset.step;
      return renderBook(true);
    }
    case "refs-done":
      state.skipRefs.add(book);
      return renderBook();
  }
});

$("#book").addEventListener("change", (ev) => {
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
    $("#reader").showModal();
  } catch (e) { toast(e.message, true); }
}
$("#reader-close").addEventListener("click", () => $("#reader").close());

// ---------- workflow board ----------
const BOARD_STAGES = ["align", "glossary", "translate", "review1", "revise1", "source_check", "review2", "reconcile"];
const STEP_NUMBERS = { align: "H", glossary: "H", translate: "1", review1: "2", revise1: "3", source_check: "4", review2: "5", reconcile: "6" };
const PRESET = { align: ["gemini"], glossary: ["claude"], translate: ["chatgpt"], review1: ["gemini"], revise1: ["chatgpt"],
                 source_check: ["claude"], review2: ["chatgpt", "gemini"], reconcile: ["claude"] };
const MODEL_RE = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,79}$/;
const isReview = (stage) => (state.settings?.review_stages || []).includes(stage);
const boardSnapshot = () => JSON.stringify({ board: state.board, palette: state.palette });
const boardDirty = () => boardSnapshot() !== state.boardSaved;

async function loadBoard() {
  try { state.settings = await api("GET", "/api/settings"); } catch (e) { return toast(e.message, true); }
  state.board = JSON.parse(JSON.stringify(state.settings.stages));
  state.palette = {};
  state.suggestions = state.suggestions || {};
  for (const [provider, info] of Object.entries(state.settings.providers)) state.palette[provider] = [...info.models];
  for (const names of Object.values(state.board)) {
    for (const name of names) {
      const provider = providerOf(name), model = modelOf(name);
      if (model && state.palette[provider] && !state.palette[provider].includes(model)) state.palette[provider].push(model);
    }
  }
  state.boardSaved = boardSnapshot();
  renderBoard();
}

function allNames() {
  return Object.entries(state.palette).flatMap(([provider, models]) => [provider, ...models.map((m) => `${provider}/${m}`)]);
}

function boardWarnings(b) {
  const out = [];
  const translator = b.translate[0], reviser = b.revise1[0], checker = b.source_check[0];
  if (b.review1.includes(translator)) out.push(["warn", L("warn_self_review1", { model: modelLabel(translator) })]);
  if (b.review2.includes(checker)) out.push(["warn", L("warn_self_review2", { model: modelLabel(checker) })]);
  if (checker === translator || checker === reviser) out.push(["warn", L("warn_source_check", { model: modelLabel(checker) })]);
  if (!b.review1.includes(translator) && b.review1.every((n) => providerOf(n) === providerOf(translator))) {
    out.push(["", L("info_same_provider", { step: L("flow_review1") })]);
  }
  if (b.review2.length < 2) out.push(["", L("info_one_reviewer")]);
  return out;
}

function renderBoard() {
  const used = new Set(Object.values(state.board).flat());
  $("#palette").innerHTML = Object.entries(state.palette).map(([provider, models]) => {
    const tool = state.settings.providers[provider]?.tool;
    const suggestions = [...new Set([...(state.settings.providers[provider]?.suggestions || []), ...(state.suggestions[provider] || [])])];
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
        ${models.map((m) => card(`${provider}/${m}`, true)).join("")}
        <form class="add-model" data-provider="${esc(provider)}">
          <input list="dl-${esc(provider)}" placeholder="${esc(L("add_model_placeholder"))}" aria-label="${esc(L("add_model_placeholder"))}">
          <button type="submit" class="btn small">${esc(L("add"))}</button>
        </form>
        <datalist id="dl-${esc(provider)}">${suggestions.map((m) => `<option value="${esc(m)}">`).join("")}</datalist>
        ${tool === "gemini" ? `<button type="button" class="icon-btn" data-act="fetch-models" data-tool="${esc(tool)}" data-provider="${esc(provider)}">${esc(L("fetch_models"))}</button>` : ""}
      </section>`;
  }).join("");

  const names = allNames();
  const steps = BOARD_STAGES.map((stage) => {
    const assigned = state.board[stage] || [];
    const review = isReview(stage);
    const chips = assigned.map((name) => `
      <span class="chip-model ${esc(providerOf(name))}">${esc(modelLabel(name))}
        ${review && assigned.length > 1 ? `<button type="button" class="icon-btn" data-act="unassign" data-stage="${stage}" data-name="${esc(name)}" aria-label="${esc(L("remove"))}">×</button>` : ""}
      </span>`).join("");
    const options = names.filter((n) => !assigned.includes(n)).map((n) => `<option value="${esc(n)}">${esc(modelLabel(n))}</option>`).join("");
    return `<li class="step-row" data-stage="${stage}">
        <div class="step-no">${STEP_NUMBERS[stage]}</div>
        <div>
          <div class="row" style="justify-content:space-between"><b>${esc(L("flow_" + stage))}</b>${review ? `<span class="parallel-tag">${esc(L("parallel_tag"))}</span>` : ""}</div>
          <div class="desc">${esc(L("step_desc_" + stage))}</div>
          <div class="dropzone" data-stage="${stage}">
            ${chips}
            <select data-act="assign" data-stage="${stage}" aria-label="${esc(L(review ? "add_reviewer" : "choose_model"))}">
              <option value="">${esc(L(review ? "add_reviewer" : "choose_model"))}</option>${options}
            </select>
          </div>
        </div>
      </li>`;
  });
  steps.push(`<li class="step-row step-human"><div class="step-no">7</div><div><b>${esc(L("human_step"))}</b><div class="desc">${esc(L("step_desc_human"))}</div></div></li>`);
  $("#steps").innerHTML = steps.join("");

  $("#board-warnings").innerHTML = boardWarnings(state.board)
    .map(([tone, text]) => `<div class="notice ${tone}">${esc(text)}</div>`).join("");
  $("#board-dirty").hidden = !boardDirty();
}

function assign(stage, name) {
  const current = state.board[stage];
  if (isReview(stage)) {
    if (current.includes(name)) return;
    if (current.length >= 4) return toast(L("max_reviewers"), true);
    current.push(name);
  } else {
    state.board[stage] = [name];
  }
  renderBoard();
}

$("#palette").addEventListener("dragstart", (ev) => {
  const card = ev.target.closest(".model-card");
  if (card) ev.dataTransfer.setData("text/plain", card.dataset.name);
});
$("#steps").addEventListener("dragover", (ev) => {
  const zone = ev.target.closest(".dropzone");
  if (!zone) return;
  ev.preventDefault();
  zone.classList.add("over");
});
$("#steps").addEventListener("dragleave", (ev) => {
  const zone = ev.target.closest(".dropzone");
  if (zone && !zone.contains(ev.relatedTarget)) zone.classList.remove("over");
});
$("#steps").addEventListener("drop", (ev) => {
  const zone = ev.target.closest(".dropzone");
  if (!zone) return;
  ev.preventDefault();
  const name = ev.dataTransfer.getData("text/plain");
  if (name && allNames().includes(name)) assign(zone.dataset.stage, name);
});
$("#steps").addEventListener("change", (ev) => {
  const select = ev.target.closest('select[data-act="assign"]');
  if (select && select.value) assign(select.dataset.stage, select.value);
});
$("#steps").addEventListener("click", (ev) => {
  const b = ev.target.closest('button[data-act="unassign"]');
  if (!b) return;
  state.board[b.dataset.stage] = state.board[b.dataset.stage].filter((n) => n !== b.dataset.name);
  renderBoard();
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
  renderBoard();
});
$("#palette").addEventListener("click", async (ev) => {
  const b = ev.target.closest("button[data-act]");
  if (!b) return;
  if (b.dataset.act === "remove-model") {
    const name = b.dataset.name;
    if (Object.values(state.board).flat().includes(name)) return toast(L("cannot_remove_used"), true);
    const provider = providerOf(name);
    state.palette[provider] = state.palette[provider].filter((m) => m !== modelOf(name));
    renderBoard();
  } else if (b.dataset.act === "test-model") {
    b.textContent = L("testing");
    await act(b, () => api("POST", "/api/models/test", { name: b.dataset.name }));
    b.textContent = L("test");
  } else if (b.dataset.act === "fetch-models") {
    const r = await act(b, () => api("GET", `/api/tools/${encodeURIComponent(b.dataset.tool)}/models`));
    if (r) {
      state.suggestions[b.dataset.provider] = r.models;
      toast(L("models_found", { count: r.models.length }));
      renderBoard();
    }
  }
});
$("#board-save").addEventListener("click", async (ev) => {
  const r = await act(ev.target, () => api("PUT", "/api/stages", { stages: state.board, models: state.palette }));
  if (r) loadBoard();
});
$("#board-revert").addEventListener("click", loadBoard);
$("#board-preset").addEventListener("click", () => {
  for (const [stage, names] of Object.entries(PRESET)) {
    const available = names.filter((n) => state.palette[n]);
    if (available.length) state.board[stage] = [...available];
  }
  renderBoard();
});
window.addEventListener("beforeunload", (ev) => {
  if (state.tab === "workflow" && state.board && boardDirty()) ev.preventDefault();
});

// ---------- prompts ----------
async function loadPrompts() {
  try { state.prompts = await api("GET", "/api/prompts"); } catch (e) { return toast(e.message, true); }
  if (!state.prompt) state.prompt = state.prompts[0].name;
  renderPrompts();
}

function renderPrompts() {
  $("#prompt-list").innerHTML = state.prompts.map((p) => `
    <li><button type="button" data-name="${esc(p.name)}" class="${p.name === state.prompt ? "active" : ""}">
      ${esc(p.name)}${p.changed ? ` <span class="badge warn" style="display:inline-flex">${esc(L("changed"))}</span>` : ""}
      <span>${esc(p.description)}</span></button></li>`).join("");
  const p = state.prompts.find((x) => x.name === state.prompt);
  $("#prompt").className = "card prompt-editor";
  $("#prompt").innerHTML = `
    <div class="row" style="justify-content:space-between">
      <div><h3>${esc(p.name)}</h3><p class="muted small">${esc(p.description)}</p></div>
      <div class="row">
        ${p.has_default && p.changed ? `<button type="button" class="btn" data-act="restore">${esc(L("restore_default"))}</button>` : ""}
        <button type="button" class="btn primary" data-act="save">${esc(L("save"))}</button>
      </div>
    </div>
    <div class="stack">
      <span class="small muted">${esc(L("required_placeholders"))}</span>
      <div class="chips">${p.required.map((r) => `<span class="chip">{{${esc(r)}}}</span>`).join("")}</div>
    </div>
    <textarea spellcheck="false">${esc(p.text)}</textarea>
    <p class="small muted">${esc(L("prompts_note"))}</p>`;
}

$("#prompt-list").addEventListener("click", (ev) => {
  const b = ev.target.closest("button[data-name]");
  if (!b) return;
  const current = state.prompts.find((x) => x.name === state.prompt);
  const text = $("#prompt textarea");
  if (current && text && text.value !== current.text && !confirm(L("confirm_discard"))) return;
  state.prompt = b.dataset.name;
  renderPrompts();
});
$("#prompt").addEventListener("click", async (ev) => {
  const b = ev.target.closest("button[data-act]");
  if (!b) return;
  const name = encodeURIComponent(state.prompt);
  if (b.dataset.act === "save") {
    const r = await act(b, () => api("PUT", `/api/prompts/${name}`, { text: $("#prompt textarea").value }));
    if (r) loadPrompts();
  } else if (b.dataset.act === "restore") {
    if (!confirm(L("confirm_restore"))) return;
    const r = await act(b, () => api("POST", `/api/prompts/${name}/restore`));
    if (r) loadPrompts();
  }
});

// ---------- start ----------
applyStaticTexts();
const startReady = (() => { try { return localStorage.getItem("setup-ready") === "1"; } catch { return false; } })();
showTab(["setup", "workflow", "books", "prompts"].includes(location.hash.slice(1)) ? location.hash.slice(1) : startReady ? "books" : "setup");
if (state.tab !== "setup") {
  api("GET", "/api/tools").then((data) => setToolsReady(toolsReady(data))).catch(() => {});
}
