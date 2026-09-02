#!/usr/bin/env python3
"""
i18n String Length Expansion Auditor
Checks translation strings against the English (en_US) baseline to detect potential UI overflow risks.
"""

import sys
import argparse
from pathlib import Path

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.i18n import LANGUAGES, SUPPORTED_LANGUAGES

# Keys that are naturally long text (errors, full descriptions, modals) and can be excluded in UI mode
NON_UI_PREFIXES = (
    "err_",
    "confirm_",
    "modal_",
    "del_summoner_prompt",
    "close_summoner_prompt",
    "key_exp_label",
    "app_sub",
    "search_game_name_ph",
    "search_match_id_ph",
    "raw_summary_title",
)

def audit_language(
    target_lang: str,
    threshold_pct: float = 50.0,
    min_diff_chars: int = 8,
    category: str = "ui"
):
    en_dict = LANGUAGES.get("en_US", {})
    target_dict = LANGUAGES.get(target_lang, {})

    if not target_dict:
        print(f"Error: Language '{target_lang}' not found in i18n dictionaries.")
        return []

    warnings = []
    for key, en_val in en_dict.items():
        if category == "ui" and any(key.startswith(p) for p in NON_UI_PREFIXES):
            continue

        target_val = target_dict.get(key, "")
        if not target_val:
            continue

        len_en = len(en_val)
        len_tgt = len(target_val)
        diff = len_tgt - len_en

        if len_en > 0 and diff >= min_diff_chars:
            pct = (diff / len_en) * 100.0
            if pct >= threshold_pct:
                warnings.append({
                    "key": key,
                    "en_val": en_val,
                    "tgt_val": target_val,
                    "len_en": len_en,
                    "len_tgt": len_tgt,
                    "diff": diff,
                    "pct": round(pct, 1)
                })

    # Sort by percentage descending
    warnings.sort(key=lambda x: x["pct"], reverse=True)
    return warnings

def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    parser = argparse.ArgumentParser(description="Audit i18n string expansion against en_US baseline.")
    parser.add_argument("-l", "--lang", default="all", help="Target language code (e.g. de_DE, pl_PL) or 'all' (default)")
    parser.add_argument("-t", "--threshold", type=float, default=50.0, help="Percentage length increase threshold (default: 50.0%)")
    parser.add_argument("-d", "--min-diff", type=int, default=8, help="Minimum character difference to trigger warning (default: 8)")
    parser.add_argument("-c", "--category", choices=["ui", "all"], default="ui", help="String scope: 'ui' (compact pills/buttons/labels) or 'all' (default: ui)")

    args = parser.parse_args()

    langs_to_check = (
        [k for k in SUPPORTED_LANGUAGES.keys() if k != "en_US"]
        if args.lang.lower() == "all"
        else [args.lang]
    )

    print("=" * 95)
    print(f"🔍 i18n Length Expansion Audit (Baseline: en_US | Scope: {args.category.upper()} | Threshold: +{args.threshold}% & +{args.min_diff} chars)")
    print("=" * 95)

    total_warnings = 0
    for lang in langs_to_check:
        lang_info = SUPPORTED_LANGUAGES.get(lang, {"name": lang, "short": lang})
        warnings = audit_language(
            lang,
            threshold_pct=args.threshold,
            min_diff_chars=args.min_diff,
            category=args.category
        )
        total_warnings += len(warnings)

        print(f"\n🌐 {lang} - {lang_info['name']} ({len(warnings)} potential overflows):")
        if not warnings:
            print("   ✅ No string expansion warnings found.")
            continue

        short_hdr = f"{lang_info['short']} (len)"
        print(f"   {'KEY':<24} | {'EN (len)':<22} | {short_hdr:<30} | {'EXPANSION'}")
        print("   " + "-" * 90)
        for w in warnings:
            en_txt = w['en_val'] if len(w['en_val']) <= 18 else w['en_val'][:16] + '...'
            tgt_txt = w['tgt_val'] if len(w['tgt_val']) <= 24 else w['tgt_val'][:22] + '...'
            en_str = f'"{en_txt}" ({w["len_en"]})'
            tgt_str = f'"{tgt_txt}" ({w["len_tgt"]})'
            pct_str = f"+{w['diff']} chars (+{w['pct']}%)"
            print(f"   {w['key']:<24} | {en_str:<22} | {tgt_str:<30} | ⚠️  {pct_str}")

    print("\n" + "=" * 95)
    print(f"Summary: {total_warnings} total expansion warnings found across {len(langs_to_check)} language(s).")
    print("=" * 95)

if __name__ == "__main__":
    main()
