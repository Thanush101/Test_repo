from typing import List, Dict
from .base_extractor import BaseExtractor
import asyncio
import logging

class IBMExtractor(BaseExtractor):
    def __init__(self, scraper):
        super().__init__(scraper)
        self.logger = logging.getLogger(__name__)

    async def extract(self, base_url: str, max_pages: int = 2) -> List[Dict]:
        """
        Extract jobs from IBM careers page
        
        Args:
            base_url: Base URL for IBM careers page
            max_pages: Number of pages to scrape
        """
        try:
            # Create new page using browser context with additional options
            context = await self.scraper.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                ignore_https_errors=True  # Added to handle SSL issues
            )
            page = await context.new_page()
            all_jobs = []
            
            # Update base URL to the correct IBM careers URL
            corrected_url = "https://www.ibm.com/in-en/careers/search?field_keyword_17[0]=Remote&field_keyword_05[0]=India"
            
            # Load initial page with longer timeout and retry logic
            try:
                await page.goto(corrected_url, 
                              wait_until='networkidle',
                              timeout=60000)  # Increased timeout
                await asyncio.sleep(5)  # Longer wait for dynamic content
                
                # Wait for job cards with retry
                for _ in range(3):  # Retry up to 3 times
                    try:
                        await page.wait_for_selector('.bx--card-group__card', timeout=20000)
                        break
                    except:
                        await asyncio.sleep(2)
                        continue
                
            except Exception as e:
                self.logger.error(f"Error loading initial page: {str(e)}")
                await page.close()
                return []
            
            # Extract jobs from each page
            for current_page in range(max_pages):
                # Extract current page jobs
                jobs = await self.extract_jobs_from_page(page)
                all_jobs.extend(jobs)
                
                if current_page < max_pages - 1:  # Don't navigate after last page
                    # Try to go to next page
                    has_next = await self.try_next_page(page)
                    if not has_next:
                        self.logger.info("No more pages available")
                        break
                    
                    await asyncio.sleep(3)  # Wait for content to load
                    await page.wait_for_selector('.bx--card-group__card')
                    
                    self.logger.info(f"Navigated to page {current_page + 2}/{max_pages}")

            await page.close()
            self.logger.info(f"Total jobs found: {len(all_jobs)}")
            return all_jobs

        except Exception as e:
            self.logger.error(f"Error extracting IBM jobs: {str(e)}")
            if 'page' in locals():
                await page.close()
            return []

    async def extract_jobs_from_page(self, page) -> List[Dict]:
        """Extract jobs from current page content"""
        try:
            # Wait for job cards to be visible
            await page.wait_for_selector('.bx--card-group__card', timeout=30000)
            
            jobs = await page.evaluate("""
                () => {
                    const jobs = [];
                    
                    // IBM job selectors
                    document.querySelectorAll('.bx--card-group__card').forEach(element => {
                        try {
                            const title = element.querySelector('.bx--card__heading')?.textContent.trim();
                            const url = element.href || element.getAttribute('href');
                            const category = element.querySelector('.bx--card__eyebrow')?.textContent.trim() || '';
                            const locationElement = element.querySelector('.ibm--card__copy__inner');
                            let location = '';
                            
                            if (locationElement) {
                                const locationText = locationElement.textContent.trim();
                                const locationParts = locationText.split('\\n');
                                location = locationParts.length > 1 ? locationParts[1].trim() : locationText;
                            }
                            
                            // Filter out non-job entries
                            const invalidTitles = [
                                'saved jobs', 'filter', 'search', 'previous', 
                                'next', 'load more', 'new job search', 'careers'
                            ];
                            
                            // Validate the entry
                            if (title && 
                                url && 
                                !invalidTitles.some(invalid => title.toLowerCase().includes(invalid))) {
                                
                                // Ensure URL is absolute
                                const fullUrl = url.startsWith('http') ? url : 
                                              new URL(url, 'https://careers.ibm.com').href;
                                
                                jobs.push({
                                    title: title,
                                    url: fullUrl,
                                    location: location,
                                    category: category,
                                    company: 'IBM'
                                });
                            }
                        } catch (e) {
                            console.error('Error processing job element:', e);
                        }
                    });
                    
                    return jobs;
                }
            """)
            
            # Additional Python-side filtering
            filtered_jobs = [
                job for job in jobs
                if (job.get('title') and 
                    job.get('url') and 
                    not job['title'].startswith('#') and
                    not job['title'].lower().startswith('filter') and
                    len(job['title'].strip()) > 0)
            ]
            
            self.logger.info(f"Found {len(filtered_jobs)} valid jobs on current page")
            return filtered_jobs
            
        except Exception as e:
            self.logger.error(f"Error extracting jobs from page: {str(e)}")
            return []

    async def try_next_page(self, page) -> bool:
        """Try to navigate to next page"""
        try:
            # Try IBM's next page button with multiple selectors
            for selector in [
                '#IBMAccessibleItemComponents-next:not([disabled])',
                '.cds--pagination-nav__page[data-key="next"]:not([disabled])',
                'a[aria-label="Next"]:not([disabled])'
            ]:
                next_button = await page.query_selector(selector)
                if next_button and await next_button.is_visible():
                    await next_button.click()
                    await page.wait_for_load_state('networkidle')
                    await asyncio.sleep(2)
                    # Verify new content loaded
                    await page.wait_for_selector('.bx--card-group__card')
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error in pagination: {e}")
            return False 