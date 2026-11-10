# Translation Pipeline

[Türkçe](README.tr.md)

Translates Turkish Islamic books into new languages. The Turkish source is the authority. Existing translations of the same book in related languages are used as references. ChatGPT, Gemini and Claude translate, review and check the text in turn. The result is the translated book and a report for the human translator.

It runs on macOS, Windows and Linux, in Turkish and English (TR / EN switch in the interface).

## Getting started

You do not need to install anything first. An internet connection is enough.

1. Download the application: on the GitHub page, click **Code**, then **Download ZIP**. Unpack the zip file into a folder (for example Documents/Translation).
2. Start the interface:
   - **macOS:** right-click `Open Interface.command`, choose **Open**, and click **Open** again in the warning. macOS asks this only the first time, for files downloaded from the internet.
     If you see "you do not have appropriate access privileges": open Terminal, type `sh ` (with a space), drag `Open Interface.command` into the Terminal window and press Enter.
   - **Windows:** double-click `Open Interface.bat`. If "Windows protected your PC" appears, click **More info**, then **Run anyway**.
   - **Linux:** run `./translate ui` in a terminal.
3. On the first start, if the computer has no suitable Python, the application installs a private Python for itself (a minute or two). Then the interface opens in the browser at `http://127.0.0.1:8765/`. The interface runs while its terminal window stays open.
4. Follow the **Getting started** list on the **Setup** tab. Everything else is done in the interface: it installs the AI tools (Claude Code, Codex, Antigravity CLI) and the PDF reader, signs in to the tools, and adds your first book.

Next time, start the interface the same way (double-click is enough after the first time).

## What you need

- **Accounts:** the interface signs in, but you need the subscriptions: a Claude Pro/Max subscription (or Anthropic Console), a paid ChatGPT plan (or an OpenAI API key), and a Google account for Antigravity CLI, which runs the Gemini models (a Google AI Pro or Ultra subscription gives higher usage limits). Since 18 June 2026 Google does not accept personal accounts in Gemini CLI any more; Antigravity CLI replaces it. The default workflow uses all three tools; without an account for one of them, assign another model to its steps on the **Workflow** tab.
- **Books as PDF:** the interface installs the PDF reader (Poppler) with the other tools, into the application's own folder. A `.docx` or `.epub` source is read more completely.
- **Exporting to PDF:** needs Chrome or Edge (Windows always has Edge). Without them, a print-ready page opens; choose "Save as PDF" in the print dialog.

Codex, Node.js and the PDF reader go into the application's own folder (`.runtime/`). Claude Code, Antigravity CLI and the private Python (uv) go into your user folder (`~/.local/bin`; Windows: under `%LOCALAPPDATA%`). To remove the application, delete its folder.

## More

The [user guide](docs/guide.md) describes the interface in detail, the workflow, the export layout, the command line, the folders, the settings, the limits and the development.
