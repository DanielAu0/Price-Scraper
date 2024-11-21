import asyncio
import json
import pandas as pd
from httpx import AsyncClient, Response
from desktop_notifier import DesktopNotifier, Button
from typing import List, Dict
from parsel import Selector
from time import gmtime, strftime

# Initialize an async httpx client
client = AsyncClient(
    headers = {
        "Accept-Language": "en-US,en;q=0.9",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
    }
)


def parse_products(response: Response) -> List[Dict]:
    """parse products from HTML"""
    selector = Selector(response.text)    
    data =[]

    price = selector.xpath("//span[@class='_6o3atzbl _6o3atzc7 _6o3atz19j']/text()").get()
    name = selector.xpath("//h1[@class='_6o3atz174 hapmhk7 hapmhkf hapmhkl']/text()").get()

    data.append({
        "name": name,
        "price": price,
        "latest_change": strftime("%Y-%m-%d %H:%M", gmtime()),
        "price_change": "N/A"   
    })
    return data


async def scrape_products(url: str) -> List[Dict]:
    """scrape product page"""
    # scrape the first product page first
    page = await client.get(url)
    products_data = parse_products(page)

    print(f"Scraped {len(products_data)} products")
    return products_data


def write_to_csv(data, filename):
    """save the data into csv"""
    df = pd.DataFrame(data)
    df.to_csv(f"./{filename}.csv", index=False)


def compare_data(new_data, filename):
    try:
        df = pd.read_csv(f"./{filename}.csv")
    except:
        return new_data
    old_data = df.to_dict(orient='records')
    for new_product in new_data:
        for old_product in old_data:
            if old_product["name"] == new_product["name"]:
                if old_product["price"] != new_product["price"]:
                    change_percentage = round((new_product['price'] - old_product['price']) / old_product['price'] * 100)
                    change_case = "+" if new_product['price'] - old_product['price'] > 1 else ""
                    new_product["price_change"] = f"{change_case}{change_percentage}%" 
                else:
                    new_product["latest_change"] = old_product["latest_change"]
    return new_data


def save_historical(new_data):
    try:
        with open("./historical.json", 'r') as file:
            existing_data = json.load(file)
    except FileNotFoundError:
        # Initialize an empty list if first run
        existing_data = []
    #  Extract timestamp from the first record
    timestamp = new_data[0]["latest_change"]
    new_data = [
        {
            "timestamp": timestamp,
            "data": [
                {
                    "name": item["name"],
                    "price": item["price"]
                }
                for item in new_data
            ]
        }
    ]
    existing_data.extend(new_data)
    with open("./historical.json", 'w') as file:
        json.dump(existing_data, file, indent=2) 


notifier = DesktopNotifier()

# Send a desktop notification
async def send_notification():
    await notifier.send(
        title="Price tracking tool",
        message="Your web scraping results are ready!",
        buttons=[
            Button(
                title="Mark as read",
            ),
        ],
    )


async def track_prices():
    print("======= Starting price tracker =======")
    data = await scrape_products(url="https://www.wayfair.ca/home/pdp/archie-oscar-southwick-ecoflex-dog-crate-end-table-durable-wood-plastic-composite-with-stainless-steel-latch-aosc1016.html?piid=30959894%2C30959892")
    save_historical(data)
    data = compare_data(data, filename="prices")
    write_to_csv(data, filename="prices")
    await send_notification()
    print("======= Price tracker complete =======")


async def main():
    while True:
        # Run the script every 3 hours
        await track_prices()
        await asyncio.sleep(3 * 60 * 60)


if __name__ == "__main__":
    asyncio.run(main())