# emailcentralpy

Python SDK for the Email Central API.

## Install

```
pip install emailcentralpy
```

Requires Python 3.10+. The only dependency is `requests`.

## Quickstart

### Construct a client

```python
from emailcentral import Client

client = Client(api_key="YOUR_API_KEY")
```

By default the client talks to `https://email-central.net/api/v1`. Pass `base_url=` to point it elsewhere (e.g. a staging environment):

```python
client = Client(api_key="YOUR_API_KEY", base_url="https://staging.email-central.net/api/v1")
```

### List products

```python
products = client.list_products()
for p in products:
    print(p.id, p.name, p.price_usd, p.stock)
```

`price_mills` on `Product` is the raw price in mills (1/1000 of a dollar) as returned by the API. `price_usd` is a convenience property that divides it by 1000.

### Check balance

```python
cents = client.balance()
print(f"${cents / 100:.2f}")
```

### Buy accounts

```python
result = client.buy(product_id=1, quantity=5)
print(result.purchase_id, result.new_balance_cents)
for item in result.items:
    print(item)
```

To make a purchase safely retryable (e.g. if your process crashes or the connection drops mid-request), pass an `idempotency_key`. Reusing the same key returns the original purchase result instead of charging again:

```python
result = client.buy(product_id=1, quantity=5, idempotency_key="order-2026-08-05-001")
```

If you reuse a key while the original call is still in flight, the API responds with `409 request_in_progress`, which surfaces as an `APIError` with `code == "request_in_progress"`.

Each string in `result.items` is one purchased account, in the form `email:password` or, for Graph-capable products, `email:password:refreshToken:clientId`.

### List transactions

```python
page = client.transactions(page=1)
for tx in page.transactions:
    print(tx.order_no, tx.amount_cents, tx.status)
print(page.page, page.total_pages, page.total)
```

### Handling errors

Any non-2xx response raises `emailcentral.APIError`, with `status` (HTTP status code), `code` (the API's error string), and `message`:

```python
from emailcentral import APIError

try:
    client.buy(product_id=999, quantity=1)
except APIError as e:
    print(e.status, e.code, e.message)
```

### Reading a Graph inbox

If a purchased item came from a Graph-capable product, its string includes a refresh token and client ID that let you read the mailbox directly through Microsoft Graph. This path never touches the Email Central API or your API key.

```python
from emailcentral import parse_account, exchange_token, read_inbox

result = client.buy(product_id=1, quantity=1)
account = parse_account(result.items[0])

access_token = exchange_token(account.client_id, account.refresh_token)

messages = read_inbox(access_token, folder="inbox", limit=10)
for m in messages:
    print(m.date, m.from_, m.subject)
```

`folder` is one of `"inbox"`, `"junk"`, or `"all"`.

Note: on `Message`, the sender field is named `from_` (with a trailing underscore) because `from` is a reserved word in Python.

`parse_account` splits on `:` and takes the email as the first field and the client ID as the last field; everything in between is rejoined with `:` as the refresh token, since refresh tokens can themselves contain colons. It raises `ValueError` if the string doesn't have at least 4 `:`-separated parts.

### Keeping a Graph token from expiring

A refresh token is valid for 90 days from when the account was created. Every exchange against Microsoft's official token endpoint issues a brand new refresh token and resets that window, so calling `refresh_account_token` periodically - even on accounts you're not actively reading mail from - keeps them alive indefinitely.

```python
from emailcentral import refresh_account_token

refreshed = refresh_account_token(account.client_id, account.refresh_token)
# refreshed.access_token can be discarded if you're just keeping the account alive
# refreshed.refresh_token replaces the old one - the old one is now invalid
```

Run this on a schedule (daily or weekly is plenty) well before the 90-day mark for any account you're holding onto. Each exchange invalidates the refresh token that was passed in, so the value you get back must be what you use next time.

## Examples

A complete, runnable script covering every method (`list_products`, `balance`, `transactions`, `orders`, `buy`, `order_items`, and the Graph flow) is in [`examples/quickstart.py`](examples/quickstart.py). It reads the API key from the `EMAILCENTRAL_API_KEY` environment variable:

```
EMAILCENTRAL_API_KEY=your-key python examples/quickstart.py
```

## Error codes

These are the `code` values you may see on a raised `APIError`, with the HTTP status they come with.

| Status | Code | Meaning |
|---|---|---|
| 401 | `unauthorized` | API key missing, invalid, or revoked |
| 400 | `invalid_body` | Request body failed validation (e.g. bad `productId`/`quantity`) |
| 415 | `unsupported_media_type` | Request `Content-Type` was not accepted |
| 413 | `payload_too_large` | Request body exceeded the size limit |
| 404 | `product_not_found` | No product exists with the given `productId` |
| 400 | `insufficient_balance` | Account balance too low to complete the purchase |
| 400 | `insufficient_stock` | Not enough stock left for the requested quantity |
| 400 | `purchase_failed` | Purchase could not be completed for another reason |
| 409 | `request_in_progress` | The same `Idempotency-Key` is already being processed |
| 500 | `internal_error` | Server-side error |
| 429 | `rate_limited` | Too many requests; back off and retry |

`unauthorized` and `rate_limited` can be returned by every endpoint (`list_products`, `buy`, `balance`, `transactions`), not just `buy`.
