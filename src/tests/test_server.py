"""
Tests for the ArXiv Query MCP Server
"""

import os
import pytest
import tempfile
from pathlib import Path
from mcp_arxiv_query.server import ArxivQueryServer


@pytest.fixture
def arxiv_server():
    """Create a temporary directory for downloads and initialize the server."""
    with tempfile.TemporaryDirectory() as temp_dir:
        server = ArxivQueryServer(Path(temp_dir))
        yield server


def test_search_arxiv(arxiv_server):
    """Test the search_arxiv method."""
    # Simple search for a common term
    results = arxiv_server.search_arxiv("neural networks", max_results=3)

    # Check that we got some results
    assert isinstance(results, list)
    assert len(results) > 0

    # Check the structure of the results
    for paper in results:
        assert "id" in paper
        assert "title" in paper
        assert "authors" in paper
        assert "abstract" in paper
        assert isinstance(paper["authors"], list)


def test_search_by_category(arxiv_server):
    """Test the search_by_category method."""
    # Search in the CS.AI category
    results = arxiv_server.search_by_category("cs.AI", max_results=3)

    # Check that we got some results
    assert isinstance(results, list)
    assert len(results) > 0

    # Check that all papers are in the specified category
    for paper in results:
        assert "categories" in paper
        # Note: papers can be in multiple categories
        assert any("cs.AI" in cat for cat in paper["categories"])


def test_search_by_author(arxiv_server):
    """Test the search_by_author method."""
    # Search for a well-known author (note: this may fail if no papers exist)
    results = arxiv_server.search_by_author("Hinton", max_results=3)

    # Check that we got some results
    assert isinstance(results, list)
    assert len(results) > 0

    # Check the structure of the results
    for paper in results:
        assert "id" in paper
        assert "title" in paper
        assert "authors" in paper


def test_download_paper(arxiv_server, monkeypatch):
    """Test the download_paper method with a mock."""

    # Mock the download_pdf method to avoid actual downloads
    def mock_download_pdf(self, paper_id, dir_path, filename):
        # Create an empty file to simulate download
        file_path = os.path.join(dir_path, filename or f"{paper_id}.pdf")
        with open(file_path, "w") as f:
            f.write("Mock PDF content")
        return file_path

    # Apply the mock
    import arxiv_query_fluent

    monkeypatch.setattr(
        arxiv_query_fluent.FeedResults, "download_pdf", mock_download_pdf
    )

    # Attempt to download a paper
    result = arxiv_server.download_paper("2301.00001")

    # Check the result contains a file path
    assert "file_path" in result
    assert os.path.exists(result["file_path"])
