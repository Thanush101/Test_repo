from typing import List, Dict
from .base_extractor import BaseExtractor
import asyncio
import logging

class HCLExtractor(BaseExtractor):
    def __init__(self, scraper):
        super().__init__(scraper)
        self.logger = logging.getLogger(__name__)

    async def extract(self, base_url: str, max_pages: int = 2) -> List[Dict]:
        """
        Extract jobs from HCL careers page
        
        Args:
            base_url: Base URL for HCL careers page
            max_pages: Number of times to click "Load more"
        """
        try:
            # Create new page using browser context
            context = await self.scraper.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = await context.new_page()
            all_jobs = []
            
            # Load initial page
            await page.goto(base_url, wait_until='networkidle')
            await page.wait_for_selector('td[headers="view-field-designation-table-column"]')
            
            # Click "Load more" button max_pages times
            for click_count in range(max_pages):
                # Extract current page jobs
                jobs = await self.extract_jobs_from_page(page)
                all_jobs.extend(jobs)
                
                if click_count < max_pages - 1:  # Don't click after last page
                    # Find and click "Load more" button
                    load_more = await page.query_selector('a.button.btn.default-34[title="Load more items"]')
                    if not load_more:
                        self.logger.info("No more jobs to load")
                        break
                        
                    # Get current job count for verification
                    current_count = len(all_jobs)
                    
                    # Click and wait for new content
                    await load_more.click()
                    await page.wait_for_load_state('networkidle')
                    await asyncio.sleep(2)  # Wait for content to load
                    
                    # Verify new content loaded
                    await page.wait_for_selector('td[headers="view-field-designation-table-column"]')
                    
                    self.logger.info(f"Clicked 'Load more' button ({click_count + 1}/{max_pages})")

            await page.close()
            self.logger.info(f"Total jobs found: {len(all_jobs)}")
            return all_jobs

        except Exception as e:
            self.logger.error(f"Error extracting HCL jobs: {str(e)}")
            if 'page' in locals():
                await page.close()
            return []

    async def extract_jobs_from_page(self, page) -> List[Dict]:
        """Extract jobs from current page content"""
        try:
            jobs = await page.evaluate("""
                () => {
                    const jobs = [];
                    
                    // HCL selectors
                    const hclElements = document.querySelectorAll('td[headers="view-field-designation-table-column"]');
                    
                    // Accenture selectors
                    const accentureElements = document.querySelectorAll('a.cmp-teaser__title-link');
                    
                    // Process HCL jobs
                    hclElements.forEach(element => {
                        const linkElement = element.querySelector('a[data-once="ajaxified-components"]');
                        if (linkElement) {
                            const title = linkElement.textContent.trim();
                            const url = new URL(linkElement.getAttribute('href'), window.location.origin).href;
                            const row = element.closest('tr');
                            const locationCell = row.querySelector('td[headers="view-field-work-location-table-column"]');
                            const location = locationCell ? locationCell.textContent.trim() : '';
                            
                            // Filter out non-job entries
                            const invalidTitles = [
                                'saved jobs', 'filter results', 'search', 'previous', 
                                'next', 'load more', 'new job search', 'careers'
                            ];
                            
                            // Validate the entry
                            if (title && 
                                url.includes('/jobs/') && 
                                !invalidTitles.some(invalid => title.toLowerCase().includes(invalid)) &&
                                !url.includes('jobsearch') &&
                                !url.includes('saved-jobs')) {
                                
                                jobs.push({
                                    title: title,
                                    url: url,
                                    location: location
                                });
                            }
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
        """Try different methods to find and click next page button"""
        try:
            # Try Accenture next button first
            next_button = await page.query_selector('a.cmp-pagination__link-next:not([disabled])')
            if next_button and await next_button.is_visible():
                await next_button.click()
                await page.wait_for_load_state('networkidle')
                return True

            # Try HCL load more button
            load_more = await page.query_selector('a.button.btn.default-34[title="Load more items"]')
            if load_more and await load_more.is_visible():
                await load_more.click()
                await page.wait_for_load_state('networkidle')
                await asyncio.sleep(2)
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error in pagination: {e}")
            return False 