from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests

DEFAULT_BASE_URL = "https://email-central.net/api/v1"


class APIError(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.status = status
        self.code = code
        self.message = message


@dataclass
class Product:
    id: int
    name: str
    price_mills: int
    stock: int
    life: str
    web_login: bool
    imap: bool
    graph: bool
    pop3: bool
    api_inbox_access: bool
    icon: str
    prefix_type: str
    warranty: bool
    description: str
    coming_soon: bool

    @property
    def price_usd(self) -> float:
        return self.price_mills / 1000


@dataclass
class BuyResult:
    purchase_id: int
    new_balance_cents: int
    items: list[str]


@dataclass
class Transaction:
    id: int
    order_no: str
    amount_cents: int
    method: str
    status: str
    created_at: int
    pay_amount: float | None
    pay_currency: str | None


@dataclass
class TransactionsPage:
    transactions: list[Transaction]
    page: int
    total_pages: int
    total: int


@dataclass
class Order:
    id: int
    product_id: int
    product_name: str
    quantity: int
    total_mills: int
    created_at: int


@dataclass
class OrdersPage:
    purchases: list[Order]
    total: int
    page: int
    total_pages: int
    sort: str


class Client:
    def __init__(self, api_key: str, base_url: str = DEFAULT_BASE_URL) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        headers = dict(kwargs.pop("headers", None) or {})
        headers["Authorization"] = f"Bearer {self.api_key}"
        response = self.session.request(method, f"{self.base_url}{path}", headers=headers, **kwargs)
        try:
            data = response.json()
        except ValueError:
            raise APIError(response.status_code, "invalid_response", response.text) from None
        if not response.ok:
            raise APIError(response.status_code, data.get("error", "unknown_error"), data.get("message", ""))
        return data

    def list_products(self) -> list[Product]:
        data = self._request("GET", "/products")
        return [
            Product(
                id=p["id"],
                name=p["name"],
                price_mills=p["priceMills"],
                stock=p["stock"],
                life=p["life"],
                web_login=p["webLogin"],
                imap=p["imap"],
                graph=p["graph"],
                pop3=p["pop3"],
                api_inbox_access=p["apiInboxAccess"],
                icon=p["icon"],
                prefix_type=p["prefixType"],
                warranty=p["warranty"],
                description=p["description"],
                coming_soon=p["comingSoon"],
            )
            for p in data["products"]
        ]

    def buy(self, product_id: int, quantity: int, idempotency_key: str | None = None) -> BuyResult:
        headers = {"Idempotency-Key": idempotency_key} if idempotency_key is not None else {}
        data = self._request(
            "POST",
            "/buy",
            json={"productId": product_id, "quantity": quantity},
            headers=headers,
        )
        return BuyResult(
            purchase_id=data["purchaseId"],
            new_balance_cents=data["newBalanceCents"],
            items=data["items"],
        )

    def balance(self) -> int:
        data = self._request("GET", "/balance")
        return data["balanceCents"]

    def transactions(self, page: int = 1) -> TransactionsPage:
        data = self._request("GET", "/transactions", params={"page": page})
        return TransactionsPage(
            transactions=[
                Transaction(
                    id=t["id"],
                    order_no=t["orderNo"],
                    amount_cents=t["amountCents"],
                    method=t["method"],
                    status=t["status"],
                    created_at=t["createdAt"],
                    pay_amount=t["payAmount"],
                    pay_currency=t["payCurrency"],
                )
                for t in data["transactions"]
            ],
            page=data["page"],
            total_pages=data["totalPages"],
            total=data["total"],
        )

    def orders(self, page: int = 1, sort: str = "desc") -> OrdersPage:
        data = self._request("GET", "/orders", params={"page": page, "sort": sort})
        return OrdersPage(
            purchases=[
                Order(
                    id=o["id"],
                    product_id=o["productId"],
                    product_name=o["productName"],
                    quantity=o["quantity"],
                    total_mills=o["totalMills"],
                    created_at=o["createdAt"],
                )
                for o in data["purchases"]
            ],
            total=data["total"],
            page=data["page"],
            total_pages=data["totalPages"],
            sort=data["sort"],
        )

    def order_items(self, order_id: int) -> list[str]:
        data = self._request("GET", f"/orders/{order_id}")
        return data["items"]
