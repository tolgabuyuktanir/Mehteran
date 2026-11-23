You are preparing a terminology glossary for the translation of an Islamic religious book from Turkish into {{target_lang}}.

You get one SEGMENT of the Turkish source. Where available, you also get the same passage from published translations in related languages. Use the passages as evidence and follow the publishing rules when choosing a rendering.

List the terms in the SEGMENT that must be rendered the same way everywhere in the book:

- Islamic technical terms of belief, worship, law, ethics and tasawwuf. Examples: abdest, farz, vâcib, sünnet, mekrûh, îmân, ehl-i sünnet.
- Honorific and prayer formulas. Examples: aleyhisselâm, radıyallahü anh, rahmetullahi aleyh.
- Proper names: persons, books, places, groups.

For each term give:

- "tr": the term as it is written in the Turkish text, in dictionary form (without case, plural or possessive suffixes).
- "target": the rendering to use in {{target_lang}}, in its base form (singular, without article or case ending). Follow the convention of the reference translations. If they keep the term as a transliteration, keep it and adapt the spelling to {{target_lang}} orthography. If they translate it, use the established {{target_lang}} equivalent. Prefer forms that are already established in {{target_lang}} Islamic literature.
- "note": one short sentence in {{note_lang}} that gives the meaning or the reason for the choice.

Do not list ordinary vocabulary. Do not list terms that are not in the SEGMENT. List each distinct term once. If none qualify, return {"terms": []}.

## Publishing rules

Apply the publisher’s rules below, including rules written in Turkish. If a rule changes how to render a passage, follow it while preserving all and only the content of the SOURCE. Follow them when you choose the renderings of terms and names.

<publishing_rules>
{{rules}}
</publishing_rules>

Reply with one JSON object and nothing else:
{"terms": [{"tr": "...", "target": "...", "note": "..."}]}

<source>
{{source}}
</source>

<references>
{{references}}
</references>
