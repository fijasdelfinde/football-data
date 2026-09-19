import os


API_KEY = os.getenv("API_KEY")

HEADERS = {
    "x-rapidapi-key": API_KEY,
    "x-rapidapi-host": "sofascore.p.rapidapi.com",
    "Content-Type": "application/json"
}

SPREADSHEET_ID = "1nDFuCEiqZRKpkdCBI9GBt3ck47hFz__dhDpixojJLLM"

# ============================================================
# TEMPORADAS QUE EL SCRIPT VA A EXTRAER
#
# IMPORTANTE:
# El script NO busca automáticamente todas las temporadas.
# Solo procesa las que aparecen aquí.
#
# Europa:
#   26/27 = temporada actual
#   25/26 = temporada anterior
#
# Brasil:
#   2026 = temporada calendario
# ============================================================

LEAGUE_SEASON_LIST = [

    # LaLiga
    (8, 97268),    # LaLiga 26/27
    (8, 77559),    # LaLiga 25/26

    # Premier League
    (17, 96668),   # Premier League 26/27
    (17, 76986),   # Premier League 25/26

    # Serie A
    (23, 95836),   # Serie A 26/27
    (23, 76457),   # Serie A 25/26

    # Brasileirão
    (325, 87678),  # Brasileirão 2026

    # Bundesliga
    (35, 97464),   # Bundesliga 26/27
    (35, 77333),   # Bundesliga 25/26
]


# Cantidad de días recientes para volver a consultar
# estadísticas de partidos que ya existen.
RECENT_DAYS = 14
