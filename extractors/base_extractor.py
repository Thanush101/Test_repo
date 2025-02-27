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
                'article', '.listing', '.posting',
                '.bx--card-group__card', '.bx--tile.bx--card',
                '.bx--card__wrapper', '.bx--card__content',
                'a[ph-tevent="job_click"]',
                'a[data-ph-at-id="job-link"]',
                '.table--advanced-search__row',  # Added for Apple
                'tr[class*="table--advanced-search"]'  # Added for Apple
            ],
            'title_selectors': [
                '.job-title', '[class*="job-title"]', '[class*="role-title"]',
                'h1', 'h2', 'h3', 'h4', '[class*="title"]',
                '.bx--card__heading', '.bx--card__title',
                'div.job-title span',
                '[data-ph-at-job-title-text]',
                '.table--advanced-search__title',  # Added for Apple
                'a[id^="jotTitle_"]'  # Added for Apple
            ],
            'location_selectors': [
                '.location-text', '[class*="location"]', '.job-location',
                '[data-location]', '[class*="city"]', '[class*="region"]',
                '.ibm--card__copy__inner', '.bx--card__copy',
                '[data-ph-at-job-location-text]',
                '.table--advanced-search__location'  # Added for Apple
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
                'a[href*="career-search"]',
                'a[href*="careers.ibm.com/job"]',
                'a[ph-tevent="job_click"]',
                'a[href*="pgcareers.com/"]',
                'a[href^="/en-in/details/"]',  # Added for Apple
                'a[id^="jotTitle_"]'  # Added for Apple
            ],
            'next_page_selectors': [
                '.next-page', '.pagination-next', '[class*="next"]',
                'a[rel="next"]', '.next a', '.load-more-jobs',
                'ppc-content[key*="nextPaginationText"]',
                '[data-ph-at-id="pagination-next-text"]',
                '.pagination li:not(.active) a[href*="startrow="]',
                'a[href*="startrow="][rel="nofollow"]',
                '.paginationItemLast',
                'ul.pagination li:not(.active) a',
                'ul.pagination li:not(.active):nth-child(2) a',
                'ul.pagination li a[href*="startrow=10"]',
                '.pagination li:not(.active) a[title="Page 2"]',
                '.pagination-well .pagination li:not(.active) a[rel="nofollow"]',
                '.pager__item:not(.is-active) a[href*="page="]',
                'li.pager__item a[href*="page="]',
                'a[href*="page=%2C"][rel="next"]',
                'a[title="Go to next page"]',
                'a[href*="page=%2C"][title="Go to next page"]'
            ]
        }

    async def extract(self, base_url: str, max_pages: int = 2) -> List[Dict]:
        jobs = []
        try:
            page = await self.scraper.browser.new_page()
            await page.goto(base_url)
            print("\nWaiting for additional content to load...")
            
            # Wait for job content to load
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(2)  # Give extra time for dynamic content
            
            # Try multiple selectors for job containers
            for container_selector in self.selectors['containers']:
                try:
                    # Wait for any container to appear
                    await page.wait_for_selector(container_selector, timeout=5000)
                    containers = await page.query_selector_all(container_selector)
                    if containers:
                        print(f"Found containers using selector: {container_selector}")
                        break
                except:
                    continue
            
            current_page = 1
            while current_page <= max_pages:
                print(f"\nProcessing page {current_page}")
                print("Waiting for page load...")
                
                # Wait for job listings to appear
                await page.wait_for_load_state('networkidle')
                await asyncio.sleep(2)  # Additional wait for dynamic content
                
                # Extract jobs using JavaScript for better reliability
                page_jobs = await page.evaluate("""
                    () => {
                        const jobs = [];
                        // Try all provided selectors
                        const containerSelectors = %s;
                        const titleSelectors = %s;
                        const locationSelectors = %s;
                        const linkSelectors = %s;
                        
                        // Find all job containers
                        let containers = [];
                        for (const selector of containerSelectors) {
                            const elements = document.querySelectorAll(selector);
                            if (elements.length > 0) {
                                containers = elements;
                                break;
                            }
                        }
                        
                        containers.forEach(container => {
                            try {
                                // Find title
                                let title = '';
                                for (const selector of titleSelectors) {
                                    const element = container.querySelector(selector);
                                    if (element) {
                                        title = element.textContent.trim();
                                        break;
                                    }
                                }
                                
                                // Find location
                                let location = '';
                                for (const selector of locationSelectors) {
                                    const element = container.querySelector(selector);
                                    if (element) {
                                        location = element.textContent.trim();
                                        break;
                                    }
                                }
                                
                                // Find link
                                let url = '';
                                let job_id = '';
                                for (const selector of linkSelectors) {
                                    const element = container.querySelector(selector);
                                    if (element && element.href) {
                                        url = element.href;
                                        // Extract job ID from URL or element ID
                                        const urlMatch = url.match(/\\d+/);
                                        if (urlMatch) {
                                            job_id = urlMatch[0];
                                        }
                                        break;
                                    }
                                }
                                
                                if (title && (url || location)) {
                                    jobs.push({ title, location, url, job_id });
                                }
                            } catch (e) {
                                console.error('Error processing container:', e);
                            }
                        });
                        return jobs;
                    }
                """ % (json.dumps(self.selectors['containers']), 
                      json.dumps(self.selectors['title_selectors']),
                      json.dumps(self.selectors['location_selectors']),
                      json.dumps(self.selectors['link_selectors'])))
                
                # Add new jobs
                for job in page_jobs:
                    if job not in jobs:  # Avoid duplicates
                        jobs.append(job)
                        print(f"Found job: {job['title']} - {job['location']}")
                
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
            print(f"\nTotal jobs found: {len(jobs)}")
            return jobs
            
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