from typing import List, Dict
from .base_extractor import BaseExtractor
import asyncio
import logging

class CapgeminiExtractor(BaseExtractor):
    def __init__(self, scraper):
        super().__init__(scraper)
        self.logger = logging.getLogger(__name__)

    async def extract(self, base_url: str, max_pages: int = 2) -> List[Dict]:
        """
        Extract jobs from Capgemini careers page
        
        Args:
            base_url: Base URL for Capgemini careers page
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
            await page.wait_for_selector('a.table-tr.filter-box.joblink')
            
            # Click "Load more" button max_pages times
            for click_count in range(max_pages):
                # Extract current page jobs
                jobs = await self.extract_jobs_from_page(page)
                all_jobs.extend(jobs)
                
                if click_count < max_pages - 1:  # Don't click after last page
                    # Find and click "Load more" button
                    load_more = await page.query_selector('a.filters-more[aria-label="Load More about jobs"]')
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
                    await page.wait_for_selector('a.table-tr.filter-box.joblink')
                    
                    self.logger.info(f"Clicked 'Load more' button ({click_count + 1}/{max_pages})")

            await page.close()
            self.logger.info(f"Total jobs found: {len(all_jobs)}")
            return all_jobs

        except Exception as e:
            self.logger.error(f"Error extracting Capgemini jobs: {str(e)}")
            if 'page' in locals():
                await page.close()
            return []

    async def extract_jobs_from_page(self, page) -> List[Dict]:
        """Extract jobs from current page content"""
        try:
            jobs = await page.evaluate("""
                () => {
                    const jobs = [];
                    
                    // Capgemini job selectors
                    document.querySelectorAll('a.table-tr.filter-box.joblink').forEach(element => {
                        try {
                            const title = element.querySelector('.table-td.table-title div:not(.table-td-header)')?.textContent.trim();
                            const url = new URL(element.getAttribute('href'), window.location.origin).href;
                            const locationDiv = Array.from(element.querySelectorAll('.table-td.table-title'))
                                .find(td => td.querySelector('.table-td-header')?.textContent.includes('Location'));
                            const location = locationDiv?.querySelector('div:not(.table-td-header)')?.textContent.trim() || '';
                            
                            // Additional details
                            const experienceDiv = Array.from(element.querySelectorAll('.table-td.table-title'))
                                .find(td => td.querySelector('.table-td-header')?.textContent.includes('Experience'));
                            const experience = experienceDiv?.querySelector('div:not(.table-td-header)')?.textContent.trim() || '';
                            
                            const contractDiv = Array.from(element.querySelectorAll('.table-td.table-title'))
                                .find(td => td.querySelector('.table-td-header')?.textContent.includes('Contract'));
                            const contractType = contractDiv?.querySelector('div:not(.table-td-header)')?.textContent.trim() || '';
                            
                            // Filter out non-job entries
                            const invalidTitles = [
                                'saved jobs', 'filter results', 'search', 'previous', 
                                'next', 'load more', 'new job search', 'careers'
                            ];
                            
                            // Validate the entry
                            if (title && 
                                url.includes('/jobs/') && 
                                !invalidTitles.some(invalid => title.toLowerCase().includes(invalid))) {
                                
                                jobs.push({
                                    title: title,
                                    url: url,
                                    location: location,
                                    experience: experience,
                                    contract_type: contractType,
                                    company: 'Capgemini'
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
        """Try to load more jobs"""
        try:
            # Try Capgemini load more button
            load_more = await page.query_selector('a.filters-more[aria-label="Load More about jobs"]')
            if load_more and await load_more.is_visible():
                await load_more.click()
                await page.wait_for_load_state('networkidle')
                await asyncio.sleep(2)
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error in pagination: {e}")
            return False 