# Mehteran: user guide

[Türkçe](mehteran.tr.md) · [Back to the README](../README.md)

Mehteran runs AI workflows on this computer. A workflow is a YAML file: a graph of nodes (read a document, ask a model, merge texts, ask a person, save a report). The models are called through the command-line tools that the translation app already uses (Claude Code, Codex, Antigravity CLI, Gemini CLI). Mehteran keeps no keys and no accounts of its own.

Use the standalone `./translate ui` app for book translation.

## Start

| | macOS / Linux | Windows |
|---|---|---|
| Web interface (double-click) | `Open Mehteran.command` | `Open Mehteran.bat` |
| Web interface | `./mehter ui` | `mehter ui` |
| Command line | `./mehter <command>` | `mehter <command>` |
| With npm (Node.js 18+): installs into `~/Mehteran` (or `MEHTERAN_DIR`) on the first run | `npx mehteran [<command>]` | `npx mehteran [<command>]` |

The interface opens at `http://127.0.0.1:8766/`. When the code changes while the interface runs (an update), the page says so in a banner: close the terminal window of the server and start it again. Starting `mehter ui` a second time on a busy port says the same when the running one is out of date. It runs while the terminal window stays open. The launcher works like the translation app's (`scripts/start.sh`, `scripts/start.cmd`): it uses Python 3.11 or later and installs a private Python (uv) when the computer has none, and before `ui` it brings a git copy of the code folder up to date (`python -m pipeline update`, the translation app's own update step).

The language button (a flag and the language's name) is at the top right: 18 interface languages, see "Languages". On the command line, use `--lang <code>` (`tr`, `en`, `de`, `ar`...) before the command.

## Web interface

The interface has the same design as the translation app's and three tabs: Workflows, Runs, Setup. Addresses of earlier versions (`#templates`, `#workflow/...`, `#runs/new/...`) still open the matching screen. The first screen is Setup while the tools are not ready, otherwise the tab used last; the Mehteran name at the top left goes there too.

- To translate existing books, run `./translate ui` from the project folder. To also show translation inside Mehteran, set `embed_book_translation = true` in `configurations/engine.toml` in your data folder and restart Mehteran.
- **Workflows**: the library and the visual editor. The library has two views. "My workflows" (the first view once you have your own workflows, favorites or runs) shows your own workflows, drafts, favorites, the workflows run last and the book translation when it is starred or has books. "Templates" shows a "Start here" group (about 20 general templates), the book translation and then one group per category. Each card shows what a run needs, for example "1 document · 2 model calls" ("up to" when a choice picks one branch), a search that ignores case and accents (also Turkish ones: "sozlesme" finds "Sözleşme") and a filter per category. Each card has a star (favorite), "Edit" and "Open". "Open", or the card itself, opens the workflow's page (`#workflows/<source>/<id>/<run|steps|runs>`; an `about` address of earlier versions opens `steps`), built like the book translation's: "← Workflows", the workflow's icon and name, and three sections. **Run** is the run form in place (see below). **Runs** lists this workflow's runs. **Instructions** lists the steps in plain words, numbered; an AI step shows its instruction (three lines, then "more"). On your own workflow, "Edit the instruction" changes it in place and saves it. Below them: "Open in the visual editor", and, folded, the drawing and the YAML (your workflows have a YAML editor there). Beside the sections are the favorite star and "⋯": "Open in the visual editor" (a built-in template opens as your own unsaved copy), "Duplicate" (a copy of your own under the first free `<id>-copy` name; it records the template and version it came from in `based_on`, and a later update of the built-in template never changes it), "Download YAML", "Share" and "Delete" (your workflows only). "Import" adds a workflow file; "New workflow" starts an empty one.
- **Runs**: select a record in the searchable history to open its details. The Runs link returns to the list. Each record shows its flow live (the editor's canvas, read-only, each box coloured by its status), a progress line per node, the results (read them formatted, compare them with another run, edit and export them: see "A run's results" below), and the panel of the selected node: its outputs (read them in the reader or download them), the prompt sent to the model, approve or reject, retry. Below the workflow runs, the list shows the last run of each book of the book translation (`GET /api/translation/runs`, read from each book's `work/run.json`); a click opens the books. Everything that runs has a stop button (■) in the list. "Resume" continues a failed, cancelled or interrupted run; "Cancel" stops it; "Run again" opens the Run section of the same workflow.
- **Setup**: the same tool cards as the translation app's Setup tab, on the same code (`pipeline.tools`, `pipeline.runtime`): installed and signed-in status, "Install missing tools" (the tools that the translation workflow and the templates use, and the PDF reader), an install button per tool, the sign-in methods (account, or an API key for Codex and Gemini), "Test", the last usage limit, and a getting-started box. Each card says who uses the tool (Translation, templates). The tools go into the same `<code folder>/.runtime` as the translation app's, so both share one installation. Each AI tool card also shows its billing (subscription, free account, local, or API key (billed); see "AI tools of the workflows" below). Below the cards, the panel "AI tools of the workflows" holds the model order of `auto`, calls at once and "Allow an API key (billed)" per tool. Each card is marked "Required" (used by a template or the translation, and the PDF reader) or "Optional". Below them, "Local tools" (all optional): the Ollama card (status, install after a confirmation that names the version, the source and the folder, the install log with Cancel), its models (installed ones with Delete; recommended ones with size, memory and languages, and a warning when one is too big for this computer; another model by name; one download at a time with progress and Cancel), the Tesseract OCR card (install after a confirmation, languages to add), and the Typst, Pandoc, speech to text (with its models) and qpdf cards (install after a confirmation that names the version, the download size, the source and the folder; the install log with Cancel). Local models are marked "local" wherever a model is chosen. A tool that is ready shows only its name, one status line and "Test"; the rest is under "Details". "AI tools of the workflows", "Run in the background" and "Local tools" are folded under their titles. When Mehteran was updated while it runs, a banner says so, and its "Restart" button starts the server again with the new code and reloads the page (refused while a run or a draft is going on; a server started before this button is restarted by hand once).

A run starts in the Run section of the workflow's page ("Open" on a card, "Run" in the editor, "Run again" on a run: the form opens with that run's values, files excepted). The section is one column: "N steps · View the instructions", the description, the inputs (a file input takes an upload), then "Options", folded: the model inputs, "Model for every step" and "Only models on this computer" (the models are chosen automatically; opened, a model input offers the configured tools with lists of their models and thinking levels), "Also save the results to this folder" and the schedule (not shown for a workflow that needs a file). At the end: "Start the run" with one line of what the run calls ("Calls: 4 · Claude Code"), and the whole estimate under "Details". "Start the run" opens the run on the Runs tab.

**The estimate in the Run section.** Under "Details" below "Start the run", the Run section shows the model calls of the run before it starts (`POST /api/templates/<source>/<id>/estimate {values}`; `mehteran/estimate.py`). It counts from the workflow and the chosen models only; it reads no file and calls no model.

- "Calls": one pass in which every step runs once. An AI step (`ai.cli`) is 1 call. A condition that asks a model (`operator: ai`) is 1 call. A loop (`ai.map`) makes 1 call per part; the number of parts depends on the text, so the window says "1 per part (at most N parts)", where N is the step's `max_items`.
- "With retries at most": the upper bound. Every step uses all its attempts (`retries` + 1), every loop has its largest number of parts, and each `ai` condition asks twice (it asks again when the answer is not a clear yes or no). A wait for a usage limit repeats a call without using an attempt; the bound does not include it.
- One line per model: the tool, the model name, its calls, and the tool's usage now (the same data as the usage hint: what the tool reports, or Mehteran's own count of the last 5 hours). The line changes when you choose another model in the form.
- "Steps after a condition": such a step runs only when its branch is taken, so the run can make fewer calls.
- The tools do not tell how much of a usage limit one call takes. The window therefore shows no percentage per run.

The book translation has its own estimate in its own interface.

**The first-start welcome.** Until you run something, the Workflows tab shows "What would you like to do?" above the library, with one card per choice: work with a document (opens the Run section of `document-explainer`), write or reply (the library with six writing workflows only), analyse data, education and exams, research and review (each the library filtered by that category). Each card names the AI tool that the choice needs with its state from the Setup tab's data (`GET /api/tools`). When the tool is missing, the card has the "Install" button; when it is not signed in, the "Sign in" button (the account sign-in of the Setup tab). Both call the Setup tab's own addresses. An API key and the details stay on the Setup tab; the card links there. `GET /api/welcome` answers `{show, choices: [{id, action, category, templates, providers}]}`. The panel is not shown again after the first workflow run or book translation, or after "Do not show again" (`PUT /api/welcome {"dismissed": true}`). The server keeps that in `<data>/configurations/library.json` (`welcome_closed`: `used` or `dismissed`), not in the browser: the browser's storage belongs to one address and port, and the choice must hold for every browser and port.

### Building a workflow: starters, "Describe it", warnings, "Test this step"

- **New workflow** asks only for the name. The id is made from the name ("Haftalık İş Raporu" gives `haftalik-is-raporu`; letters are folded as the library search does; a number is added while the id is taken). You can write another id under "Advanced settings" in that window.
- **The empty canvas** offers three starters: "Read a document → AI → Save", "A text I type → AI → Save" and "Describe it, I will build it". A starter adds the steps, their connections and the inputs of the run form (the file or the text, the model, the language of the answer) in one step; "Undo" brings the empty canvas back. Nothing is called a problem before the first step.
- **The model of a step** is one list: the run form's model inputs, the automatic choices, and the tools. Under "Details": the tool's model and thinking level (each from a list), the written value (for a name that is not in the lists) and "Test this model".
- **The palette** lists the step types; folded (an existing workflow on a window narrower than 1680 px), it is one "+ Add step" button that opens it.
- **Adding a step** (a click on the palette) connects it from the selected step, or else from the step added last, when that step gives a text; the new box stands to the right of it. A step dropped on the canvas is connected only from the selected step. A step that takes a model gets the run form's model input (made when there is none). All of that is one step of "Undo".
- **Problems and warnings** name the step by its title and the field by its label; a click opens that field. A problem blocks running. A warning does not: the workflow passes the check but probably does not do what you want. The warnings are: a step with no incoming connection whose instruction uses no field of the run form; a step whose result nobody uses; a workflow with no export step and no result. The Run section shows the warnings too. No built-in template has one (`tests/test_mehteran_drafting.py`).
- **Texts in two languages**: a name, description or label has one field, in the interface language. The text of the other language (Turkish or English) is under "Advanced settings"; until you write one there, it is the same text.
- **"Describe it, I will build it" in the library**: the box at the top of the Workflows tab. Write what you want to do (or click one of the short examples) and select "Build the workflow". The model is the automatic choice of your installed tools; the box names it. The work shows in the box as one line with "Stop" (the log under "Details"). The model writes the workflow, with the instruction of every AI step (the same calls as below). A draft that passes the check is saved to your workflows at once, and its page opens on the Run section with **"Here is what I built"**: the steps with their instructions ("Edit the instruction" changes one in place), "Change: …" (one sentence, for example "make it shorter": the model writes the workflow again from its current file and the sentence; a result that passes the check replaces it, otherwise it stays as it was), "Looks good" (closes the card) and "Delete". Nothing runs until you start it. A draft that does not pass the check opens in the editor with its problems.
- **"Describe it, I will build it" on the empty canvas**: write what the workflow should do, choose the model, and that model writes a first draft. This is one model call; when the answer does not pass the check, one more call repairs it with the list of problems. The draft opens in the editor as an unsaved workflow with the note "<model> wrote this. Check the instruction of every step, then run it." It is never saved or run by itself. A draft that still does not pass the check opens on the YAML tab with its problems. The draft always uses the run form's model input, has a `language` input, and is written in the instruction-only style. What you write is sent to the tool of the model you choose, like any step's prompt.
- **"Test this step"** (under the instruction of an AI step, or the question of a condition that asks a model) runs only that step, with your unsaved changes. The texts of the steps before it come from the last run of this workflow in which those steps finished (the panel names that run), or from a sample text that you paste. The panel shows the model, its tool's usage, and then the answer. It is one model call; it counts for the usage page; nothing is saved and the source run does not change.

How it works: `mehteran/drafting.py`. The draft prompt has a summary of the node types made from the registry (`nodes.REGISTRY`, the same data as `GET /api/node-types`), the rules, two example files, and your description between data tags. Both features are jobs of the server (`POST /api/editor/draft`, `POST /api/editor/try`, state and live log with `POST /api/editor/jobs/<id>`, stop with `POST /api/editor/jobs/<id>/cancel`); the model call runs in its own process like a run's step, so "Stop" ends the tool too. `schema.warnings()` makes the warnings.

### The book translation

The book translation is the translation app's own interface, inside Mehteran's page: `pipeline/ui/app.js` (served as `/tr/app.js`, the same file, no copy) draws Books, the translation workflow and the instructions in the Workflows tab (`TranslationUI.mount`), with Mehteran's language, session key and message line. Its links to Setup open Mehteran's Setup tab.

Its requests go to `/api/tr/...` of Mehteran's own server (`mehteran/translation.py`). With `embed_book_translation = true`, startup loads the translation project once, the way `./translate ui` does (`pipeline.web.App(Project.load(...))`), without a second server. A request to `/api/tr/<path>` is answered by the translation app's own request handling (`pipeline.web.make_handler`) as `/api/<path>`: the same routes, checks, streamed uploads (up to 300 MB), downloads and error codes. Mehteran's Host and session-key checks come first; the translation app takes Mehteran's session key. When the project cannot load, the book translation view and the terminal say why; the rest of Mehteran works. `./translate ui` (port 8765) can run at the same time: a book's run is locked per book, across programs.

The translation workflow's diagram ("Translation workflow", in Mehteran and in `./translate ui`) is zoomable: −, + and the zoom level (a click: 100 %), "Fit", Ctrl/⌘ + wheel or a trackpad pinch, and dragging empty space to pan. The chosen zoom is kept in the browser and put back after every redraw; without one the diagram fits the canvas, at 85 % or more. "Full screen" gives the diagram and the panel of the selected step the whole window (Esc ends it; new steps come in through the "+" between the steps there). The steps are drawn larger, with a clear number, the whole model names and a clear selected step; "+ Add step" before the delivery says what the "+" does. On a wide window the panel of the selected step is next to the diagram, otherwise below it. Selecting steps, changing models, dragging, adding, removing and reordering steps and saving work as before.

When the translation app's code changes (`pipeline/*.py`, `pipeline/ui/*`) while `mehter ui` runs, the page shows the same "restart the server" banner as for Mehteran's own code.

### A run's results: read, compare, edit, export

- **Read**: once a run has ended, its first text result is shown formatted in the results box, with "Open in full" (the reader); above it is one download per file the workflow saved ("↓ Word", "↓ Markdown", …). The other Markdown results have a button each (its name opens the reader, "↓" downloads it); a step's outputs open the same reader. A `.md` result is shown formatted: headings, paragraphs, bold, italic, strikethrough, lists, numbered lists, block quotes, code, GFM pipe tables, links and horizontal rules. "Formatted / Plain text" switches the view; the browser remembers the choice. A line break inside a paragraph is kept, as in the exported documents. Each block finds its own direction (`dir="auto"`): an Arabic paragraph reads right to left, an English one left to right, in any interface language; a list, a quote or a table follows the first letter of its text. A link opens only an `http` or `https` address, in a new tab (`rel="noopener noreferrer"`); any other address keeps only its text. Raw HTML in a result stays text. The renderer is `mehteran/ui/markdown.js`: it builds the page with DOM calls and text nodes only (no HTML strings).
- **Compare** (a finished run, "⇄ Compare" in the results box): the run's result next to the same result (the same output id) of another finished run of the same workflow (the same template; a run without a template: the same workflow id). Choose the other run, and the result when there are several. The paragraphs that differ are highlighted ("Highlight the paragraphs that differ"; in the formatted view). On a narrow window the two results are one under the other.
- **Edit** ("✎ Edit" in the reader): the text on the left, its formatted preview on the right (on a narrow window the text alone). "Save" writes the edited version next to the run, as `<run>/edited/<node>.<name>.md`; the original output never changes. The reader then offers "Original" and "Edited" (the edited version first) and the time of the last edit. Unsaved changes are not lost by Esc or "Close" without a question. Only a step's Markdown outputs (`nodes/<node>/<name>.md`) can be edited, at most 1 MB.
- **Export** (an edited version, "Export the edited version"): Markdown, Word, HTML, PDF or EPUB, made by the export step's own code (`nodes.export_document`, the code of `document.export`): Word with Mehteran's converter (Pandoc when it is installed and the text has formulas), PDF with Typst, EPUB with Pandoc. The title is the workflow name; the language is the run's first `language` input (else English). The file is saved as `<run>/edited/<node>.<name>.<format>` and downloaded. A format whose tool is missing says what to install ("PDF export needs Typst. Install Typst on the Setup tab.").

The API (with the session key, like every run route; `<output>` is the original output's path in the run folder, for example `nodes/report/text.md`):

- `GET /api/runs/<run>/edits/<output>` → `{path, exists, text, modified, limit}`.
- `PUT /api/runs/<run>/edits/<output>` `{text}` → `{path, exists, size, modified}`. Over 1 MB of UTF-8 text: 413.
- `POST /api/runs/<run>/edits/<output>` `{format}` → `{path, size}`. Unknown format: 400; nothing saved yet: 404; a missing tool: 400 with what to install.
- A path that is not a step's Markdown output, that leaves the run folder, or an `edited` folder that is a link elsewhere: 404. The edited files are files of the run: they are listed in "All files" and downloaded like the others.

### The run history, batches, saving to a folder, sharing

- **The list** (Runs tab): a search field (it finds the workflow name, the run's name and note, its main input, its id and its status; case and accents are ignored) and one group per workflow; a click on a group's title folds it (the browser remembers it). The book translations have their own group. Each row shows the run's main input: the name of its first file, or else the first 40 characters of its first text or address input. A run that you named shows its name instead.
- **Name and note** ("✎ Rename" on a run's page): a name (at most 120 characters) and a note (at most 2000). The name replaces the workflow name in the list and on the page; the note is shown under the title and as the row's tooltip. `PUT /api/runs/<run>/label {label, note}`; an empty text removes it.
- **Delete** ("Delete" on the page of a finished run): the confirmation names the size of the run's folder. The run's rows and its folder `executions/<run>` are deleted; the usage records of its model calls stay. A run that is queued, running or waiting for an approval, or whose lock another process holds (`executions/<run>/.lock`), is not deleted: stop it first. Only paths inside the data folder are removed; a link inside the run folder is removed as a link, never followed. `DELETE /api/runs/<run>` (`{"dry_run": true}`: only `{size, deletable}`).
- **Delete runs older than…** (under the search field): 30, 90 or 365 days. The window first names how many finished runs and how many bytes; working runs are kept. `POST /api/runs/cleanup {days, dry_run}`.
- **A finished run's page**: the diagram, the steps and the live log fold into one line ("4/4 steps · 1 min · show the flow"), so the results have the room. A run that did not succeed stays open (its steps can be retried there).
- **Once per file** (the Run section, under a single-file input: "Run once for each file"): choose up to 50 files; each becomes one queued run with the same other inputs. The list shows them as one batch row with its progress ("2/5 done"); open it to see the runs. At most 2 runs of a batch work at a time (there is no limit per provider yet); the others wait as "queued". The estimate of the window shows the calls × the number of files. `POST /api/runs` with `"batch": {"input": "<file input>", "files": [<upload ids>]}` answers `{batch, ids, id}`. The queued runs of a batch are started again when the server starts.
- **Also save the results to this folder** (the Run section, also for a batch): type the full path of a folder. The server checks it: an absolute path to an existing, writable folder; not a system folder (`/`, `/etc`, `/usr`, `/System`, `/Library`, `~/Library`, `C:\Windows`, `Program Files`, ...), not Mehteran's own folder and not its data folder. The first time a folder is used, the window asks to confirm it; after that, the folder is remembered for this workflow (`<data>/configurations/output_folders.json`). The results are copied only after the run succeeded: the workflow's outputs (or, without outputs, the files its steps saved). Nothing is overwritten: a name that exists gets " (2)", " (3)", ... A run of a batch puts the name of its file first ("invoice-3 - report.docx"). The run's page says where the files went, or why they could not be saved. `GET /api/output-folders/<source>/<id>`, `POST /api/output-folders/check {path}` → `{path, problem, confirmed}`; `POST /api/runs` takes `output_dir` and `output_confirmed`.
- **Share** ("⋯" on a workflow's page, "Share"): downloads `<id>.mehteran.yaml`: the workflow file with `author` (an optional name you type) and, for a built-in template, `based_on: builtin:<id>@<version>`. `GET /api/templates/<source>/<id>/share?author=<name>`.
- **Import with a preview**: "Import" (paste the YAML or choose a file), or a `.yaml` file dropped on the library, first opens a preview: the description, the author, the diagram, the inputs, what the workflow needs here (each model with its tool and whether it is installed and signed in, the local tools such as Typst or Tesseract, and whether it reads web pages), every instruction it sends to a model, and its problems. "Add to my workflows" imports it; when its id is taken, it asks for a new one. The check refuses credentials as for every import. `POST /api/templates/preview {yaml}`, `POST /api/templates/import {yaml, id}`.
- **The user guide** (the footer's "Guide") is shown formatted, like a Markdown result.

## Languages

One list holds every language: `mehteran/languages.json` (the language registry). An entry has the code, the language's own name, its English name, the country code of its flag and its direction: `{"code": "ar", "native": "العربية", "english": "Arabic", "flag": "sa", "dir": "rtl", "ui": true}`. The Mehteran page, the book translation's interface and the workflows use this list (`mehteran/languages.py`, `GET /api/languages`). It contains every language of the translation app's default list (`config.default.toml`, `[languages]`); a test checks that.

- **Interface languages** (`"ui": true`): Türkçe, English, العربية, Deutsch, Français, Español, Português, Italiano, Русский, فارسی, اردو, Bahasa Indonesia, Bahasa Melayu, Azərbaycanca, Bosanski, Shqip, 简体中文, 日本語. Choose one with the language button at the top right: a list with flags and a search field (type a name in any language, or the code). The keyboard works: Enter, Space or ↓ opens the list, ↑ ↓ move, Enter chooses, Esc closes. The choice is kept in the browser. Arabic, Persian and Urdu turn the page right to left (`<html dir="rtl">`); the workflow drawing, code and logs stay left to right.
- **Complete and partial languages**: Turkish and English have every text. Another language may have only some of the texts; a text that it lacks is shown in English (the page and the server messages both). The translation app's own server messages (`pipeline/i18n.py`) are Turkish or English: every other interface language gets them in English.
- **Flags**: a flag is a country's, a language is not: the flag only helps to find the row, the language's own name is always written beside it. The flags are SVG files of this program (`mehteran/ui/flags/<country>.svg`, from flag-icons 7.2.3, MIT; the license is in that folder), because emoji flags do not show on Windows. Nothing is loaded from the internet.
- **Output language of a workflow**: an input of type `language` offers every language of the registry in the same flag list. A `choice` input whose options are all language codes (and whose id contains `lang`) is shown as the flag list too, with only its options. The Run section starts at the interface language when the workflow offers it; else at the workflow's default.

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

**Ollama** runs models on this computer; nothing is sent anywhere. Mehteran's adapter `ollama` calls it (the translation app's `config.toml` is not changed). A step uses it as `ollama/<model>`, for example `ollama/gemma3:4b`; the run form offers the installed models. Mehteran calls Ollama's HTTP API on `127.0.0.1` (port 11434) with its own system prompt and the same data tags as for any other model, in the same separate process, so cancel and timeout work the same.

- An Ollama that already runs is used as it is. Else the system's `ollama` (PATH, the macOS app, the Windows install), else the one Mehteran installed. Mehteran starts `ollama serve` on 127.0.0.1 when a run or a download needs it and stops it when Mehteran ends, only if Mehteran started it (its log: `<data>/jobs/ollama-serve.log`).
- Install: Ollama 0.40.16, the official archive of the GitHub release (`ollama-darwin.tgz`, `ollama-linux-amd64.tar.zst` / `-arm64`, `ollama-windows-amd64.zip` / `-arm64`), checked against the SHA-256 sums written in `mehteran/ollama.py` (from the release's `sha256sum.txt`, which matches GitHub's own digests). No install script is run. On Linux, unpacking needs Python 3.14 or the `zstd` program.
- Models: the installed ones (name, size, date), a list of recommended ones (size on disk, memory needed, languages, a note; the tags were checked in the Ollama registry), download with progress and cancel (one at a time), delete. Before a download Mehteran warns when the computer has too little memory, and refuses when the disk is too full (unless forced). Models stay in Ollama's own folder (`~/.ollama/models`, or `OLLAMA_MODELS`).
- Settings: `<data>/configurations/providers.toml` may set `[providers.ollama]` `model` (the default model) and `options` (`num_ctx`, `temperature`, `top_p`, `seed`). Mehteran sizes the context (`num_ctx`) of each call itself: the prompt plus room for the reply, at least 8192 tokens, at most the model's maximum (from `/api/show`) and what the memory allows (1024 tokens per GB, 4096 to 131072). A `num_ctx` in `options` wins. When the prompt still fills the whole context (`prompt_eval_count` is not below `num_ctx`), the step fails with "the document is too long for this model" instead of answering from a cut text: use a loop step or a model with a larger context.

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
./mehter install-local browser                    install the browser of agent steps (Playwright MCP)
./mehter browser-signin [url]                     open Chrome with the profile of agent steps, to sign in
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

## AI tools of the workflows (providers)

Mehteran calls the AI tools through adapters of its own, one module per tool in `mehteran/providers/`: `claude` (Claude Code), `codex` (Codex CLI; the old name `chatgpt` still works), `antigravity` (Antigravity CLI), `gemini` (Gemini CLI) and `ollama` (local models). Each adapter knows the tool's command and Mehteran's own safe flags, the neutral system prompt, how the answer and a usage limit come out, where the text goes, the billing kind, the context size and the default number of calls at once. The book translation keeps its own commands in `config.toml`; they are not changed.

| Tool | Billing shown | Text goes to | Flags Mehteran adds |
|---|---|---|---|
| Claude Code | subscription (API key when `claude auth status` names an `apiKeySource` that Mehteran passes) | Anthropic | `-p --safe-mode --tools "" --no-session-persistence --strict-mcp-config --output-format stream-json --verbose --system-prompt …`; never `--bare` (it would need an API key) |
| Codex CLI | subscription (API key when `codex login status` says so) | OpenAI | `exec --sandbox read-only --ephemeral --ignore-user-config --skip-git-repo-check --color never -o <file>` |
| Antigravity CLI | free account | Google | `--input-format stream-json --output-format stream-json --disable-slash-commands` |
| Gemini CLI | API key (billed): personal Google accounts lost the free CLI sign-in; the free Google path is Antigravity CLI | Google | `-p … -o json --skip-trust` |
| Ollama | local (a `…:cloud` / `…-cloud` model: Ollama Cloud, not local) | this computer | Ollama's HTTP API on 127.0.0.1 |
| Local server (`openai-local`) | local | this computer | `POST <url>/chat/completions` with `stream: true` (LM Studio, llama.cpp's llama-server, vLLM) |

**Local server.** Setup → "Local server (OpenAI-compatible)": the server's address (only `http(s)://127.0.0.1|localhost|[::1]:<port>/…`), a model (or the server's first one from `GET <url>/models`), "Save" and "Test". Mehteran calls it with the standard library (`urllib`), with no proxy and without following a redirect, so the text cannot leave the computer through it; the answer streams into the live log. It counts as local (`auto:local`, privacy: local). A step uses it as `openai-local/<model>`; a model name with `/` cannot be written. Settings: `[providers.openai-local] url = "http://127.0.0.1:1234/v1"`, `model = "…"`.

The Claude flags were checked against `claude --help` (2.1.316). The Codex flags come from the Codex CLI reference (Codex was not installed where this was written). Antigravity CLI has `--sandbox` and `--mode plan`; Mehteran does not add them: checking that they leave a plain answer unchanged needs a real model call, and plan mode may answer with a plan. Every call runs in an empty temporary folder and asks for no tools.

**Billing guard.** The worker's environment has none of `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, `CODEX_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, `GOOGLE_API_KEY`, so a tool cannot bill an API account by accident. "Allow an API key (billed)" for a tool (Setup) gives that tool back its own variables. The choice is frozen with each run. A key that a tool stores itself (a Codex API key login, `~/.gemini/.env`) is not an environment variable: the Setup tab then shows "API key (billed)".

**`auto`.** A model may be `auto`, `auto:fast`, `auto:strong` or `auto:local` (the templates' default is `auto`). When a run starts, Mehteran takes the user's model order (Setup: "Model order", with ↑ ↓ and ✕; without one, the installed and signed-in tools in the order Claude Code, Codex, Antigravity, Ollama) and keeps only the tools that are installed, signed in and not billed by an API key. `auto` takes the first one; `auto:fast` its fast model (Claude: `haiku`) or a low thinking level; `auto:strong` its strong model (Claude: `opus`) or a high level; `auto:local` only a model on this computer. A provider with a usage limit that has not reset goes to the end. The choice and the other candidates are frozen into the run (`provider_cfg.auto`). The run form shows "Automatic: <model> · <usage>" and lets you choose a tool instead; a template whose default tool cannot run here starts on `auto`.

**Usage limits across runs.** Before each call, a provider whose last usage limit has not reset (the `calls` table of all runs, and the translation app's `.jobs/quota.json`) is treated as blocked without a call. An `auto` step then moves to the next model of its candidates; when every one is blocked, it waits until the earliest reset. A step with a fixed model waits as before. A step does not count its own limit this way (it waits for it itself; a resume tries again).

**Calls at once.** Each tool has a limit of calls at once over all runs of one Mehteran program (defaults: Claude Code and Codex 2, Antigravity 1, Ollama 1; Setup: "At once"). It comes on top of the 4 calls per run.

**Privacy: local.** A workflow with `privacy: local` (a top-level key), or a run started with "Only models on this computer", accepts only local models: `auto` becomes `auto:local`, and any other model is refused before the run starts. The run form's estimate lists each step with where its text goes ("Sent to: Anthropic", "Stays on this computer (Ollama)") and marks the steps that privacy: local would refuse.

**Model for every step.** The Run section's "Model for every step" runs every model step of the workflow with one tool (or with "Automatic": the model order), whatever the workflow and its model fields set; the step fallbacks use it too, and the workflow's own model fields are hidden. It is for a person who has only one of the AI tools: a workflow written for Claude runs with Codex alone. The estimate shows the chosen model. Privacy: local still applies. A run that names a tool that is not there says so and points to this choice. API: `every_step` in `POST /api/runs` and in the estimate (`POST /api/templates/<source>/<id>/estimate`); command line: `mehter run <workflow> --every-step codex`.

**Settings file** `<data>/configurations/providers.toml` (written by the Setup tab; no secrets):

```
order = ["claude", "codex/gpt-5.5@high", "ollama/qwen3:8b"]
[providers.claude]
api_key = false
concurrency = 2
[providers.ollama]
model = "gemma3:4b"
options = {num_ctx = 8192}
```

API: `GET /api/providers` → `{providers: [{name, label, vendor, local, adapter, installed, signed_in, billing, default_billing, api_key_allowed, key_dropped, problem, concurrency, in_use, blocked_until, models}], order, order_is_default, auto: {auto|auto:fast|auto:strong|auto:local: {name, vendor, local}|null}}`; `PUT /api/providers {order?: [model], providers?: {name: {api_key?, concurrency?}}}`. `POST /api/runs` and the estimate take `privacy: "local"`. Claude Code's live output: its stream-json events are shown as text in the step's live log, and each call's `rate_limit_event` updates `usage.json`.

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

- Codex: its session logs (`~/.codex/sessions/**/rollout-*.jsonl`, `$CODEX_HOME`) hold its rate limits; the newest entry: `{source: "codex-session-log", observed_at, plan, limit_reached, windows: [{name: "primary"|"secondary", used_percent, window_minutes, resets_at, expired}]}` (primary: the 5-hour window, secondary: the weekly one; `expired`: the window has reset since). Mehteran's own Codex calls are `--ephemeral` and write no session log, so the value comes from the last interactive Codex use. No credentials file is read.
- Claude Code: reports its limits only in its stream-json output (`rate_limit_event`). Mehteran's Claude adapter uses stream-json, so each workflow call updates the value. `POST /api/usage/probe/<provider>` (a Claude provider only) asks once, with the smallest model and a one-word prompt, and keeps the answer: `{source: "claude-rate-limit-event", observed_at, status, limit_type, resets_at, windows: [{name: "five_hour"|"seven_day", utilization (0–1), resets_at, status}]}`.
- Gemini CLI, Antigravity CLI, Ollama: no limits reported (`null`).

**Switching the model of a step** (`POST /api/runs/<run>/nodes/<node>/switch` `{provider: "gemini/<model>"}` → `{ok}`): for an AI step that waits for a usage limit, failed, was cancelled or was interrupted. The provider must be configured. The event log gets "Model switched: old → new" (key `event_switched`). A waiting step stops waiting at once and runs again with the new model; the others are retried. A loop keeps the parts it already has (a part's answer is keyed by its prompt, not by the model). Not switching means waiting, as before. The run keeps the new model (`providers` of the run).

A step may name a fallback model (off unless written): `fallback_provider: gemini/gemini-2.5-pro` (or a `provider` input, `"{{inputs.backup}}"`) next to `retries`. When the step's model reports a usage limit, the step switches to it at once instead of waiting (event key `event_switched_auto`); when the fallback reports a limit too, the step waits. Only AI steps (and conditions that ask a model) take it; the check refuses others and names that are not provider names.

**Live logs** (`GET /api/runs/<run>/log?node=<node>&offset=<bytes>` → `{text, offset, size, done, status}`): each node writes `nodes/<node>/log.txt` while it works: attempts, each model call (and its answer), a "still working" line every 30 seconds, usage-limit waits, model switches, loop parts. Read it from `offset` 0, then from the returned `offset`; `done` is true when the node has ended and everything was read. At most 64 KB per answer, 2 MB per log; obvious secrets (`sk-…`, `Bearer …`, Google and GitHub keys) are masked. A log is written in the language of the run.

What streams: Ollama's answer streams into the log as the model writes it. The command-line tools (Claude Code, Codex, Gemini CLI, Antigravity) are called through Mehteran's adapters (`mehteran/providers/base.py` `run`); its `on_output` callback gives each line of the tool's stdout as it arrives, and the worker writes it to the log (`mehteran/toolstream.py`). The answer that the call returns is the same as without it. A provider that the user added to `config.toml` runs through `pipeline.providers.run` and shows its answer at the end. A tool shows live only what it prints on stdout while it works:

- Antigravity CLI (`--output-format stream-json`): its JSON events are turned into text: the answer's text as it is written, and an error line from a failed result.
- Claude Code (`--output-format stream-json --verbose`, Mehteran's adapter): the assistant's text as each message arrives, and each tool use as a short line (`· tool: Read`), never the raw JSON. Its `rate_limit_event` is kept for the usage page.
- Codex (`codex exec ... -o <file>`): prints its final message on stdout at the end; its progress goes to stderr, which is not shown live. The answer appears at the end.
- Gemini CLI (`-o json`): prints one JSON document at the end; nothing is shown live, and the answer appears at the end.

Meanwhile the log shows the call and the heartbeat lines. Streamed text is written in whole lines (a long line up to its last word but one), so that secrets are masked whole; the parts of a loop write whole lines with their label (`part 3: `). When the streamed text already ends with the answer, the answer is not written a second time.

**Activity** (`GET /api/activity` → `{runs: [...], translation: [...], time}`), cheap enough for a header indicator: each running, queued or waiting run `{id, workflow_name, status, started, elapsed, done, total, waiting_quota, nodes: [{id, status, started, elapsed, attempts, waiting_reason, progress}]}` (only the nodes that work or wait), and each book the translation app is translating now `{book, state ("running"|"waiting_quota"), stage, started, elapsed, quota}` (its `run.json`, read only).

**In the interface** (`mehteran/ui/live.js`):

- Setup: each AI tool's card has a "Usage" part: Mehteran's own counts (today, last 5 hours, last 7 days: calls, failures, usage limits, time), the last usage limit with a countdown to its reset, and the limits the tool reports itself ("unknown" when it reports none). A Claude Code card has "Check usage", which makes one tiny model call (`POST /api/usage/probe/<provider>`).
- The run form and the model choice of a step show a short usage hint next to the tool ("5 hours: 54 %"), in a warning colour near a limit.
- The run page: an overall progress bar, elapsed timers, attempts and the waiting reason of each step, and the live log of the selected step (else the step that works now): monospace, it follows the end, pauses when you scroll up ("Paused · jump to the end"), "Copy". A step that waits for a usage limit, failed, was cancelled or was interrupted offers "Keep waiting" (the default) and "Continue with another model" (every configured model, with its usage hint); the step's panel lists its model switches.
- The editor: "Fallback model" in the advanced settings of a step that takes a model (empty: off).
- The header shows what runs now ("2 running", in a warning colour while something waits for a usage limit); a click lists the runs and the books being translated, each a link with a stop button (■). It asks every 4 seconds while something runs, every 20 seconds otherwise, and less often while the window is hidden.
- The library: a star on each card and beside the sections of the workflow's page marks a favorite (kept in `<data>/configurations/library.json`; `PUT /api/templates/<source>/<id>/favorite {on}`; the list's `favorite` flag). "Favorites" comes right under the book translation, with a "★ Favorites" filter; "Recently used" lists the workflows of the last runs, each with "Open", which goes to the workflow's page. The run form remembers the last values of each workflow in this browser (models, choices, texts; never files or anything named like a key or password): "Same as last time" fills them in. "/" puts the cursor in the search.

## Command line

Run the social video workflow with the command below. The web interface, CLI and scheduler use the same workflow engine. The CLI prints the run ID at the script approval, the audio preview path at the voice approval, and the ZIP path at completion.

```sh
./mehter run builtin:topic-video-series --input "topics=Zeytin ağacı nasıl büyür?" --input language=tr
./mehter approve RUN_ID review
./mehter approve RUN_ID listen
```


```
./mehter templates                               list the templates
./mehter validate my-flow.yaml                   check a workflow file; lists every problem
./mehter run document-comparison \
    --input documents=old.docx --input documents=new.docx \
    --input model=claude/opus@high --input language=tr
./mehter run document-comparison \
    --input mode=set --input documents=a.pdf --input documents=b.docx --input documents=c.md
./mehter runs                                    the run history
./mehter resume <run> [--node <id>]              continue a run, or retry one failed node
./mehter cancel <run>                            stop a run
./mehter approve <run> <node> [--comment ...]    approve a waiting approval node (reject: the same)
./mehter schedules                               the scheduled runs
./mehter background on|off|status                start Mehteran in the background at sign-in
```

`run` takes a template id (`builtin:<id>`, `user:<id>` or a bare id) or a path to a `.yaml` file. An input with `multiple: true` takes `--input <id>=<file>` once per file. `--every-step <model>` runs every step with one model (`codex`, `claude/opus@high`, `auto`). It shows the status of each node until the run ends. Ctrl+C cancels the run. Exit code: 0 finished, 3 waiting for an approval, 1 otherwise.

## Built-in templates

77 built-in templates in 10 categories. Each one is described in the Templates view (what it does, its inputs, its flow). A star after a name marks the templates of the "Start here" group (field `tier: core`). The exam templates (SAT, AP, LGS, YKS) are in `exams`; `education` is general study and teaching.

Some older templates were merged into others. The old ids still work (runs, favorites and `mehter run` accept them): `multi-document-comparison` → `document-comparison`; `chapter-summaries` → `document-summary`; `multi-length-summary` → `document-summary`; `terms-plain-language` → `plain-language-rewrite`; `proofreading-change-list` → `writing-polish`; `abstract-title-improvement` → `writing-polish`; `sat-math-practice-set` → `exam-practice-set`; `sat-reading-writing-practice` → `exam-practice-set`; `lgs-yks-practice` → `exam-practice-set`; `ap-mcq-from-notes` → `ap-question-generator`; `ap-frq-generator` → `ap-question-generator`; `policy-gap-analysis` → `regulatory-compliance-checklist`; `client-follow-up-email` → `email-reply-draft`.

| Category | Templates |
|---|---|
| **Business** (`business`) | `business-plan-critique` (Business plan and pitch critique), `customer-feedback-insights` (Insights from customer reviews*), `expense-anomaly-review` (Invoice and expense anomaly notes), `financial-period-comparison` (Two-period financial comparison), `financial-report-analysis` (Financial report analysis), `job-posting-writer` (Job posting writer), `proposal-from-brief` (Proposal from a client brief*), `receipts-to-expense-table` (Expense table from receipts and invoices*), `request-triage` (Request and complaint triage), `review-reply-drafts` (Replies to customer reviews), `rfp-compliance-matrix` (RFP compliance matrix), `weekly-report-from-notes` (Weekly report from notes) |
| **Data** (`data`) | `data-analysis-plan` (Data analysis plan and interpretation), `dataset-documentation-review` (Dataset documentation review), `spreadsheet-analysis` (Spreadsheet (CSV / Excel) analysis*), `sql-query-writer` (SQL query from a question), `survey-response-themes` (Survey free-text themes) |
| **Documents** (`documents`) | `ask-your-documents` (Ask your documents*), `document-comparison` (Document comparison*), `document-consistency-check` (Document consistency check), `document-explainer` (Explain a document in plain language*), `document-summary` (Document summary*), `meeting-minutes-actions` (Meeting minutes and action items*), `pdf-to-slide-outline` (Slide outline from a long document*), `recording-to-notes` (Notes from a meeting or lecture recording*), `requirements-review` (Requirements document review) |
| **Education** (`education`) | `answer-key-verification` (Answer key verification), `differentiated-worksheet` (Differentiated worksheet), `essay-rubric-grader` (Essay grading with your rubric), `exam-from-lecture-notes` (A/B exam from lecture notes), `flashcards` (Flashcards (Anki)*), `lesson-plan` (Lesson plan), `mistake-explainer` (Missed-question explainer), `parent-letter` (Letter to parents), `question-variants-from-references` (New question variants from reference questions), `report-card-comments` (Report card comments), `scenario-generator` (Scenario, case and word-problem generator), `study-guide-questions` (Study notes and exam questions), `weekly-study-plan` (Weekly study plan) |
| **Exams** (`exams`) | `ap-frq-grader` (AP FRQ grading (double scoring)), `ap-question-generator` (AP question generator (multiple choice and free response)), `exam-practice-set` (Exam practice set (SAT, LGS, YKS)), `sat-math-solver` (SAT Math: worked solution with a double check), `sat-practice-scoring` (SAT practice test: scoring and study plan) |
| **Legal** (`legal`) | `contract-risk-review` (Contract risk review*), `nda-review` (NDA review), `regulatory-compliance-checklist` (Regulatory compliance checklist) |
| **Research** (`research`) | `academic-paper-review` (Academic paper review), `grant-proposal-review` (Grant proposal review), `literature-synthesis` (Literature synthesis), `research-question-critique` (Research question and hypothesis critique), `reviewer-response-letter` (Response letter to reviewers), `thesis-chapter-feedback` (Thesis chapter feedback) |
| **Software** (`developers`) | `bug-report-triage` (Bug report triage), `changelog-from-commits` (Changelog from commits), `code-review` (Code review*), `log-or-stacktrace-explainer` (Log and stack trace explainer), `pr-description` (Pull request description), `readme-from-code` (README from code), `test-cases-from-code` (Test cases from code) |
| **Web research** (`web`) | `ai-news-bulletin` (AI news bulletin), `economy-news-bulletin` (Economy news bulletin), `listing-search` (Find home or car listings), `research-to-x-post` (Research and prepare an X post), `stay-search` (Find a place to stay (hotel)) |
| **Writing** (`writing`) | `cv-and-cover-letter` (Tailored CV and cover letter*), `cv-job-fit` (CV and job posting fit), `document-translation-glossary` (Document translation with glossary and consistency check), `email-reply-draft` (Email reply draft*), `official-letter-writer` (Petition and formal letter writer*), `plain-language-rewrite` (Plain-language writing*), `product-description-seo` (Product descriptions and SEO text), `social-media-posts` (Social media posts from an article or report*), `style-guide-review` (Editorial review against a style guide), `tone-audience-adaptation` (Tone and audience adaptation), `translation-quality-review` (Translation quality review), `writing-polish` (Writing polish*) |

## Browser agent steps

A **Browser agent** step (`ai.agent`) lets a model open sites in Google Chrome, read them and, after an approval, fill in forms. It is the only kind of step that gets a tool; the other model steps only receive text and return text.

Setup, once:

1. Install Node.js (nodejs.org) and Google Chrome.
2. Setup tab → "Browser for agent steps" → Install. This installs Playwright MCP 0.0.84 (Microsoft) with `npm ci --ignore-scripts` from the lock file `mehteran/browser_mcp/package-lock.json` (exact versions and sha512 sums) into `<code folder>/.runtime/browser-mcp`. No browser is downloaded: it uses your Chrome. Command line: `mehter install-local browser`.
3. To use sites that need a sign-in (for example X), choose "Open the browser to sign in" (command line: `mehter browser-signin https://x.com/login`). Chrome opens with Mehteran's own profile, `<data>/browser/profile`. Sign in, then close the window: Chrome cannot use the profile twice at the same time. Agent steps use this profile and its sign-ins; your own Chrome profile is never used.

How a step runs:

- Only with Claude Code (signed in on the Setup tab). An `auto` model chooses Claude Code; another model, or "Model for every step" with another tool, refuses the run before it starts. Codex and the other tools cannot run agent steps yet.
- Claude Code starts with `--restricted --strict-mcp-config --mcp-config <the browser> --tools "" --permission-mode dontAsk --allowedTools <the step's tools>`: no shell, no file tools, no other MCP server, and any tool that is not listed is refused without a question. (Not `--safe-mode`: it drops the browser server too.)
- `mode: read` (the default) gets the tools that look and move around: navigate, back, read the page (snapshot, find), click, hover, tabs, wait, screenshot, close, dialogs. It cannot type. The prompt also forbids signing in, posting, liking, following, buying and sending forms.
- `mode: act` also gets typing, filling in forms, pressing keys and choosing options. A workflow with such a step is valid only when an `approval` step comes before it.
- No step gets running JavaScript in the page (`browser_evaluate`, `browser_run_code_unsafe`), uploading or dropping files.
- `sites`: the host names the step may open, one per line (subdomains included). Playwright's own origin list is not a security boundary, so Mehteran checks every address the step navigates to and every page a tool ends on; another site stops the step at once ("The step was stopped"). The check comes from the tool's own output, so the page that broke the rule may already have started to load.
- Every browser action (`» browser_navigate https://…`) is written to the step's live log, and the prompt tells the model that text on pages is data, not instructions.
- `headless: true` runs without a window; by default you see the window.
- The step's prompt and the browser's settings are kept in the run folder (`nodes/<id>/prompt.txt`, `browser-mcp.json`).

**Share on X** (`share.x`): gives a link that opens X's post window with the text filled in (`https://x.com/intent/post?text=…`). The run page shows the text and an "Open in X" button; you read it and press "Post" yourself. Mehteran never posts by itself. We do not automate posting with the browser, because, as far as we know, X's automation rules forbid scripting its site (not checked against the current text of the rules).

The template `research-to-x-post` puts these together: a read-only agent researches the topic on the sites you list, a model writes the post, a second model checks it against the research notes, you approve it (a comment changes the post), and X opens with the text.

Two more templates use a read-only agent to search sites and compare what they find. **`listing-search`** (Find home or car listings): you give the kind (home or car), buy or rent, the location, the features you want and a budget; the agent searches the listing sites you list (by default sahibinden.com, hepsiemlak.com, emlakjet.com, arabam.com) with their own filters, a model writes a comparison table (each wanted feature ✓, ✗ or ?, the best match first, links to the listings), and a second model checks every listing against the agent's notes. **`stay-search`** (Find a place to stay): you give the place, the check-in and check-out dates, the guests, a budget and your wishes; the agent searches the hotel sites you list (by default booking.com, hotels.com, etstur.com, trivago.com.tr) for those dates and guests, and the comparison gives the total and nightly prices, rating, breakfast and cancellation terms. Both run their browser without a window. Neither books, signs in or contacts anyone; prices are those of the moment of the search. A site that asks for a sign-in, shows a captcha or blocks the agent is named in the report, so that you can look there by hand. A workflow with a browser agent cannot keep everything on this computer: its "Only models on this computer" box is off and says why, and "Model for every step" with another tool leaves the agent on Claude Code.

## Scheduled runs and running in the background

**Schedule a run.** In a workflow's run window, fill in the inputs and choose "Run on a schedule instead of now". Then choose the days and a time (local time), or "Every few hours" (1 to 168), and "Save the schedule". The inputs, the model choices, "only models on this computer" and "save the results to a folder" are saved with the schedule.

- The schedules are in the Runs tab, in the "Scheduled" group: the rule, the next time and the status of the last run. Each one has Pause/Resume, "Run now" and Delete. A click on a schedule opens its last run.
- Each run uses the workflow as it is at that moment. A changed template applies from the next run on. When a run cannot start (for example, a deleted template or a missing input), the schedule shows why.
- A workflow that needs a file cannot be scheduled, because a schedule keeps only text values.
- Times that passed while Mehteran was closed start one run when it opens again, not one per missed time.
- While the last run of a schedule is still queued or running, its time is skipped. A run that waits for an approval does not hold up the next one.
- Approval steps wait for you. A desktop notification tells you when a scheduled run waits for an approval, is ready, or did not finish (macOS: Notification Center; Linux: `notify-send`; Windows: no notification yet).
- The schedules are kept in `<data>/configurations/schedules.json`. Command line: `mehter schedules`.

**Run in the background.** Runs start only while Mehteran is open. Setup tab → "Run in the background" → Turn on (command line: `mehter background on`). Mehteran then starts when you sign in to the computer, with no window and without opening the browser. Open it at `http://127.0.0.1:8766/` or with `./mehter ui` whenever you like.

- macOS: a LaunchAgent, `~/Library/LaunchAgents/com.mehteran.ui.plist`. Linux: a systemd user service, `~/.config/systemd/user/mehteran.service`. Windows: a script in the Startup folder (not tested on Windows).
- The service runs `python -m mehteran ui --no-browser` with the Python of this Mehteran. It gets the `PATH` of the moment you turned it on, so that it finds the AI tools. No other variable is copied: API keys never go into the service file. When you install a tool in a new folder later, turn the background off and on again.
- When Mehteran is already open in a terminal, the background server waits and takes over within about 30 seconds after you close it.
- Its output goes to `<data>/logs/background.log`.
- Turn off stops the background server and removes the service file. When the page you use is served by it, the page stops working; runs that are going on stop and can be resumed later.
- After a code update the background server keeps the old code until it starts again (sign out and in, or turn it off and on).

## Where the data is

Mehteran keeps its data outside the code folder:

| System | Folder |
|---|---|
| macOS | `~/Library/Application Support/Mehteran` |
| Windows | `%LOCALAPPDATA%\Mehteran` |
| Linux | `$XDG_DATA_HOME/mehteran`, else `~/.local/share/mehteran` |

The environment variable `MEHTERAN_HOME` replaces this folder. Subfolders:

- `templates/`: your templates (one `<id>.yaml` each).
- `executions/<run>/`: one folder per run: `workflow.yaml` (the frozen copy), `inputs/` (the uploaded files; `inputs/<id>/<n>/` for each file of an input with several), `nodes/<node>/` (the outputs of each node, the prompt of each model call; a loop keeps each part's prompt and answer in `nodes/<node>/parts/`), `edited/` (the edited versions of results and their exports; only when the user edits a result).
- `databases/mehteran.sqlite3`: the state of every run and node (SQLite, WAL mode).
- `configurations/`: what the Setup tab keeps: `providers.toml` (the model order, calls at once, "API key (billed)", the Ollama model and options; no secrets), `models.json` (the model lists read from the tools), `quota.json` (the last usage limit that a model test met) and `usage.json` (what Claude Code last reported about its limits).
- `jobs/`: the logs of the installs started from the Setup tab.
- `workflows/`: reserved for later versions; empty now.

The workflows use Mehteran's own adapters (`mehteran/providers/`, see "AI tools of the workflows"). The translation app's `config.toml` is only read: its `[general]` timeouts and limits, and any `[providers.*]` section that the user added under another name. Its `claude`, `chatgpt`, `antigravity` and `gemini` sections belong to the book translation only. Sign-ins are kept by the tools themselves, in their own folders (as in the translation app). `MEHTERAN_CONFIG` can name another TOML file with `[providers.*]` sections; there, a provider wins over the adapter of the same name (the tests use it for a fake tool).

## How a run works

- A node starts as soon as all nodes it is connected from have finished. Nodes that do not depend on each other run at the same time (at most 4 per run).
- Each node has a number of retries and a timeout per attempt. A timeout or a cancel stops the model call together with the tool it started.
- A model gets the prompt on stdin, in an empty temporary folder, through Mehteran's adapter of the tool (`mehteran/providers/base.py`), without the API keys that would bill an account. A provider that the user added to `config.toml` runs through the translation app's call (`pipeline.providers.run`). Mehteran makes one attempt per call; the engine counts the retries.
- Usage limits: when a tool reports a usage or rate limit (the adapter's own report, such as Claude Code's `rate_limit_event`, or the limit messages that `pipeline.providers.is_quota_message` knows), the node does not fail. An `auto` step moves to the next model of the order first, and a limit seen earlier by another run is known without a call (see "AI tools of the workflows"). It shows "waiting for the usage limit" (`waiting_quota`), the event log says until when, and it tries again when the limit resets: the time the tool names, else `quota_wait_minutes` of `config.toml` (`[general]`). A wait is not counted as a failed attempt. When the waiting would last longer than `quota_max_hours` in total, the node fails. Cancel ends the wait at once.
- At most 4 model calls run at the same time per run, also those of loop parts.
- Conditions: a `condition` node outputs only the port of the branch it takes (`true` or `false`). The nodes connected to the other port are skipped, and so is everything that depends only on them. A join (`text.merge`, `document.export`) runs when at least one of its connections comes from a branch that was taken; the output of a skipped branch is an empty text there. Any other node runs only when all its connections were taken. A skipped branch does not fail the run; a failed node still skips everything after it and fails the run.
- Loops: an `ai.map` node splits a text into parts and asks the model once per part, in parallel. Each answer is stored with a hash of its prompt: a retry or a resumed run asks only for the parts that have no answer yet. The node's timeout applies to each model call, not to the whole node; the retries apply to the node (finished parts are kept between attempts).
- The run stores a frozen copy of the workflow, the resolved model names (`claude/opus@high`) and the tool settings. Resume and retry use these copies, not the current template.
- Resume: the nodes that finished are kept; only the others run. A run whose program ended (closed terminal, crash) shows as "interrupted" and can be resumed.
- An approval node stops its branch until a person approves or rejects it. No program needs to stay open meanwhile; the approval can come from the interface or the command line, also after a restart.
- Only one program drives a run at a time (a lock file in the run folder).
- Keep awake: from the first run on, Mehteran asks the system not to sleep (`pipeline.system.keep_awake`: `caffeinate` on macOS, the execution state on Windows, `systemd-inhibit` on Linux). This holds until Mehteran ends, so a run that waits for a usage limit keeps the computer awake too.
- Resume at start (opt-in): with `resume_interrupted = true` in `<data>/configurations/engine.toml`, `mehter ui` resumes the runs that were running or waiting for a usage limit when the previous program ended (not cancelled, failed or finished ones, and not a run that another program drives). They continue with their frozen settings. Off by default.
- Empty input: a `document.export` step with an empty text fails ("the text to save is empty") and writes no file. An `ai.cli` step that receives data (a connection, a `{{nodes.*}}` reference or a file input) but all of it is empty fails before the model is called. A step with no data at all is an instruction only ("write a haiku") and runs as written; the editor's `schema.warnings()` warn about it.
- A loop part that reports a usage limit stops the parts that have not started; after the wait (or a switch) the loop asks only for the parts without an answer. Part headings ("Part 1") use the language of the run's output: the workflow's `language` input when it has one, else the language of the run.
- A failed step's `error` is the full text of the tool; `error_summary` (in `GET /api/runs/<run>`, per node) is its last meaningful line, not a traceback frame. The run view shows the summary and keeps the full text under "Details".
- Messages in any language: Mehteran stores its own messages (the event log, the errors of nodes and runs) with their message key and values, and shows them in the language of whoever reads them (the interface language, the command line's `--lang`). An event in `GET /api/runs/<run>` is `{time, node_id, kind, message, text, key, params}`: `message` and `text` are the same text in the request's language; `key` and `params` are the stored message (a nested message is `{"$key": ..., "params": {...}}`), or `null` for older runs and for text that a tool wrote, which is shown as it was stored. A node (and a run in the run list) has `error` in the request's language, plus `error_key` and `error_params` in the same form. The database gets the new columns by itself; old rows keep their text.

## Workflow file reference (schema_version 1)

```yaml
schema_version: 1
id: my-review                 # lower-case letters, digits, "-" and "_"; at most 64
author: Ayşe Yılmaz           # optional, at most 80 characters: who shared the file ("Share"); based_on likewise
name: {tr: İnceleme, en: Review}   # a text, or a {tr, en} map (the same for description and labels)
description: What the workflow does.
version: "1.0"
category: research
inputs:
  - {id: paper, type: file, label: {tr: Makale, en: Paper}, formats: [pdf, docx, epub, md, txt]}
  - {id: sources, type: file, multiple: true, required: false, formats: [pdf, md, csv, xlsx]}   # several files
  - {id: language, type: language}   # the output language: any language, chosen from the flag list (see below)
  - {id: model, type: provider, default: auto}
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

Input types: `file` (an upload; `formats` limits the types: `pdf`, `docx`, `epub`, `md`, `txt`, `csv`, `tsv`, `xlsx`, images `png`, `jpg`, `jpeg`, `tif`, `tiff` (read by OCR), `odt`, `rtf` (read by Pandoc), and audio and video `mp3`, `wav`, `m4a`, `ogg`, `opus`, `flac`, `aac`, `mp4`, `webm`, `mov`, `mkv` (speech to text); `multiple: true` takes 1 to 20 files, at most 500 MB together), `text` (`multiline`), `choice` (`options`: texts or `{value, label}`), `provider` (a tool, optionally with model and thinking level), `language` (a language code of the registry; see "The output language"), `url` (a web page or a news feed that `document.extract` reads: see below; `multiple: true` takes up to 30 addresses, one per line, and skips empty lines and lines that start with `#`). Inputs are required unless `required: false`.

Web pages: a `document.extract` step whose `file` is a `url` input (or, without `file`, the workflow's only file or address input) reads the page at that address. Only `http` and `https`, no user name or password in the address. The host name is resolved first: every address it resolves to must be public, so addresses of this computer (`127.0.0.1`, `::1`), of the local network (`10.x`, `172.16–31.x`, `192.168.x`, `fc00::/7`), link-local (`169.254.x`, `fe80::`), multicast and reserved ones are refused; the connection goes to the address that was checked. At most 3 redirects, each checked the same way; no proxy; 10 seconds; at most 5 MB. An HTML page becomes readable text (its title, headings, paragraphs and lists; script, style, navigation and forms are left out); plain text is kept; a PDF is read like an uploaded PDF. JavaScript is not run: a page that builds its text in the browser gives little or no text. Code: `mehteran/urlfetch.py`.

News feeds: an RSS (0.9x, 1.0, 2.0) or Atom feed (by its type, or by its start when the server calls it HTML or text) becomes a list of its items, newest first, at most 50: the feed's title, then for each item its title, its publication date in UTC, its link and a summary of at most 600 characters. The step's `max_age_days` (it may be a placeholder such as `{{inputs.days}}`) keeps only the items of the last days; an item without a date is kept. A line before the items says how many were kept and for which period. A feed with a DTD (`<!DOCTYPE>`, `<!ENTITY>`) is refused, wherever it is and in any encoding: no entity is expanded and nothing else is loaded. With several addresses, each text is between `<document name="<address>" index="<n>">` and `</document>` (an `ai.map` with `split: files` takes one address per part); an address that cannot be read is noted in its place, and the step fails only when no address can be read.

Tables: a CSV, TSV or Excel (.xlsx) file is read into Markdown tables, the first row as the header. A CSV may use `,`, `;`, a tab or `|` (detected); UTF-8, or else Windows Turkish (cp1254). Each visible sheet of an .xlsx file is a table under `## <sheet name>`; numbers with a date format become dates (`2024-01-31`). Limits, each with a note in the text where it cut: 1,000 rows and 40 columns per table, 300 characters per cell, 20 sheets, 500,000 characters per file.

Node types:

| Type | Settings (`config`) | Outputs | Default retries / timeout |
|---|---|---|---|
| `document.extract` | `file` (exactly one file placeholder), `max_chars` (per file), `max_age_days` (feeds), `ocr` (`auto`, `always`, `never`), `ocr_languages`, `speech_model`, `speech_language` | `text` (empty when an optional file input was left empty; with several files, each between `<document name="<file>" index="<n>">` and `</document>`) | 0 / 3600 s |
| `ai.cli` | `provider`, `prompt`, `output` (`text` or `json`), `json_schema` (optional, with `json`) | `text` (with `json`: the answer as pretty-printed JSON) | 2 / the `timeout` of `config.toml` |
| `condition` | `value` (the text to test; default: the connected text), `operator` (`ai`, `contains`, `not_contains`, `equals`, `regex`, `is_yes`, `empty`; default `contains`), `question` and `provider` (for `ai`), `match` (not for `ai`, `is_yes` and `empty`), `case_sensitive` (default false), `pass` (the text the branch carries; default: `value`) | `true` or `false`: only the branch taken, carrying `pass` or `value` | 0 / 60 s |
| `ai.map` | `source`, `split` (`headings`, `paragraphs`, `chunks`, `files`), `chunk_chars` (500–200000, default 12000), `max_items` (1–200, default 50), `provider`, `prompt` (may use `{{item.text}}`, `{{item.title}}`, `{{item.index}}`, `{{item.count}}`), `heading` (default true) | `text`: the answers in order, each under `## <part title>` | 2 / the `timeout` of `config.toml`, per model call |
| `text.merge` | `template` | `text` | 0 / 60 s |
| `approval` | `show` (the text to approve), `instructions` | `text`, `comment` | none (waits for a person) |
| `ai.agent` | `provider` (Claude Code), `prompt`, `sites` (one host per line), `mode` (`read`, `act`; `act` needs an approval before it), `headless` | `text` (the model's report) | 0 / 1800 s |
| `share.x` | `text` (default: the connected text) | `text`, `url` (X's post window, filled in) | 0 / 60 s |
| `document.export` | `source`, `title`, `lang`, `formats` (`md`, `docx`, `html`, `pdf`, `epub`, `eml`, `json`, `csv`), `filename`, `converter` (`auto`, `builtin`, `pandoc`) | one file per format; Markdown tables become real tables in Word, HTML and PDF; links (`[text](https://…)`, `<https://…>`) are links in HTML, PDF and the e-mail, and "text (address)" in Word | 0 / 300 s |

- `output: json` (an AI step): the prompt asks for JSON only, with the schema when `json_schema` is given (a JSON Schema object; the check refuses text that is not one). The answer is read as JSON (also from a ```` ```json ```` fence); when it is not JSON or does not match the schema (`type`, `enum`, `const`, `required`, `properties`, `additionalProperties: false`, `items`, `minItems`, `maxItems`, `minLength`, `maxLength`, `minimum`, `maximum`), the model is asked once more with the error. A second wrong answer fails the attempt with the error. The run's reader shows the result pretty-printed. The estimate counts 2 calls per attempt for such a step.
- `eml`: an e-mail draft that a mail program opens to edit and send (`X-Unsent: 1`): the title as the subject, the text as plain text and as HTML, no sender, no recipient. Mehteran never sends mail.
- `json`, `csv`: when the text is JSON (also in a ```` ```json ```` fence) or has a Markdown table. `json`: the JSON, or the first table as a list of objects. `csv`: the first table, or JSON that is a list of objects or of lists; UTF-8 with a byte order mark for Excel; a cell that starts with `=`, `+`, `-` or `@` (and is not a number) gets a `'` so that a spreadsheet does not run it as a formula. Text with neither fails the step before anything is written. The edited version of a result exports to these formats too.

### The output language (for template authors)

Use an input of type `language` for the language a workflow writes in:

```yaml
inputs:
  - {id: language, type: language, label: {tr: Rapor dili, en: Report language}}
```

- The Run section shows it as the flag list with every language of the registry, and starts at the interface language of whoever runs it. Do not set `default`: with `default: en` a Turkish user gets English documents unless they change it. (`default: <code>` is allowed for a workflow that must start at one language.)
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
- Every file access is resolved inside the data folder; a path that leaves it is refused. Word and HTML results are only downloaded, never shown inside the interface. A Markdown result is shown formatted from DOM elements and text nodes; its raw HTML stays text and its links open only `http`/`https` addresses in a new tab without the opener.
- Answers carry `X-Content-Type-Options: nosniff`, `Cache-Control: no-store` and a strict Content-Security-Policy (no inline scripts or styles, no frames). No other page may frame Mehteran.
- A `url` input reads only public addresses (see "Web pages" above): the guard checks every resolved address and every redirect, uses no proxy, and limits time and size.
- Saving results to a folder writes only into a folder that the user typed and confirmed, never into a system folder or Mehteran's folders, and never over an existing file. Deleting a run removes only its folder inside the data folder, and never while a process drives the run.

## The boundary with the translation app

The translation app's Python code is not changed by Mehteran. Mehteran changes none of these files: `pipeline/*.py`, `prompts/`, `config.default.toml`, `config.toml`, `scripts/start.sh`, `scripts/start.cmd`, `translate`, `translate.cmd`, `Open Interface.*`, `books/`. The translation app's interface (`pipeline/ui/`) is shared: `app.js` mounts itself on its own page and in Mehteran's (`TranslationUI.mount`), and `style.css` scopes its own rules under `.tr-app`. Mehteran's stylesheet starts with a copy of the base rules of `pipeline/ui/style.css`; the page loads `pipeline/ui/style.css` before it, for the book translation.

Mehteran imports these parts of `pipeline` and only reads or calls them:

| Module | Used for |
|---|---|
| `pipeline.providers.run` | the model call of a provider that the user added to `config.toml` (in `mehteran/worker.py`) |
| `pipeline.providers.is_quota_message`, `quota_wait_seconds`, `ACCOUNT_REFUSED`, `parse_json`, `_stream_json_answer` | reading a tool's answer and its usage limit (Mehteran's adapters, as pure functions) |
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

Deliberately left out: plugins and a plugin registry, registering any command-line tool from the interface, shell or Python code nodes, scheduling, and an online place to share workflows (sharing is a file: "Share" and "Import").

## Development

- Tests: `python3 -m unittest discover tests` (the Mehteran tests are `tests/test_mehteran_*.py`; they use the fake tool `tests/mehteran_fake_llm.py`, set `MEHTERAN_HOME` to a temporary folder and make no network calls).
- Code: `mehteran/` (stdlib only). YAML: PyYAML 6.0.2, pure Python, vendored in `mehteran/_vendor/yaml/` (MIT license there), used only through the safe loader and safe dumper.
- A new node type: add a `NodeType` to `mehteran/nodes.py` (`register(...)`) with a label, a description and labelled config fields. The schema and the engine pick it up. `GET /api/node-types` describes every type for the editor's forms: `[{type, label, description, outputs: [{name, kind}], outputs_from ("formats" for document.export, else null), joins, branches, takes_retries, default_retries, default_timeout, timeout_per_call, config: [{name, kind (template | localized | int | bool | choice | formats | id), widget ("area", "provider" or ""), required, default, label, help, options: [{value, label}], min, max (int only), item_fields (fields that take {{item.*}})}]}]`; labels and help are `{tr, en}`.
- Interface: `mehteran/ui/` (vanilla JavaScript, no build step): `app.js` (tabs, the book translation, the library, the Run section, Runs, Setup), `editor.js` (the visual editor), `canvas.js` (the canvas, also used by the run monitor). The book translation's interface is the translation app's `pipeline/ui/app.js` and `style.css`, served as `/tr/app.js` and `/tr/style.css` (`mehteran/translation.py`). Every element is made with DOM calls and text nodes, never from HTML text.
