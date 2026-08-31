"""
Fetches and structures season-by-season + career NFL player stats from the ESPN splits API.
"""
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.core.cache import cache

SPLITS_URL = "https://site.api.espn.com/apis/common/v3/sports/football/nfl/athletes/{id}/splits"

# ── Position group lookup ─────────────────────────────────────────────────────

POSITION_MAP = {
    'QB': 'QB',
    'RB': 'RB', 'HB': 'RB', 'FB': 'RB',
    'WR': 'WR',
    'TE': 'TE',
    'T': 'OL', 'OT': 'OL', 'G': 'OL', 'C': 'OL',
    'DE': 'DL', 'DT': 'DL', 'NT': 'DL', 'DL': 'DL',
    'LB': 'LB', 'MLB': 'LB', 'OLB': 'LB', 'ILB': 'LB',
    'CB': 'DB', 'S': 'DB', 'FS': 'DB', 'SS': 'DB', 'DB': 'DB',
    'K': 'K', 'PK': 'K',
    'P': 'P',
    'LS': 'LS',
}

# ── Stat table definitions ────────────────────────────────────────────────────
# Each table: name, stats list, and career computation rules.
# stat tuple: (espn_name, display_label, is_countable)
# is_countable=True  → sum across seasons for career
# is_countable=False → recompute from career countable totals
# is_countable='max' → take max across seasons

_QB = [
    {
        'name': 'Passing',
        'stats': [
            ('completions',          'CMP',     True),
            ('passingAttempts',      'ATT',     True),
            ('completionPct',        'CMP%',    False),
            ('passingYards',         'YDS',     True),
            ('yardsPerPassAttempt',  'Y/A',     False),
            ('passingTouchdowns',    'TD',      True),
            ('interceptions',        'INT',     True),
            ('sacks',                'SACK',    True),
            ('QBRating',             'RTG',     False),
        ],
        'career_derived': {
            'completionPct':       lambda c: _pct(c, 'completions', 'passingAttempts'),
            'yardsPerPassAttempt': lambda c: _div(c, 'passingYards', 'passingAttempts'),
            'QBRating':            lambda _: '--',
        },
    },
    {
        'name': 'Rushing',
        'stats': [
            ('rushingAttempts',      'CAR',     True),
            ('rushingYards',         'YDS',     True),
            ('yardsPerRushAttempt',  'AVG',     False),
            ('rushingTouchdowns',    'TD',      True),
        ],
        'career_derived': {
            'yardsPerRushAttempt': lambda c: _div(c, 'rushingYards', 'rushingAttempts'),
        },
    },
]

_RUSHING_TABLE = {
    'name': 'Rushing',
    'stats': [
        ('rushingAttempts',      'CAR',     True),
        ('rushingYards',         'YDS',     True),
        ('yardsPerRushAttempt',  'AVG',     False),
        ('rushingTouchdowns',    'TD',      True),
        ('longRushing',          'LNG',     'max'),
    ],
    'career_derived': {
        'yardsPerRushAttempt': lambda c: _div(c, 'rushingYards', 'rushingAttempts'),
    },
}

_RECEIVING_TABLE = {
    'name': 'Receiving',
    'stats': [
        ('receptions',           'REC',     True),
        ('receivingYards',       'YDS',     True),
        ('yardsPerReception',    'AVG',     False),
        ('receivingTouchdowns',  'TD',      True),
        ('longReception',        'LNG',     'max'),
    ],
    'career_derived': {
        'yardsPerReception': lambda c: _div(c, 'receivingYards', 'receptions'),
    },
}

_DEFENSE_TABLE = {
    'name': 'Defense',
    'stats': [
        ('totalTackles',             'TOT',    True),
        ('soloTackles',              'SOLO',   True),
        ('assistTackles',            'AST',    True),
        ('sacks',                    'SACK',   True),
        ('stuffs',                   'STF',    True),
        ('passesDefended',           'PD',     True),
        ('interceptions',            'INT',    True),
        ('interceptionYards',        'INT YDS',True),
        ('interceptionTouchdowns',   'INT TD', True),
        ('fumblesForced',            'FF',     True),
        ('fumblesRecovered',         'FR',     True),
    ],
    'career_derived': {},
}

_K_TABLE = {
    'name': 'Kicking',
    'stats': [
        ('fieldGoalsMade1_19-fieldGoalAttempts1_19',   '1-19',   'fg'),
        ('fieldGoalsMade20_29-fieldGoalAttempts20_29', '20-29',  'fg'),
        ('fieldGoalsMade30_39-fieldGoalAttempts30_39', '30-39',  'fg'),
        ('fieldGoalsMade40_49-fieldGoalAttempts40_49', '40-49',  'fg'),
        ('fieldGoalsMade50-fieldGoalAttempts50',        '50+',    'fg'),
        ('fieldGoalsMade-fieldGoalAttempts',            'FG',     'fg'),
        ('fieldGoalPct',                                'FG%',    False),
        ('longFieldGoalMade',                           'LNG',    'max'),
        ('extraPointsMade-extraPointAttempts',          'XP',     'fg'),
        ('totalKickingPoints',                          'PTS',    True),
    ],
    'career_derived': {
        'fieldGoalPct': lambda c: _fg_pct(c, 'fieldGoalsMade-fieldGoalAttempts'),
    },
}

_P_TABLE = {
    'name': 'Punting',
    'stats': [
        ('punts',             'PUNTS', True),
        ('puntYards',         'YDS',   True),
        ('grossAvgPuntYards', 'GRS AVG', False),
        ('netAvgPuntYards',   'NET AVG', False),
        ('longPunt',          'LNG',   'max'),
        ('touchbacks',        'TB',    True),
        ('puntsInside20',     'IN20',  True),
    ],
    'career_derived': {
        'grossAvgPuntYards': lambda c: _div(c, 'puntYards', 'punts'),
        'netAvgPuntYards':   lambda _: '--',
    },
}

STAT_TABLES = {
    'QB': _QB,
    'RB': [dict(_RUSHING_TABLE), dict(_RECEIVING_TABLE)],
    'WR': [dict(_RECEIVING_TABLE)],
    'TE': [dict(_RECEIVING_TABLE)],
    'DL': [dict(_DEFENSE_TABLE)],
    'LB': [dict(_DEFENSE_TABLE)],
    'DB': [dict(_DEFENSE_TABLE)],
    'K':  [dict(_K_TABLE)],
    'P':  [dict(_P_TABLE)],
    'OL': [],  # no individual stats
    'LS': [],
}


# ── Helper math ───────────────────────────────────────────────────────────────

def _pct(career_counts, num_key, den_key):
    n = career_counts.get(num_key, 0)
    d = career_counts.get(den_key, 0)
    return f"{n / d * 100:.1f}" if d else '--'


def _div(career_counts, num_key, den_key):
    n = career_counts.get(num_key, 0)
    d = career_counts.get(den_key, 0)
    return f"{n / d:.1f}" if d else '--'


def _fg_pct(career_counts, fg_key):
    raw = career_counts.get(fg_key, '')
    parts = str(raw).split('-')
    if len(parts) == 2:
        try:
            m, a = float(parts[0]), float(parts[1])
            return f"{m / a * 100:.1f}" if a else '--'
        except ValueError:
            return '--'
    return '--'


def _parse_float(val):
    """Convert ESPN display value to float, stripping commas. Returns None if unparseable."""
    if val in ('--', '', None):
        return None
    try:
        return float(str(val).replace(',', ''))
    except ValueError:
        return None


def _fmt(val):
    """Format a float back to a display string (strip trailing .0 for integers)."""
    if val is None:
        return '--'
    if val == int(val):
        return f"{int(val):,}"
    return f"{val:.1f}"


# ── Core data fetching ────────────────────────────────────────────────────────

def _fetch_season(player_id, season):
    url = SPLITS_URL.format(id=player_id)
    resp = requests.get(url, params={'season': season, 'seasontype': '2'}, timeout=10)
    if resp.status_code != 200:
        return None
    data = resp.json()

    # Extract the "All Splits" row (first split in first splitCategory)
    split_cats = data.get('splitCategories', [])
    if not split_cats or not split_cats[0].get('splits'):
        return None

    raw_stats = split_cats[0]['splits'][0].get('stats', [])
    names = data.get('names', [])
    if not names or not raw_stats:
        return None

    # Build {stat_name: display_value}
    stat_dict = dict(zip(names, raw_stats))

    return {
        'year': season,
        'stats': stat_dict,
        'availableSeasons': [
            o['value']
            for f in data.get('filters', [])
            if f.get('name') == 'season'
            for o in f.get('options', [])
        ],
    }


def get_player_stats(player_id: str, player_info: dict) -> dict:
    cache_key = f"player_stats_nfl_{player_id}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    position = player_info.get('position', '')
    pos_group = POSITION_MAP.get(position, 'OL')
    tables_config = STAT_TABLES.get(pos_group, [])

    # Step 1: fetch most recent season to discover available seasons
    initial = _fetch_season(player_id, '2025')
    if not initial:
        result = _build_result(player_info, pos_group, [], tables_config)
        cache.set(cache_key, result, timeout=300)
        return result

    available_seasons = initial.get('availableSeasons', ['2025'])

    # Step 2: fetch remaining seasons concurrently
    season_data = {initial['year']: initial['stats']}
    remaining = [s for s in available_seasons if s != '2025']

    if remaining:
        with ThreadPoolExecutor(max_workers=6) as pool:
            futures = {pool.submit(_fetch_season, player_id, s): s for s in remaining}
            for future in as_completed(futures):
                s_result = future.result()
                if s_result:
                    season_data[s_result['year']] = s_result['stats']

    # Step 3: build season rows sorted newest first
    sorted_seasons = sorted(season_data.keys(), reverse=True)
    season_rows = [{'year': yr, 'stats': season_data[yr]} for yr in sorted_seasons]

    result = _build_result(player_info, pos_group, season_rows, tables_config)
    cache.set(cache_key, result, timeout=300)
    return result


def _build_result(player_info, pos_group, season_rows, tables_config):
    tables = []
    for table_cfg in tables_config:
        stat_defs = table_cfg['stats']
        career_derived = table_cfg.get('career_derived', {})

        # Column headers (skip stats with no data across all seasons)
        stat_names = [s[0] for s in stat_defs]
        active_stats = _get_active_stats(stat_defs, season_rows)

        if not active_stats:
            continue

        headers = ['Season'] + [label for name, label, _ in active_stats]

        # Per-season rows
        rows = []
        for sr in season_rows:
            vals = [_season_val(sr['stats'], name, kind) for name, _, kind in active_stats]
            if any(v not in ('--', '0', '0.0') for v in vals):
                rows.append({'year': sr['year'], 'values': vals})

        if not rows:
            continue

        # Career totals
        career = _compute_career(season_rows, active_stats, career_derived)

        tables.append({
            'name': table_cfg['name'],
            'headers': headers,
            'seasons': rows,
            'career': career,
        })

    return {
        'player': player_info,
        'positionGroup': pos_group,
        'tables': tables,
    }


def _get_active_stats(stat_defs, season_rows):
    """Return only stat defs that have at least one non-zero value across all seasons."""
    if not season_rows:
        return stat_defs
    active = []
    for name, label, kind in stat_defs:
        for sr in season_rows:
            val = sr['stats'].get(name, '--')
            if val not in ('--', '0', '0.0', '0.00', '', None):
                active.append((name, label, kind))
                break
    return active if active else stat_defs


def _season_val(stat_dict, name, kind):
    val = stat_dict.get(name, '--')
    if val in (None, ''):
        return '--'
    return str(val)


def _compute_career(season_rows, active_stats, career_derived):
    """Sum countable stats and compute derived stats for career totals."""
    counts = {}
    maxes = {}
    fg_accum = {}

    for name, _, kind in active_stats:
        if kind is True:
            total = 0.0
            for sr in season_rows:
                v = _parse_float(sr['stats'].get(name))
                if v is not None:
                    total += v
            counts[name] = total
        elif kind == 'max':
            best = 0.0
            for sr in season_rows:
                v = _parse_float(sr['stats'].get(name))
                if v is not None and v > best:
                    best = v
            maxes[name] = best
        elif kind == 'fg':
            # Accumulate M-A format (e.g., "41-48")
            made_total = 0.0
            att_total = 0.0
            for sr in season_rows:
                raw = sr['stats'].get(name, '')
                parts = str(raw).split('-')
                if len(parts) == 2:
                    try:
                        made_total += float(parts[0])
                        att_total += float(parts[1])
                    except ValueError:
                        pass
            fg_accum[name] = f"{int(made_total)}-{int(att_total)}" if att_total else '--'

    career_vals = []
    for name, _, kind in active_stats:
        if kind is True:
            career_vals.append(_fmt(counts.get(name)))
        elif kind == 'max':
            career_vals.append(_fmt(maxes.get(name)))
        elif kind == 'fg':
            career_vals.append(fg_accum.get(name, '--'))
        else:
            # Derived: use lambda from career_derived
            fn = career_derived.get(name)
            if fn:
                all_counts = {**counts, **fg_accum}
                career_vals.append(fn(all_counts))
            else:
                career_vals.append('--')

    return career_vals
