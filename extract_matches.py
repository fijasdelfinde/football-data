import pandas as pd
import logging

from api_client import get


URL = "https://sofascore.p.rapidapi.com/tournaments/get-matches"


def get_matches(headers, league_season_list):

    all_matches = []

    # ============================================================
    # RECORRER CADA LIGA + TEMPORADA
    # ============================================================

    for league_id, season_id in league_season_list:

        page_index = 0
        seen_match_ids = set()

        logging.info(
            f"INICIO - Liga {league_id} | Temporada {season_id}"
        )

        # ========================================================
        # PAGINACIÓN
        #
        # Antes:
        #   solo pageIndex = 0
        #
        # Ahora:
        #   pageIndex = 0, 1, 2, 3...
        #   hasta que no haya más datos
        # ========================================================

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

            # Si la API falla
            if not data:
                logging.warning(
                    f"Sin respuesta - Liga {league_id} | "
                    f"Temporada {season_id} | Página {page_index}"
                )
                break

            events = data.get("events", [])

            # Si no hay partidos, terminamos la paginación
            if not events:
                logging.info(
                    f"FIN PAGINACIÓN - Liga {league_id} | "
                    f"Temporada {season_id} | "
                    f"No hay datos en página {page_index}"
                )
                break

            # ====================================================
            # EVITAR REPETIR LA MISMA PÁGINA
            # ====================================================

            current_ids = {
                event.get("id")
                for event in events
                if event.get("id") is not None
            }

            new_ids = current_ids - seen_match_ids

            if not new_ids:

                logging.warning(
                    f"La API repitió datos. "
                    f"Se detiene paginación - Liga {league_id} | "
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
                f"Partidos recibidos: {len(events)} | "
                f"Acumulados: {len(seen_match_ids)}"
            )

            page_index += 1

    # ============================================================
    # SI NO SE RECIBIÓ NADA
    # ============================================================

    if not all_matches:

        logging.error(
            "No se recibieron partidos de ninguna temporada."
        )

        return pd.DataFrame()

    # ============================================================
    # JSON → DATAFRAME
    # ============================================================

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

    # reindex evita que el programa se caiga si alguna columna
    # no viene en una respuesta puntual de la API.
    df = df.reindex(columns=cols)

    # ============================================================
    # FECHA
    # ============================================================

    df["date"] = pd.to_datetime(
        df["startTimestamp"],
        unit="s",
        errors="coerce"
    )

    # ============================================================
    # SOLO PARTIDOS TERMINADOS
    # ============================================================

    df = df[
        df["status.type"] == "finished"
    ].copy()

    # ============================================================
    # RENOMBRAR ID
    # ============================================================

    df = df.rename(
        columns={
            "id": "match_id"
        }
    )

    # ============================================================
    # ELIMINAR DUPLICADOS
    # ============================================================

    df = df.drop_duplicates(
        subset=["match_id"]
    )

    logging.info(
        f"TOTAL PARTIDOS TERMINADOS EXTRAÍDOS: {len(df)}"
    )

    return df
