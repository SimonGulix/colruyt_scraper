import requests
import json
import time
import database
import concurrent.futures
from lxml.html import fromstring
from itertools import cycle
import random

API_URL = "https://ecgproductmw.colruyt.be/ecgproductmw/v2/nl/products/"
WINKEL = "Colruyt"
MAX_THREADS = 5
SLEEP_TIME = 20

PROXIES = []
PROXY_POOL = None
MIN_NB_PROXIES = 10

"""
    Function that returns a list of proxys
"""
def get_proxies():
    url = 'https://free-proxy-list.net/'
    try:
        response = requests.get(url)
        parser = fromstring(response.text)
    except Exception as e:
        database.log("error", "Error getting proxies:" + str(e), WINKEL)
        return set()

    proxies = set()
    for i in parser.xpath('//tbody/tr'):
        if i.xpath('.//td[7][contains(text(),"yes")]'):
            proxy = ":".join([i.xpath('.//td[1]/text()')[0], i.xpath('.//td[2]/text()')[0]])
            proxies.add(proxy)
    
    global PROXIES
    PROXIES = proxies
    global PROXY_POOL
    PROXY_POOL = cycle(PROXIES)

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
    # time.sleep(int(random.random()*SLEEP_TIME)) #TODO, its in order to limit the send rate. 
    if len(PROXIES) < MIN_NB_PROXIES:
        get_proxies()
        database.log("info", "New proxies: #" + str(len(PROXIES)), WINKEL)

    params = {
        "clientCode": "clp",
        "isAvailable": "true",
        "page": int(page),
        "placeId": int(placeId),
        "size": int(amount),
        "sort": "popularity asc",
        "ts": time.time()
    }
    global PROXY_POOL
    proxy = next(PROXY_POOL)
    try:
        res = requests.get(API_URL, params=params, proxies={"http": str(proxy), "https": str(proxy)}, timeout=(60,120))
        
        #  res = requests.get(API_URL, params=params)

    except (requests.exceptions.ProxyError, requests.exceptions.ConnectTimeout, requests.exceptions.SSLError) as err:
        database.log("error", "Error using proxies: " + str(err), WINKEL)
        if proxy in PROXIES:
            PROXIES.remove(proxy)
            PROXY_POOL = cycle(PROXIES)
            return getProducts(page, amount, placeId)
    except Exception as e:
        database.log("error", "Request error : " + str(e), WINKEL)
        print(str(e))
        return None
    return res.text

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
    processProducts(response_json)
    print(">>> process page " + str(page) + " done.")


# start_time = time.time()
pages = range(1,1000)
get_proxies()
# for page in pages:
#     test(page)


threads = MAX_THREADS
with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
    executor.map(test, pages)

# end_time = time.time()

# print("DONE, Time elapsed = " + str(end_time-start_time) + "seconds.")
# test
