import logging
import requests


def get(url, headers, params=None, name="request"):

    try:

        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=15
        )

        response.raise_for_status()

        return response.json()

    except requests.exceptions.HTTPError as e:

        logging.error(
            f"[{name}] HTTP error: {e} | "
            f"status={response.status_code}"
        )

    except requests.exceptions.RequestException as e:

        logging.error(
            f"[{name}] request error: {e}"
        )

    except ValueError as e:

        logging.error(
            f"[{name}] JSON error: {e}"
        )

    except Exception as e:

        logging.error(
            f"[{name}] unknown error: {e}"
        )

    return None
