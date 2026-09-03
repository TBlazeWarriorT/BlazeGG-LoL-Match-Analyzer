"""
Small safe CLI for editing src/locales/*.json without hand-rolled string
replacement (which is exactly what corrupted every locale file once already —
see git history). Always goes through json.load/json.dump, so the output is
guaranteed to be structurally valid JSON no matter what.

Usage:
  py scripts/i18n_tool.py set <lang|all> <key> <value>
      Sets one key in one locale (by code, e.g. pt_BR) or in every locale file
      at once (lang = "all"). Creates the key if it doesn't exist yet.

  py scripts/i18n_tool.py delete <lang|all> <key>
      Removes one key from one locale, or from every locale file at once.

  py scripts/i18n_tool.py status
      Prints, for every non-English locale, how many of en_US's keys it has
      (as a %) and lists exactly which keys are missing.

Examples:
  py scripts/i18n_tool.py set pt_BR btn_view_cached "Ver tudo do cache"
  py scripts/i18n_tool.py set all btn_view_cached "View all cached"
  py scripts/i18n_tool.py delete all old_unused_key
  py scripts/i18n_tool.py status
"""
import json
import sys
from pathlib import Path

LOCALES_DIR = Path(__file__).resolve().parent.parent / "src" / "locales"
REFERENCE_LANG = "en_US"


def load_locale(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_locale(path: Path, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def all_locale_files():
    return sorted(LOCALES_DIR.glob("*.json"))


def cmd_set(lang: str, key: str, value: str) -> None:
    if lang.lower() == "all":
        targets = all_locale_files()
    else:
        target = LOCALES_DIR / f"{lang}.json"
        if not target.exists():
            print(f"Locale file not found: {target}")
            sys.exit(1)
        targets = [target]

    for path in targets:
        data = load_locale(path)
        was_new = key not in data
        data[key] = value
        save_locale(path, data)
        tag = "added" if was_new else "updated"
        print(f"{path.stem}: {tag} '{key}'")


def cmd_delete(lang: str, key: str) -> None:
    if lang.lower() == "all":
        targets = all_locale_files()
    else:
        target = LOCALES_DIR / f"{lang}.json"
        if not target.exists():
            print(f"Locale file not found: {target}")
            sys.exit(1)
        targets = [target]

    for path in targets:
        data = load_locale(path)
        if key in data:
            del data[key]
            save_locale(path, data)
            print(f"{path.stem}: removed '{key}'")
        else:
            print(f"{path.stem}: '{key}' not present, nothing to do")


def cmd_status() -> None:
    ref_path = LOCALES_DIR / f"{REFERENCE_LANG}.json"
    ref = load_locale(ref_path)
    ref_keys = set(ref.keys())
    print(f"{REFERENCE_LANG} (reference): {len(ref_keys)} keys\n")

    for path in all_locale_files():
        if path.stem == REFERENCE_LANG:
            continue
        data = load_locale(path)
        keys = set(data.keys())
        missing = sorted(ref_keys - keys)
        extra = sorted(keys - ref_keys)
        pct = 100.0 * (len(ref_keys) - len(missing)) / len(ref_keys) if ref_keys else 100.0
        print(f"{path.stem}: {pct:.1f}% complete ({len(ref_keys) - len(missing)}/{len(ref_keys)})")
        if missing:
            print(f"   missing ({len(missing)}): {missing}")
        if extra:
            print(f"   extra, not in {REFERENCE_LANG} ({len(extra)}): {extra}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "set":
        if len(sys.argv) != 5:
            print("Usage: py scripts/i18n_tool.py set <lang|all> <key> <value>")
            sys.exit(1)
        cmd_set(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == "delete":
        if len(sys.argv) != 4:
            print("Usage: py scripts/i18n_tool.py delete <lang|all> <key>")
            sys.exit(1)
        cmd_delete(sys.argv[2], sys.argv[3])
    elif cmd == "status":
        cmd_status()
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
