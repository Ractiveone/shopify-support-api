import os
import logging
from flask import Flask, request, jsonify
import requests

# Flask App initialisieren
app = Flask(__name__)

# Logging konfigurieren
logging.basicConfig(level=logging.INFO)

# Shopify API Credentials aus Umgebungsvariablen
SHOPIFY_STORE = os.getenv("SHOPIFY_STORE", "e23hvj-5j.myshopify.com")
SHOPIFY_ACCESS_TOKEN = os.getenv("SHOPIFY_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# API Headers für Shopify
HEADERS = {
    "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
    "Content-Type": "application/json"
}

def get_order_info(order_id=None, customer_name=None):
    """
    Ruft Bestellinformationen aus Shopify ab.
    Falls keine Parameter angegeben sind, werden die letzten 5 Bestellungen abgerufen.
    """
    url = f"https://{SHOPIFY_STORE}/admin/api/2023-04/graphql.json"

    query {
  orders(first: 5) {
    edges {
      node {
        id
        name
        createdAt
        displayFinancialStatus  # ERSETZT financialStatus
        displayFulfillmentStatus  # ERSETZT fulfillmentStatus
        totalPriceSet {
          presentmentMoney {
            amount
            currencyCode
          }
        }
        customer {
          firstName
          lastName
          email
        }
        fulfillments {
          trackingInfo {
            number
            url
          }
        }
      }
    }
  }
}

    # Falls keine Order-ID oder kein Kundenname übergeben wurde → Alle Bestellungen abrufen
    query_value = None
    if order_id:
        query_value = f"name:#{order_id}"
    elif customer_name:
        query_value = f"customer:{customer_name}"

    payload = {"query": graphql_query, "variables": {"query": query_value}}

    logging.info(f"GraphQL Request an Shopify: {payload}")

    response = requests.post(url, headers=HEADERS, json=payload)
    
    if response.status_code != 200:
        logging.error(f"GraphQL-Anfrage fehlgeschlagen: {response.status_code} - {response.text}")
        return {"error": f"GraphQL-Anfrage fehlgeschlagen: {response.status_code}", "details": response.text}
    
    data = response.json()
    orders = data.get("data", {}).get("orders", {}).get("edges", [])

    if not orders:
        logging.warning("Keine Bestellungen gefunden.")
        return {"error": "Keine Bestellungen gefunden."}

    bestell_liste = []
    for order in orders:
        order_data = order["node"]
        tracking_info = "Keine Tracking-Informationen verfügbar"
        if order_data.get("fulfillments"):
            tracking = order_data["fulfillments"][0].get("trackingInfo", [{}])
            if tracking and tracking[0].get("number"):
                tracking_info = f"Tracking-Nummer: {tracking[0]['number']} - [Sendungsverfolgung]({tracking[0]['url']})"

        bestell_liste.append({
            "order_id": order_data["name"],
            "customer": f"{order_data['customer']['firstName']} {order_data['customer']['lastName']}" if order_data["customer"] else "Unbekannt",
            "email": order_data["customer"]["email"] if order_data["customer"] else "Keine E-Mail verfügbar",
            "total_price": f"{order_data['totalPriceSet']['presentmentMoney']['amount']} {order_data['totalPriceSet']['presentmentMoney']['currencyCode']}",
            "status": f"Finanzstatus: {order_data['financialStatus']}, Erfüllungsstatus: {order_data['fulfillmentStatus']}",
            "tracking_info": tracking_info,
            "created_at": order_data["createdAt"]
        })

    logging.info(f"{len(bestell_liste)} Bestellungen gefunden.")
    return bestell_liste

@app.route('/order_info', methods=['GET'])
def order_info():
    """
    API-Endpoint für die Bestellinformationen inkl. Tracking.
    Falls keine Parameter angegeben sind, gibt er die letzten 5 Bestellungen zurück.
    """
    order_id = request.args.get('order_id')
    customer_name = request.args.get('customer_name')

    logging.info(f"Angefragte Order ID: {order_id}, Kundenname: {customer_name}")

    # Falls keine Parameter übergeben wurden, hole alle Bestellungen
    orders = get_order_info(order_id, customer_name)
    
    return jsonify(orders)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
