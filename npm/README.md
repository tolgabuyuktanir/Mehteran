# mehteran

Installs and starts [Mehteran](https://github.com/tolgabuyuktanir/Mehteran): local AI workflows on the AI tools you already use.

```
npx mehteran            # install on the first run, then open the interface
npx mehteran templates  # any Mehteran command: the same as ./mehter <command>
```

- The first run installs Mehteran into `~/Mehteran` (with `git clone`; without git, from the GitHub archive). Set `MEHTERAN_DIR` to use another folder.
- Later runs start the copy in that folder. A git copy updates itself when the interface starts. A copy installed without git does not update: install git and install again.
- Mehteran needs Python 3.11 or later. When the computer has none, Mehteran installs a private Python (uv); no administrator rights are needed.
- Commands run in the Mehteran folder: give file paths as full paths.
- Your books and settings stay in the Mehteran folder. npm never deletes them.

---

[Mehteran](https://github.com/tolgabuyuktanir/Mehteran)'ı kurar ve başlatır: kullandığınız yapay zekâ araçlarıyla yerel iş akışları.

```
npx mehteran            # ilk çalıştırmada kurar, sonra arayüzü açar
npx mehteran templates  # her Mehteran komutu: ./mehter <komut> ile aynı
```

- İlk çalıştırma Mehteran'ı `~/Mehteran` klasörüne kurar (`git clone` ile; git yoksa GitHub arşivinden). Başka bir klasör için `MEHTERAN_DIR` değişkenini ayarlayın.
- Sonraki çalıştırmalar o klasördeki kopyayı başlatır. git kopyası, arayüz başlarken kendini günceller. git olmadan kurulan kopya güncellenmez: git kurun ve yeniden kurun.
- Mehteran Python 3.11 ya da daha yenisini ister. Bilgisayarda yoksa Mehteran kendine ayrı bir Python kurar (uv); yönetici izni gerekmez.
- Komutlar Mehteran klasöründe çalışır: dosya yollarını tam yol olarak verin.
- Kitaplarınız ve ayarlarınız Mehteran klasöründe kalır. npm onları hiçbir zaman silmez.
