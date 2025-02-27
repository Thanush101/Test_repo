from typing import Dict, List
from .base_extractor import BaseExtractor
import asyncio
from datetime import datetime

class CiscoExtractor(BaseExtractor):
    async def extract(self, base_url: str, max_pages: int = 2) -> List[Dict]:
        try:
            # Create new page with custom headers and viewport
            context = await self.scraper.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
            )
            page = await context.new_page()
            page.set_default_timeout(60000)  # 60 second timeout
            
            all_jobs = []
            current_page = 1
            
            # Initial page load with better error handling
            print(f"\nLoading Cisco jobs page: {base_url}")
            await page.goto(base_url, wait_until="domcontentloaded")
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(5)  # Wait for dynamic content
            
            while current_page <= max_pages:
                print(f"\nProcessing page {current_page}")
                
                # Wait for job listings to appear
                await page.wait_for_selector("a[href*='/jobs/ProjectDetail/']", timeout=60000)
                
                # Extract jobs using JavaScript
                jobs = await page.evaluate("""
                    () => {
                        const jobs = [];
                        const jobLinks = document.querySelectorAll("a[href*='/jobs/ProjectDetail/']");
                        
                        jobLinks.forEach(link => {
                            try {
                                const container = link.closest('.job-listing') || link.parentElement;
                                const title = link.innerText;
                                const href = link.href;
                                const location = container.querySelector('[class*="location"]')?.innerText || '';
                                const jobId = href.split('/').pop();
                                
                                if (title && href) {
                                    jobs.push({
                                        title: title.trim(),
                                        location: location.trim(),
                                        url: href,
                                        job_id: jobId
                                    });
                                }
                            } catch (e) {
                                console.error('Error processing job link:', e);
                            }
                        });
                        return jobs;
                    }
                """)
                
                # Add new jobs to the list
                for job in jobs:
                    if job not in all_jobs:  # Avoid duplicates
                        all_jobs.append(job)
                        print(f"Found: {job['title']} - {job['location']}")
                
                if current_page >= max_pages:
                    break
                
                # Try to go to next page
                try:
                    next_button = await page.query_selector("a.pagination_item:has-text('Next >>')")
                    if next_button and await next_button.is_visible():
                        href = await next_button.get_attribute('href')
                        if href:
                            await page.goto(href, wait_until="domcontentloaded")
                            await page.wait_for_load_state("networkidle")
                            await asyncio.sleep(3)  # Wait for page to settle
                            current_page += 1
                        else:
                            print("No more pages available")
                            break
                    else:
                        print("Reached last page")
                        break
                except Exception as e:
                    print(f"Error navigating to next page: {e}")
                    break
            
            await page.close()
            print(f"\nTotal Cisco jobs found: {len(all_jobs)}")
            return all_jobs
            
        except Exception as e:
            print(f"Error extracting Cisco jobs: {e}")
            return [] 