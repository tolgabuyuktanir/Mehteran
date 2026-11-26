## What this changes / Ne değişiyor

<!-- One or two sentences. Link the issue: "Closes #12". / Bir iki cümle. Issue'yu bağlayın: "Closes #12". -->

## AI tools / Yapay zekâ araçları

<!-- Which tool, and for what? "None" is fine. See "AI tools" in CONTRIBUTING.md. -->
<!-- Hangi araç, ne için? "Yok" da olur. CONTRIBUTING.tr.md içindeki "Yapay zekâ araçları" bölümüne bakın. -->

## Checks / Kontroller

<!-- CONTRIBUTING.md lists the commands. Tick what you ran. A translation or text fix needs only the last one. -->
<!-- Komutlar CONTRIBUTING.tr.md dosyasında. Çalıştırdıklarınızı işaretleyin. Çeviri ya da metin düzeltmesi için yalnızca sonuncusu yeter. -->

- [ ] `ruff check mehteran tests`
- [ ] `python3 -m unittest discover tests`
- [ ] `python3 -m mehteran.i18n_tools validate`
- [ ] `node --test tests/mehteran_markdown_test.mjs` (only for changes in `mehteran/ui/markdown.js` / yalnızca `mehteran/ui/markdown.js` değişikliklerinde)
