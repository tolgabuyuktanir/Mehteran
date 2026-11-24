# Security policy

[Türkçe](#güvenlik-politikası)

## Reporting a vulnerability

Do not open a public issue for a security problem. Report it privately on GitHub: **Security → Report a vulnerability** ([open a private report](https://github.com/tolgabuyuktanir/Mehteran/security/advisories/new)).

Include:

- the Mehteran version or commit, and your operating system,
- the steps that show the problem,
- what an attacker can do with it.

You get an answer within 7 days. When the fix is released, the report is published with credit to you, unless you ask otherwise.

## Supported versions

Only the latest commit on `main` and the latest npm release get security fixes.

## What is in scope

Mehteran runs on your computer. These parts matter most:

- **The local web server.** It listens only on `127.0.0.1`. It accepts only requests addressed to `127.0.0.1:<port>` or `localhost:<port>`. Every `/api/` request must carry the session key made at start. A way around any of these is a vulnerability.
- **Files.** Every file must stay inside Mehteran's data folder. A path that reads or writes outside it is a vulnerability.
- **Tool installation.** The Setup tab downloads and installs command-line tools. A download over plain HTTP, or from a source other than the tool's official one, is a vulnerability.
- **Workflows from others.** An imported workflow file must not run commands or read files without the user's action.

These are not vulnerabilities in Mehteran:

- A model that follows an instruction written inside a document (prompt injection). Read the result before you use it. Report it as a normal issue if a built-in template makes it worse.
- Problems in Claude Code, Codex, Antigravity CLI, Ollama or other tools. Report them to their makers.
- `evals/docs/user_lookup.py`. It contains errors on purpose; it is an evaluation example.

---

# Güvenlik politikası

## Güvenlik açığı bildirme

Güvenlik sorunları için herkese açık bir issue açmayın. Sorunu GitHub'da özel olarak bildirin: **Security → Report a vulnerability** ([özel bildirim açın](https://github.com/tolgabuyuktanir/Mehteran/security/advisories/new)).

Bildirime şunları ekleyin:

- Mehteran sürümü ya da commit'i ve işletim sisteminiz,
- sorunu gösteren adımlar,
- bir saldırganın bununla ne yapabileceği.

7 gün içinde yanıt alırsınız. Düzeltme yayımlandığında bildirim, aksini istemezseniz adınız anılarak yayımlanır.

## Desteklenen sürümler

Güvenlik düzeltmelerini yalnızca `main` dalındaki son commit ve son npm sürümü alır.

## Kapsam

Mehteran sizin bilgisayarınızda çalışır. En önemli bölümler şunlardır:

- **Yerel web sunucusu.** Yalnızca `127.0.0.1` adresini dinler. Yalnızca `127.0.0.1:<port>` ya da `localhost:<port>` adresine gönderilen istekleri kabul eder. Her `/api/` isteği başlangıçta üretilen oturum anahtarını taşımalıdır. Bunlardan birini aşan bir yol güvenlik açığıdır.
- **Dosyalar.** Her dosya Mehteran'ın veri klasöründe kalmalıdır. Bu klasörün dışında okuyan ya da yazan bir yol güvenlik açığıdır.
- **Araç kurulumu.** Kurulum sekmesi komut satırı araçlarını indirir ve kurar. Düz HTTP üzerinden ya da aracın resmî kaynağı dışında bir yerden yapılan bir indirme güvenlik açığıdır.
- **Başkalarının iş akışları.** İçe aktarılan bir iş akışı dosyası, kullanıcı bir işlem yapmadan komut çalıştırmamalı ve dosya okumamalıdır.

Şunlar Mehteran'daki güvenlik açıkları değildir:

- Bir belgenin içine yazılmış bir talimata uyan model (prompt injection). Sonucu kullanmadan önce okuyun. Yerleşik bir şablon bunu kötüleştiriyorsa normal bir issue olarak bildirin.
- Claude Code, Codex, Antigravity CLI, Ollama ya da başka araçlardaki sorunlar. Bunları araçların yapımcılarına bildirin.
- `evals/docs/user_lookup.py`. Bilerek hata içerir; bir değerlendirme örneğidir.
