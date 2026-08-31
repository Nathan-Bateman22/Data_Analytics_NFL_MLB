"""
Fetches and structures season-by-season + career NHL player stats from the ESPN splits API.

Two position groups:
  - Skaters (C, LW, RW, D, F): GP G A PTS +/- PIM S FO% PPG PPA SHG SHA GWG TOI/G
  - Goalies (G): GS W L OTL GA GAA SA SV SV% SO

TOI/G is in "MM:SS" format — displayed per season, shown as '--' for career totals.
+/-  is a counting stat that can be negative — summed directly for career.
"""
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.core.cache import cache

SPLITS_URL = "https://site.api.espn.com/apis/common/v3/sports/hockey/nhl/athletes/{id}/splits"

GOALIE_POSITIONS = {'G'}

# ── Stat table definitions ────────────────────────────────────────────────────
# tuple: (espn_name, display_label, career_type)
# career_type: True=sum, False=derived/rate, 'toi'=time-on-ice (skip for career)

SKATER_TABLE = {
    'name': 'Skating',
    'stats': [
        ('games',               'GP',    True),
        ('goals',               'G',     True),
        ('assists',             'A',     True),
        ('points',              'PTS',   True),
        ('plusMinus',           '+/-',   True),
        ('penaltyMinutes',      'PIM',   True),
        ('shotsTotal',          'S',     True),
        ('powerPlayGoals',      'PPG',   True),
        ('powerPlayAssists',    'PPA',   True),
        ('shortHandedGoals',    'SHG',   True),
        ('shortHandedAssists',  'SHA',   True),
        ('gameWinningGoals',    'GWG',   True),
        ('faceoffPercent',      'FO%',   False),
        ('timeOnIcePerGame',    'TOI/G', 'toi'),
    ],
    'career_derived': {
        'faceoffPercent':   lambda _: '--',
        'timeOnIcePerGame': lambda _: '--',
    },
}

GOALIE_TABLE = {
    'name': 'Goaltending',
    'stats': [
        ('gameStarted',      'GS',   True),
        ('wins',             'W',    True),
        ('losses',           'L',    True),
        ('overtimeLosses',   'OTL',  True),
        ('goalsAgainst',     'GA',   True),
        ('avgGoalsAgainst',  'GAA',  False),
        ('shotsAgainst',     'SA',   True),
        ('saves',            'SV',   True),
        ('savePct',          'SV%',  False),
        ('shutouts',         'SO',   True),
    ],
    'career_derived': {
        'avgGoalsAgainst': lambda _: '--',
        'savePct':         lambda c: _sv_pct(c),
    },
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_float(val):
    if val in ('--', '', None):
        return None
    try:
        return float(str(val).replace(',', ''))
    except ValueError:
        return None


def _fmt(val):
    if val is None:
        return '--'
    if val == int(val):
        return f"{int(val):,}"
    return f"{val:.1f}"


def _sv_pct(c):
    sv = c.get('saves', 0)
    sa = c.get('shotsAgainst', 0)
    return f"{sv / sa:.3f}".lstrip('0') or '.000' if sa else '--'


# ── Core fetching ─────────────────────────────────────────────────────────────

def _fetch_season_nhl(player_id, season):
    url = SPLITS_URL.format(id=player_id)
    resp = requests.get(url, params={'season': season, 'seasontype': '2'}, timeout=10)
    if resp.status_code != 200:
        return None
    data = resp.json()

    split_cats = data.get('splitCategories', [])
    if not split_cats or not split_cats[0].get('splits'):
        return None

    raw_stats = split_cats[0]['splits'][0].get('stats', [])
    names = data.get('names', [])
    if not names or not raw_stats:
        return None

    available = [
        o['value']
        for f in data.get('filters', [])
        if f.get('name') == 'season'
        for o in f.get('options', [])
    ]

    return {'year': season, 'stats': dict(zip(names, raw_stats)), 'availableSeasons': available}


def get_nhl_player_stats(player_id: str, player_info: dict) -> dict:
    cache_key = f"player_stats_nhl_{player_id}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    position = player_info.get('position', '')
    is_goalie = position in GOALIE_POSITIONS
    table_cfg = GOALIE_TABLE if is_goalie else SKATER_TABLE

    # 2026 = the 2025-26 NHL season (regular season just completed in April 2026)
    initial = _fetch_season_nhl(player_id, '2026')
    if not initial:
        initial = _fetch_season_nhl(player_id, '2025')
    if not initial:
        result = _build_nhl_result(player_info, is_goalie, [], table_cfg)
        cache.set(cache_key, result, timeout=300)
        return result

    available = initial.get('availableSeasons', ['2026'])
    season_data = {initial['year']: initial['stats']}
    remaining = [s for s in available if s != initial['year']]

    if remaining:
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = {pool.submit(_fetch_season_nhl, player_id, s): s for s in remaining}
            for future in as_completed(futures):
                s_result = future.result()
                if s_result:
                    season_data[s_result['year']] = s_result['stats']

    sorted_seasons = sorted(season_data.keys(), reverse=True)
    season_rows = [{'year': yr, 'stats': season_data[yr]} for yr in sorted_seasons]

    result = _build_nhl_result(player_info, is_goalie, season_rows, table_cfg)
    cache.set(cache_key, result, timeout=300)
    return result


def _build_nhl_result(player_info, is_goalie, season_rows, table_cfg):
    stat_defs = table_cfg['stats']
    career_derived = table_cfg.get('career_derived', {})

    active_stats = _get_active_stats(stat_defs, season_rows)
    headers = ['Season'] + [label for _, label, _ in active_stats]

    rows = []
    for sr in season_rows:
        vals = [str(sr['stats'].get(name, '--') or '--') for name, _, _ in active_stats]
        if any(v not in ('--', '0', '0.0', '.000') for v in vals):
            rows.append({'year': sr['year'], 'values': vals})

    career = _compute_career_nhl(season_rows, active_stats, career_derived)

    tables = []
    if rows:
        tables.append({
            'name': table_cfg['name'],
            'headers': headers,
            'seasons': rows,
            'career': career,
        })

    pos_group = 'G' if is_goalie else player_info.get('position', 'F')

    return {
        'player': player_info,
        'positionGroup': pos_group,
        'tables': tables,
    }


def _get_active_stats(stat_defs, season_rows):
    if not season_rows:
        return stat_defs
    active = []
    for name, label, kind in stat_defs:
        for sr in season_rows:
            val = sr['stats'].get(name, '--')
            if val not in ('--', '0', '0.0', '.000', '0.00', '', None):
                active.append((name, label, kind))
                break
    return active if active else stat_defs


def _compute_career_nhl(season_rows, active_stats, career_derived):
    counts = {}

    for name, _, kind in active_stats:
        if kind is True:
            total = 0.0
            for sr in season_rows:
                v = _parse_float(sr['stats'].get(name))
                if v is not None:
                    total += v
            counts[name] = total

    career_vals = []
    for name, _, kind in active_stats:
        if kind is True:
            career_vals.append(_fmt(counts.get(name)))
        else:
            fn = career_derived.get(name)
            career_vals.append(fn(counts) if fn else '--')

    return career_vals
