# Roadmap: things to do

[Türkçe](#yol-haritası-yapılacaklar)

Mehteran is for people who do not write code. Every improvement here makes it easier for one of them to get work done with AI on their own computer. Many items need no programming at all.

## How to take an item

1. Choose an item below. The level and the skills tell you if it fits you.
2. Open an issue with the item's name, or write in its issue if it has one. Say that you take it. Then nobody else does the same work.
3. Ask questions in the issue at any time. A question is never a bother.
4. Open a pull request. [CONTRIBUTING.md](CONTRIBUTING.md) shows how to run Mehteran and the checks.

**Levels:** 🟢 good first item (a few hours, small and clear) · 🟡 medium (some code in one or two files) · 🔴 larger (a new feature; talk about the plan in the issue first)

## Find an item by skill

| You know | Items |
| --- | --- |
| No programming | [Review a translation](#review-a-translation) · [The sample document in your language](#the-sample-document-in-your-language) · [New screenshots](#new-screenshots) · [Test with a screen reader and the keyboard](#test-with-a-screen-reader-and-the-keyboard) |
| YAML (a simple text format) | [Share a workflow](#share-a-workflow) · [Template defaults in the interface language](#template-defaults-in-the-interface-language) |
| Python | [Sign-in without a terminal window](#sign-in-without-a-terminal-window) · [Audio through Gemini](#audio-through-gemini) |
| Python and JavaScript | [Updates for zip copies](#updates-for-zip-copies) · [Describe a workflow by voice](#describe-a-workflow-by-voice) |

## No programming

### Review a translation
🟢 · You need: one of the interface languages as your mother tongue.
The interface has 18 languages. The 16 other than English and Turkish were translated with AI tools, and nobody who speaks them has read them yet.
- **Start at:** `mehteran/locales/<language>.json`. Each line is one text of the interface. Compare it with the same line in `en.json`.
- **Done when:** the texts read naturally. Small corrections are welcome too: one fixed word is a good pull request.

### The sample document in your language
🟢 · You need: a language other than English and Turkish.
"Try with a sample document" on the Workflows tab opens a made-up lease agreement. It exists in Turkish and English (`mehteran/ui/sample-tr.md`, `sample-en.md`). Other languages get the English one.
- **Start at:** copy `sample-en.md` to `sample-<language>.md` and translate it. Use names and addresses that are clearly made up.
- **Done when:** the file exists and `putSample` in `mehteran/ui/app.js` and `STATIC_TYPES` in `mehteran/web.py` know the new file. Ask in the issue if you want help with these two lines.

### New screenshots
🟢 · You need: to run Mehteran (see the quick start in the README).
The screenshots on the website and in the README (`docs/assets/screens/`) show the old colors and the old Setup tab.
- **Done when:** the eight images show the current interface, in English and Turkish, at the same size as the old ones.

### Test with a screen reader and the keyboard
🟢 · You need: a screen reader (VoiceOver, NVDA or Narrator) or patience with the Tab key.
- **Do:** set up Mehteran, run one workflow and open the result with the keyboard only. Write down where you get stuck.
- **Done when:** an issue with the label `accessibility` lists each problem: which screen, what you did, what happened.

## YAML

### Share a workflow
🟢 · You need: a task you repeat that AI could do.
The built-in workflows are in `mehteran/templates/*.yaml`. Build your workflow in the app, then save it with "Download YAML" and put the file there.
- **Done when:** the template has English and Turkish texts and runs from start to end. The "Templates" part of [CONTRIBUTING.md](CONTRIBUTING.md) lists the rules.

### Template defaults in the interface language
🟡 · You need: YAML, a little Python.
Some text fields have an English default even in other languages. Example: "Who will read it" in `document-explainer.yaml` has `default: "a person with no legal or technical background"`.
- **Do:** let `default` take a text per language, as `label` already does (`{tr: "...", en: "..."}`). Then give the defaults in the templates a Turkish text.
- **Done when:** the Turkish run form shows Turkish defaults, and a test covers it.

## Python

### Sign-in without a terminal window
🟡 · You need: Python, a Linux desktop to test on.
Setup opens a terminal window to sign in to an AI tool. When it cannot (`can_open_terminal()` in `mehteran/common/system.py` is false, for example on some Linux desktops), it asks the user to run a command.
- **Do:** run the sign-in command in the background and show its link and code in the interface.
- **Done when:** a user on such a desktop can sign in without a terminal.

### Audio through Gemini
🟡 · You need: Python, a Gemini or Antigravity account.
Gemini models understand audio. Speech-to-text today runs on this computer with whisper.cpp (`mehteran/speech.py`).
- **Do:** check if the Gemini or Antigravity command-line tool accepts an audio file. Write the result in the issue, with the command you tried.
- **Done when:** we know if it works. If it does, offering it as a second way is a next item.

## Python and JavaScript

### Updates for zip copies
🟡 · You need: Python, JavaScript.
A copy downloaded as a zip file never updates itself.
- **Do:** compare `__version__` (`mehteran/__init__.py`) with the newest release on GitHub, and show "A new version is available" with a download link in the interface. Ask at most once a day, and do nothing when the computer is offline.
- **Done when:** a zip copy of an older version shows the message, and a test covers the version check without the network.

### Describe a workflow by voice
🔴 · You need: Python, JavaScript.
A 🎤 button in the "Describe it, I will build it" box (`#describe-box` in `mehteran/ui/editor.js`). The browser records the voice. Mehteran's own speech-to-text tool (whisper.cpp, `mehteran/speech.py`) writes it down on this computer. The text goes into the box, and the user reads and corrects it. Nothing leaves the computer and no AI usage is spent.
- **Done when:** the button works when whisper.cpp is installed, and offers to install it when it is not.

---

# Yol haritası: yapılacaklar

Mehteran, kod yazmayan insanlar için. Buradaki her iyileştirme, onlardan birinin yapay zekâyla kendi bilgisayarında iş yapmasını kolaylaştırır. Birçok madde hiç programlama gerektirmez.

## Bir maddeyi nasıl üstlenirsiniz

1. Aşağıdan bir madde seçin. Seviye ve beceriler size uyup uymadığını gösterir.
2. Maddenin adıyla bir issue açın ya da varsa maddenin issue'suna yazın. Üstlendiğinizi söyleyin. Böylece başka biri aynı işi yapmaz.
3. Sorularınızı istediğiniz zaman issue'da sorun. Soru sormak hiçbir zaman rahatsızlık değildir.
4. Bir pull request açın. Mehteran'ı çalıştırmayı ve kontrolleri [CONTRIBUTING.tr.md](CONTRIBUTING.tr.md) anlatıyor.

**Seviyeler:** 🟢 ilk katkı için iyi (birkaç saat, küçük ve net) · 🟡 orta (bir iki dosyada biraz kod) · 🔴 büyük (yeni bir özellik; önce planı issue'da konuşun)

## Becerinize göre madde bulun

| Bildiğiniz | Maddeler |
| --- | --- |
| Programlama gerekmez | [Bir çeviriyi gözden geçirin](#bir-çeviriyi-gözden-geçirin) · [Örnek belge sizin dilinizde](#örnek-belge-sizin-dilinizde) · [Yeni ekran görüntüleri](#yeni-ekran-görüntüleri) · [Ekran okuyucu ve klavyeyle deneyin](#ekran-okuyucu-ve-klavyeyle-deneyin) |
| YAML (basit bir metin biçimi) | [Bir iş akışı paylaşın](#bir-iş-akışı-paylaşın) · [Şablon varsayılanları arayüz dilinde](#şablon-varsayılanları-arayüz-dilinde) |
| Python | [Terminal penceresi olmadan giriş](#terminal-penceresi-olmadan-giriş) · [Gemini üzerinden ses](#gemini-üzerinden-ses) |
| Python ve JavaScript | [ZIP kopyaları için güncelleme](#zip-kopyaları-için-güncelleme) · [Sesle iş akışı anlatmak](#sesle-iş-akışı-anlatmak) |

## Programlama gerekmez

### Bir çeviriyi gözden geçirin
🟢 · Gereken: arayüz dillerinden birinin anadiliniz olması.
Arayüz 18 dilde. İngilizce ve Türkçe dışındaki 16 dil yapay zekâ araçlarıyla çevrildi ve o dilleri konuşan biri henüz okumadı.
- **Nereden başlanır:** `mehteran/locales/<dil>.json`. Her satır arayüzün bir metnidir. `en.json` içindeki aynı satırla karşılaştırın.
- **Bitti sayılır:** metinler doğal okunduğunda. Küçük düzeltmeler de memnuniyetle karşılanır: düzeltilmiş tek bir kelime de iyi bir pull request'tir.

### Örnek belge sizin dilinizde
🟢 · Gereken: İngilizce ve Türkçe dışında bir dil.
İş akışları sekmesindeki "Örnek belgeyle deneyin" uydurma bir kira sözleşmesi açar. Türkçesi ve İngilizcesi var (`mehteran/ui/sample-tr.md`, `sample-en.md`). Diğer diller İngilizcesini alır.
- **Nereden başlanır:** `sample-en.md` dosyasını `sample-<dil>.md` adıyla kopyalayıp çevirin. Açıkça uydurma adlar ve adresler kullanın.
- **Bitti sayılır:** dosya var ve `mehteran/ui/app.js` içindeki `putSample` ile `mehteran/web.py` içindeki `STATIC_TYPES` yeni dosyayı tanıyor. Bu iki satır için yardım isterseniz issue'da sorun.

### Yeni ekran görüntüleri
🟢 · Gereken: Mehteran'ı çalıştırmak (README'deki hızlı başlangıca bakın).
Web sitesindeki ve README'deki ekran görüntüleri (`docs/assets/screens/`) eski renkleri ve eski Kurulum sekmesini gösteriyor.
- **Bitti sayılır:** sekiz görüntü güncel arayüzü İngilizce ve Türkçe olarak, eskileriyle aynı boyutta gösteriyor.

### Ekran okuyucu ve klavyeyle deneyin
🟢 · Gereken: bir ekran okuyucu (VoiceOver, NVDA ya da Narrator) ya da Tab tuşuna sabır.
- **Yapılacak:** Mehteran'ı kurun, bir iş akışı çalıştırın ve sonucu yalnızca klavyeyle açın. Takıldığınız yerleri not edin.
- **Bitti sayılır:** `accessibility` etiketli bir issue her sorunu listeliyor: hangi ekran, ne yaptınız, ne oldu.

## YAML

### Bir iş akışı paylaşın
🟢 · Gereken: yapay zekânın yapabileceği, tekrar ettiğiniz bir iş.
Yerleşik iş akışları `mehteran/templates/*.yaml` içinde. İş akışınızı uygulamada kurun, "YAML olarak indir" ile kaydedin ve dosyayı oraya koyun.
- **Bitti sayılır:** şablonun İngilizce ve Türkçe metinleri var ve baştan sona çalışıyor. Kurallar [CONTRIBUTING.tr.md](CONTRIBUTING.tr.md) dosyasının "Şablonlar" bölümünde.

### Şablon varsayılanları arayüz dilinde
🟡 · Gereken: YAML, biraz Python.
Bazı metin alanlarının varsayılanı başka dillerde de İngilizce. Örnek: `document-explainer.yaml` içindeki "Kim okuyacak" alanında `default: "a person with no legal or technical background"` yazıyor.
- **Yapılacak:** `default` alanının da `label` gibi her dil için bir metin almasını sağlayın (`{tr: "...", en: "..."}`). Sonra şablonlardaki varsayılanlara Türkçe metin verin.
- **Bitti sayılır:** Türkçe çalıştırma formu Türkçe varsayılanlar gösteriyor ve bir test bunu denetliyor.

## Python

### Terminal penceresi olmadan giriş
🟡 · Gereken: Python, deneme için bir Linux masaüstü.
Kurulum, bir yapay zekâ aracına giriş için terminal penceresi açar. Açamadığında (`mehteran/common/system.py` içindeki `can_open_terminal()` false döndüğünde, örneğin bazı Linux masaüstlerinde) kullanıcıdan bir komut çalıştırmasını ister.
- **Yapılacak:** giriş komutunu arka planda çalıştırıp bağlantısını ve kodunu arayüzde gösterin.
- **Bitti sayılır:** böyle bir masaüstündeki kullanıcı terminal olmadan giriş yapabiliyor.

### Gemini üzerinden ses
🟡 · Gereken: Python, bir Gemini ya da Antigravity hesabı.
Gemini modelleri sesi anlayabiliyor. Konuşmayı yazıya dökme bugün bu bilgisayarda whisper.cpp ile yapılıyor (`mehteran/speech.py`).
- **Yapılacak:** Gemini ya da Antigravity komut satırı aracının ses dosyası kabul edip etmediğini deneyin. Sonucu, denediğiniz komutla birlikte issue'ya yazın.
- **Bitti sayılır:** çalışıp çalışmadığını biliyoruz. Çalışıyorsa ikinci bir yol olarak sunmak ayrı bir madde olur.

## Python ve JavaScript

### ZIP kopyaları için güncelleme
🟡 · Gereken: Python, JavaScript.
ZIP olarak indirilen bir kopya kendini hiç güncellemez.
- **Yapılacak:** `__version__` değerini (`mehteran/__init__.py`) GitHub'daki en yeni sürümle karşılaştırın ve arayüzde indirme bağlantısıyla "Yeni sürüm var" gösterin. Günde en fazla bir kez sorun; bilgisayar çevrimdışıyken hiçbir şey yapmayın.
- **Bitti sayılır:** eski sürümün ZIP kopyası mesajı gösteriyor ve bir test sürüm denetimini ağa bağlanmadan sınıyor.

### Sesle iş akışı anlatmak
🔴 · Gereken: Python, JavaScript.
"Anlat, oluşturayım" kutusunda (`mehteran/ui/editor.js` içindeki `#describe-box`) bir 🎤 düğmesi. Tarayıcı sesi kaydeder. Mehteran'ın kendi konuşmayı yazıya dökme aracı (whisper.cpp, `mehteran/speech.py`) sesi bu bilgisayarda yazıya döker. Metin kutuya gelir; kullanıcı okuyup düzeltir. Hiçbir şey bilgisayardan çıkmaz ve yapay zekâ kullanım hakkından harcanmaz.
- **Bitti sayılır:** düğme whisper.cpp kuruluyken çalışıyor, kurulu değilken kurmayı öneriyor.
