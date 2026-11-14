// The language picker: a button that shows the chosen language (its flag and its own name) and opens a list to
// choose from, with a search field when the list is long. Used for the interface language (the header) and for the
// output language of a workflow (the run window, the editor).
//
//   LangPicker.create({languages, value, onChange, label, searchLabel, emptyText, otherName(code), id}) -> element
//     languages     entries of the language registry (GET /api/languages): {code, native, english, flag, dir}
//     otherName     the name of a language in the interface language, shown beside its own name and searched too
//     element.value / element.setValue(code) / element.setLanguages(list) / element.button
//
// A flag is a country's and a language is not: the flag only helps to find the row; the name is always written.
// The flags are files of this program (/flags/<country>.svg, from flag-icons, MIT): emoji flags do not show on
// Windows. Keys: Enter, Space or ↓ opens; typing searches; ↑ ↓ Home End move; Enter chooses; Esc closes.
"use strict";

const LangPicker = (() => {
  let seq = 0;
  let openPicker = null;

  function el(tag, attrs, ...children) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(attrs || {})) if (value != null && value !== false) node.setAttribute(key, value === true ? "" : value);
    for (const child of children) if (child != null) node.append(child);
    return node;
  }

  const flag = (lang) => el("img", {class: "flag", src: `/flags/${lang.flag}.svg`, alt: "", width: "20", height: "15", loading: "lazy"});
  const fold = (text) => String(text || "").toLocaleLowerCase("en").normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/ı/g, "i");

  function create(opts) {
    const uid = "lang-pick-" + (++seq);
    let languages = opts.languages || [];
    let value = opts.value || "";
    let shown = [], active = -1;
    const otherName = (lang) => (opts.otherName && opts.otherName(lang.code)) || lang.english;
    const button = el("button", {type: "button", class: "lang-pick-btn", "aria-haspopup": "listbox", "aria-expanded": "false", id: opts.id || null});
    const search = el("input", {type: "search", class: "lang-pick-search", role: "combobox", "aria-expanded": "true", "aria-controls": uid + "-list",
      "aria-autocomplete": "list", autocomplete: "off", spellcheck: "false", "aria-label": opts.searchLabel || "", placeholder: opts.searchLabel || ""});
    const list = el("ul", {class: "lang-pick-list", role: "listbox", id: uid + "-list", "aria-label": opts.label || ""});
    const empty = el("p", {class: "lang-pick-empty small muted", hidden: true}, opts.emptyText || "");
    const pop = el("div", {class: "lang-pick-pop", hidden: true}, search, list, empty);
    const root = el("span", {class: "lang-pick"}, button, pop);
    const find = (code) => languages.find((lang) => lang.code === code);

    function drawButton() {
      const lang = find(value);
      // The name in its own language and direction, whatever the page's direction is.
      button.replaceChildren(...(lang ? [flag(lang), el("span", {class: "lang-pick-name", lang: lang.code, dir: lang.dir}, lang.native)]
        : [el("span", {class: "lang-pick-name"}, value || "–")]), el("span", {class: "lang-pick-caret", "aria-hidden": "true"}, "▾"));
      button.setAttribute("aria-label", (opts.label ? opts.label + ": " : "") + (lang ? lang.native : value));
    }

    function drawList() {
      const query = fold(search.value.trim());
      shown = languages.filter((lang) => !query || [lang.native, lang.english, otherName(lang), lang.code].some((name) => fold(name).includes(query)));
      list.replaceChildren(...shown.map((lang, i) => {
        const other = otherName(lang);
        const item = el("li", {role: "option", id: `${uid}-${lang.code}`, "aria-selected": String(lang.code === value), "data-code": lang.code},
          flag(lang), el("span", {class: "lang-pick-name", lang: lang.code, dir: lang.dir}, lang.native),
          other && fold(other) !== fold(lang.native) ? el("span", {class: "lang-pick-other small muted"}, other) : null);
        item.addEventListener("click", () => choose(lang.code));
        item.addEventListener("pointermove", () => setActive(i, false));
        return item;
      }));
      empty.hidden = shown.length > 0;
      setActive(Math.max(0, shown.findIndex((lang) => lang.code === value)), true);
    }

    function setActive(i, scroll) {
      active = shown.length ? Math.max(0, Math.min(shown.length - 1, i)) : -1;
      [...list.children].forEach((item, k) => item.classList.toggle("active", k === active));
      if (active < 0) return search.removeAttribute("aria-activedescendant");
      search.setAttribute("aria-activedescendant", list.children[active].id);
      if (scroll) list.children[active].scrollIntoView({block: "nearest"});
    }

    // The list is placed against the window (position: fixed), so that a dialog's scrolling body does not cut it.
    function place() {
      const r = button.getBoundingClientRect();
      const width = Math.min(Math.max(r.width, 260), window.innerWidth - 16);
      const rtl = getComputedStyle(root).direction === "rtl";
      const left = Math.max(8, Math.min(window.innerWidth - width - 8, rtl ? r.right - width : r.left));
      const below = window.innerHeight - r.bottom - 12, above = r.top - 12;
      const up = below < 220 && above > below;
      pop.style.width = width + "px";
      pop.style.left = left + "px";
      pop.style.maxHeight = Math.max(140, Math.min(380, up ? above : below)) + "px";
      pop.style.top = up ? "" : r.bottom + 4 + "px";
      pop.style.bottom = up ? window.innerHeight - r.top + 4 + "px" : "";
    }

    function open() {
      if (openPicker && openPicker !== close) openPicker();
      openPicker = close;
      search.value = "";
      search.hidden = languages.length <= 8;  // a short list needs no search
      pop.hidden = false;
      button.setAttribute("aria-expanded", "true");
      place();
      drawList();
      (search.hidden ? list : search).focus({preventScroll: true});
      document.addEventListener("pointerdown", outside, true);
      window.addEventListener("resize", close);
      window.addEventListener("scroll", scrolled, true);
    }

    function close(refocus) {
      if (pop.hidden) return;
      pop.hidden = true;
      if (openPicker === close) openPicker = null;
      button.setAttribute("aria-expanded", "false");
      document.removeEventListener("pointerdown", outside, true);
      window.removeEventListener("resize", close);
      window.removeEventListener("scroll", scrolled, true);
      if (refocus === true) button.focus({preventScroll: true});
    }

    const outside = (e) => { if (!root.contains(e.target)) close(); };
    const scrolled = (e) => { if (!pop.contains(e.target)) close(); };

    function choose(code) {
      const changed = code !== value;
      value = code;
      drawButton();
      close(true);
      if (changed && opts.onChange) opts.onChange(code);
    }

    function keys(e) {
      if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); setActive(active + (e.key === "ArrowDown" ? 1 : -1), true); }
      else if (e.key === "Home" && e.target === list) { e.preventDefault(); setActive(0, true); }
      else if (e.key === "End" && e.target === list) { e.preventDefault(); setActive(shown.length - 1, true); }
      else if (e.key === "Enter" || (e.key === " " && e.target === list)) { e.preventDefault(); if (shown[active]) choose(shown[active].code); }
      else if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); close(true); }  // not the dialog around it
      else if (e.key === "Tab") close();
    }

    list.tabIndex = -1;
    button.addEventListener("click", () => (pop.hidden ? open() : close(true)));
    button.addEventListener("keydown", (e) => { if (e.key === "ArrowDown" && pop.hidden) { e.preventDefault(); open(); } });
    search.addEventListener("input", drawList);
    search.addEventListener("keydown", keys);
    list.addEventListener("keydown", keys);
    drawButton();

    Object.defineProperty(root, "value", {get: () => value});
    root.setValue = (code) => { value = code; drawButton(); };
    root.setLanguages = (items) => { languages = items; drawButton(); };
    root.button = button;
    return root;
  }

  return {create, flag};
})();
