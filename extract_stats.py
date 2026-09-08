import pandas as pd
import logging
from api_client import get

URL = "https://sofascore.p.rapidapi.com/matches/get-statistics"

def get_stats(headers, match_ids):

    rows = []

    for match_id in match_ids:

        data = get(URL, headers, {"matchId": str(match_id)}, f"stats-{match_id}")

        logging.warning(f"[stats-{match_id}] response keys: {list(data.keys()) if data else data}")
        
        if not data or "statistics" not in data:
            continue

        for period in data["statistics"]:
            for group in period["groups"]:
                for item in group["statisticsItems"]:

                    rows.append({
                        "match_id": match_id,
                        "period": period["period"],
                        "group": group["groupName"],
                        "key": item.get("key"),
                        "home_value": item.get("homeValue"),
                        "away_value": item.get("awayValue")
                    })

    return pd.DataFrame(rows)
