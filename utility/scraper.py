import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import urlencode
from bs4 import BeautifulSoup
import re
import time
import os
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


def requests_retry_session(
    retries=3,
    backoff_factor=1,  # Increased backoff_factor for a more conservative approach
    status_forcelist=(429, 500, 502, 504),  # Including 429 in the retry status codes
    session=None,
):
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        respect_retry_after_header=True,  # Ensure we respect 'Retry-After'
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def extract_document_id(action_url):
    """
    Extract the document ID from the action URL.
    Assuming the URL follows a pattern like: https://indiankanoon.org/doc/155481249/
    """
    match = re.search(r"/doc/(\d+)/", action_url)
    if match:
        return match.group(1)
    return None


def download_document_pdf(action_url):
    os.makedirs("data/pdfs", exist_ok=True)
    doc_id = extract_document_id(action_url)
    if not doc_id:
        print(f"Failed to extract document ID from URL: {action_url}")
        return

    filename = f"{doc_id}.pdf"
    file_path = os.path.join("data/pdfs/", filename)
    data_payload = {"type": "pdf"}

    with requests_retry_session(retries=5, backoff_factor=2) as session:
        response = session.post(action_url, data=data_payload)
        if response.status_code == 200:
            with open(file_path, "wb") as f:
                f.write(response.content)
            print(f"Successfully downloaded {file_path}")
        elif response.status_code == 429:
            delay = int(
                response.headers.get("Retry-After", 60)
            )  # Fallback to 60 seconds
            print(f"Rate limited. Retrying after {delay} seconds.")
            time.sleep(delay)
            download_document_pdf(action_url)  # Recursive retry
        else:
            print(
                f"Failed to download PDF for document ID {doc_id}, Status code: {response.status_code}"
            )
    os.makedirs("data/pdfs", exist_ok=True)
    doc_id = extract_document_id(action_url)
    if not doc_id:
        print(f"Failed to extract document ID from URL: {action_url}")
        return

    filename = f"{doc_id}.pdf"
    file_path = os.path.join("data/pdfs", filename)
    data_payload = {"type": "pdf"}

    with requests_retry_session() as session:
        response = session.post(action_url, data=data_payload)
        if response.status_code == 200:
            with open(file_path, "wb") as f:
                f.write(response.content)
        else:
            print(
                f"Failed to download PDF for document ID {doc_id}, Status code: {response.status_code}"
            )


def fetch_and_download_pdfs(links):
    for link in links:
        with requests_retry_session(retries=5, backoff_factor=2) as session:
            response = session.get(link)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                form = soup.find("form")
                if form and "action" in form.attrs:
                    action_url = "https://indiankanoon.org" + form["action"]
                    # Perform document PDF download
                    download_document_pdf(action_url)
                else:
                    print("Form not found for", link)
            elif response.status_code == 429:
                delay = int(response.headers.get("Retry-After", 60))
                print(f"Rate limited. Retrying after {delay} seconds.")
                time.sleep(delay)
                # With the retry mechanism, there might be a subsequent attempt after this delay
            else:
                # Handle other error status codes
                print(
                    f"Failed to fetch page for {link}, Status code: {response.status_code}"
                )

        # Adding a delay of 2 seconds between downloads to avoid overwhelming the server
        time.sleep(2)


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


# Example usage:
if __name__ == "__main__":
    base_url = "https://indiankanoon.org"
    search_term = "qureshi doctypes: supremecourt"
    results_url = construct_search_results_url(base_url, search_term)
    print(f"Search Results URL: {results_url}")


# Interactive mode:
if __name__ == "__main__":
    print("Welcome to the Indian Kanoon PDF Downloader!")
    base_url = "https://indiankanoon.org"
    search_term = input("What type of cases are you looking for?: ")
    max_cases = int(input("How many cases would you like to download?: "))
    results_url = construct_search_results_url(base_url, search_term)
    links = fetch_full_document_links(results_url, max_cases)
    save_links_to_csv(links, "data/index.csv")
    print("Index of Downloaded PDFs saved to data/index.csv. Initiating download...")
    fetch_and_download_pdfs(links)
