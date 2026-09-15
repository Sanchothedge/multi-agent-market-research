from __future__ import annotations

import unittest

from src import config
from src.llm import select_direct_competitors
from src.you_search import search


class DryRunModeTests(unittest.TestCase):
    def setUp(self) -> None:
        config.DRY_RUN = True
        config.YOU_API_KEY = ""
        config.OPENAI_API_KEY = ""

    def test_you_search_returns_stubbed_results_in_dry_run(self) -> None:
        result = search("test query")
        self.assertIn("web", result)
        self.assertTrue(result["web"])

    def test_llm_returns_stubbed_competitors_in_dry_run(self) -> None:
        competitors = select_direct_competitors(
            company_name="Acme",
            company_website="https://acme.com",
            industry="B2B software",
            target_market="Mid-market SaaS",
            country_or_region="US",
            you_evidence={"web": [{"url": "https://example.com"}]},
        )
        self.assertTrue(competitors)
        self.assertIn("name", competitors[0])


if __name__ == "__main__":
    unittest.main()
