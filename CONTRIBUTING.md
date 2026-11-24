# Contributing to Mehteran

[Türkçe](CONTRIBUTING.tr.md)

Thank you for helping. Bug reports, translation fixes, new templates and code changes are all welcome.

## Before you start

- For a small fix (a typo, a wrong translation, a clear bug), open a pull request directly.
- For a larger change (a new feature, a new step type, a change in how runs work), open an issue first. Describe the problem and your plan, so that nobody does the same work twice.
- For a security problem, do not open an issue. See [SECURITY.md](SECURITY.md).

Looking for something to do? [ROADMAP.md](ROADMAP.md) lists items with a level (🟢 good first item, 🟡 medium, 🔴 larger) and the skills each needs. Many need no programming.

## Run Mehteran from the source

Mehteran needs Python 3.11 or later and nothing else. There are no packages to install and no build step.

```
git clone https://github.com/tolgabuyuktanir/Mehteran.git
cd Mehteran
./mehter ui          # Windows: mehter.cmd ui
```

## Checks before a pull request

CI runs the first four commands on Ubuntu, macOS and Windows. The unit tests also check the locale files, as the last command does. Run all of them on your computer first:

```
python3 -m pip install ruff==0.4.10
ruff check mehteran tests
node --test tests/mehteran_markdown_test.mjs
python3 -m unittest discover tests
python3 -m mehteran.i18n_tools validate
```

The tests use a fake AI tool and make no network calls. A bug fix needs a test that fails without the fix.

## Code

- Write code, comments, names and commit messages in English.
- Use only the Python standard library. The interface is plain JavaScript in `mehteran/ui/`; do not add a framework or a build step.
- Match the style of the code around your change. Keep the change small: no features that nobody asked for.
- The reference ([docs/mehteran.md](docs/mehteran.md) and [docs/mehteran.tr.md](docs/mehteran.tr.md)) describes every screen, setting and API route. When you change one of them, update both files.

## Interface texts and translations

The interface has 18 languages. The texts are in `mehteran/locales/<language>.json`.

- Every new text needs an English (`en.json`) and a Turkish (`tr.json`) version. The other languages may leave a text out; Mehteran then shows the English text.
- A translated text keeps the `{name}` placeholders of the English text.
- `python3 -m mehteran.i18n_tools coverage` shows how complete each language is. `python3 -m mehteran.i18n_tools missing <language>` lists the missing texts.

**Help wanted:** the 16 languages other than English and Turkish were translated with AI tools. Native speakers have not reviewed them. If you speak one of them, correct the texts in its file and open a pull request. Small corrections are welcome.

## Templates

The built-in workflows are in `mehteran/templates/*.yaml`. The workflow file is described in the reference.

- `tier: core` puts a template in the "Start here" group. Keep this group small (about 20 templates).
- Use `tier: experimental` when a template needs paid API keys, drives a browser on websites that change, or publishes to an outside service. The interface then shows an "Experimental" badge and a notice.
- A template's name, description and instructions need English and Turkish text.
- `python3 -m unittest tests.test_mehteran_builtin_templates` checks the other rules of a built-in template: the file name, the category, 3 to 10 steps, a language input, a Word/HTML/Markdown export. When a check fails, the output names the template.

## Evaluation set

When you change the instruction of a template that a case in `evals/cases.json` uses, run the evaluation set before and after the change and compare:

```
./mehter eval --model claude/haiku --out before
# make the change
./mehter eval --model claude/haiku --out after
./mehter eval --compare before/report-<time>.json after/report-<time>.json
```

The evaluation set makes real model calls with your own AI tools, so it costs usage. CI does not run it. Put the result of the comparison in the pull request.

## License

By contributing, you agree that your contribution is licensed under the [MIT License](LICENSE).
