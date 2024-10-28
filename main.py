import time
import sqlite3
from curl_cffi import requests
from fake_headers import Headers
from bs4 import BeautifulSoup
from contextlib import closing
import urllib.parse
import logging
from threading import Thread, BoundedSemaphore
from datetime import datetime

MAX_WORKERS = 3

logger = logging.getLogger(__name__)
logger.name = "LordScraper"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - Thread: %(threadName)s - %(message)s',
)

header = Headers(
    browser="chrome",  # Generate only Chrome UA
    os="win",  # Generate ony Windows platform
    headers=True  # generate misc headers
)


def is_every_dict_key_null(d):
    for key in d:
        if d[key]:
            return False
    return True


def parse_addresses(html_content):
    try:
        # Create BeautifulSoup object
        soup = BeautifulSoup(html_content, 'html.parser')

        # Find the select element with id 'suggested-addresses'
        select_element = soup.find('select', id='suggested-addresses')

        # Initialize empty list to store addresses
        addresses = []

        # Find all option elements except the first one (which shows count)
        if select_element:
            options = select_element.find_all('option')[1:]  # Skip first option

            for option in options:
                # Get the address from the option text
                address = option.text.strip()
                # Get the value attribute which contains the ID and address
                value = option.get('value', '')

                if address and value:
                    addresses.append({
                        'address': address,
                        'full_address': value
                    })

        return addresses
    except Exception as e:
        # Handle any exceptions that may occur during the parsing process
        logger.error(f"Error parsing addresses: {e}")
        return []


def parse_address_details(html_content):
    """
    Extract the requested address details from the HTML content.
    Returns a dictionary with the following keys:
    - application_by
    - joint_owners
    - agent_details
    - local_authority
    - contact_address
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    address_details = {}

    # Application by
    application_by_element = soup.find('dd', {'data-testid': 'property-lead-owner'})
    address_details['application_by'] = application_by_element.text.strip() if application_by_element else None

    # Joint owner(s)
    joint_owners_element = soup.find('dd', {'data-testid': 'property-joint-owner'})
    address_details['joint_owners'] = joint_owners_element.text.strip() if joint_owners_element else None

    # Agent's details
    agent_details_element = soup.find('dd', string=lambda
        text: text and 'Please contact the relevant Local Authority' in text)
    address_details['agent_details'] = agent_details_element.text.strip() if agent_details_element else None

    # Local authority
    local_authority_element = soup.find('dd', {'data-testid': 'property-reg-authority'})
    address_details['local_authority'] = local_authority_element.text.strip() if local_authority_element else None

    # Contact address
    contact_address_element = soup.find('dd', {'data-testid': 'property-contact-details'})
    address_details['contact_address'] = contact_address_element.text.strip() if contact_address_element else None

    return address_details


def investigate_address(full_address: str, simple_address: str, session: requests.Session, headers: dict):
    encoded_address = urllib.parse.quote_plus(full_address)

    i = 0
    while i < 3:
        try:
            response = session.post("https://www.landlordregistrationscotland.gov.uk/search/registration/property",data=f"selectedAddress="f"{encoded_address}",headers=headers)
            break
        except requests.exceptions.Timeout:
            logger.error("Timeout error for postcode: " + postcode)
            logger.error("Retrying...")
            time.sleep(1)
            i += 1
            return []

    if "No registration details available" in response.text:
        logger.info("No registration details available for " + simple_address)
        return {}

    if "This property is not in the register" in response.text:
        logger.info("No registration details available for " + simple_address)
        return {}

    if response.status_code != 200:
        logger.error(f"Error: {response.status_code}")
        # Write error response to file
        with open("error.log", "w") as f:
            f.write(response.text)
        logger.error("Error response written to error.log")
        return {}

    details = parse_address_details(response.text)
    if is_every_dict_key_null(details):
        return None

    details["address"] = simple_address
    return details


def scrape_addresses(postcode: str, session, headers):
    postcode = postcode.replace(" ", "+")
    postcode = postcode.strip()

    i = 0
    while i < 3:
        try:
            responsePostData = session.post("https://www.landlordregistrationscotland.gov.uk/search/postcode", data="postcode=" + postcode, headers=headers)
            break
        except requests.exceptions.Timeout:
            logger.error("Timeout error for postcode: " + postcode)
            logger.error("Retrying...")
            time.sleep(1)
            i += 1
            return []

    if responsePostData.status_code == 200:
        if "Postcode not found" in responsePostData.text:
            logger.info(f"Postcode {postcode} not found")
            return []

        return parse_addresses(responsePostData.text)
    else:
        logger.error(f"Error: {responsePostData.status_code}")
        # Write error response to file
        with open("error.log", "w") as f:
            f.write(responsePostData.text)
        logger.error("Error response written to error.log")

def with_database_connection(func):
    def wrapper(*args, **kwargs):
        with closing(sqlite3.connect('address_data.db')) as conn:
            with conn:
                return func(conn, *args, **kwargs)
    return wrapper


@with_database_connection
def add_to_database(conn, postcode, address_details):
    cursor = conn.cursor()

    try:
        # Insert the address details into the table
        cursor.execute("INSERT INTO addresses (postcode, application_by, joint_owners, agent_details, local_authority, contact_address, address, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (
            postcode,
            address_details['application_by'],
            address_details['joint_owners'],
            address_details['agent_details'],
            address_details['local_authority'],
            address_details['contact_address'],
            address_details['address'],
            datetime.now()
        ))
        conn.commit()
    except sqlite3.IntegrityError:
        # Address already exists in the database
        logger.info(f"Address already in database: {address_details['address']}")


@with_database_connection
def is_address_in_database(conn, postcode, address):
    cursor = conn.cursor()

    # Check if the address is in the database
    cursor.execute("SELECT * FROM addresses WHERE postcode = ? AND address = ?", (postcode, address))
    result = cursor.fetchone()

    return result is not None


@with_database_connection
def count_data(conn):
    cursor = conn.cursor()

    # Count the number of postcodes and addresses
    cursor.execute("SELECT COUNT(DISTINCT postcode) FROM addresses")
    postcode_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM addresses")
    address_count = cursor.fetchone()[0]

    return postcode_count, address_count


@with_database_connection
def get_last_postcode(conn):
    cursor = conn.cursor()

    # Get the last postcode
    cursor.execute("SELECT postcode FROM addresses ORDER BY postcode DESC LIMIT 1")
    result = cursor.fetchone()
    last_postcode = result[0] if result else None

    return last_postcode

def parse_input_entry(entry):
    if entry.find('"') != -1:
        entry = entry.replace('"', "")

    if entry.find(",") != -1:
        entry = entry.replace(",", "")

    if entry.find("\n") != -1:
        entry = entry.replace("\n", "")

    return entry


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
    logger = logging.getLogger(__name__)

    logger.info("Starting LordScraper")

    # Create the SQLite3 database and table with a unique constraint on the address column
    with closing(sqlite3.connect('address_data.db')) as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS addresses
                         (id INTEGER PRIMARY KEY AUTOINCREMENT, postcode TEXT, application_by TEXT, joint_owners TEXT, agent_details TEXT, local_authority TEXT, contact_address TEXT, address TEXT UNIQUE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        conn.commit()

    postcodes, addresses = count_data()
    logger.info(f"Found {postcodes} postcodes and {addresses} addresses in the database")
    logger.info(f"Last postcode in the database: {get_last_postcode()}")

    logger.info("Press Enter to start scraping")

    input()

    with open("postcodes.txt", "r") as f:
        postcodes = [parse_input_entry(postcode) for postcode in f.readlines()]

    logger.info(f"Found {len(postcodes)} postcodes to investigate")

    # Create a bounded semaphore to limit the number of concurrent threads
    semaphore = BoundedSemaphore(MAX_WORKERS)


    def worker(postcode):
        with semaphore:
            scrape_process(postcode)


    def scrape_process(postcode):
        logger.info(f"Scraping postcode: {postcode}")
        session = requests.Session(impersonate="chrome")
        headers = header.generate()
        headers["Content-Type"] = "application/x-www-form-urlencoded"

        addresses = scrape_addresses(postcode, session, headers)
        logger.info(f"Found {len(addresses)} addresses for postcode {postcode}")

        for address in addresses:
            if is_address_in_database(postcode, address["address"]):
                continue
            logger.info(f"Investigating address: {address['address']}")
            address_details = investigate_address(address['full_address'], address["address"], session, headers)

            if address_details:
                logger.info(f"Found details for address: {address_details}")
                add_to_database(postcode, address_details)


    threads = []
    for postcode in postcodes:
        thread = Thread(target=worker, args=(postcode,))
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()