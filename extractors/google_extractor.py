from typing import Dict, List
from .base_extractor import BaseExtractor
import json
from datetime import datetime
import asyncio
from urllib.parse import urlparse, parse_qs

class GoogleExtractor(BaseExtractor):
    async def extract(self, base_url: str, max_pages: int = 2) -> List[Dict]:
        try:
            # Create new page with headers
            context = await self.scraper.browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            all_jobs = []
            current_page = 1
            
            # Navigate to the jobs page first
            print(f"\nLoading Google jobs page: {base_url}")
            await page.goto(base_url)
            await page.wait_for_load_state('networkidle')
            
            while current_page <= max_pages:
                print(f"\nProcessing page {current_page}")
                
                # Wait for job listings to appear
                await page.wait_for_selector("a.WpHeLc.VfPpkd-mRLv6.VfPpkd-RLmnJb", timeout=60000)
                
                # Get pagination info for logging
                pagination = await page.query_selector("div[jsname='uEp2ad']")
                if pagination:
                    pagination_text = await pagination.inner_text()
                    print(f"Current page: {pagination_text}")
                
                # Extract jobs using JavaScript
                jobs = await page.evaluate("""
                    () => {
                        const jobs = [];
                        const jobLinks = document.querySelectorAll("a.WpHeLc.VfPpkd-mRLv6.VfPpkd-RLmnJb");
                        
                        jobLinks.forEach(link => {
                            try {
                                const href = link.getAttribute('href');
                                const title = link.getAttribute('aria-label');
                                const location = link.querySelector('[class*="location"]')?.textContent || '';
                                
                                if (href && title) {
                                    jobs.push({
                                        title: title.trim(),
                                        location: location.trim(),
                                        url: `https://www.google.com/about/careers/applications/${href}`,
                                        job_id: href.split('/').pop()
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
                    next_button = await page.query_selector("a[jsname='hSRGPd'][aria-label='Go to next page']")
                    if next_button and await next_button.is_visible():
                        href = await next_button.get_attribute('href')
                        if href:
                            await page.goto(href)
                            await page.wait_for_load_state('networkidle')
                            await asyncio.sleep(2)  # Wait for page to settle
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
            print(f"\nTotal Google jobs found: {len(all_jobs)}")
            return all_jobs
            
        except Exception as e:
            print(f"Error extracting Google jobs: {e}")
            return []