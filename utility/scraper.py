import requests
from urllib.parse import urlencode
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
import time
import csv


def fetch_full_document_links(search_url, max_cases):
    links_collected = []
    page_num = 0  # Start from the first page
    while len(links_collected) < max_cases:
        url = f"{search_url}&pagenum={page_num}"
        response = requests.get(url)
        if response.status_code != 200:
            print("Failed to fetch page", page_num)
            break
        soup = BeautifulSoup(response.text, "html.parser")
        result_divs = soup.find_all("div", class_="result")
        for div in result_divs:
            full_doc_link = div.find("a", string="Full Document")
            if full_doc_link:
                full_link = "https://indiankanoon.org" + full_doc_link["href"]
                links_collected.append(full_link)
                if len(links_collected) >= max_cases:
                    break
        page_num += 1
    return links_collected


def save_links_to_csv(links, file_name):
    with open(file_name, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        for link in links:
            writer.writerow([link])


def setup_selenium_driver(download_folder="data/pdfs/"):
    chrome_options = Options()

    # Specify the path to ChromeDriver executable
    # Make sure to provide the correct path or manage the driver with webdriver-manager
    service = Service(ChromeDriverManager().install())

    # Set up Chrome preferences to automate download behavior:
    prefs = {
        "download.default_directory": download_folder,  # specifies the directory to download files
        "download.prompt_for_download": False,  # disables the download prompt
        "download.directory_upgrade": True,  # refers to a feature Chrome has to auto-open certain file types
        "plugins.always_open_pdf_externally": True,  # automatically opens PDFs
        "safebrowsing.enabled": True,  # provides safe browsing protections
    }
    chrome_options.add_experimental_option("prefs", prefs)

    # Additional options to run Chrome in headless mode if needed (uncomment if required)
    chrome_options.add_argument("--headless")

    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver


def download_pdfs_from_links(links):
    driver = setup_selenium_driver()
    for link in links:
        try:
            driver.get(link)
            # Wait for page to load - consider using explicit wait here for more reliability
            time.sleep(1)
            # Find and click the download button
            download_button = driver.find_element(By.ID, "pdfdoc")
            download_button.click()
            # Add a delay to ensure the file gets downloaded before moving to the next link
            print(f"Downloaded document from {link}")
        except Exception as e:
            print(f"An error occurred while downloading the document from {link}: {e}")
    driver.quit()


def construct_search_results_url(base_url, search_term):
    """
    Constructs the URL for the search results given a search term.

    Args:
    - base_url (str): The base URL of the website's search page.
    - search_term (str): The term to search for.

    Returns:
    - str: The URL of the search results page.
    """

    query_params = {"formInput": search_term}
    query_string = urlencode(query_params)
    results_url = f"{base_url}/search/?{query_string}"

    return results_url


if __name__ == "__main__":
    print("Welcome to the Indian Kanoon PDF Downloader!")
    print(" ")
    print(
        "This program will download PDFs of legal cases from Indian Kanoon based on your search term."
    )
    print(" ")
    print(
        "Ensure you have a stable and fast internet connection to avoid interruptions."
    )
    print(
        "ATTENTION: This program is relatively slow, will take on an average 1 second per download!"
    )
    print(" ")
    base_url = "https://indiankanoon.org"
    search_term = input("What type of cases are you looking for?: ")
    max_cases = int(input("How many cases would you like to download?: "))
    results_url = construct_search_results_url(base_url, search_term)
    links = fetch_full_document_links(results_url, max_cases)
    save_links_to_csv(links, file_name="data/index.csv")
    print("Index of Downloaded PDFs saved to data/index.csv. Initiating download...")
    download_pdfs_from_links(links)
    print("All downloads completed!")
