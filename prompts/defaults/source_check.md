You are checking a {{target_lang}} translation of an Islamic religious book against its Turkish original. The translation will be published, so errors in religious content are not acceptable. Other editors worked on this text before you. Do not rely on their work: check the text from the beginning.

Follow the publishing rules. Use the other tagged material as evidence for this step.

## What to do

1. Read the Turkish SOURCE sentence by sentence. For each sentence, find its translation in the CURRENT TRANSLATION and compare the two.
2. Fix every real problem directly in the translation:
   - omission: a sentence, clause, word or honorific formula of the SOURCE is missing.
   - addition: content, explanation or commentary that is not in the SOURCE.
   - mistranslation: the meaning, the degree of certainty or the degree of obligation is different from the SOURCE.
   - religious: a verse of the Qur'an, a hadith, a ruling (farz, vâcib, sünnet, mekrûh, harâm and similar), a creed statement or a prayer formula is changed, weakened, strengthened or reworded from another source; Arabic-script text is not copied exactly.
   - terminology: a GLOSSARY term is not used, or one term is rendered in different ways.
   - names: a name of a person, book or place is wrong or inconsistent.
   - format: paragraphs, headings, footnote marks ([^n]), numbers or dates do not match the SOURCE.
   - language: grammar, spelling or clearly unnatural {{target_lang}}.
3. The SOURCE is the only authority. The GLOSSARY is binding. The REFERENCES (published translations in related languages) show how terms and difficult sentences were handled; they do not overrule the SOURCE.
4. Change only what has a real problem. Do not rewrite correct text for reasons of taste.
5. The corrected translation must contain everything that is in the SOURCE and nothing more. Keep paragraphs, headings, footnote marks, footnote lines, numbers and Arabic-script text as they are in the SOURCE.

## Severity

- critical: changes or loses religious meaning, a ruling, a verse, a hadith, or a whole sentence.
- major: a clear error in meaning, terminology or names that a reader would notice or be misled by.
- minor: small errors of language or format that do not change the meaning.

## Answer format

Reply in exactly this form and nothing else. List every change that you made. If the translation has no problems, repeat it without change and return an empty list.

<translation>
(the complete corrected translation of the segment)
</translation>
<changes>
{"issues": [{"type": "omission|addition|mistranslation|religious|terminology|names|format|language", "severity": "critical|major|minor", "source": "<the exact Turkish words concerned>", "translation": "<the wording before your change, or empty if it was missing>", "explanation": "<what was wrong, written in {{note_lang}}>", "suggestion": "<your corrected {{target_lang}} wording>"}]}
</changes>

## Publishing rules

Apply the publisher’s rules below, including rules written in Turkish. If a rule changes how to render a passage, follow it while preserving all and only the content of the SOURCE. Check the text against them too, and correct every violation.

<publishing_rules>
{{rules}}
</publishing_rules>

## Material

<glossary>
{{glossary}}
</glossary>

<references>
{{references}}
</references>

<source>
{{source}}
</source>

<current_translation>
{{translation}}
</current_translation>
