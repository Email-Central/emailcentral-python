from __future__ import annotations

from dataclasses import dataclass

import requests

TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"

FOLDER_TO_GRAPH_NAME = {
    "inbox": "inbox",
    "junk": "junkemail",
}


@dataclass
class Account:
    email: str
    password: str
    refresh_token: str
    client_id: str


@dataclass
class Message:
    id: str
    subject: str
    from_: str
    date: str


@dataclass
class RefreshedTokens:
    access_token: str
    refresh_token: str


def parse_account(raw: str) -> Account:
    parts = raw.split(":")
    if len(parts) < 4:
        raise ValueError(f"invalid account string: {raw!r}")
    email, password = parts[0], parts[1]
    client_id = parts[-1]
    refresh_token = ":".join(parts[2:-1])
    return Account(email=email, password=password, refresh_token=refresh_token, client_id=client_id)


def _request_token(client_id: str, refresh_token: str) -> dict:
    response = requests.post(
        TOKEN_URL,
        data={
            "client_id": client_id,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "scope": "https://graph.microsoft.com/.default offline_access",
        },
    )
    response.raise_for_status()
    return response.json()


def exchange_token(client_id: str, refresh_token: str) -> str:
    return _request_token(client_id, refresh_token)["access_token"]


def refresh_account_token(client_id: str, refresh_token: str) -> RefreshedTokens:
    data = _request_token(client_id, refresh_token)
    return RefreshedTokens(access_token=data["access_token"], refresh_token=data["refresh_token"])


def read_inbox(access_token: str, folder: str = "inbox", limit: int = 10) -> list[Message]:
    select = "id,subject,from,receivedDateTime"
    if folder == "all":
        url = f"{GRAPH_BASE_URL}/me/messages"
    else:
        url = f"{GRAPH_BASE_URL}/me/mailFolders/{FOLDER_TO_GRAPH_NAME[folder]}/messages"
    response = requests.get(
        url,
        params={"$top": limit, "$orderby": "receivedDateTime desc", "$select": select},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    response.raise_for_status()
    messages = []
    for item in response.json()["value"]:
        email_address = (item.get("from") or {}).get("emailAddress") or {}
        name = email_address.get("name")
        address = email_address.get("address")
        if name:
            from_ = f"{name} <{address}>"
        elif address:
            from_ = address
        else:
            from_ = ""
        messages.append(Message(id=item["id"], subject=item["subject"], from_=from_, date=item["receivedDateTime"]))
    return messages
