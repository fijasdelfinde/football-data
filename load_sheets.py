import gspread
from google.oauth2.service_account import Credentials


def connect_sheets(service_file, spreadsheet_id):

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = Credentials.from_service_account_file(
        service_file,
        scopes=scopes
    )

    gc = gspread.authorize(creds)

    sh = gc.open_by_key(spreadsheet_id)

    return (
        sh.worksheet("Matches"),
        sh.worksheet("Stats")
    )
