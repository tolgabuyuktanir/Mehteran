"""Checks that an uploaded reference is what it should be: a translation of the same book, in the chosen language.

The checks need no model. They read signals that survive translation:
- Arabic phrases (âyat, hadîths, prayers) and numbers (sûra and verse numbers, hadîth numbers, years) stay the
  same in every translation of the book. Few of them in the reference: probably another book.
- The alphabet of the text: Danish is written in Latin letters, Russian in Cyrillic letters, Urdu in Arabic letters.
- Turkish function words: a reference that is full of them is the Turkish book itself.
- The length: a translation is about as long as its source.
Each problem is a warning for the user, not an error: a reference can be partial, and a rule can be wrong.
"""

from __future__ import annotations

import re
import unicodedata

# The alphabet of each language that does not use Latin letters.
SCRIPTS = {
    "arabic": {"ar", "fa", "ur", "ps", "sd", "ug", "ckb", "dv"},
    "cyrillic": {"ru", "uk", "bg", "mk", "be", "kk", "ky", "tg", "mn", "ba", "tt", "cv", "ce"},
    "greek": {"el"}, "hebrew": {"he", "yi"}, "georgian": {"ka"}, "armenian": {"hy"},
    "devanagari": {"hi", "mr", "ne"}, "bengali": {"bn"}, "thai": {"th"},
    "cjk": {"zh", "ja", "ko"},
}
# Unicode name prefixes of the letters of each alphabet.
_SCRIPT_OF_NAME = {"LATIN": "latin", "CYRILLIC": "cyrillic", "ARABIC": "arabic", "GREEK": "greek", "HEBREW": "hebrew",
                   "GEORGIAN": "georgian", "ARMENIAN": "armenian", "DEVANAGARI": "devanagari", "BENGALI": "bengali",
                   "THAI": "thai", "CJK": "cjk", "HIRAGANA": "cjk", "KATAKANA": "cjk", "HANGUL": "cjk"}
# Frequent Turkish words that no other language of these books uses as often ("de" and "da" are Danish words too).
TURKISH_WORDS = {"ve", "bir", "bu", "ile", "için", "olan", "gibi", "daha", "çok", "ki", "olarak", "sonra", "kadar",
                 "ise", "değil", "olur", "veya", "ancak", "şey", "diye", "buyurdu", "olduğu", "şöyle"}
_WORD = re.compile(r"\w+", re.UNICODE)
_ARABIC_WORD = re.compile(r"[ء-يٱ-ۓ]{2,}")
_ARABIC_MARKS = re.compile(r"[ً-ٰٟۖ-ۭ]")
_NUMBER = re.compile(r"(?<!\d)\d{2,}(?!\d)")

MIN_ANCHORS = 6        # a reference with fewer Arabic words and numbers than this: the book check says nothing
SAME_BOOK = 0.35       # share of the reference's Arabic words and numbers that the source of the same book contains
TURKISH_SHARE = 0.04   # share of Turkish function words above which a text is Turkish (Turkish prose: about 0.08)
SHORT, LONG = 0.4, 2.5  # length of the reference compared with the source


def script_counts(text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for ch in text:
        if ch.isalpha():
            script = _SCRIPT_OF_NAME.get(unicodedata.name(ch, "").split(" ")[0], "other")
            counts[script] = counts.get(script, 0) + 1
    return counts


def script_of(text: str) -> str:
    """The alphabet of the text. Arabic letters count only when they are most of the text: Islamic books quote
    Arabic in any language."""
    counts = script_counts(text)
    if counts.get("arabic", 0) > sum(counts.values()) / 2:
        return "arabic"
    counts.pop("arabic", None)
    return max(counts, key=counts.get) if counts else "arabic"


def expected_script(lang: str) -> str:
    base = lang.split("-")[0].lower()
    return next((script for script, langs in SCRIPTS.items() if base in langs), "latin")


def anchors(text: str) -> set[str]:
    """The Arabic words (without vowel signs) and the numbers of a text."""
    plain = _ARABIC_MARKS.sub("", text)
    return set(_ARABIC_WORD.findall(plain)) | set(_NUMBER.findall(text))


def turkish_share(text: str) -> float:
    words = [w.lower() for w in _WORD.findall(text) if not w.isdigit()]
    return sum(1 for w in words if w in TURKISH_WORDS) / len(words) if words else 0.0


def problems(source: str, reference: str, lang: str) -> list[tuple[str, dict]]:
    """The warnings for a reference in the language lang: (message key, values). source may be "" (not uploaded)."""
    out: list[tuple[str, dict]] = []
    if turkish_share(reference) >= TURKISH_SHARE:
        return [("ref_looks_turkish", {})]  # the other checks say nothing more about a Turkish text
    expected, found = expected_script(lang), script_of(reference)
    if found != expected:
        out.append(("ref_wrong_script", {"found": found, "expected": expected}))
    if not source:
        return out
    # Measured from the reference: a translation of a part of the book still finds its Arabic words and numbers in
    # the source; another book does not.
    found_anchors, wanted = anchors(reference), anchors(source)
    if not _ARABIC_WORD.search(reference):  # some translations leave the Arabic text out: only the numbers count
        wanted = set(_NUMBER.findall(source))
    ratio = len(reference) / max(len(source), 1)
    if len(found_anchors) >= MIN_ANCHORS:
        share = len(found_anchors & wanted) / len(found_anchors)
    elif len(wanted) * min(ratio, 1) >= MIN_ANCHORS:
        # The source has many and the reference is long enough to carry them, but it has almost none.
        share = len(found_anchors & wanted) / (len(wanted) * min(ratio, 1))
    else:
        share = 1.0  # too few signals to say anything
    if share < SAME_BOOK:
        out.append(("ref_not_same_book", {"percent": round(share * 100)}))
        return out  # the length of another book says nothing
    if ratio < SHORT:
        out.append(("ref_too_short", {"percent": round(ratio * 100)}))
    elif ratio > LONG:
        out.append(("ref_too_long", {"times": f"{ratio:.1f}"}))
    return out
