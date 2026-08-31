# Seattle Sports Tracker — Interview Overview

## Quick summary for myself:

Project Architecture: React + Vite frontend, Django + Django REST backend

Data is pulled from ESPN, nflverse, MLB stats API

Advanced stat tracking: nfl-data-py, numpy, pandas

NFL INJURY:

Surface and Injury analysis runs Chi-sq test on 2x2 table (contact, noncontact, grass, turf)

The results are statistically insignificant (pval ~ 0.69)

There are other confounding factors like fields with grass generally play outdoors (no dome) so cold or wet games can impact injury too.

MLB PITCHING TEMP:

Statistically significant results (pval ~ 0.018)

Could only use games where the roof was open

Not a lot of data for "cold temp" games since roof is often closed during cold

---

## What it is
A full-stack web app that aggregates real-time roster data, season-by-season player stats, and advanced analytics for Seattle's three major pro sports teams: Seahawks (NFL), Mariners (MLB), and Kraken (NHL).

---

## Architecture

**Backend: Django + Django REST Framework**
- Python-based REST API serving JSON to the frontend
- Each team has two endpoints: `/api/{team}/roster/` and `/api/{team}/players/{id}/stats/`
- Analytics endpoint: `/api/nfl/injuries/`
- File-based Django cache (24-hour TTL) prevents re-fetching the same data on every request

**Frontend: React + Vite**
- Single-page app with React Router for client-side navigation
- CSS Modules for scoped, component-level styling
- Recharts for data visualization on the analytics page
- Custom `useRoster` hook centralizes all API fetching with loading/error state

**Dev setup:** Both servers start with a single `bash start.sh`. Vite proxies `/api` requests to Django so there are no CORS issues in development.

---

## Where the data comes from

**Roster data (all 3 teams):** ESPN's public (undocumented) API
- `site.api.espn.com/apis/common/v3/sports/{sport}/athletes`
- Returns active roster with headshots, jersey numbers, height/weight/age/college
- Cached for 5 minutes

**Player stats (all 3 teams):** ESPN's splits endpoint
- `site.api.espn.com/apis/common/v3/sports/{sport}/athletes/{id}/splits?season={year}&seasontype=2`
- Returns season-by-season stat splits; fetches all available seasons concurrently using `ThreadPoolExecutor`
- Stats are **position-aware**: a QB sees passing/rushing tables, a WR sees receiving, a lineman sees no individual stats. Columns where every season value is 0 are automatically hidden.
- Career row: counting stats summed, rate stats recomputed from career totals (not averaged), so career batting average = career H / career AB, not the mean of yearly averages

**Sport-specific edge cases worth knowing:**
- *MLB Innings Pitched*: ESPN returns `"180.2"` to mean 180⅔ innings (not 180.2). Career IP is accumulated in outs (×3) then converted back.
- *NHL Goalies vs Skaters*: completely different stat sets — goalies get GAA/SV%/SO, skaters get G/A/PTS/+−. Career SV% = total saves / total shots against.

**Injury analytics:** `nfl_data_py` (the nflverse Python package)
- `import_injuries()` — weekly NFL injury report filings (2016–2024)
- `import_schedules()` — game schedules including surface type (grass vs. various turf brands)
- The two are joined on `(season, week, team)` to know which surface each player's team played on each week

---

## Injury Analysis — the key technical piece

**What it does:** Measures whether non-contact soft-tissue injuries (hamstring, quad, calf, groin, achilles) occur at different rates on grass vs. artificial turf compared to contact/traumatic injuries (concussion, fracture, laceration).

**Methodology:**
- **Denominator:** 46 active players × team-game appearances per surface type → total player-game exposures
- **Rate:** injuries per 1,000 player-game exposures
- **Chi-square test** on the 2×2 contingency table (surface × injury type)
- **Poisson rate ratio** with Wald 95% confidence intervals (turf rate / grass rate)
- Broken down by: specific injury type, position group (QB through S), and season trend (2016–2024)

**The honest finding:** No statistically significant aggregate difference (p ≈ 0.69, Rate Ratio ≈ 1.00 for both injury types). This is actually the correct data science answer — and being able to explain *why* it's not significant (injury reports are administrative filings, not play-level occurrence data; they lag the actual injury; surface type correlates with team/stadium, not individual exposure) demonstrates real analytical thinking.

**Visualizations:** Four Recharts charts — grouped bar (rates by surface), multi-line trend (all four series 2016–2024), horizontal bar + rate ratio table (per injury type), grouped bar (per position group).

---

---

## Mariners Starting Pitching by Temperature — the second advanced analytic

**What it does:** Measures how game-day temperature affects Mariners starting pitcher performance (ERA, WHIP, K/9) across the full 2025 regular season.

**Data source:** MLB Stats API (`statsapi.mlb.com`) — official MLB data, completely free, no API key required. Fetches all 162 game live feeds concurrently using `ThreadPoolExecutor` (12 workers, ~35 seconds on first load), then cached to disk for 24 hours.

**What each game feed provides:**
- Starting pitcher identity and full per-game stats (IP, ER, H, BB, K)
- Game-day weather: temperature (°F), condition, wind
- Roof status — critical for T-Mobile Park, which has a retractable roof

**Methodology:**
- **Outdoor starts only** for temperature analysis — games with "Roof Closed" are classified as "Controlled Environment" and excluded from temp comparisons (but included in overall pitcher stats)
- **Aggregate ERA** = Σ(ER) × 9 / Σ(IP), not the mean of per-game ERAs — a methodologically important distinction
- **Pearson correlation** between game-day temperature (°F) and per-start ERA across all outdoor starts
- Temperature bucketed into four bands: <55°F, 55–64°F, 65–74°F, ≥75°F
- Per-pitcher cold/warm splits (cold = <60°F, warm = ≥70°F, minimum 3 starts to display)

**Key findings (2025 season):**
- **Statistically significant positive correlation**: r = 0.203, p = 0.018 — warmer temperatures associate with higher ERA
- **Sweet spot at 65–74°F**: ERA 3.44, the best of any temperature band
- **Worst in heat (≥75°F)**: ERA 5.05 — the rotation noticeably struggles in hot conditions
- **Roof effect**: ERA 3.17 with roof closed vs 4.05 outdoors across 26 vs 135 starts

**Visualizations:** Scatter plot (temp vs per-start ERA, colored by pitcher), bar chart by temperature band, outdoor vs controlled environment comparison, per-pitcher cold/warm split table.

**Honest caveats to mention:** Opposition quality, home/away splits, and pitcher fatigue all correlate with temperature in ways this data cannot isolate. The next analytical step would be a multivariate regression controlling for those factors. Per-pitcher temperature splits have small sample sizes and should be interpreted cautiously.

---

## Things likely to come up in an interview

| Question | Answer |
|---|---|
| Why ESPN's API? | It's public, well-structured, and returns headshots + bio + stats in one call. No API key needed. |
| Why not a database? | All source data is live from ESPN/nflverse; no need to store it ourselves. Cache handles performance. |
| Why is the injury finding "not significant" valuable? | Shows honest analysis over cherry-picking. The methodology note on the page explicitly explains the data's limitations — that's what good data work looks like. |
| How do you handle different sports having totally different stat structures? | Three separate stat modules (`player_stats.py`, `player_stats_mlb.py`, `player_stats_nhl.py`) with position maps and position-aware table definitions. The frontend `PlayerDetail` page is generic — it just renders whatever tables the backend returns. |
| What would you do differently at scale? | Store roster/stats in PostgreSQL with scheduled refresh jobs, use Redis for caching, add proper authentication, and switch injury analysis to a proper database-backed pipeline with play-level data from NFL's Next Gen Stats. |
