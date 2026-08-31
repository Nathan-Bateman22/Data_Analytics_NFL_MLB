from django.urls import path
from . import views

urlpatterns = [
    path("seahawks/roster/", views.seahawks_roster, name="seahawks-roster"),
    path("seahawks/players/<str:player_id>/stats/", views.seahawks_player_stats, name="seahawks-player-stats"),
    path("mariners/roster/", views.mariners_roster, name="mariners-roster"),
    path("mariners/players/<str:player_id>/stats/", views.mariners_player_stats, name="mariners-player-stats"),
    path("kraken/roster/", views.kraken_roster, name="kraken-roster"),
    path("kraken/players/<str:player_id>/stats/", views.kraken_player_stats, name="kraken-player-stats"),
    path("nfl/injuries/", views.nfl_injury_analysis, name="nfl-injury-analysis"),
    path("mariners/pitching-temps/", views.mariners_pitching_temps, name="mariners-pitching-temps"),
]
