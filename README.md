<p align="center"><img src="docs/assets/icon.svg" width="88" alt="Mehteran"></p>

<h1 align="center">Mehteran</h1>

<p align="center"><b>AI workflows on your own computer, with the AI subscriptions you already have.</b></p>

<p align="center"><a href="README.tr.md">Türkçe</a> · <a href="https://tolgabuyuktanir.github.io/TranslationPipeline/">Website</a> · <a href="https://tolgabuyuktanir.github.io/TranslationPipeline/docs.html">Docs</a> · <a href="docs/mehteran.md">Full reference</a></p>

![The Mehteran workflow library](docs/assets/screens/en-library.png)

Mehteran turns the AI tools you already use into repeatable workflows. A workflow reads a document, asks a model, checks the answer, lets a person approve and saves a Word or PDF file. Mehteran calls the AI through the command-line tools of your subscriptions (Claude Code, Codex, Antigravity CLI) or through models on this computer (Ollama, LM Studio, llama.cpp). It keeps no keys and no accounts of its own, and it costs nothing on top of what you already pay.

It runs on macOS, Windows and Linux, in 18 interface languages.

## Why Mehteran

- **No extra bill.** Mehteran removes API keys from every model call, so a tool cannot bill an API account by accident. A billed API key is used only when you allow it for that tool.
- **Your files stay with you.** The interface runs only on `127.0.0.1`. Runs, results and settings are folders on your disk. A workflow marked "local only" sends no text off the computer.
- **72 ready-made templates** in 10 categories: documents, business, legal, education, exams, research, writing, data, software and everyday tasks.
- **A visual editor**, or plain words: draw steps on a canvas (AI steps, conditions, loops, human approvals), or describe the workflow and let a model draft it. "Test this step" runs one step on its own.
- **Real documents in and out.** Reads PDF, Word, EPUB, Excel, web pages, scans (OCR) and recordings (speech to text). Saves Markdown, Word, HTML, PDF, EPUB, e-mail drafts, JSON and CSV.
- **Usage limits do not break a run.** A step waits for the limit to reset, or continues with the next model of your order.
- **Every run is kept**: watch it live, stop and resume it, compare two runs, edit a result and export it.

## Getting started

You do not need to install anything first. An internet connection is enough.

1. On this GitHub page, click **Code**, then **Download ZIP**. Unpack the zip file into a folder (for example `Documents/Mehteran`).
2. Start the interface:
   - **macOS:** right-click `Open Mehteran.command`, choose **Open**, and click **Open** again in the warning. macOS asks this only the first time, for files downloaded from the internet.
     If you see "you do not have appropriate access privileges": open Terminal, type `sh ` (with a space), drag `Open Mehteran.command` into the Terminal window and press Enter.
   - **Windows:** double-click `Open Mehteran.bat`. If "Windows protected your PC" appears, click **More info**, then **Run anyway**.
   - **Linux:** run `./mehter ui` in a terminal.
3. On the first start, if the computer has no suitable Python (3.11 or later), Mehteran installs a private Python for itself (a minute or two). Then the interface opens in the browser at `http://127.0.0.1:8766/`. It runs while its terminal window stays open.
4. On the **Setup** tab, install the AI tools you want and sign in. Then open a workflow on the **Workflows** tab and run it.

Next time, start it the same way (double-click is enough after the first time).

## AI tools

| Tool | How it is paid | Where the text goes |
|---|---|---|
| Claude Code | Subscription (Claude Pro / Max) | Anthropic |
| Codex CLI | Subscription (a paid ChatGPT plan) | OpenAI |
| Antigravity CLI | Free Google account | Google |
| Ollama | Local | Stays on this computer |
| LM Studio, llama.cpp, vLLM (OpenAI-compatible local server) | Local | Stays on this computer |
| Gemini CLI | API key (billed) | Google |

You need at least one of them. The Setup tab installs the tools, signs you in and shows each tool's usage. With `auto` as a step's model, Mehteran picks the first tool of your model order that is installed, signed in and not billed by an API key.

The optional local tools (Ollama, Tesseract OCR, Typst for PDF, Pandoc, whisper.cpp for speech to text, qpdf) are installed only when you ask, as pinned versions checked against SHA-256 sums.

## Islamic book translation

Mehteran grew out of a book translation pipeline, and the translation is still inside, as the pinned "Islamic book translation" card of the Workflows tab. It translates Turkish Islamic books into new languages. The Turkish source is the authority. Existing translations of the same book in related languages are used as references. ChatGPT, Gemini and Claude translate, review and check the text in turn. The result is the translated book and a report for the human translator.

The translation app also runs on its own: `Open Interface.command` (macOS), `Open Interface.bat` (Windows) or `./translate ui` (Linux), at `http://127.0.0.1:8765/`. Its [user guide](docs/guide.md) describes it in detail.

What the default translation workflow needs:

- **Accounts:** a Claude Pro/Max subscription (or Anthropic Console), a paid ChatGPT plan (or an OpenAI API key), and a Google account for Antigravity CLI, which runs the Gemini models (a Google AI Pro or Ultra subscription gives higher usage limits). Since 18 June 2026 Google does not accept personal accounts in Gemini CLI any more; Antigravity CLI replaces it. Without an account for one of the tools, assign another model to its steps in the translation workflow.
- **Books as PDF:** the Setup tab installs the PDF reader (Poppler). A `.docx` or `.epub` source is read more completely.
- **Exporting the book to PDF:** needs Chrome or Edge (Windows always has Edge). Without them, a print-ready page opens; choose "Save as PDF" in the print dialog.

## Updates

If you got the application with git (`git clone` or `gh repo clone`), it updates itself from GitHub each time the interface starts. Without internet or without a GitHub sign-in, it starts as it is.

If you downloaded a zip file, download the new zip. Mehteran's workflows and runs are kept outside the code folder, so they stay where they are. For the book translation, move these from the old folder into the new one: `books/`, `glossary/`, `config.toml` and the `.md` files directly in `prompts/` (and `prompts/custom/`).

Codex, Node.js and the PDF reader go into the application's own folder (`.runtime/`). Claude Code, Antigravity CLI and the private Python (uv) go into your user folder (`~/.local/bin`; Windows: under `%LOCALAPPDATA%`). To remove the application, delete its folder and Mehteran's data folder (see the docs).

## Documentation

- [Website](https://tolgabuyuktanir.github.io/TranslationPipeline/) and [docs](https://tolgabuyuktanir.github.io/TranslationPipeline/docs.html): install, connect your AI tools, run and build workflows, local models, the workflow file, troubleshooting.
- [Mehteran full reference](docs/mehteran.md): every screen, setting, API route and limit.
- [Book translation user guide](docs/guide.md).

## Development

- Code: `mehteran/` (Mehteran) and `pipeline/` (the book translation), Python standard library only; the interface is plain JavaScript with no build step.
- Tests: `python3 -m unittest discover tests`. They use a fake AI tool and make no network calls.
- The website is static HTML in `docs/` (`index.html`, `docs.html`, `assets/`); it loads nothing from other servers.
