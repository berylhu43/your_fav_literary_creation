# LLM Design Document — Recommendations Subsystem

*The LLM-driven recommendation feature of the Media Tracker. Companion to the main `design.md`; cross-references its sections as §N.*

---

## 1. Purpose

Turn a user's free-text request ("a sci-fi movie that's easy to follow but not too cliché", "a first-date film to watch at home") into a short list of personalized recommendations, grounded in that user's own rating history.

This subsystem is the concrete realization of the **Home page as the LLM surface** planned in the main doc. It lives in its own `recommendations` app (main doc §5), keeping LLM concerns out of `catalog` and `reviews`.

### Design stance

The guiding idea is a division of labor between the LLM and the database:

- **The LLM does what only it can do**: understand fuzzy human intent and translate it into structured conditions, and — at the end — turn a taste profile into concrete titles.
- **The database does what it does best**: filter and retrieve the user's actual records.

The LLM is *not* asked to be the whole recommender. It is a **translator at the front** and a **generator at the back**, with a plain ORM query in the middle. This keeps the system transparent and debuggable — every step's output can be printed and inspected — and avoids handing control to an opaque framework. (This is why no agent-orchestration library — LangChain, LangGraph, MCP, Skills — is used: the task is a single linear pass, not a multi-step stateful agent, and those tools would hide the very steps this project exists to understand.)

---

## 2. Architecture

### Reuse the Stage 2 client/service pattern

The recommendation pipeline is **structurally identical** to the external-API integration already built in Stage 2 (main doc §8.7). It is not a new architecture — it is the same layering applied to a new data source.

| Stage 2 (TMDB/Books) | Recommendations (LLM) |
|---|---|
| `_tmdb_get(path)` — low-level client: call, timeout, `try/except` → safe fallback | `_llm_get(messages, model, json_mode)` — same shape for the LLM API |
| `get_or_create_work()` — service: fetch → map → persist | `get_recommendations(user, query, media_types)` — service: extract → sample → generate |
| Thin view calls the service | Thin view calls the service |
| Per-source mappers converge on one `Catalog` shape | Two branches (history-grounded / fallback) converge on one recommendation shape |

`_llm_get` is to the LLM what `_tmdb_get` is to TMDB: it knows nothing about reviews or recommendations, only "send messages, return raw text, degrade to `None` on failure." Business logic lives entirely in `services.py`.

### Files

```
recommendations/
├── clients.py      # _llm_get()  — mirrors catalog/clients.py
├── services.py     # get_recommendations() + prompt builders + parser
├── views.py        # one thin view (@login_required)
├── urls.py
└── templates/recommendations/recommend.html
```

---

## 3. The Pipeline

Two LLM calls sandwiching one ORM query:

```
User input: free text  +  required media_type checkboxes (form)
   │
   ▼
① EXTRACT  (LLM)
   free text → filter JSON
   {genres, rating_min, rating_max, artist, year_min, year_max}
   (media_type is NOT extracted here — it comes from the form)
   │
   ▼
② SAMPLE  (ORM, no LLM)
   Review.filter(user, media_type∈form, + dynamic filters from ①).distinct()
   bucket by star rating, take up to N per bucket
   (may return 0 rows — that's fine)
   │
   ▼
③ GENERATE  (LLM)
   prompt = user intent + sampled history (however many)
   instruction: "recommend from taste; if history < N, fill with general knowledge"
   → N recommendations {title, media_type, reason}
   │
   ▼
Display (plain text for now; click-to-persist is TODO ④)
```

The extract prompt is short (just the user's sentence + instructions + genre whitelist), so its cost is small and its fixed prefix is cacheable (see §6). The generate prompt is longer (carries the sampled history), which is why per-bucket sampling caps its size.

---

## 4. Key Design Decisions

Recorded with rationale, matching the convention of main doc §8.

### 4.1 LLM extracts filters; the DB does the filtering

The LLM's job in step ① is translation only: natural language → a structured filter object. It does **not** query anything. The resulting filter is fed to a plain ORM query in step ②.

**Why split it this way.** Filtering is a solved, deterministic problem the ORM does perfectly; asking the LLM to also "pick from the library" would be slower, non-deterministic, and untestable. Conversely, translating "first-date film at home" into `genres: [romance, comedy]` is exactly what the ORM *cannot* do and the LLM excels at. Each tool does the half it is good at.

### 4.2 `media_type` comes from the form, not the LLM

The user selects media types via required checkboxes; the LLM's extract schema deliberately **excludes** `media_type`.

**Why.** `media_type` is a small fixed set with a reliable UI control (checkboxes) — the same reasoning as main doc §8.4 (`TextChoices`/explicit selection for fixed single-select-style sets). Making the user state it removes one dimension the LLM could get wrong, and the value is 100% trustworthy. It then constrains the query directly (`catalog__media_type__in=media_types`), which also means an off-target genre from the LLM (e.g. a TV-only genre when the user picked *movie*) simply yields no rows rather than a wrong result — the `Catalog` layer's `media_type` filter already guards it. (This is also why `Genre` needs **no** `media_type` field: the relationship is many-to-many and already expressed through `Catalog`↔`Genre`; it can be recovered by reverse query when needed.)

### 4.3 Feed the full star-rating spectrum, not just high ratings

Step ② samples across **all** rating buckets (0–0.5, 1–1.5, … , 5), not only the user's favorites.

**Why — validated empirically.** A user's low ratings are signal too: they say "not this." In testing, feeding the low-rated abstract/art-house sci-fi the user disliked led the model to recommend *Arrival* with the reason "emotionally engaging and crystal clear, **unlike the abstract films you rated low**." The negative examples let the model calibrate *away* from disliked traits — impossible if only high ratings were sent. Per-bucket capping (N per bucket) keeps the prompt bounded while preserving the spread.

### 4.4 Fallback lives in the prompt, not in Python branching

When history is thin or empty, the system does not branch in code. It always passes whatever was sampled (even zero rows) into the generate prompt, with one instruction: *"ground recommendations in the history; if it's insufficient for N, fill the rest with your own knowledge."*

**Why.** History size is a continuous quantity (0 → many), not a binary. Letting the model decide how much to lean on history vs. general knowledge is more natural than a hardcoded threshold, removes a magic number to tune, and keeps a single code path with one unified output shape. (This is "option 3" from the design discussion; "option 2 — relax the ORM filters — " remains a separate TODO.)

### 4.5 Inject the current date into every time-aware prompt

Prompts that touch relative time include `Today's date: <ISO date>` explicitly.

**Why.** An LLM has no clock; its notion of "now" is frozen at its knowledge cutoff. Without the injected date, "the last 20 years" was computed from the model's cutoff year, not the real one (observed: it resolved to 2024, not 2026). Supplying the real date fixes relative-time reasoning. Note this does **not** fix the deeper limit that the model cannot know works released after its cutoff (see §7).

### 4.6 Genre-name alignment via a DB-sourced whitelist

The extract prompt passes the actual `Genre.name` values from the DB and instructs the LLM to choose **only** from that list, verbatim.

**Why.** Step ② matches genres with an exact `catalog__genres__name__in` lookup. If the LLM returns "Sci-Fi" but the DB stores "Science Fiction", the match silently fails and the history-grounded half degrades to pure fallback — a bug that produces plausible-looking output, so it's easy to miss. Sourcing the whitelist live from the DB (not a hardcoded JSON) keeps it in sync as the catalog grows, consistent with the project's "let data speak, don't hardcode" stance (§8.4, §8.11). When picked media types matter, the list can be narrowed by reverse query: `Genre.objects.filter(catalogs__media_type__in=...).distinct()` — no model change required.

### 4.7 `_llm_get` is provider-generic (model as a parameter)

`_llm_get` takes `model` as an argument rather than hardcoding it. DeepSeek is accessed through the OpenAI-compatible SDK (`base_url` pointed at DeepSeek), and DeepSeek can emit both OpenAI- and Anthropic-format output.

**Why.** Keeping the model (and, later, the provider/base_url) parameterized means switching models — or running the same prompt across several for comparison — changes only the call site, never the service logic above it. This mirrors how `_tmdb_get` and `_google_books_get` sit side by side under one dispatching service.

### 4.8 Structured output via json_mode + defensive parsing

`_llm_get` requests JSON-object mode; the parser wraps `json.loads` in `try/except` and falls back to an empty result.

**Why.** External output is untrusted — the same mindset as `_tmdb_get`'s error handling. json_mode makes the model return clean JSON (no markdown fences, no preamble), but the parser still degrades gracefully if a call misbehaves, so one bad response can't crash the page. (json_mode requires the word "json" to appear in the prompt — the prompts satisfy this in their output-format instruction.)

---

## 5. Prompt Structure Convention

Both prompts follow the same four-part shape, which makes them easy to debug (fix the relevant block when something is off):

1. **Role + task** — what the model is and what it must do.
2. **Input data** — the user query; for generate, the sampled history and current date.
3. **Rules** — explicit constraints, especially *negative* ones ("do NOT recommend already-seen titles") and boundaries ("only genres from this list", "media_type must be one of …").
4. **Output format** — the exact JSON schema.

Debugging method: print the raw LLM output and inspect it before trusting it — did extract map the intent correctly, did generate respect the negative constraints, is the JSON well-formed. Same "print the external response first" habit used throughout Stage 2.

---

## 6. Cost & Token Behavior

Per recommendation = two LLM calls. Observed on a representative run (~2,800 total tokens): well under one cent. Cost is not a constraint at this project's call volume.

**Caching structure worth noting.** The extract prompt's fixed prefix (role, rules, genre whitelist) is cacheable and was observed hitting the cache (cache-hit tokens billed at the cheap tier). The generate prompt varies every time (history + query differ), so it does not cache. Prompt design that puts the stable part first and the variable part last naturally benefits from prefix caching.

Token usage is logged inside `_llm_get` (`resp.usage`), so both calls report prompt/completion/total automatically — useful when comparing models later.

---

## 7. Known Limitations

- **Knowledge cutoff vs. new releases.** Injecting the date (§4.5) fixes relative-time *reasoning*, but the model still cannot recommend works released after its training cutoff, and may hallucinate them. Recommending genuinely new titles will require blending in live TMDB data (e.g. `now_playing`, `/discover` by year) rather than relying on the model's memory. (Related to TODO ④, which already needs a title→TMDB resolution step.)
- **Slow responses.** Two sequential LLM calls take several seconds; users see a blank page and may re-submit (observed as harmless broken-pipe logs). A loading state is TODO ⑦.
- **Genre alignment is only as good as the whitelist.** If the whitelist is out of sync or the DB genre language is inconsistent, the history-grounded half silently weakens (§4.6).

---

## 8. Roadmap / TODOs

- **TODO ①** — User taste store: persist each user's preferences so recommendations remember taste across sessions. Separate design needed: store raw prefs vs. an LLM-summarized profile, and how/when to update it.
- **TODO ②** — Relax the ORM filters when candidates are scarce (the DB-side complement to §4.4's prompt-side fallback).
- **TODO ③** — Multi-turn interaction: recommend → user picks / revises the request → re-recommend. Requires conversation state, which the current stateless views deliberately avoid. (Not a ReAct-style agent loop — it's user-driven, essentially a stateful form.)
- **TODO ④** — Persist a clicked recommendation. The LLM returns a **title string**, not a TMDB id, so the flow must first resolve title → TMDB search → id before calling `get_or_create_work`. That middle step has pitfalls (not found / wrong match / same-name collisions) — do it as its own round.
- **TODO ⑤** — Balance sampling and generation by `media_type` (currently mixed: picking movie + book can yield all movies and no books).
- **TODO ⑥** — Genre-name alignment: enforce the DB-sourced whitelist so extracted names always match `Genre.name` (§4.6).
- **TODO ⑦** — Loading state for the slow two-call round-trip (§7).
- **TODO ⑧** — Disambiguate title → external_id resolution. `_resolve_external_id` currently takes `results[0]` (the top search hit), which works well for now but can pick the wrong entry for same-name works or when the LLM's title differs slightly from the source's. Improve by matching on additional signal — e.g. have the LLM emit a `year` field with each recommendation, then match the search results by release year instead of blindly taking the first. (Quality is acceptable at present, so this is deferred.)

---

## 9. Implementation Status

| Item | Status |
|---|---|
| `recommendations` app scaffolding (app + urls + wiring) | ✅ Implemented |
| `_llm_get` client (DeepSeek via OpenAI-compatible SDK) | ✅ Implemented |
| Token/usage logging in `_llm_get` | ✅ Implemented |
| ① Intent extraction (free text → filter JSON) | ✅ Implemented |
| Current-date injection | ✅ Implemented |
| ② Star-bucket sampling from `Review` (dynamic filters, `.distinct()`) | ✅ Implemented |
| ③ Generate prompt with in-prompt fallback | ✅ Implemented |
| Required media-type selection (front + back validation) | ✅ Implemented |
| Plain-text display of recommendations | ✅ Implemented |
| Genre whitelist enforcement | ✅ Implemented |
| Click-to-persist (title → TMDB → `get_or_create_work`) | ✅ Implemented |
| Multi-turn interaction | ⬜ TODO ③ |
| User taste store | ⬜ TODO ① |
| Balanced sampling by media_type | ⬜ TODO ⑤ |
| Loading state | ⬜ TODO ⑦ |

*Legend: ✅ implemented · 🚧 partial / in progress · ⬜ planned*