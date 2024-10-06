import os
import re
import pandas as pd
import pytesseract
from PIL import Image
from io import BytesIO
from bs4 import BeautifulSoup
from typing import Any, List, Dict, Tuple


# Function to clean text by removing HTML/XML tags and special characters
def clean_text(text: str) -> str:
    text = re.sub(r'<.*?>', '', text)  # Remove HTML/XML tags
    text = re.sub(r'[^\w\sáéíóúÁÉÍÓÚñÑ]', '', text)  # Remove special characters
    text = re.sub(r'\s+', ' ', text)  # Replace multiple spaces with single space
    return text.strip()

# Function to extract text from images using OCR
def extract_text_from_image(image_bytes: bytes) -> str:
    try:
        image = Image.open(BytesIO(image_bytes))
        extracted_text = pytesseract.image_to_string(image, lang="eng")
        return extracted_text.strip()
    except Exception as e:
        logging.error(f"Error performing OCR: {e}")
        return ""

# Function to extract images and perform OCR on embedded images
def extract_images_and_text(soup: BeautifulSoup) -> str:
    extracted_text = ""
    img_tags = soup.find_all('img')
    for img_tag in img_tags:
        img_src = img_tag.get('src')
        if img_src.startswith('data:image'):  # Base64-encoded images
            image_data = img_src.split(",")[1]
            img_bytes = base64.b64decode(image_data)
            text_from_image = extract_text_from_image(img_bytes)
            if text_from_image:
                extracted_text += text_from_image + "\n\n"
    return extracted_text

# Function to extract tables from HTML/XML
def extract_tables(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    tables = []
    table_tags = soup.find_all('table')
    for table in table_tags:
        try:
            df = pd.read_html(str(table))[0]
            tables.append(df.to_dict(orient='records'))
        except Exception as e:
            continue  # Skip tables that can't be parsed
    return tables