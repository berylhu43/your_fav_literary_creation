# Frontend Page Map

*Navigation structure and per-page **data needs** for the React frontend — the *planning* view (which pages exist, how they flow, what each page consumes conceptually). Companion to `design.md` (§8.16) and `llm_design.md`.*

*For the wire contract — endpoint URLs, request/response shapes, auth — see [api_contract_for_frontend.md](./api_contract_for_frontend.md), which also carries the canonical navigation diagram. This doc names data needs conceptually and points there; it does not repeat URLs or shapes.*

---

## 1. Pages & flow

Four top-level pages via the nav bar: **Home / Recommendations**, **Discovery**, **My Records**, **Login / Register**.

- **Work Detail** is a shared hub — reached from Home, Discovery, Search Results, and My Records (mirrors `design.md` §8.13: the detail page is the single place to act on a work).
- **Artist Detail ↔ Work Detail** form a loop: from a work you open an artist, from an artist you open another work.
- **Search Results** is not a separate nav destination — it's a state of Discovery driven by a query param, the same "params drive one page's two states" pattern as `?q=` on My Records.
- **Wishlist** is *designed, not built* — reserved as a nav slot but has no endpoint (same design-vs-implementation split as Artist/Credit in `design.md` §8.6; an empty endpoint the frontend codes against is worse than none).

> Canonical navigation diagram: `api_contract_for_frontend.md` §2.

---

## 2. Per-page data needs

Conceptual only — *what kind* of data each page consumes and how clicks flow. Endpoint URLs, shapes, and auth are in `api_contract`.

**Home / Recommendations** — "for you" picks generated from a free-text intent + chosen media types (LLM). Recommendations come back as *titles, not works*, so opening one needs a title→id resolve/persist step before Work Detail can render it (see `llm_design.md` TODO ④).

**Discovery (+ Search sub-state)** — popular movie/TV walls, optional genre filter, and a search box that hits TMDB (distinct from the local library — search vs discover, Stage 3 notes). Clicking any item opens Work Detail; search results carry only an `external_id`, so opening one persists-on-click first.

**My Records** — the user's own reviews, newest first, searchable by work title. Edit/delete inline; clicking an item opens Work Detail.

**Work Detail** — the hub: work info (title, metadata, cover, genres), all reviews + average rating, own-review actions (add/edit/delete), and clickable artists that open Artist Detail.
> **Build-time decision (unresolved):** does Work Detail fetch info and reviews as one packed response, or two (info instant, reviews load/paginate after)? And is `average_rating` computed server-side or client-side from the review list? Packed = simpler; split = info shows first. Decide when building the page.

**Artist Detail** — artist + full filmography read *live from TMDB* (`design.md` §8.14), not the local library. Filmography works may not exist locally yet, so clicking one uses the same persist-on-click step as search / recommendations.

**Login / Register** — credentials→token login; register returns a token that logs the new user straight in; logout is client-side (drop the token) plus the server-side invalidation endpoint. A separate-origin SPA also needs CORS; a token-refresh story stays optional until actually wanted.

**Wishlist** *(planned, not built)* — no endpoints yet; kept here only to reserve its nav slot.