# app/services/scheduler.py
import schedule
import asyncio
import logging
from datetime import datetime
from app.services.market_scraper import MarketScraper
from app.services.price_analyzer import PriceAnalyzer
from app.services.supabase_service import SupabaseService
from app.config import settings

logger = logging.getLogger(__name__)

class PriceScheduler:
    def __init__(self):
        self.supabase = SupabaseService()
        self.scraper = MarketScraper(self.supabase)
        self.analyzer = PriceAnalyzer(self.supabase)
        self.running = False

    async def run_full_update(self):
        """Run complete price update cycle"""
        logger.info("🔄 Starting full market price update...")
        start_time = datetime.now()
        
        try:
            # Step 1: Scrape all sources
            scraped_count = await self.scraper.scrape_all_sources()
            logger.info(f"📊 Scraped {scraped_count} new prices")
            
            # Step 2: Analyze and update vehicle values
            # Get all active variants
            variants = await self.supabase.get_all_variants()
            updated_count = 0
            
            for variant in variants:
                # Get the most recent year available
                year = datetime.now().year
                analysis = await self.analyzer.analyze_prices(variant['id'], year)
                
                if analysis and analysis.confidence_score > 0.5:
                    # Update vehicle's current market value
                    await self.supabase.update_vehicle_value(
                        variant['id'], 
                        analysis.median_price
                    )
                    updated_count += 1
            
            # Step 3: Log the update
            duration = (datetime.now() - start_time).seconds
            await self.supabase.save_scrape_log({
                'scraped_at': datetime.now().isoformat(),
                'records_updated': scraped_count,
                'vehicles_updated': updated_count,
                'duration_seconds': duration,
                'status': 'success'
            })
            
            logger.info(f"✅ Price update complete: {scraped_count} prices, {updated_count} vehicles")
            
        except Exception as e:
            logger.error(f"❌ Price update failed: {e}")
            await self.supabase.save_scrape_log({
                'scraped_at': datetime.now().isoformat(),
                'status': 'failed',
                'error': str(e)
            })

    def schedule_updates(self):
        """Schedule regular price updates"""
        # Run every 24 hours
        schedule.every(settings.SCRAPE_INTERVAL_HOURS).hours.do(
            lambda: asyncio.create_task(self.run_full_update())
        )
        
        # Run immediately on startup
        asyncio.create_task(self.run_full_update())
        
        logger.info(f"⏰ Scheduled price updates every {settings.SCRAPE_INTERVAL_HOURS} hours")

    def run(self):
        """Run the scheduler loop"""
        self.schedule_updates()
        self.running = True
        
        while self.running:
            schedule.run_pending()
            asyncio.sleep(60)
