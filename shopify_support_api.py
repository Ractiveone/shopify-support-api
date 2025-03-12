import os
from flask import Flask, request, jsonify
import requests
import openai

app = Flask(__name__)

# Shopify API Credentials (from environment variables)
SHOPIFY_STORE = "e23hvj-5j.myshopify.com"
SHOPIFY_ACCESS_TOKEN = os.getenv("SHOPIFY_API_KEY")  # Secure from environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # Secure from environment

HEADERS = {
    "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN
}

def get_order_info(order_id=None, customer_name=None):
    """
    Retrieves order details from Shopify using GraphQL based on Order ID or Customer Name.
    """
    url = f"https://{SHOPIFY_STORE}/admin/api/2023-04/graphql.json"

    headers = {
        "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }

    # Define GraphQL query
    graphql_query = """
    query ($query: String!) {
      orders(first: 5, query: $query) {
        edges {
          node {
            id
            name
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
            totalPriceSet {
              presentmentMoney {
                amount
                currencyCode
              }
            }
            createdAt
            financialStatus
            fulfillmentStatus
          }
        }
      }
    }
    """

    # Build GraphQL variables
    if order_id:
        query_value = f"name:#{order_id}"  # Search using visible order number
    elif customer_name:
        query_value = f"customer:{customer_name}"  # Search by customer name
    else:
        return {"error": "No valid search parameter provided."}

    payload = {
        "query": graphql_query,
        "variables": {"query": query_value}
    }

    # Send request to Shopify GraphQL API
    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        data = response.json()
        orders = data.get("data", {}).get("orders", {}).get("edges", [])

        if not orders:
            return {"error": "No order found."}

        # Extract first order
        order_data = orders[0]["node"]

        # Extract tracking info if available
        tracking_info = "No tracking available"
        if order_data.get("fulfillments"):
            tracking = order_data["fulfillments"][0].get("trackingInfo", [{}])
            if tracking and tracking[0].get("number"):
                tracking_info = f"Tracking Number: {tracking[0]['number']} - [Track Order]({tracking[0]['url']})"

        # Build response
        return {
            "order_id": order_data["name"],
            "customer": f"{order_data['customer']['firstName']} {order_data['customer']['lastName']}" if order_data["customer"] else "Unknown",
            "email": order_data["customer"]["email"] if order_data["customer"] else "No email",
            "total_price": f"{order_data['totalPriceSet']['presentmentMoney']['amount']} {order_data['totalPriceSet']['presentmentMoney']['currencyCode']}",
            "status": f"Financial: {order_data['financialStatus']}, Fulfillment: {order_data['fulfillmentStatus']}",
            "tracking_info": tracking_info,
            "created_at": order_data["createdAt"]
        }

    else:
        return {"error": f"GraphQL request failed: {response.status_code}", "details": response.text}

def extract_tracking_number(order):
    """
    Extracts tracking number from Shopify order data.
    """
    fulfillments = order.get("fulfillments", [])
    if fulfillments and "tracking_number" in fulfillments[0]:
        return fulfillments[0]["tracking_number"]
    return None

def get_tracking_info(tracking_number):
    """
    Fetches the latest tracking status from ParcelsApp.
    """
    if not tracking_number:
        return "No tracking number available."
    
    tracking_url = f"https://parcelsapp.com/api/v1/track?tracking_number={tracking_number}"
    response = requests.get(tracking_url)
    
    if response.status_code == 200:
        tracking_data = response.json()
        status = tracking_data.get("status", "No status information available.")
        return f"Current status: {status} - [Tracking link](https://parcelsapp.com/en/tracking/{tracking_number})"
    else:
        return "Error retrieving tracking information."

@app.route('/order_info', methods=['GET'])
def order_info():
    """
    API Endpoint to retrieve order details including tracking.
    """
    order_id = request.args.get('order_id')
    customer_name = request.args.get('customer_name')

    if not order_id and not customer_name:
        return jsonify({"error": "Please provide an order ID or a customer name."}), 400

    order = get_order_info(order_id, customer_name)
    
    return jsonify(order)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
