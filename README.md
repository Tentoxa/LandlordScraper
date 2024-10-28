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
- `json` for handling JSON data
- `urllib.parse` for URL encoding
- `logging` for error handling and logging
- `threading` for multithreaded scraping

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
The collected data is stored in a JSON file named `data.json`. The structure of the JSON file is as follows:

```json
{
  "postcodes": {
    "postcode1": [
      {
        "address": "Address 1",
        "application_by": "Applicant 1",
        "joint_owners": "Joint Owner 1, Joint Owner 2",
        "agent_details": "Agent Details 1",
        "local_authority": "Local Authority 1",
        "contact_address": "Contact Address 1"
      },
      {
        "address": "Address 2",
        "application_by": "Applicant 2",
        "joint_owners": "Joint Owner 3",
        "agent_details": "Agent Details 2",
        "local_authority": "Local Authority 2",
        "contact_address": "Contact Address 2"
      }
    ],
    "postcode2": [
      {
        "address": "Address 3",
        "application_by": "Applicant 3",
        "joint_owners": null,
        "agent_details": "Agent Details 3",
        "local_authority": "Local Authority 3",
        "contact_address": "Contact Address 3"
      }
    ]
  }
}
```

## License
This project is licensed under the MIT License. See the License file for more information.
