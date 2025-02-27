from abc import ABC, abstractmethod
from typing import List, Dict, Tuple
from utils.html_cleaner import clean_html
import asyncio
import re
import json
from datetime import datetime

class BaseExtractor(ABC):
    def __init__(self, scraper):
        self.scraper = scraper
        # Common selectors found across job sites
        self.selectors = {
            'containers': [
                '.job-tile', '[data-job-id]', 'div[class*="job"]', 
                'div[class*="career"]', 'div[class*="position"]', 
                '.careers-list', '.job-card', '[class*="job-item"]',
                'article', '.listing', '.posting'
            ],
            'title_selectors': [
                '.job-title', '[class*="job-title"]', '[class*="role-title"]',
                'h1', 'h2', 'h3', 'h4', '[class*="title"]'
            ],
            'location_selectors': [
                '.location-text', '[class*="location"]', '.job-location',
                '[data-location]', '[class*="city"]', '[class*="region"]'
            ],
            'link_selectors': [
                # Job-specific paths
                'a[href*="/jobs/"]',
                'a[href*="/careers/"]',
                'a[href*="/positions/"]',
                'a[href*="/opportunities/"]',
                'a[href*="/openings/"]',
                'a[href*="/vacancy/"]',
                'a[href*="/role/"]',
                'a[href*="/details/"]',
                'a[href*="/description/"]',
                'a[href*="/apply/"]',
                
                # Common URL patterns
                'a[href*="job"]',
                'a[href*="career"]',
                'a[href*="position"]',
                'a[href*="posting"]',
                'a[href*="vacancy"]',
                'a[href*="opening"]',
                'a[href*="requisition"]',
                'a[href*="req-id"]',
                'a[href*="jobid"]',
                
                # Common job board patterns
                'a[href*="linkedin.com/jobs"]',
                'a[href*="workday.com/"]',
                'a[href*="lever.co/"]',
                'a[href*="greenhouse.io/"]',
                'a[href*="smartrecruiters.com"]',
                'a[href*="recruitingsite.com"]',
                'a[href*="brassring.com"]',
                'a[href*="icims.com"]',
                
                # Common URL parameters
                'a[href*="?job="]',
                'a[href*="?posting="]',
                'a[href*="?position="]',
                'a[href*="?req="]',
                'a[href*="?id="]',
                
                # Common class and ID patterns
                'a[class*="job-link"]',
                'a[class*="career-link"]',
                'a[class*="position-link"]',
                'a[class*="posting-link"]',
                'a[id*="job-link"]',
                'a[data-job-id]',
                'a[data-posting-id]',
                
                # Generic but relevant patterns
                'a[href*="employment"]',
                'a[href*="work-with-us"]',
                'a[href*="join-our-team"]',
                'a[href*="job-search"]',
                'a[href*="career-search"]'
            ]
        }

    async def extract(self, base_url: str, max_pages: int = 2) -> List[Dict]:
        """
        Generic extract method that works as a fallback for most job sites
        
        Args:
            base_url: Base URL for the company's careers page
            max_pages: Maximum number of pages to scrape
        """
        try:
            context = await self.scraper.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                # Add additional headers to appear more like a real browser
                extra_http_headers={
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Connection': 'keep-alive',
                }
            )
            
            page = await context.new_page()
            
            # Increase default timeout
            page.set_default_timeout(60000)  # 60 seconds
            
            all_jobs = []
            current_page = 1
            
            print(f"\nLoading jobs page: {base_url}")
            
            # Add retry logic for initial page load
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    await page.goto(base_url, wait_until='domcontentloaded', timeout=60000)
                    
                    # Wait for either the job listings or a known element to appear
                    try:
                        await page.wait_for_selector([
                            '.job-tile',
                            '.table--advanced-search__title',
                            'div[class*="job"]',
                            '#frmPagination'
                        ], timeout=30000)
                    except:
                        print("Waiting for additional content to load...")
                        await page.wait_for_load_state('networkidle', timeout=30000)
                    
                    break  # If successful, exit retry loop
                except Exception as e:
                    print(f"Attempt {attempt + 1} failed: {str(e)}")
                    if attempt == max_retries - 1:
                        raise
                    print("Retrying after 5 seconds...")
                    await asyncio.sleep(5)
            
            while current_page <= max_pages:
                print(f"\nProcessing page {current_page}")
                
                # Add delay before extraction to allow dynamic content to load
                await asyncio.sleep(3)
                
                # Extract jobs using enhanced JavaScript logic
                jobs = await self.extract_job_links(page)
                
                # Add new jobs to the list
                for job in jobs:
                    if job not in all_jobs:  # Avoid duplicates
                        all_jobs.append(job)
                        print(f"Found: {job['title']} - {job['location']}")
                
                if current_page >= max_pages:
                    break
                
                # Try to find and click next page button
                next_page_found = await self.try_next_page(page)
                if not next_page_found:
                    break
                    
                current_page += 1
                # Increased delay between pages
                await asyncio.sleep(5)
            
            await page.close()
            print(f"\nTotal jobs found: {len(all_jobs)}")
            return all_jobs
            
        except Exception as e:
            print(f"Error extracting jobs: {str(e)}")
            if 'page' in locals():
                try:
                    # Take screenshot on error for debugging
                    await page.screenshot(path=f'error_screenshot_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
                    print("Error screenshot saved")
                except:
                    pass
                await page.close()
            return []

    async def extract_job_links(self, page):
        """Enhanced job extraction with intelligent selectors"""
        try:
            # Add delay to ensure page is fully loaded
            await asyncio.sleep(2)
            
            # Check if page is loaded properly
            if not await self.scraper.wait_for_page_load(page):
                print("Page not loaded properly, retrying...")
                await page.reload()
                await asyncio.sleep(5)
                if not await self.scraper.wait_for_page_load(page):
                    print("Page still not loaded properly after retry")
                    return []

            # Convert selectors lists to JavaScript arrays
            containers_js = json.dumps(self.selectors['containers'])
            titles_js = json.dumps(self.selectors['title_selectors'])
            locations_js = json.dumps(self.selectors['location_selectors'])
            links_js = json.dumps(self.selectors['link_selectors'])

            jobs = await page.evaluate(f"""
                () => {{
                    const jobs = new Set();
                    const containers = {containers_js};
                    const titleSelectors = {titles_js};
                    const locationSelectors = {locations_js};
                    const linkSelectors = {links_js};
                    
                    const safeQuerySelector = (element, selectors) => {{
                        for (const selector of selectors) {{
                            try {{
                                const found = element.querySelector(selector);
                                if (found) return found;
                            }} catch {{
                                continue;
                            }}
                        }}
                        return null;
                    }};
                    
                    const findJobElements = () => {{
                        let elements = [];
                        for (const selector of containers) {{
                            try {{
                                elements = [...elements, ...document.querySelectorAll(selector)];
                            }} catch {{
                                continue;
                            }}
                        }}
                        return elements;
                    }};
                    
                    const jobElements = findJobElements();
                    
                    jobElements.forEach(container => {{
                        try {{
                            let link = null;
                            // Try finding link in container first
                            for (const linkSelector of linkSelectors) {{
                                link = safeQuerySelector(container, [linkSelector]);
                                if (link?.href) break;
                            }}
                            
                            // If no link found, check if container itself is a link
                            if (!link?.href && container.tagName === 'A') {{
                                link = container;
                            }}
                                
                            if (link?.href) {{
                                const title = 
                                    safeQuerySelector(container, titleSelectors)?.textContent ||
                                    link.textContent;
                                    
                                const location = 
                                    safeQuerySelector(container, locationSelectors)?.textContent ||
                                    '';
                                
                                if (title?.trim()) {{
                                    jobs.add(JSON.stringify({{
                                        url: link.href,
                                        title: title.trim(),
                                        location: location?.trim() || ''
                                    }}));
                                }}
                            }}
                        }} catch (e) {{
                            console.error('Error processing container:', e);
                        }}
                    }});
                    
                    return Array.from(jobs).map(job => JSON.parse(job));
                }}
            """)
            
            return jobs
            
        except Exception as e:
            print(f"Error in job extraction: {str(e)}")
            return []

    async def try_next_page(self, page) -> bool:
        """Try different methods to find and click next page button"""
        next_page_selectors = [
            # Standard next buttons
            '[aria-label*="Next"]',
            '[aria-label*="next"]',
            '[class*="next"]',
            '[class*="Next"]',
            'a[rel="next"]',
            '.next-page',
            '.nextPage',
            '.pagination__next',
            
            # Button-specific selectors
            'button[aria-label*="next"]',
            'button[aria-label*="Next"]',
            'button[class*="next"]',
            'button[class*="Next"]',
            'button.next',
            'button.Next',
            '[data-action*="next"]',
            '[data-action*="Next"]',
            
            # Common pagination patterns
            '.pagination li:last-child a',
            '.pagination__next a',
            '[class*="pagination-next"]',
            '[class*="pager-next"]',
            '.next-link',
            
            # Icon/Arrow based selectors
            '[class*="arrow-next"]',
            '[class*="arrow_next"]',
            '[class*="chevron-right"]',
            '[aria-label="Forward"]',
            '[aria-label="Next Page"]',
            
            # Form-based pagination (like Apple)
            '#frmPagination',
            'form[id*="pagination"]',
            'form[class*="pagination"]',
            
            # Common text patterns
            'a:contains("Next")',
            'a:contains("next")',
            'a:contains("Next Page")',
            'a:contains("Show More")',
            
            # Data attribute patterns
            '[data-page="next"]',
            '[data-navigation="next"]',
            '[data-test*="next"]',
            '[data-testid*="next"]',
            
            # Common class name patterns
            '.load-more',
            '.loadMore',
            '.show-more',
            '.showMore',
            
            # SVG/Icon containers
            '[class*="next-icon"]',
            '[class*="nextIcon"]',
            '.icon-next',
            '.iconNext',
            
            # Specific vendor patterns
            '[class*="pagination-next"]',
            '[class*="pager-next"]',
            '[class*="paginate-next"]',
            
            # URL patterns
            'a[href*="page="]',
            'a[href*="pageNumber="]',
            'a[href*="pageNum="]',
            
            # ARIA patterns
            '[role="button"][aria-label*="next"]',
            '[role="button"][aria-label*="Next"]',
            '[aria-controls*="pagination"]'
        ]

        # Additional form-based pagination selectors
        pagination_form_selectors = {
            'form': [
                '#frmPagination',
                'form[id*="pagination"]',
                'form[class*="pagination"]',
                '.pagination__mid form'
            ],
            'input': [
                '#page-number',
                'input[name*="page"]',
                'input[id*="page"]',
                '[type="text"][name*="page"]'
            ],
            'total_pages': [
                '.pageNumber:last-child',
                '[class*="total-pages"]',
                '[class*="page-count"]',
                'span:contains("of")+span'
            ]
        }
        
        for selector in next_page_selectors:
            try:
                next_button = await page.query_selector(selector)
                if next_button and await next_button.is_visible():
                    # Check if it's a link or button
                    if await next_button.get_attribute('href'):
                        await page.goto(await next_button.get_attribute('href'))
                    else:
                        await next_button.click()
                    await page.wait_for_load_state('networkidle')
                    return True
            except:
                continue
        
        return False

    async def clean_job_description(self, html: str) -> str:
        """Clean job description HTML"""
        return clean_html(html) 