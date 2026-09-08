import os


API_KEY = os.getenv("API_KEY")

HEADERS = {
    "x-rapidapi-key": API_KEY,
    "x-rapidapi-host": "sofascore.p.rapidapi.com",
    "Content-Type": "application/json"
}

SPREADSHEET_ID = "1nDFuCEiqZRKpkdCBI9GBt3ck47hFz__dhDpixojJLLM"

LEAGUE_SEASON_LIST = [
    (8, 97268),    # LaLiga
    (17, 96668),   # Premier League
    (23, 95836),   # Serie A
    (325, 87678),  # Brasileirao
    (35, 97464)    # Bundesliga
]
