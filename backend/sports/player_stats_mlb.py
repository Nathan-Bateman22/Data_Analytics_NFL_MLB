"""
Fetches and structures season-by-season + career MLB player stats from the ESPN splits API.

Innings pitched format: "180.2" means 180 full innings + 2 outs (NOT 180.2 innings).
  .0 = 0 outs, .1 = 1 out (1/3 inning), .2 = 2 outs (2/3 inning)
"""
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.core.cache import cache

SPLITS_URL = "https://site.api.espn.com/apis/common/v3/sports/baseball/mlb/athletes/{id}/splits"

PITCHER_POSITIONS = {'SP', 'RP', 'CL', 'P'}
HITTER_POSITIONS  = {'C', '1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF', 'OF', 'DH', 'IF'}

# ── Stat table definitions ────────────────────────────────────────────────────
# tuple: (espn_name, display_label, career_type)
# career_type: True=sum, False=derived/rate, 'max'=maximum, 'ip'=innings pitched

HITTING_TABLE = {
    'name': 'Batting',
    'stats': [
        ('atBats',        'AB',   True),
        ('runs',          'R',    True),
        ('hits',          'H',    True),
        ('doubles',       '2B',   True),
        ('triples',       '3B',   True),
        ('homeRuns',      'HR',   True),
        ('RBIs',          'RBI',  True),
        ('walks',         'BB',   True),
        ('hitByPitch',    'HBP',  True),
        ('strikeouts',    'SO',   True),
        ('stolenBases',   'SB',   True),
        ('caughtStealing','CS',   True),
        ('avg',           'AVG',  False),
        ('onBasePct',     'OBP',  False),
        ('slugAvg',       'SLG',  False),
        ('OPS',           'OPS',  False),
    ],
    'career_derived': {
        'avg':       lambda c: _batting_avg(c),
        'onBasePct': lambda c: _obp(c),
        'slugAvg':   lambda c: _slg(c),
        'OPS':       lambda c: _ops(c),
    },
}

PITCHING_TABLE = {
    'name': 'Pitching',
    'stats': [
        ('wins',             'W',    True),
        ('losses',           'L',    True),
        ('ERA',              'ERA',  False),
        ('saves',            'SV',   True),
        ('saveOpportunities','SVO',  True),
        ('gamesPlayed',      'G',    True),
        ('gamesStarted',     'GS',   True),
        ('innings',          'IP',   'ip'),
        ('hits',             'H',    True),
        ('runs',             'R',    True),
        ('earnedRuns',       'ER',   True),
        ('homeRuns',         'HR',   True),
        ('walks',            'BB',   True),
        ('strikeouts',       'K',    True),
        ('opponentAvg',      'OBA',  False),
    ],
    'career_derived': {
        'ERA':         lambda c: _era(c),
        'opponentAvg': lambda _: '--',
    },
}


# ── MLB math helpers ──────────────────────────────────────────────────────────

def _parse_avg(val):
    """Parse a batting average string like '.267' to float."""
    if val in ('--', '', None):
        return None
    try:
        return float(str(val).replace(',', ''))
    except ValueError:
        return None


def _fmt_avg(val):
    if val is None:
        return '--'
    s = f"{val:.3f}"
    return s.lstrip('0') or '.000'


def _fmt_era(val):
    if val is None:
        return '--'
    return f"{val:.2f}"


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


def _ip_to_outs(ip_str) -> int:
    """'180.2' → 542 outs  (180 full innings × 3 + 2 outs)"""
    try:
        s = str(ip_str).replace(',', '')
        parts = s.split('.')
        full = int(parts[0]) if parts[0] else 0
        partial = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
        return full * 3 + partial
    except (ValueError, IndexError):
        return 0


def _outs_to_ip_str(outs: int) -> str:
    return f"{outs // 3}.{outs % 3}"


def _ip_decimal(outs: int) -> float:
    return outs / 3


# Career rate stat calculators
def _batting_avg(c):
    ab = c.get('atBats', 0)
    h  = c.get('hits', 0)
    return _fmt_avg(h / ab) if ab else '--'


def _obp(c):
    h   = c.get('hits', 0)
    bb  = c.get('walks', 0)
    hbp = c.get('hitByPitch', 0)
    ab  = c.get('atBats', 0)
    denom = ab + bb + hbp
    return _fmt_avg((h + bb + hbp) / denom) if denom else '--'


def _slg(c):
    ab  = c.get('atBats', 0)
    h   = c.get('hits', 0)
    d   = c.get('doubles', 0)
    t   = c.get('triples', 0)
    hr  = c.get('homeRuns', 0)
    tb  = h + d + 2 * t + 3 * hr
    return _fmt_avg(tb / ab) if ab else '--'


def _ops(c):
    obp_str = _obp(c)
    slg_str = _slg(c)
    try:
        val = float(obp_str) + float(slg_str)
        return _fmt_avg(val)
    except (ValueError, TypeError):
        return '--'


def _era(c):
    er   = c.get('earnedRuns', 0)
    outs = c.get('_total_outs', 0)
    ip   = _ip_decimal(outs)
    return _fmt_era(er * 9 / ip) if ip else '--'


# ── Core data fetching ────────────────────────────────────────────────────────

def _fetch_season_mlb(player_id, season):
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

    stat_dict = dict(zip(names, raw_stats))

    available = [
        o['value']
        for f in data.get('filters', [])
        if f.get('name') == 'season'
        for o in f.get('options', [])
    ]

    return {'year': season, 'stats': stat_dict, 'availableSeasons': available}


def get_mlb_player_stats(player_id: str, player_info: dict) -> dict:
    cache_key = f"player_stats_mlb_{player_id}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    position = player_info.get('position', '')
    is_pitcher = position in PITCHER_POSITIONS
    table_cfg = PITCHING_TABLE if is_pitcher else HITTING_TABLE

    # Fetch most recent season to discover all available seasons
    # Use 2025 (completed MLB season) as starting point; 2026 may have early stats
    initial = _fetch_season_mlb(player_id, '2025')
    if not initial:
        initial = _fetch_season_mlb(player_id, '2024')
    if not initial:
        result = _build_mlb_result(player_info, is_pitcher, [], table_cfg)
        cache.set(cache_key, result, timeout=300)
        return result

    available = initial.get('availableSeasons', ['2025'])

    season_data = {initial['year']: initial['stats']}
    remaining = [s for s in available if s != initial['year']]

    if remaining:
        with ThreadPoolExecutor(max_workers=6) as pool:
            futures = {pool.submit(_fetch_season_mlb, player_id, s): s for s in remaining}
            for future in as_completed(futures):
                s_result = future.result()
                if s_result:
                    season_data[s_result['year']] = s_result['stats']

    sorted_seasons = sorted(season_data.keys(), reverse=True)
    season_rows = [{'year': yr, 'stats': season_data[yr]} for yr in sorted_seasons]

    result = _build_mlb_result(player_info, is_pitcher, season_rows, table_cfg)
    cache.set(cache_key, result, timeout=300)
    return result


def _build_mlb_result(player_info, is_pitcher, season_rows, table_cfg):
    stat_defs = table_cfg['stats']
    career_derived = table_cfg.get('career_derived', {})

    active_stats = _get_active_stats(stat_defs, season_rows)
    headers = ['Season'] + [label for _, label, _ in active_stats]

    rows = []
    for sr in season_rows:
        vals = [_season_val_mlb(sr['stats'], name, kind) for name, _, kind in active_stats]
        if any(v not in ('--', '0', '0.0', '.000') for v in vals):
            rows.append({'year': sr['year'], 'values': vals})

    career = _compute_career_mlb(season_rows, active_stats, career_derived)

    tables = []
    if rows:
        tables.append({
            'name': table_cfg['name'],
            'headers': headers,
            'seasons': rows,
            'career': career,
        })

    pos_group = 'P' if is_pitcher else player_info.get('position', 'OF')

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
            if val not in ('--', '0', '0.0', '.000', '', None):
                active.append((name, label, kind))
                break
    return active if active else stat_defs


def _season_val_mlb(stat_dict, name, kind):
    val = stat_dict.get(name, '--')
    if val in (None, ''):
        return '--'
    return str(val)


def _compute_career_mlb(season_rows, active_stats, career_derived):
    counts = {}
    total_outs = 0

    for name, _, kind in active_stats:
        if kind is True:
            total = 0.0
            for sr in season_rows:
                v = _parse_float(sr['stats'].get(name))
                if v is not None:
                    total += v
            counts[name] = total
        elif kind == 'ip':
            for sr in season_rows:
                total_outs += _ip_to_outs(sr['stats'].get(name, '0'))

    counts['_total_outs'] = total_outs

    career_vals = []
    for name, _, kind in active_stats:
        if kind is True:
            career_vals.append(_fmt(counts.get(name)))
        elif kind == 'ip':
            career_vals.append(_outs_to_ip_str(total_outs))
        else:
            fn = career_derived.get(name)
            career_vals.append(fn(counts) if fn else '--')

    return career_vals
