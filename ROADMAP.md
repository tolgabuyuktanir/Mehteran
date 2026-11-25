# Roadmap: things to do

[Türkçe](#yol-haritası-yapılacaklar)

Mehteran is for people who do not write code. Every improvement here makes it easier for one of them to get work done with AI on their own computer. Many items need no programming at all.

## How to take an item

1. Choose an item below. The level and the skills tell you if it fits you.
2. Write a comment in the item's issue (the link is next to its level) and say what you take. Several people can work on one item when it has many parts: say which language or which workflow is yours.
3. Ask questions in the issue at any time. A question is never a bother.
4. Open a pull request, or write your result in the issue when the item asks for that. [CONTRIBUTING.md](CONTRIBUTING.md) shows how to run Mehteran and the checks.

**A text or translation fix needs no installation:** open the file on GitHub, click the pencil, change the text and click "Propose changes". The checks run by themselves.

**Levels:** 🟢 good first item (small and clear) · 🟡 medium (code in a few files) · 🔴 larger (a new feature; talk about the plan in the issue first)

## Find an item by skill

| Your skills | Items |
| --- | --- |
| No programming | [Review a translation](#review-a-translation) · [The sample document in your language](#the-sample-document-in-your-language) · [New screenshots](#new-screenshots) · [Test with a screen reader and the keyboard](#test-with-a-screen-reader-and-the-keyboard) · [Share a workflow](#share-a-workflow) |
| A terminal | [Audio through Gemini](#audio-through-gemini) |
| Python and JavaScript | [Template defaults in the interface language](#template-defaults-in-the-interface-language) · [Updates for zip copies](#updates-for-zip-copies) · [Sign-in without a terminal window](#sign-in-without-a-terminal-window) · [Describe a workflow by voice](#describe-a-workflow-by-voice) |

## No programming

### Review a translation
🟢 · [issue #1](https://github.com/tolgabuyuktanir/Mehteran/issues/1) · You need: one of the interface languages as your native language.
The interface has 18 languages. The 16 other than English and Turkish were translated with AI tools, and nobody who speaks them has read them yet.
- **Start at:** `mehteran/locales/<language>.json`. Each line is one text of the interface: the name on the left, the text on the right. Compare it with the line with the same name in `en.json`. Keep `{name}` parts and the quotation marks as they are.
- **Done when:** the texts read naturally. The file has about 1,350 short texts; a part is fine too, so say which part you read. One fixed word is a good pull request.

### The sample document in your language
🟢 · [issue #2](https://github.com/tolgabuyuktanir/Mehteran/issues/2) · You need: a language other than English and Turkish.
"Try with a sample document", on the first panel of the Workflows tab, opens a made-up lease agreement. It exists in Turkish and English (`mehteran/ui/sample-tr.md`, `sample-en.md`). Other languages get the English one.
- **Start at:** copy `sample-en.md` to `sample-<language>.md` and translate it. Use names and addresses that are clearly made up.
- **Done when:** the file exists, and `putSample` in `mehteran/ui/app.js` and `STATIC_TYPES` in `mehteran/web.py` know it. Ask in the issue if you want help with these two places.

### New screenshots
🟢 · [issue #3](https://github.com/tolgabuyuktanir/Mehteran/issues/3) · You need: to run Mehteran (see the quick start in the README) with a signed-in AI tool or a local model, for the result screen.
The screenshots on the website (`docs/assets/screens/`) show the old colors and an older Workflows page.
- **Done when:** the same eight files show the current interface: `en-` and `tr-` versions of `library`, `editor`, `runform` and `reader`. The old ones are 2720×1720 pixels (a 1360×860 window on a 2× screen); 1360×860 is fine too.

### Test with a screen reader and the keyboard
🟢 · [issue #4](https://github.com/tolgabuyuktanir/Mehteran/issues/4) · You need: a screen reader (VoiceOver, NVDA or Narrator), or patience with the Tab key; a signed-in AI tool or a local model to run a workflow.
- **Do:** set up Mehteran, run one workflow and open the result with the keyboard only. Write down where you get stuck.
- **Done when:** a comment in the issue lists each problem: which screen, what you did, what happened.

### Share a workflow
🟢 · [issue #5](https://github.com/tolgabuyuktanir/Mehteran/issues/5) · You need: a task you repeat that AI could do.
Build your workflow in the app. Then save it: the ⋯ menu on the workflow's page → "Download YAML".
- **Done when:** you attach the downloaded file to the issue and say what it does. We help to make it a built-in template (English and Turkish texts, the tests). If you want to do that part yourself, the "Templates" part of [CONTRIBUTING.md](CONTRIBUTING.md) lists the rules.

## A terminal

### Audio through Gemini
🟢 · [issue #8](https://github.com/tolgabuyuktanir/Mehteran/issues/8) · You need: a terminal, a Gemini or Antigravity account.
Gemini models understand audio. Speech-to-text today runs on this computer with whisper.cpp (`mehteran/speech.py`).
- **Do:** check if the Gemini or Antigravity command-line tool accepts an audio file. Write the result in the issue, with the command you tried.
- **Done when:** we know if it works. If it does, offering it as a second way is a next item.

## Python and JavaScript

### Template defaults in the interface language
🟡 · [issue #6](https://github.com/tolgabuyuktanir/Mehteran/issues/6) · You need: Python, JavaScript, YAML.
Some text fields have an English default in every language. Example: "Who will read it" in `document-explainer.yaml` has `default: "a person with no legal or technical background"`. Six text defaults in five templates are like this.
- **Do:** let `default` take a text per language, as `label` already does (`{tr: "...", en: "..."}`). Then give those defaults a Turkish text.
- **Start at:** `mehteran/schema.py` (the `default` check of text inputs), `mehteran/engine.py`, `mehteran/ui/app.js` (the run form), `mehteran/ui/editor.js` (the "Default" field).
- **Done when:** the Turkish run form shows Turkish defaults, and a test covers it.

### Updates for zip copies
🟡 · [issue #9](https://github.com/tolgabuyuktanir/Mehteran/issues/9) · You need: Python, JavaScript.
A copy downloaded as a zip file never updates itself. The same is true of an npm copy.
- **Do:** in Python, compare `__version__` (`mehteran/__init__.py`) with the newest release on GitHub. Show "A new version is available" with a download link in the page footer. Ask at most once a day, send nothing but the request, and do nothing when the computer is offline.
- **Start at:** `mehteran/update.py`, `drawFooter` in `mehteran/ui/live.js` and the text `footer_updates`.
- **Done when:** a zip copy of an older version shows the message, a test covers the version check without the network, and the reference (`docs/mehteran.md`, `docs/mehteran.tr.md`) says that Mehteran makes this request.

### Sign-in without a terminal window
🔴 · [issue #7](https://github.com/tolgabuyuktanir/Mehteran/issues/7) · You need: Python, JavaScript, a Linux desktop to test on.
Setup opens a terminal window to sign in to an AI tool. When it cannot (`can_open_terminal()` in `mehteran/common/system.py` is false, for example on some Linux desktops), it asks the user to run a command. The sign-in commands are in `mehteran/common/tools.py`; for Antigravity and Gemini the command starts the tool itself.
- **Do:** start with one tool. Check if its sign-in command can print a link and a code without a terminal (for example a device-code option, if the tool has one), and write what you find in the issue. Then run it in the background and show the link and the code in Setup.
- **Done when:** a user on such a desktop can sign in to that tool without a terminal.

### Describe a workflow by voice
🔴 · [issue #10](https://github.com/tolgabuyuktanir/Mehteran/issues/10) · You need: Python, JavaScript.
A 🎤 button in the "Describe it, I will build it" box (`#describe-box` in `mehteran/ui/editor.js`). The browser records the voice. Mehteran's own speech-to-text tool (whisper.cpp, `mehteran/speech.py`) writes it down on this computer. The text goes into the box, and the user reads and corrects it. Nothing leaves the computer and no AI usage is spent.
- **Done when:** the button works when whisper.cpp is installed, and offers to install it when it is not.

---

# Yol haritası: yapılacaklar

[English](#roadmap-things-to-do)

Mehteran, kod yazmayan insanlar için. Buradaki her iyileştirme, onlardan birinin yapay zekâyla kendi bilgisayarında iş yapmasını kolaylaştırır. Birçok madde hiç programlama gerektirmez.

## Bir maddeyi nasıl üstlenirsiniz

1. Aşağıdan bir madde seçin. Seviye ve beceriler size uyup uymadığını gösterir.
2. Maddenin issue'suna (bağlantısı seviyesinin yanında) bir yorum yazıp neyi üstlendiğinizi söyleyin. Çok parçalı bir maddede aynı anda birkaç kişi çalışabilir: hangi dili ya da hangi iş akışını üstlendiğinizi yazın.
3. Sorularınızı istediğiniz zaman issue'da sorun. Soru sormak hiçbir zaman rahatsızlık değildir.
4. Bir pull request açın ya da madde bunu istiyorsa sonucunuzu issue'ya yazın. Mehteran'ı çalıştırmayı ve kontrolleri [CONTRIBUTING.tr.md](CONTRIBUTING.tr.md) anlatıyor.

**Metin ya da çeviri düzeltmesi için kurulum gerekmez:** dosyayı GitHub'da açın, kalem simgesine tıklayın, metni değiştirin ve "Propose changes" düğmesine tıklayın. Kontroller kendiliğinden çalışır.

**Seviyeler:** 🟢 ilk katkı için iyi (küçük ve net) · 🟡 orta (birkaç dosyada kod) · 🔴 büyük (yeni bir özellik; önce planı issue'da konuşun)

## Becerinize göre madde bulun

| Becerileriniz | Maddeler |
| --- | --- |
| Programlama bilmiyorum | [Bir çeviriyi gözden geçirin](#bir-çeviriyi-gözden-geçirin) · [Örnek belge sizin dilinizde](#örnek-belge-sizin-dilinizde) · [Yeni ekran görüntüleri](#yeni-ekran-görüntüleri) · [Ekran okuyucu ve klavyeyle deneyin](#ekran-okuyucu-ve-klavyeyle-deneyin) · [Bir iş akışı paylaşın](#bir-iş-akışı-paylaşın) |
| Terminal | [Gemini üzerinden ses](#gemini-üzerinden-ses) |
| Python ve JavaScript | [Şablon varsayılanları arayüz dilinde](#şablon-varsayılanları-arayüz-dilinde) · [ZIP kopyaları için güncelleme](#zip-kopyaları-için-güncelleme) · [Terminal penceresi olmadan giriş](#terminal-penceresi-olmadan-giriş) · [Sesle iş akışı anlatmak](#sesle-iş-akışı-anlatmak) |

## Programlama gerekmez

### Bir çeviriyi gözden geçirin
🟢 · [issue #1](https://github.com/tolgabuyuktanir/Mehteran/issues/1) · Gereken: arayüz dillerinden birinin anadiliniz olması.
Arayüz 18 dilde. İngilizce ve Türkçe dışındaki 16 dil yapay zekâ araçlarıyla çevrildi ve o dilleri konuşan biri henüz okumadı.
- **Nereden başlanır:** `mehteran/locales/<dil>.json`. Her satır arayüzün bir metnidir: solda adı, sağda metni. `en.json` içinde solda aynı adı taşıyan satırla karşılaştırın. `{ad}` biçimindeki parçaları ve tırnak işaretlerini olduğu gibi bırakın.
- **Bitti sayılır:** metinler doğal okunduğunda. Dosyada yaklaşık 1.350 kısa metin var; bir bölümü de yeter, hangi bölümü okuduğunuzu yazın. Düzeltilmiş tek bir kelime de iyi bir pull request'tir.

### Örnek belge sizin dilinizde
🟢 · [issue #2](https://github.com/tolgabuyuktanir/Mehteran/issues/2) · Gereken: İngilizce ve Türkçe dışında bir dil.
İş akışları sekmesinin ilk panelindeki "Örnek belgeyle deneyin" uydurma bir kira sözleşmesi açar. Türkçesi ve İngilizcesi var (`mehteran/ui/sample-tr.md`, `sample-en.md`). Diğer dillerde İngilizcesi açılır.
- **Nereden başlanır:** `sample-en.md` dosyasını `sample-<dil>.md` adıyla kopyalayıp çevirin. Açıkça uydurma adlar ve adresler kullanın.
- **Bitti sayılır:** dosya eklendiğinde ve `mehteran/ui/app.js` içindeki `putSample` ile `mehteran/web.py` içindeki `STATIC_TYPES` onu tanıdığında. Bu iki yer için yardım isterseniz issue'da sorun.

### Yeni ekran görüntüleri
🟢 · [issue #3](https://github.com/tolgabuyuktanir/Mehteran/issues/3) · Gereken: sonuç ekranı için Mehteran'ı giriş yapılmış bir yapay zekâ aracıyla ya da yerel bir modelle çalıştırmak (README'deki hızlı başlangıca bakın).
Web sitesindeki ekran görüntüleri (`docs/assets/screens/`) eski renkleri ve İş akışları sayfasının eski hâlini gösteriyor.
- **Bitti sayılır:** aynı sekiz dosya güncel arayüzü gösterdiğinde: `library`, `editor`, `runform` ve `reader` görüntülerinin `en-` ve `tr-` sürümleri. Eskileri 2720×1720 piksel (2× ekranda 1360×860 bir pencere); 1360×860 da olur.

### Ekran okuyucu ve klavyeyle deneyin
🟢 · [issue #4](https://github.com/tolgabuyuktanir/Mehteran/issues/4) · Gereken: bir ekran okuyucu (VoiceOver, NVDA ya da Narrator) ya da Tab tuşuyla ilerleyecek sabır; bir iş akışı çalıştırmak için giriş yapılmış bir yapay zekâ aracı ya da yerel bir model.
- **Yapılacak:** Mehteran'ı kurun, bir iş akışı çalıştırın ve sonucu yalnızca klavyeyle açın. Takıldığınız yerleri not edin.
- **Bitti sayılır:** issue'ya yazdığınız bir yorum her sorunu listelediğinde: hangi ekran, ne yaptınız, ne oldu.

### Bir iş akışı paylaşın
🟢 · [issue #5](https://github.com/tolgabuyuktanir/Mehteran/issues/5) · Gereken: yapay zekânın yapabileceği, tekrar ettiğiniz bir iş.
İş akışınızı uygulamada kurun. Sonra kaydedin: iş akışının sayfasındaki ⋯ menüsü → "YAML olarak indir".
- **Bitti sayılır:** indirdiğiniz dosyayı issue'ya ekleyip ne yaptığını yazdığınızda. Onu yerleşik bir şablona dönüştürmek için (İngilizce ve Türkçe metinler, testler) biz yardım ederiz. Bu kısmı kendiniz yapmak isterseniz kurallar [CONTRIBUTING.tr.md](CONTRIBUTING.tr.md) dosyasının "Şablonlar" bölümünde.

## Terminal

### Gemini üzerinden ses
🟢 · [issue #8](https://github.com/tolgabuyuktanir/Mehteran/issues/8) · Gereken: terminal, bir Gemini ya da Antigravity hesabı.
Gemini modelleri sesi anlayabiliyor. Konuşmayı yazıya dökme bugün bu bilgisayarda whisper.cpp ile yapılıyor (`mehteran/speech.py`).
- **Yapılacak:** Gemini ya da Antigravity komut satırı aracının ses dosyası kabul edip etmediğini deneyin. Sonucu, denediğiniz komutla birlikte issue'ya yazın.
- **Bitti sayılır:** çalışıp çalışmadığını öğrendiğimizde. Çalışıyorsa ikinci bir yol olarak sunmak ayrı bir madde olur.

## Python ve JavaScript

### Şablon varsayılanları arayüz dilinde
🟡 · [issue #6](https://github.com/tolgabuyuktanir/Mehteran/issues/6) · Gereken: Python, JavaScript, YAML.
Bazı metin alanlarının varsayılanı her dilde İngilizce. Örnek: `document-explainer.yaml` içindeki "Kim okuyacak" alanında `default: "a person with no legal or technical background"` yazıyor. Beş şablonda böyle altı varsayılan var.
- **Yapılacak:** `default` alanının da `label` gibi her dil için bir metin almasını sağlayın (`{tr: "...", en: "..."}`). Sonra bu varsayılanlara Türkçe metin verin.
- **Nereden başlanır:** `mehteran/schema.py` (metin girdilerinde `default` denetimi), `mehteran/engine.py`, `mehteran/ui/app.js` (çalıştırma formu), `mehteran/ui/editor.js` ("Varsayılan" alanı).
- **Bitti sayılır:** Türkçe çalıştırma formu Türkçe varsayılanları gösterdiğinde ve bir test bunu denetlediğinde.

### ZIP kopyaları için güncelleme
🟡 · [issue #9](https://github.com/tolgabuyuktanir/Mehteran/issues/9) · Gereken: Python, JavaScript.
ZIP olarak indirilen bir kopya kendini hiç güncellemez. npm kopyası için de bu geçerli.
- **Yapılacak:** Python'da `__version__` değerini (`mehteran/__init__.py`) GitHub'daki en yeni sürümle karşılaştırın. Sayfanın alt bilgisinde indirme bağlantısıyla "Yeni sürüm var" gösterin. Günde en fazla bir kez sorun, istekten başka hiçbir şey göndermeyin ve bilgisayar çevrimdışıyken hiçbir şey yapmayın.
- **Nereden başlanır:** `mehteran/update.py`, `mehteran/ui/live.js` içindeki `drawFooter` ve `footer_updates` metni.
- **Bitti sayılır:** eski sürümün ZIP kopyası mesajı gösterdiğinde, bir test sürüm denetimini ağa bağlanmadan sınadığında ve başvuru belgesi (`docs/mehteran.md`, `docs/mehteran.tr.md`) Mehteran'ın bu isteği yaptığını söylediğinde.

### Terminal penceresi olmadan giriş
🔴 · [issue #7](https://github.com/tolgabuyuktanir/Mehteran/issues/7) · Gereken: Python, JavaScript, deneme için bir Linux masaüstü.
Kurulum, bir yapay zekâ aracına giriş için terminal penceresi açar. Açamadığında (`mehteran/common/system.py` içindeki `can_open_terminal()` false döndüğünde, örneğin bazı Linux masaüstlerinde) kullanıcıdan bir komut çalıştırmasını ister. Giriş komutları `mehteran/common/tools.py` içinde; Antigravity ve Gemini için komut aracın kendisini başlatır.
- **Yapılacak:** tek bir araçla başlayın. Giriş komutunun terminal olmadan bir bağlantı ve kod yazdırıp yazdıramadığını denetleyin (örneğin aracın varsa bir "device code" seçeneği) ve bulduğunuzu issue'ya yazın. Sonra komutu arka planda çalıştırıp bağlantıyı ve kodu Kurulum'da gösterin.
- **Bitti sayılır:** böyle bir masaüstündeki kullanıcı o araca terminal olmadan giriş yapabildiğinde.

### Sesle iş akışı anlatmak
🔴 · [issue #10](https://github.com/tolgabuyuktanir/Mehteran/issues/10) · Gereken: Python, JavaScript.
"Anlat, oluşturayım" kutusunda (`mehteran/ui/editor.js` içindeki `#describe-box`) bir 🎤 düğmesi. Tarayıcı sesi kaydeder. Mehteran'ın kendi konuşmayı yazıya dökme aracı (whisper.cpp, `mehteran/speech.py`) sesi bu bilgisayarda yazıya döker. Metin kutuya gelir; kullanıcı okuyup düzeltir. Hiçbir şey bilgisayardan çıkmaz ve yapay zekâ kullanım hakkınızdan harcamaz.
- **Bitti sayılır:** düğme whisper.cpp kuruluyken çalıştığında ve kurulu değilken kurmayı önerdiğinde.
