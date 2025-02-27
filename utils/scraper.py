import asyncio
from playwright.async_api import async_playwright, TimeoutError
from urllib.parse import urljoin, urlparse, parse_qs, urlencode
import re

class JobScraper:
    def __init__(self):
        self.job_patterns = {
            'container_patterns': [
                '.job-tile', '.jobs-list', '.job-card', 
                'div[class*="job"]', 'div[class*="career"]',
                '[data-job-id]', '[class*="job-item"]'
            ],
            'title_patterns': [
                'h2', 'h3', 'h4', '.job-title', 
                '[class*="job-title"]', '[class*="role-title"]'
            ],
            'location_patterns': [
                '.location', '[class*="location"]', 
                '[data-location]', '.job-location'
            ]
        }

    async def init_browser(self):
        """Initialize browser instance"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=False,  # Set to True in production
            args=[
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-accelerated-2d-canvas',
                '--disable-gpu',
                '--window-size=1920,1080',
            ]
        )
        return self.browser

    async def close(self):
        """Close browser and playwright instances"""
        await self.browser.close()
        await self.playwright.stop()

    async def get_page_content(self, url: str, max_retries=3):
        """Get page content using Playwright with retries"""
        context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36'
        )
        page = await context.new_page()

        for attempt in range(max_retries):
            try:
                await page.goto(url, timeout=30000)
                await self.wait_for_page_load(page)
                return page
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(5)

    async def wait_for_page_load(self, page):
        """Wait for page to load with multiple strategies"""
        try:
            print("Waiting for page load...")
            await page.wait_for_load_state("networkidle", timeout=30000)
            
            content_found = False
            for pattern in self.job_patterns['container_patterns']:
                try:
                    element = await page.wait_for_selector(pattern, timeout=5000)
                    if element:
                        content_found = True
                        print(f"Found job content with selector: {pattern}")
                        break
                except:
                    continue
            
            if not content_found:
                content = await page.content()
                if any(term in content.lower() for term in ['job', 'career', 'position']):
                    content_found = True
            
            return content_found
        except Exception as e:
            print(f"Page load check failed: {e}")
            return False 