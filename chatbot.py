from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import JSONResponse
import database_connection
import session_controll

app = FastAPI()

inprogress_orders = {}

@app.post("/")
async def handle_request(request: Request):
    # Retrieve the JSON data from the request
    payload = await request.json()

    # Extract the necessary information from the payload
    # based on the structure of the WebhookRequest from Dialogflow
    intent = payload['queryResult']['intent']['displayName']
    parameters = payload['queryResult']['parameters']
    output_contexts = payload['queryResult']['outputContexts']
    session_id = session_controll.extract_session_id(output_contexts[0]["name"])



    if intent=="track.order.context":
       return track_order(parameters)
    elif intent=="order.add":
        return order_add(parameters,session_id)
    elif intent=="order.complete":
        return order_complete(parameters,session_id)
       
def save_to_db(order: dict):
    next_order_id = database_connection.get_next_order_id()

    # Insert individual items along with quantity in orders table
    for product_item, quantity in order.items():
        rcode = database_connection.insert_order_item(
            product_item,
            quantity,
            next_order_id
        )

        if rcode == -1:
            return -1

    # Now insert order tracking status
    database_connection.insert_order_tracking(next_order_id, "en cours")

    return next_order_id
# def save_to_db(order: dict):
#     next_order_id = database_connection.get_next_order_id()

#     # Insert individual items along with quantity in orders table
#     for food_item, quantity in order.items():
#         insert_order_item = """
#             INSERT INTO order_tracking (product_item, quantity, id_product)
#             VALUES (%s, %s, %s)
#         """

#         # Assuming database_connection.execute_query takes a SQL query and parameters
#         rcode = database_connection.execute_query(insert_order_item, (food_item, quantity, next_order_id))

#         if rcode == -1:
#             return -1

#     # Now insert order tracking status
#     sql_insert_order_tracking = """
#         INSERT INTO track_order (id, status)
#         VALUES (%s, %s)
#     """

#     # Assuming database_connection.execute_query takes a SQL query and parameters
#     database_connection.execute_query(sql_insert_order_tracking, (next_order_id, "in progress"))

#     return next_order_id
    

def save_to_db(order):
    try:
        # Get the next order_id using the get_next_order_id function
        order_id = database_connection.get_next_order_id()

        # Iterate through the products in the order and insert order items
        for product_name, quantity in order.items():
            # Get the product_id and price from the 'product' table
            product_id, price = database_connection.get_product_info(product_name)

            # Calculate the total price for the order item
            total_price = quantity * price

            # Insert the order item into the 'order_item' table
            database_connection.insert_order_item(product_id, quantity, order_id)

        # Insert the order tracking information into the 'order_tracking' table
        database_connection.insert_order_tracking(order_id, "in progress")

        # Commit the changes to the database
        database_connection.cnx.commit()

        return order_id

    except Exception as e:
        print(f"An error occurred while saving to the database: {e}")
        # Rollback changes if necessary
        database_connection.cnx.rollback()

        return None

#done
def order_add(parameters : dict,session_id: str):
    product_items=parameters["store-product"]
    number=parameters["number"]

    if len(number) != len(product_items):
        fulfillment_text="sorry you should to specify the number and product name at same time like i want to order 2 iphone 13 and one samsung s22"
    else:
        new_product_dict = dict(zip(product_items, number))
        if session_id in inprogress_orders:
            current_product_dict = inprogress_orders[session_id]
            current_product_dict.update(new_product_dict)
            inprogress_orders[session_id] = current_product_dict
            print(inprogress_orders)
        else:
            inprogress_orders[session_id] = new_product_dict
            print(inprogress_orders)
        order_str = session_controll.get_str_from_food_dict(inprogress_orders[session_id])
        fulfillment_text=f'reçu {order_str} tu veux autre chose ?'

    return JSONResponse(content={"fulfillmentText":f"{fulfillment_text}"})




def order_complete(parameters:dict,session_id:str):
    if session_id not in inprogress_orders:
        fulfillment_text="i havent found your order can you please place a new order !"
    else:
        fulfillment_text="jaya katjri"
        order =inprogress_orders[session_id]
        save_to_db(order)
    return JSONResponse(content={"fulfillmentText":f"{fulfillment_text}"})




#done
def track_order(parameters: dict):
    order_id= int (parameters['number'])
    order_status = database_connection.get_order_status(order_id)

    if order_status:
        fulfillment_text=f"votre commande {order_id} est {order_status}"
        
    else:
        fulfillment_text=f"no order found with this order id : {order_id}"

    return JSONResponse(content={"fulfillmentText":f"{fulfillment_text}"})

