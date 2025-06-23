import requests
import whois
import time
import configparser
import csv
import os
from datetime import datetime
import socket
from colorama import Fore, Style, init
from urllib.parse import urlparse

init(autoreset=True)

# Read configuration from config.ini
config = configparser.ConfigParser()
config.read("config/config.ini")

# Function to get websites from a file
def get_websites(file_path):
    try:
        with open(file_path, 'r') as file:
            websites = [line.strip() for line in file if line.strip()]
        return websites
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return []

# Function to get WHOIS information
def get_whois_info(domain_name):
    try:
        domain_name = domain_name.split("//")[-1].split("/")[0]
        domain_info = whois.query(domain_name)
        return domain_info
    except Exception as e:
        print(f"{Fore.RED}WHOIS lookup failed for {domain_name}: {e}{Style.RESET_ALL}")
        return None

# Function to validate URL and check website status with retry logic
def validate_url_with_retry(url, retries=3, delay=5):
    for attempt in range(retries):
        try:
            # Ensure the URL starts with http:// or https://
            if not url.startswith(("http://", "https://")):
                url = "http://" + url

            # Measure the load time of the website
            start_time = time.time()
            response = requests.get(url, timeout=15)
            load_time = time.time() - start_time

            # Check if the website is reachable
            if response.status_code == 200:
                status = "Up"
            else:
                status = f"Down (HTTP {response.status_code})"

            # Check for error messages in the HTML content
            error_messages = ["Pardon us!", "We are in the middle of upgrading.", "We will be back in a few minutes", "PAGE NOT FOUND!"]
            error_page_found = any(error_message in response.text for error_message in error_messages)

            # Check for error in the title tag
            title_error = "<title>Error Page</title>" in response.text or "<title>404</title>" in response.text or "Page Not Found" in response.text

            # Determine if the site is down due to error page
            if error_page_found or title_error:
                status = "Down (Error Page)"
                error_page_status = "Pardon Page Found" if error_page_found else "Error in Title"
            else:
                error_page_status = "No"

            # Get domain details using WHOIS
            domain_info = get_whois_info(url)
            domain_expiry = (
                domain_info.expiration_date[0]
                if domain_info and hasattr(domain_info, "expiration_date") and isinstance(domain_info.expiration_date, list)
                else getattr(domain_info, "expiration_date", "Unavailable")
            )

            return load_time, status, domain_expiry, error_page_status

        except (requests.exceptions.RequestException, Exception) as e:
            print(f"{Fore.YELLOW}Attempt {attempt + 1}/{retries} failed for {url}. Retrying in {delay} seconds...{Style.RESET_ALL}")
            time.sleep(delay)

    # If all attempts fail, return consistent data
    print(f"{Fore.RED}All retry attempts failed for {url}.{Style.RESET_ALL}")
    return None, "Down (Error)", None, "No"

# Function to log website data into a CSV file
def log_website_data(sl, tester_name, website, load_time, status, domain_expiry, downtime, simplia_site, error_page_status, log_file):
    # Ensure the logs directory exists
    logs_dir = "logs"
    os.makedirs(logs_dir, exist_ok=True)

    # Construct the full path to the log file
    log_file_path = os.path.join(logs_dir, log_file)

    try:
        # Check if the log file exists, and write headers if it doesn't
        if not os.path.exists(log_file_path):
            with open(log_file_path, "w", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(["SL", "Date", "Time", "Tester Name", "Website", "Load Time", "Status", "Domain Expiry Date", "Downtime", "Is Simplia Site", "Error Page"])

        # Append the data to the log file
        with open(log_file_path, "a", newline="") as file:
            writer = csv.writer(file)
            date = datetime.now().strftime("%Y-%m-%d")
            time_str = datetime.now().strftime("%H:%M:%S")
            writer.writerow([sl, date, time_str, tester_name, website, load_time, status, domain_expiry, downtime, simplia_site, error_page_status])
    except PermissionError:
        print(f"Permission denied while accessing {log_file_path}. Close the file if opened. Retrying...")
        time.sleep(2)  # Wait for a moment before retrying
        log_website_data(sl, tester_name, website, load_time, status, domain_expiry, downtime, simplia_site, error_page_status, log_file)

# Function to check if a website is a Simplia site
def is_simplia_site(url):
    """
    Check if the given website's source code contains the word "simplia".

    Args:
        url (str): The URL of the website to check.

    Returns:
        str: "Yes" if the word "simplia" is found, otherwise "No".
    """
    try:
        # Ensure the URL has a scheme (e.g., http:// or https://)
        if not urlparse(url).scheme:
            url = "http://" + url

        # Define headers to mimic a legitimate browser request
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        # Fetch the HTML source code of the website
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Check if the word "simplia" is in the source code (case-insensitive)
        if "simplia" in response.text.lower():
            return "Yes"
        else:
            return "No"

    except requests.exceptions.RequestException as e:
        print(Fore.RED + f"Error fetching {url}: {e}")
        return "No"