import pandas as pd
import os
from datetime import datetime
from typing import List, Dict
import csv

class ExcelGenerator:
    def __init__(self):
        self.output_dir = 'output'
        os.makedirs(self.output_dir, exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create both CSV and Excel files
        self.csv_file = f'{self.output_dir}/all_jobs_{self.timestamp}.csv'
        self.excel_file = f'{self.output_dir}/all_jobs_{self.timestamp}.xlsx'
        
        # Initialize CSV with headers
        self.headers = ['company', 'title', 'location', 'url', 'job_id', 'timestamp', 'source']
        with open(self.csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.headers)
            writer.writeheader()

    def append_jobs(self, jobs: List[Dict], company: str):
        """
        Append jobs to both CSV and Excel files
        
        Args:
            jobs: List of job dictionaries
            company: Company name
        """
        try:
            # Append to CSV
            with open(self.csv_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.headers)
                for job in jobs:
                    job_data = {
                        'company': company,
                        'title': job.get('title', ''),
                        'location': job.get('location', ''),
                        'url': job.get('url', ''),
                        'job_id': job.get('job_id', ''),
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'source': job.get('source', company)
                    }
                    writer.writerow(job_data)

            # Convert CSV to Excel
            df = pd.read_csv(self.csv_file)
            df.to_excel(self.excel_file, index=False, engine='openpyxl')
            
            print(f"Added {len(jobs)} jobs from {company}")
            print(f"Updated files: \n- {self.csv_file}\n- {self.excel_file}")
            
        except Exception as e:
            print(f"Error appending jobs for {company}: {e}")

    def get_file_paths(self):
        """Return paths to the generated files"""
        return {
            'csv': self.csv_file,
            'excel': self.excel_file
        } 