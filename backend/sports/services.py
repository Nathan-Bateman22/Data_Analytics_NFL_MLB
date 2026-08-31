import requests
from django.core.cache import cache

ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports"

TEAMS = {
    "seahawks": {
        "sport": "football/nfl",
        "team_id": "26",
        "name": "Seattle Seahawks",
        "abbr": "SEA",
        "primary": "#002244",
        "secondary": "#69BE28",
        "accent": "#A5ACAF",
        "headshot_sport": "nfl",
    },
    "mariners": {
        "sport": "baseball/mlb",
        "team_id": "12",
        "name": "Seattle Mariners",
        "abbr": "SEA",
        "primary": "#0C2C56",
        "secondary": "#005C5C",
        "accent": "#C4CED4",
        "headshot_sport": "mlb",
    },
    "kraken": {
        "sport": "hockey/nhl",
        "team_id": "124292",
        "name": "Seattle Kraken",
        "abbr": "SEA",
        "primary": "#001628",
        "secondary": "#99D9D9",
        "accent": "#C8102E",
        "headshot_sport": "nhl",
    },
}


def _fetch_roster(team_key: str) -> dict:
    cache_key = f"roster_{team_key}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    cfg = TEAMS[team_key]
    url = f"{ESPN_BASE}/{cfg['sport']}/teams/{cfg['team_id']}/roster"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    players = []
    for group in data.get("athletes", []):
        position_group = group.get("position", "")
        for athlete in group.get("items", []):
            headshot = athlete.get("headshot", {}).get("href") or (
                f"https://a.espncdn.com/i/headshots/{cfg['headshot_sport']}/players/full/{athlete.get('id')}.png"
            )
            players.append({
                "id": athlete.get("id"),
                "fullName": athlete.get("fullName", ""),
                "firstName": athlete.get("firstName", ""),
                "lastName": athlete.get("lastName", ""),
                "jersey": athlete.get("jersey", "--"),
                "position": athlete.get("position", {}).get("abbreviation", ""),
                "positionGroup": position_group,
                "age": athlete.get("age"),
                "birthPlace": _birth_place(athlete),
                "height": _format_height(athlete.get("displayHeight", "")),
                "weight": athlete.get("displayWeight", ""),
                "experience": athlete.get("experience", {}).get("years"),
                "college": athlete.get("college", {}).get("name", ""),
                "status": athlete.get("status", {}).get("type", ""),
                "headshot": headshot,
            })

    result = {
        "team": {
            "name": cfg["name"],
            "abbr": cfg["abbr"],
            "primary": cfg["primary"],
            "secondary": cfg["secondary"],
            "accent": cfg["accent"],
            "logo": f"https://a.espncdn.com/i/teamlogos/{cfg['headshot_sport'].split('/')[0]}/500/{cfg['abbr'].lower()}.png",
        },
        "players": players,
        "total": len(players),
    }

    cache.set(cache_key, result, timeout=300)
    return result


def _birth_place(athlete: dict) -> str:
    bp = athlete.get("birthPlace", {})
    parts = [bp.get("city"), bp.get("state") or bp.get("country")]
    return ", ".join(p for p in parts if p) or ""


def _format_height(raw: str) -> str:
    return raw


def get_seahawks_roster() -> dict:
    return _fetch_roster("seahawks")


def get_mariners_roster() -> dict:
    return _fetch_roster("mariners")


def get_kraken_roster() -> dict:
    return _fetch_roster("kraken")
