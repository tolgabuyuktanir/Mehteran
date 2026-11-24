# mehteran

Installs and starts [Mehteran](https://github.com/tolgabuyuktanir/Mehteran): local AI workflows on the AI tools you already use.

```
npx mehteran            # install on the first run, then open the interface
npx mehteran templates  # any Mehteran command: the same as ./mehter <command>
```

- The first run installs the source bundled with that npm release into `~/Mehteran`. Set `MEHTERAN_DIR` to use another folder. The installer requires `tar`.
- Later runs start the existing copy. To try a different release, install it in a new folder with `MEHTERAN_DIR`.
- Mehteran needs Python 3.11 or later. When the computer has none, Mehteran installs a private Python (uv); no administrator rights are needed.
- Commands run in the Mehteran folder: give file paths as full paths.
- Your workflows, runs and settings are kept in Mehteran's data folder (the footer of the interface shows it). npm never deletes them.

Mehteran is an independent project, not affiliated with or endorsed by Anthropic, OpenAI or Google. Claude Code, Codex and Antigravity are trademarks of their owners. License: MIT.

---

[Mehteran](https://github.com/tolgabuyuktanir/Mehteran)'ı kurar ve başlatır: kullandığınız yapay zekâ araçlarıyla yerel iş akışları.

```
npx mehteran            # ilk çalıştırmada kurar, sonra arayüzü açar
npx mehteran templates  # her Mehteran komutu: ./mehter <komut> ile aynı
```

- İlk çalıştırma npm sürümünün içerdiği kaynak kodu `~/Mehteran` klasörüne kurar. Başka bir klasör için `MEHTERAN_DIR` değişkenini ayarlayın. Kurulum için `tar` gerekir.
- Sonraki çalıştırmalar mevcut kopyayı başlatır. Farklı bir sürümü denemek için `MEHTERAN_DIR` ile yeni bir klasöre kurun.
- Mehteran Python 3.11 ya da daha yenisini ister. Bilgisayarda yoksa Mehteran kendine ayrı bir Python kurar (uv); yönetici izni gerekmez.
- Komutlar Mehteran klasöründe çalışır: dosya yollarını tam yol olarak verin.
- İş akışlarınız, çalıştırmalarınız ve ayarlarınız Mehteran'ın veri klasöründe tutulur (arayüzün alt bilgisinde görünür). npm onları hiçbir zaman silmez.

Mehteran bağımsız bir projedir; Anthropic, OpenAI ya da Google ile bağlantılı değildir ve onlar tarafından onaylanmamıştır. Claude Code, Codex ve Antigravity sahiplerinin ticari markalarıdır. Lisans: MIT.
