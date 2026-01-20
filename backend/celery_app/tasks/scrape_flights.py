import asyncio
from datetime import date, timedelta
from celery import shared_task
from celery.utils.log import get_task_logger
from app.database import SessionLocal
from app.models import Route, FlightPrice
from app.scrapers.google_flights import GoogleFlightsScraper, ScraperError
from app.services.price_analyzer import PriceAnalyzer
from app.services.notification import NtfyNotifier

logger = get_task_logger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def scrape_route_prices(self, route_id: int):
    db = SessionLocal()
    
    try:
        route = db.query(Route).filter(Route.id == route_id).first()
        if not route:
            logger.error(f"Route {route_id} not found")
            return
        
        logger.info(f"Scraping route: {route.name}")
        
        departure_dates = [
            date.today() + timedelta(weeks=w)
            for w in [4, 8, 12, 16]
        ]
        
        scraper = GoogleFlightsScraper()
        analyzer = PriceAnalyzer(db)
        notifier = NtfyNotifier()
        
        async def run_scrape():
            for dep_date in departure_dates:
                return_date = dep_date + timedelta(days=7)
                
                try:
                    results = await scraper.scrape_route(
                        origin=route.origin,
                        destination=route.destination,
                        departure_date=dep_date,
                        return_date=return_date,
                        passengers=4
                    )
                    
                    if not results:
                        logger.warning(f"No results for {route.name} on {dep_date}")
                        continue
                    
                    best_price = min(results, key=lambda r: r.price_nzd)
                    
                    flight_price = FlightPrice(
                        route_id=route.id,
                        departure_date=dep_date,
                        return_date=return_date,
                        price_nzd=best_price.price_nzd,
                        airline=best_price.airline,
                        stops=best_price.stops,
                        passengers=4,
                        raw_data=best_price.raw_data
                    )
                    db.add(flight_price)
                    db.commit()
                    
                    deal = analyzer.analyze_price(flight_price)
                    
                    if deal.is_deal:
                        logger.info(f"Deal found for {route.name}: ${best_price.price_nzd}")
                        await notifier.send_deal_alert(
                            route_name=route.name,
                            departure_date=str(dep_date),
                            return_date=str(return_date),
                            price_nzd=best_price.price_nzd,
                            deal=deal,
                            airline=best_price.airline
                        )
                    
                except ScraperError as e:
                    logger.error(f"Scraper error for {route.name}: {e}")
                    continue
            
            await scraper.close()
        
        asyncio.run(run_scrape())
        logger.info(f"Completed scraping for {route.name}")
        
    except Exception as e:
        logger.exception(f"Failed to scrape route {route_id}")
        raise self.retry(exc=e)
    
    finally:
        db.close()


@shared_task
def scrape_all_routes():
    db = SessionLocal()
    
    try:
        routes = db.query(Route).filter(Route.is_active == True).all()
        logger.info(f"Starting scrape for {len(routes)} active routes")
        
        for route in routes:
            scrape_route_prices.delay(route.id)
        
    finally:
        db.close()
