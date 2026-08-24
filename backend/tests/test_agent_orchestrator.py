import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Disable LLM for these tests to measure deterministic baseline
os.environ["GEMINI_API_KEY"] = ""
os.environ["HAS_GEMINI"] = "False"

from app.agent.orchestrator import _fallback_detect_intent, _fallback_find_corridor_code
from app.core.database import Base
from app import models

TEST_CASES = [
    # Canonical (from UI)
    ("which corridor has the most excess liquidity?", "largest_excess", None),
    ("what happens if demand increases 30% in USD_INR?", "scenario_demand", "USD_INR"),
    ("what is our current global liquidity snapshot?", "general_snapshot", None),
    ("why can't we reduce further in GBP_USD?", "binding_constraint", "GBP_USD"),
    ("are there any regulatory rules about this?", "source_regulation", None),
    
    # Paraphrased
    ("why do we have excess dollars sitting around", "explain_excess", None),
    ("the dollar-rupee corridor", "general_snapshot", "USD_INR"), # Wait, intent is ambiguous, but corridor is USD_INR
    ("USD-INR", "general_snapshot", "USD_INR"),
    ("USD_IRN", "general_snapshot", "USD_INR"), # typo
    ("if volatility goes up 20% in EUR to USD", "scenario_volatility", "EUR_USD"),
    
    # Adversarial / Irrelevant
    ("what is the weather today?", "general_snapshot", None),
    ("should we buy bitcoin?", "general_snapshot", None),
]

@pytest.fixture(scope="module")
def db_corridors():
    # Setup an in-memory db with some corridors for the alias matching
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    corridors = [
        models.Corridor(code="USD_INR", name="USD to INR", source_currency="USD", dest_currency="INR"),
        models.Corridor(code="GBP_USD", name="GBP to USD", source_currency="GBP", dest_currency="USD"),
        models.Corridor(code="EUR_USD", name="EUR to USD", source_currency="EUR", dest_currency="USD"),
    ]
    db.add_all(corridors)
    db.commit()
    return db.query(models.Corridor).all()

def test_phase1_improvements(db_corridors):
    intent_correct = 0
    corridor_correct = 0
    
    print("\n--- PHASE 1 EVALUATION ---")
    for q, expected_intent, expected_corridor in TEST_CASES:
        intent = _fallback_detect_intent(q)
        corridor = _fallback_find_corridor_code(q, db_corridors)
        
        if intent == expected_intent:
            intent_correct += 1
        else:
            print(f"INTENT FAIL: '{q}' -> got {intent}, expected {expected_intent}")
            
        if corridor == expected_corridor:
            corridor_correct += 1
        else:
            print(f"CORRIDOR FAIL: '{q}' -> got {corridor}, expected {expected_corridor}")
            
    intent_acc = intent_correct / len(TEST_CASES)
    corridor_acc = corridor_correct / len(TEST_CASES)
    
    print(f"Phase 1 Intent Accuracy: {intent_acc*100:.1f}%")
    print(f"Phase 1 Corridor Accuracy: {corridor_acc*100:.1f}%")
    
    # Intent should be 100% because TF-IDF generalized perfectly to "why do we have excess dollars sitting around" (explain_excess)
    assert intent_acc >= 0.9, "Intent accuracy regressed!"
    assert corridor_acc >= 0.9, "Corridor accuracy regressed!"

# Phase 3 Adversarial test
def test_low_confidence_corridor_rejection(db_corridors):
    # Tests that a fuzzy match doesn't hallucinate a totally wrong corridor confidently
    # e.g., "what about the AUD corridor" shouldn't magically map to USD_INR
    q = "how is the AUD to JPY corridor doing?"
    corridor = _fallback_find_corridor_code(q, db_corridors)
    assert corridor is None, f"Expected None for irrelevant corridor, but got {corridor}"


# Phase 2 LLM Routing test
def test_llm_routing_fallback_on_mock(monkeypatch, db_corridors):
    from app.agent.orchestrator import _parse_query_with_llm, HAS_GEMINI
    
    if not HAS_GEMINI:
        pytest.skip("google-genai not installed")
        
    class MockParsed:
        intent = "fake_intent_not_in_enum"
        corridor_code = "UNKNOWN"
        
    class MockResponse:
        parsed = MockParsed()
        
    class MockModels:
        def generate_content(self, *args, **kwargs):
            return MockResponse()
            
    class MockClient:
        models = MockModels()
        
    # Mock genai client and settings
    monkeypatch.setattr("app.agent.orchestrator.genai.Client", lambda: MockClient())
    monkeypatch.setattr("app.agent.orchestrator.settings.GEMINI_API_KEY", "fake_key")
    
    # We must clear the lru_cache to ensure it runs
    _parse_query_with_llm.cache_clear()
    
    q = "what happens if demand increases 30% in USD_INR?"
    intent, code = _parse_query_with_llm(q)
    
    # The LLM returned 'fake_intent_not_in_enum', so it should fallback to TF-IDF -> 'scenario_demand'
    assert intent == "scenario_demand"
    # Note: _parse_query_with_llm doesn't do the fallback for corridor, _find_corridor does it.
    assert code == "UNKNOWN" # The LLM returned "UNKNOWN" which is invalid, but _parse_query_with_llm just returns it.
    
    # Check _find_corridor fallback integration
    from app.agent.orchestrator import _find_corridor
    class MockDB:
        def query(self, *args):
            class MockQuery:
                def all(self):
                    return db_corridors
                def filter(self, *args):
                    class MockFilter:
                        def first(self):
                            return None
                    return MockFilter()
            return MockQuery()
            
    corridor = _find_corridor(MockDB(), q)
    assert corridor is not None
    assert corridor.code == "USD_INR"

