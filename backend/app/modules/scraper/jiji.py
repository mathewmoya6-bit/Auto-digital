# app/modules/scraper/base_scraper.py
# Add these methods if they don't exist

import re
from typing import Optional

class BaseScraper:
    # ... existing code ...

    def _parse_year(self, text: str) -> Optional[int]:
        """
        Parse year from text.
        Looks for 4-digit numbers between 1950 and 2030.
        """
        if not text:
            return None
        
        # Look for year patterns
        patterns = [
            r'\b(19[5-9]\d|20[0-3]\d)\b',  # 1950-2030
            r'\b(19[5-9]\d|20[0-3]\d)\s*[kKmM]m\b',  # Year followed by km
            r'\b(19[5-9]\d|20[0-3]\d)\s*[Kk][Mm]\b',  # Year followed by KM
            r'[Yy]ear\s*[:.]?\s*(19[5-9]\d|20[0-3]\d)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                year_str = match.group(1) if match.groups() else match.group(0)
                try:
                    year = int(year_str)
                    if 1950 <= year <= 2030:
                        return year
                except ValueError:
                    pass
        
        return None

    def _parse_mileage(self, text: str) -> Optional[int]:
        """
        Parse mileage from text.
        Looks for numbers followed by km, KM, or kilometers.
        """
        if not text:
            return None
        
        patterns = [
            r'(\d{1,3}(?:,\d{3})*)\s*[Kk][Mm]\b',
            r'(\d{1,3}(?:,\d{3})*)\s*[Kk]m\b',
            r'(\d{1,3}(?:,\d{3})*)\s*[Kk]ilometers?\b',
            r'[Mm]ileage\s*[:.]?\s*(\d{1,3}(?:,\d{3})*)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                mileage_str = match.group(1).replace(',', '')
                try:
                    return int(mileage_str)
                except ValueError:
                    pass
        
        return None

    def _parse_engine_size(self, text: str) -> Optional[float]:
        """
        Parse engine size from text.
        Looks for numbers like 1.4, 2.0, 3.0 followed by L or liter.
        """
        if not text:
            return None
        
        patterns = [
            r'(\d+\.?\d*)\s*[Ll](?:\s*[Ii]t?e?r?)?\b',
            r'[Ee]ngine\s*[:.]?\s*(\d+\.?\d*)\s*[Ll]',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    pass
        
        return None

    def _parse_price(self, text: str) -> Optional[float]:
        """
        Parse price from text.
        Looks for KES, KSh, or numeric patterns.
        """
        if not text:
            return None
        
        patterns = [
            r'[Kk][Ee][Ss]\s*([\d,]+)',
            r'[Kk][Ss][Hh]\s*([\d,]+)',
            r'[Kk][Ee][Nn]\s*([\d,]+)',
            r'[Kk][Ee]\s*([\d,]+)',
            r'([\d,]+)\s*[Kk][Ss][Hh]',
            r'([\d,]+)\s*[Kk][Ee][Ss]',
            r'(?:Price|P\s*[:.]?\s*)([\d,]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                price_str = match.group(1).replace(',', '')
                try:
                    return float(price_str)
                except ValueError:
                    pass
        
        # Try to find any large number with commas
        match = re.search(r'([\d,]{4,})', text)
        if match:
            price_str = match.group(1).replace(',', '')
            try:
                price = float(price_str)
                if price > 1000:  # Likely a real price
                    return price
            except ValueError:
                pass
        
        return None
