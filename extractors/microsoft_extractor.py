from typing import Dict, List
from .base_extractor import BaseExtractor

def extract(scraper, base_url: str) -> List[Dict]:
    """
    Extract job listings from Microsoft careers page
    
    Args:
        scraper: JobScraper instance
        base_url: Base URL for Microsoft careers
    
    Returns:
        List of job dictionaries containing title, location, and link
    """
    jobs = []
    page = scraper.get_page(base_url)
    
    # Add Microsoft-specific extraction logic here
    # This is a placeholder - you'll need to implement the actual scraping logic
    
    return jobs 

class MicrosoftExtractor(BaseExtractor):
    async def extract(self, base_url):
        try:
            # Navigate to Microsoft careers page
            page = await self.scraper.browser.new_page()
            await page.goto(base_url)
            
            # Wait for job listings to load
            await page.wait_for_selector('div[class*="job"]', timeout=60000)
            
            # Extract job information
            jobs = []
            job_elements = await page.query_selector_all('div[class*="job"]')
            
            for job in job_elements:
                title = await job.query_selector('h3, [class*="title"]')
                location = await job.query_selector('[class*="location"]')
                link = await job.query_selector('a')
                
                job_data = {
                    'title': (await title.inner_text() if title else '').strip(),
                    'location': (await location.inner_text() if location else '').strip(),
                    'url': await link.get_attribute('href') if link else ''
                }
                if job_data['title'] and job_data['url']:
                    jobs.append(job_data)
            
            await page.close()
            return jobs
            
        except Exception as e:
            print(f"Error extracting Microsoft jobs: {e}")
            return [] 