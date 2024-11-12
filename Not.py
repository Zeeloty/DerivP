import websocket
import json
import time
import threading

# Deriv API Token
API_TOKEN = 'WeipIgZSsgdptZr'

# Define your volume (stake) for each step manually
volumes = [1, 2, 4, 5, 6, 7, 9, 12, 15, 19]

# Initialize global variables
current_step = 0
symbol = "R_10"  # Default market symbol
contract_type = "ONETOUCH"  # Change to "ONETOUCH" or "NOTOUCH" for Touch/No Touch
duration_in_ticks = 10  # Contract duration in ticks
waiting_for_result = False  # Track if waiting for the trade result

# User input for barrier
barrier = input("Enter barrier value (default is 0.1 for Touch/No Touch): ") or "0.1"

def on_open(ws):
    print("Connected to Deriv API")
    authorize(ws)
    # Start sending keep-alive ping messages
    threading.Thread(target=keep_alive, args=(ws,), daemon=True).start()

def authorize(ws):
    data = {
        "authorize": API_TOKEN
    }
    ws.send(json.dumps(data))

def on_message(ws, message):
    global current_step, waiting_for_result

    try:
        response = json.loads(message)
    except json.JSONDecodeError:
        print("Failed to parse message:", message)
        return

    # Handle authorization
    if "authorize" in response:
        if response.get("error"):
            print("Authorization error:", response["error"].get("message"))
            ws.close()
            return
        print("Authorized successfully!")
        request_proposal(ws)

    # Handle proposal response
    elif "proposal" in response:
        if response.get("error"):
            print("Proposal error:", response["error"].get("message"))
            return
        proposal_id = response["proposal"]["id"]
        print("Proposal received. Proceeding to buy.")
        execute_trade(ws, proposal_id)

    # Handle trade execution
    elif "buy" in response:
        if response.get("error"):
            print("Trade execution error:", response["error"].get("message"))
            return
        print(f"Trade executed: {contract_type} - Volume: {volumes[current_step]}")
        waiting_for_result = True

    # Handle contract results
    elif "proposal_open_contract" in response:
        contract = response["proposal_open_contract"]

        if contract.get('is_sold'):  # Contract has been settled
            waiting_for_result = False  # No longer waiting
            if contract.get('status') == 'won':
                print("Trade WON! Resetting to step 1.")
                current_step = 0  # Reset on win
            elif contract.get('status') == 'lost':
                print(f"Trade LOST! Moving to step {current_step + 2}")
                current_step = min(current_step + 1, len(volumes) - 1)  # Increment step on loss

            time.sleep(5)  # Wait before placing the next trade
            request_proposal(ws)

def request_proposal(ws):
    global current_step, waiting_for_result
    if not waiting_for_result:
        stake = volumes[current_step]

        # Request a new contract proposal
        data = {
            "proposal": 1,
            "amount": stake,
            "basis": "stake",
            "contract_type": contract_type,
            "currency": "USD",
            "duration": duration_in_ticks,
            "duration_unit": "t",  # 't' stands for ticks
            "symbol": symbol,
            "barrier": barrier  # Use the user-defined or default barrier
        }
        ws.send(json.dumps(data))

def execute_trade(ws, proposal_id):
    data = {
        "buy": proposal_id,
        "price": volumes[current_step]  # Ensure matching stake
    }
    ws.send(json.dumps(data))

def on_close(ws, close_status_code, close_msg):
    print(f"Disconnected from server with code: {close_status_code}, Message: {close_msg}")
    reconnect(ws)

def on_error(ws, error):
    print("WebSocket error:", error)
    time.sleep(5)  # Attempt reconnection after a delay
    reconnect(ws)

def keep_alive(ws):
    while True:
        time.sleep(30)  # Send a ping every 30 seconds
        try:
            ws.send(json.dumps({"ping": 1}))
        except Exception as e:
            print("Ping failed:", e)
            break

def reconnect(ws):
    time.sleep(5)  # Wait 5 seconds before reconnecting
    print("Reconnecting...")
    run_bot()

# WebSocket connection
def run_bot():
    url = "wss://ws.binaryws.com/websockets/v3?app_id=65545"  # Replace with your custom app_id if available
    ws = websocket.WebSocketApp(
        url,
        on_open=on_open,
        on_message=on_message,
        on_close=on_close,
        on_error=on_error
    )
    ws.run_forever()

if __name__ == "__main__":
    run_bot()
