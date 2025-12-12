"""
Critical Fixes Test Suite
Tests for known issues to prevent regression:
1. KnowledgeGraph field names (from_node, to_node)
2. feedparser Python 3.13 compatibility
3. yfinance installation verification
"""

import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestCriticalFixes:
    """Test suite for critical bug fixes"""

    def test_knowledge_graph_field_names(self):
        """
        ERROR #1 FIX: KnowledgeGraph Model Field Names
        
        Issue: Test code was using "from"/"to" instead of "from_node"/"to_node"
        Fix: Ensure GraphEdge model uses correct field names
        Verification: Create edges with from_node and to_node fields
        """
        from app.models.knowledge_graph import KnowledgeGraph, GraphEdge
        
        # Create a knowledge graph
        graph = KnowledgeGraph(alert_id="test_alert_123")
        
        # Add nodes
        graph.add_node("event_1", "event", "Supply Chain Disruption")
        graph.add_node("company_1", "company", "Apple Inc.")
        
        # Add edge with CORRECT field names
        graph.add_edge("event_1", "company_1", "impacts", 0.95)
        
        # Verify the edge was created with correct fields
        assert len(graph.edges) == 1
        edge = graph.edges[0]
        
        # These should NOT raise AttributeError
        assert edge.from_node == "event_1", "Edge should have from_node field"
        assert edge.to_node == "company_1", "Edge should have to_node field"
        assert edge.type == "impacts"
        assert edge.confidence == 0.95
        
        print("✅ KnowledgeGraph field names verified: from_node and to_node")

    def test_feedparser_python_3_13_compatibility(self):
        """
        ERROR #2 FIX: feedparser Python 3.13 Compatibility
        
        Issue: feedparser 6.0.10 tried to import 'cgi' module which was removed in Python 3.13
        Fix: Upgrade feedparser to 6.0.12 which removed dependency on 'cgi'
        Verification: Successfully import feedparser without ModuleNotFoundError
        """
        try:
            import feedparser
            
            # Verify version is compatible with Python 3.13
            version = feedparser.__version__
            major, minor, patch = map(int, version.split('.')[:3])
            
            # feedparser 6.0.11+ is compatible with Python 3.13
            assert major >= 6, f"feedparser version {version} is too old"
            assert minor >= 0, f"feedparser version {version} is too old"
            assert patch >= 11, f"feedparser version {version} < 6.0.11 (incompatible with Python 3.13)"
            
            print(f"✅ feedparser version {version} is Python 3.13 compatible")
            
        except ImportError as e:
            pytest.fail(f"feedparser import failed: {e}")
        except ModuleNotFoundError as e:
            if "'cgi'" in str(e):
                pytest.fail(f"feedparser trying to import removed 'cgi' module: {e}")
            raise

    def test_yfinance_installed(self):
        """
        ERROR #3 FIX: yfinance Installation
        
        Issue: yfinance was in requirements.txt but pip install -r failed, so it wasn't installed
        This broke entire import chain: main.py → routes.py → market_data.py → yfinance
        
        Fix: Ensure yfinance==0.2.32 is in requirements.txt and successfully installed
        Verification: Successfully import yfinance without ModuleNotFoundError
        """
        try:
            import yfinance as yf
            
            # Verify module exists and has expected attributes
            assert hasattr(yf, 'download'), "yfinance should have download function"
            assert hasattr(yf, 'Ticker'), "yfinance should have Ticker class"
            
            print("✅ yfinance successfully imported with all required functions")
            
        except ImportError as e:
            pytest.fail(f"yfinance import failed: {e}")

    def test_import_chain_market_data(self):
        """
        INTEGRATION TEST: Import Chain (was broken by missing yfinance)
        
        Chain: main.py → routes.py → market_data.py → yfinance
        Verification: All imports succeed without errors
        """
        try:
            from app.services.market_data import market_data_service
            assert market_data_service is not None
            print("✅ market_data_service imported successfully")
        except ImportError as e:
            pytest.fail(f"market_data import chain broken: {e}")

    def test_import_chain_routes(self):
        """
        INTEGRATION TEST: API Routes Import (was blocked by market_data)
        
        Verification: routes.py can be imported (which requires market_data.py)
        """
        try:
            from app.api.routes import router
            assert router is not None
            assert len(router.routes) > 0, "Router should have at least one route"
            print(f"✅ API routes imported successfully ({len(router.routes)} endpoints)")
        except ImportError as e:
            pytest.fail(f"API routes import failed: {e}")

    def test_import_chain_fastapi_app(self):
        """
        INTEGRATION TEST: FastAPI Main Application
        
        Verification: main.py can initialize FastAPI app
        """
        try:
            from app.main import app
            assert app is not None
            assert app.title == "MarketPulse-X API"
            print("✅ FastAPI app initialized successfully")
        except ImportError as e:
            pytest.fail(f"FastAPI app initialization failed: {e}")

    def test_news_aggregator_with_feedparser(self):
        """
        INTEGRATION TEST: News Aggregator with feedparser
        
        Verification: NewsAggregator can be initialized after feedparser upgrade
        """
        try:
            from app.services.news_aggregator import NewsAggregator
            agg = NewsAggregator()
            assert agg is not None
            print("✅ NewsAggregator initialized successfully")
        except ImportError as e:
            pytest.fail(f"NewsAggregator initialization failed: {e}")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])
