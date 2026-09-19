import pandas as pd
import logging

from api_client import get


URL = "https://sofascore.p.rapidapi.com/tournaments/get-matches"


def get_matches(headers, league_season_list):

    all_matches = []

    for league_id, season_id in league_season_list:

        page_index = 0
        seen_match_ids = set()

        logging.info(
            f"INICIO - Liga {league_id} | Temporada {season_id}"
        )

        while True:

            data = get(
                URL,
                headers,
                {
                    "tournamentId": str(league_id),
                    "seasonId": str(season_id),
                    "pageIndex": str(page_index)
                },
                f"matches-{league_id}-{season_id}-page-{page_index}"
            )

            if not data:
                logging.warning(
                    f"Sin respuesta - Liga {league_id} | "
                    f"Temporada {season_id} | "
                    f"Página {page_index}"
                )
                break

            events = data.get("events", [])

            if not events:
                logging.info(
                    f"FIN PAGINACIÓN - Liga {league_id} | "
                    f"Temporada {season_id}"
                )
                break

            current_ids = {
                event.get("id")
                for event in events
                if event.get("id") is not None
            }

            new_ids = current_ids - seen_match_ids

            if not new_ids:
                logging.warning(
                    f"La API repitió datos. "
                    f"Se detiene paginación - "
                    f"Liga {league_id} | "
                    f"Temporada {season_id} | "
                    f"Página {page_index}"
                )
                break

            seen_match_ids.update(current_ids)

            all_matches.extend(events)

            logging.info(
                f"Liga {league_id} | "
                f"Temporada {season_id} | "
                f"Página {page_index} | "
                f"Partidos: {len(events)} | "
                f"Acumulados: {len(seen_match_ids)}"
            )

            page_index += 1

    if not all_matches:
        logging.error(
            "No se recibieron partidos."
        )
        return pd.DataFrame()

    df = pd.json_normalize(all_matches)

    cols = [
        "id",
        "startTimestamp",
        "tournament.category.id",
        "tournament.category.name",
        "tournament.id",
        "tournament.name",
        "season.id",
        "season.year",
        "roundInfo.round",
        "homeTeam.id",
        "homeTeam.name",
        "homeTeam.nameCode",
        "awayTeam.id",
        "awayTeam.name",
        "awayTeam.nameCode",
        "homeScore.current",
        "awayScore.current",
        "status.type",
        "winnerCode",
        "homeRedCards",
        "awayRedCards"
    ]

    df = df.reindex(columns=cols)

    df["date"] = pd.to_datetime(
        df["startTimestamp"],
        unit="s",
        errors="coerce"
    )

    # Solo partidos terminados
    df = df[
        df["status.type"] == "finished"
    ].copy()

    df = df.rename(
        columns={"id": "match_id"}
    )

    df["match_id"] = df["match_id"].astype(str)

    df = df.drop_duplicates(
        subset=["match_id"]
    )

    logging.info(
        f"TOTAL PARTIDOS TERMINADOS: {len(df)}"
    )

    return df
