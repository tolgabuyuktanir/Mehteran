// Mehteran's web site: the language switch (English / Türkçe), the small-screen menu and, on the docs page,
// the table of contents with its search. No framework and nothing loaded from other servers.
(function () {
  "use strict";
  var KEY = "mehteran.site.lang";
  var root = document.documentElement;

  function stored() { try { return localStorage.getItem(KEY); } catch (e) { return null; } }
  function store(lang) { try { localStorage.setItem(KEY, lang); } catch (e) { /* private window: the choice lasts for this page */ } }

  // ?lang=tr in a link wins, then the visitor's earlier choice, then the browser's language.
  function initialLang() {
    var asked = new URLSearchParams(location.search).get("lang");
    if (asked === "tr" || asked === "en") return asked;
    var saved = stored();
    if (saved === "tr" || saved === "en") return saved;
    return (navigator.language || "").toLowerCase().indexOf("tr") === 0 ? "tr" : "en";
  }

  function setLang(lang, remember) {
    root.lang = lang;
    var title = document.querySelector('meta[name="title-' + lang + '"]');
    if (title) document.title = title.content;
    var desc = document.querySelector('meta[name="description-' + lang + '"]');
    var meta = document.querySelector('meta[name="description"]');
    if (desc && meta) meta.content = desc.content;
    document.querySelectorAll(".lang button").forEach(function (b) { b.setAttribute("aria-pressed", String(b.dataset.set === lang)); });
    document.querySelectorAll("[data-ph-" + lang + "]").forEach(function (el) { el.placeholder = el.getAttribute("data-ph-" + lang); });
    if (remember) store(lang);
    if (window.MehteranDocs) window.MehteranDocs.refresh();
  }

  document.addEventListener("click", function (ev) {
    var b = ev.target.closest(".lang button");
    if (b) setLang(b.dataset.set, true);
    var m = ev.target.closest(".menu-toggle");
    if (m) {
      var top = m.closest(".top");
      top.classList.toggle("open");
      m.setAttribute("aria-expanded", String(top.classList.contains("open")));
    } else if (ev.target.closest(".nav a")) {
      var t = document.querySelector(".top.open");
      if (t) t.classList.remove("open");
    }
  });

  // --- docs page: contents, search, the section in view ---------------------------------------------------
  var toc = document.querySelector(".toc ol");
  if (toc) {
    var search = document.querySelector(".toc .search");
    var observer = null;

    var article = function () { return document.querySelector('.prose[data-l="' + root.lang + '"]'); };

    var fold = function (s) {
      return s.toLocaleLowerCase(root.lang === "tr" ? "tr" : "en").normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/ı/g, "i");
    };

    var build = function () {
      var art = article();
      toc.textContent = "";
      if (observer) observer.disconnect();
      if (!art) return;
      var links = {};
      art.querySelectorAll("section[id]").forEach(function (sec) {
        var h = sec.querySelector("h2");
        if (!h) return;
        var li = document.createElement("li");
        var a = document.createElement("a");
        a.href = "#" + sec.id;
        a.textContent = h.textContent;
        li.appendChild(a);
        toc.appendChild(li);
        links[sec.id] = a;
      });
      if ("IntersectionObserver" in window) {
        observer = new IntersectionObserver(function (entries) {
          entries.forEach(function (e) {
            if (!e.isIntersecting) return;
            Object.keys(links).forEach(function (id) { links[id].classList.toggle("on", id === e.target.id); });
          });
        }, {rootMargin: "-90px 0px -70% 0px"});
        art.querySelectorAll("section[id]").forEach(function (sec) { observer.observe(sec); });
      }
      filter();
    };

    // The search hides the sections that do not contain every word typed (case and accents ignored).
    var filter = function () {
      var art = article();
      if (!art) return;
      var words = fold(search.value.trim()).split(/\s+/).filter(Boolean);
      var shown = 0;
      art.querySelectorAll("section[id]").forEach(function (sec) {
        var text = fold(sec.textContent);
        var ok = words.every(function (w) { return text.indexOf(w) !== -1; });
        sec.hidden = !ok;
        var a = toc.querySelector('a[href="#' + sec.id + '"]');
        if (a) a.parentNode.hidden = !ok;
        if (ok) shown += 1;
      });
      var none = art.querySelector(".empty-search");
      if (none) none.hidden = shown > 0;
    };

    // The contents are open beside the text and folded above it (a narrow screen); a chosen section folds them again.
    var list = document.querySelector(".toc-list");
    var narrow = window.matchMedia("(max-width: 900px)");
    var fit = function () { list.open = !narrow.matches; };
    if (narrow.addEventListener) narrow.addEventListener("change", fit);
    fit();
    toc.addEventListener("click", function (ev) { if (narrow.matches && ev.target.closest("a")) list.open = false; });

    search.addEventListener("input", function () { if (search.value.trim()) list.open = true; filter(); });
    search.addEventListener("keydown", function (ev) { if (ev.key === "Escape") { search.value = ""; filter(); } });
    document.addEventListener("keydown", function (ev) {
      if (ev.key === "/" && document.activeElement !== search && !/input|textarea/i.test(document.activeElement.tagName)) {
        ev.preventDefault();
        search.focus();
      }
    });
    window.MehteranDocs = {refresh: build};
  }

  setLang(initialLang(), false);
})();
