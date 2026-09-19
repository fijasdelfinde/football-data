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
            "No se extrajeron partidos. "
            "Se detiene el proceso para evitar modificar Sheets."
        )

        return

    # ============================================================
    # LIMPIEZA
    # ============================================================

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
        f"Partidos extraídos y limpios: {len(df_matches)}"
    )

    # ============================================================
    # 2. CONECTAR A GOOGLE SHEETS
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

    else:

        if "match_id" in existing_matches.columns:

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
    # 4. IDENTIFICAR PARTIDOS NUEVOS
    # ============================================================

    new_matches = df_matches[
        ~df_matches["match_id"].isin(
            existing_match_ids
        )
    ].copy()

    logging.info(
        f"Partidos nuevos encontrados: {len(new_matches)}"
    )

    # ============================================================
    # 5. AGREGAR PARTIDOS NUEVOS A GOOGLE SHEETS
    # ============================================================

    if not new_matches.empty:

        ws_matches.append_rows(
            new_matches.values.tolist(),
            value_input_option="USER_ENTERED"
        )

        logging.info(
            f"Se agregaron {len(new_matches)} "
            f"partidos nuevos a Matches."
        )

    # ============================================================
    # 6. IDENTIFICAR PARTIDOS CUYAS ESTADÍSTICAS DEBEMOS
    #    CONSULTAR
    #
    #    A) partidos nuevos
    #    B) partidos recientes
    # ============================================================

    # IDs de partidos nuevos
    new_match_ids = set(
        new_matches["match_id"].astype(str)
    )

    # Fecha límite para refrescar estadísticas
    cutoff_date = (
        datetime.utcnow()
        - timedelta(days=RECENT_DAYS)
    )

    # Copia para trabajar fechas
    df_matches_for_stats = df_matches.copy()

    df_matches_for_stats["date_parsed"] = pd.to_datetime(
        df_matches_for_stats["date"],
        errors="coerce"
    )

    # Partidos de los últimos N días
    recent_matches = df_matches_for_stats[
        df_matches_for_stats["date_parsed"] >= cutoff_date
    ].copy()

    recent_match_ids = set(
        recent_matches["match_id"].astype(str)
    )

    # Unión:
    # nuevos + recientes
    stats_match_ids = sorted(
        new_match_ids | recent_match_ids
    )

    logging.info(
        f"Partidos nuevos para estadísticas: "
        f"{len(new_match_ids)}"
    )

    logging.info(
        f"Partidos recientes para refrescar estadísticas: "
        f"{len(recent_match_ids)}"
    )

    logging.info(
        f"Total partidos a consultar estadísticas: "
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

        # Solo periodo ALL
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
        f"Filas de estadísticas obtenidas: "
        f"{len(df_stats_filtered)}"
    )

    # ============================================================
    # 9. LEER STATS EXISTENTES
    # ============================================================

    existing_stats_data = (
        ws_stats.get_all_records()
    )

    existing_stats = pd.DataFrame(
        existing_stats_data
    )

    # ============================================================
    # 10. REEMPLAZAR STATS DE LOS PARTIDOS REFRESCADOS
    #
    # Esto evita duplicados.
    #
    # Ejemplo:
    #
    # Antes:
    # match 123 → estadísticas antiguas
    #
    # Hoy:
    # match 123 → estadísticas nuevas
    #
    # Resultado:
    # match 123 → SOLO estadísticas nuevas
    # ============================================================

    if not existing_stats.empty:

        if "match_id" in existing_stats.columns:

            existing_stats["match_id"] = (
                existing_stats["match_id"]
                .astype(str)
            )

            # Eliminar del histórico las estadísticas
            # de los partidos que estamos refrescando.
            existing_stats_to_keep = (
                existing_stats[
                    ~existing_stats["match_id"].isin(
                        stats_match_ids
                    )
                ].copy()
            )

        else:

            existing_stats_to_keep = (
                existing_stats.copy()
            )

    else:

        existing_stats_to_keep = pd.DataFrame(
            columns=[
                "match_id",
                "group",
                "key",
                "home_value",
                "away_value"
            ]
        )

    # ============================================================
    # 11. COMBINAR HISTÓRICO + ESTADÍSTICAS ACTUALIZADAS
    # ============================================================

    final_stats = pd.concat(
        [
            existing_stats_to_keep,
            df_stats_filtered
        ],
        ignore_index=True
    )

    if not final_stats.empty:

        final_stats = final_stats[
            [
                "match_id",
                "group",
                "key",
                "home_value",
                "away_value"
            ]
        ]

        final_stats["match_id"] = (
            final_stats["match_id"]
            .astype(str)
        )

        final_stats = (
            final_stats
            .drop_duplicates(
                subset=["match_id", "key"],
                keep="last"
            )
        )

    # ============================================================
    # 12. ACTUALIZAR HOJA STATS
    #
    # Se conserva el histórico y se reemplazan solamente
    # las estadísticas de los partidos refrescados.
    # ============================================================

    if stats_match_ids:

        ws_stats.clear()

        headers_stats = [
            "match_id",
            "group",
            "key",
            "home_value",
            "away_value"
        ]

        ws_stats.append_row(
            headers_stats,
            value_input_option="USER_ENTERED"
        )

        if not final_stats.empty:

            ws_stats.append_rows(
                final_stats.values.tolist(),
                value_input_option="USER_ENTERED"
            )

        logging.info(
            "Hoja Stats actualizada correctamente."
        )

    else:

        logging.info(
            "No hubo estadísticas nuevas ni recientes "
            "para actualizar."
        )

    # ============================================================
    # 13. RESUMEN FINAL
    # ============================================================

    logging.info("==========================================")
    logging.info("ACTUALIZACIÓN TERMINADA")
    logging.info(
        f"Total partidos extraídos: {len(df_matches)}"
    )
    logging.info(
        f"Nuevos partidos agregados: {len(new_matches)}"
    )
    logging.info(
        f"Partidos consultados para estadísticas: "
        f"{len(stats_match_ids)}"
    )
    logging.info(
        f"Filas de estadísticas obtenidas: "
        f"{len(df_stats_filtered)}"
    )
    logging.info("==========================================")


if __name__ == "__main__":
    main()
