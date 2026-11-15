"""User-facing messages in Turkish and English.

The language is chosen per web request (set_request) or once per process (set_default: command line,
or the TP_LANG environment variable that the web interface passes to the pipeline process).
Prompts sent to the models are not translated; only the language of the notes they write changes (note_language).
"""

from __future__ import annotations

import os
import threading

LANGUAGES = ("tr", "en")
_default = os.environ.get("TP_LANG") if os.environ.get("TP_LANG") in LANGUAGES else "tr"
_local = threading.local()


def set_default(lang: str | None) -> None:
    global _default
    if lang in LANGUAGES:
        _default = lang


def set_request(lang: str | None) -> None:
    """Language for the current thread only (one web request)."""
    _local.lang = lang if lang in LANGUAGES else None


def current() -> str:
    return getattr(_local, "lang", None) or _default


def note_language() -> str:
    """The language in which the models write explanations, notes and reasons."""
    return {"tr": "Turkish", "en": "English"}[current()]


def t(key: str, **values) -> str:
    text = MESSAGES[key][current()]
    return text.format(**values) if values else text


MESSAGES = {
    # --- general ---
    "error": {"tr": "HATA", "en": "ERROR"},
    "interrupted": {"tr": "Durduruldu. Aynı komutla kaldığı yerden devam edebilirsiniz.",
                    "en": "Stopped. Run the same command again to continue where it stopped."},
    "config_missing": {"tr": "Ayar dosyası yok: {path}", "en": "Configuration file not found: {path}"},
    "config_invalid": {"tr": "config.toml okunamadı: {error}", "en": "Cannot read config.toml: {error}"},
    "unknown_language": {
        "tr": "'{code}' dil kodu tanımlı değil. config.toml dosyasında [languages] altına ekleyin, örnek: {code} = \"Language name\"",
        "en": "Language code '{code}' is not defined. Add it under [languages] in config.toml, for example: {code} = \"Language name\""},

    # --- documents ---
    "unsupported_file": {"tr": "Desteklenmeyen dosya türü: {name} (desteklenen: {supported})",
                         "en": "Unsupported file type: {name} (supported: {supported})"},
    "pdftotext_missing": {
        "tr": "{name}: PDF okumak için PDF okuyucu (Poppler) gerekli. Kurulum sekmesinde \"PDF okuyucu\" kartındaki \"Kur\" "
              "düğmesine basın (komut satırında: ./translate install pdf). Mümkünse kitabı .docx veya .epub olarak verin.",
        "en": "{name}: reading a PDF needs the PDF reader (Poppler). Click \"Install\" on the \"PDF reader\" card of the Setup tab "
              "(on the command line: ./translate install pdf). If possible, supply the book as .docx or .epub."},
    "pdf_no_text": {
        "tr": "{name} dosyasında metin yok; büyük olasılıkla taranmış (resim olarak kaydedilmiş) bir PDF. Önce bir OCR programıyla "
              "metne çevirin (örneğin Adobe Acrobat veya ABBYY FineReader) ya da kitabın .docx veya .epub hâlini verin.",
        "en": "{name} contains no text; it is probably a scanned PDF (saved as images). Convert it to text with an OCR program first "
              "(for example Adobe Acrobat or ABBYY FineReader), or supply the book as .docx or .epub."},
    "xml_entity": {"tr": "Dosyadaki XML varlık (ENTITY) tanımı içeriyor; güvenlik nedeniyle okunmadı.",
                   "en": "The XML in the file contains an entity (ENTITY) declaration; it was not read for security reasons."},
    "epub_missing_part": {"tr": "EPUB dosyası eksik: içindeki {name} bulunamadı.", "en": "The EPUB file is incomplete: {name} is missing inside it."},
    "zip_member_too_large": {"tr": "Dosyanın içindeki {name} çok büyük; okunmadı.",
                             "en": "{name} inside the file is too large; it was not read."},

    # --- providers ---
    "provider_not_configured": {"tr": "config.toml dosyasında [providers.{name}] tanımlı değil.",
                                "en": "[providers.{name}] is not defined in config.toml."},
    "no_answer_in_time": {"tr": "{seconds} saniyede yanıt gelmedi", "en": "no answer within {seconds} seconds"},
    "command_not_found": {"tr": "'{command}' komutu bulunamadı. './translate setup' ile denetleyin.",
                          "en": "Command '{command}' not found. Check with './translate setup'."},
    "empty_answer": {"tr": "çıkış kodu {code}, boş yanıt", "en": "exit code {code}, empty answer"},
    "llm_failed": {"tr": "{name} yanıt vermedi: {error}", "en": "{name} did not answer: {error}"},
    "stopped": {"tr": "durduruldu", "en": "stopped"},
    "quota_waiting": {"tr": "{name} kullanım sınırına ulaştı; {time} saatine kadar bekleniyor, sonra kendiliğinden devam edecek.",
                      "en": "{name} reached its usage limit; waiting until {time}, then it continues by itself."},
    "quota_hit": {"tr": "{name} kullanım sınırına ulaştı. Yeniden deneme: {time}.",
                  "en": "{name} reached its usage limit. Try again at {time}."},
    "quota_gave_up": {"tr": "{name} kullanım sınırı çok uzun sürdü; bekleme bırakıldı. Daha sonra yeniden başlatın.",
                      "en": "The usage limit of {name} lasted too long; stopped waiting. Start again later."},
    "bad_format": {"tr": "{name} beklenen biçimde yanıt vermedi: {error}",
                   "en": "{name} did not answer in the expected format: {error}"},

    # --- mechanical checks ---
    "check_arabic_missing": {"tr": "Arap harfli {count} ibare çeviride aynen yer almıyor: {sample}",
                             "en": "{count} Arabic-script passages do not appear unchanged in the translation: {sample}"},
    "check_numbers_missing": {"tr": "Kaynaktaki şu sayılar çeviride yok: {numbers}",
                              "en": "These numbers of the source are missing in the translation: {numbers}"},
    "check_numbers_extra": {"tr": "Çeviride kaynakta olmayan sayılar var: {numbers}",
                            "en": "The translation has numbers that are not in the source: {numbers}"},
    "check_footnotes": {"tr": "Dipnot işaretleri ([^n]) kaynakla aynı değil.",
                        "en": "The footnote marks ([^n]) are not the same as in the source."},
    "check_paragraphs": {"tr": "Paragraf sayısı farklı: kaynak {source}, çeviri {translation}.",
                         "en": "Different number of paragraphs: source {source}, translation {translation}."},
    "check_headings": {"tr": "Başlık sayısı farklı: kaynak {source}, çeviri {translation}.",
                       "en": "Different number of headings: source {source}, translation {translation}."},
    "check_too_short": {
        "tr": "Çeviri beklenenden kısa (oran {ratio}, kitap ortancası {median}): atlanmış metin olabilir.",
        "en": "The translation is shorter than expected (ratio {ratio}, book median {median}): text may be missing."},
    "check_too_long": {
        "tr": "Çeviri beklenenden uzun (oran {ratio}, kitap ortancası {median}): eklenmiş metin olabilir.",
        "en": "The translation is longer than expected (ratio {ratio}, book median {median}): text may have been added."},

    "check_note_pairs": {"tr": "Dipnot işareti ile dipnot metni eşleşmiyor: {numbers}",
                         "en": "Footnote marks and footnote texts do not match: {numbers}"},
    "check_sentences": {"tr": "Şu paragraflarda kaynağa göre belirgin daha az cümle var (atlanmış cümle olabilir): {paragraphs}",
                        "en": "These paragraphs have clearly fewer sentences than the source (a sentence may be missing): {paragraphs}"},
    "gate_paragraphs": {"tr": "cevapta {answer} paragraf var, kaynakta {source}",
                        "en": "the answer has {answer} paragraphs, the source {source}"},
    "gate_footnotes": {"tr": "cevaptaki dipnot işaretleri kaynakla aynı değil", "en": "the footnote marks of the answer differ from the source"},
    "gate_shrunk": {"tr": "düzeltilmiş metin öncekinden %{percent} kısa", "en": "the corrected text is {percent}% shorter than before"},
    "gate_paragraph_shrunk": {"tr": "{n}. paragraf belirgin kısalmış (atlanmış cümle olabilir)",
                              "en": "paragraph {n} became clearly shorter (a sentence may be missing)"},
    "gate_paragraph_short": {"tr": "{n}. paragrafın çevirisi diğerlerine göre çok kısa (atlanmış cümle olabilir)",
                             "en": "the translation of paragraph {n} is much shorter than the others (a sentence may be missing)"},
    "gate_checked_count": {"tr": "tashihçi {got} paragrafı okuduğunu gösterdi, metinde {expected} paragraf var",
                           "en": "the reviewer showed that it read {got} paragraphs, the text has {expected}"},
    "gate_checked_wrong": {"tr": "tashihçinin okuma kanıtı şu paragraflarla uyuşmuyor: {paragraphs}",
                           "en": "the reviewer's reading proof does not match these paragraphs: {paragraphs}"},
    "gate_decisions_missing": {"tr": "şu bulgular için karar verilmedi: {ids}", "en": "no decision for these findings: {ids}"},
    "answer_rejected": {"tr": "cevap reddedildi: {problems}", "en": "answer rejected: {problems}"},
    "missing_segment_marker": {"tr": "[[EKSİK BÖLÜM {id} — henüz çevrilmedi / MISSING SEGMENT {id} — not translated yet]]",
                               "en": "[[MISSING SEGMENT {id} — not translated yet / EKSİK BÖLÜM {id} — henüz çevrilmedi]]"},
    "report_missing_segments": {"tr": "Çıktıda eksik bölümler (işaretli): {segments}",
                                "en": "Segments missing from the output (marked): {segments}"},

    # --- stages ---
    "nothing_to_do": {"tr": "yapılacak iş yok, hepsi hazır", "en": "nothing to do, all done"},
    "stage_failed": {
        "tr": "'{stage}' aşamasında {count} iş başarısız: {names}. Aynı komutu yeniden çalıştırın; kaldığı yerden devam eder.",
        "en": "{count} tasks failed in stage '{stage}': {names}. Run the same command again; it continues where it stopped."},
    "need_one_source": {"tr": "{folder} içinde tam bir Türkçe kaynak dosyası olmalı ({supported}); bulunan: {found}.",
                        "en": "{folder} must contain exactly one Turkish source file ({supported}); found: {found}."},
    "need_one_reference": {"tr": "{folder} içinde tam bir '{ref}.*' dosyası olmalı; bulunan: {found}.",
                           "en": "{folder} must contain exactly one '{ref}.*' file; found: {found}."},
    "no_text": {"tr": "{name} dosyasından metin çıkarılamadı.", "en": "No text could be extracted from {name}."},
    "prepared_source": {"tr": "{name}: {count} bölüm", "en": "{name}: {count} segments"},
    "prepared_reference": {"tr": "referans {name}: {count} paragraf", "en": "reference {name}: {count} paragraphs"},
    "source_changed": {
        "tr": "Kaynak dosya ({name}) ilk çalıştırmadan sonra değişmiş. Yeni kaynakla baştan başlamak için {work} klasörünü silin.",
        "en": "The source file ({name}) has changed since the first run. To start again with the new source, delete the folder {work}."},
    "reference_changed": {
        "tr": "Referans dosya ({name}) ilk çalıştırmadan sonra değişmiş. Yeniden işlemek için {work}/references/{ref}.md ve "
              "{work}/alignment/{ref}.json dosyalarını silin, {meta} içinden '{ref}' satırını çıkarın.",
        "en": "The reference file ({name}) has changed since the first run. To process it again, delete {work}/references/{ref}.md "
              "and {work}/alignment/{ref}.json, and remove the '{ref}' line from {meta}."},
    "align_skipped": {"tr": "referans dil yok, atlandı", "en": "no reference language, skipped"},
    "paragraphs": {"tr": "paragraf {first}-{last}", "en": "paragraphs {first}-{last}"},
    "align_not_found": {"tr": "bulunamadı", "en": "not found"},
    "glossary_done": {"tr": "{added} yeni terim eklendi, toplam {total}: {path}",
                      "en": "{added} new terms added, {total} in total: {path}"},
    "nothing_to_assemble": {"tr": "Birleştirilecek tamamlanmış bölüm yok.", "en": "There are no finished segments to assemble."},
    "output_translation": {"tr": "çeviri", "en": "translation"},
    "output_report": {"tr": "rapor ", "en": "report     "},
    "output_incomplete": {"tr": "DİKKAT: çıktı eksik, {done}/{total} bölüm tamamlandı",
                          "en": "WARNING: the output is incomplete, {done}/{total} segments finished"},
    "reset_done": {"tr": "{count} bölümde '{stage}' ve sonrası silindi",
                   "en": "'{stage}' and later stages deleted for {count} segments"},

    # --- report ---
    "report_title": {"tr": "Çeviri raporu: {book} → {language} ({code})", "en": "Translation report: {book} → {language} ({code})"},
    "report_incomplete": {"tr": "EKSİK ÇIKTI: {total} bölümün {done} tanesi tamamlandı.",
                          "en": "INCOMPLETE OUTPUT: {done} of {total} segments finished."},
    "report_segments": {"tr": "Tamamlanan bölüm: {done}/{total}", "en": "Finished segments: {done}/{total}"},
    "report_references": {"tr": "Referans diller: {refs}", "en": "Reference languages: {refs}"},
    "report_review": {"tr": "Tashih ({stage})", "en": "Review ({stage})"},
    "report_source_check": {"tr": "Baştan kaynak kontrolü ({stage})", "en": "Source check from the start ({stage})"},
    "report_custom": {"tr": "Özel adım: {title} ({stage})", "en": "Custom step: {title} ({stage})"},
    "report_gate": {"tr": "Kontrol noktası ({stage})", "en": "Checkpoint ({stage})"},
    "report_gate_summary": {"tr": "{sent} kez geri gönderdi; ciddi sorunu kalan bölüm: {left}",
                            "en": "sent back {sent} times; segments with serious problems left: {left}"},
    "report_summary": {
        "tr": "{total} bulgu (kritik {critical}, önemli {major}, küçük {minor}); kabul {accepted}, ret {rejected}",
        "en": "{total} findings (critical {critical}, major {major}, minor {minor}); accepted {accepted}, rejected {rejected}"},
    "report_warnings": {"tr": "Mekanik uyarı bulunan bölüm: {count}", "en": "Segments with mechanical warnings: {count}"},
    "report_unaligned": {"tr": "Referansı ({ref}) bulunamayan bölümler: {segments}",
                         "en": "Segments without a reference passage ({ref}): {segments}"},
    "report_attention": {"tr": "İnsan tercümanın bakması gerekenler", "en": "For the human translator to check"},
    "report_attention_intro": {
        "tr": "Aşağıda mekanik uyarılar, kritik bulgular ve kabul edilmeyen önemli bulgular yer alır. Bütün bulgular ve kararlar "
              "`work/{lang}/` altında, tashihleri uygulayan adımların ve kaynak kontrollerinin klasörlerinde, bölüm başına bir `.json` dosyasındadır.",
        "en": "Below are the mechanical warnings, the critical findings and the major findings that were not accepted. All findings "
              "and decisions are under `work/{lang}/`, in the folders of the steps that apply reviews and of the source checks, one `.json` file per segment."},
    "report_segment": {"tr": "Bölüm {id}", "en": "Segment {id}"},
    "report_warning": {"tr": "UYARI", "en": "WARNING"},
    "report_source": {"tr": "Kaynak", "en": "Source"},
    "report_translation": {"tr": "Çeviri", "en": "Translation"},
    "report_suggestion": {"tr": "Öneri", "en": "Suggestion"},
    "report_reason": {"tr": "Karar gerekçesi", "en": "Reason for the decision"},
    "report_nothing": {"tr": "Bakılması gereken bir kayıt yok.", "en": "Nothing needs checking."},
    "report_stale": {
        "tr": "DİKKAT: şu bölümler üretildikten sonra sözlük, referans veya talimat değişti; eski girdilerle duruyorlar. "
              "Yenilemek için bu bölümleri '{stage}' adımından yeniden üretin: {segments}",
        "en": "ATTENTION: the glossary, the references or the instructions changed after these segments were produced; they "
              "still use the old inputs. To renew them, produce these segments again from the '{stage}' step: {segments}"},
    "report_audit": {"tr": "Tashihçi denetimi", "en": "Reviewer audit"},
    "report_audit_intro": {
        "tr": "Her tashihçi her paragrafı okuduğunu kanıtlamak zorundadır; kanıtsız cevap reddedilir. Yine de bulgu yazmamak "
              "\"metin temiz\" demek olmayabilir. Aşağıda tashihçi başına sayılar ve sonradan hata çıkan sessiz bölümler yer alır.",
        "en": "Each reviewer must prove that it read every paragraph; an answer without the proof is rejected. Still, no "
              "findings does not always mean a clean text. Below are the numbers per reviewer, and the silent segments in which "
              "errors were found later."},
    "report_audit_row": {"tr": "{stage} · {reviewer}: {segments} bölüm, {empty} bölümde bulgu yok, toplam {issues} bulgu",
                         "en": "{stage} · {reviewer}: {segments} segments, no findings in {empty}, {issues} findings in total"},
    "report_audit_quiet": {
        "tr": "DİKKAT: {reviewer} bölümlerin %{percent} kadarında hiçbir bulgu yazmadı. Birkaç bölümü elle kontrol edin; "
              "gerekirse bu adım için başka bir model seçin.",
        "en": "ATTENTION: {reviewer} wrote no findings in {percent}% of the segments. Check a few segments by hand; "
              "if needed, choose another model for this step."},
    "report_audit_missed": {
        "tr": "DİKKAT: {reviewer} şu bölümlerde bulgu yazmadı, ama {by} aynı bölümlerde kritik veya önemli hata buldu: {segments}",
        "en": "ATTENTION: {reviewer} wrote no findings in these segments, but {by} found critical or major errors in them: {segments}"},
    "report_audit_by_source_check": {"tr": "baştan kaynak kontrolü", "en": "the source check"},
    "report_audit_by_other": {"tr": "aynı turdaki başka bir tashihçi", "en": "another reviewer of the same round"},
    "decision_accepted": {"tr": "kabul edildi", "en": "accepted"},
    "decision_rejected": {"tr": "REDDEDİLDİ", "en": "REJECTED"},
    "decision_none": {"tr": "karar yok", "en": "no decision"},
    "severity_critical": {"tr": "kritik", "en": "critical"},
    "severity_major": {"tr": "önemli", "en": "major"},
    "severity_minor": {"tr": "küçük", "en": "minor"},
    "type_omission": {"tr": "eksik", "en": "omission"},
    "type_addition": {"tr": "fazlalık", "en": "addition"},
    "type_mistranslation": {"tr": "yanlış anlam", "en": "mistranslation"},
    "type_terminology": {"tr": "terim", "en": "terminology"},
    "type_religious": {"tr": "dinî içerik", "en": "religious content"},
    "type_names": {"tr": "özel ad", "en": "names"},
    "type_format": {"tr": "biçim", "en": "format"},
    "type_language": {"tr": "dil", "en": "language"},

    # --- command line ---
    "cli_description": {"tr": "İslami kitap çevirisi: yapay zekâ modelleriyle çok adımlı kitap çevirisi", "en": "Islamic book translation: multi-step book translation with AI models"},
    "cli_lang": {"tr": "arayüz dili (tr veya en)", "en": "interface language (tr or en)"},
    "cli_setup": {"tr": "claude / gemini / codex araçları kurulu ve yanıt veriyor mu, denetler",
                  "en": "checks that the claude / gemini / codex tools are installed and answer"},
    "cli_new": {"tr": "yeni kitap klasörü oluşturur", "en": "creates a new book folder"},
    "cli_book": {"tr": "kitabın kısa adı (klasör adı), örnek: ilmihal", "en": "short name of the book (folder name), for example: ilmihal"},
    "cli_run": {"tr": "kitabı hedef dile çevirir; kaldığı yerden devam eder",
                "en": "translates the book into the target language; continues where it stopped"},
    "cli_target": {"tr": "hedef dil kodu, örnek: no", "en": "target language code, for example: no"},
    "cli_refs": {"tr": "kullanılacak referans diller, örnek: da,sv (varsayılan: references/ içindekilerin hepsi)",
                 "en": "reference languages to use, for example: da,sv (default: all in references/)"},
    "cli_segments": {"tr": "yalnızca bu bölümler, örnek: 1-3 (deneme çevirisi için)",
                     "en": "only these segments, for example: 1-3 (for a trial translation)"},
    "cli_until": {"tr": "bu aşamadan sonra dur", "en": "stop after this stage"},
    "cli_redo": {"tr": "bu aşamanın ve sonrakilerin çıktısını silip yeniden üret",
                 "en": "delete the output of this stage and later stages, and produce it again"},
    "cli_parallel": {"tr": "aynı anda çalışan istek sayısı", "en": "number of requests that run at the same time"},
    "cli_status": {"tr": "kitapların ilerleme durumunu gösterir", "en": "shows the progress of the books"},
    "cli_ui": {"tr": "web arayüzünü başlatır (yalnızca bu bilgisayardan erişilir)",
               "en": "starts the web interface (reachable only from this computer)"},
    "cli_no_browser": {"tr": "tarayıcıyı otomatik açma", "en": "do not open the browser automatically"},
    "bad_segments": {"tr": "--segments değeri anlaşılmadı: '{spec}'. Örnek: 1-5 veya 1-5,9",
                     "en": "Cannot read the --segments value '{spec}'. Example: 1-5 or 1-5,9"},
    "no_such_segments": {"tr": "--segments {spec}: kitapta bu numarada bölüm yok (1-{total}).",
                         "en": "--segments {spec}: the book has no segment with this number (1-{total})."},
    "unused": {"tr": "kullanılmıyor", "en": "not used"},
    "tool_missing": {"tr": "'{command}' komutu kurulu değil. Kurulum: {hint}", "en": "command '{command}' is not installed. Install: {hint}"},
    "tool_ok": {"tr": "çalışıyor (yanıt: {answer})", "en": "works (answer: {answer})"},
    "tool_no_answer": {"tr": "kurulu ama yanıt alınamadı: {error}", "en": "installed, but no answer: {error}"},
    "all_ready": {"tr": "Her şey hazır.", "en": "Everything is ready."},
    "fix_and_retry": {"tr": "Eksikleri giderdikten sonra yeniden deneyin.", "en": "Fix the problems above, then try again."},
    "book_created": {
        "tr": "Klasör hazır: {path}\n"
              "1. Türkçe kitabı {source} içine koyun (tek dosya; .docx, .epub, .md, .txt veya .pdf).\n"
              "2. Mevcut tercümeleri {references} içine dil koduyla koyun (örnek: da.docx, sv.epub).\n"
              "3. Çalıştırın: ./translate run {book} <hedef-dil-kodu>",
        "en": "Folder ready: {path}\n"
              "1. Put the Turkish book into {source} (one file: .docx, .epub, .md, .txt or .pdf).\n"
              "2. Put the existing translations into {references}, named by language code (for example: da.docx, sv.epub).\n"
              "3. Run: ./translate run {book} <target-language-code>"},
    "book_busy": {"tr": "Bu kitap için başka bir çalıştırma sürüyor. Onun bitmesini bekleyin.",
                  "en": "Another run of this book is in progress. Wait until it finishes."},
    "book_not_found": {"tr": "Kitap bulunamadı: {path}. Önce: ./translate new {book}",
                       "en": "Book not found: {path}. First run: ./translate new {book}"},
    "no_references_warning": {"tr": "UYARI: referans tercüme yok; çeviri yalnızca Türkçe kaynaktan yapılacak.",
                              "en": "WARNING: no reference translation; the translation uses only the Turkish source."},
    "tools_not_installed": {"tr": "Şu araçlar kurulu değil: {names}. Ayrıntı için: ./translate setup",
                            "en": "These tools are not installed: {names}. For details: ./translate setup"},
    "run_header": {"tr": "{book} → {language}: {selected}/{total} bölüm, referans: {refs}",
                   "en": "{book} → {language}: {selected}/{total} segments, references: {refs}"},
    "no_books": {"tr": "Henüz kitap yok. Başlamak için: ./translate new <kitap-adi>",
                 "en": "No books yet. To start: ./translate new <book-name>"},
    "segments_count": {"tr": "{count} bölüm", "en": "{count} segments"},
    "not_prepared": {"tr": "henüz hazırlanmadı", "en": "not prepared yet"},
    "status_alignment": {"tr": "referans {ref}: {aligned}/{total} bölüm hizalı",
                         "en": "reference {ref}: {aligned}/{total} segments aligned"},
    "status_unaligned": {"tr": "referansta bulunamayan bölümler (referanssız çevrilir): {segments}",
                         "en": "segments not found in the reference (translated without it): {segments}"},
    "ui_port_busy": {"tr": "{port} numaralı bağlantı noktası kullanımda; arayüz büyük olasılıkla zaten açık: {url}\n"
                           "Başka bir arayüz açmak için: ./translate ui --port 8766",
                     "en": "Port {port} is in use; the interface is probably already open: {url}\n"
                           "To open another one: ./translate ui --port 8766"},
    "run_failed_at_start": {"tr": "Çeviri başlatılamadı: {reason}", "en": "The translation could not start: {reason}"},
    "pdf_tool_missing": {"tr": "PDF okumak için PDF okuyucu (Poppler) gerekli. Kurulum sekmesinde \"PDF okuyucu\" kartındaki \"Kur\" düğmesine basın; kurulum birkaç dakika sürer. Mümkünse kitabı .docx veya .epub olarak yükleyin.",
                         "en": "Reading a PDF needs the PDF reader (Poppler). Click \"Install\" on the \"PDF reader\" card of the Setup tab; it takes a few minutes. If possible, upload the book as .docx or .epub."},
    "pdf_tool_downloading": {"tr": "PDF okuyucu için paket yöneticisi (micromamba) indiriliyor (uygulamanın kendi klasörüne; yönetici izni gerekmez)...",
                             "en": "Downloading the package manager for the PDF reader (micromamba; into the application's own folder; no administrator rights needed)..."},
    "pdf_tool_checksum_mismatch": {"tr": "İndirilen paket yöneticisi doğrulanamadı (SHA-256 farklı); kullanılmadı. Yeniden deneyin.",
                                   "en": "The downloaded package manager failed verification (SHA-256 differs); it was not used. Try again."},
    "pdf_tool_install_failed": {"tr": "PDF okuyucu kurulamadı: kurulumdan sonra pdftotext bulunamadı. Ayrıntı yukarıdaki satırlarda.",
                                "en": "The PDF reader could not be installed: pdftotext is missing after the installation. The details are in the lines above."},
    "pdf_tool_unsupported": {"tr": "Bu işlemci türü için PDF okuyucu kurulamıyor: {machine}. Kitabı .docx veya .epub olarak verin.",
                             "en": "The PDF reader cannot be installed for this processor type: {machine}. Supply the book as .docx or .epub."},
    "tool_name_pdf": {"tr": "PDF okuyucu (Poppler)", "en": "PDF reader (Poppler)"},
    "tool_use_denied": {"tr": "(model metinle cevap vermek yerine bir araç kullanmaya çalıştı; izin verilmedi)",
                        "en": "(the model tried to use a tool instead of answering with text; it was not allowed)"},
    "ui_running": {"tr": "Arayüz çalışıyor: {url}\nKapatmak için bu pencerede Ctrl+C'ye basın.",
                   "en": "The interface is running: {url}\nTo stop it, press Ctrl+C in this window."},

    # --- tools ---
    "gemini_settings_invalid": {"tr": "{path} okunamadı (geçerli JSON değil). Dosyayı elle düzeltin.",
                                "en": "Cannot read {path} (not valid JSON). Correct the file by hand."},
    "status_unreadable": {"tr": "Oturum durumu okunamadı.", "en": "Cannot read the sign-in status."},
    "claude_subscription": {"tr": "Claude aboneliği", "en": "Claude subscription"},
    "not_signed_in": {"tr": "Oturum açılmamış.", "en": "Not signed in."},
    "google_account": {"tr": "Google hesabı", "en": "Google account"},
    "stored_sign_in": {"tr": "Oturum kayıtlı", "en": "Sign-in stored"},
    "api_key": {"tr": "API anahtarı", "en": "API key"},
    "google_not_selected": {"tr": "Google oturumu var ama seçili değil. 'Google hesabıyla' düğmesine basın.",
                            "en": "A Google sign-in exists but is not selected. Click 'With Google account'."},
    "need_curl": {"tr": "Kurulum için 'curl' komutu gerekli.", "en": "The installation needs the 'curl' command."},
    "run_in_terminal": {"tr": "Bir terminal açıp şu komutu çalıştırın: {command}", "en": "Open a terminal and run: {command}"},
    "terminal_opened": {
        "tr": "Terminal penceresi açıldı. Oradaki adımları tamamlayın, sonra bu sayfada 'Durumu yenile' düğmesine basın.",
        "en": "A Terminal window opened. Complete the steps there, then click 'Refresh status' on this page."},
    "invalid_key": {"tr": "Anahtar geçersiz görünüyor (boşluksuz, en az 20 karakter olmalı).",
                    "en": "The key does not look valid (it must have no spaces and at least 20 characters)."},
    "install_first": {"tr": "Önce aracı kurun.", "en": "Install the tool first."},
    "google_selected": {"tr": "Mevcut Google oturumu seçildi.", "en": "The existing Google sign-in is selected."},
    "gemini_key_saved": {"tr": "Gemini API anahtarı kaydedildi.", "en": "Gemini API key saved."},
    "codex_key_rejected": {"tr": "Codex anahtarı kabul etmedi.", "en": "Codex did not accept the key."},
    "codex_key_saved": {"tr": "OpenAI API anahtarıyla oturum açıldı.", "en": "Signed in with the OpenAI API key."},
    "login_method_unsupported": {"tr": "Bu araç için bu oturum açma yöntemi yok.",
                                 "en": "This sign-in method is not available for this tool."},

    # --- installation ---
    "cli_package": {"tr": "paylaşmak için uygulamanın zip dosyasını yazar (kitaplar, kurulu araçlar ve günlükler girmez)",
                    "en": "writes a zip of the application for sharing (without books, installed tools and logs)"},
    "cli_package_out": {"tr": "zip dosyasının yolu (varsayılan: dist/translation-pipeline.zip)",
                        "en": "path of the zip file (default: dist/translation-pipeline.zip)"},
    "cli_update": {"tr": "uygulamayı GitHub'dan günceller; talimatlar ve iş akışı değişmez (arayüz her açılışta bunu yapar)",
                   "en": "updates the application from GitHub; the instructions and the workflow do not change (the interface does this at each start)"},
    "update_done": {"tr": "Uygulama güncellendi ({count} yeni değişiklik). Talimatlarınız ve iş akışınız olduğu gibi kaldı.",
                    "en": "The application is updated ({count} new changes). Your instructions and your workflow are unchanged."},
    "update_skipped_offline": {"tr": "Güncelleme denetlenemedi (internet veya GitHub girişi yok); uygulama olduğu gibi açılıyor.",
                               "en": "Could not check for updates (no internet or no GitHub sign-in); the application starts as it is."},
    "update_skipped_running": {"tr": "Bir çeviri sürdüğü için güncelleme atlandı; çeviri bitince arayüzü yeniden açın.",
                               "en": "An update was skipped because a translation is running; open the interface again when it is done."},
    "update_skipped_local": {"tr": "Güncelleme uygulanamadı, bu bilgisayardaki kod değiştirilmiş: {reason}. Uygulama olduğu gibi açılıyor.",
                             "en": "The update could not be applied, the code on this computer was changed: {reason}. The application starts as it is."},
    "package_done": {"tr": "Paket yazıldı ({count} dosya): {path}", "en": "Package written ({count} files): {path}"},
    "cli_install": {"tr": "araçları ve PDF okuyucuyu kurar (gerekirse taşınabilir Node.js'i de); yönetici izni gerekmez",
                    "en": "installs the tools and the PDF reader (and a portable Node.js when needed); no administrator rights needed"},
    "tool_installed": {"tr": "{name} kuruldu.", "en": "{name} is installed."},
    "nothing_to_install": {"tr": "Bütün araçlar zaten kurulu.", "en": "All tools are already installed."},
    "download_progress": {"tr": "  indiriliyor: %{percent} ({mb} MB)", "en": "  downloading: {percent}% ({mb} MB)"},
    "node_downloading": {"tr": "Node.js {version} indiriliyor (uygulamanın kendi klasörüne; yönetici izni gerekmez)...",
                         "en": "Downloading Node.js {version} (into the application's own folder; no administrator rights needed)..."},
    "node_installed": {"tr": "Node.js {version} kuruldu ve doğrulandı.", "en": "Node.js {version} is installed and verified."},
    "node_unsupported": {"tr": "Bu işlemci türü için Node.js indirilemiyor: {machine}. Node.js'i https://nodejs.org adresinden kurun.",
                         "en": "No Node.js download for this processor type: {machine}. Install Node.js from https://nodejs.org."},
    "node_no_checksum": {"tr": "{name} için doğrulama bilgisi bulunamadı; indirme yapılmadı.",
                         "en": "No checksum found for {name}; nothing was downloaded."},
    "node_checksum_mismatch": {"tr": "İndirilen Node.js doğrulanamadı (SHA-256 farklı); kullanılmadı. Yeniden deneyin.",
                               "en": "The downloaded Node.js failed verification (SHA-256 differs); it was not used. Try again."},
    "node_install_failed": {"tr": "Node.js kurulamadı.", "en": "Node.js could not be installed."},
    "archive_unsafe": {"tr": "İndirilen arşiv güvenli değil; açılmadı.", "en": "The downloaded archive is not safe; it was not unpacked."},
    "install_step_failed": {"tr": "Kurulum adımı başarısız oldu (çıkış kodu {code}). Ayrıntı yukarıdaki satırlarda.",
                            "en": "An installation step failed (exit code {code}). The details are in the lines above."},
    "requirements_claude": {"tr": "Gerekenler: Claude Pro veya Max aboneliği ya da Anthropic Console (API) hesabı.",
                            "en": "Needs: a Claude Pro or Max subscription, or an Anthropic Console (API) account."},
    "requirements_codex": {"tr": "Gerekenler: ücretli bir ChatGPT planı (Plus, Pro, Business…) ya da OpenAI API anahtarı.",
                           "en": "Needs: a paid ChatGPT plan (Plus, Pro, Business…) or an OpenAI API key."},
    "requirements_antigravity": {
        "tr": "Gerekenler: bir Google hesabı. Google AI Pro veya Ultra aboneliği daha yüksek kullanım sınırı verir. Gemini "
              "modellerinin yanında Claude modelleri de seçilebilir.",
        "en": "Needs: a Google account. A Google AI Pro or Ultra subscription gives higher usage limits. Besides the Gemini "
              "models, Claude models can be selected too."},
    "requirements_gemini": {
        "tr": "Gerekenler: bir Gemini API anahtarı veya bir şirket (Google Cloud) hesabı. Google, 18 Haziran 2026'dan beri kişisel "
              "hesapları (ücretsiz, Pro ve Ultra) bu araçta kabul etmiyor; kişisel hesap için Antigravity CLI'ı kullanın.",
        "en": "Needs: a Gemini API key or a company (Google Cloud) account. Since 18 June 2026 Google does not accept personal "
              "accounts (free, Pro and Ultra) in this tool; for a personal account, use Antigravity CLI."},
    "requirements_pdf": {
        "tr": "Gerekenler: yok. Uygulamanın kendi klasörüne kurulur; yönetici izni gerekmez.",
        "en": "Needs: nothing. It is installed into the application's own folder; no administrator rights are needed."},
    "sign_in_help_claude": {"tr": "Oturum açma: açılan terminal tarayıcıda bir sayfa açar; hesabınızla giriş yapın. Terminal girişin başarılı olduğunu yazınca pencereyi kapatabilirsiniz.",
                            "en": "Sign-in: the terminal opens a page in your browser; sign in with your account. When the terminal says the login succeeded, you can close the window."},
    "sign_in_help_codex": {"tr": "Oturum açma: tarayıcıda ChatGPT hesabınızla giriş yapın. Terminal girişin başarılı olduğunu yazınca pencereyi kapatabilirsiniz.",
                           "en": "Sign-in: sign in with your ChatGPT account in the browser. When the terminal says the login succeeded, you can close the window."},
    "sign_in_help_gemini": {
        "tr": "Oturum açma: Gemini terminalde açılır ve tarayıcıda Google girişini başlatır. Giriş bitince terminale /quit yazıp "
              "Enter'a basın. Alternatif: https://aistudio.google.com/apikey adresinden alınan bir API anahtarı.",
        "en": "Sign-in: Gemini opens in the terminal and starts the Google sign-in in your browser. When it is done, type /quit in "
              "the terminal and press Enter. Alternative: an API key from https://aistudio.google.com/apikey."},
    "sign_in_help_antigravity": {
        "tr": "Oturum açma: Antigravity terminalde açılır ve tarayıcıda Google girişini başlatır. Giriş bitince terminale /exit "
              "yazıp Enter'a basın, sonra \"Dene\" düğmesiyle kontrol edin.",
        "en": "Sign-in: Antigravity opens in the terminal and starts the Google sign-in in your browser. When it is done, type "
              "/exit in the terminal and press Enter, then check with the \"Test\" button."},
    "sign_in_help_pdf": {"tr": "", "en": ""},
    # Shown first in the sign-in terminal window. No characters that cmd (Windows) would read: & | < > ^ % "
    "terminal_note_claude": {"tr": "Tarayıcıda bir sayfa açılacak: Claude hesabınızla giriş yapın. Giriş başarılı yazınca bu pencereyi kapatıp arayüze dönün.",
                             "en": "A page opens in your browser: sign in with your Claude account. When the login succeeds, close this window and return to the interface."},
    "terminal_note_codex": {"tr": "Tarayıcıda bir sayfa açılacak: ChatGPT hesabınızla giriş yapın. Giriş başarılı yazınca bu pencereyi kapatıp arayüze dönün.",
                            "en": "A page opens in your browser: sign in with your ChatGPT account. When the login succeeds, close this window and return to the interface."},
    "terminal_note_antigravity": {"tr": "Tarayıcıda Google girişi açılacak: Google hesabınızla giriş yapın. Antigravity açılınca /exit yazıp Enter'a basın, sonra arayüzde Dene düğmesine basın.",
                                  "en": "A Google sign-in opens in your browser: sign in with your Google account. When Antigravity opens, type /exit and press Enter, then click Test in the interface."},
    "terminal_note_gemini": {"tr": "Gemini açılınca Google ile giriş yapın. Giriş bitince /quit yazıp Enter'a basın.",
                             "en": "When Gemini starts, sign in with Google. When it is done, type /quit and press Enter."},
    "effort_invalid": {"tr": "{name}: bu araç bu düşünme seviyesini desteklemiyor.",
                       "en": "{name}: this tool does not support this thinking level."},
    "account_refused": {
        "tr": "{name} bu hesabı kabul etmiyor ({reason}). Kurulum sekmesinde başka bir hesapla ya da API anahtarıyla oturum açın, "
              "veya İş akışı sekmesinde bu aracın adımlarına başka bir model atayın.",
        "en": "{name} does not accept this account ({reason}). Sign in with another account or with an API key on the Setup tab, "
              "or assign another model to this tool's steps on the Workflow tab."},

    # --- web ---
    "bad_host": {"tr": "Geçersiz adres.", "en": "Invalid address."},
    "bad_token": {"tr": "Oturum anahtarı geçersiz. Sayfayı yenileyin.", "en": "Invalid session key. Reload the page."},
    "not_found": {"tr": "Bulunamadı.", "en": "Not found."},
    "not_allowed": {"tr": "İzin verilmiyor.", "en": "Not allowed."},
    "bad_request": {"tr": "Geçersiz istek.", "en": "Invalid request."},
    "request_too_large": {"tr": "İstek çok büyük.", "en": "The request is too large."},
    "unexpected_error": {"tr": "Beklenmeyen bir hata oluştu. Ayrıntı sunucunun terminalinde.",
                         "en": "An unexpected error occurred. The details are in the server's terminal."},
    "job_running": {"tr": "Bu iş zaten çalışıyor.", "en": "This job is already running."},
    "job_done": {"tr": "tamamlandı", "en": "completed"},
    "job_failed": {"tr": "hata ile bitti (kod {code})", "en": "failed (code {code})"},
    "install_started": {"tr": "Kurulum başladı.", "en": "Installation started."},
    "test_answer": {"tr": "Yanıt alındı ({seconds} sn): {answer}", "en": "Answer received ({seconds} s): {answer}"},
    "language_code_invalid": {"tr": "Dil kodu 2-3 küçük harf olmalı (örnek: tg, ckb).",
                              "en": "The language code must be 2-3 lowercase letters (for example: tg, ckb)."},
    "language_name_invalid": {"tr": "Dil adını İngilizce yazın (örnek: Tajik). Model bu adı görür.",
                              "en": "Write the language name in English (for example: Tajik). The model sees this name."},
    "language_exists": {"tr": "Bu dil kodu zaten tanımlı.", "en": "This language code is already defined."},
    "languages_not_last": {"tr": "config.toml içinde [languages] son bölüm olmalı; dili elle ekleyin.",
                           "en": "[languages] must be the last section of config.toml; add the language by hand."},
    "language_added": {"tr": "{name} ({code}) eklendi.", "en": "{name} ({code}) added."},
    "book_missing": {"tr": "Kitap bulunamadı.", "en": "Book not found."},
    "book_name_invalid": {"tr": "Kitap adı geçersiz. Harf ve rakam kullanın.", "en": "Invalid book name. Use letters and digits."},
    "book_exists": {"tr": "'{name}' adlı kitap zaten var.", "en": "A book named '{name}' already exists."},
    "book_added": {"tr": "'{name}' oluşturuldu.", "en": "'{name}' created."},
    "book_running": {"tr": "Bu kitap şu anda çalışıyor. Önce durdurun veya bitmesini bekleyin.",
                     "en": "This book is running now. Stop it first, or wait until it finishes."},
    "upload_type": {"tr": "Desteklenmeyen dosya türü. Desteklenenler: {supported}", "en": "Unsupported file type. Supported: {supported}"},
    "upload_size": {"tr": "Dosya boş veya çok büyük (en çok {limit} MB).", "en": "The file is empty or too large (at most {limit} MB)."},
    "uploaded_with_warnings": {"tr": "{name} yüklendi. Kontrol edin: {warnings}", "en": "{name} is uploaded. Please check: {warnings}"},
    "ref_looks_turkish": {
        "tr": "Bu dosya Türkçe görünüyor. Referans, kitabın başka bir dildeki tercümesi olmalı; Türkçe kitabı \"Türkçe kaynak\" adımında yükleyin.",
        "en": "This file looks Turkish. A reference must be a translation of the book into another language; upload the Turkish book in the \"Turkish source\" step."},
    "ref_wrong_script": {
        "tr": "Bu dosya {found} harflerle yazılmış, ama seçilen dil ({lang}) {expected} harflerle yazılır. Dili doğru seçtiğinizi kontrol edin.",
        "en": "This file is written in {found} letters, but the selected language ({lang}) is written in {expected} letters. Check that you selected the right language."},
    "ref_not_same_book": {
        "tr": "Bu dosya aynı kitabın tercümesi gibi görünmüyor: Arapça ibarelerinin ve numaralarının yalnızca %{percent}'i Türkçe kaynakta var. Doğru kitabı yüklediğinizi kontrol edin.",
        "en": "This file does not look like a translation of the same book: only {percent}% of its Arabic phrases and numbers are in the Turkish source. Check that you uploaded the right book."},
    "ref_too_short": {
        "tr": "Referans, Türkçe kaynağın yalnızca yaklaşık %{percent}'i uzunluğunda; kitabın bir kısmı olabilir. Karşılığı bulunamayan bölümler referanssız çevrilir.",
        "en": "The reference is only about {percent}% as long as the Turkish source; it may be a part of the book. The segments without a match are translated without the reference."},
    "ref_too_long": {
        "tr": "Referans, Türkçe kaynağın {times} katı uzunluğunda; başka metinler de içeriyor olabilir.",
        "en": "The reference is {times} times as long as the Turkish source; it may contain other texts as well."},
    "script_latin": {"tr": "Latin", "en": "Latin"}, "script_cyrillic": {"tr": "Kiril", "en": "Cyrillic"},
    "script_arabic": {"tr": "Arap", "en": "Arabic"}, "script_greek": {"tr": "Yunan", "en": "Greek"},
    "script_hebrew": {"tr": "İbrani", "en": "Hebrew"}, "script_georgian": {"tr": "Gürcü", "en": "Georgian"},
    "script_armenian": {"tr": "Ermeni", "en": "Armenian"}, "script_devanagari": {"tr": "Devanagari", "en": "Devanagari"},
    "script_bengali": {"tr": "Bengal", "en": "Bengali"}, "script_thai": {"tr": "Tay", "en": "Thai"},
    "script_cjk": {"tr": "Çin, Japon veya Kore", "en": "Chinese, Japanese or Korean"}, "script_other": {"tr": "başka", "en": "other"},
    "upload_incomplete": {"tr": "Yükleme yarıda kaldı.", "en": "The upload is incomplete."},
    "export_invalid": {"tr": "Biçim ayarı geçersiz: {field}.", "en": "Invalid layout setting: {field}."},
    "export_field_page_size": {"tr": "sayfa boyutu", "en": "page size"},
    "export_field_margin_top": {"tr": "üst kenar boşluğu (0,5–5 cm)", "en": "top margin (0.5–5 cm)"},
    "export_field_margin_bottom": {"tr": "alt kenar boşluğu (0,5–5 cm)", "en": "bottom margin (0.5–5 cm)"},
    "export_field_margin_side": {"tr": "yan kenar boşlukları (0,5–5 cm)", "en": "side margins (0.5–5 cm)"},
    "export_field_font": {"tr": "yazı tipi (en çok 60 karakter; tırnak ve < > ; { } & olmadan)",
                          "en": "font (at most 60 characters; no quotes and no < > ; { } &)"},
    "export_field_arabic_font": {"tr": "Arapça yazı tipi (en çok 60 karakter; tırnak ve < > ; { } & olmadan)",
                                 "en": "Arabic font (at most 60 characters; no quotes and no < > ; { } &)"},
    "export_field_font_size": {"tr": "punto (8–16)", "en": "font size (8–16)"},
    "export_field_line_spacing": {"tr": "satır aralığı (1–3)", "en": "line spacing (1–3)"},
    "export_field_justify": {"tr": "iki yana yaslama", "en": "justification"},
    "export_field_chapter_new_page": {"tr": "bölümün yeni sayfada başlaması", "en": "chapters on a new page"},
    "export_saved": {"tr": "Biçim ayarları kaydedildi.", "en": "Layout settings saved."},
    "template_saved": {"tr": "Word şablonu yüklendi: {name}", "en": "Word template uploaded: {name}"},
    "template_removed": {"tr": "Word şablonu kaldırıldı.", "en": "Word template removed."},
    "template_invalid_type": {"tr": "Şablon bir Word dosyası olmalı (.docx veya .dotx).",
                              "en": "The template must be a Word file (.docx or .dotx)."},
    "template_invalid_size": {"tr": "Şablon boş veya çok büyük (en çok 20 MB).", "en": "The template is empty or too large (at most 20 MB)."},
    "template_invalid_macros": {"tr": "Makro içeren Word dosyaları şablon olarak kabul edilmez. Dosyayı .docx olarak kaydedin.",
                                "en": "Word files with macros are not accepted as templates. Save the file as .docx."},
    "template_invalid_broken": {"tr": "Bu Word dosyası okunamadı. Word'de açıp yeniden kaydedin ve tekrar deneyin.",
                                "en": "This Word file cannot be read. Open it in Word, save it again and try again."},
    "upload_not_valid": {"tr": "Dosya geçerli bir {ext} değil.", "en": "The file is not a valid {ext}."},
    "upload_not_utf8": {"tr": "Metin dosyası UTF-8 olmalı.", "en": "A text file must be UTF-8."},
    "source_locked": {"tr": "Bu kitap hazırlanmış. Kaynağı değiştirmek için önce 'Çalışmayı sıfırla' düğmesine basın.",
                      "en": "This book is prepared. To change the source, first click 'Reset work'."},
    "uploaded": {"tr": "{name} yüklendi.", "en": "{name} uploaded."},
    "reference_deleted": {"tr": "Referans silindi.", "en": "Reference deleted."},
    "book_reset": {"tr": "Çalışma dosyaları silindi. Kitap baştan hazırlanacak.",
                   "en": "The work files are deleted. The book will be prepared again."},
    "target_not_turkish": {"tr": "Hedef dil Türkçe olamaz.", "en": "The target language cannot be Turkish."},
    "segments_format": {"tr": "Bölüm biçimi: 1-3 veya 1-5,9", "en": "Segment format: 1-3 or 1-5,9"},
    "stage_invalid": {"tr": "Geçersiz aşama.", "en": "Invalid stage."},
    "stage_not_in_flow": {"tr": "'{stage}' bu iş akışında bir aşama değil. Aşamalar: {stages}",
                          "en": "'{stage}' is not a stage of this workflow. Stages: {stages}"},
    "flow_invalid": {"tr": "config.toml'daki iş akışı (flow) geçersiz. İş akışı sekmesinde \"Şemadaki dağılım\" ile düzeltin.",
                     "en": "The workflow (flow) in config.toml is invalid. Fix it with \"Diagram assignment\" in the Workflow tab."},
    "flow_unapplied": {"tr": "'{node}' adımının bulguları hiçbir yerde uygulanmıyor. Ondan sonra, metni değiştiren başka bir adımdan önce bir \"Uygula\" adımı koyun.",
                       "en": "The findings of the step '{node}' are not applied anywhere. Put an \"Apply\" step after it, before any other step that changes the text."},
    "flow_gate_invalid": {"tr": "'{node}' kontrol noktası geçersiz: daha önceki bir adıma (önceki kontrol noktasından sonraki bir adıma) geri göndermeli ve en çok 1-5 kez göndermeli.",
                          "en": "The checkpoint '{node}' is invalid: it must send back to an earlier step (after the checkpoint before it), at most 1 to 5 times."},
    "flow_custom_invalid": {"tr": "Özel adımın adı en çok 60 karakter olabilir ve \"rapor yazar\" veya \"metni düzeltir\" seçilmelidir.",
                            "en": "A custom step's name can have at most 60 characters, and it must either report findings or correct the text."},
    "instructions_too_long": {"tr": "Özel adımın talimatı çok uzun (en çok 20000 karakter).",
                              "en": "The custom step's instructions are too long (at most 20000 characters)."},
    "gate_sent_back": {"tr": "{id}: ciddi sorun bulundu, '{node}' adımına geri gönderildi.",
                       "en": "{id}: serious problems found; sent back to the step '{node}'."},
    "gate_limit": {"tr": "{id}: ciddi sorun kaldı ama geri gönderme sınırı doldu; raporda işaretlendi.",
                   "en": "{id}: serious problems remain, but the limit of sending back is reached; marked in the report."},
    "stage_not_assigned": {"tr": "Şu adımlara model atanmamış: {stages}. İş akışı sekmesinde model seçin.",
                           "en": "No model is assigned to these steps: {stages}. Choose a model in the Workflow tab."},
    "run_started": {"tr": "Çalıştırma başladı.", "en": "The run started."},
    "nothing_running": {"tr": "Çalışan bir iş yok.", "en": "Nothing is running."},
    "run_stopped": {"tr": "Durduruldu. Aynı ayarlarla yeniden başlatınca kaldığı yerden devam eder.",
                    "en": "Stopped. Start it again with the same settings to continue where it stopped."},
    "output_missing": {"tr": "Çıktı bulunamadı.", "en": "Output not found."},
    "model_invalid": {"tr": "Geçersiz model adı: {name}. Biçim: araç veya araç/model (örnek: claude/opus).",
                      "en": "Invalid model name: {name}. Format: tool or tool/model (for example: claude/opus)."},
    "stage_needs_model": {"tr": "'{stage}' adımına en az bir model atayın.", "en": "Assign at least one model to step '{stage}'."},
    "stage_one_model": {"tr": "'{stage}' adımına tek model atanabilir.", "en": "Step '{stage}' takes exactly one model."},
    "stage_too_many": {"tr": "'{stage}' adımına en çok 4 model atanabilir.", "en": "Step '{stage}' takes at most 4 models."},
    "stages_saved": {"tr": "İş akışı kaydedildi. Bundan sonra başlatılan çalıştırmalarda kullanılır.",
                     "en": "The workflow is saved. It applies to runs started from now on."},
    "report_word": {"tr": "Rapor", "en": "Report"},
    "prompt_rules": {"tr": "Yayın ilkeleri: bütün adımlarda geçerli kurallar", "en": "Publishing rules: rules for every step"},
    "prompt_translate": {"tr": "1. adım: ilk tercüme", "en": "Step 1: first translation"},
    "prompt_review": {"tr": "Tashih turları: tashih raporu", "en": "Review rounds: review report"},
    "prompt_revise": {"tr": "Tashih turları: tashihleri uygulama ve raporları uzlaştırma",
                      "en": "Review rounds: applying the review and reconciling the reports"},
    "prompt_source_check": {"tr": "Baştan kaynak kontrolü", "en": "Source check from the start"},
    "prompt_custom_report": {"tr": "Özel adım (rapor yazar): adımın talimatını {{instructions}} yerine koyar",
                             "en": "Custom step (reports findings): puts the step's instructions at {{instructions}}"},
    "prompt_custom_rewrite": {"tr": "Özel adım (metni düzeltir): adımın talimatını {{instructions}} yerine koyar",
                              "en": "Custom step (corrects the text): puts the step's instructions at {{instructions}}"},
    "prompt_gate": {"tr": "Kontrol noktası: kalan ciddi sorunları arar", "en": "Checkpoint: looks for serious problems that remain"},
    "prompt_glossary": {"tr": "Hazırlık: terim sözlüğü", "en": "Preparation: terminology glossary"},
    "prompt_align": {"tr": "Hazırlık: referans tercümede karşılığı bulma", "en": "Preparation: finding the passage in the reference translation"},
    "placeholders_missing": {"tr": "eksik yer tutucular: {names}", "en": "missing placeholders: {names}"},
    "placeholders_unknown": {"tr": "tanınmayan yer tutucular: {names}", "en": "unknown placeholders: {names}"},
    "prompt_not_saved": {"tr": "Kaydedilmedi; {problems}. Yer tutucular, çeviri uygulamasının metni koyduğu yerlerdir.",
                         "en": "Not saved; {problems}. Placeholders are where the translation app inserts the text."},
    "prompt_saved": {"tr": "Kaydedildi. Bundan sonra işlenen bölümlerde kullanılır.",
                     "en": "Saved. It applies to the segments processed from now on."},
    "prompt_restored": {"tr": "Varsayılan talimat geri yüklendi.", "en": "The default instructions are restored."},
}
