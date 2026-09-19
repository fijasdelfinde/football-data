import pandas as pd

from api_client import get


URL = "https://sofascore.p.rapidapi.com/matches/get-statistics"


def get_stats(headers, match_ids):

    rows = []

    for match_id in match_ids:

        data = get(
            URL,
            headers,
            {"matchId": str(match_id)},
            f"stats-{match_id}"
        )

        if not data:
            continue

        if "statistics" not in data:
            continue

        for period in data["statistics"]:

            for group in period.get("groups", []):

                for item in group.get("statisticsItems", []):

                    rows.append({
                        "match_id": str(match_id),
                        "period": period.get("period"),
                        "group": group.get("groupName"),
                        "key": item.get("key"),
                        "home_value": item.get("homeValue"),
                        "away_value": item.get("awayValue")
                    })

    return pd.DataFrame(rows)
