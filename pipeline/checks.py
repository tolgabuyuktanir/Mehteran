"""Mechanical checks that use no LLM. Their results go into the report as warnings."""

from __future__ import annotations

import re
import statistics
from collections import Counter

from .i18n import t

_AR = r"[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]"
_ARABIC_RUN = re.compile(rf"{_AR}+(?:\s+{_AR}+)*")
_ARABIC_CHAR = re.compile(_AR)
_FOOTNOTE = re.compile(r"\[\^\d+\]")
_NOTE_MARK = re.compile(r"\[\^(\d+)\](?!:)")
_NOTE_DEF = re.compile(r"^\[\^(\d+)\]:", re.M)
_SENTENCE_END = re.compile(r"[.!?…。！？؟](?=\s|$|[\"'”’»)\]])")


def _numbers(text: str) -> Counter:
    return Counter(re.findall(r"\d+", _FOOTNOTE.sub("", text)))


def _blocks(text: str) -> list[str]:
    return [b for b in re.split(r"\n\s*\n", text) if b.strip()]


def _headings(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.startswith("#"))


def _sentences(text: str) -> int:
    return len(_SENTENCE_END.findall(text))


def completeness_problems(source: str, answer: str, previous: str | None = None) -> list[str]:
    """Reasons to reject a model's text before it goes to the next stage. Empty list: the answer is acceptable.

    source: the Turkish segment. previous: the text the model was asked to correct (revision stages); None for the
    first translation. Rules: same paragraphs and footnote marks as the source; for corrections, the text must not
    shrink noticeably; no single long paragraph may lose a large part of its text (a dropped sentence).
    """
    problems = []
    src_blocks, out_blocks = _blocks(source), _blocks(answer)
    if len(src_blocks) != len(out_blocks):
        problems.append(t("gate_paragraphs", source=len(src_blocks), answer=len(out_blocks)))
    if Counter(_FOOTNOTE.findall(source)) != Counter(_FOOTNOTE.findall(answer)):
        problems.append(t("gate_footnotes"))
    if previous is not None:
        prev_blocks = _blocks(previous)
        if len(answer) < 0.85 * len(previous):
            problems.append(t("gate_shrunk", percent=round(100 * (1 - len(answer) / len(previous)))))
        if len(prev_blocks) == len(out_blocks):
            for n, (before, after) in enumerate(zip(prev_blocks, out_blocks), 1):
                if len(before) >= 200 and len(after) < 0.7 * len(before):
                    problems.append(t("gate_paragraph_shrunk", n=n))
                    break
    elif len(src_blocks) == len(out_blocks):
        ratios = [(n, len(b) / len(a)) for n, (a, b) in enumerate(zip(src_blocks, out_blocks), 1) if len(a) >= 200]
        if len(ratios) >= 2:
            median = statistics.median(r for _, r in ratios)
            short = [n for n, r in ratios if r < 0.5 * median]
            if short:
                problems.append(t("gate_paragraph_short", n=short[0]))
    return problems


def _words(text: str) -> str:
    return " ".join(re.findall(r"\w+", str(text).lower()))


def coverage_problems(translation: str, checked) -> list[str]:
    """Checks a reviewer's proof that it read the whole translation. Empty list: the proof is acceptable.

    checked: one entry per paragraph of the translation, in order, each holding the last words of that paragraph.
    An empty findings list is only believable with this proof: without it, "no problems" and "did not look" are
    the same answer. One copying mistake (or one in ten paragraphs) is tolerated.
    """
    blocks = _blocks(translation)
    if not isinstance(checked, list) or len(checked) != len(blocks):
        got = len(checked) if isinstance(checked, list) else 0
        return [t("gate_checked_count", expected=len(blocks), got=got)]
    misses = [n for n, (block, end) in enumerate(zip(blocks, checked), 1) if not _words(end) or _words(end) not in _words(block)]
    if len(misses) > max(1, len(blocks) // 10):
        return [t("gate_checked_wrong", paragraphs=", ".join(map(str, misses[:5])))]
    return []


def check_segment(source: str, translation: str) -> list[str]:
    """Compares a Turkish segment with its translation; returns warning sentences."""
    warnings = []

    # Unless the target language uses Arabic script, Arabic-script passages of the source must appear unchanged.
    letters = sum(ch.isalpha() for ch in translation) or 1
    if len(_ARABIC_CHAR.findall(translation)) / letters < 0.3:
        flat = " ".join(translation.split())
        missing = [run for run in _ARABIC_RUN.findall(source) if " ".join(run.split()) not in flat]
        if missing:
            warnings.append(t("check_arabic_missing", count=len(missing), sample=" | ".join(missing[:3])))

    src, tr = _numbers(source), _numbers(translation)
    if src - tr:
        warnings.append(t("check_numbers_missing", numbers=", ".join(sorted((src - tr).elements()))))
    if tr - src:
        warnings.append(t("check_numbers_extra", numbers=", ".join(sorted((tr - src).elements()))))

    if Counter(_FOOTNOTE.findall(source)) != Counter(_FOOTNOTE.findall(translation)):
        warnings.append(t("check_footnotes"))

    marks, defs = set(_NOTE_MARK.findall(translation)), set(_NOTE_DEF.findall(translation))
    if marks != defs:
        warnings.append(t("check_note_pairs", numbers=", ".join(sorted(marks ^ defs, key=int))))

    src_blocks, out_blocks = _blocks(source), _blocks(translation)
    a, b = len(src_blocks), len(out_blocks)
    if a != b:
        warnings.append(t("check_paragraphs", source=a, translation=b))
    else:
        # A paragraph with clearly fewer sentences than its source probably lost a sentence.
        fewer = [n for n, (x, y) in enumerate(zip(src_blocks, out_blocks), 1)
                 if _sentences(x) >= 3 and _sentences(y) < 0.7 * _sentences(x)]
        if fewer:
            warnings.append(t("check_sentences", paragraphs=", ".join(map(str, fewer[:5]))))

    a, b = _headings(source), _headings(translation)
    if a != b:
        warnings.append(t("check_headings", source=a, translation=b))

    return warnings


def length_outliers(lengths: dict[str, tuple[int, int]]) -> dict[str, str]:
    """Finds segments whose translation/source length ratio differs clearly from the book's median.

    lengths: {segment: (source length, translation length)}
    """
    ratios = {sid: tr / src for sid, (src, tr) in lengths.items() if src >= 500}
    if len(ratios) < 5:
        return {}
    median = statistics.median(ratios.values())
    out = {}
    for sid, ratio in ratios.items():
        if ratio < 0.75 * median:
            out[sid] = t("check_too_short", ratio=f"{ratio:.2f}", median=f"{median:.2f}")
        elif ratio > 1.35 * median:
            out[sid] = t("check_too_long", ratio=f"{ratio:.2f}", median=f"{median:.2f}")
    return out
