import time

from curl_cffi import requests
from fake_headers import Headers
from bs4 import BeautifulSoup
import json
import urllib.parse
import logging
from threading import Thread, BoundedSemaphore

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
            response = session.post("https://www.landlordregistrationscotland.gov.uk/search/registration/property",
                                    data=f"selectedAddress="
                                         f"{encoded_address}",
                                    headers=headers)
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
            responsePostData = session.post("https://www.landlordregistrationscotland.gov.uk/search/postcode",
                                            data="postcode=" + postcode, headers=headers)
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


def add_to_json(postcode, address_details):
    data = {
        "postcodes": {}
    }

    try:
        # Load existing JSON data, if available
        with open("data.json", "r") as file:
            data = json.load(file)
    except FileNotFoundError:
        # Create a new JSON file if it doesn't exist
        with open("data.json", "w") as file:
            json.dump(data, file, indent=2)

        with open("data.json", "r") as file:
            data = json.load(file)

    # Check if the postcode key exists, and create it if not
    if postcode not in data["postcodes"]:
        data["postcodes"][postcode] = []

    # Check for duplicates based on the address
    if not any(existing['address'] == address_details['address'] for existing in data["postcodes"][postcode]):
        data["postcodes"][postcode].append(address_details)

    # Write the updated data back to the JSON file
    with open("data.json", "w") as file:
        json.dump(data, file, indent=2)

    return data


def scrape_process(postcode):
    logger.info(f"Scraping postcode: {postcode}")
    session = requests.Session(impersonate="chrome")
    headers = header.generate()
    headers["Content-Type"] = "application/x-www-form-urlencoded"

    addresses = scrape_addresses(postcode, session, headers)
    logger.info(f"Found {len(addresses)} addresses for postcode {postcode}")

    for address in addresses:
        logger.info(f"Investigating address: {address['address']}")
        address_details = investigate_address(address['full_address'], address["address"], session, headers)

        if address_details:
            logger.info(f"Found details for address: {address_details}")

            add_to_json(postcode, address_details)


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

    with open("postcodes.txt", "r") as f:
        postcodes = [parse_input_entry(postcode) for postcode in f.readlines()]

    logger.info(f"Found {len(postcodes)} postcodes to investigate")

    # Create a bounded semaphore to limit the number of concurrent threads
    semaphore = BoundedSemaphore(MAX_WORKERS)


    def worker(postcode):
        with semaphore:
            scrape_process(postcode)


    threads = []
    for postcode in postcodes:
        thread = Thread(target=worker, args=(postcode,))
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()
