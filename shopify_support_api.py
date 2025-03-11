from flask import Flask, request, jsonify
import requests
import openai

app = Flask(__name__)
# Shopify API credentials
SHOPIFY_STORE = "www.ractiveone.com"
API_KEY = "b756755fd0290c14bacad6d371d9081f"
PASSWORD = "0d3687e149dd68ceaba840e6f7652b71"

# OpenAI API Key
OPENAI_API_KEY = "ysk-proj-4amXuDVshljXIbrc1zovWTG9mSNnzZhbWP-JWBBNoJerJAvHwnCB-iax-XaQPk3wzbeVSpvt5bT3BlbkFJkkP3AeyCKGSsoDDLDdhi-7BEmqvPiCA68NZz4KAPuNR8I4l3YTzpSMxWQ3wxoPPxkqHLxHhXYA"

def get_order_info(order_id=None, customer_name=None):
    """
    Retrieves order details from Shopify based on Order ID or Customer Name.
    """
    url = f"https://{API_KEY}:{PASSWORD}@{SHOPIFY_STORE}/admin/api/2023-04/orders.json"
    
    if order_id:
        url += f"?ids={order_id}"
    elif customer_name:
        url += f"?name={customer_name}"

    response = requests.get(url)
    
    if response.status_code == 200:
        orders = response.json().get("orders", [])
        if not orders:
            return {"error": "No order found."}
        return orders[0]  # Return the first matching order
    else:
        return {"error": f"Error retrieving order: {response.status_code}"}

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

def ask_chatgpt(question):
    """
    Uses OpenAI's GPT-4 to generate a support response.
    """
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "system", "content": "You are a Shopify customer support assistant."},
                  {"role": "user", "content": question}]
    )
    return response["choices"][0]["message"]["content"]

@app.route('/order_info', methods=['GET'])
def order_info():
    """
    API Endpoint for customer support: Retrieves order and tracking information.
    """
    order_id = request.args.get('order_id')
    customer_name = request.args.get('customer_name')

    if not order_id and not customer_name:
        return jsonify({"error": "Please provide an order ID or a customer name."}), 400

    order = get_order_info(order_id, customer_name)
    
    if "error" in order:
        return jsonify(order), 404

    order_status = order.get("financial_status", "Unknown")
    tracking_number = order.get("fulfillments", [{}])[0].get("tracking_number", None)
    
    tracking_info = get_tracking_info(tracking_number) if tracking_number else "No tracking number available."

    response_text = f"""
    **Order Number:** {order.get("id")}
    **Customer:** {order.get("customer", {}).get("first_name", "Unknown")} {order.get("customer", {}).get("last_name", "Unknown")}
    **Order Status:** {order_status}
    **Tracking:** {tracking_info}
    """

    chat_response = ask_chatgpt(f"A customer is asking about order {order.get('id')}. Here are the details: {response_text}. Provide a support response.")

    return jsonify({"response": chat_response})

if __name__ == '__main__':
    app.run(debug=True)

