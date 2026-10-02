"""
Social Listening Enrichment Service

Applies NLP-style enrichment to social listening data during ETL Transform:
- Event type classification for Market_Signal rows
- Severity scoring based on content signals
- Sentiment scoring for Brand_Sentiment rows
- Entity extraction (location, commodity) validation and normalization
"""

import os
import json
import time
from typing import Any, Dict, List, Optional

from loguru import logger

enrich_logger = logger.bind(component="social-listening-enrichment")

VALID_EVENT_TYPES = [
    "Supply_Disruption", "Regulatory_Change", "Weather_Event",
    "Port_Congestion", "Labor_Strike", "Demand_Spike", "Competitor_Action",
]

VALID_SEVERITIES = ["Critical", "High", "Medium", "Low"]

VALID_COMMODITIES = [
    "Sugar", "Aluminum", "PET_Resin", "Glass", "CO2", "Concentrate",
    "High_Fructose_Corn_Syrup",
]

VALID_LOCATIONS = [
    "Singapore", "Malaysia", "Thailand", "Indonesia", "Philippines",
    "Vietnam", "Myanmar", "Cambodia", "Laos", "India", "China", "Japan",
    "South_Korea", "Taiwan", "Australia", "Global",
]

SENTIMENT_TOPICS = [
    "Taste", "Packaging", "Price", "Availability",
    "Sustainability", "Health", "Quality", "Brand_Image",
]


class SocialListeningEnrichmentService:

    def __init__(self):
        self._llm_available = False
        self._api_key = os.getenv("OPENAI_API_KEY", "")
        if not self._api_key:
            try:
                from src.config.config_provider import get_config
                self._api_key = get_config().openai_api_key or ""
            except Exception:
                pass
        self._llm_available = bool(self._api_key)

    def enrich_batch(self, rows: List[Dict]) -> List[Dict]:
        result = []
        for row in rows:
            source_table = row.get('_source_table', '')
            if source_table == 'Market_Signal':
                result.append(self._enrich_market_signal(row))
            elif source_table == 'Brand_Sentiment':
                result.append(self._enrich_brand_sentiment(row))
            elif source_table == 'Commodity_Price':
                result.append(self._enrich_commodity_price(row))
            else:
                result.append(row)
        return result

    def _enrich_market_signal(self, row: Dict) -> Dict:
        enriched = dict(row)
        changed = False

        event_type = enriched.get('Event_Type', '')
        if event_type and event_type not in VALID_EVENT_TYPES:
            best = self._fuzzy_match(event_type, VALID_EVENT_TYPES)
            if best:
                enriched['Event_Type'] = best
                changed = True

        severity = enriched.get('Severity', '')
        if severity and severity not in VALID_SEVERITIES:
            best = self._fuzzy_match(severity, VALID_SEVERITIES)
            if best:
                enriched['Severity'] = best
                changed = True

        if not enriched.get('Severity') and enriched.get('Event_Type'):
            enriched['Severity'] = self._infer_severity(enriched['Event_Type'])
            changed = True

        commodity = enriched.get('Affected_Commodity', '')
        if commodity and commodity not in VALID_COMMODITIES:
            best = self._fuzzy_match(commodity, VALID_COMMODITIES)
            if best:
                enriched['Affected_Commodity'] = best
                changed = True

        location = enriched.get('Location', '')
        if location and location not in VALID_LOCATIONS:
            best = self._fuzzy_match(location, VALID_LOCATIONS)
            if best:
                enriched['Location'] = best
                changed = True

        if self._llm_available and not enriched.get('Event_Type'):
            llm_fields = self._llm_classify_signal(enriched)
            if llm_fields:
                enriched.update(llm_fields)
                changed = True

        if changed:
            enriched['_enriched'] = True
        return enriched

    def _enrich_brand_sentiment(self, row: Dict) -> Dict:
        enriched = dict(row)
        changed = False

        score = enriched.get('Sentiment_Score')
        if score is not None:
            try:
                score = float(score)
                score = max(-1.0, min(1.0, score))
                enriched['Sentiment_Score'] = round(score, 3)
                if 'Sentiment_Label' not in enriched:
                    if score > 0.3:
                        enriched['Sentiment_Label'] = 'Positive'
                    elif score < -0.3:
                        enriched['Sentiment_Label'] = 'Negative'
                    else:
                        enriched['Sentiment_Label'] = 'Neutral'
                    changed = True
            except (ValueError, TypeError):
                pass

        topic = enriched.get('Topic', '')
        if topic and topic not in SENTIMENT_TOPICS:
            best = self._fuzzy_match(topic, SENTIMENT_TOPICS)
            if best:
                enriched['Topic'] = best
                changed = True

        if changed:
            enriched['_enriched'] = True
        return enriched

    def _enrich_commodity_price(self, row: Dict) -> Dict:
        enriched = dict(row)
        changed = False

        commodity = enriched.get('Commodity', '')
        if commodity and commodity not in VALID_COMMODITIES:
            best = self._fuzzy_match(commodity, VALID_COMMODITIES)
            if best:
                enriched['Commodity'] = best
                changed = True

        change_pct = enriched.get('Change_Pct_30D')
        if change_pct is not None and 'Price_Trend' not in enriched:
            try:
                pct = float(change_pct)
                if pct > 5:
                    enriched['Price_Trend'] = 'Rising_Sharply'
                elif pct > 0:
                    enriched['Price_Trend'] = 'Rising'
                elif pct > -5:
                    enriched['Price_Trend'] = 'Falling'
                else:
                    enriched['Price_Trend'] = 'Falling_Sharply'
                changed = True
            except (ValueError, TypeError):
                pass

        if changed:
            enriched['_enriched'] = True
        return enriched

    @staticmethod
    def _fuzzy_match(value: str, candidates: List[str]) -> Optional[str]:
        normalized = value.lower().replace(' ', '_').replace('-', '_')
        for c in candidates:
            if c.lower() == normalized:
                return c
        for c in candidates:
            if normalized in c.lower() or c.lower() in normalized:
                return c
        return None

    @staticmethod
    def _infer_severity(event_type: str) -> str:
        high_severity = {"Supply_Disruption", "Labor_Strike", "Port_Congestion"}
        medium_severity = {"Weather_Event", "Demand_Spike", "Competitor_Action"}
        if event_type in high_severity:
            return "High"
        if event_type in medium_severity:
            return "Medium"
        return "Low"

    def _llm_classify_signal(self, row: Dict) -> Optional[Dict]:
        if not self._llm_available:
            return None

        try:
            import openai
            client = openai.OpenAI(api_key=self._api_key, timeout=30.0)
        except ImportError:
            return None

        row_text = json.dumps({k: v for k, v in row.items() if not k.startswith('_')}, default=str)
        prompt = (
            "Classify this market signal. Return ONLY a JSON object with these fields:\n"
            f"- Event_Type: one of {VALID_EVENT_TYPES}\n"
            f"- Severity: one of {VALID_SEVERITIES}\n"
            f"- Affected_Commodity: one of {VALID_COMMODITIES} or empty\n"
            f"- Location: one of {VALID_LOCATIONS} or empty\n\n"
            "Signal data:\n" + row_text[:2000]
        )

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=200,
            )
            content = response.choices[0].message.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            fields = json.loads(content)
            return {k: v for k, v in fields.items() if v}
        except Exception as e:
            enrich_logger.warning(f"LLM classification failed: {e}")
            return None
