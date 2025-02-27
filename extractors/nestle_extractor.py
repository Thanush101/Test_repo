from typing import List, Dict
from .base_extractor import BaseExtractor
import asyncio
import logging

class NestleExtractor(BaseExtractor):
    def __init__(self, scraper):
        super().__init__(scraper)
        self.logger = logging.getLogger(__name__)

    async def extract(self, base_url: str, max_pages: int = 2) -> List[Dict]:
        """
        Extract jobs from Nestle careers page
        
        Args:
            base_url: Base URL for Nestle careers page
            max_pages: Maximum number of pages to scrape
        """
        try:
            context = await self.scraper.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = await context.new_page()
            all_jobs = []
            
            # Load initial page with retry mechanism
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # First wait for initial load
                    await page.goto(base_url, wait_until='domcontentloaded', timeout=30000)
                    
                    # Then wait for network to be idle
                    await page.wait_for_load_state('networkidle', timeout=30000)
                    
                    # Wait for specific content
                    await page.wait_for_selector('.views-row', timeout=30000)
                    
                    # Success - break the retry loop
                    break
                    
                except Exception as e:
                    self.logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                    if attempt == max_retries - 1:
                        self.logger.error("All attempts to load page failed")
                        await page.close()
                        return []
                    await asyncio.sleep(5)  # Wait before retrying

            current_page = 1
            while current_page <= max_pages:
                self.logger.info(f"Processing page {current_page}")
                
                # Extract jobs from current page
                jobs = await self.extract_jobs_from_page(page)
                all_jobs.extend(jobs)
                
                if current_page >= max_pages:
                    break
                
                # Try to navigate to next page
                has_next = await self.try_next_page(page)
                if not has_next:
                    self.logger.info("No more pages available")
                    break
                
                current_page += 1
                await asyncio.sleep(3)

            await page.close()
            return all_jobs

        except Exception as e:
            self.logger.error(f"Error extracting Nestle jobs: {str(e)}")
            if 'page' in locals():
                await page.close()
            return []

    async def extract_jobs_from_page(self, page) -> List[Dict]:
        """Extract jobs from current page"""
        try:
            # Wait for job listings to be visible
            await page.wait_for_selector('.views-row', timeout=30000)
            
            jobs = await page.evaluate("""
                () => {
                    const jobs = [];
                    // Look for job links in views-row containers
                    document.querySelectorAll('.views-row').forEach(row => {
                        try {
                            const link = row.querySelector('a[href*="jobdetails.nestle.com/job"]');
                            if (link) {
                                const title = link.textContent.trim();
                                const url = link.href;
                                const location = row.querySelector('.field--name-field-job-location')?.textContent?.trim() 
                                            || row.querySelector('.field-location')?.textContent?.trim() 
                                            || 'India';
                                
                                if (title && url && 
                                    !title.toLowerCase().includes('hundreds of jobs')) {
                                    jobs.push({
                                        title: title,
                                        url: url,
                                        location: location,
                                        company: 'Nestle'
                                    });
                                }
                            }
                        } catch (e) {
                            console.error('Error processing job row:', e);
                        }
                    });
                    return jobs;
                }
            """)
            
            filtered_jobs = [
                job for job in jobs
                if job.get('title') and job.get('url') and
                not job['title'].lower().startswith('filter') and
                len(job['title'].strip()) > 0 and
                'jobdetails.nestle.com' in job['url']
            ]
            
            self.logger.info(f"Found {len(filtered_jobs)} valid jobs on current page")
            return filtered_jobs
            
        except Exception as e:
            self.logger.error(f"Error extracting jobs from page: {str(e)}")
            return []

    async def try_next_page(self, page) -> bool:
        """Try to navigate to next page"""
        try:
            # Try to find the next page link using multiple selectors
            for selector in [
                'a[rel="next"][title="Go to next page"]',
                'a[rel="next"]',
                'a[title="Go to next page"]',
                '.pager__item--next a'
            ]:
                next_link = await page.query_selector(selector)
                if next_link and await next_link.is_visible():
                    await next_link.click()
                    await page.wait_for_load_state('networkidle', timeout=30000)
                    await page.wait_for_selector('.views-row', timeout=30000)
                    await asyncio.sleep(3)
                    return True
                    
            return False
            
        except Exception as e:
            self.logger.error(f"Error in pagination: {e}")
            return False 