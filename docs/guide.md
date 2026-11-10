# Translation Pipeline: user guide

[Türkçe](guide.tr.md) · [Back to the README](../README.md)

How to start the application is in the [README](../README.md). This guide describes the interface in detail, the command line, the workflow, the folders, the settings and the limits.

## Web interface (recommended)

To open the interface, double-click `Open Interface.command` (macOS) or `Open Interface.bat` (Windows). From a terminal: `./translate ui` (Windows: `translate ui`).

The browser opens `http://127.0.0.1:8765/`. The interface runs while the terminal window stays open.

Nothing needs to be installed in advance (see [Getting started](../README.md#getting-started)). The interface has four tabs:

| Tab | What you do there |
|---|---|
| Setup | Installs Claude Code, Codex and Gemini CLI. Signs in to each of them. "Test" checks that a tool answers. Shows which tool does which step. |
| Workflow | Builds the steps of the workflow and their models by drag and drop (see below). |
| Books | Adds books. Uploads the Turkish source and the reference translations. Selects the target language and starts or stops the translation. Shows the progress and the log. Reads the translation and the report, and exports them as Markdown, Word, PDF or HTML. |
| Instructions | Edits the instructions given to the models. Restores changed instructions to the default. |

Sign-in methods:

- Claude: "With Claude account" opens a terminal window. Sign in in the browser.
- Codex (ChatGPT): "With ChatGPT account" opens a terminal window. Alternative: an OpenAI API key.
- Gemini: "With Google account" opens a terminal window. When Gemini starts, sign in with Google, then type `/quit`. Then check with the "Test" button that the account is accepted. Alternative: an API key from https://aistudio.google.com/apikey (saved in `~/.gemini/.env`).

After you sign in, click "Refresh status".

Security: the interface is reachable only from this computer (`127.0.0.1`). Each start creates a new session key, so other web sites cannot send commands to the server. Uploaded files are checked by content; the maximum file size is 300 MB.

The interface runs a book with the `./translate run` command. A started translation continues when the interface closes. When the interface opens again, it shows the running translation and can stop it.

## Workflow tab: which model does which step

The workflow is drawn as boxes joined by arrows, from left to right: preparation, the first translation, the steps after it, and the human editor. Each step works on the latest text. Add as many steps as you like, in any order:

| Step | What it does |
|---|---|
| Review | Up to 4 models compare the text with the source in parallel and write findings. The text does not change. |
| Apply | Weighs all findings written since the last text (reviews, reporting custom steps, checkpoints) against the source and applies the correct ones. |
| Source check | Compares the text with the source again from the start and corrects it. |
| Custom step | Your own instructions (written in the step's panel; Turkish is fine). It either reports findings (like a review) or corrects the text (like a source check). |
| Checkpoint | A model looks for serious (critical or major) problems that remain. A segment with such problems is sent back to an earlier step that you choose, at most as many times as you set (1–5); the checkpoint's findings go to the next "Apply". At the limit, the segment is marked in the report and goes on. |
| Review round | A shortcut: puts in a Review and an Apply step together. |

- Add a step: drag it from the left onto an arrow, or press the + on an arrow. A click on the card adds it at the end.
- Change the order: drag a box onto another arrow. Preparation and the first translation stay at the start; their models can be changed.
- Click a box to set its options and models below. A reporting step takes up to 4 models (switched on and off); the other steps take one. You can also drop a model card from the left on a role in a box. The panel also has "Move earlier", "Move later" and "Remove step".
- A checkpoint's arc shows where it sends segments back. Checkpoints cannot overlap: a checkpoint cannot send back past the checkpoint before it. Each sending back runs the steps in between again for that segment, which uses quota and time.
- A box marked red cannot run, for example findings that no "Apply" step uses, or a checkpoint without a target. The workflow is not saved until it is fixed. A "!" on a box is a warning only, for example a model that reviews the text it wrote itself.
- The model lists are read from the tools themselves (Claude's model names, the list that Codex keeps, `gemini --list-models`). Add another model by name under its tool; "Test" sends a short request to check that the tool answers.
- Every change is saved at once in `config.toml` (`[stages]` and `[nodes]`; the instructions of custom steps in `prompts/custom/`) and applies to runs started afterwards. "Diagram assignment" restores the workflow of the "Translation and Review Workflow" diagram. A changed order does not redo finished segments; the Books screen shows which segments need to be made again. A stopped run continues where it stopped, also inside a loop.

## Export

The pipeline writes Markdown (`output/<lang>.md`, `output/<lang>.report.md`). In the Books tab you can export each of them:

- Word (.docx): headings as Word headings, footnotes as real Word footnotes. The text is justified and hyphenated automatically; each main chapter starts on a new page; the footer has the page number. Arabic passages inside the text run right to left, and paragraphs made only of Arabic (âyat, hadîth) are centred. For target languages such as Arabic, Persian and Urdu the whole document is right to left.
- PDF: when Chrome or Edge is on the computer, a PDF file is made directly (Windows always has Edge). It is set as a book: justified and hyphenated text, indented paragraphs, page numbers, each main chapter on a new page, footnotes at the end of their chapter. Without such a browser, a print-ready page opens; choose "Save as PDF" in the print dialog.
- HTML and Markdown. Italics and bold are kept in every format.

**Layout of the book.** Click **Layout settings** next to the export links. The settings apply to all books; the report always has the standard A4 layout.

- **Page and type:** page size (A4, A5, B5, 13.5 × 21 cm, 16 × 24 cm, Letter), top, bottom and side margins, font, Arabic font, font size, line spacing (as in Word: 1 is single), justified paragraphs, each top-level chapter on a new page. They are saved in `config.toml` under `[export]`. A font must be installed: the PDF is made with the fonts of this computer, a Word file uses the fonts of the computer that opens it.
- **Word template:** upload the `.docx` or `.dotx` template of your publishing house. The Word file of the book then takes the template's styles, page size, margins, headers and footers; the text of the template is not used. The built-in Word styles "Heading 1–3", "Quote", "List Bullet", "Footnote Text" and "Footnote Reference" are used, also when Word gave them names in another language; the styles that the template lacks are added. With a template, the settings above apply only to PDF and HTML. Files with macros are not accepted. The template is saved as `export/word-template.docx`.

## Long books, usage limits and sleep

- Before you start, the Books tab shows how many segments will be processed, how many model calls each tool needs, and an estimated time. While the run is going, it shows the current step, the elapsed time and the remaining calls and time (measured from the run's own speed).
- When a tool reaches its usage limit (quota), the run does not stop. All requests to that tool wait until the limit resets, then continue by themselves. If the tool does not say when the limit resets, the run waits `quota_wait_minutes` (default 30) and tries again; after `quota_max_hours` (default 24) it gives up. The Books tab and the Setup tab show the wait and the time it ends.
- The computer is kept awake while a translation runs (`keep_awake`; macOS, Windows, and Linux with systemd). On a laptop, keep the lid open and the computer plugged in: when the lid closes, the computer still sleeps and the translation stops. Click "Start" again to continue.
- Segments that were not found in a reference translation are listed under the reference.

## Command line

The messages are in Turkish or English: use `--lang tr` or `--lang en`; the default is `[general] language` in `config.toml`.

On Windows, write `translate` instead of `./translate`.

```sh
./translate setup                       # checks the tools
./translate new <book>                  # creates a book folder
./translate run <book> <lang>           # translates
./translate status [book]               # shows the progress
./translate ui                          # starts the web interface
./translate package                     # writes dist/translation-pipeline.zip for sharing
```

`package` packs only the application. Books, translations, installed tools (`.runtime`) and logs do not go into the zip. Use this command; do not compress the folder by hand.

`run` options:

| Option | Meaning |
|---|---|
| `--refs da,sv` | Uses only these reference languages. Default: all languages in `references/`. |
| `--segments 1-3` | Processes only these segments. `1-5,9` is also valid. |
| `--until glossary` | Stops after this stage. |
| `--redo translate` | Deletes the output of this stage and of the later stages for the selected segments, and produces it again. |
| `--parallel 5` | Number of requests that run at the same time. |

`run` continues where it stopped. If an error or a usage limit stops the work, run the same command again. Finished segments are not produced again.

## Recommended way of working

Review the glossary and a few segments before you translate the whole book.

1. Extract only the glossary: `./translate run ilmihal no --until glossary`
2. Open `glossary/no.tsv` and correct the renderings. This file is shared by all books in that language.
3. Translate the first three segments as a trial, and read the output: `./translate run ilmihal no --segments 1-3`
4. If the result is good, run the whole book: `./translate run ilmihal no`
5. Give the book and `output/no.report.md` to the human translator. After the translator, a human editor reads the book.

If you change the glossary later, produce the translation again: `./translate run ilmihal no --redo translate`

## Workflow

Each segment goes through these steps in order. The numbers are the steps of the "Translation and Review Workflow" diagram.

| Step | Stage | What it does | Default tool |
|---|---|---|---|
| preparation | `prepare` | Converts the source and the references to text. Splits the source into segments of about 6000 characters. | none |
| preparation | `align` | Finds each Turkish segment in the reference translations. | Gemini |
| preparation | `glossary` | Extracts religious terms and proper names. Adds only new terms to `glossary/<lang>.tsv`. | Claude |
| 1 | `translate` | First translation, with the Turkish source, the reference passages and the glossary. | ChatGPT |
| 2 | `review1` | Review: compares the translation with the Turkish source sentence by sentence and reports the issues. | Gemini |
| 3 | `revise1` | Weighs each finding against the Turkish source. Applies correct findings and rejects the others with a reason. | ChatGPT |
| 4 | `source_check` | Compares the text with the Turkish source from the start, without relying on the earlier steps, and corrects the errors. | Claude |
| 5a, 5b | `review2` | Second independent review: two models write findings reports in parallel, without seeing each other. | ChatGPT and Gemini |
| 6 | `reconcile` | Reconciles the two reports against the Turkish source and produces the final text. | Claude |
| delivery | `assemble` | Joins the segments, runs the mechanical checks and writes the report. | none |
| 7 | | The human translator receives the book and the report. Then a human editor reads it. | human |

The reason for this order: each step that changes the text is checked by a model that did not make the change. Gemini reviews ChatGPT's translation. ChatGPT and Gemini check Claude's corrections from step 4.

Every text a model returns (steps 1, 3, 4 and 6) passes a completeness gate before the next step uses it: it must have the same paragraphs and footnote marks as the source, a correction must not make the text noticeably shorter, and no long paragraph may lose a large part of its text. A rejected answer is requested again (up to 3 times); if it is still incomplete, the segment is marked as failed and is not passed on. Segments that are not finished appear in the output as a visible `[[MISSING SEGMENT …]]` line and are listed in the report.

The reviewers (steps 2 and 5) must give a reading proof: they write back the last three words of every paragraph. If the proof does not match the text, the answer is rejected and requested again. Thus the answer "no problems" cannot hide that the text was not read. The model that applies the reviews (steps 3 and 6) must give a decision for every finding. The "Reviewer audit" section of the report shows in how many segments each reviewer wrote no findings, and the segments where a reviewer wrote nothing but serious errors were found later.

If the glossary, the references or the instructions change after a segment was produced, the pipeline detects it. The segment is not produced again by itself; the report and the interface tell you which segments still use old inputs, and from which step. The "Prepare to produce again" button in the interface fills the form; on the command line, use `--redo <step> --segments <segments>`.

The mechanical checks use no AI. They compare the translation with the source: Arabic-script passages, numbers, footnote marks and their texts, number of paragraphs, headings and sentences per paragraph, length of the translation.

The report lists: the mechanical warnings, all critical findings, the major findings that were not accepted, and the segments without a reference passage. The models write their explanations in the interface language of the run. All findings and decisions are in the `revise1`, `source_check` and `reconcile` folders under `work/<lang>/`, one `.json` file per segment. The text of each step is in the same folders, so you can see in which step a sentence changed.

## Folders

```
Open Interface.command  starts the web interface (macOS, double-click)
Open Interface.bat      starts the web interface (Windows, double-click)
translate, translate.cmd  command-line launcher (macOS/Linux, Windows)
config.toml             which tool and model does which stage, language codes
prompts/                instructions for the models (the translation rules are here)
prompts/defaults/       the original instructions; "Restore default" uses them
export/word-template.docx  the Word template of the publishing house (when one is uploaded)
glossary/<lang>.tsv     one glossary per language; edited by hand; shared by all books
books/<book>/
  source/               the Turkish book (one file)
  references/           existing translations: da.docx, sv.epub ...
  work/                 intermediate files; produced by the pipeline
  output/               <lang>.md and <lang>.report.md
  logs/                 the log of each run
pipeline/               the code (pipeline/i18n.py: messages; pipeline/ui/: web interface)
```

Supported file types: `.docx`, `.epub`, `.md`, `.txt`, `.pdf`. If possible, supply `.docx` or `.epub`: from these, headings (also the publisher's own heading styles), footnotes, italics, bold and numbered items are read completely. A PDF is read from the position and type size of each word: page headers and page numbers are dropped; footnotes in a smaller type at the page bottom and raised note numbers in the text become footnotes; paragraphs are found from indentation and spacing, headings from the type size; a paragraph that runs on to the next page is joined. Arabic and Persian text is read from the PDF's own glyphs and put in reading order with its vowel signs; a repeated Besmele is not taken for a page header. A letter that the PDF does not identify (some fonts do not say which letters a ligature shows) stays as pdftotext reads it; check the âyat and hadîths in the preview. A scanned PDF (images) cannot be read; it needs OCR first. Before you translate, check how the text is read with the "Split the text and preview" button on the Books screen. Reading a PDF needs the `pdftotext` program (Poppler or Xpdf); the interface checks this when you upload.

## Configuration

In `config.toml`:

- `[stages]`: the tool and model for each stage, as `provider` or `provider/model`. The Workflow tab edits this section.
- `[providers.*]`: the commands of the tools. If `model` is empty, the tool's default model is used.
- `[languages]`: language codes. For a new language, add one line, for example `tg = "Tajik"`. The models see the English name.
- `[general]`: interface language, segment size, number of parallel requests, timeout, usage-limit waiting, keeping awake.

The translation rules are in `prompts/translate.md`. Examples: how verses and hadiths are translated, keeping Arabic expressions, adding no explanations. If your publishing policy is different, edit this file. The other prompts: `review.md` (Review), `revise.md` (Apply), `source_check.md` (Source check), `custom_report.md` and `custom_rewrite.md` (custom steps; the step's own instructions are put at `{{instructions}}`), `gate.md` (Checkpoint).

## Limits

- The output is Markdown; export gives Word, PDF and HTML. Headings, footnotes, italics, bold and numbered items are kept. Tables, images and colours of the source are not. Print typesetting is a separate step.
- Windows support is written for and tested on macOS only; it has not run on a Windows computer yet.
- If the source file changes after the first run, the pipeline stops. To start again with a new source, click "Reset work" in the interface, or delete `books/<book>/work/`.
- If a reference translation is organised very differently from the Turkish book, some segments have no reference passage. These segments are translated without a reference and listed in the report.
- AI review does not replace human review. Before publication, the human translator and the human editor must read the book.

## Development

The code, the comments and the names are in English. User-facing texts are in two languages:

- Python messages: `pipeline/i18n.py` (`MESSAGES`, a `tr` and an `en` text for each key)
- Web interface texts: the `I18N` dictionary at the top of `pipeline/ui/app.js`

A new message needs both languages. A test checks that every Python message has both languages with the same placeholders.

```sh
python3 -m unittest discover -s tests
```

The tests make no real AI calls. They use a fake tool (`tests/fake_llm.py`).
