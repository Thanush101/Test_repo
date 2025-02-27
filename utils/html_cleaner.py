import re
from bs4 import BeautifulSoup

def clean_html(html: str) -> str:
    """
    Clean HTML content by removing unnecessary whitespace and tags
    
    Args:
        html: Raw HTML content
        
    Returns:
        Cleaned HTML content
    """
    # Remove script and style elements
    soup = BeautifulSoup(html, 'html.parser')
    for script in soup(["script", "style"]):
        script.decompose()
    
    # Get text
    text = soup.get_text()
    
    # Remove extra whitespace
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = ' '.join(chunk for chunk in chunks if chunk)
    
    return text 