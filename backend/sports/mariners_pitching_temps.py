import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
from scipy import stats as scipy_stats
from django.core.cache import cache

MARINERS_ID = 136
SEASON = 2025
CACHE_KEY = 'mariners_pitching_temp_v3'
CACHE_TTL = 86400

CONTROLLED_KEYWORDS = {'roof closed', 'dome', 'indoor', 'retractable roof closed'}
MIN_IP = 1.0            # must have pitched at least 1 inning to count as a start
MIN_STARTS = 5          # skip openers / spot starters in per-pitcher breakdown
MIN_BUCKET_N = 3        # min starts for overall temp-bucket aggregates
MIN_PITCHER_BUCKET_N = 1  # min starts for per-pitcher cold/warm splits


def _ip_to_decimal(ip_str):
    """'6.2' → 6.667  (baseball innings format: tenths are thirds)"""
    try:
        parts = str(ip_str).split('.')
        return int(parts[0]) + (int(parts[1]) if len(parts) > 1 else 0) / 3
    except (ValueError, TypeError):
        return 0.0


def _fetch_game(pk):
    url = f'https://statsapi.mlb.com/api/v1.1/game/{pk}/feed/live'
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            return pk, json.loads(r.read())
    except Exception:
        return pk, None


def _get_mariners_pks():
    url = (
        f'https://statsapi.mlb.com/api/v1/schedule'
        f'?teamId={MARINERS_ID}&season={SEASON}&gameType=R&sportId=1'
    )
    with urllib.request.urlopen(url, timeout=10) as r:
        sched = json.loads(r.read())
    return [
        g['gamePk']
        for date in sched['dates']
        for g in date['games']
        if g['status']['detailedState'] == 'Final'
    ]


def _aggregate_era(starts):
    """Proper aggregate ERA: sum(ER)*9 / sum(IP) — not mean of per-game ERAs."""
    total_er = sum(s['er'] for s in starts)
    total_ip = sum(s['ip_dec'] for s in starts)
    return round(total_er * 9 / total_ip, 2) if total_ip > 0 else None


def _aggregate_whip(starts):
    total_baserunners = sum(s['h'] + s['bb'] for s in starts)
    total_ip = sum(s['ip_dec'] for s in starts)
    return round(total_baserunners / total_ip, 3) if total_ip > 0 else None


def _aggregate_k9(starts):
    total_k = sum(s['k'] for s in starts)
    total_ip = sum(s['ip_dec'] for s in starts)
    return round(total_k * 9 / total_ip, 2) if total_ip > 0 else None


def _aggregate_avg_ip(starts):
    return round(sum(s['ip_dec'] for s in starts) / len(starts), 2) if starts else None


def _bucket_stats(bucket_starts, label):
    if len(bucket_starts) < MIN_BUCKET_N:
        return {'label': label, 'starts': len(bucket_starts), 'insufficient': True}
    return {
        'label': label,
        'starts': len(bucket_starts),
        'insufficient': False,
        'era': _aggregate_era(bucket_starts),
        'whip': _aggregate_whip(bucket_starts),
        'k9': _aggregate_k9(bucket_starts),
        'avg_ip': _aggregate_avg_ip(bucket_starts),
    }


TEMP_BUCKETS = [
    ('< 55°F',  lambda t: t < 55),
    ('55–64°F', lambda t: 55 <= t < 65),
    ('65–74°F', lambda t: 65 <= t < 75),
    ('≥ 75°F',  lambda t: t >= 75),
]


def compute_pitching_temp_analysis():
    cached = cache.get(CACHE_KEY)
    if cached:
        return cached

    pks = _get_mariners_pks()
    starts = []

    with ThreadPoolExecutor(max_workers=12) as ex:
        futures = {ex.submit(_fetch_game, pk): pk for pk in pks}
        for future in as_completed(futures):
            pk, data = future.result()
            if data is None:
                continue

            gd = data['gameData']
            home_id = gd['teams']['home']['id']
            sea_side = 'home' if home_id == MARINERS_ID else 'away'

            weather = gd.get('weather', {})
            condition = weather.get('condition', '').lower()
            is_controlled = any(kw in condition for kw in CONTROLLED_KEYWORDS)

            try:
                temp_f = int(weather.get('temp', ''))
            except (ValueError, TypeError):
                temp_f = None

            sea_pitchers = data['liveData']['boxscore']['teams'][sea_side]['pitchers']
            if not sea_pitchers:
                continue

            sp_id = sea_pitchers[0]
            sp_data = data['liveData']['boxscore']['teams'][sea_side]['players'].get(f'ID{sp_id}')
            if not sp_data:
                continue

            sp_stats = sp_data['stats'].get('pitching', {})
            ip_dec = _ip_to_decimal(sp_stats.get('inningsPitched', '0'))
            if ip_dec < MIN_IP:
                continue

            er  = int(sp_stats.get('earnedRuns', 0))
            h   = int(sp_stats.get('hits', 0))
            bb  = int(sp_stats.get('baseOnBalls', 0))
            k   = int(sp_stats.get('strikeOuts', 0))
            bf  = int(sp_stats.get('battersFaced', 0))

            opp_side = 'away' if sea_side == 'home' else 'home'
            opponent = gd['teams'][opp_side]['name']

            starts.append({
                'game_pk': pk,
                'date': gd['datetime']['officialDate'],
                'venue': gd['venue']['name'],
                'opponent': opponent,
                'home_away': sea_side,
                'pitcher': sp_data['person']['fullName'],
                'pitcher_id': sp_id,
                'temp_f': temp_f,
                'condition': weather.get('condition', ''),
                'wind': weather.get('wind', ''),
                'is_controlled': is_controlled,
                'ip': sp_stats.get('inningsPitched', '0.0'),
                'ip_dec': round(ip_dec, 3),
                'er': er,
                'h': h,
                'bb': bb,
                'k': k,
                'bf': bf,
            })

    starts.sort(key=lambda x: x['date'])

    outdoor = [
        s for s in starts
        if not s['is_controlled'] and s['temp_f'] is not None
    ]

    # ── Temperature bucket aggregates ─────────────────────────────────────────
    temp_buckets = [
        _bucket_stats([s for s in outdoor if fn(s['temp_f'])], label)
        for label, fn in TEMP_BUCKETS
    ]

    # ── Per-pitcher aggregates ─────────────────────────────────────────────────
    pitcher_map: dict[str, list] = {}
    for s in starts:
        pitcher_map.setdefault(s['pitcher'], []).append(s)

    per_pitcher = []
    for name, p_starts in pitcher_map.items():
        if len(p_starts) < MIN_STARTS:
            continue
        p_outdoor = [s for s in p_starts if not s['is_controlled'] and s['temp_f'] is not None]
        cold = [s for s in p_outdoor if s['temp_f'] is not None and s['temp_f'] < 60]
        warm = [s for s in p_outdoor if s['temp_f'] is not None and s['temp_f'] >= 70]

        per_pitcher.append({
            'name': name,
            'total_starts': len(p_starts),
            'outdoor_starts': len(p_outdoor),
            'controlled_starts': len(p_starts) - len(p_outdoor),
            'overall_era':  _aggregate_era(p_starts),
            'overall_whip': _aggregate_whip(p_starts),
            'overall_k9':   _aggregate_k9(p_starts),
            'outdoor_era':  _aggregate_era(p_outdoor) if p_outdoor else None,
            'cold_era':  _aggregate_era(cold)  if len(cold)  >= MIN_PITCHER_BUCKET_N else None,
            'warm_era':  _aggregate_era(warm)  if len(warm)  >= MIN_PITCHER_BUCKET_N else None,
            'cold_whip': _aggregate_whip(cold) if len(cold)  >= MIN_PITCHER_BUCKET_N else None,
            'warm_whip': _aggregate_whip(warm) if len(warm)  >= MIN_PITCHER_BUCKET_N else None,
            'cold_k9':   _aggregate_k9(cold)   if len(cold)  >= MIN_PITCHER_BUCKET_N else None,
            'warm_k9':   _aggregate_k9(warm)   if len(warm)  >= MIN_PITCHER_BUCKET_N else None,
            'cold_n': len(cold),
            'warm_n': len(warm),
        })

    per_pitcher.sort(key=lambda x: x['total_starts'], reverse=True)

    # ── Pearson correlation: temperature vs ERA (outdoor starts) ──────────────
    scatter = [
        {'temp_f': s['temp_f'], 'er': s['er'], 'ip_dec': s['ip_dec'],
         'pitcher': s['pitcher'], 'date': s['date'], 'opponent': s['opponent'],
         'era': round(s['er'] * 9 / s['ip_dec'], 2) if s['ip_dec'] > 0 else None}
        for s in outdoor if s['ip_dec'] > 0
    ]

    correlation = None
    valid_scatter = [pt for pt in scatter if pt['era'] is not None]
    if len(valid_scatter) >= 10:
        temps_arr = np.array([pt['temp_f'] for pt in valid_scatter])
        eras_arr  = np.array([pt['era']    for pt in valid_scatter])
        r, p = scipy_stats.pearsonr(temps_arr, eras_arr)
        correlation = {
            'r': round(float(r), 4),
            'p_value': round(float(p), 4),
            'significant': bool(p < 0.05),
            'n': len(valid_scatter),
            'interpretation': (
                f"r = {r:.3f}: {'weak' if abs(r) < 0.3 else 'moderate' if abs(r) < 0.6 else 'strong'} "
                f"{'negative' if r < 0 else 'positive'} correlation between temperature and ERA "
                f"({'statistically significant' if p < 0.05 else 'not statistically significant'} at α = 0.05)."
            ),
        }

    # ── Controlled vs outdoor split ───────────────────────────────────────────
    controlled_starts = [s for s in starts if s['is_controlled']]
    env_comparison = {
        'outdoor': {
            'starts': len(outdoor),
            'era': _aggregate_era(outdoor),
            'whip': _aggregate_whip(outdoor),
            'k9': _aggregate_k9(outdoor),
        },
        'controlled': {
            'starts': len(controlled_starts),
            'era': _aggregate_era(controlled_starts),
            'whip': _aggregate_whip(controlled_starts),
            'k9': _aggregate_k9(controlled_starts),
        },
    }

    result = {
        'meta': {
            'season': SEASON,
            'team': 'Seattle Mariners',
            'total_starts': len(starts),
            'outdoor_starts': len(outdoor),
            'controlled_starts': len(controlled_starts),
            'note': (
                'Temperature analysis uses only outdoor / open-roof starts. '
                'T-Mobile Park has a retractable roof — home starts with the roof closed '
                'are classified as "Controlled Environment" and excluded from temperature analysis. '
                'ERA, WHIP, and K/9 use aggregate rates (total counting stats ÷ total IP), '
                'not averages of per-game rates. '
                'Pearson r measures linear association between game-day temperature and per-start ERA.'
            ),
        },
        'correlation': correlation,
        'temp_buckets': temp_buckets,
        'per_pitcher': per_pitcher,
        'env_comparison': env_comparison,
        'scatter': scatter,
    }

    cache.set(CACHE_KEY, result, CACHE_TTL)
    return result
