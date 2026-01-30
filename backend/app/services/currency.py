import httpx
import logging
from typing import Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)

FALLBACK_RATES = {
    "USD": 1.0,
    "EUR": 0.92,
    "GBP": 0.79,
    "NZD": 1.67,
    "AUD": 1.53,
    "CAD": 1.36,
    "SGD": 1.34,
    "JPY": 149.5,
    "CHF": 0.88,
    "HKD": 7.82,
    "CNY": 7.24,
    "KRW": 1320.0,
    "THB": 35.5,
    "MYR": 4.47,
    "PHP": 56.2,
    "INR": 83.1,
    "IDR": 15800.0,
    "VND": 24500.0,
    "MXN": 17.1,
    "BRL": 4.97,
    "ZAR": 18.9,
    "AED": 3.67,
    "QAR": 3.64,
    "FJD": 2.25,
}


@dataclass
class ExchangeRates:
    base: str
    rates: dict[str, float]
    updated_at: datetime


class CurrencyService:
    _cache: Optional[ExchangeRates] = None
    _cache_ttl = timedelta(hours=6)
    
    @classmethod
    async def get_rates(cls, base: str = "USD") -> dict[str, float]:
        if cls._cache and cls._cache.base == base:
            if datetime.utcnow() - cls._cache.updated_at < cls._cache_ttl:
                return cls._cache.rates
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"https://api.exchangerate-api.com/v4/latest/{base}"
                )
                if response.status_code == 200:
                    data = response.json()
                    cls._cache = ExchangeRates(
                        base=base,
                        rates=data.get("rates", {}),
                        updated_at=datetime.utcnow(),
                    )
                    return cls._cache.rates
        except Exception as e:
            logger.warning(f"Failed to fetch exchange rates: {e}, using fallback")
        
        if base == "USD":
            return FALLBACK_RATES
        
        usd_to_base = FALLBACK_RATES.get(base, 1.0)
        return {k: v / usd_to_base for k, v in FALLBACK_RATES.items()}
    
    @classmethod
    async def convert(
        cls,
        amount: float,
        from_currency: str,
        to_currency: str,
    ) -> Optional[float]:
        if from_currency == to_currency:
            return amount
        
        rates = await cls.get_rates("USD")
        
        from_rate = rates.get(from_currency.upper())
        to_rate = rates.get(to_currency.upper())
        
        if not from_rate or not to_rate:
            return None
        
        usd_amount = amount / from_rate
        return round(usd_amount * to_rate, 2)
    
    @classmethod
    def convert_sync(
        cls,
        amount: float,
        from_currency: str,
        to_currency: str,
    ) -> Optional[float]:
        if from_currency == to_currency:
            return amount
        
        from_rate = FALLBACK_RATES.get(from_currency.upper())
        to_rate = FALLBACK_RATES.get(to_currency.upper())
        
        if not from_rate or not to_rate:
            return None
        
        usd_amount = amount / from_rate
        return round(usd_amount * to_rate, 2)
    
    @classmethod
    def format_price(
        cls,
        amount: float,
        currency: str,
        show_symbol: bool = True,
    ) -> str:
        symbols = {
            "USD": "$",
            "EUR": "€",
            "GBP": "£",
            "NZD": "NZ$",
            "AUD": "A$",
            "CAD": "C$",
            "JPY": "¥",
            "CNY": "¥",
            "SGD": "S$",
            "HKD": "HK$",
        }
        
        if currency in ("JPY", "KRW", "VND", "IDR"):
            formatted = f"{int(amount):,}"
        else:
            formatted = f"{amount:,.2f}"
        
        if show_symbol:
            symbol = symbols.get(currency, currency + " ")
            return f"{symbol}{formatted}"
        return formatted


def convert_deal_price(
    price: Optional[int],
    from_currency: Optional[str],
    to_currency: str,
) -> Optional[dict]:
    if not price or not from_currency:
        return None
    
    if from_currency == to_currency:
        return {
            "original": CurrencyService.format_price(price, from_currency),
            "converted": None,
            "converted_amount": price,
            "currency": to_currency,
        }
    
    converted = CurrencyService.convert_sync(price, from_currency, to_currency)
    if converted is None:
        return {
            "original": CurrencyService.format_price(price, from_currency),
            "converted": None,
            "converted_amount": None,
            "currency": from_currency,
        }
    
    return {
        "original": CurrencyService.format_price(price, from_currency),
        "converted": CurrencyService.format_price(converted, to_currency),
        "converted_amount": converted,
        "currency": to_currency,
    }
