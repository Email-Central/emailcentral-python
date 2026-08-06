import os

from emailcentral import Client, exchange_token, parse_account, read_inbox, refresh_account_token


def main():
    api_key = os.environ["EMAILCENTRAL_API_KEY"]
    client = Client(api_key=api_key)

    products = client.list_products()
    for product in products:
        print(product.id, product.name, product.price_usd, product.stock)

    cents = client.balance()
    print(f"balance: ${cents / 100:.2f}")

    tx_page = client.transactions(page=1)
    for tx in tx_page.transactions:
        print(tx.order_no, tx.amount_cents, tx.status)
    print(f"transactions page {tx_page.page}/{tx_page.total_pages}, total {tx_page.total}")

    orders_page = client.orders(page=1, sort="desc")
    for order in orders_page.purchases:
        print(order.id, order.product_name, order.quantity)
    print(f"orders page {orders_page.page}/{orders_page.total_pages}, total {orders_page.total}")

    graph_products = [p for p in products if p.graph]
    if not graph_products:
        return

    result = client.buy(product_id=graph_products[0].id, quantity=1, idempotency_key="quickstart-example-001")
    print(result.purchase_id, result.new_balance_cents)
    for item in result.items:
        print(item)

    items = client.order_items(result.purchase_id)
    print(items)

    account = parse_account(result.items[0])
    access_token = exchange_token(account.client_id, account.refresh_token)
    messages = read_inbox(access_token, folder="inbox", limit=10)
    for message in messages:
        print(message.date, message.from_, message.subject)

    refreshed = refresh_account_token(account.client_id, account.refresh_token)
    print(f"refreshed token, new refresh token starts with: {refreshed.refresh_token[:12]}...")


if __name__ == "__main__":
    main()
