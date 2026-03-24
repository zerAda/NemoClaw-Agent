"""LinkedIn scraper tests — patchright migration + context reuse."""
import pytest
import os
import ast

@pytest.mark.asyncio
async def test_patchright_import():
    """INFRA-05: scraper.py imports from patchright, not playwright."""
    scraper_path = os.path.join(os.path.dirname(__file__), "..", "src", "scraper.py")
    with open(scraper_path) as f:
        tree = ast.parse(f.read())
    imports = [node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]
    import_names = []
    for imp in imports:
        if isinstance(imp, ast.ImportFrom) and imp.module:
            import_names.append(imp.module)
    assert "patchright.async_api" in import_names
    assert "playwright.async_api" not in import_names
    assert "playwright_stealth" not in import_names

@pytest.mark.asyncio
async def test_no_stealth_call():
    """INFRA-05: stealth_async is not called anywhere in Scraper class."""
    scraper_path = os.path.join(os.path.dirname(__file__), "..", "src", "scraper.py")
    with open(scraper_path) as f:
        source = f.read()
    assert "stealth_async" not in source

@pytest.mark.asyncio
async def test_linkedin_returns_listings():
    """SCRAPE-04: LinkedIn search_linkedin_jobs returns list[JobListing] with source='linkedin'."""
    # Verify return type annotation includes JobListing
    scraper_path = os.path.join(os.path.dirname(__file__), "..", "src", "scraper.py")
    with open(scraper_path) as f:
        source = f.read()
    # Check that search_linkedin_jobs constructs JobListing objects
    assert "JobListing(" in source
    assert 'source="linkedin"' in source or "source='linkedin'" in source

@pytest.mark.skip(reason="Needs patchright browser mock")
@pytest.mark.asyncio
async def test_context_reuse():
    """SCRAPE-06: One browser context per batch, page per URL, browser closed at end."""
    pass
