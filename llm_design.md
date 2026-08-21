用户输入
  ↓
① LLM：人话 → filter JSON（media_type/genres/rating_min/rating_max/artist/year_min/year_max）
  ↓
② ORM：Review.filter(user, 按①条件).distinct()，每星级取样（可能 0 条，没关系）
  ↓
③ LLM：把取样（无论多少）+ ①的意图 拼进一个 prompt，
        指令里说明"基于历史推荐，不足 5 个用通用知识补齐" → 出 5 个推荐
  ↓
展示（纯文字）

TODO ① User taste store — persist each user's preferences so recommendations remember their taste across sessions (separate design: store raw prefs vs. an LLM-summarized profile? how to update?).
TODO ② Relax filters when candidates are scarce (option 2). Note: option 3's fallback is already built into the recommend prompt ("use general knowledge if history is insufficient").
TODO ③ Multi-turn interaction (recommend → user picks / revises the request → re-recommend). Requires introducing conversation state, which the current stateless views deliberately avoid.
TODO ④ Persist a clicked recommendation. The LLM returns a title string, not a TMDB id, so the flow must first resolve "title → TMDB search → id" before calling get_or_create_work. That middle step has pitfalls (not found / wrong match / same-name collisions) — do it as its own round.
TODO ⑤ Balance sampling and recommendations by media_type (currently mixed — e.g. picking movie+book may yield all movies, no books).
TODO ⑥ Genre-name alignment: the LLM's extracted genre names must match Genre.name in the DB (exact __in match), or the history-based half silently falls back. Likely fix: pass the DB's genre list into the extract prompt so the LLM only picks from it.
TODO 7 Loading page since the load is slow.