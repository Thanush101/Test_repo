import asyncio
import json
import os
from datetime import datetime
from utils.scraper import JobScraper
from utils.excel_generator import ExcelGenerator
from urllib.parse import urlencode
from extractors.base_extractor import BaseExtractor

async def main():
    # Load company configurations
    with open('company_mappings.json', 'r') as f:
        company_mappings = json.load(f)
    
    # Initialize scraper and excel generator
    scraper = JobScraper()
    await scraper.init_browser()
    excel_gen = ExcelGenerator()
    
    try:
        # Scrape each company
        for company, config in company_mappings.items():
            try:
                print(f"Scraping {company}...")
                
                # Build URL with query parameters
                base_url = config['base_url']
                if 'params' in config and 'query' in config['params']:
                    query_string = urlencode(config['params']['query'])
                    full_url = f"{base_url}?{query_string}"
                else:
                    full_url = base_url
                
                # Get max pages from config or use default
                max_pages = config.get('params', {}).get('max_pages', 2)
                
                # Initialize extractor
                try:
                    module_path, class_name = config['extractor'].split('.')
                    extractor_module = __import__(f"extractors.{module_path}", fromlist=[class_name])
                    extractor_class = getattr(extractor_module, class_name)
                    extractor = extractor_class(scraper)
                except (KeyError, ImportError, AttributeError):
                    print(f"No specific extractor found for {company}, using base extractor")
                    extractor = BaseExtractor(scraper)
                
                print(f"Scraping URL: {full_url}")
                print(f"Max pages to scrape: {max_pages}")
                
                # Extract jobs with configured parameters
                jobs = await extractor.extract(full_url, max_pages=max_pages)
                excel_gen.append_jobs(jobs, company)
                        
            except Exception as e:
                print(f"Error processing {company}: {str(e)}")
                continue
    
    finally:
        await scraper.close()

if __name__ == "__main__":
    asyncio.run(main()) 