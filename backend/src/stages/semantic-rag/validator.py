"""
Semantic RAG Validator

Runs the 10 black-box test scenarios from semantic-rag.md to score
retrieval quality across 6 dimensions:
  1. Correct Object Identified
  2. Correct Fields Retrieved
  3. Policy Retrieved
  4. Workflow Dependency Retrieved
  5. Cross-System Impact Retrieved
  6. Version Correct

Each test scores 0-6, production readiness target is >= 5.0 average.
"""

import asyncio
from typing import Dict, Any, List

TEST_SCENARIOS = [
    {
        "id": 1,
        "question": "Which system is the source of truth for customer credit limit?",
        "expected_keywords": {
            "object": ["account", "credit_limit"],
            "field": ["credit_limit__c"],
            "policy": ["source of truth", "policy", "owns"],
            "workflow": ["sync", "integration"],
            "cross_system": ["oracle", "ar"],
            "version": ["version", "v", "1.0"],
        },
    },
    {
        "id": 2,
        "question": "What happens if I increase a customer's credit limit by more than 15%?",
        "expected_keywords": {
            "object": ["credit_limit", "account"],
            "field": ["credit_limit__c", "threshold"],
            "policy": ["approval", "10%", "15%", "threshold"],
            "workflow": ["approval flow", "workflow"],
            "cross_system": ["erp", "sync", "oracle"],
            "version": ["version", "1.0"],
        },
    },
    {
        "id": 3,
        "question": "If I deactivate a customer in Salesforce, what is impacted in Oracle ERP?",
        "expected_keywords": {
            "object": ["account", "customer"],
            "field": ["status", "active"],
            "policy": ["deactivation", "balance check"],
            "workflow": ["ar", "invoice"],
            "cross_system": ["oracle", "erp", "ar"],
            "version": ["version", "1.0"],
        },
    },
    {
        "id": 4,
        "question": "Can customer credit limits be modified during financial close?",
        "expected_keywords": {
            "object": ["credit_limit"],
            "field": ["credit_limit__c"],
            "policy": ["close window", "financial close", "sox", "restriction"],
            "workflow": ["close", "period"],
            "cross_system": ["erp"],
            "version": ["version", "1.0"],
        },
    },
    {
        "id": 5,
        "question": "What validations apply to the credit limit field?",
        "expected_keywords": {
            "object": ["credit_limit", "account"],
            "field": ["currency", "max", "validation"],
            "policy": ["justification", "approval", "threshold"],
            "workflow": ["risk tier", "evaluation"],
            "cross_system": ["sync", "dependency"],
            "version": ["version", "1.0"],
        },
    },
    {
        "id": 6,
        "question": "What workflows are triggered when a new enterprise customer is created?",
        "expected_keywords": {
            "object": ["account", "customer"],
            "field": ["creation", "required"],
            "policy": ["risk assessment", "credit review"],
            "workflow": ["workflow", "provisioning", "creation"],
            "cross_system": ["oracle", "erp"],
            "version": ["version", "1.0"],
        },
    },
    {
        "id": 7,
        "question": "How is customer risk tier determined and where is it used?",
        "expected_keywords": {
            "object": ["risk_tier", "customer"],
            "field": ["risk_tier__c"],
            "policy": ["scoring", "risk", "credit"],
            "workflow": ["collection", "approval"],
            "cross_system": ["erp", "ar"],
            "version": ["version", "1.0"],
        },
    },
    {
        "id": 8,
        "question": "What changed in customer schema in the last release?",
        "expected_keywords": {
            "object": ["schema", "customer", "account"],
            "field": ["field", "added", "deprecated"],
            "policy": ["policy update"],
            "workflow": ["migration"],
            "cross_system": ["sync"],
            "version": ["version", "release", "v", "1.0"],
        },
    },
    {
        "id": 9,
        "question": "Who is authorized to override customer credit block?",
        "expected_keywords": {
            "object": ["credit", "block", "override"],
            "field": ["credit_block"],
            "policy": ["role", "finance manager", "authorization", "rbac"],
            "workflow": ["audit", "logging", "justification"],
            "cross_system": ["system"],
            "version": ["version", "1.0"],
        },
    },
    {
        "id": 10,
        "question": "What steps are required to fully onboard a new B2B customer across systems?",
        "expected_keywords": {
            "object": ["account", "customer", "onboard"],
            "field": ["required fields", "creation"],
            "policy": ["credit assessment", "validation"],
            "workflow": ["provisioning", "sequence", "rollback"],
            "cross_system": ["oracle", "salesforce", "erp"],
            "version": ["version", "1.0"],
        },
    },
    {
        "id": 11,
        "question": "What is the safety stock policy for Class A materials?",
        "expected_keywords": {
            "object": ["inventory", "material", "safety_stock"],
            "field": ["abc", "class", "days"],
            "policy": ["inventory", "policy", "7 days"],
            "workflow": ["reorder", "replenishment"],
            "cross_system": ["sap"],
            "version": ["version", "1.0"],
        },
    },
    {
        "id": 12,
        "question": "How does demand forecasting work in the supply chain?",
        "expected_keywords": {
            "object": ["forecast", "demand", "opportunity"],
            "field": ["quantity", "sku", "region"],
            "policy": ["pricing", "freshness"],
            "workflow": ["forecast", "ensemble", "promotion"],
            "cross_system": ["salesforce", "sap"],
            "version": ["version", "1.0"],
        },
    },
    {
        "id": 13,
        "question": "What data flows from Salesforce to SAP for demand planning?",
        "expected_keywords": {
            "object": ["opportunity", "material", "demand"],
            "field": ["product_id", "quantity", "delivery"],
            "policy": ["freshness", "data"],
            "workflow": ["sync", "demand"],
            "cross_system": ["salesforce", "sap"],
            "version": ["version", "1.0"],
        },
    },
    {
        "id": 14,
        "question": "What is the supplier risk scoring process?",
        "expected_keywords": {
            "object": ["vendor", "supplier", "risk"],
            "field": ["risk_rating", "score", "delivery"],
            "policy": ["risk", "threshold", "single"],
            "workflow": ["risk scoring", "assessment"],
            "cross_system": ["sap", "oracle"],
            "version": ["version", "1.0"],
        },
    },
    {
        "id": 15,
        "question": "Which applications use Material_Master?",
        "expected_keywords": {
            "object": ["material_master", "product", "sku"],
            "field": ["gtin", "material_id", "category"],
            "policy": ["inventory", "quality"],
            "workflow": ["forecast", "production"],
            "cross_system": ["sap", "salesforce"],
            "version": ["version", "1.0"],
        },
    },
    {
        "id": 16,
        "question": "What are the SCOR Plan process entities in the supply chain?",
        "expected_keywords": {
            "object": ["plan", "demand", "inventory"],
            "field": ["forecast", "safety_stock", "reorder"],
            "policy": ["inventory policy"],
            "workflow": ["demand forecast", "rebalancing"],
            "cross_system": ["sap", "salesforce"],
            "version": ["version", "1.0"],
        },
    },
    {
        "id": 17,
        "question": "What is Material_Master and how is it mapped to a data source?",
        "expected_keywords": {
            "object": ["material_master", "material", "product"],
            "field": ["gtin", "material_id", "category", "brand"],
            "policy": ["sustainability", "inventory"],
            "workflow": ["forecast", "production"],
            "cross_system": ["sap", "mapping", "simulator"],
            "version": ["version", "1.0"],
        },
    },
    {
        "id": 18,
        "question": "Show me AR_Invoice fields and which system owns it.",
        "expected_keywords": {
            "object": ["oracle_ar_invoice", "invoice"],
            "field": ["invoice_id", "amount", "status", "customer_id"],
            "policy": ["order fulfillment", "credit"],
            "workflow": ["order-to-cash", "billing"],
            "cross_system": ["oracle", "salesforce"],
            "version": ["version", "1.0"],
        },
    },
    {
        "id": 19,
        "question": "What entities are needed for the Demand Forecasting use case?",
        "expected_keywords": {
            "object": ["opportunity", "material_master", "campaign", "forecast"],
            "field": ["product_id", "quantity", "region"],
            "policy": ["pricing", "data freshness"],
            "workflow": ["demand forecast", "consensus"],
            "cross_system": ["salesforce", "sap"],
            "version": ["version", "1.0"],
        },
    },
    {
        "id": 20,
        "question": "How does Account in Salesforce sync to AR_Customer?",
        "expected_keywords": {
            "object": ["account", "ar_customer"],
            "field": ["credit_limit", "tier", "collection_priority"],
            "policy": ["credit", "sync"],
            "workflow": ["integration", "sync"],
            "cross_system": ["salesforce", "oracle"],
            "version": ["version", "1.0"],
        },
    },
    {
        "id": 21,
        "question": "What is the inventory policy for safety stock levels?",
        "expected_keywords": {
            "object": ["inventory", "safety_stock"],
            "field": ["abc", "days", "reorder"],
            "policy": ["inventory", "policy", "safety stock"],
            "workflow": ["rebalancing", "replenishment"],
            "cross_system": ["sap"],
            "version": ["version", "1.0"],
        },
    },
    {
        "id": 22,
        "question": "Which virtual entities are mapped via simulator data sources?",
        "expected_keywords": {
            "object": ["virtual", "entity", "simulator"],
            "field": ["mapping", "source", "table"],
            "policy": ["data freshness"],
            "workflow": ["mapping", "rule"],
            "cross_system": ["sap", "oracle", "salesforce"],
            "version": ["version", "1.0"],
        },
    },
]

DIMENSIONS = ["object", "field", "policy", "workflow", "cross_system", "version"]


class SemanticRagValidator:
    def __init__(self, logger=None):
        self._log = logger

    def _info(self, msg):
        if self._log:
            self._log.log_info(msg)

    def _get_services(self):
        from src.services.fdw_connection_manager import PostgreSQLConnectionManager
        from src.services.control_plane.vector_store import VectorStore
        from src.services.control_plane.embedding_service import EmbeddingService
        from src.config.fdw_config import FDWConfig

        config = FDWConfig.from_environment()
        conn_mgr = PostgreSQLConnectionManager(config)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(conn_mgr.initialize())

        store = VectorStore(conn_mgr)
        emb_svc = EmbeddingService()
        return store, emb_svc, loop

    def run_tests(self) -> Dict[str, Any]:
        try:
            store, emb_svc, loop = self._get_services()
        except Exception as e:
            self._info(f"Cannot run validation — services unavailable: {e}")
            return {"error": str(e), "total_tests": 0, "tests_passed": 0, "average_score": 0}

        if not emb_svc.available:
            self._info("EmbeddingService has no API key — running keyword-only validation")

        results = []
        for scenario in TEST_SCENARIOS:
            score, details = self._run_single_test(scenario, store, emb_svc, loop)
            results.append({
                "test_id": scenario["id"],
                "question": scenario["question"],
                "score": score,
                "max_score": 6,
                "dimensions": details,
            })
            self._info(f"  Test {scenario['id']}: {score}/6")

        scores = [r["score"] for r in results]
        avg = sum(scores) / len(scores) if scores else 0
        passed = sum(1 for s in scores if s >= 5)

        self._info(f"Validation: {passed}/{len(results)} tests passed, avg score {avg:.1f}/6.0")

        return {
            "total_tests": len(results),
            "tests_passed": passed,
            "average_score": round(avg, 2),
            "threshold": 5.0,
            "production_ready": avg >= 5.0,
            "test_results": results,
        }

    def _run_single_test(self, scenario: Dict, store, emb_svc, loop) -> tuple:
        query = scenario["question"]
        expected = scenario["expected_keywords"]

        try:
            if emb_svc.available:
                query_emb = emb_svc.embed_text(query)
                results = loop.run_until_complete(
                    store.search(query_embedding=query_emb, limit=10, min_similarity=0.2)
                )
            else:
                results = loop.run_until_complete(
                    store.search_by_text(query, limit=10)
                ) if hasattr(store, 'search_by_text') else []
        except Exception as e:
            self._info(f"  Search failed for test {scenario['id']}: {e}")
            return 0, {d: {"score": 0, "found": False} for d in DIMENSIONS}

        retrieved_text = " ".join(
            r.get("content", "") + " " + str(r.get("metadata", {}))
            for r in (results or [])
        ).lower()

        details = {}
        total_score = 0

        for dim in DIMENSIONS:
            keywords = expected.get(dim, [])
            found = any(kw.lower() in retrieved_text for kw in keywords)
            dim_score = 1 if found else 0
            details[dim] = {"score": dim_score, "found": found,
                            "searched_keywords": keywords}
            total_score += dim_score

        return total_score, details
