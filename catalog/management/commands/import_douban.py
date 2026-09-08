"""
Django management command: import Douban "watched" records into the catalog.

Two stages, matching the "match report first, commit later" plan:

  Stage 1 (match) — search TMDB for each title, write a CSV report. NO DB writes.
    python manage.py import_douban match douban_watched.json --out match_report.csv

  Stage 2 (commit) — read the (possibly hand-edited) report, create Catalog + Review.
    python manage.py import_douban commit match_report.csv --user <username>

Place this file at:  <app>/management/commands/import_douban.py
(e.g. catalog/management/commands/import_douban.py) and make sure both
`management/` and `management/commands/` contain an empty __init__.py .

Adjust the two import lines below to match where your code actually lives.
"""

import csv
import json
import os
import re
import time
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from catalog import clients  # module holding _tmdb_get

# --- adjust these imports to your project layout -------------------------------
from catalog.models import Catalog
from catalog.services import get_or_create_work  # your central persistence fn
from reviews.models import Review

# ------------------------------------------------------------------------------

User = get_user_model()

# File cache so a crashed `match` run can resume (LocMemCache can't: the process
# dies at end of the command and takes the cache with it).
CACHE_DIR = ".douban_import_cache"
SEARCH_CACHE = os.path.join(CACHE_DIR, "search_cache.json")

RATE_LIMIT_SECONDS = 0.25  # be polite to TMDB; ~5 min for 1275 titles


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _norm(s):
    """Normalize a title for comparison: lowercase, strip spaces/punctuation."""
    if not s:
        return ""
    s = s.lower().strip()
    s = re.sub(r'[\s\-_:：,，.。!！?？\'"·・()（）\[\]]', "", s)
    return s


def _load_cache():
    if os.path.exists(SEARCH_CACHE):
        with open(SEARCH_CACHE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_cache(cache):
    os.makedirs(CACHE_DIR, exist_ok=True)
    tmp = SEARCH_CACHE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False)
    os.replace(tmp, SEARCH_CACHE)  # atomic, won't corrupt on Ctrl-C mid-write


def _tmdb_multi_search(query):
    """Return list of movie/tv candidates (person results dropped)."""
    data = clients._tmdb_get("/search/multi", {"query": query})
    if not data:
        return []
    out = []
    for r in data.get("results", []):
        mt = r.get("media_type")
        if mt not in ("movie", "tv"):
            continue
        out.append(
            {
                "tmdb_id": r.get("id"),
                "media_type": mt,
                "title": r.get("title") or r.get("name") or "",
                "original_title": r.get("original_title")
                or r.get("original_name")
                or "",
                "popularity": r.get("popularity") or 0,
                "year": (r.get("release_date") or r.get("first_air_date") or "")[:4],
            }
        )
    return out


def _score(entry, candidate):
    """
    Confidence without a year to disambiguate:
      high   — exact normalized match on any douban title vs any candidate title
      medium — this is the top (most popular) candidate but no exact string match
      low    — matched only weakly / many candidates
    """
    douban_titles = {_norm(entry["title_original"]), _norm(entry["title_zh"])}
    douban_titles.discard("")
    cand_titles = {_norm(candidate["title"]), _norm(candidate["original_title"])}
    cand_titles.discard("")

    if douban_titles & cand_titles:
        return "high"
    return "medium"


def _pick(entry, candidates):
    """Choose the best candidate + a confidence label."""
    if not candidates:
        return None, "nomatch"

    # exact-match candidate wins regardless of popularity
    for c in candidates:
        if _score(entry, c) == "high":
            return c, "high"

    # otherwise the most popular result, flagged for review
    top = max(candidates, key=lambda c: c["popularity"])
    label = "review" if len(candidates) > 1 else "medium"
    return top, label


MEDIA_TYPE_MAP = {
    "movie": Catalog.MediaType.MOVIE,
    "tv": Catalog.MediaType.TV,
}


# ---------------------------------------------------------------------------
# command
# ---------------------------------------------------------------------------


class Command(BaseCommand):
    help = "Import Douban watched records (two stages: match | commit)."

    def add_arguments(self, parser):
        parser.add_argument("action", choices=["match", "commit"])
        parser.add_argument("infile", help="input json (match) or csv report (commit)")
        parser.add_argument(
            "--out",
            default="match_report.csv",
            help="output CSV path for the match stage",
        )
        parser.add_argument(
            "--user", help="username to attach reviews to (commit stage)"
        )

    def handle(self, *args, **opts):
        if opts["action"] == "match":
            self._match(opts["infile"], opts["out"])
        else:
            self._commit(opts["infile"], opts["user"])

    # ---- stage 1 -----------------------------------------------------------
    def _match(self, infile, outfile):
        with open(infile, encoding="utf-8") as f:
            entries = json.load(f)

        cache = _load_cache()
        rows = []
        for i, e in enumerate(entries, 1):
            key = e["douban_id"]
            if key in cache:
                candidates = cache[key]
            else:
                candidates = _tmdb_multi_search(e["search_title"])
                cache[key] = candidates
                time.sleep(RATE_LIMIT_SECONDS)
                if i % 25 == 0:
                    _save_cache(cache)
                    self.stdout.write(f"  searched {i}/{len(entries)}")

            best, status = _pick(e, candidates)

            # short note listing top alternatives, to help manual review
            note = " | ".join(
                f"{c['title']}({c['media_type']},{c['year']},id={c['tmdb_id']})"
                for c in sorted(candidates, key=lambda c: -c["popularity"])[:3]
            )

            rows.append(
                {
                    "douban_id": e["douban_id"],
                    "title_zh": e["title_zh"],
                    "title_original": e["title_original"],
                    "rating": "" if e["rating"] is None else e["rating"],
                    "watched_date": e["watched_date"],
                    "tmdb_id": best["tmdb_id"] if best else "",
                    "tmdb_media_type": best["media_type"] if best else "",
                    "tmdb_title": best["title"] if best else "",
                    "status": status,  # high/medium/review/nomatch  -> edit to ok/skip
                    "candidates": note,
                }
            )

        _save_cache(cache)

        fieldnames = [
            "douban_id",
            "title_zh",
            "title_original",
            "rating",
            "watched_date",
            "tmdb_id",
            "tmdb_media_type",
            "tmdb_title",
            "status",
            "candidates",
        ]
        with open(outfile, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)

        # summary
        from collections import Counter

        by_status = Counter(r["status"] for r in rows)
        self.stdout.write(self.style.SUCCESS(f"\nwrote {outfile} ({len(rows)} rows)"))
        for k, v in by_status.items():
            self.stdout.write(f"  {k}: {v}")
        self.stdout.write(
            "\nNext: open the CSV. Rows with status 'high' import automatically. "
            "For 'review'/'medium'/'nomatch', verify tmdb_id + tmdb_media_type, then "
            "set status to 'ok' to approve or 'skip' to exclude. Then run `commit`."
        )

    # ---- stage 2 -----------------------------------------------------------
    def _commit(self, infile, username):
        if not username:
            raise CommandError("--user is required for commit")
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"no such user: {username}")

        review_has_watched = any(
            f.name == "watched_date" for f in Review._meta.get_fields()
        )
        if not review_has_watched:
            self.stdout.write(
                self.style.WARNING(
                    "Review has no watched_date field — watch dates will NOT be stored. "
                    "Add `watched_date = models.DateField(null=True, blank=True)` + migrate "
                    "to keep your timeline."
                )
            )

        APPROVED = {"high", "ok"}  # statuses that get imported
        created, skipped, failed = 0, 0, 0

        with open(infile, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                status = row["status"].strip().lower()
                if status not in APPROVED:
                    skipped += 1
                    continue

                tmdb_id = row["tmdb_id"].strip()
                mt_raw = row["tmdb_media_type"].strip()
                if not tmdb_id or mt_raw not in MEDIA_TYPE_MAP:
                    self.stdout.write(
                        self.style.WARNING(
                            f"skip (bad tmdb_id/media_type): {row['title_zh']}"
                        )
                    )
                    failed += 1
                    continue

                media_type = MEDIA_TYPE_MAP[mt_raw]

                work = get_or_create_work(media_type=media_type, external_id=tmdb_id)
                if work is None:
                    self.stdout.write(
                        self.style.WARNING(
                            f"skip (TMDB fetch failed): {row['title_zh']} id={tmdb_id}"
                        )
                    )
                    failed += 1
                    continue

                rating_raw = row["rating"].strip()
                if not rating_raw:
                    # unrated on douban -> catalog exists, but Review needs a rating
                    skipped += 1
                    continue

                defaults = {"rating": Decimal(rating_raw)}
                if review_has_watched and row["watched_date"].strip():
                    try:
                        y, m, d = row["watched_date"].split("-")
                        defaults["watched_date"] = date(int(y), int(m), int(d))
                    except ValueError:
                        pass

                _, was_created = Review.objects.update_or_create(
                    user=user,
                    catalog=work,
                    defaults=defaults,
                )
                created += was_created
                self.stdout.write(
                    f"  {'created' if was_created else 'updated'}: "
                    f"{work} -> {defaults['rating']}"
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\ndone. reviews created: {created}, skipped: {skipped}, failed: {failed}"
            )
        )
