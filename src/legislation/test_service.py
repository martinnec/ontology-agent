"""
Simple test for the LegislationService.
This test file follows the project's testing guidelines:
- No testing library dependencies
- Simple Python script with main function
- Tests placed directly in src directory
- Named with test_ prefix
- Self-contained and runnable independently

HOW TO RUN:
From the src directory, run:
    python -m legislation.test_service

Or from the project root:
    cd src && python -m legislation.test_service

The test uses mock implementations to avoid external dependencies like OpenAI API.
"""

import os
from pydantic import AnyUrl
from typing import Optional
from .service import LegislationService
from .datasource import LegislationDataSource
from .domain import LegalAct, LegalStructuralElement

# Set dummy environment variable to avoid OpenAI API key requirement in tests
os.environ["OPENAI_API_KEY"] = "dummy-key-for-testing"


class MockDataSource(LegislationDataSource):
    """Mock implementation of LegislationDataSource for testing."""
    
    def __init__(self):
        self.stored_acts = {}
        self.stored_elements = {}
        
    def get_legal_act(self, id: AnyUrl) -> LegalAct:
        """Return a mock legal act for testing."""
        legal_act_id = str(id)
        
        # Return a sample legal act without summaries for testing
        return LegalAct(
            id=id,
            officialIdentifier="Test Act 2025",
            title="Test Legal Act",
            summary=None,  # No summary to trigger summarization
            textContent="This is a test legal act content.",
            elements=[
                LegalStructuralElement(
                    id=f"{legal_act_id}/par_1",
                    officialIdentifier="Section 1",
                    title="First Section",
                    summary=None,  # No summary to trigger summarization
                    textContent="Content of the first section.",
                    elements=None
                )
            ]
        )
    
    def get_legal_act_element(self, element_id: AnyUrl) -> LegalStructuralElement:
        """Return a mock legal act element for testing."""
        return LegalStructuralElement(
            id=element_id,
            officialIdentifier="Section 1",
            title="First Section",
            summary=None,
            textContent="Content of the first section.",
            elements=None
        )
    
    def store_legal_act(self, legal_act: LegalAct) -> None:
        """Store the legal act in memory for testing."""
        self.stored_acts[str(legal_act.id)] = legal_act
        print(f"Stored legal act with ID: {legal_act.id}")


class MockSummarizer:
    """Mock summarizer to avoid LLM dependencies in tests."""
    
    def __init__(self, model_identifier: str):
        self.model_identifier = model_identifier
    
    def summarize(self, legal_act: LegalAct) -> LegalAct:
        """Add mock summaries to the legal act."""
        # Add summary to the main act
        legal_act.summary = f"Mock summary for {legal_act.title}"
        
        # Add summaries to elements recursively
        if legal_act.elements:
            for element in legal_act.elements:
                self._add_summary_to_element(element)
        
        return legal_act
    
    def _add_summary_to_element(self, element: LegalStructuralElement) -> None:
        """Add summary to an element and its sub-elements."""
        element.summary = f"Mock summary for {element.title}"
        
        if element.elements:
            for sub_element in element.elements:
                self._add_summary_to_element(sub_element)


def test_legislation_service_init():
    """Test that LegislationService can be initialized properly."""
    print("Testing LegislationService initialization...")
    
    datasource = MockDataSource()
    service = LegislationService(datasource, "mock-llm-model")
    
    assert service.datasource == datasource
    assert service.summarizer.model == "mock-llm-model"
    
    print("✓ LegislationService initialized successfully")


def test_get_legal_act_with_summarization():
    """Test getting a legal act that needs summarization."""
    print("Testing get_legal_act with summarization...")
    
    # Mock the summarizer to avoid LLM calls
    datasource = MockDataSource()
    service = LegislationService(datasource, "mock-llm-model")
    
    # Replace the real summarizer with our mock
    service.summarizer = MockSummarizer("mock-llm-model")
    
    legal_act_id = AnyUrl("https://example.com/legal-act/test-2025")
    
    # Get the legal act (should trigger summarization)
    result = service.get_legal_act(legal_act_id)
    
    # Verify that summaries were added
    assert result.summary is not None
    assert result.summary == "Mock summary for Test Legal Act"
    assert result.elements[0].summary is not None
    assert result.elements[0].summary == "Mock summary for First Section"
    
    # Verify that the legal act was stored
    assert str(legal_act_id) in datasource.stored_acts
    
    print("✓ Legal act retrieved and summarized successfully")


def test_get_legal_act_element():
    """Test getting a specific legal act element."""
    print("Testing get_legal_act_element...")
    
    datasource = MockDataSource()
    service = LegislationService(datasource, "mock-llm-model")
    service.summarizer = MockSummarizer("mock-llm-model")
    
    element_id = AnyUrl("https://example.com/legal-act/test-2025/par_1")
    
    # Get the element (should trigger summarization of the whole act)
    result = service.get_legal_act_element(element_id)
    
    # Verify the element was returned
    assert result.id == element_id
    assert result.title == "First Section"
    
    print("✓ Legal act element retrieved successfully")


def test_needs_summarization():
    """Test the _needs_summarization method."""
    print("Testing _needs_summarization logic...")
    
    datasource = MockDataSource()
    service = LegislationService(datasource, "mock-llm-model")
    
    # Create an act without summary
    act_without_summary = LegalAct(
        id=AnyUrl("https://example.com/test"),
        officialIdentifier="Test",
        title="Test Act",
        summary=None,
        textContent="Some content",
        elements=None
    )
    
    # Should need summarization
    assert service._needs_summarization(act_without_summary) == True
    
    # Create an act with summary
    act_with_summary = LegalAct(
        id=AnyUrl("https://example.com/test"),
        officialIdentifier="Test",
        title="Test Act", 
        summary="Already has summary",
        textContent="Some content",
        elements=None
    )
    
    # Should not need summarization
    assert service._needs_summarization(act_with_summary) == False
    
    print("✓ _needs_summarization logic working correctly")


def test_extract_legal_act_id_from_element_id():
    """Test the ID extraction logic."""
    print("Testing _extract_legal_act_id_from_element_id...")
    
    datasource = MockDataSource()
    service = LegislationService(datasource, "mock-llm-model")
    
    # Test section ID format
    element_id = AnyUrl("https://example.com/legal-act/test-2025/par_1")
    result = service._extract_legal_act_id_from_element_id(element_id)
    expected = "https://example.com/legal-act/test-2025"
    
    assert str(result) == expected
    
    print("✓ Legal act ID extraction working correctly")


def run_all_tests():
    """Run all test functions."""
    print("=" * 50)
    print("Running LegislationService Tests")
    print("=" * 50)
    
    test_functions = [
        test_legislation_service_init,
        test_get_legal_act_with_summarization,
        test_get_legal_act_element,
        test_needs_summarization,
        test_extract_legal_act_id_from_element_id
    ]
    
    passed = 0
    failed = 0
    
    for test_func in test_functions:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"✗ {test_func.__name__} FAILED: {e}")
            failed += 1
    
    print("=" * 50)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 50)
    
    return failed == 0


def main():
    """Main function to run the tests."""
    success = run_all_tests()
    if success:
        print("All tests passed!")
        return 0
    else:
        print("Some tests failed!")
        return 1


if __name__ == "__main__":
    exit(main())
