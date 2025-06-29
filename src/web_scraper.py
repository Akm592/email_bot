import requests
from bs4 import BeautifulSoup

def scrape_company_info(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status() # Raise an exception for HTTP errors
        soup = BeautifulSoup(response.text, 'html.parser')

        # Basic scraping: try to find common elements that might contain company info
        # This is a very simplified example and might need significant improvement
        # for real-world scenarios.
        text_content = soup.get_text(separator=' ', strip=True)
        
        # Limit the content to avoid overwhelming the LLM
        return text_content[:2000] # Return first 2000 characters

    except requests.exceptions.RequestException as e:
        print(f"Web scraping error: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during scraping: {e}")
        return None
