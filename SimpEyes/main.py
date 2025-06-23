import os
import time
import pyfiglet
import threading
from colorama import Fore, Style, init
from utils import get_websites, log_website_data, validate_url_with_retry, is_simplia_site
from datetime import datetime

init(autoreset=True)

# Banner
def display_banner():
    banner = pyfiglet.figlet_format("SimpEyes")
    print(Fore.CYAN + banner + Style.RESET_ALL)
    print(Fore.YELLOW + "Coded with love by Subir | Version 2.0" + Style.RESET_ALL)

# Function to check a single website
def check_website(website, tester_name, downtime_tracker, index):
    # Validate URL with retry logic
    load_time, status, domain_expiry, error_page_status = validate_url_with_retry(website)

    # Format load time to 2 decimal places
    load_time_str = f"{load_time:.2f} sec" if load_time is not None else "Unavailable"

    # Determine downtime status
    downtime_status = "NA" if downtime_tracker[website] == 0 else f"{downtime_tracker[website]} sec"

    # Check if the website is a Simplia site
    simplia_site = is_simplia_site(website)

    # Handle downtime logic
    if status != "Up":
        downtime_tracker[website] += 15  # Increment downtime by 15 seconds
        print(
            Fore.RED
            + f"[ALERT] {website} is DOWN! Downtime: {downtime_tracker[website]} seconds."
            + Style.RESET_ALL
        )

        # Log failure on the first attempt
        if downtime_tracker[website] == 15:
            log_website_data(index, tester_name, website, load_time_str, status, domain_expiry, downtime_status, simplia_site, error_page_status, "down_sites.csv")
    else:
        # If the website was previously down, notify it's back up
        if downtime_tracker[website] > 0:
            print(
                Fore.GREEN
                + f"[RECOVERY] {website} is BACK UP! Total Downtime: {downtime_tracker[website]} seconds."
                + Style.RESET_ALL
            )
            downtime_tracker[website] = 0  # Reset downtime

        # Log "Up" sites in a separate CSV file
        log_website_data(index, tester_name, website, load_time_str, status, domain_expiry, downtime_status, simplia_site, error_page_status, "up_sites.csv")

    # Beautify console output
    status_color = Fore.GREEN if status == "Up" else Fore.RED
    print(
        Fore.CYAN
        + f"[{index}] "
        + Fore.YELLOW
        + f"Website: {website} | "
        + Fore.BLUE
        + f"Load Time: {load_time_str} | "
        + status_color
        + f"Status: {status} | "
        + Fore.MAGENTA
        + f"Domain Expiry: {domain_expiry} | Downtime: {downtime_status} | Simplia Site: {simplia_site} | Error Page: {error_page_status}"
        + Style.RESET_ALL
    )

# Monitor websites concurrently in batches of 20
def monitor_websites(websites, tester_name):
    downtime_tracker = {website: 0 for website in websites}  # Track downtime in seconds

    try:
        while True:
            # Process websites in batches of 20
            for i in range(0, len(websites), 20):
                batch = websites[i:i + 20]  # Get the next 20 websites
                threads = []

                # Create a thread for each website in the batch
                for j, website in enumerate(batch, start=i + 1):
                    thread = threading.Thread(target=check_website, args=(website, tester_name, downtime_tracker, j))
                    threads.append(thread)
                    thread.start()

                # Wait for all threads in the batch to complete
                for thread in threads:
                    thread.join()

                # Wait 2 seconds before the next batch
                if i + 20 < len(websites):  # Only wait if there are more websites to check
                    print(Fore.YELLOW + "\nWaiting for 2 seconds before the next batch..." + Style.RESET_ALL)
                    time.sleep(2)

            # Wait 10 minutes before restarting the monitoring cycle
            print(Fore.YELLOW + "\nAll websites checked. Waiting for 30 min before restarting..." + Style.RESET_ALL)
            time.sleep(1800)  # Wait for 15 minutes

    except KeyboardInterrupt:
        print(Fore.RED + "\nMonitoring Stopped by User..." + Style.RESET_ALL)

# Main function
def main():
    display_banner()

    choice = input("\nDo you want to monitor a single website or load from a file? (single/file): ")

    if choice.lower() == 'single':
        website = input("\nEnter the website URL: ")
        websites = [website]
    elif choice.lower() == 'file':
        file_path = input("\nEnter the path to the websites file: ")
        websites = get_websites(file_path)
    else:
        print("\nInvalid choice. Exiting.")
        return

    tester_name = input("\nEnter your name: ")
    monitor_websites(websites, tester_name)

if __name__ == "__main__":
    main()