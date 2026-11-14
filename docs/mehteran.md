# Mehteran: user guide

[Türkçe](mehteran.tr.md) · [Back to the README](../README.md)

Mehteran runs AI workflows on this computer. A workflow is a YAML file: a graph of nodes (read a document, ask a model, merge texts, ask a person, save a report). The models are called through the command-line tools that the translation app already uses (Claude Code, Codex, Antigravity CLI, Gemini CLI). Mehteran keeps no keys and no accounts of its own.

The translation app is part of Mehteran's interface: the "Book translation" card of its Workflows tab opens the translation app with all its features, in Mehteran's own page (see below). The translation app's Python code stays unchanged, and `./translate ui` keeps working on its own.

## Start

| | macOS / Linux | Windows |
|---|---|---|
| Web interface (double-click) | `Open Mehteran.command` | `Open Mehteran.bat` |
| Web interface | `./mehter ui` | `mehter ui` |
| Command line | `./mehter <command>` | `mehter <command>` |

The interface opens at `http://127.0.0.1:8766/`. When the code changes while the interface runs (an update), the page says so in a banner: close the terminal window of the server and start it again. Starting `mehter ui` a second time on a busy port says the same when the running one is out of date. It runs while the terminal window stays open. The launcher works like the translation app's (`scripts/start.sh`, `scripts/start.cmd`): it uses Python 3.11 or later and installs a private Python (uv) when the computer has none, and before `ui` it brings a git copy of the code folder up to date (`python -m pipeline update`, the translation app's own update step).

The language button (a flag and the language's name) is at the top right: 18 interface languages, see "Languages". On the command line, use `--lang <code>` (`tr`, `en`, `de`, `ar`...) before the command.

## Web interface

The interface has the same design as the translation app's and three tabs: Workflows, Runs, Setup. Addresses of earlier versions (`#templates`, `#workflow/...`, `#runs/new/...`) still open the matching screen. The first screen is Setup while the tools are not ready, otherwise the tab used last; the Mehteran name at the top left goes there too.

- **Islamic book translation** (the pinned card at the top of the Workflows library, with a book icon; address `#workflows/translation[/books|workflow|prompts]`, the old `#translation...` addresses lead there): the translation app itself, with all its features: Books, its translation workflow and its instructions, as sections under "← Workflows". The card is built like a workflow's card (icon, badges, name, description, star, main button) and shows how many books there are and how many are being translated. Its star makes it a favorite (`app:translation` in `library.json`, `PUT /api/templates/app/translation/favorite`). Its Setup tab is Mehteran's Setup tab: every link to it opens that one. The language switch changes both. How it works: see "The book translation" below.
- **Workflows**: the library and the visual editor. The library shows a card per workflow (your own first, then by category), a search that ignores case and accents (also Turkish ones: "sozlesme" finds "Sözleşme") and a filter per category. A card opens a panel with the description, a drawing, the inputs and the results, the YAML, and the actions: "Run", "Edit" (opens the editor; a built-in template opens as your own unsaved copy), "Duplicate" (a copy of your own under a new id; it records the template and version it came from in `based_on`, and a later update of the built-in template never changes it), "Download YAML", "Delete" (your workflows only). Your workflows also have a YAML editor there; "Import" adds a workflow file; "New workflow" starts an empty one.
- **Runs**: the run history on the left, one run on the right: its flow live (the editor's canvas, read-only, each box coloured by its status), a progress line per node, the results to download, and the panel of the selected node: its outputs (read them in the reader or download them), the prompt sent to the model, approve or reject, retry. Below the workflow runs, the list shows the last run of each book of the book translation (`GET /api/translation/runs`, read from each book's `work/run.json`); a click opens the books. Everything that runs has a stop button (■) in the list. "Resume" continues a failed, cancelled or interrupted run; "Cancel" stops it; "Run again" opens the run window with the same workflow.
- **Setup**: the same tool cards as the translation app's Setup tab, on the same code (`pipeline.tools`, `pipeline.runtime`): installed and signed-in status, "Install missing tools" (the tools that the translation workflow and the templates use, and the PDF reader), an install button per tool, the sign-in methods (account, or an API key for Codex and Gemini), "Test", the last usage limit, and a getting-started box. Each card says who uses the tool (Translation, templates). The tools go into the same `<code folder>/.runtime` as the translation app's, so both share one installation. A tool that the translation app's `config.toml` does not configure is shown, but cannot be used. Each card is marked "Required" (used by a template or the translation, and the PDF reader) or "Optional". Below them, "Local tools" (all optional): the Ollama card (status, install after a confirmation that names the version, the source and the folder, the install log with Cancel), its models (installed ones with Delete; recommended ones with size, memory and languages, and a warning when one is too big for this computer; another model by name; one download at a time with progress and Cancel), the Tesseract OCR card (install after a confirmation, languages to add), and the Typst, Pandoc, speech to text (with its models) and qpdf cards (install after a confirmation that names the version, the download size, the source and the folder; the install log with Cancel). Local models are marked "local" wherever a model is chosen.

A run starts in the run window ("Run" on a card, in a workflow's panel or in the editor): every input of the workflow (a file input takes an upload, a model input offers the configured tools with their models and thinking levels); "Start the run" opens the run on the Runs tab.

### The book translation

The book translation is the translation app's own interface, inside Mehteran's page: `pipeline/ui/app.js` (served as `/tr/app.js`, the same file, no copy) draws Books, the translation workflow and the instructions in the Workflows tab (`TranslationUI.mount`), with Mehteran's language, session key and message line. Its links to Setup open Mehteran's Setup tab.

Its requests go to `/api/tr/...` of Mehteran's own server (`mehteran/translation.py`). When `mehter ui` starts, it loads the translation project once, the way `./translate ui` does (`pipeline.web.App(Project.load(...))`), without a second server. A request to `/api/tr/<path>` is answered by the translation app's own request handling (`pipeline.web.make_handler`) as `/api/<path>`: the same routes, checks, streamed uploads (up to 300 MB), downloads and error codes. Mehteran's Host and session-key checks come first; the translation app takes Mehteran's session key. When the project cannot load, the book translation view and the terminal say why; the rest of Mehteran works. `./translate ui` (port 8765) can run at the same time: a book's run is locked per book, across programs.

The translation workflow's diagram ("Translation workflow", in Mehteran and in `./translate ui`) is zoomable: −, + and the zoom level (a click: 100 %), "Fit", Ctrl/⌘ + wheel or a trackpad pinch, and dragging empty space to pan. The chosen zoom is kept in the browser and put back after every redraw; without one the diagram fits the canvas, at 85 % or more. "Full screen" gives the diagram and the panel of the selected step the whole window (Esc ends it; new steps come in through the "+" between the steps there). The steps are drawn larger, with a clear number, the whole model names and a clear selected step; "+ Add step" before the delivery says what the "+" does. On a wide window the panel of the selected step is next to the diagram, otherwise below it. Selecting steps, changing models, dragging, adding, removing and reordering steps and saving work as before.

When the translation app's code changes (`pipeline/*.py`, `pipeline/ui/*`) while `mehter ui` runs, the page shows the same "restart the server" banner as for Mehteran's own code.

## Languages

One list holds every language: `mehteran/languages.json` (the language registry). An entry has the code, the language's own name, its English name, the country code of its flag and its direction: `{"code": "ar", "native": "العربية", "english": "Arabic", "flag": "sa", "dir": "rtl", "ui": true}`. The Mehteran page, the book translation's interface and the workflows use this list (`mehteran/languages.py`, `GET /api/languages`). It contains every language of the translation app's default list (`config.default.toml`, `[languages]`); a test checks that.

- **Interface languages** (`"ui": true`): Türkçe, English, العربية, Deutsch, Français, Español, Português, Italiano, Русский, فارسی, اردو, Bahasa Indonesia, Bahasa Melayu, Azərbaycanca, Bosanski, Shqip, 简体中文, 日本語. Choose one with the language button at the top right: a list with flags and a search field (type a name in any language, or the code). The keyboard works: Enter, Space or ↓ opens the list, ↑ ↓ move, Enter chooses, Esc closes. The choice is kept in the browser. Arabic, Persian and Urdu turn the page right to left (`<html dir="rtl">`); the workflow drawing, code and logs stay left to right.
- **Complete and partial languages**: Turkish and English have every text. Another language may have only some of the texts; a text that it lacks is shown in English (the page and the server messages both). The translation app's own server messages (`pipeline/i18n.py`) are Turkish or English: every other interface language gets them in English.
- **Flags**: a flag is a country's, a language is not: the flag only helps to find the row, the language's own name is always written beside it. The flags are SVG files of this program (`mehteran/ui/flags/<country>.svg`, from flag-icons 7.2.3, MIT; the license is in that folder), because emoji flags do not show on Windows. Nothing is loaded from the internet.
- **Output language of a workflow**: an input of type `language` offers every language of the registry in the same flag list. A `choice` input whose options are all language codes (and whose id contains `lang`) is shown as the flag list too, with only its options. The run window starts at the interface language when the workflow offers it; else at the workflow's default.

### Where the texts are

| Texts | Turkish and English | Other languages |
|---|---|---|
| Mehteran's page (`S("key")` in `mehteran/ui/*.js`) | `mehteran/locales/tr.json`, `en.json`: `"ui"` | `mehteran/locales/<code>.json`: `"ui"` |
| Server and command-line messages (`i18n.t("key")`) | the same files: `"messages"` | the same files: `"messages"` |
| The book translation's interface | `I18N` in `pipeline/ui/app.js` (its own page has only that file) | `pipeline/ui/locales/<code>.json` (`{key: text}`; Mehteran serves them as `/tr/locales/<code>.json` and gives them to `TranslationUI.mount` / `setLang`) |

- A text added in `mehteran/i18n.py` as `MESSAGES.update({...})` or `UI.update({"key": {"tr": ..., "en": ...}})` still works: it is merged into the loaded texts and does not remove the other languages of that key. `python3 -m mehteran.i18n_tools absorb` moves such blocks into the locale files (run it when nobody else edits `i18n.py`).
- The server reads the locale files when it starts: restart it after a change (the page says so).
- A text keeps the `{name}` placeholders of the English text; a text of the book translation's interface keeps its HTML tags too.

```text
python3 -m mehteran.i18n_tools coverage              how many texts each language has
python3 -m mehteran.i18n_tools missing de            the keys German lacks, with the English text
python3 -m mehteran.i18n_tools missing de --json     the same as {"ui": {...}, "messages": {...}, "translation": {...}}
python3 -m mehteran.i18n_tools merge de done.json    adds a translated file of that form to the locale files
python3 -m mehteran.i18n_tools validate [de]         complete tr and en, known keys, equal placeholders and tags
```

A new interface language: set `"ui": true` on its entry in `mehteran/languages.json`, then `missing <code> --json`, translate the values, `merge`, `validate`.

## Local models (Ollama) and text recognition (OCR)

They are optional and are installed only when you ask (the Setup tab, or the command line below); so are Typst, Pandoc, speech to text (whisper.cpp with ffmpeg) and qpdf, described after them. Each one that is already on the computer (on PATH) is found and used; Mehteran's own copy in `.runtime` comes first. They go into the same `<code folder>/.runtime` folder as the other tools; no administrator rights are needed.

**Ollama** runs models on this computer; nothing is sent anywhere. Mehteran adds a provider `ollama` of its own (the translation app's `config.toml` is not changed; a `[providers.ollama]` there would win). A step uses it as `ollama/<model>`, for example `ollama/gemma3:4b`; the run form offers the installed models. Mehteran calls Ollama's HTTP API on `127.0.0.1` (port 11434) with its own system prompt and the same data tags as for any other model, in the same separate process, so cancel and timeout work the same.

- An Ollama that already runs is used as it is. Else the system's `ollama` (PATH, the macOS app, the Windows install), else the one Mehteran installed. Mehteran starts `ollama serve` on 127.0.0.1 when a run or a download needs it and stops it when Mehteran ends, only if Mehteran started it (its log: `<data>/jobs/ollama-serve.log`).
- Install: Ollama 0.40.16, the official archive of the GitHub release (`ollama-darwin.tgz`, `ollama-linux-amd64.tar.zst` / `-arm64`, `ollama-windows-amd64.zip` / `-arm64`), checked against the SHA-256 sums written in `mehteran/ollama.py` (from the release's `sha256sum.txt`, which matches GitHub's own digests). No install script is run. On Linux, unpacking needs Python 3.14 or the `zstd` program.
- Models: the installed ones (name, size, date), a list of recommended ones (size on disk, memory needed, languages, a note; the tags were checked in the Ollama registry), download with progress and cancel (one at a time), delete. Before a download Mehteran warns when the computer has too little memory, and refuses when the disk is too full (unless forced). Models stay in Ollama's own folder (`~/.ollama/models`, or `OLLAMA_MODELS`).
- Settings: `<data>/configurations/providers.toml` may set `[providers.ollama]` `model` (the default model) and `options` (`num_ctx`, `temperature`, `top_p`, `seed`). Mehteran asks for a context of 8192 tokens by default: Ollama's own default is small and would cut a document silently.

**Tesseract OCR** reads scanned PDFs and images. A PDF page becomes an image with Poppler's `pdftoppm` (300 dpi), then Tesseract reads it.

- Install: Poppler (and micromamba) through the translation app's installer when missing; Tesseract 5.5.4 from conda-forge (micromamba checks every package) into `.runtime/tesseract` (about 460 MB: the package brings the language data of 125 languages, among them `tur`, `eng`, `ara`, `fas`); only when a language is still missing, the language data `eng`, `tur`, `ara`, `fas` from `tesseract-ocr/tessdata_fast`, tag 4.1.0, each checked against a SHA-256 sum written in `mehteran/ocr.py`, into `.runtime/tessdata`. An installed Tesseract (for example from Homebrew) is used too, with its own languages. There is no Tesseract model for Ottoman Turkish (`ota` does not exist); use `ara` or `fas` for the Arabic script.
- More languages, offered in the Setup tab and downloaded only when chosen: `deu`, `fra`, `spa`, `ita`, `por`, `nld`, `rus`, `ell`, `aze`, `kmr` (Kurmanji), `urd`, `heb`, `hin`, `chi_sim`, `jpn`, `kor` (tessdata_fast 4.1.0, each checked against its SHA-256 sum; the sums were also checked against the git blob hashes of the tag). The conda-forge Tesseract already brings most of them; only the missing ones are downloaded. Without a choice, `ocr-languages` installs `eng tur ara fas` as before.
- `document.extract` takes `ocr`: `auto` (the default: only the pages of a PDF that have almost no text layer, and images), `always`, `never`; and `ocr_languages` (`tur+eng`; empty: Turkish and English as far as installed). File inputs also take images: `png`, `jpg`, `jpeg`, `tif`, `tiff`. Limits: 500 pages per file, 180 seconds per page; cancel stops the running program. Without Tesseract, a PDF that has a text layer on some pages is read as before; a fully scanned one fails with a message that says what to install.

**Typst** makes the PDF of `document.export` (`formats: [pdf]`).

- Install: Typst 0.15.1, the official release archive on GitHub (`typst-aarch64-apple-darwin.tar.xz`, `typst-x86_64-apple-darwin.tar.xz`, `typst-x86_64-unknown-linux-musl.tar.xz`, `typst-aarch64-unknown-linux-musl.tar.xz`, `typst-x86_64-pc-windows-msvc.zip`, `typst-aarch64-pc-windows-msvc.zip`; 14–22 MB), into `.runtime/typst`, and the Amiri 1.003 font (SIL Open Font License, 1 MB, from `aliftype/amiri`) into `.runtime/typst/fonts`. Each archive is checked against the SHA-256 sum written in `mehteran/typst.py` (computed from the downloaded files; they match GitHub's own asset digests).
- The Markdown becomes Typst markup: headings, paragraphs (a line break stays a line break, as in the Word and HTML exports), bullet and numbered lists (nested), quotes, code blocks, tables (with their column alignment), rules, bold, italic, strike-through, inline code, `http(s)`/`mailto` links and footnotes (`[^n]` with a `[^n]: text` line). Every piece of text goes into the Typst file as a string literal, so no character of the text can act as Typst markup or code. The page is A4 with page numbers. Fonts: Libertinus Serif (built into Typst; Turkish is covered) and Amiri for the Arabic script; a mostly Arabic paragraph in a left-to-right document is set right to left; `lang` sets the language (an RTL language makes the whole document right to left). Other scripts (Chinese, Japanese, Hebrew...) use the computer's own fonts when it has them. LaTeX math stays as text in the PDF (use Word through Pandoc for equations).
- Without Typst, a workflow with `pdf` fails before it writes anything, with "PDF export needs Typst. Install Typst on the Setup tab."

**Pandoc** (optional) converts documents. Mehteran's own Word exporter stays the default.

- Install: Pandoc 3.14, the official release archive on GitHub (`pandoc-3.14-arm64-macOS.zip`, `-x86_64-macOS.zip`, `-linux-amd64.tar.gz`, `-linux-arm64.tar.gz`, `-windows-x86_64.zip`; 27–44 MB, about 190 MB unpacked; Windows on ARM uses the x64 build), checked against the SHA-256 sums in `mehteran/pandoc.py`, into `.runtime/pandoc`. Pandoc always runs with `--sandbox`: a document cannot make it read other files or fetch anything.
- `document.export`: `formats: [epub]` needs Pandoc. `converter`: `auto` (the default: Mehteran's own Word file; Pandoc's when Pandoc is installed and the text has LaTeX math, `$...$` or `$$...$$`, which becomes real Word equations), `builtin`, `pandoc` (every Word file through Pandoc). A lone `$5` is not math.
- `document.extract` reads `.odt` and `.rtf` through Pandoc (as Markdown; tables become Markdown tables). EPUB and Word input are read as before, without Pandoc.

**Speech to text** (whisper.cpp with ffmpeg) writes down what is said in audio and video files, on this computer.

- Install: the pinned conda-forge packages `whisper.cpp=1.9.3` (about 13 MB download) and, only when the computer has no ffmpeg, `ffmpeg=9.0.2` (about 80–170 MB with its libraries, depending on the system), into `.runtime/speech`; micromamba checks every package. conda-forge builds both for macOS (arm64, x64), Linux (x64, arm64) and Windows x64; there is no build for Windows on ARM. Then the `base` model.
- Models: the multilingual ggml models of the official `ggerganov/whisper.cpp` repository on Hugging Face, at the pinned revision `5359861c`, each checked against the SHA-256 sum in `mehteran/speech.py` (computed from the downloaded files; they match the repository's LFS sums), into `.runtime/whisper-models`: `tiny` (78 MB), `base` (148 MB), `small` (488 MB), `large-v3-turbo-q5_0` (574 MB, the most accurate), `medium` (1.5 GB).
- `document.extract` reads `mp3`, `wav`, `m4a`, `ogg`, `opus`, `flac`, `aac`, `mp4`, `webm`, `mov`, `mkv`: ffmpeg makes a 16 kHz mono WAV, whisper.cpp writes the text. Advanced settings: `speech_model` (`auto`: the first installed of base, small, large-v3-turbo-q5_0, medium, tiny; or one of them) and `speech_language` (`auto` detects it; `tr`, `en`, `ar`, `fa`, `ur`, `de`, `fr`, `es`, `it`, `ru`, `az`, `nl`, `pt`, `zh`, `ja`). Cancel stops the running program. Without the tools or a model the step fails with a message that says what to install.

**qpdf** repairs damaged PDFs and removes the encryption of PDFs that open without a password. When `document.extract` cannot read a PDF (pdftotext fails), it lets qpdf write a repaired copy and reads that; without qpdf the first error stands. Install: the pinned conda-forge package `qpdf=12.4.2` (about 6 MB download) into `.runtime/qpdf`.

The conda-forge installs (speech to text, qpdf) need micromamba; when it is missing, the translation app's installer brings it with Poppler first (the confirmation says so).

**Recommended Ollama models** also list a vision model (`qwen2.5vl:7b`, 6.0 GB) and an embedding model (`bge-m3:567m`, 1.2 GB), labelled as such. Mehteran's steps do not send images to a model yet, and an embedding model cannot be a step's model: they are listed for later use.

```
./mehter install-local ollama                     install Ollama (pinned version, checked)
./mehter install-local ocr [tur eng ara fas]      install Tesseract OCR and language data
./mehter install-local ocr-languages tur ara jpn  add language data
./mehter install-local typst                      install Typst and the Amiri font
./mehter install-local pandoc                     install Pandoc
./mehter install-local speech [base]              install whisper.cpp (and ffmpeg when missing) and models
./mehter install-local speech-models small tiny   add speech models
./mehter install-local qpdf                       install qpdf
```

The API of the Setup tab:

| Route | Answer |
|---|---|
| `GET /api/local-tools` | `{tools: [ollama, ocr, typst, pandoc, speech, qpdf], pull}` (below) |
| `POST /api/local-tools/(ollama\|ocr\|typst\|pandoc\|speech\|qpdf)/install` | starts the install job; `{message}` |
| `POST /api/local-tools/ocr-languages/install` `{languages: [..]}` | adds language data |
| `POST /api/local-tools/speech-models/install` `{models: [..]}` | adds speech models; 400 for an unknown name |
| `POST /api/local-tools/(ollama\|ocr\|ocr-languages\|typst\|pandoc\|speech\|speech-models\|qpdf)/cancel` | stops that job; `{cancelled}` |
| `GET /api/ollama/models` | `{running, installed: [{name, size, modified}], recommended: [{name, size, ram, languages, notes: {tr, en}, installed}], memory, disk_free}` (starts Ollama when it is installed) |
| `POST /api/ollama/pull` `{name, force?}` | `{started, warnings}`; 409 with `problems` when the disk is too full or a download runs |
| `GET /api/ollama/pull` | `{name, status, completed, total, percent, done, error, cancelled, started}` |
| `POST /api/ollama/pull/cancel` | `{cancelled}` |
| `POST /api/ollama/delete` `{name}` | `{ok}` |

`ollama`: `{id, name, installed, source ("system" | "mehteran" | null), path, version, running, started_by_mehteran, url, pinned_version, size, install_dir, models_dir, disk_free, memory, job}`. `ocr`: `{id, name, installed, source, path, version, pinned_version, pdftoppm, size, languages, available_languages: [{code, size, installed}], job, languages_job}`. `typst`, `pandoc`, `speech`, `qpdf`: `{id, name, installed, source, path, version, pinned_version, size, download_size, install_dir, disk_free, job}`; `typst` adds `arabic_font`; `speech` adds `ffmpeg` (its path or null), `ffmpeg_source`, `ffmpeg_version`, `poppler_first`, `models`, `available_models: [{name, size, installed}]`, `models_job`; `qpdf` adds `poppler_first` (true: micromamba and Poppler come first). A recommended model may have `kind`: `"vision"` or `"embedding"`. A `job` is `null` or `{running, code, log}`, as in `/api/tools`. Sizes are in bytes.

## Usage, switching the model of a step, live logs

**Usage** (`GET /api/usage`). Mehteran counts each of its model calls (table `calls`: provider, model, start, seconds, outcome `ok` / `failed` / `quota` / `aborted`, for a limit until when). Per provider:

```
{generated, providers: [{provider, tool ("claude"|"codex"|"gemini"|"antigravity"|"ollama"|null), configured,
  calls, ok, failed, quota, aborted, seconds, last_call,
  windows: {today|5h|7d: {calls, ok, failed, quota, aborted, seconds}}, models: {<model>: {...the same counts}},
  last_quota: {at, until, message}|null, resets_at (until, while it is in the future)|null,
  tool_reported: {...}|null, translation_quota: <the translation app's .jobs/quota.json entry>|null,
  setup_quota: <the last limit of a Setup model test>|null}]}
```

`tool_reported` is only what a tool itself writes; `null` means unknown:

- Codex: its session logs (`~/.codex/sessions/**/rollout-*.jsonl`, `$CODEX_HOME`) hold its rate limits; the newest entry: `{source: "codex-session-log", observed_at, plan, limit_reached, windows: [{name: "primary"|"secondary", used_percent, window_minutes, resets_at, expired}]}` (primary: the 5-hour window, secondary: the weekly one; `expired`: the window has reset since). Mehteran's own Codex calls are `--ephemeral` (the translation app's command) and write no session log, so the value comes from the last interactive Codex use. No credentials file is read.
- Claude Code: reports its limits only in its stream-json output (`rate_limit_event`); the translation app's command uses text output. `POST /api/usage/probe/<provider>` (a Claude provider only) asks once, with the smallest model and a one-word prompt, and keeps the answer: `{source: "claude-rate-limit-event", observed_at, status, limit_type, resets_at, windows: [{name: "five_hour"|"seven_day", utilization (0–1), resets_at, status}]}`.
- Gemini CLI, Antigravity CLI, Ollama: no limits reported (`null`).

**Switching the model of a step** (`POST /api/runs/<run>/nodes/<node>/switch` `{provider: "gemini/<model>"}` → `{ok}`): for an AI step that waits for a usage limit, failed, was cancelled or was interrupted. The provider must be configured. The event log gets "Model switched: old → new" (key `event_switched`). A waiting step stops waiting at once and runs again with the new model; the others are retried. A loop keeps the parts it already has (a part's answer is keyed by its prompt, not by the model). Not switching means waiting, as before. The run keeps the new model (`providers` of the run).

A step may name a fallback model (off unless written): `fallback_provider: gemini/gemini-2.5-pro` (or a `provider` input, `"{{inputs.backup}}"`) next to `retries`. When the step's model reports a usage limit, the step switches to it at once instead of waiting (event key `event_switched_auto`); when the fallback reports a limit too, the step waits. Only AI steps (and conditions that ask a model) take it; the check refuses others and names that are not provider names.

**Live logs** (`GET /api/runs/<run>/log?node=<node>&offset=<bytes>` → `{text, offset, size, done, status}`): each node writes `nodes/<node>/log.txt` while it works: attempts, each model call (and its answer), a "still working" line every 30 seconds, usage-limit waits, model switches, loop parts. Read it from `offset` 0, then from the returned `offset`; `done` is true when the node has ended and everything was read. At most 64 KB per answer, 2 MB per log; obvious secrets (`sk-…`, `Bearer …`, Google and GitHub keys) are masked. A log is written in the language of the run.

What streams: Ollama's answer streams into the log as the model writes it. The command-line tools (Claude Code, Codex, Gemini CLI, Antigravity) are called through the translation app's provider code (`pipeline.providers.run`), which waits for the tool to end and returns only the answer: their answer appears in the log when the call ends; meanwhile the log shows the call and the heartbeat lines.

**Activity** (`GET /api/activity` → `{runs: [...], translation: [...], time}`), cheap enough for a header indicator: each running, queued or waiting run `{id, workflow_name, status, started, elapsed, done, total, waiting_quota, nodes: [{id, status, started, elapsed, attempts, waiting_reason, progress}]}` (only the nodes that work or wait), and each book the translation app is translating now `{book, state ("running"|"waiting_quota"), stage, started, elapsed, quota}` (its `run.json`, read only).

**In the interface** (`mehteran/ui/live.js`):

- Setup: each AI tool's card has a "Usage" part: Mehteran's own counts (today, last 5 hours, last 7 days: calls, failures, usage limits, time), the last usage limit with a countdown to its reset, and the limits the tool reports itself ("unknown" when it reports none). A Claude Code card has "Check usage", which makes one tiny model call (`POST /api/usage/probe/<provider>`).
- The run form and the model choice of a step show a short usage hint next to the tool ("5 hours: 54 %"), in a warning colour near a limit.
- The run page: an overall progress bar, elapsed timers, attempts and the waiting reason of each step, and the live log of the selected step (else the step that works now): monospace, it follows the end, pauses when you scroll up ("Paused · jump to the end"), "Copy". A step that waits for a usage limit, failed, was cancelled or was interrupted offers "Keep waiting" (the default) and "Continue with another model" (every configured model, with its usage hint); the step's panel lists its model switches.
- The editor: "Fallback model" in the advanced settings of a step that takes a model (empty: off).
- The header shows what runs now ("2 running", in a warning colour while something waits for a usage limit); a click lists the runs and the books being translated, each a link with a stop button (■). It asks every 4 seconds while something runs, every 20 seconds otherwise, and less often while the window is hidden.
- The library: a star on each card and in the workflow's panel marks a favorite (kept in `<data>/configurations/library.json`; `PUT /api/templates/<source>/<id>/favorite {on}`; the list's `favorite` flag). "Favorites" comes right under the book translation, with a "★ Favorites" filter; "Recently used" lists the workflows of the last runs. The run form remembers the last values of each workflow in this browser (models, choices, texts; never files or anything named like a key or password): "Same as last time" fills them in. "/" puts the cursor in the search.

## Command line

```
./mehter templates                               list the templates
./mehter validate my-flow.yaml                   check a workflow file; lists every problem
./mehter run document-comparison \
    --input first=old.docx --input second=new.docx \
    --input analyst_model=claude/opus@high --input language=tr
./mehter run multi-document-comparison \
    --input documents=a.pdf --input documents=b.docx --input documents=c.md
./mehter runs                                    the run history
./mehter resume <run> [--node <id>]              continue a run, or retry one failed node
./mehter cancel <run>                            stop a run
./mehter approve <run> <node> [--comment ...]    approve a waiting approval node (reject: the same)
```

`run` takes a template id (`builtin:<id>`, `user:<id>` or a bare id) or a path to a `.yaml` file. An input with `multiple: true` takes `--input <id>=<file>` once per file. It shows the status of each node until the run ends. Ctrl+C cancels the run. Exit code: 0 finished, 3 waiting for an approval, 1 otherwise.

## Built-in templates

36 built-in templates in six categories. Each one is described in the Templates tab (what it does, its inputs, its flow).

| Category | Templates |
|---|---|
| **Research** (`research`) | `abstract-title-improvement` (Abstract and title improvement), `academic-paper-review` (Academic paper review), `grant-proposal-review` (Grant proposal review), `literature-synthesis` (Literature synthesis), `research-question-critique` (Research question and hypothesis critique), `reviewer-response-letter` (Response letter to reviewers), `study-guide-questions` (Study notes and exam questions), `thesis-chapter-feedback` (Thesis chapter feedback) |
| **Documents** (`documents`) | `chapter-summaries` (Long document, chapter by chapter; a loop), `document-comparison` (Document comparison), `document-consistency-check` (Document consistency check), `meeting-minutes-actions` (Meeting minutes and action items), `multi-document-comparison` (Multi-document comparison; several files and a loop), `multi-length-summary` (Summary at several lengths), `policy-gap-analysis` (Policy gap analysis), `requirements-review` (Requirements document review) |
| **Legal** (`legal`) | `contract-risk-review` (Contract risk review), `nda-review` (NDA review), `regulatory-compliance-checklist` (Regulatory compliance checklist), `terms-plain-language` (Terms and privacy policy in plain language) |
| **Business** (`business`) | `business-plan-critique` (Business plan and pitch critique), `expense-anomaly-review` (Invoice and expense anomaly notes), `financial-period-comparison` (Two-period financial comparison), `financial-report-analysis` (Financial report analysis), `request-triage` (Request and complaint triage; a condition), `rfp-compliance-matrix` (RFP compliance matrix) |
| **Data** (`data`) | `data-analysis-plan` (Data analysis plan and interpretation), `dataset-documentation-review` (Dataset documentation review), `spreadsheet-analysis` (Spreadsheet (CSV / Excel) analysis), `survey-response-themes` (Survey free-text themes) |
| **Writing** (`writing`) | `cv-job-fit` (CV and job posting fit), `plain-language-rewrite` (Plain-language rewrite), `proofreading-change-list` (Proofreading with a change list), `style-guide-review` (Editorial review against a style guide), `tone-audience-adaptation` (Tone and audience adaptation), `translation-quality-review` (Translation quality review) |

## Where the data is

Mehteran keeps its data outside the code folder:

| System | Folder |
|---|---|
| macOS | `~/Library/Application Support/Mehteran` |
| Windows | `%LOCALAPPDATA%\Mehteran` |
| Linux | `$XDG_DATA_HOME/mehteran`, else `~/.local/share/mehteran` |

The environment variable `MEHTERAN_HOME` replaces this folder. Subfolders:

- `templates/`: your templates (one `<id>.yaml` each).
- `executions/<run>/`: one folder per run: `workflow.yaml` (the frozen copy), `inputs/` (the uploaded files; `inputs/<id>/<n>/` for each file of an input with several), `nodes/<node>/` (the outputs of each node, the prompt of each model call; a loop keeps each part's prompt and answer in `nodes/<node>/parts/`).
- `databases/mehteran.sqlite3`: the state of every run and node (SQLite, WAL mode).
- `configurations/`: what the Setup tab keeps: `models.json` (the model lists read from the tools, offered next to the models of `config.toml`) and `quota.json` (the last usage limit that a model test met).
- `jobs/`: the logs of the installs started from the Setup tab.
- `workflows/`: reserved for later versions; empty now.

The tools come from the translation app's `config.toml` (`[providers.*]`), which Mehteran only reads; it never writes it. Sign-ins are kept by the tools themselves, in their own folders (as in the translation app). `MEHTERAN_CONFIG` can name another TOML file with the same sections.

## How a run works

- A node starts as soon as all nodes it is connected from have finished. Nodes that do not depend on each other run at the same time (at most 4 per run).
- Each node has a number of retries and a timeout per attempt. A timeout or a cancel stops the model call together with the tool it started.
- A model gets the prompt on stdin, in an empty temporary folder, through the translation app's provider code (`pipeline.providers.run`). Mehteran makes one attempt per call; the engine counts the retries.
- Usage limits: when a tool reports a usage or rate limit (detected by the translation app's code, `pipeline.providers`), the node does not fail. It shows "waiting for the usage limit" (`waiting_quota`), the event log says until when, and it tries again when the limit resets: the time the tool names, else `quota_wait_minutes` of `config.toml` (`[general]`). A wait is not counted as a failed attempt. When the waiting would last longer than `quota_max_hours` in total, the node fails. Cancel ends the wait at once.
- At most 4 model calls run at the same time per run, also those of loop parts.
- Conditions: a `condition` node outputs only the port of the branch it takes (`true` or `false`). The nodes connected to the other port are skipped, and so is everything that depends only on them. A join (`text.merge`, `document.export`) runs when at least one of its connections comes from a branch that was taken; the output of a skipped branch is an empty text there. Any other node runs only when all its connections were taken. A skipped branch does not fail the run; a failed node still skips everything after it and fails the run.
- Loops: an `ai.map` node splits a text into parts and asks the model once per part, in parallel. Each answer is stored with a hash of its prompt: a retry or a resumed run asks only for the parts that have no answer yet. The node's timeout applies to each model call, not to the whole node; the retries apply to the node (finished parts are kept between attempts).
- The run stores a frozen copy of the workflow, the resolved model names (`claude/opus@high`) and the tool settings. Resume and retry use these copies, not the current template.
- Resume: the nodes that finished are kept; only the others run. A run whose program ended (closed terminal, crash) shows as "interrupted" and can be resumed.
- An approval node stops its branch until a person approves or rejects it. No program needs to stay open meanwhile; the approval can come from the interface or the command line, also after a restart.
- Only one program drives a run at a time (a lock file in the run folder).
- Messages in any language: Mehteran stores its own messages (the event log, the errors of nodes and runs) with their message key and values, and shows them in the language of whoever reads them (the interface language, the command line's `--lang`). An event in `GET /api/runs/<run>` is `{time, node_id, kind, message, text, key, params}`: `message` and `text` are the same text in the request's language; `key` and `params` are the stored message (a nested message is `{"$key": ..., "params": {...}}`), or `null` for older runs and for text that a tool wrote, which is shown as it was stored. A node (and a run in the run list) has `error` in the request's language, plus `error_key` and `error_params` in the same form. The database gets the new columns by itself; old rows keep their text.

## Workflow file reference (schema_version 1)

```yaml
schema_version: 1
id: my-review                 # lower-case letters, digits, "-" and "_"; at most 64
name: {tr: İnceleme, en: Review}   # a text, or a {tr, en} map (the same for description and labels)
description: What the workflow does.
version: "1.0"
category: research
inputs:
  - {id: paper, type: file, label: {tr: Makale, en: Paper}, formats: [pdf, docx, epub, md, txt]}
  - {id: sources, type: file, multiple: true, required: false, formats: [pdf, md, csv, xlsx]}   # several files
  - {id: language, type: language}   # the output language: any language, chosen from the flag list (see below)
  - {id: model, type: provider, default: claude}
  - {id: note, type: text, multiline: true, required: false, default: ""}
nodes:
  - id: extract
    type: document.extract
    config: {file: "{{inputs.paper}}"}
  - id: review
    type: ai.cli
    retries: 2                 # extra attempts (0 to 10)
    timeout: 900               # seconds per attempt
    config:
      provider: "{{inputs.model}}"   # or a fixed name: claude, claude/opus, claude/opus@high
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
layout:                        # optional: where the editor draws each node
  extract: {x: 0, y: 0}
  review: {x: 324, y: 0}
  save: {x: 648, y: 0}
```

`layout` is written by the visual editor: for each node, the position of its box in canvas pixels. Only node ids of the workflow, each with exactly `x` and `y`, whole numbers from −100000 to 100000. The engine ignores it. Without it, the editor places the boxes automatically in flow order.

Input types: `file` (an upload; `formats` limits the types: `pdf`, `docx`, `epub`, `md`, `txt`, `csv`, `tsv`, `xlsx`, images `png`, `jpg`, `jpeg`, `tif`, `tiff` (read by OCR), `odt`, `rtf` (read by Pandoc), and audio and video `mp3`, `wav`, `m4a`, `ogg`, `opus`, `flac`, `aac`, `mp4`, `webm`, `mov`, `mkv` (speech to text); `multiple: true` takes 1 to 20 files, at most 500 MB together), `text` (`multiline`), `choice` (`options`: texts or `{value, label}`), `provider` (a tool, optionally with model and thinking level), `language` (a language code of the registry; see "The output language"). Inputs are required unless `required: false`.

Tables: a CSV, TSV or Excel (.xlsx) file is read into Markdown tables, the first row as the header. A CSV may use `,`, `;`, a tab or `|` (detected); UTF-8, or else Windows Turkish (cp1254). Each visible sheet of an .xlsx file is a table under `## <sheet name>`; numbers with a date format become dates (`2024-01-31`). Limits, each with a note in the text where it cut: 1,000 rows and 40 columns per table, 300 characters per cell, 20 sheets, 500,000 characters per file.

Node types:

| Type | Settings (`config`) | Outputs | Default retries / timeout |
|---|---|---|---|
| `document.extract` | `file` (exactly one file placeholder), `max_chars` (per file), `ocr` (`auto`, `always`, `never`), `ocr_languages`, `speech_model`, `speech_language` | `text` (empty when an optional file input was left empty; with several files, each between `<document name="<file>" index="<n>">` and `</document>`) | 0 / 3600 s |
| `ai.cli` | `provider`, `prompt` | `text` | 2 / the `timeout` of `config.toml` |
| `condition` | `value` (the text to test; default: the connected text), `operator` (`ai`, `contains`, `not_contains`, `equals`, `regex`, `is_yes`, `empty`; default `contains`), `question` and `provider` (for `ai`), `match` (not for `ai`, `is_yes` and `empty`), `case_sensitive` (default false) | `true` or `false`: only the branch taken, carrying `value` | 0 / 60 s |
| `ai.map` | `source`, `split` (`headings`, `paragraphs`, `chunks`, `files`), `chunk_chars` (500–200000, default 12000), `max_items` (1–200, default 50), `provider`, `prompt` (may use `{{item.text}}`, `{{item.title}}`, `{{item.index}}`, `{{item.count}}`), `heading` (default true) | `text`: the answers in order, each under `## <part title>` | 2 / the `timeout` of `config.toml`, per model call |
| `text.merge` | `template` | `text` | 0 / 60 s |
| `approval` | `show` (the text to approve), `instructions` | `text`, `comment` | none (waits for a person) |
| `document.export` | `source`, `title`, `lang`, `formats` (`md`, `docx`, `html`, `pdf`, `epub`), `filename`, `converter` (`auto`, `builtin`, `pandoc`) | one file per format; Markdown tables become real tables in Word, HTML and PDF | 0 / 300 s |

### The output language (for template authors)

Use an input of type `language` for the language a workflow writes in:

```yaml
inputs:
  - {id: language, type: language, label: {tr: Rapor dili, en: Report language}}
```

- The run window shows it as the flag list with every language of the registry, and starts at the interface language of whoever runs it. Do not set `default`: with `default: en` a Turkish user gets English documents unless they change it. (`default: <code>` is allowed for a workflow that must start at one language.)
- Its value is the language code (`tr`, `en`, `ar`, `uz`...). Give it to `document.export` as `lang: "{{inputs.language}}"`. When the input's id is `language` and an instruction does not use `{{inputs.language}}`, the line "Write the answer in <English name of the language>." is added to that instruction, so an instruction needs no language sentence of its own.
- From the command line or the API, a run without a value (and without a default) uses the message language (`--lang`, `X-Lang`).
- `options` is not allowed on a `language` input. To offer only some languages, keep a `choice` input with language codes as its options (`options: [tr, en, ar]`, id `language`): it is shown as the flag list with those options, and starts at the interface language when that is one of them.
- The labels and descriptions of a workflow stay `{tr, en}` maps; another interface language shows the English text.

### Instruction-only steps

A step may be only an instruction and a model; the connections say which texts it works on. This is what the editor's simple panel shows (the fields marked `basic` in `GET /api/node-types`: `ai.cli` and `ai.map`: `prompt` (the instruction) and `provider`; `condition`: `question` and `provider`; `document.export`: `formats`; `approval`: `instructions`; `document.extract` and `text.merge`: none). A new condition node starts with `initial_config` (`{"operator": "ai"}`).

```yaml
schema_version: 1
id: minimal
name: Summary
inputs:
  - {id: doc, type: file}
nodes:
  - {id: read, type: document.extract}                       # no file named: the only file input
  - {id: summary, type: ai.cli, config: {provider: claude, prompt: "Summarise this document in five points."}}
  - {id: urgent, type: condition, config: {operator: ai, provider: claude, question: "Does it ask for something urgent?"}}
  - {id: alert, type: ai.cli, config: {provider: claude, prompt: "Write a short alert for the manager."}}
  - {id: save, type: document.export, config: {formats: [md, docx]}}   # no source: the connected texts
connections:
  - {from: read.text, to: summary}
  - {from: summary.text, to: urgent}
  - {from: urgent.true, to: alert}
  - {from: summary.text, to: save}
  - {from: alert.text, to: save}
```

The rules (a step that names its data, as every built-in template does, works exactly as before):

- `ai.cli`: when the instruction names no data (no `{{nodes.*}}` and no file input), the texts of the connected steps are added after it, in connection order, each under its step's label and between data tags (the same data-not-instructions note as always). When the workflow has an input `language` that the instruction does not use, a last line says "Write the answer in <language>." (`tr` → Turkish, `en` → English; other values as written). A connection from a whole node brings its `text` output; a skipped branch adds nothing.
- `ai.map`: without `source`, the connected texts (joined); without `{{item.text}}` in the instruction, each part (its title and text, as data) and the language line are added after the instruction.
- `text.merge` without `template`, `document.export` without `source`: the connected texts in connection order, each under a `## <label>` heading when there are several; a skipped branch is left out.
- `condition` without `value`: the connected text. `operator: ai` asks the model (`provider`) the `question` with that text as data; the answer's first word decides: yes, y, true, evet, e, doğru → `true`; no, n, false, hayır, h, yanlış, değil → `false` (formatting ignored). Anything else is asked once more; still unclear, the node fails ("did not answer yes or no"). The branch passes on the tested text, not the answer; the answer is kept in the node folder (`answer.md`).
- `approval` without `show`: the connected text.
- `document.extract` without `file`: the workflow's only file input (with none or several, the check asks for it).

The check reports only what is really missing: an AI step without instruction or model, a condition with `operator: ai` without question or model, an extract that cannot know its file.

Conditions in a workflow (a connection from a condition must name its branch):

```yaml
  - id: gate
    type: condition
    config: {value: "{{nodes.assess.text}}", operator: is_yes}   # the AI step answered "yes ..." or "no ..."
  - id: escalate
    type: ai.cli
    config: {provider: claude, prompt: "Escalate: {{nodes.gate.true}}"}
  - id: reply
    type: ai.cli
    config: {provider: claude, prompt: "Reply: {{nodes.gate.false}}"}
  - id: report
    type: text.merge                      # a join: gets the text of the branch taken
    config: {template: "{{nodes.escalate.text}}{{nodes.reply.text}}"}
connections:
  - {from: assess.text, to: gate}
  - {from: gate.true, to: escalate}
  - {from: gate.false, to: reply}
  - {from: escalate.text, to: report}
  - {from: reply.text, to: report}
```

`is_yes` is true when the first word of the text is yes, y, true, evet, e or doğru (any case, formatting ignored). `equals` ignores spaces at both ends. `regex` uses Python's syntax and is checked when `match` has no placeholder. The operator is not called `yes`: YAML reads a bare `yes` as true.

A loop:

```yaml
  - id: chapters
    type: ai.map
    config:
      source: "{{nodes.extract.text}}"
      split: headings          # the highest heading level found; text before the first heading is a part too
      max_items: 150           # more parts: the node fails with a clear message
      provider: "{{inputs.model}}"
      prompt: "Summarise chapter {{item.index}} of {{item.count}}: {{item.title}} {{item.text}}"
```

`split: paragraphs` makes one part per paragraph; `chunks` groups paragraphs into parts of about `chunk_chars` characters (the translation app's segmenter); `files` makes one part per file of a several-files extract (the title is the file name). In the prompt, `{{item.text}}` and `{{item.title}}` are put between data tags like node outputs. `{{item.*}}` is allowed only in the prompt of an `ai.map` node.

Placeholders: `{{inputs.<id>}}` and `{{nodes.<id>.<output>}}` (and `{{item.*}}` in a loop's prompt). A file input with several files gives its paths, one per line. Rules:

- A node may use the output of another node only when a connection joins them (`from: <node>.<output>`, `to: <node>`). So the drawing is the real data flow.
- Placeholders are replaced in one pass: text that a placeholder inserts (a document, an answer) is never scanned again.
- In an `ai.cli` prompt, each node output is put between `<data source="...">` and `</data>` tags, and the prompt starts with a note that the content of these tags is data, not instructions. A `</data>` inside the text is broken up, so it cannot end the block.

The check rejects: unknown keys at any level, duplicate ids or keys, connections to missing nodes or outputs, cycles, unknown node types, placeholders that do not resolve or have no connection, and anything that looks like a credential (keys such as `api_key`, `token`, `password`, or values that look like API keys). Every problem is listed at once, with its place in the file.

## Security

- The interface listens only on `127.0.0.1`. Requests must be addressed to `127.0.0.1:<port>` or `localhost:<port>`.
- Each start creates a new session key; every API request must carry it (compared in constant time).
- Size limits: 2 MB for a JSON request, 300 MB for an upload, 20 files and 500 MB together for an input with several files. An uploaded file name is reduced to a safe base name.
- An .xlsx file is read with the translation app's guarded XML reader: no entity declarations, no part that unpacks to more than 100 MB.
- Every file access is resolved inside the data folder; a path that leaves it is refused. Word and HTML results are only downloaded, never shown inside the interface.
- Answers carry `X-Content-Type-Options: nosniff`, `Cache-Control: no-store` and a strict Content-Security-Policy (no inline scripts or styles, no frames). No other page may frame Mehteran.

## The boundary with the translation app

The translation app's Python code is not changed by Mehteran. Mehteran changes none of these files: `pipeline/*.py`, `prompts/`, `config.default.toml`, `config.toml`, `scripts/start.sh`, `scripts/start.cmd`, `translate`, `translate.cmd`, `Open Interface.*`, `books/`. The translation app's interface (`pipeline/ui/`) is shared: `app.js` mounts itself on its own page and in Mehteran's (`TranslationUI.mount`), and `style.css` scopes its own rules under `.tr-app`. Mehteran's stylesheet starts with a copy of the base rules of `pipeline/ui/style.css`; the page loads `pipeline/ui/style.css` before it, for the book translation.

Mehteran imports these parts of `pipeline` and only reads or calls them:

| Module | Used for |
|---|---|
| `pipeline.providers.run` | each model call (in `mehteran/worker.py`) |
| `pipeline.core.Project`, `pipeline.core.ROOT` | the provider call's settings object; where `config.toml` is |
| `pipeline.documents.read_blocks` | the text of PDF, Word, EPUB, Markdown and text files |
| `pipeline.documents.segment`, `split_long`, `_parse_xml`, `_zip_read` | the parts of a loop split by length; reading .xlsx safely |
| `pipeline.export.to_docx`, `to_html`, `inlines` | Word and HTML reports (`mehteran/tables.py` adds the tables) |
| `pipeline.providers.QuotaError` | a usage limit reported by a tool (the worker passes it on; the engine waits) |
| `pipeline.system` | process groups, stopping a process tree, the run lock |
| `pipeline.tools` | finding the installed tools; their status, sign-in and model lists (Setup tab) |
| `pipeline.runtime.install_tool` | installing a tool into `.runtime` (`mehter install`, started by the Setup tab) |
| `pipeline.i18n` | the messages of `pipeline.tools` in the same language (Turkish or English; English for the other interface languages) |
| `pipeline.web` | the book translation's API (its `App`, and its request handling for `/api/tr/...`) |
| `pipeline.stages` | which tools the translation workflow uses (Setup) |

For its workflows, Mehteran builds its `Project` object directly from the read settings and does not call `Project.load()`, because that may update `config.toml` and the instructions. The book translation is the exception: it is the translation app itself, so it loads its project as `./translate ui` does (`pipeline.web.App(Project.load(...))`). Mehteran's installer (`mehter install <tool>`) calls `pipeline.runtime` directly, without loading the project, for the same reason as the workflows. The launcher's update step is the translation app's own (`python -m pipeline update`), as in `scripts/start.sh`.

## Not in this slice

Deliberately left out: plugins and a plugin registry, generating workflows with AI, registering any command-line tool from the interface, shell or Python code nodes, scheduling, and sharing between users. PDF reports: the translation app makes its PDF by printing the HTML page in a browser (it has no PDF writer), so Mehteran offers HTML (print it to PDF) and Word.

## Development

- Tests: `python3 -m unittest discover tests` (the Mehteran tests are `tests/test_mehteran_*.py`; they use the fake tool `tests/mehteran_fake_llm.py`, set `MEHTERAN_HOME` to a temporary folder and make no network calls).
- Code: `mehteran/` (stdlib only). YAML: PyYAML 6.0.2, pure Python, vendored in `mehteran/_vendor/yaml/` (MIT license there), used only through the safe loader and safe dumper.
- A new node type: add a `NodeType` to `mehteran/nodes.py` (`register(...)`) with a label, a description and labelled config fields. The schema and the engine pick it up. `GET /api/node-types` describes every type for the editor's forms: `[{type, label, description, outputs: [{name, kind}], outputs_from ("formats" for document.export, else null), joins, branches, takes_retries, default_retries, default_timeout, timeout_per_call, config: [{name, kind (template | localized | int | bool | choice | formats | id), widget ("area", "provider" or ""), required, default, label, help, options: [{value, label}], min, max (int only), item_fields (fields that take {{item.*}})}]}]`; labels and help are `{tr, en}`.
- Interface: `mehteran/ui/` (vanilla JavaScript, no build step): `app.js` (tabs, the book translation, the library, the run window, Runs, Setup), `editor.js` (the visual editor), `canvas.js` (the canvas, also used by the run monitor). The book translation's interface is the translation app's `pipeline/ui/app.js` and `style.css`, served as `/tr/app.js` and `/tr/style.css` (`mehteran/translation.py`). Every element is made with DOM calls and text nodes, never from HTML text.
