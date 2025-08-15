"""
Simple test for the LegislationSummarizer.
This test file follows the project's testing guidelines:
- No testing library dependencies
- Simple Python script with main function
- Tests placed directly in src directory
- Named with test_ prefix
- Self-contained and runnable independently

HOW TO RUN:
From the src directory, run:
    python -m legislation.test_summarizer

Or from the project root:
    cd src && python -m legislation.test_summarizer

The test uses mock implementations to avoid external dependencies.
"""

import os
# Set any required environment variables for testing
os.environ["OPENAI_API_KEY"] = "dummy-api-key-for-testing"

# Import statements using relative imports
from .summarizer import LegislationSummarizer
from .domain import LegalAct, LegalSection


class MockOpenAIClient:
    """Mock implementation of OpenAI client for testing."""
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.chat = MockChatCompletions()


class MockChatCompletions:
    """Mock implementation of chat completions."""
    
    def create(self, model, messages, max_tokens, temperature):
        """Mock create method that returns different responses based on the system prompt."""
        system_message = messages[0]["content"] if messages else ""
        user_message = messages[1]["content"] if len(messages) > 1 else ""
        
        # Mock response for summarization
        if "summarizes legal texts" in system_message:
            return MockResponse("This is a mock summary of the legal text content. It captures the main concepts and relationships in a concise manner.")
        
        # Mock response for concept extraction
        elif "important semantic concepts and relationships" in system_message:
            return MockResponse("legal obligation\ncompliace requirement\npenalty\nviolation\nenforcement\nauthority")
        
        # Default response
        else:
            return MockResponse("Mock response for unknown prompt type.")


class MockResponse:
    """Mock response object."""
    
    def __init__(self, content):
        self.choices = [MockChoice(content)]


class MockChoice:
    """Mock choice object."""
    
    def __init__(self, content):
        self.message = MockMessage(content)


class MockMessage:
    """Mock message object."""
    
    def __init__(self, content):
        self.content = content


def test_summarizer_initialization():
    """Test that the summarizer initializes correctly with mock API key."""
    print("Testing summarizer initialization...")
    
    summarizer = LegislationSummarizer("gpt-4")
    assert summarizer.model == "gpt-4"
    assert summarizer.open_api_key == "dummy-api-key-for-testing"
    
    print("✓ Summarizer initialization working correctly")


def test_summarizer_with_mock_client():
    """Test summarizer functionality with mock OpenAI client."""
    print("Testing summarizer with mock client...")
    
    # Create a simple legal section for testing
    section = LegalSection(
        id="http://example.com/section1",
        officialIdentifier="§ 1",
        title="Test Section",
        textContent="This is a test legal text that defines obligations and penalties for violations."
    )
    
    # Create summarizer and replace client with mock
    summarizer = LegislationSummarizer("gpt-4")
    summarizer.client = MockOpenAIClient("dummy-key")
    
    # Test the _summarize_element method
    summary = summarizer._summarize_element(section)
    
    # Verify that summary was generated
    assert section.summary is not None
    assert isinstance(section.summary, str)
    assert len(section.summary) > 0
    
    # Verify that concept names were extracted
    assert section.summary_names is not None
    assert isinstance(section.summary_names, list)
    assert len(section.summary_names) > 0
    
    print(f"Summary: {section.summary}")
    print(f"Concept names: {section.summary_names}")
    print("✓ Summarizer with mock client working correctly")


def test_summarizer_with_hierarchical_structure():
    """Test summarizer with nested structural elements."""
    print("Testing summarizer with hierarchical structure...")
    
    # Create nested structure
    subsection1 = LegalSection(
        id="http://example.com/section1_1",
        officialIdentifier="§ 1.1",
        title="Subsection 1",
        textContent="First subsection defines basic terms and concepts."
    )
    
    subsection2 = LegalSection(
        id="http://example.com/section1_2",
        officialIdentifier="§ 1.2",
        title="Subsection 2",
        textContent="Second subsection establishes compliance requirements and procedures."
    )
    
    main_section = LegalSection(
        id="http://example.com/section1",
        officialIdentifier="§ 1",
        title="Main Section",
        textContent="This main section contains important provisions.",
        elements=[subsection1, subsection2]
    )
    
    # Create summarizer and replace client with mock
    summarizer = LegislationSummarizer("gpt-4")
    summarizer.client = MockOpenAIClient("dummy-key")
    
    # Test the _summarize_element method
    summary = summarizer._summarize_element(main_section)
    
    # Verify that all elements have summaries and concept names
    assert main_section.summary is not None
    assert main_section.summary_names is not None
    assert subsection1.summary is not None
    assert subsection1.summary_names is not None
    assert subsection2.summary is not None
    assert subsection2.summary_names is not None
    
    print(f"Main section summary: {main_section.summary}")
    print(f"Main section concept names: {main_section.summary_names}")
    print("✓ Hierarchical structure summarization working correctly")


def test_concept_names_parsing():
    """Test that concept names are parsed correctly from LLM response."""
    print("Testing concept names parsing...")
    
    summarizer = LegislationSummarizer("gpt-4")
    summarizer.client = MockOpenAIClient("dummy-key")
    
    # Test the _extract_concept_names method directly
    test_text = "This is a legal text about obligations and penalties."
    concept_names = summarizer._extract_terms(test_text)
    
    # Verify that concepts were extracted and parsed
    assert isinstance(concept_names, list)
    assert len(concept_names) > 0
    
    # Expected concepts from our mock response
    expected_concepts = ["legal obligation", "compliace requirement", "penalty", "violation", "enforcement", "authority"]
    assert concept_names == expected_concepts
    
    print(f"Extracted concept names: {concept_names}")
    print("✓ Concept names parsing working correctly")


def test_empty_content_handling():
    """Test handling of elements with no content."""
    print("Testing empty content handling...")
    
    # Create element with no content
    empty_section = LegalSection(
        id="http://example.com/empty",
        officialIdentifier="§ Empty",
        title="Empty Section"
    )
    
    summarizer = LegislationSummarizer("gpt-4")
    summarizer.client = MockOpenAIClient("dummy-key")
    
    # Test summarization of empty element
    summary = summarizer._summarize_element(empty_section)
    
    # Verify handling of empty content
    assert empty_section.summary is not None
    assert "Summary of Empty Section" in empty_section.summary
    assert isinstance(empty_section.summary_names, list)
    
    print(f"Empty section summary: {empty_section.summary}")
    print(f"Empty section concept names: {empty_section.summary_names}")
    print("✓ Empty content handling working correctly")


def run_all_tests():
    """Run all test functions."""
    print("=" * 50)
    print("Running LegislationSummarizer Tests")
    print("=" * 50)
    
    test_functions = [
        test_summarizer_initialization,
        test_summarizer_with_mock_client,
        test_summarizer_with_hierarchical_structure,
        test_concept_names_parsing,
        test_empty_content_handling
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
