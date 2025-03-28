"""
Shopify scraper
Description: Scrapes products from a Shopify store by parsing products.json and converting it to a pandas DataFrame.
Author: Matt Clarke
"""

import json
import pandas as pd
import requests
import time


def get_json(url, page, max_retries=3):
    """
    Get Shopify products.json from a store URL with retry mechanism.

    Args:
        url (str): URL of the store.
        page (int): Page number of the products.json.
        max_retries (int): Maximum number of retry attempts
    Returns:
        products_json: Products.json from the store or None if all retries fail.
    """
    for attempt in range(max_retries):
        try:
            response = requests.get(
                f'{url}/products.json?limit=250&page={page}',
                timeout=10,  # Increased timeout
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )
            response.raise_for_status()
            return response.text

        except requests.exceptions.RequestException as error:
            print(f"Attempt {attempt + 1}/{max_retries} failed: {error}")
            if attempt == max_retries - 1:
                print(f"Failed to fetch data after {max_retries} attempts")
                return None
            time.sleep(2)  # Wait 2 seconds before retrying


def to_df(products_json):
    """
    Convert products.json to a pandas DataFrame.

    Args:
        products_json (json): Products.json from the store.
    Returns:
        df: Pandas DataFrame of the products.json or empty DataFrame if conversion fails.
    """
    if not products_json:
        return pd.DataFrame()

    try:
        products_dict = json.loads(products_json)
        if not products_dict or 'products' not in products_dict:
            return pd.DataFrame()
        return pd.DataFrame.from_dict(products_dict['products'])
    except Exception as e:
        print(f"Error converting JSON to DataFrame: {e}")
        return pd.DataFrame()


def get_products(url):
    """
    Get all products from a store.

    Args:
        url (str): Store URL
    Returns:
        df: Pandas DataFrame of the products.json.
    """
    results = True
    page = 1
    df = pd.DataFrame()
    max_pages = 100  # Safety limit to prevent infinite loops

    while results and page <= max_pages:
        print(f"Fetching page {page}...")
        products_json = get_json(url, page)
        products_dict = to_df(products_json)

        if products_dict.empty:
            break
        
        df = pd.concat([df, products_dict], ignore_index=True)
        page += 1

    if df.empty:
        print("No products were found or there was an error fetching the data.")
        return df

    df['url'] = f"{url}/products/" + df['handle'].astype(str)
    print(f"Successfully fetched {len(df)} products")
    return df


def get_variants(products):
    """Get variants from a list of products and merge with product data.

    Args:
        products (pd.DataFrame): Pandas dataframe of products from get_products()

    Returns:
        variants (pd.DataFrame): Pandas dataframe of variants with product data
    """
    products['id'] = products['id'].astype(int)
    df_variants = pd.DataFrame()

    for row in products.itertuples(index='True'):
        variants_df = pd.DataFrame.from_records(getattr(row, 'variants'))
        
        # Get all images for this product
        product_images = []
        if hasattr(row, 'images') and isinstance(row.images, list):
            for img in row.images:
                if isinstance(img, dict):
                    product_images.append({
                        'image_url': img.get('src'),
                        'position': img.get('position', 1),
                        'image_id': img.get('id')
                    })
        
        # If no images found, try featured_image
        if not product_images and hasattr(row, 'featured_image'):
            if isinstance(row.featured_image, dict):
                product_images.append({
                    'image_url': row.featured_image.get('src'),
                    'position': 1,
                    'image_id': row.featured_image.get('id')
                })

        # Add product information to each variant
        variants_df['product_id'] = row.id
        variants_df['product_title'] = row.title
        variants_df['product_vendor'] = row.vendor
        variants_df['product_handle'] = row.handle
        variants_df['product_url'] = row.url
        variants_df['product_type'] = row.product_type
        variants_df['published_at'] = row.published_at
        variants_df['tags'] = ','.join(row.tags) if isinstance(row.tags, list) else ''
        
        # Duplicate variants for each image
        if product_images:
            variants_expanded = pd.DataFrame()
            for img in product_images:
                variants_copy = variants_df.copy()
                variants_copy['image_url'] = img['image_url']
                variants_copy['image_position'] = img['position']
                variants_copy['image_id'] = img['image_id']
                variants_expanded = pd.concat([variants_expanded, variants_copy])
            variants_df = variants_expanded
        
        df_variants = pd.concat([df_variants, variants_df])

    return df_variants


def json_list_to_df(df, col):
    """Return a Pandas dataframe based on a column that contains a list of JSON objects.

    Args:
        df (Pandas dataframe): The dataframe to be flattened.
        col (str): The name of the column that contains the JSON objects.

    Returns:
        Pandas dataframe: A new dataframe with the JSON objects expanded into columns.
    """
    try:
        # Handle empty dataframe
        if df.empty:
            return pd.DataFrame()

        # Create a list of all items from the JSON lists
        rows = []
        for items in df[col]:
            if isinstance(items, list):
                rows.extend(items)
            
        # Convert to DataFrame
        if rows:
            return pd.DataFrame(rows)
        return pd.DataFrame()
        
    except Exception as e:
        print(f"Error processing JSON list to DataFrame: {e}")
        return pd.DataFrame()


def get_images(df_products):
    """Get images from a list of products.

    Args:
        df_products (pd.DataFrame): Pandas dataframe of products from get_products()

    Returns:
        images (pd.DataFrame): Pandas dataframe of images
    """

    return json_list_to_df(df_products, 'images')

