import os
import json
import requests
import redis
import random
import string

# --- ENVIRONMENT VARIABLES ---
WA_TOKEN = os.environ["WA_TOKEN"]
REDIS_HOST = os.environ["REDIS_HOST"]
REDIS_PORT = int(os.environ["REDIS_PORT"])
REDIS_PASSWORD = os.environ["REDIS_PASSWORD"]
gen_api = os.environ.get("GEN_API")  # Gemini API Key
owner_phone = os.environ.get("OWNER_PHONE") # Owner's phone number with country code
owner_phone_1 = os.environ.get("OWNER_PHONE_1")
owner_phone_2 = os.environ.get("OWNER_PHONE_2")
owner_phone_3 = os.environ.get("OWNER_PHONE_3")
owner_phone_4 = os.environ.get("OWNER_PHONE_4")


# --- REDIS CLIENT ---
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,
    decode_responses=True
)

# --- DATA STRUCTURES ---
CATEGORIES = [
    {
        "name": "Pantry",
        "products": [
            {"name": "Ace Instant Porridge 1kg Assorted", "price": 27.99, "desc": "Instant porridge mix"},
            {"name": "All Gold Tomato Sauce 700g", "price": 44.99, "desc": "Tomato sauce"},
            {"name": "Aromat Original 50g", "price": 24.99, "desc": "Seasoning"},
            {"name": "Bakers Inn Bread", "price": 23.99, "desc": "Brown loaf bread"},
            {"name": "Bakers Inn White Loaf", "price": 23.99, "desc": "White loaf bread"},
            {"name": "Bella Macaroni 3kg", "price": 82.99, "desc": "Macaroni pasta"},
            {"name": "Bisto Gravy 125g", "price": 19.99, "desc": "Gravy mix"},
            {"name": "Blue Band Margarine 500g", "price": 44.99, "desc": "Margarine"},
            {"name": "Blue Ribbon Self Raising 2kg", "price": 37.99, "desc": "Self-raising flour"},
            {"name": "Bokomo Cornflakes 1kg", "price": 54.90, "desc": "Cornflakes"},
            {"name": "Bullbrand Corned Beef 300g", "price": 39.99, "desc": "Corned beef"},
            {"name": "Buttercup Margarine 500g", "price": 44.99, "desc": "Margarine"},
            {"name": "Cashel Valley Baked Beans 400g", "price": 18.99, "desc": "Baked beans"},
            {"name": "Cerevita 500g", "price": 69.99, "desc": "Cereal"},
            {"name": "Cookmore Cooking Oil 2L", "price": 67.99, "desc": "Cooking oil"},
            {"name": "Cross and Blackwell Mayonnaise 700g", "price": 49.99, "desc": "Mayonnaise"},
            {"name": "Dried Kapenta 1kg", "price": 134.99, "desc": "Dried fish"},
            {"name": "Ekonol Rice 5kg", "price": 119.29, "desc": "Rice"},
            {"name": "Fattis Macaroni 500g", "price": 22.99, "desc": "Macaroni"},
            {"name": "Gloria Self Raising Flour 5kg", "price": 79.90, "desc": "Self-raising flour"},
            {"name": "Jungle Oats 1kg", "price": 44.99, "desc": "Oats"},
            {"name": "Knorr Brown Onion Soup 50g", "price": 7.99, "desc": "Onion soup mix"},
            {"name": "Lucky Star Pilchards in Tomato Sauce 155g", "price": 17.99, "desc": "Pilchards"},
            {"name": "Mahatma Rice 2kg", "price": 52.99, "desc": "Rice"},
            {"name": "Peanut Butter 350ml", "price": 19.99, "desc": "Peanut butter"},
            {"name": "Roller Meal 10kg- Zim Meal", "price": 136.99, "desc": "Maize meal"},
        ]
    },
    {
        "name": "Beverages",
        "products": [
            {"name": "Stella Teabags 100 Pack", "price": 42.99, "desc": "Tea bags"},
            {"name": "Mazoe Raspberry 2 Litres", "price": 67.99, "desc": "Fruit drink"},
            {"name": "Cremora Creamer 750g", "price": 72.99, "desc": "Coffee creamer"},
            {"name": "Everyday Milk Powder 400g", "price": 67.99, "desc": "Milk powder"},
            {"name": "Freshpack Rooibos 80s", "price": 84.99, "desc": "Rooibos tea"},
            {"name": "Nestle Gold Cross Condensed Milk 385g", "price": 29.99, "desc": "Condensed milk"},
            {"name": "Pine Nut Soft Drink 2L", "price": 37.99, "desc": "Soft drink"},
            {"name": "Mazoe Blackberry 2L", "price": 68.99, "desc": "Fruit drink"},
            {"name": "Quench Mango 2L", "price": 32.99, "desc": "Fruit drink"},
            {"name": "Coca Cola 2L", "price": 39.99, "desc": "Soft drink"},
            {"name": "Pfuko Dairibord Maheu 500ml", "price": 14.99, "desc": "Maheu drink"},
            {"name": "Sprite 2 Litres", "price": 37.99, "desc": "Soft drink"},
            {"name": "Pepsi (500ml x 24)", "price": 178.99, "desc": "Soft drink pack"},
            {"name": "Probands Milk 500ml", "price": 20.99, "desc": "Steri milk"},
            {"name": "Lyons Hot Chocolate 125g", "price": 42.99, "desc": "Hot chocolate"},
            {"name": "Dendairy Long Life Full Cream Milk 1 Litre", "price": 28.99, "desc": "Long life milk"},
            {"name": "Joko Tea Bags 100", "price": 55.99, "desc": "Tea bags"},
            {"name": "Cool Splash 5 Litre Orange Juice", "price": 99.99, "desc": "Orange juice"},
            {"name": "Cremora Coffee Creamer 750g", "price": 72.99, "desc": "Coffee creamer"},
            {"name": "Fanta Orange 2 Litres", "price": 37.99, "desc": "Soft drink"},
            {"name": "Quench Mango 5L", "price": 92.25, "desc": "Fruit drink"},
            {"name": "Ricoffy Coffee 250g", "price": 52.99, "desc": "Coffee"},
            {"name": "Dendairy Low Fat Long Life Milk", "price": 28.99, "desc": "Low fat milk"},
            {"name": "Quickbrew Teabags 50", "price": 25.99, "desc": "Teabags"},
            {"name": "Fruitrade 2L Orange Juice", "price": 32.90, "desc": "Orange juice"},
            {"name": "Mazoe Orange Crush 2L", "price": 69.99, "desc": "Fruit drink"},
            {"name": "Joko Rooibos Tea Bags 80s", "price": 84.99, "desc": "Rooibos tea"},
        ]
    },
    {
        "name": "Household",
        "products": [
            {"name": "Sta Soft Lavender 2L", "price": 59.99, "desc": "Fabric softener"},
            {"name": "Sunlight Dishwashing Liquid 750ml", "price": 35.99, "desc": "Dishwashing liquid"},
            {"name": "Nova 2-Ply Toilet Paper 9s", "price": 49.90, "desc": "Toilet paper"},
            {"name": "Domestos Thick Bleach Assorted 750ml", "price": 39.99, "desc": "Bleach cleaner"},
            {"name": "Doom Odourless Multi-Insect Killer 300ml", "price": 32.90, "desc": "Insect killer"},
            {"name": "Handy Andy Assorted 500ml", "price": 32.99, "desc": "Multi-surface cleaner"},
            {"name": "Jik Assorted 750ml", "price": 29.99, "desc": "Disinfectant"},
            {"name": "Maq Dishwashing Liquid 750ml", "price": 35.99, "desc": "Dishwashing liquid"},
            {"name": "Maq 3kg Washing Powder", "price": 72.90, "desc": "Washing powder"},
            {"name": "Maq Handwashing Powder 2kg", "price": 78.99, "desc": "Handwashing powder"},
            {"name": "Elangeni Washing Bar 1kg", "price": 24.59, "desc": "Washing bar"},
            {"name": "Vim Scourer 500g", "price": 21.99, "desc": "Scouring pad"},
            {"name": "Matches Carton (10s)", "price": 8.99, "desc": "Matches"},
            {"name": "Surf 5kg", "price": 159.99, "desc": "Washing powder"},
            {"name": "Britelite Candles 6s", "price": 32.99, "desc": "Candles"},
            {"name": "Sta-Soft Assorted Refill Sachet 2L", "price": 39.99, "desc": "Fabric softener refill"},
            {"name": "Poppin Fresh Dishwashing Liquid 750ml", "price": 22.99, "desc": "Dishwashing liquid"},
            {"name": "Poppin Fresh Toilet Cleaner 500ml", "price": 34.99, "desc": "Toilet cleaner"},
            {"name": "Poppin Fresh Multi-Purpose Cleaner", "price": 25.99, "desc": "Multi-purpose cleaner"},
        ]
    },
    # ... Add other categories from your main.py: Personal Care, Snacks and Sweets, Fresh Groceries, Stationery, Baby Section ...
]

DELIVERY_AREAS = {
    "Harare": 240,
    "Chitungwiza": 300,
    "Mabvuku": 300,
    "Ruwa": 300,
    "Domboshava": 250,
    "Southlea": 300,
    "Southview": 300,
    "Epworth": 300,
    "Mazoe": 300,
    "Chinhoyi": 350,
    "Banket": 350,
    "Rusape": 400,
    "Dema": 300
}

# --- UTILITY FUNCTIONS ---
def get_user_state(user_id):
    state = redis_client.get(f"user:{user_id}")
    if state:
        return json.loads(state)
    return {
        "step": "ask_name",
        "cart": [],
        "checkout": {},
        "selected_category": None,
        "selected_product": None
    }

def save_user_state(user_id, state):
    redis_client.set(f"user:{user_id}", json.dumps(state), ex=60*60*3)  # 3 hours expiry

def send_whatsapp_message(text, to, phone_id):
    url = f"https://graph.facebook.com/v19.0/{phone_id}/messages"
    headers = {
        'Authorization': f'Bearer {WA_TOKEN}',
        'Content-Type': 'application/json'
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text}
    }
    resp = requests.post(url, headers=headers, json=data)
    if not resp.ok:
        print("WhatsApp send error:", resp.text)

def list_categories():
    return "\n".join([f"{chr(65+i)}. {cat['name']}" for i, cat in enumerate(CATEGORIES)])

def get_category_by_letter(letter):
    idx = ord(letter.upper()) - 65
    if 0 <= idx < len(CATEGORIES):
        return CATEGORIES[idx]
    return None

def list_products(category):
    return "\n".join([f"{i+1}. {p['name']} - R{p['price']:.2f}: {p['desc']}" for i, p in enumerate(category["products"])])

def show_cart(cart):
    if not cart:
        return "Your cart is empty."
    lines = [f"{item['name']} x{item['qty']} = R{item['price']*item['qty']:.2f}" for item in cart]
    total = sum(item['price']*item['qty'] for item in cart)
    return "\n".join(lines) + f"\n\nTotal: R{total:.2f}"

def list_delivery_areas():
    return "\n".join([f"{k} - R{v:.2f}" for k, v in DELIVERY_AREAS.items()])

# --- MAIN HANDLER FUNCTION ---
def handler(request, response):
    if request.method == "GET":
        # Webhook verification
        mode = request.query.get("hub.mode")
        token = request.query.get("hub.verify_token")
        challenge = request.query.get("hub.challenge")
        if mode == "subscribe" and token == "BOT":
            response.status_code = 200
            response.body = challenge
            return response
        response.status_code = 403
        response.body = "Failed"
        return response

    if request.method == "POST":
        body = request.json()
        value = body["entry"][0]["changes"][0]["value"]
        if "messages" not in value or not value["messages"]:
            response.status_code = 200
            response.body = json.dumps({"status": "no user message"})
            return response

        data = value["messages"][0]
        phone_id = value["metadata"]["phone_number_id"]
        sender = data["from"]
        prompt = data["text"]["body"].strip()
        state = get_user_state(sender)

        step = state.get("step", "ask_name")
        cart = state.get("cart", [])
        selected_category = state.get("selected_category")
        selected_product = state.get("selected_product")
        checkout = state.get("checkout", {})

        # --- STATE MACHINE LOGIC ---
        if step == "ask_name":
            send_whatsapp_message("Hello! Welcome to Zimbogrocer. What's your name?", sender, phone_id)
            state["step"] = "save_name"

        elif step == "save_name":
            state["username"] = prompt.title()
            send_whatsapp_message(
                f"Thanks {state['username']}! Please select a category:\n{list_categories()}",
                sender, phone_id
            )
            state["step"] = "choose_category"

        elif step == "choose_category":
            if prompt.isalpha() and len(prompt) == 1:
                cat = get_category_by_letter(prompt)
                if cat:
                    state["selected_category"] = cat["name"]
                    send_whatsapp_message(
                        f"Products in {cat['name']}:\n{list_products(cat)}\nSelect a product by number.",
                        sender, phone_id
                    )
                    state["step"] = "choose_product"
                else:
                    send_whatsapp_message("Invalid category. Try again:\n" + list_categories(), sender, phone_id)
            else:
                send_whatsapp_message("Please enter a valid category letter (e.g., A, B, C).", sender, phone_id)

        elif step == "choose_product":
            try:
                index = int(prompt) - 1
                cat = get_category_by_letter(selected_category[0]) if selected_category else None
                if not cat: cat = get_category_by_letter(prompt)
                if not cat: 
                    send_whatsapp_message("Please select a valid category first.", sender, phone_id)
                    state["step"] = "choose_category"
                else:
                    if 0 <= index < len(cat["products"]):
                        prod = cat["products"][index]
                        state["selected_product"] = prod
                        send_whatsapp_message(f"You selected {prod['name']}. How many would you like to add?", sender, phone_id)
                        state["step"] = "ask_quantity"
                    else:
                        send_whatsapp_message("Invalid product number. Try again.", sender, phone_id)
            except Exception:
                send_whatsapp_message("Please enter a valid product number.", sender, phone_id)

        elif step == "ask_quantity":
            try:
                qty = int(prompt)
                prod = state["selected_product"]
                if qty < 1:
                    raise ValueError
                cart.append({"name": prod["name"], "price": prod["price"], "qty": qty})
                state["cart"] = cart
                send_whatsapp_message(
                    "Item added to your cart.\nWhat would you like to do next?\n- View cart\n- Clear cart\n- Remove <item>\n- Add Item",
                    sender, phone_id
                )
                state["step"] = "post_add_menu"
            except Exception:
                send_whatsapp_message("Please enter a valid number for quantity (e.g., 1, 2, 3).", sender, phone_id)

        elif step == "post_add_menu":
            if prompt.lower() == "view cart":
                send_whatsapp_message(show_cart(cart) + "\n\nPlease select your delivery area:\n" + list_delivery_areas(), sender, phone_id)
                state["step"] = "get_area"
            elif prompt.lower() == "clear cart":
                cart.clear()
                state["cart"] = cart
                send_whatsapp_message("Cart cleared.\nWhat would you like to do next?\n- View cart\n- Add Item", sender, phone_id)
                state["step"] = "post_add_menu"
            elif prompt.lower().startswith("remove "):
                item = prompt[7:].strip()
                cart = [i for i in cart if i["name"].lower() != item.lower()]
                state["cart"] = cart
                send_whatsapp_message(f"{item} removed from cart.\n{show_cart(cart)}\nWhat would you like to do next?\n- View cart\n- Add Item", sender, phone_id)
                state["step"] = "post_add_menu"
            elif prompt.lower() in ["add", "add item", "add another", "add more"]:
                send_whatsapp_message("Sure! Here are the available categories:\n" + list_categories(), sender, phone_id)
                state["step"] = "choose_category"
            else:
                send_whatsapp_message("Sorry, I didn't understand. You can:\n- View Cart\n- Clear Cart\n- Remove <item>\n- Add Item", sender, phone_id)

        elif step == "get_area":
            area = prompt.strip().title()
            if area in DELIVERY_AREAS:
                checkout["delivery_area"] = area
                fee = DELIVERY_AREAS[area]
                checkout["delivery_fee"] = fee
                cart.append({"name": "__Delivery__", "price": fee, "qty": 1})
                state["cart"] = cart
                state["checkout"] = checkout
                send_whatsapp_message(show_cart(cart) + "\nWould you like to checkout? (yes/no)", sender, phone_id)
                state["step"] = "ask_checkout"
            else:
                send_whatsapp_message(f"Invalid area. Please choose from:\n{list_delivery_areas()}", sender, phone_id)

        elif step == "ask_checkout":
            if prompt.lower() in ["yes", "y"]:
                send_whatsapp_message("Please enter the receiver’s full name.", sender, phone_id)
                state["step"] = "get_receiver_name"
            elif prompt.lower() in ["no", "n"]:
                send_whatsapp_message("What would you like to do next?\n- View cart\n- Clear cart\n- Remove <item>\n- Add Item", sender, phone_id)
                state["step"] = "post_add_menu"
            else:
                send_whatsapp_message("Please respond with 'yes' or 'no'.", sender, phone_id)

        elif step == "get_receiver_name":
            checkout["receiver_name"] = prompt
            send_whatsapp_message("Enter the delivery address.", sender, phone_id)
            state["checkout"] = checkout
            state["step"] = "get_address"

        elif step == "get_address":
            checkout["address"] = prompt
            send_whatsapp_message("Enter receiver’s ID number.", sender, phone_id)
            state["checkout"] = checkout
            state["step"] = "get_id"

        elif step == "get_id":
            checkout["id_number"] = prompt
            send_whatsapp_message("Enter receiver’s phone number.", sender, phone_id)
            state["checkout"] = checkout
            state["step"] = "get_phone"

        elif step == "get_phone":
            checkout["phone"] = prompt
            details = checkout
            confirm_message = (
                f"Please confirm the details below:\n\n"
                f"Name: {details.get('receiver_name','')}\n"
                f"Address: {details.get('address','')}\n"
                f"ID: {details.get('id_number','')}\n"
                f"Phone: {details.get('phone','')}\n\n"
                "Are these correct? (yes/no)"
            )
            send_whatsapp_message(confirm_message, sender, phone_id)
            state["checkout"] = checkout
            state["step"] = "confirm_details"

        elif step == "confirm_details":
            if prompt.lower() in ["yes", "y"]:
                order_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                payment_info = (
                    f"Please make payment using one of the following options:\n\n"
                    f"1. EFT\nBank: FNB\nName: Zimbogrocer (Pty) Ltd\nAccount: 62847698167\nBranch Code: 250655\nSwift Code: FIRNZAJJ\nReference: {order_id}\nPlease remember to send the Proof of Payment as soon as possible.\n"
                    f"2. Pay at supermarkets: SHOPRITE, CHECKERS, USAVE, PICK N PAY, GAME, MAKRO or SPAR using Mukuru wicode\n"
                    f"3. World Remit Transfer (payment details provided upon request)\n"
                    f"4. Western Union (payment details provided upon request)\n"
                )
                send_whatsapp_message(
                    f"Order placed! 🛒\nOrder ID: {order_id}\n\n"
                    f"{show_cart(cart)}\n\n"
                    f"Receiver: {checkout.get('receiver_name','')}\n"
                    f"Address: {checkout.get('address','')}\n"
                    f"Phone: {checkout.get('phone','')}\n\n"
                    f"{payment_info}\n\nWould you like to place another order? (yes/no)",
                    sender, phone_id
                )
                # Reset state for new order
                state.clear()
                state.update({
                    "step": "ask_place_another_order",
                    "cart": [],
                    "checkout": {},
                    "selected_category": None,
                    "selected_product": None
                })
            else:
                send_whatsapp_message("Okay, let's correct the details. What's the receiver’s full name?", sender, phone_id)
                state["step"] = "get_receiver_name"

        elif step == "ask_place_another_order":
            if prompt.lower() in ["yes", "y"]:
                send_whatsapp_message("Great! Please select a category:\n" + list_categories(), sender, phone_id)
                state["step"] = "choose_category"
            else:
                send_whatsapp_message("Okay. Have a good day! 😊", sender, phone_id)
                state["step"] = "ask_name"

        else:
            send_whatsapp_message("Sorry, something went wrong. Please try again.", sender, phone_id)
            state = {
                "step": "ask_name",
                "cart": [],
                "checkout": {},
                "selected_category": None,
                "selected_product": None
            }

        # --- Persist user state ---
        save_user_state(sender, state)

        response.status_code = 200
        response.body = json.dumps({"status": "ok"})
        return response

# --- Vercel Python Entrypoint ---
def main(request, response):
    return handler(request, response)
