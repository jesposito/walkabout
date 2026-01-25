import logging
from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from app.models.deal import Deal
from app.models.route_market_price import RouteMarketPrice
from app.services.flight_price_fetcher import FlightPriceFetcher, FetchResult

logger = logging.getLogger(__name__)


RATING_THRESHOLDS = {
    "hot": 30,
    "good": 15,
    "decent": 5,
}

RATING_LABELS = {
    "hot": "🔥 Hot Deal",
    "good": "✨ Good Deal",
    "decent": "👍 Decent",
    "normal": "Normal",
    "above": "⚠️ Above Market",
}

MARKET_PRICE_MAX_AGE_DAYS = 7


def calculate_rating(deal_price: float, market_price: float) -> Tuple[float, str]:
    if market_price <= 0:
        return 0.0, RATING_LABELS["normal"]
    
    savings_percent = ((market_price - deal_price) / market_price) * 100
    
    if savings_percent >= RATING_THRESHOLDS["hot"]:
        return savings_percent, RATING_LABELS["hot"]
    elif savings_percent >= RATING_THRESHOLDS["good"]:
        return savings_percent, RATING_LABELS["good"]
    elif savings_percent >= RATING_THRESHOLDS["decent"]:
        return savings_percent, RATING_LABELS["decent"]
    elif savings_percent >= 0:
        return savings_percent, RATING_LABELS["normal"]
    else:
        return savings_percent, RATING_LABELS["above"]


def get_cached_market_price(
    db: Session,
    origin: str,
    destination: str,
    cabin_class: str = "economy",
    travel_month: Optional[int] = None,
) -> Optional[RouteMarketPrice]:
    if travel_month is None:
        travel_month = datetime.now().month
    
    cutoff = datetime.utcnow() - timedelta(days=MARKET_PRICE_MAX_AGE_DAYS)
    
    return db.query(RouteMarketPrice).filter(
        RouteMarketPrice.origin == origin.upper(),
        RouteMarketPrice.destination == destination.upper(),
        RouteMarketPrice.cabin_class == cabin_class,
        RouteMarketPrice.month == travel_month,
        RouteMarketPrice.checked_at >= cutoff,
    ).order_by(RouteMarketPrice.checked_at.desc()).first()


def save_market_price(
    db: Session,
    origin: str,
    destination: str,
    price: float,
    currency: str,
    source: str,
    cabin_class: str = "economy",
    travel_month: Optional[int] = None,
) -> RouteMarketPrice:
    if travel_month is None:
        travel_month = datetime.now().month
    
    existing = db.query(RouteMarketPrice).filter(
        RouteMarketPrice.origin == origin.upper(),
        RouteMarketPrice.destination == destination.upper(),
        RouteMarketPrice.cabin_class == cabin_class,
        RouteMarketPrice.month == travel_month,
    ).first()
    
    if existing:
        new_count = existing.sample_count + 1
        new_avg = ((existing.market_price * existing.sample_count) + price) / new_count
        existing.market_price = new_avg
        existing.sample_count = new_count
        existing.min_price = min(existing.min_price or price, price)
        existing.max_price = max(existing.max_price or price, price)
        existing.checked_at = datetime.utcnow()
        existing.source = source
        db.commit()
        return existing
    
    market_price = RouteMarketPrice(
        origin=origin.upper(),
        destination=destination.upper(),
        cabin_class=cabin_class,
        market_price=price,
        currency=currency,
        source=source,
        month=travel_month,
        sample_count=1,
        min_price=price,
        max_price=price,
    )
    db.add(market_price)
    db.commit()
    return market_price


async def fetch_market_price(
    origin: str,
    destination: str,
    cabin_class: str = "economy",
    currency: str = "NZD",
    travel_date: Optional[date] = None,
) -> Optional[FetchResult]:
    fetcher = FlightPriceFetcher()
    
    if not fetcher.get_available_sources():
        logger.warning("No price sources available for market price fetch")
        return None
    
    if travel_date is None:
        travel_date = date.today() + timedelta(days=60)
    
    return_date = travel_date + timedelta(days=7)
    
    result = await fetcher.fetch_prices(
        origin=origin,
        destination=destination,
        departure_date=travel_date,
        return_date=return_date,
        adults=2,
        children=0,
        cabin_class=cabin_class,
        currency=currency,
        include_ai_analysis=False,
    )
    
    return result


async def rate_deal(db: Session, deal: Deal) -> bool:
    if not deal.parsed_origin or not deal.parsed_destination:
        logger.debug(f"Deal {deal.id} missing origin/destination, skipping rating")
        return False
    
    if not deal.parsed_price:
        logger.debug(f"Deal {deal.id} missing price, skipping rating")
        return False
    
    cabin_class = deal.parsed_cabin_class or "economy"
    travel_month = None
    
    cached = get_cached_market_price(
        db,
        deal.parsed_origin,
        deal.parsed_destination,
        cabin_class,
        travel_month,
    )
    
    if cached:
        logger.info(f"Using cached market price for {deal.parsed_origin}-{deal.parsed_destination}: {cached.market_price}")
        market_price = cached.market_price
        source = cached.source
        currency = cached.currency
    else:
        logger.info(f"Fetching market price for {deal.parsed_origin}-{deal.parsed_destination}")
        result = await fetch_market_price(
            deal.parsed_origin,
            deal.parsed_destination,
            cabin_class,
            deal.parsed_currency or "NZD",
        )
        
        if not result or not result.success or not result.prices:
            logger.warning(f"Failed to fetch market price for deal {deal.id}")
            return False
        
        prices = [float(p.price) for p in result.prices]
        market_price = sum(prices) / len(prices)
        currency = deal.parsed_currency or "NZD"
        source = result.source
        
        save_market_price(
            db,
            deal.parsed_origin,
            deal.parsed_destination,
            market_price,
            currency,
            source,
            cabin_class,
            travel_month,
        )
    
    rating, label = calculate_rating(deal.parsed_price, market_price)
    
    deal.market_price = market_price
    deal.market_currency = currency
    deal.deal_rating = rating
    deal.rating_label = label
    deal.market_price_source = source
    deal.market_price_checked_at = datetime.utcnow()
    
    db.commit()
    
    logger.info(f"Rated deal {deal.id}: {rating:.1f}% ({label}) - deal ${deal.parsed_price} vs market ${market_price:.0f}")
    return True


async def rate_unrated_deals(db: Session, limit: int = 10) -> int:
    unrated_deals = db.query(Deal).filter(
        Deal.parsed_origin.isnot(None),
        Deal.parsed_destination.isnot(None),
        Deal.parsed_price.isnot(None),
        Deal.deal_rating.is_(None),
    ).order_by(Deal.created_at.desc()).limit(limit).all()
    
    rated_count = 0
    for deal in unrated_deals:
        try:
            if await rate_deal(db, deal):
                rated_count += 1
        except Exception as e:
            logger.error(f"Error rating deal {deal.id}: {e}")
    
    return rated_count
