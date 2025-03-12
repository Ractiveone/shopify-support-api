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
    Retrieves order details from Shopify based on Order ID or Customer Name.
    """
    # Base URL for orders
    url = f"https://{SHOPIFY_STORE}/admin/api/2023-04/orders.json"
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN
    }

    params = {}
    if order_id:
        params["name"] = f"#{order_id}"  # Search by visible order number
    elif customer_name:
        params["customer"] = customer_name

    # First request: Get the correct internal Order ID
    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        orders = response.json().get("orders", [])
        if not orders:
            return {"error": "No order found."}
        
        # Get the correct internal order ID
        correct_order_id = orders[0]["id"]
        
        # Fetch full order details using internal ID
        url = f"https://{SHOPIFY_STORE}/admin/api/2023-04/orders/{correct_order_id}.json"
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            order_data = response.json().get("order", {})
            tracking_number = extract_tracking_number(order_data)
            
            # Retrieve tracking info if tracking number exists
            tracking_info = get_tracking_info(tracking_number) if tracking_number else "No tracking number available."
            
            order_data["tracking_info"] = tracking_info
            return order_data
        else:
            return {"error": f"Error retrieving order details: {response.status_code}", "response": response.text}
    
    else:
        return {"error": f"Error retrieving order: {response.status_code}", "response": response.text}


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
