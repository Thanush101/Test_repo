from typing import List, Dict
from .base_extractor import BaseExtractor
import asyncio
import logging

class MahindraExtractor(BaseExtractor):
    def __init__(self, scraper):
        super().__init__(scraper)
        self.logger = logging.getLogger(__name__)

    async def extract(self, base_url: str, max_pages: int = 2) -> List[Dict]:
        """
        Extract jobs from Mahindra careers page
        
        Args:
            base_url: Base URL for Mahindra careers page
            max_pages: Maximum number of pages to scrape
        """
        try:
            # Create new page using browser context
            context = await self.scraper.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = await context.new_page()
            all_jobs = []
            
            # Load initial page with increased timeout
            try:
                await page.goto(base_url, 
                              wait_until='networkidle',
                              timeout=60000)  # Increased timeout to 60 seconds
                await asyncio.sleep(5)  # Additional wait for content
                await page.wait_for_selector('.jobTitle-link', timeout=60000)
            except Exception as e:
                self.logger.error(f"Error loading page: {str(e)}")
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
                    await page.wait_for_selector('.jobTitle-link', timeout=30000)
                    
                    self.logger.info(f"Navigated to page {current_page + 2}/{max_pages}")

            await page.close()
            self.logger.info(f"Total jobs found: {len(all_jobs)}")
            return all_jobs

        except Exception as e:
            self.logger.error(f"Error extracting Mahindra jobs: {str(e)}")
            if 'page' in locals():
                await page.close()
            return []

    async def extract_jobs_from_page(self, page) -> List[Dict]:
        """Extract jobs from current page content"""
        try:
            jobs = await page.evaluate("""
                () => {
                    const jobs = [];
                    
                    // Mahindra job selectors
                    document.querySelectorAll('.jobTitle-link').forEach(element => {
                        try {
                            const title = element.textContent.trim();
                            const url = element.href;
                            const jobContainer = element.closest('.job-listing-item');
                            const location = jobContainer?.querySelector('.job-location')?.textContent.trim();
                            
                            // Filter out non-job entries
                            const invalidTitles = [
                                'saved jobs', 'filter', 'search', 'previous', 
                                'next', 'load more', 'new job search', 'careers'
                            ];
                            
                            // Validate the entry
                            if (title && 
                                url && 
                                !invalidTitles.some(invalid => title.toLowerCase().includes(invalid))) {
                                
                                // Ensure absolute URL
                                const baseUrl = 'https://jobs.mahindracareers.com';
                                const fullUrl = url.startsWith('http') ? url : `${baseUrl}${url}`;
                                
                                jobs.push({
                                    title: title,
                                    url: fullUrl,
                                    location: location || 'India',
                                    company: 'Mahindra'
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
        """Try to navigate to next page using Mahindra's pagination"""
        try:
            # Find the current page number
            current_page = await page.evaluate("""
                () => {
                    const activePage = document.querySelector('.pagination li.active a');
                    return activePage ? parseInt(activePage.getAttribute('title').replace('Page ', '')) : 1;
                }
            """)
            
            # Calculate next page's startrow value
            next_startrow = (current_page) * 10
            
            # Try to find and click next page link
            next_page = await page.query_selector(f'a[href*="startrow={next_startrow}"][rel="nofollow"]')
            if next_page:
                await next_page.click()
                await page.wait_for_load_state('networkidle')
                await asyncio.sleep(3)  # Increased wait time
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error in pagination: {e}")
            return False 