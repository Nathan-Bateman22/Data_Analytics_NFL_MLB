import numpy as np
import pandas as pd
from scipy import stats
from django.core.cache import cache

SEASONS = list(range(2016, 2025))
CACHE_KEY = "nfl_injury_analysis_v3"
CACHE_TTL = 86400  # 24 hours — historical data, no need to refresh often

NON_CONTACT_KEYWORDS = [
    'hamstring', 'quad', 'quadricep', 'calf', 'groin', 'achilles',
    'hip flexor', 'iliopsoas', 'adductor',
]
CONTACT_KEYWORDS = [
    'concussion', 'fracture', 'laceration', 'rib', 'broken',
    'contusion',
]

POSITION_GROUPS = {
    'QB': 'QB', 'RB': 'RB', 'FB': 'RB', 'HB': 'RB',
    'WR': 'WR', 'TE': 'TE',
    'OT': 'OL', 'OG': 'OL', 'OL': 'OL', 'C': 'OL', 'G': 'OL', 'T': 'OL',
    'DE': 'DL', 'DT': 'DL', 'NT': 'DL', 'DL': 'DL',
    'LB': 'LB', 'ILB': 'LB', 'OLB': 'LB', 'MLB': 'LB',
    'CB': 'CB', 'S': 'S', 'SS': 'S', 'FS': 'S', 'DB': 'S',
}
POSITION_ORDER = ['QB', 'RB', 'WR', 'TE', 'OL', 'DL', 'LB', 'CB', 'S']
ACTIVE_PLAYERS_PER_TEAM = 46


def _classify_injury(s):
    if not isinstance(s, str):
        return None
    s = s.lower()
    if any(k in s for k in NON_CONTACT_KEYWORDS):
        return 'non_contact'
    if any(k in s for k in CONTACT_KEYWORDS):
        return 'contact'
    return None


def _classify_surface(s):
    if not isinstance(s, str):
        return None
    s = s.lower()
    if s == 'grass':
        return 'grass'
    if any(k in s for k in ['turf', 'matrix', 'sport', 'astro', 'artificial']):
        return 'turf'
    return None


def _rate_ratio_ci(n_turf, exp_turf, n_grass, exp_grass):
    """Poisson rate ratio (turf vs grass) with Wald 95% CI on log scale."""
    if not all(x > 0 for x in [n_turf, exp_turf, n_grass, exp_grass]):
        return None, None, None
    rr = (n_turf / exp_turf) / (n_grass / exp_grass)
    log_se = np.sqrt(1 / n_turf + 1 / n_grass)
    z = 1.96
    return (
        round(float(rr), 3),
        round(float(np.exp(np.log(rr) - z * log_se)), 3),
        round(float(np.exp(np.log(rr) + z * log_se)), 3),
    )


def compute_injury_analysis():
    cached = cache.get(CACHE_KEY)
    if cached:
        return cached

    import nfl_data_py as nfl

    injuries = nfl.import_injuries(SEASONS)
    schedules = nfl.import_schedules(SEASONS)

    # Build (season, week, team) → surface lookup
    sched = schedules[['season', 'week', 'home_team', 'away_team', 'surface']].dropna(subset=['surface'])
    home_rows = sched[['season', 'week', 'home_team', 'surface']].rename(columns={'home_team': 'team'})
    away_rows = sched[['season', 'week', 'away_team', 'surface']].rename(columns={'away_team': 'team'})
    team_surface = pd.concat([home_rows, away_rows], ignore_index=True)
    team_surface['surface_type'] = team_surface['surface'].apply(_classify_surface)
    team_surface = team_surface.dropna(subset=['surface_type'])

    # Exposures: each team-week = 46 player-game exposures
    exposures = (
        team_surface.groupby('surface_type').size() * ACTIVE_PLAYERS_PER_TEAM
    )
    exp_grass = float(exposures.get('grass', 1))
    exp_turf = float(exposures.get('turf', 1))

    # Classify and join injuries
    inj = injuries[['season', 'week', 'team', 'full_name', 'position',
                     'report_primary_injury']].copy()
    inj['injury_type'] = inj['report_primary_injury'].apply(_classify_injury)
    inj = inj.dropna(subset=['injury_type'])
    inj = inj.merge(
        team_surface[['season', 'week', 'team', 'surface_type']],
        on=['season', 'week', 'team'],
        how='inner',
    )
    # One injury entry per player per week (avoid double-counting from duplicate rows)
    inj = inj.drop_duplicates(subset=['season', 'week', 'team', 'full_name', 'injury_type'])

    # ── Overall ────────────────────────────────────────────────────────────────
    oc = (
        inj.groupby(['surface_type', 'injury_type']).size()
        .unstack(fill_value=0)
        .reindex(index=['grass', 'turf'], columns=['non_contact', 'contact'], fill_value=0)
    )

    def rate(count, exp):
        return round(count / exp * 1000, 4) if exp > 0 else 0

    chi2, p_val, dof, _ = stats.chi2_contingency(oc.values)

    rr_nc, ci_lo_nc, ci_hi_nc = _rate_ratio_ci(
        oc.loc['turf', 'non_contact'], exp_turf,
        oc.loc['grass', 'non_contact'], exp_grass,
    )
    rr_c, ci_lo_c, ci_hi_c = _rate_ratio_ci(
        oc.loc['turf', 'contact'], exp_turf,
        oc.loc['grass', 'contact'], exp_grass,
    )

    overall = {
        'grass': {
            'non_contact': {'count': int(oc.loc['grass', 'non_contact']), 'rate': rate(oc.loc['grass', 'non_contact'], exp_grass)},
            'contact':     {'count': int(oc.loc['grass', 'contact']),     'rate': rate(oc.loc['grass', 'contact'],     exp_grass)},
            'exposure':    int(exp_grass),
        },
        'turf': {
            'non_contact': {'count': int(oc.loc['turf', 'non_contact']), 'rate': rate(oc.loc['turf', 'non_contact'], exp_turf)},
            'contact':     {'count': int(oc.loc['turf', 'contact']),     'rate': rate(oc.loc['turf', 'contact'],     exp_turf)},
            'exposure':    int(exp_turf),
        },
        'chi_square': {
            'statistic': round(float(chi2), 4),
            'p_value':   round(float(p_val), 4),
            'dof':       int(dof),
            'significant': bool(p_val < 0.05),
        },
        'rate_ratio': {
            'non_contact': {'value': rr_nc, 'ci_lower': ci_lo_nc, 'ci_upper': ci_hi_nc},
            'contact':     {'value': rr_c,  'ci_lower': ci_lo_c,  'ci_upper': ci_hi_c},
        },
    }

    # ── By season ──────────────────────────────────────────────────────────────
    season_exp = (
        team_surface.groupby(['season', 'surface_type']).size() * ACTIVE_PLAYERS_PER_TEAM
    ).reset_index(name='exposure')
    season_counts = (
        inj.groupby(['season', 'surface_type', 'injury_type']).size()
        .reset_index(name='count')
    )
    sm = season_counts.merge(season_exp, on=['season', 'surface_type'], how='left')
    sm['rate'] = sm['count'] / sm['exposure'] * 1000

    by_season = []
    for season in sorted(inj['season'].unique()):
        row = {'season': int(season)}
        for surf in ['grass', 'turf']:
            for inj_type in ['non_contact', 'contact']:
                match = sm[
                    (sm['season'] == season) &
                    (sm['surface_type'] == surf) &
                    (sm['injury_type'] == inj_type)
                ]
                row[f'{surf}_{inj_type}_rate'] = round(float(match['rate'].iloc[0]), 4) if len(match) else 0
        by_season.append(row)

    # ── By specific injury keyword ─────────────────────────────────────────────
    specific = {
        'hamstring': 'Hamstring', 'quad': 'Quadricep', 'calf': 'Calf',
        'groin': 'Groin', 'achilles': 'Achilles',
        'concussion': 'Concussion', 'fracture': 'Fracture',
    }
    by_injury_type = []
    for kw, label in specific.items():
        mask = inj['report_primary_injury'].str.lower().str.contains(kw, na=False)
        sub = inj[mask]
        row = {'injury': label}
        for surf, exp in [('grass', exp_grass), ('turf', exp_turf)]:
            cnt = int(sub[sub['surface_type'] == surf].shape[0])
            row[f'{surf}_count'] = cnt
            row[f'{surf}_rate'] = round(cnt / exp * 1000, 4) if exp > 0 else 0
        # rate ratio turf vs grass for each specific injury
        rr, ci_lo, ci_hi = _rate_ratio_ci(
            row['turf_count'], exp_turf, row['grass_count'], exp_grass,
        )
        row['rate_ratio'] = rr
        row['ci_lower'] = ci_lo
        row['ci_upper'] = ci_hi
        by_injury_type.append(row)

    # ── By position group ──────────────────────────────────────────────────────
    inj['pos_group'] = inj['position'].map(POSITION_GROUPS)
    inj_pos = inj.dropna(subset=['pos_group'])

    by_position = []
    for pos in POSITION_ORDER:
        sub = inj_pos[inj_pos['pos_group'] == pos]
        row = {'position': pos}
        for surf, exp in [('grass', exp_grass), ('turf', exp_turf)]:
            s = sub[sub['surface_type'] == surf]
            nc = int(s[s['injury_type'] == 'non_contact'].shape[0])
            c  = int(s[s['injury_type'] == 'contact'].shape[0])
            row[f'{surf}_non_contact_count'] = nc
            row[f'{surf}_contact_count']     = c
            row[f'{surf}_non_contact_rate']  = round(nc / exp * 1000, 4) if exp > 0 else 0
            row[f'{surf}_contact_rate']      = round(c  / exp * 1000, 4) if exp > 0 else 0
        by_position.append(row)

    result = {
        'meta': {
            'seasons': f"{SEASONS[0]}-{SEASONS[-1]}",
            'total_classified': int(len(inj)),
            'data_source': 'NFL Injury Reports (nflverse)',
            'methodology': (
                'Injury reports are administrative filings submitted by teams; they indicate a player '
                'was managed for an injury during the week, not necessarily that the injury occurred '
                'that week. Surface determined from the game schedule each player\'s team played. '
                'Non-contact injuries: soft-tissue (hamstring, quad, calf, groin, achilles). '
                'Contact injuries: traumatic (concussion, fracture, laceration, contusion). '
                'Rates expressed per 1,000 player-game exposures (46 active players × team-games).'
            ),
        },
        'overall': overall,
        'by_season': by_season,
        'by_injury_type': by_injury_type,
        'by_position': by_position,
    }

    cache.set(CACHE_KEY, result, CACHE_TTL)
    return result
