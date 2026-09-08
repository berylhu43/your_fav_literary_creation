"""
Generic backfill: re-map existing Catalog rows from their source API and write
back whichever fields you name.

This deliberately reuses the same mappers used when a work is first created
(_map_movie / _map_tv / _map_book), so there is exactly one place that knows how
to turn an API response into model fields. Adding a new field later means
editing the mapper (which you'd do anyway for new rows) and then running:

    python manage.py backfill_catalog --fields <new_field>

No change to this command is needed.

Examples
--------
    # what would change, nothing written
    python manage.py backfill_catalog --fields vote_average --dry-run --limit 10

    # movies only: collection + score
    python manage.py backfill_catalog \
        --fields collection_id collection_name vote_average --media-types movie

    # tv scores
    python manage.py backfill_catalog --fields vote_average --media-types tv

    # everything the mappers produce, all media types
    python manage.py backfill_catalog --all-fields --media-types movie tv book

Progress is tracked per job (see --job), so an interrupted run resumes, and a
later backfill of a different field set starts fresh instead of being skipped.

Place at: <app>/management/commands/backfill_catalog.py
"""

import json
import os
import time

from django.core.management.base import BaseCommand, CommandError

# --- adjust to your project layout --------------------------------------------
from catalog.models import Catalog
from catalog.services import _map_book, _map_movie, _map_tv

# ------------------------------------------------------------------------------

STATE_DIR = ".backfill_cache"
RATE_LIMIT_SECONDS = 0.25

MAPPERS = {
    Catalog.MediaType.MOVIE: _map_movie,
    Catalog.MediaType.TV: _map_tv,
    Catalog.MediaType.BOOK: _map_book,
}

# Keys the mappers return that are NOT plain model fields — they're handled
# separately at creation time (m2m / credits) and must never be assigned here.
NON_FIELD_KEYS = {"genre_names", "created_by", "author_names"}


def _state_path(job):
    return os.path.join(STATE_DIR, f"{job}.json")


def _load_done(job):
    path = _state_path(job)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def _save_done(job, done):
    os.makedirs(STATE_DIR, exist_ok=True)
    path = _state_path(job)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(sorted(done), f)
    os.replace(tmp, path)  # atomic: survives Ctrl-C mid-write


def _model_field_names():
    return {
        f.name
        for f in Catalog._meta.get_fields()
        if getattr(f, "concrete", False) and not f.many_to_many
    }


class Command(BaseCommand):
    help = (
        "Re-map existing Catalog rows from their source API and write back "
        "the fields you name."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--fields",
            nargs="+",
            help="model field names to write, e.g. --fields vote_average collection_id",
        )
        parser.add_argument(
            "--all-fields",
            action="store_true",
            help="write every plain field the mapper returns (excludes genres/credits)",
        )
        parser.add_argument(
            "--media-types",
            nargs="+",
            default=["movie"],
            choices=["movie", "tv", "book"],
            help="which media types to process (default: movie)",
        )
        parser.add_argument(
            "--job",
            help="name for the progress file; defaults to the field list, so a "
            "different field set tracks its own progress",
        )
        parser.add_argument(
            "--dry-run", action="store_true", help="fetch and report, write nothing"
        )
        parser.add_argument("--limit", type=int, help="only process the first N rows")
        parser.add_argument(
            "--restart",
            action="store_true",
            help="ignore saved progress, process everything again",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="also overwrite fields that already have a value "
            "(default: only fill blanks/None)",
        )

    def handle(self, *args, **opts):
        fields = opts["fields"]
        all_fields = opts["all_fields"]
        if not fields and not all_fields:
            raise CommandError("give --fields <names> or --all-fields")

        valid = _model_field_names()
        if fields:
            unknown = [f for f in fields if f not in valid]
            if unknown:
                raise CommandError(f"not Catalog fields: {', '.join(unknown)}")
            bad = [f for f in fields if f in NON_FIELD_KEYS]
            if bad:
                raise CommandError(
                    f"{', '.join(bad)} are relations handled at creation time, "
                    f"not plain fields — this command cannot set them"
                )

        media_types = opts["media_types"]
        dry_run = opts["dry_run"]
        overwrite = opts["overwrite"]

        job = opts["job"] or ("all_fields" if all_fields else "_".join(sorted(fields)))
        job = f"{job}__{'_'.join(sorted(media_types))}"
        done = set() if opts["restart"] else _load_done(job)

        qs = (
            Catalog.objects.filter(media_type__in=media_types)
            .exclude(external_id="")
            .exclude(source=Catalog.Source.MANUAL)
            .order_by("id")
        )

        # key by media_type too: tmdb movie and tv ids share a namespace
        targets = [c for c in qs if f"{c.media_type}:{c.external_id}" not in done]
        if opts["limit"]:
            targets = targets[: opts["limit"]]

        total = len(targets)
        self.stdout.write(
            f"job '{job}': {qs.count()} rows in scope, {len(done)} already done, "
            f"{total} to process." + ("  [DRY RUN]" if dry_run else "")
        )
        if not total:
            return

        written = 0
        unchanged = 0
        failed = 0
        per_field = {}

        for i, work in enumerate(targets, 1):
            mapper = MAPPERS.get(work.media_type)
            if mapper is None:
                failed += 1
                continue

            mapped = mapper(work.external_id)
            time.sleep(RATE_LIMIT_SECONDS)

            if mapped is None:
                failed += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"  fetch failed: {work.title} ({work.media_type} "
                        f"id={work.external_id})"
                    )
                )
                continue

            if all_fields:
                wanted = [k for k in mapped if k not in NON_FIELD_KEYS and k in valid]
            else:
                # a field the mapper doesn't produce for this media type is
                # simply skipped (tv has no collection_id, books have no runtime)
                wanted = [f for f in fields if f in mapped]

            changed = []
            for name in wanted:
                new = mapped[name]
                old = getattr(work, name)
                if not overwrite and old not in (None, ""):
                    continue
                if old == new:
                    continue
                setattr(work, name, new)
                changed.append(name)
                per_field[name] = per_field.get(name, 0) + 1

            if changed:
                if not dry_run:
                    work.save(update_fields=changed)
                written += 1
                if dry_run and written <= 10:
                    self.stdout.write(
                        f"  would set {', '.join(changed)} on {work.title}"
                    )
            else:
                unchanged += 1

            done.add(f"{work.media_type}:{work.external_id}")

            if i % 25 == 0:
                if not dry_run:
                    _save_done(job, done)
                self.stdout.write(f"  {i}/{total} …")

        if not dry_run:
            _save_done(job, done)

        self.stdout.write(
            self.style.SUCCESS(
                f"\ndone. rows updated: {written}, already current: {unchanged}, "
                f"failed: {failed}"
            )
        )
        for name, count in sorted(per_field.items()):
            self.stdout.write(f"  {name}: {count}")
        if dry_run:
            self.stdout.write("(dry run — nothing was written)")
