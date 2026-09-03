# Notes for Claude Code sessions on this repo

## Editing translation files (src/locales/*.json)

**Always use `scripts/i18n_tool.py` — never hand-edit or script raw string
replacement on these files.** It goes through `json.load`/`json.dump`, so the
output is always structurally valid JSON no matter what.

```
py scripts/i18n_tool.py set <lang|all> <key> <value>   # add/update a key
py scripts/i18n_tool.py delete <lang|all> <key>         # remove a key
py scripts/i18n_tool.py status                          # % complete + missing keys per locale
```

Why this rule exists: a one-off `content.replace(...)` script (meant to be a
no-op guard) accidentally matched a substring that exists in every locale
file's structure and replaced it with the *entire file's own content* —
duplicating all 11 locale files in place. It was only caught because the
resulting JSON diffs were huge and `json.load` failed. `git checkout` fixed
it, but a version of this script that used `json.load`/`json.dump` from the
start would never have been able to produce invalid JSON in the first place.
Manual placeholder-value edits (e.g. fixing an invented example string) are
fine via the normal Edit tool for one-off single-line changes — but for
anything touching more than one locale, or a repeated pattern across files,
use the tool instead of a throwaway script.

Shared, non-translatable example values (the "Hide on bush#KR1" search
example, the "KR_8326219860" match ID example) live in `SHARED_EXAMPLES` in
`src/i18n.py` and are injected into every `get_text()` call automatically.
Locale strings should reference them as `{example_name}` / `{example_tag}` /
`{example_match_id}` rather than hardcoding their own copy of the value.

Don't put styling (`<span style='...'>`) inside translation strings — the
CSS/color is the same regardless of language, so it belongs in the Python
call site (wrap the `get_text(...)` result), not duplicated across 11 files.
