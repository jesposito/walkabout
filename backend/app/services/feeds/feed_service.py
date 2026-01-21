from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
import logging

from app.models.deal import Deal, DealSource, ParseStatus
from app.models.feed_health import FeedHealth
from app.services.feeds.base import BaseFeedParser, ParsedDeal
from app.services.feeds.secret_flying import SecretFlyingParser
from app.services.feeds.omaat import OMAATParser
from app.services.feeds.ai_extractor import AIExtractor, AIInsightsEngine
from app.config import get_settings

logger = logging.getLogger(__name__)


class FeedService:
    
    PARSERS: dict[DealSource, type[BaseFeedParser]] = {
        DealSource.SECRET_FLYING: SecretFlyingParser,
        DealSource.OMAAT: OMAATParser,
    }
    
    def __init__(self, db: Session):
        self.db = db
        self.ai_extractor = AIExtractor()
        self.ai_insights = AIInsightsEngine()
        self.settings = get_settings()
    
    async def ingest_all_feeds(self) -> dict[str, dict]:
        results = {}
        for source in self.PARSERS:
            try:
                result = await self.ingest_feed(source)
                results[source.value] = result
            except Exception as e:
                logger.error(f"Failed to ingest {source.value}: {e}")
                results[source.value] = {"error": str(e), "fetched": 0, "new": 0}
                self._record_failure(source, str(e))
        return results
    
    async def ingest_feed(self, source: DealSource) -> dict:
        parser_class = self.PARSERS.get(source)
        if not parser_class:
            raise ValueError(f"No parser for source: {source}")
        
        parser = parser_class()
        
        try:
            deals = await parser.fetch_feed()
            
            ai_enhanced = 0
            for deal in deals:
                if self.ai_extractor.should_use_ai(deal.result):
                    enhanced_result = await self.ai_extractor.extract(deal)
                    if enhanced_result.confidence > deal.result.confidence:
                        deal.result = enhanced_result
                        ai_enhanced += 1
            
            new_count = self._store_deals(deals)
            
            self._record_success(source, len(deals), new_count)
            
            return {
                "fetched": len(deals),
                "new": new_count,
                "ai_enhanced": ai_enhanced,
                "source": source.value,
            }
            
        except Exception as e:
            self._record_failure(source, str(e))
            raise
    
    def _store_deals(self, parsed_deals: list[ParsedDeal]) -> int:
        new_count = 0
        
        for parsed in parsed_deals:
            existing = self.db.query(Deal).filter(
                Deal.source == parsed.source,
                Deal.link == parsed.link
            ).first()
            
            if existing:
                continue
            
            result = parsed.result
            
            deal = Deal(
                source=parsed.source,
                guid=parsed.guid,
                link=parsed.link,
                published_at=parsed.published_at,
                raw_title=parsed.raw_title,
                raw_summary=parsed.raw_summary,
                raw_content_html=parsed.raw_content_html,
                parsed_origin=result.origin,
                parsed_destination=result.destination,
                parsed_price=result.price,
                parsed_currency=result.currency,
                parsed_travel_dates=result.travel_dates,
                parsed_airline=result.airline,
                parsed_cabin_class=result.cabin_class,
                parse_status=result.status,
                parse_error="; ".join(result.reasons) if result.reasons else None,
                fetched_at=datetime.utcnow(),
            )
            
            self.db.add(deal)
            new_count += 1
        
        self.db.commit()
        return new_count
    
    def _get_or_create_health(self, source: DealSource) -> FeedHealth:
        health = self.db.query(FeedHealth).filter(FeedHealth.source == source).first()
        if not health:
            health = FeedHealth(source=source)
            self.db.add(health)
            self.db.commit()
            self.db.refresh(health)
        return health
    
    def _record_success(self, source: DealSource, fetched: int, new: int):
        health = self._get_or_create_health(source)
        health.last_fetch_at = datetime.utcnow()
        health.last_success_at = datetime.utcnow()
        health.consecutive_failures = 0
        health.total_items_fetched += fetched
        health.total_items_new += new
        self.db.commit()
    
    def _record_failure(self, source: DealSource, error: str):
        health = self._get_or_create_health(source)
        health.last_fetch_at = datetime.utcnow()
        health.last_error_at = datetime.utcnow()
        health.last_error = error
        health.consecutive_failures += 1
        self.db.commit()
        
        if health.consecutive_failures >= 3:
            logger.warning(f"Feed {source.value} has {health.consecutive_failures} consecutive failures")
    
    def get_feed_health(self) -> list[dict]:
        healths = self.db.query(FeedHealth).all()
        return [
            {
                "source": h.source.value,
                "last_success": h.last_success_at.isoformat() if h.last_success_at else None,
                "consecutive_failures": h.consecutive_failures,
                "total_fetched": h.total_items_fetched,
                "total_new": h.total_items_new,
                "last_error": h.last_error if h.consecutive_failures > 0 else None,
            }
            for h in healths
        ]
    
    def get_deals(
        self,
        origin: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Deal]:
        query = self.db.query(Deal).order_by(Deal.published_at.desc())
        
        if origin:
            query = query.filter(Deal.parsed_origin == origin.upper())
        
        return query.offset(offset).limit(limit).all()
    
    def get_deals_for_home(self, home_airport: str, limit: int = 50) -> list[Deal]:
        return self.db.query(Deal).filter(
            Deal.parsed_origin == home_airport.upper()
        ).order_by(Deal.published_at.desc()).limit(limit).all()
    
    async def get_insights(
        self,
        home_airport: str,
        watched_destinations: list[str],
        days: int = 30,
    ) -> dict:
        deals = self.db.query(Deal).filter(
            Deal.parsed_origin == home_airport.upper()
        ).order_by(Deal.published_at.desc()).limit(100).all()
        
        deals_data = [
            {
                "origin": d.parsed_origin,
                "destination": d.parsed_destination,
                "price": d.parsed_price,
                "currency": d.parsed_currency,
                "cabin_class": d.parsed_cabin_class,
                "airline": d.parsed_airline,
                "published_at": d.published_at.isoformat() if d.published_at else None,
            }
            for d in deals
        ]
        
        return await self.ai_insights.generate_insights(
            deals_data,
            home_airport,
            watched_destinations,
            days,
        )
