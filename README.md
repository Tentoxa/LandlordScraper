# 🌍 LordScraper: Landlord Registration Collector

<p align="center">
  A Python script that automatically retrieves and stores landlord registration data from the Landlord Registration Scotland website.
</p>

## Features

- **Scrapes Addresses**: Fetches all registered addresses for a given postcode from the Landlord Registration Scotland website.
- **Extracts Address Details**: Collects detailed information about each registered address, such as the application owner, joint owners, agent details, local authority, and contact address.
- **Stores Data in JSON**: Saves the collected data in a JSON file for easy access and analysis.
- **Multithreaded Scraping**: Utilizes a thread pool to scrape multiple postcodes concurrently, improving the overall performance.

## Prerequisites

- Python 3.x
- `curl_cffi` library for making HTTP requests
- `fake_headers` for generating realistic user agents
- `BeautifulSoup` for parsing HTML
- `urllib.parse` for URL encoding
- `logging` for error handling and logging
- `threading` for multithreaded scraping
- `datetime` for timestamp generation
- `contextlib` for concurrency management
- `sqlite3` for database operations

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Tentoxa/LandlordScraper
   cd LandlordScraper
   ```
1. **Install required Python packages**:
   ```bash
   pip3 install -r requirements.txt
   ```

## Usage
1. **Prepare the `postcodes.txt` file**:
   - Create a text file named `postcodes.txt` in the project directory.
   - Add one or more postcodes (e.g., `EH1 1AA`) to the file, each on a new line.
2. **Run the script**:
   ```bash
   python3 main.py
   ```
   
## Data Structure
The database is named **`address_data.db`** and contains a single table called **`addresses`**. This table is designed to store essential information related to property addresses.

### Table Structure: `addresses`

| Column Name        | Data Type              | Description                                         |
|--------------------|------------------------|-----------------------------------------------------|
| `id`               | Integer (Auto-increment) | Unique identifier for each address record          |
| `postcode`         | Text                   | The postcode associated with the address            |
| `application_by`   | Text                   | The applicant for the landlord registration         |
| `joint_owners`     | Text                   | The joint owners of the property                    |
| `agent_details`    | Text                   | The agent details for the property                  |
| `local_authority`  | Text                   | The local authority responsible for the property     |
| `contact_address`   | Text                   | The contact address for the property                |
| `address`          | Text                   | The full address of the property                    |
| `created_at`       | Timestamp              | The timestamp when the address record was created   |


## License
This project is licensed under the MIT License. See the License file for more information.
