import logging
from datetime import datetime, timedelta

import pandas as pd

from config import (
    HEADERS,
    SPREADSHEET_ID,
    LEAGUE_SEASON_LIST,
    RECENT_DAYS
)

from extract_matches import get_matches
from extract_stats import get_stats
from load_sheets import connect_sheets
from utils import setup_logging


def main():

    setup_logging()

    logging.info("==========================================")
    logging.info("INICIO ACTUALIZACIÓN FOOTBALL DATA")
    logging.info("==========================================")

    # ============================================================
    # 1. EXTRAER TODOS LOS PARTIDOS
    # ============================================================

    df_matches = get_matches(
        HEADERS,
        LEAGUE_SEASON_LIST
    )

    if df_matches.empty:

        logging.error(
            "No se extrajeron partidos."
        )

        return

    df_matches = df_matches.fillna("")

    df_matches["match_id"] = (
        df_matches["match_id"]
        .astype(str)
    )

    df_matches["date"] = (
        df_matches["date"]
        .astype(str)
    )

    df_matches = df_matches.drop_duplicates(
        subset=["match_id"]
    )

    logging.info(
        f"Partidos extraídos: {len(df_matches)}"
    )

    # ============================================================
    # 2. CONECTAR GOOGLE SHEETS
    # ============================================================

    ws_matches, ws_stats = connect_sheets(
        "creds.json",
        SPREADSHEET_ID
    )

    # ============================================================
    # 3. LEER MATCHES EXISTENTES
    # ============================================================

    existing_matches_data = (
        ws_matches.get_all_records()
    )

    existing_matches = pd.DataFrame(
        existing_matches_data
    )

    if existing_matches.empty:

        existing_match_ids = set()

    elif "match_id" in existing_matches.columns:

        existing_matches["match_id"] = (
            existing_matches["match_id"]
            .astype(str)
        )

        existing_match_ids = set(
            existing_matches["match_id"]
        )

    else:

        existing_match_ids = set()

    # ============================================================
    # 4. SOLO PARTIDOS NUEVOS
    # ============================================================

    new_matches = df_matches[
        ~df_matches["match_id"].isin(
            existing_match_ids
        )
    ].copy()

    logging.info(
        f"Partidos nuevos: {len(new_matches)}"
    )

    # ============================================================
    # 5. AGREGAR PARTIDOS NUEVOS
    # ============================================================

    if not new_matches.empty:

        ws_matches.append_rows(
            new_matches.values.tolist(),
            value_input_option="USER_ENTERED"
        )

        logging.info(
            f"Agregados {len(new_matches)} "
            f"partidos nuevos a Matches."
        )

    # ============================================================
    # 6. DEFINIR PARTIDOS PARA ACTUALIZAR ESTADÍSTICAS
    #
    # Nuevos + últimos RECENT_DAYS días
    # ============================================================

    new_match_ids = set(
        new_matches["match_id"].astype(str)
    )

    df_matches_dates = df_matches.copy()

    df_matches_dates["date_parsed"] = pd.to_datetime(
        df_matches_dates["date"],
        errors="coerce"
    )

    cutoff_date = (
        datetime.utcnow()
        - timedelta(days=RECENT_DAYS)
    )

    recent_matches = df_matches_dates[
        df_matches_dates["date_parsed"] >= cutoff_date
    ]

    recent_match_ids = set(
        recent_matches["match_id"]
        .astype(str)
    )

    stats_match_ids = sorted(
        new_match_ids | recent_match_ids
    )

    logging.info(
        f"Partidos nuevos para estadísticas: "
        f"{len(new_match_ids)}"
    )

    logging.info(
        f"Partidos recientes para refrescar: "
        f"{len(recent_match_ids)}"
    )

    logging.info(
        f"TOTAL estadísticas a consultar: "
        f"{len(stats_match_ids)}"
    )

    # ============================================================
    # 7. EXTRAER ESTADÍSTICAS
    # ============================================================

    if stats_match_ids:

        df_stats = get_stats(
            HEADERS,
            stats_match_ids
        )

    else:

        df_stats = pd.DataFrame()

    # ============================================================
    # 8. PROCESAR ESTADÍSTICAS
    # ============================================================

    if not df_stats.empty:

        df_stats_filtered = df_stats[
            df_stats["period"] == "ALL"
        ].copy()

        df_stats_filtered = df_stats_filtered[
            [
                "match_id",
                "group",
                "key",
                "home_value",
                "away_value"
            ]
        ]

        df_stats_filtered["match_id"] = (
            df_stats_filtered["match_id"]
            .astype(str)
        )

        df_stats_filtered = (
            df_stats_filtered
            .drop_duplicates(
                subset=["match_id", "key"]
            )
        )

        df_stats_filtered = (
            df_stats_filtered
            .fillna("")
        )

    else:

        df_stats_filtered = pd.DataFrame(
            columns=[
                "match_id",
                "group",
                "key",
                "home_value",
                "away_value"
            ]
        )

    logging.info(
        f"Estadísticas recibidas: "
        f"{len(df_stats_filtered)} filas"
    )

    # ============================================================
    # 9. LEER STATS ACTUALES
    # ============================================================

    existing_stats_data = (
        ws_stats.get_all_records()
    )

    existing_stats = pd.DataFrame(
        existing_stats_data
    )

    # ============================================================
    # 10. CREAR MAPA DE FILAS EXISTENTES
    #
    # CLAVE ÚNICA:
    # match_id + key
    #
    # Así:
    # partido 123 + ballPossession
    # es una fila única.
    # ============================================================

    existing_row_map = {}

    if not existing_stats.empty:

        if "match_id" in existing_stats.columns:

            existing_stats["match_id"] = (
                existing_stats["match_id"]
                .astype(str)
            )

        if "key" in existing_stats.columns:

            for idx, row in existing_stats.iterrows():

                match_id = str(
                    row.get("match_id", "")
                )

                key = str(
                    row.get("key", "")
                )

                if match_id and key:

                    # +2 porque:
                    # fila 1 = encabezados
                    # dataframe comienza en índice 0
                    existing_row_map[
                        (match_id, key)
                    ] = idx + 2

    # ============================================================
    # 11. ACTUALIZAR O INSERTAR STATS
    # ============================================================

    rows_to_append = []

    updated_count = 0
    inserted_count = 0

    for _, row in df_stats_filtered.iterrows():

        match_id = str(
            row["match_id"]
        )

        key = str(
            row["key"]
        )

        values = [
            match_id,
            row["group"],
            key,
            row["home_value"],
            row["away_value"]
        ]

        unique_key = (
            match_id,
            key
        )

        # --------------------------------------------------------
        # YA EXISTE → ACTUALIZAR
        # --------------------------------------------------------

        if unique_key in existing_row_map:

            row_number = existing_row_map[
                unique_key
            ]

            ws_stats.update(
                f"A{row_number}:E{row_number}",
                [values],
                value_input_option="USER_ENTERED"
            )

            updated_count += 1

        # --------------------------------------------------------
        # NO EXISTE → AGREGAR
        # --------------------------------------------------------

        else:

            rows_to_append.append(
                values
            )

            # Lo agregamos al mapa para evitar
            # duplicados dentro de la misma ejecución.
            existing_row_map[
                unique_key
            ] = -1

            inserted_count += 1

    # ============================================================
    # 12. INSERTAR NUEVAS ESTADÍSTICAS EN BLOQUE
    # ============================================================

    if rows_to_append:

        ws_stats.append_rows(
            rows_to_append,
            value_input_option="USER_ENTERED"
        )

    logging.info(
        f"Estadísticas actualizadas: {updated_count}"
    )

    logging.info(
        f"Estadísticas nuevas: {inserted_count}"
    )

    # ============================================================
    # 13. RESUMEN
    # ============================================================

    logging.info("==========================================")
    logging.info("ACTUALIZACIÓN TERMINADA")
    logging.info(
        f"Total partidos encontrados: "
        f"{len(df_matches)}"
    )
    logging.info(
        f"Nuevos partidos agregados: "
        f"{len(new_matches)}"
    )
    logging.info(
        f"Partidos revisados para estadísticas: "
        f"{len(stats_match_ids)}"
    )
    logging.info(
        f"Stats actualizadas: "
        f"{updated_count}"
    )
    logging.info(
        f"Stats nuevas: "
        f"{inserted_count}"
    )
    logging.info("==========================================")


if __name__ == "__main__":
    main()
