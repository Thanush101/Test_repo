from typing import Dict, List
from .base_extractor import BaseExtractor
import asyncio
from datetime import datetime
from utils.excel_generator import ExcelGenerator

class AmazonExtractor(BaseExtractor):
    async def extract(self, base_url: str, max_pages: int = 2) -> List[Dict]:
        try:
            # Create new page with custom headers
            context = await self.scraper.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36'
            )
            page = await context.new_page()
            
            all_jobs = []
            current_page = 1

            # Initial page load with retries
            print(f"\nLoading Amazon jobs page: {base_url}")
            await page.goto(base_url)
            
            while current_page <= max_pages:
                print(f"\nProcessing page {current_page}")
                
                # Wait for job listings to load
                await page.wait_for_selector('.job-tile', timeout=60000)
                
                # Extract jobs using JavaScript
                jobs = await page.evaluate("""
                    () => {
                        const jobs = [];
                        const jobTiles = document.querySelectorAll('.job-tile');
                        
                        jobTiles.forEach(tile => {
                            try {
                                const title = tile.querySelector('h3')?.textContent;
                                const location = tile.querySelector('.location-text')?.textContent;
                                const link = tile.querySelector('a')?.href;
                                const jobId = tile.getAttribute('data-job-id');
                                
                                if (title && link) {
                                    jobs.push({
                                        title: title.trim(),
                                        location: location ? location.trim() : '',
                                        url: link,
                                        job_id: jobId
                                    });
                                }
                            } catch (e) {
                                console.error('Error processing job tile:', e);
                            }
                        });
                        return jobs;
                    }
                """)
                
                # Add new jobs to the list and CSV file
                for job in jobs:
                    if job not in all_jobs:  # Avoid duplicates
                        all_jobs.append(job)
                        print(f"Found: {job['title']} - {job['location']}")
                
                if current_page >= max_pages:
                    break
                    
                # Try to go to next page
                try:
                    next_button = await page.wait_for_selector('[aria-label*="Next"]', timeout=5000)
                    if next_button and await next_button.is_visible():
                        await next_button.click()
                        await asyncio.sleep(2)  # Wait for page load
                        current_page += 1
                    else:
                        print("No more pages available")
                        break
                except Exception as e:
                    print(f"Error navigating to next page: {e}")
                    break
            
            await page.close()
            print(f"\nTotal Amazon jobs found: {len(all_jobs)}")
            
            # Add jobs to Excel/CSV
            excel_gen = ExcelGenerator()
            excel_gen.append_jobs(all_jobs, "Amazon")
            
            return all_jobs
            
        except Exception as e:
            print(f"Error extracting Amazon jobs: {e}")
            return []

def extract(scraper, base_url: str) -> List[Dict]:
    """
    Extract job listings from Amazon careers page
    
    Args:
        scraper: JobScraper instance
        base_url: Base URL for Amazon careers
    
    Returns:
        List of job dictionaries containing title, location, and link
    """
    jobs = []
    page = scraper.get_page(base_url)
    amazon_selectors = {
        'job_container': '.job-tile',
        'title': 'h3', 
        'location': '.location-text',
        'url': 'a',
        'next_page': '[data-action="pagination-next-page"]'
    }

    # Wait for job container elements to load
    job_elements = page.query_selector_all(amazon_selectors['job_container'])

    # Extract job information from each container
    for job in job_elements:
        title = job.query_selector(amazon_selectors['title'])
        location = job.query_selector(amazon_selectors['location']) 
        url = job.query_selector(amazon_selectors['url'])

        if title and location and url:
            job_data = {
                'title': title.inner_text(),
                'location': location.inner_text(),
                'link': url.get_attribute('href')
            }
            jobs.append(job_data)
    return jobs 