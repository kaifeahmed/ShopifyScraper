from shopify_scraper import scraper
import requests

url = "https://goddiva.co.uk/"

# Test connection first
try:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    print(f"Store is accessible. Status code: {response.status_code}")
    
    # Continue with scraping if store is accessible
    products = scraper.get_products(url)
    
    if not products.empty:
        # Get variants with images included
        complete_products = scraper.get_variants(products)
        
        # Save to CSV
        complete_products.to_csv('complete_products.csv', index=False)
        print('Total product variants with images:', len(complete_products))
    else:
        print("No products found or error occurred during scraping.")
        
except requests.exceptions.RequestException as e:
    print(f"Cannot access the store: {e}")
