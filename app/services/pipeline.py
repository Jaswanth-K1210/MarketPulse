"""
Processing Pipeline
7-stage deterministic pipeline for generating alerts from articles
"""

import logging
from typing import Optional, Dict, List
from datetime import datetime
from app.models.article import Article
from app.models.alert import Alert, AffectedHolding
from app.models.knowledge_graph import KnowledgeGraph
from app.services.gemini_client import gemini_client
from app.services.database import get_db_connection
from app.services import persistence  # For database operations
database = persistence.persistence_service  # Database service singleton
from app.services.market_data import market_data_service
from app.config import (
    SUPPLY_CHAIN_COMPANIES,
    SEVERITY_THRESHOLDS, MIN_CONFIDENCE, COMPANY_TICKERS
)

logger = logging.getLogger(__name__)


class Pipeline:
    """7-stage processing pipeline"""

    def __init__(self):
        """Initialize pipeline"""
        logger.info("Processing Pipeline initialized")

    def _get_portfolio(self) -> Dict:
        """Get portfolio data from database"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT ticker, company_name, quantity, avg_price, current_price FROM holdings")
            rows = cursor.fetchall()
            conn.close()
            
            portfolio = []
            for row in rows:
                portfolio.append({
                    "ticker": row[0],
                    "company_name": row[1],
                    "quantity": row[2],
                    "avg_price": row[3],
                    "current_price": row[4]
                })
            
            return {"portfolio": portfolio}
        except Exception as e:
            logger.error(f"Error getting portfolio: {e}")
            return {"portfolio": []}


    # ═══════════════════════════════════════════════════════════════════
    # STAGE 1: EVENT VALIDATOR
    # ═══════════════════════════════════════════════════════════════════

    def event_validator(self, article: Article) -> Optional[Article]:
        """
        Validate article is relevant and complete

        Args:
            article: Article to validate

        Returns:
            Validated article or None
        """
        try:
            # Check if article has required fields
            if not article.title or not article.content:
                logger.warning(f"Article missing required fields: {article.url}")
                return None

            # Check if article is too old (>7 days)
            age_days = (datetime.now() - article.published_at).days
            if age_days > 7:
                logger.info(f"Article too old ({age_days} days): {article.title}")
                return None

            # Note: We don't check companies_mentioned here because 
            # the relation_extractor will identify relevant companies
            
            logger.info(f"✓ Article validated: {article.title}")
            return article

        except Exception as e:
            logger.error(f"Error in event_validator: {str(e)}")
            return None


    # ═══════════════════════════════════════════════════════════════════
    # STAGE 2: RELATION EXTRACTOR
    # ═══════════════════════════════════════════════════════════════════

    def relation_extractor(self, article: Article) -> Optional[Dict]:
        """
        Extract company relationships using Gemini

        Args:
            article: Validated article

        Returns:
            Dict with relationships or None
        """
        try:
            logger.info(f"Extracting relationships from: {article.title}")

            result = gemini_client.extract_relationships(
                article.content,
                article.title
            )

            if not result or not result.get('relationships'):
                logger.info("No relationships found")
                return None

            # Update article with event type
            if result.get('event_type'):
                article.event_type = result['event_type']

            logger.info(f"✓ Extracted {len(result['relationships'])} relationships")
            return result

        except Exception as e:
            logger.error(f"Error in relation_extractor: {str(e)}")
            return None

    # ═══════════════════════════════════════════════════════════════════
    # STAGE 3: RELATION VERIFIER
    # ═══════════════════════════════════════════════════════════════════

    def relation_verifier(self, relationships: List[Dict]) -> List[Dict]:
        """
        Verify relationships meet confidence threshold

        Args:
            relationships: List of extracted relationships

        Returns:
            List of verified relationships
        """
        try:
            verified = []
            for rel in relationships:
                confidence = rel.get('confidence', 0.0)
                if confidence >= MIN_CONFIDENCE:
                    verified.append(rel)
                    logger.info(
                        f"✓ Verified: {rel['from_company']} -> {rel['to_company']} "
                        f"(confidence: {confidence})"
                    )
                else:
                    logger.info(
                        f"✗ Rejected: {rel['from_company']} -> {rel['to_company']} "
                        f"(confidence too low: {confidence})"
                    )

            return verified

        except Exception as e:
            logger.error(f"Error in relation_verifier: {str(e)}")
            return []

    # ═══════════════════════════════════════════════════════════════════
    # STAGE 4: CASCADE INFERENCER
    # ═══════════════════════════════════════════════════════════════════

    def cascade_inferencer(
        self,
        event_summary: str,
        relationships: List[Dict]
    ) -> Optional[Dict]:
        """
        Infer cascade effects on portfolio

        Args:
            event_summary: Event summary
            relationships: Verified relationships

        Returns:
            Dict with cascade chain or None
        """
        try:
            logger.info("Inferring cascade effects...")

            # Get portfolio from database
            portfolio_data = self._get_portfolio()
            portfolio_companies = [h["ticker"] for h in portfolio_data.get("portfolio", [])]

            result = gemini_client.infer_cascade(
                event_summary,
                relationships,
                portfolio_companies
            )

            if not result:
                logger.info("No cascade inference generated - creating informational alert")
                # Create default informational cascade
                result = {
                    "cascade_chain": [],
                    "affected_portfolio_companies": [],
                    "severity": "info",
                    "estimated_impact_percent": 0.0,
                    "reasoning": "News detected but no direct portfolio impact at this time."
                }

            affected = result.get('affected_portfolio_companies', [])
            logger.info(f"✓ Cascade affects {len(affected)} portfolio companies: {affected}")

            return result

        except Exception as e:
            logger.error(f"Error in cascade_inferencer: {str(e)}")
            return None

    # ═══════════════════════════════════════════════════════════════════
    # STAGE 5: IMPACT SCORER
    # ═══════════════════════════════════════════════════════════════════

    def impact_scorer(
        self,
        cascade_result: Dict,
        portfolio_data: Dict
    ) -> Optional[Dict]:
        """
        Calculate impact on portfolio

        Args:
            cascade_result: Cascade inference result
            portfolio_data: Portfolio holdings

        Returns:
            Dict with impact scores or None
        """
        try:
            logger.info("Calculating portfolio impact...")

            affected_companies = cascade_result.get('affected_portfolio_companies', [])
            estimated_impact_pct = cascade_result.get('estimated_impact_percent', 0.0)

            if not affected_companies:
                logger.info("No portfolio companies affected")
                return None

            # Get current portfolio value
            holdings = portfolio_data.get('portfolio', [])
            portfolio_value_data = market_data_service.get_portfolio_value(holdings)

            if not portfolio_value_data:
                logger.error("Could not get portfolio value")
                return None

            total_portfolio_value = portfolio_value_data['total_value']

            # Calculate impact for each holding
            affected_holdings = []
            total_impact_dollar = 0

            for holding_data in portfolio_value_data['holdings']:
                company_name = holding_data['company_name']
                ticker = holding_data['ticker']

                # Check if this holding is affected
                is_affected = False
                for affected_company in affected_companies:
                    if (affected_company in company_name or
                        affected_company == ticker or
                        affected_company == ticker):
                        is_affected = True
                        break

                if is_affected:
                    # Calculate impact on this holding
                    holding_value = holding_data['current_value']
                    impact_dollar = holding_value * (estimated_impact_pct / 100)

                    affected_holding = {
                        "company": company_name,
                        "ticker": ticker,
                        "quantity": holding_data['quantity'],
                        "impact_percent": round(estimated_impact_pct, 2),
                        "impact_dollar": round(impact_dollar, 2),
                        "current_price": holding_data['current_price']
                    }

                    affected_holdings.append(affected_holding)
                    total_impact_dollar += impact_dollar

                    logger.info(
                        f"Impact on {company_name}: {estimated_impact_pct}% "
                        f"(${impact_dollar:.2f})"
                    )

            # Calculate total portfolio impact percentage
            total_impact_pct = (total_impact_dollar / total_portfolio_value) * 100 if total_portfolio_value > 0 else 0

            # Determine severity
            abs_impact = abs(total_impact_pct)
            if abs_impact >= SEVERITY_THRESHOLDS['high']:
                severity = 'high'
            elif abs_impact >= SEVERITY_THRESHOLDS['medium']:
                severity = 'medium'
            else:
                severity = 'low'

            result = {
                "affected_holdings": affected_holdings,
                "total_impact_dollar": round(total_impact_dollar, 2),
                "total_impact_percent": round(total_impact_pct, 2),
                "severity": severity,
                "portfolio_value": total_portfolio_value
            }

            logger.info(
                f"✓ Total portfolio impact: {total_impact_pct:.2f}% "
                f"(${total_impact_dollar:.2f}) - Severity: {severity}"
            )

            return result

        except Exception as e:
            logger.error(f"Error in impact_scorer: {str(e)}")
            return None

    # ═══════════════════════════════════════════════════════════════════
    # STAGE 6: EXPLANATION GENERATOR
    # ═══════════════════════════════════════════════════════════════════

    def explanation_generator(
        self,
        event_summary: str,
        cascade_result: Dict,
        impact_result: Dict,
        sources: List[str]
    ) -> str:
        """
        Generate human-readable explanation

        Args:
            event_summary: Event summary
            cascade_result: Cascade inference
            impact_result: Impact calculation
            sources: Source URLs

        Returns:
            Explanation string
        """
        try:
            cascade_chain = cascade_result.get('cascade_chain', [])
            affected_holdings = impact_result.get('affected_holdings', [])
            impact_percent = impact_result.get('total_impact_percent', 0.0)

            explanation = gemini_client.generate_explanation(
                event_summary,
                cascade_chain,
                affected_holdings,
                impact_percent,
                sources
            )

            logger.info("✓ Generated explanation")
            return explanation

        except Exception as e:
            logger.error(f"Error in explanation_generator: {str(e)}")
            return f"Supply chain event detected with {impact_result.get('total_impact_percent', 0)}% portfolio impact."

    # ═══════════════════════════════════════════════════════════════════
    # STAGE 7: GRAPH ORCHESTRATOR
    # ═══════════════════════════════════════════════════════════════════

    def graph_orchestrator(
        self,
        alert_id: str,
        event_summary: str,
        relationships: List[Dict],
        cascade_chain: List[Dict]
    ) -> KnowledgeGraph:
        """
        Build knowledge graph

        Args:
            alert_id: Alert ID
            event_summary: Event summary
            relationships: Company relationships
            cascade_chain: Cascade chain

        Returns:
            KnowledgeGraph object
        """
        try:
            graph = KnowledgeGraph(alert_id=alert_id)

            # Add event node
            graph.add_node(
                node_id="event_1",
                node_type="event",
                label=event_summary[:50],
                metadata={"description": event_summary}
            )

            # Add company nodes and edges from relationships
            for idx, rel in enumerate(relationships):
                from_company = rel['from_company']
                to_company = rel['to_company']
                rel_type = rel.get('relationship_type', 'affects')
                confidence = rel.get('confidence', 1.0)

                # Add company nodes
                graph.add_node(
                    node_id=f"company_{from_company}",
                    node_type="company",
                    label=from_company
                )
                graph.add_node(
                    node_id=f"company_{to_company}",
                    node_type="company",
                    label=to_company
                )

                # Add edge
                graph.add_edge(
                    from_id=f"company_{from_company}",
                    to_id=f"company_{to_company}",
                    edge_type=rel_type,
                    confidence=confidence
                )

            # Add cascade chain nodes
            for level_data in cascade_chain:
                company = level_data.get('company')
                level = level_data.get('level')
                impact_type = level_data.get('impact_type')

                graph.add_node(
                    node_id=f"impact_level_{level}_{company}",
                    node_type="impact",
                    label=f"Level {level}: {company}",
                    metadata=level_data
                )

            logger.info(f"✓ Built knowledge graph: {len(graph.nodes)} nodes, {len(graph.edges)} edges")
            return graph

        except Exception as e:
            logger.error(f"Error in graph_orchestrator: {str(e)}")
            return KnowledgeGraph(alert_id=alert_id)

    # ═══════════════════════════════════════════════════════════════════
    # DIRECT IMPACT PROCESSING (NEW!)
    # ═══════════════════════════════════════════════════════════════════

    def _process_direct_impact(self, article: Article, direct_impact: Dict) -> Optional[Alert]:
        """
        Process article with direct impact (skip cascade inference)

        Args:
            article: Validated article
            direct_impact: Direct impact detection result

        Returns:
            Alert object or None
        """
        try:
            logger.info("\n🎯 PROCESSING DIRECT IMPACT (No supply chain cascade)")

            # Get portfolio data from database (NO STATIC DATA)
            portfolio_data = self._get_portfolio()
            if not portfolio_data:
                logger.warning("No portfolio data found in database")
                return None  # Cannot proceed without portfolio

            # Get affected companies and impact
            affected_companies = direct_impact.get('affected_companies', [])
            estimated_impact_pct = direct_impact.get('estimated_impact_percent', 0.0)
            impact_type = direct_impact.get('impact_type', 'neutral')
            event_summary = direct_impact.get('summary', article.title)

            # Calculate impact for each affected holding
            portfolio_value_data = market_data_service.get_portfolio_value(portfolio_data.get('portfolio', []))
            if not portfolio_value_data:
                logger.error("Could not get portfolio value")
                return None

            total_portfolio_value = portfolio_value_data['total_value']
            affected_holdings = []
            total_impact_dollar = 0

            for holding_data in portfolio_value_data['holdings']:
                company_name = holding_data['company_name']
                ticker = holding_data['ticker']

                # Check if this holding is affected
                is_affected = False
                for affected_company in affected_companies:
                    if (affected_company in company_name or
                        affected_company == ticker or
                        affected_company == ticker):
                        is_affected = True
                        break

                if is_affected:
                    holding_value = holding_data['current_value']
                    impact_dollar = holding_value * (estimated_impact_pct / 100)

                    affected_holding = {
                        "company": company_name,
                        "ticker": ticker,
                        "quantity": holding_data['quantity'],
                        "impact_percent": round(estimated_impact_pct, 2),
                        "impact_dollar": round(impact_dollar, 2),
                        "current_price": holding_data['current_price']
                    }

                    affected_holdings.append(affected_holding)
                    total_impact_dollar += impact_dollar

            if not affected_holdings:
                logger.info("No affected holdings found")
                return None

            # Calculate total portfolio impact
            total_impact_pct = (total_impact_dollar / total_portfolio_value) * 100 if total_portfolio_value > 0 else 0

            # Determine severity
            abs_impact = abs(total_impact_pct)
            if abs_impact >= SEVERITY_THRESHOLDS['high']:
                severity = 'high'
            elif abs_impact >= SEVERITY_THRESHOLDS['medium']:
                severity = 'medium'
            else:
                severity = 'low'

            # Generate explanation
            explanation = f"{event_summary} This {impact_type} news directly affects {', '.join(affected_companies)} with an estimated {estimated_impact_pct}% impact. {direct_impact.get('reasoning', '')}"

            # Determine recommendation
            if estimated_impact_pct < -3:
                recommendation = "SELL"
            elif estimated_impact_pct < -1:
                recommendation = "MONITOR"
            elif estimated_impact_pct > 3:
                recommendation = "BUY"
            else:
                recommendation = "HOLD"

            # Create Alert
            alert = Alert(
                type="portfolio_impact",
                severity=severity,
                trigger_article_id=article.id,
                affected_holdings=[AffectedHolding(**h) for h in affected_holdings],
                impact_percent=round(total_impact_pct, 2),
                impact_dollar=round(total_impact_dollar, 2),
                recommendation=recommendation,
                confidence=0.80,  # Slightly lower confidence for direct impact
                chain={
                    "level_1": direct_impact.get('event_category', 'direct_impact'),
                    "level_2": event_summary,
                    "level_3": f"Direct portfolio impact: {total_impact_pct:.2f}%"
                },
                sources=[article.url],
                explanation=explanation
            )

            # Save to database using persistence service
            #database.save_article(article)  # Skip for now - article saving not critical
            
            # Build reasoning trail for database
            reasoning_trail = []
            for company in direct_impact.get('affected_companies', []):
                reasoning_trail.append({
                    'ticker': company,
                    'level': direct_impact.get('severity', 'low'),
                    'reasoning': direct_impact.get('reasoning', 'Direct impact detected'),
                    'confidence': 0.8
                })
            
            
            # Generate headline from article and impact
            impact_direction = "positive" if alert.impact_percent > 0 else "negative" if alert.impact_percent < 0 else "neutral"
            headline = f"{impact_direction.capitalize()} impact on portfolio: {article.title[:100]}"
            
            # Save alert with correct signature
            database.save_alert(
                alert_id=alert.id,
                headline=headline,
                severity=alert.severity,
                impact_pct=alert.impact_percent,  # Use impact_percent not impact_pct
                article_id=article.url,  # Using URL as article ID
                reasoning_trail=reasoning_trail,
                source_urls=[article.url],
                ai_analysis=alert.recommendation,
                full_reasoning=alert.explanation
            )

            # Create simple knowledge graph
            graph = KnowledgeGraph(alert_id=alert.id)
            graph.add_node("event_1", "event", event_summary)
            for company in affected_companies:
                graph.add_node(f"company_{company}", "company", company)
                graph.add_edge("event_1", f"company_{company}", "directly_affects", 1.0)

            database.save_knowledge_graph(graph)

            logger.info(f"\n✅ DIRECT IMPACT ALERT GENERATED: {alert.id}\n")

            return alert

        except Exception as e:
            logger.error(f"Error processing direct impact: {str(e)}", exc_info=True)
            return None

    # ═══════════════════════════════════════════════════════════════════
    # FULL PIPELINE EXECUTION
    # ═══════════════════════════════════════════════════════════════════

    def process_article(self, article: Article) -> Optional[Alert]:
        """
        Run full pipeline on article

        Args:
            article: Article to process

        Returns:
            Alert object or None
        """
        try:
            logger.info(f"\n{'='*70}\nProcessing article: {article.title}\n{'='*70}")

            # Stage 1: Validate
            validated_article = self.event_validator(article)
            if not validated_article:
                return None

            # Stage 2: Extract relationships
            extraction_result = self.relation_extractor(validated_article)

            # NEW: Stage 2B - If no relationships found, check for direct impact
            if not extraction_result or not extraction_result.get('relationships'):
                logger.info("No relationships found, checking for direct impact...")

                # Check for direct impact on portfolio companies
                # Get portfolio from database
                portfolio_data = self._get_portfolio()
                portfolio_companies = [h["ticker"] for h in portfolio_data.get("portfolio", [])]

                direct_impact = gemini_client.detect_direct_impact(
                    validated_article.content,
                    validated_article.title,
                    portfolio_companies
                )

                if not direct_impact or not direct_impact.get('has_direct_impact'):
                    logger.info("No direct impact detected either")
                    return None

                # Handle direct impact (skip cascade inference, go straight to impact)
                logger.info(f"✓ Direct impact detected: {direct_impact.get('impact_type')}")
                return self._process_direct_impact(validated_article, direct_impact)

            relationships = extraction_result.get('relationships', [])
            event_summary = extraction_result.get('summary', validated_article.title)

            # Stage 3: Verify relationships
            verified_relationships = self.relation_verifier(relationships)
            if not verified_relationships:
                logger.info("No verified relationships")
                return None

            # Stage 4: Infer cascade
            cascade_result = self.cascade_inferencer(event_summary, verified_relationships)
            if not cascade_result:
                return None

            # Get portfolio data from database (NO STATIC DATA)
            portfolio_data = self._get_portfolio()
            if not portfolio_data:
                logger.warning("No portfolio data found in database")
                return None  # Cannot proceed without portfolio

            # Stage 5: Score impact
            impact_result = self.impact_scorer(cascade_result, portfolio_data)
            if not impact_result:
                return None

            # Determine if impact is significant enough
            # if abs(impact_result['total_impact_percent']) < SEVERITY_THRESHOLDS['low']:
            #     logger.info(f"Impact too small ({impact_result['total_impact_percent']}%), skipping alert")
            #     return None

            # Stage 6: Generate explanation
            explanation = self.explanation_generator(
                event_summary,
                cascade_result,
                impact_result,
                [validated_article.url]
            )

            # Determine recommendation
            impact_pct = impact_result['total_impact_percent']
            if impact_pct < -3:
                recommendation = "SELL"
            elif impact_pct < -1:
                recommendation = "MONITOR"
            elif impact_pct > 3:
                recommendation = "BUY"
            else:
                recommendation = "HOLD"

            # Create Alert object
            alert = Alert(
                type="portfolio_impact",
                severity=impact_result['severity'],
                trigger_article_id=validated_article.id,
                affected_holdings=[AffectedHolding(**h) for h in impact_result['affected_holdings']],
                impact_percent=impact_result['total_impact_percent'],
                impact_dollar=impact_result['total_impact_dollar'],
                recommendation=recommendation,
                confidence=cascade_result.get('severity') == 'high' and 0.9 or 0.75,
                chain={
                    "level_1": (cascade_result.get('cascade_chain', [{}]) or [{}])[0].get('description', event_summary),
                    "level_2": event_summary,
                    "level_3": f"Portfolio impact: {impact_result['total_impact_percent']}%"
                },
                sources=[validated_article.url],
                explanation=explanation
            )

            # Stage 7: Build knowledge graph
            graph = self.graph_orchestrator(
                alert.id,
                event_summary,
                verified_relationships,
                cascade_result.get('cascade_chain', [])
            )

            # Save to database
            database.save_article(validated_article)
            database.save_alert(alert)
            database.save_knowledge_graph(graph)

            # Save relationships
            for rel in verified_relationships:
                database.save_relationship({
                    **rel,
                    'article_id': validated_article.id,
                    'alert_id': alert.id
                })

            logger.info(f"\n✅ ALERT GENERATED: {alert.id}\n{'='*70}\n")

            return alert

        except Exception as e:
            logger.error(f"Error in process_article: {str(e)}", exc_info=True)
            return None


# Create singleton instance
pipeline = Pipeline()
