import requests
import json
import time
import database
import concurrent.futures
import logging
import random
from proxy_requests import *


API_URL = "https://ecgproductmw.colruyt.be/ecgproductmw/v2/nl/products/"
WINKEL = "Colruyt"
MAX_THREADS = 5
SLEEP_TIME = 5

"""
    Colruyt's categories are stored in the way displayed below.
    This function transforms it into a list [ "Parent, Child 1 , ...", "Parent, Child 1, ..."]
    [ {"name" : ...
       "children" : [
           "name": ..
           "children: ...

       },
       {
        name:....
        children: ...
       }
       ]]
"""
def getCategoryTxt(cat):
    result = ""
    if type(cat) is list:
        for l in cat:
            result += getCategoryTxt(l) +", "
        return result  
    if cat.get("name") is not None:
        result += cat.get("name") + ", "
    if cat.get("children") is not None:
        result += getCategoryTxt(cat.get("children"))
    return result


"""
    Perform a request to Colruyt's API. 
    Specify the "page" and the amount of products on that "page". 
    Max 250 products.
    Returns the response. <=> None if there is an error.
"""
def getProducts(page, amount, placeId=604):
    time.sleep(int(random.random()*SLEEP_TIME)) #TODO, its in order to limit the send rate. 


    params = {
        "clientCode": "clp",
        "isAvailable": "true",
        "page": int(page),
        "placeId": int(placeId),
        "size": int(amount),
        "sort": "popularity asc",
        "ts": time.time()
    }
    try:        
        # res = requests.get(API_URL, params=params)
        res = ProxyRequests(API_URL)
        res.get(params)

    except (requests.exceptions.ProxyError, requests.exceptions.ConnectTimeout, requests.exceptions.SSLError) as err:
        database.log("error", "Error using proxies: " + str(err), WINKEL)

    except Exception as e:
        database.log("error", "Request error : " + str(e), WINKEL)
        print(str(e))
        return None
    return str(res)

"""
    Convert text into JSON. 
    Return None if there is an error.

"""
def responseToJson(resp):
    try:
        result = json.loads(resp)
    except Exception as e:
        print("responseToJson: " + str(e))
        database.log("error", "ResponseToJSON ERROR: " + str(e) + "\n ---- RESPONSE WAS:" + str(resp), WINKEL)
        return None
    return result


def processProducts(js):
    if js is not None and js.get("products") is not None:
        products = js.get("products")

        # threads = MAX_THREADS
        # with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
        #     executor.map(processProduct, products)

        for product in js.get("products"):
            processProduct(product)

def processProduct(product):
    price = product.get("price")
    if product.get("catagories") is not None:
        categories = product.get("categories")
        categories = getCategoryTxt(categories)
    else:
        categories = product.get("topCategoryName")
    database.processProduct("Colruyt", 
    product.get("productId"),
    product.get("name"),
    product.get("description"),
    product.get("brand"),
    product.get("thumbNail"),
    product.get("content"),
    price.get("basicPrice"),
    price.get("quantityPrice"),
    price.get("quantityPriceQuantity"),
    price.get("measurementUnitPrice"),
    price.get("measurementUnitQuantityPrice"),
    price.get("measurementUnit"),
    categories)

def test(page):
    print("Process page " + str(page))
    response = getProducts(page, 250)
    response_json = responseToJson(response)
    if response_json is not None and response_json.get("productsReturned") is not None and response_json.get("productsReturned") == 0:
        database.log("error", "No products returned. " + str(response[0:500]), WINKEL)
        return None
        
    processProducts(response_json)
    print(">>> process page " + str(page) + " done.")

pages = range(1,1000)




threads = MAX_THREADS
with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
    executor.map(test, pages)




# Experiment
# - Using no threading for the request, but for the processing of the received data (check & update database): 306 seconds
# - Using threading for the requests and no for processing: 332 sec - 176sec

