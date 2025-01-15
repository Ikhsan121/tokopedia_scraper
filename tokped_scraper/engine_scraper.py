import json
import os
from idlelib.debugobj import AtomicObjectTreeItem
from itertools import product
from pathlib import Path

import pandas as pd
from playwright.sync_api import sync_playwright
from time import sleep
from bs4 import BeautifulSoup
import config

COOKIE_FILE = "cookies.json"
adv_links = []


def save_cookies(context):
    """Save cookies to a file."""
    cookies = context.cookies()
    with open(COOKIE_FILE, "w") as f:
        json.dump(cookies, f)
    print("Cookies saved!")


def load_cookies(context):
    """Load cookies from a file if it exists."""
    file_path = Path(COOKIE_FILE)
    if file_path.exists():
        with open(COOKIE_FILE, "r") as f:
            cookies = json.load(f)
            context.add_cookies(cookies)
        print("Cookies loaded!")
    else:
        print("No cookies found. Starting fresh session.")


def slow_scroll(page, step=300, delay=1):
    """
    Scrolls the page slowly in small increments with a delay.

    Parameters:
    - page: Playwright page object
    - step: Number of pixels to scroll per step
    - delay: Time delay between scrolls (in seconds)
    """
    total_height = page.evaluate("document.body.scrollHeight")
    current_position = 0

    while current_position < total_height:
        # Scroll by step size
        page.evaluate(f"window.scrollBy(0, {step})")
        current_position += step
        print(f"Scrolled to: {current_position}px")

        # Wait for content to load
        sleep(delay)

        # Recalculate height in case content has loaded and expanded the page
        total_height = page.evaluate("document.body.scrollHeight")

    print("Reached the bottom of the page!")


def get_all_links(html_content):
    links_list = []
    # Parse the HTML using Beautiful Soup
    soup = BeautifulSoup(html_content, 'html.parser')
    # print(soup.prettify())
    containers = soup.find_all('div', class_="css-5wh65g")
    for container in containers:
        link = container.find('a').get('href')
        links_list.append(link)
    return links_list


def browser_context(max_page=config.MAX_PAGE, keyword=config.KEYWORD):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)

        # Create a new browser context
        context = browser.new_context()

        # Check if cookies.json exists and load cookies
        if os.path.isfile(COOKIE_FILE):
            print("The file cookies.json exists.")
            load_cookies(context)  # Load cookies into the context

        # Create a new page and navigate to the site
        page = context.new_page()
        page.set_default_navigation_timeout(60000)  # Set navigation timeout

        # If cookies.json exists, wait to verify the session is restored
        if os.path.isfile(COOKIE_FILE):
            print("Waiting for session verification...")
            sleep(2)  # Adjust as needed to verify the session
        else:
            print("Saving cookies for future use.")
            sleep(60)  # Wait to simulate user interaction
            save_cookies(context)  # Save cookies to the file
        for pg in range(1, max_page+1):
            link = f"https://www.tokopedia.com/search?navsource=&page={pg}&q={keyword}&search_id=20250114104223FD057DD9BB888533FT17&srp_component_id=02.01.00.00&srp_page_id=&srp_page_title=&st="
            page.goto(link)
            slow_scroll(page, step=1000, delay=1)
            html_content = page.content()
            links = get_all_links(html_content)
            for link in links:
                adv_links.append(link)

        # go to each product page
        final_data = []
        for product_item in adv_links:
            page.goto(product_item)
            print("link: ", product_item)

            # scraping process
            page.wait_for_selector('h1[data-expanded="false"][data-testid="lblPDPDetailProductName"]', state="visible") # wait for title element to be visible
            page.wait_for_selector('div[class="items"]', state="attached")
            page.wait_for_selector('div[data-testid="lblPDPDescriptionProduk"]', state="visible")

            html_content = page.content()
            final_data.append(get_all_fields(html_content, product_item))
            # Convert to a DataFrame and save to CSV
            df = pd.DataFrame(final_data)
            df.to_csv("data.csv", index=False)

            print("CSV file created using Pandas!")


def get_all_fields(html_content, link):
    data = {}
    soup = BeautifulSoup(html_content, 'html.parser')
    title = soup.find('h1', {'data-testid':'lblPDPDetailProductName'}).text
    try:
        rating = soup.find('span', {'data-testid':'lblPDPDetailProductRatingNumber'}).text
    except AttributeError:
        rating = ''

    try:
        rating_counter = soup.find('span', {'data-testid':'lblPDPDetailProductRatingCounter'}).text.replace("(", "").replace(")", "").replace('rating', '').strip()
    except AttributeError:
        rating_counter = ''
    price = soup.find('div', {'data-testid':'lblPDPDetailProductPrice'}).text
    try:
        sold = soup.find('p', {'data-testid':'lblPDPDetailProductSoldCounter'}).text.replace("Terjual", "").replace('rb+', "000").replace(" ", "")
    except AttributeError:
        sold = ''
    description = soup.find('div', {'data-testid':'lblPDPDescriptionProduk'}).text.strip().replace("\n", " ")
    shop_name = soup.find('a', {'data-testid': 'llbPDPFooterShopName'}).text
    store_location = soup.find('h2', class_='css-1pd07ge-unf-heading e1qvo2ff2').text.replace('Dikirim dari', '').strip()

    data['title'] = title
    data['rating'] = rating
    data['price'] = price
    data['rating counter'] = rating_counter
    data['sold'] = sold
    data['description'] = description
    data['shop name'] = shop_name
    data['url'] = link
    data['store location'] = store_location


    print('title: ', title)
    print('shop name: ', shop_name)
    print('rating: ', rating)
    print('rating counter: ', rating_counter)
    print('price: ', price)
    print('sold: ', sold)
    print('description: ', description)
    print('send from: ', store_location)
    return data




