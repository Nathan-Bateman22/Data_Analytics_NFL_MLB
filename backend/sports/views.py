from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .services import get_seahawks_roster, get_mariners_roster, get_kraken_roster
from .player_stats import get_player_stats
from .player_stats_mlb import get_mlb_player_stats
from .player_stats_nhl import get_nhl_player_stats
from .injury_analysis import compute_injury_analysis
from .mariners_pitching_temps import compute_pitching_temp_analysis


@api_view(["GET"])
def seahawks_roster(request):
    try:
        return Response(get_seahawks_roster())
    except Exception as exc:
        return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)


@api_view(["GET"])
def mariners_roster(request):
    try:
        return Response(get_mariners_roster())
    except Exception as exc:
        return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)


@api_view(["GET"])
def kraken_roster(request):
    try:
        return Response(get_kraken_roster())
    except Exception as exc:
        return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)


@api_view(["GET"])
def seahawks_player_stats(request, player_id):
    try:
        roster = get_seahawks_roster()
        player_info = next(
            (p for p in roster['players'] if str(p['id']) == str(player_id)), None
        )
        if player_info is None:
            return Response({"error": "Player not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(get_player_stats(player_id, player_info))
    except Exception as exc:
        return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)


@api_view(["GET"])
def mariners_player_stats(request, player_id):
    try:
        roster = get_mariners_roster()
        player_info = next(
            (p for p in roster['players'] if str(p['id']) == str(player_id)), None
        )
        if player_info is None:
            return Response({"error": "Player not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(get_mlb_player_stats(player_id, player_info))
    except Exception as exc:
        return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)


@api_view(["GET"])
def kraken_player_stats(request, player_id):
    try:
        roster = get_kraken_roster()
        player_info = next(
            (p for p in roster['players'] if str(p['id']) == str(player_id)), None
        )
        if player_info is None:
            return Response({"error": "Player not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(get_nhl_player_stats(player_id, player_info))
    except Exception as exc:
        return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)


@api_view(["GET"])
def nfl_injury_analysis(request):
    try:
        return Response(compute_injury_analysis())
    except Exception as exc:
        return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)


@api_view(["GET"])
def mariners_pitching_temps(request):
    try:
        return Response(compute_pitching_temp_analysis())
    except Exception as exc:
        return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
