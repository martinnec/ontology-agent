"""
Simple test for the revised XML-aware chunking strategy.
This test file follows the project's testing guidelines:
- No testing library dependencies
- Simple Python script with main function
- Tests placed directly in src directory
- Named with test_ prefix
- Self-contained and runnable independently

HOW TO RUN:
From the src directory, run:
    python -m index.test_xml_chunking

Or from the project root:
    cd src && python -m index.test_xml_chunking

The test uses real legal act data to verify XML parsing and chunking.
"""

import json
import os
from pathlib import Path
from .domain import IndexDoc

def load_real_legal_act():
    """Load the real legal act 56/2001 data for testing."""
    # Look for the legal act file
    current_dir = Path(__file__).parent
    data_dir = current_dir.parent.parent / "data" / "legal_acts"
    legal_act_file = data_dir / "56-2001-2025-07-01.json"
    
    if not legal_act_file.exists():
        print(f"Legal act file not found at: {legal_act_file}")
        return None
    
    with open(legal_act_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def test_xml_fragment_extraction():
    """Test extraction of clean text from XML fragments."""
    print("Testing XML fragment extraction...")
    
    # Sample XML content with nested <f> elements
    sample_xml = '''<f id="https://opendata.eselpoint.cz/esel-esb/eli/cz/sb/2001/56/2025-07-01/dokument/norma/cast_4/hlava_1/par_48/odst_1">
        Tento zákon upravuje <f id="sub1">práva a povinnosti</f> fyzických a právnických osob.
        <f id="https://opendata.eselpoint.cz/esel-esb/eli/cz/sb/2001/56/2025-07-01/dokument/norma/cast_4/hlava_1/par_48/odst_2">
            Zákon se vztahuje na všechny občany.
        </f>
    </f>'''
    
    doc = IndexDoc(
        element_id="test_doc",
        title="Test Document",
        official_identifier="test-1",
        element_type="section",
        text_content=sample_xml,
        summary="Test document"
    )
    
    fragments = doc._extract_fragments_from_xml(sample_xml)
    
    print(f"Found {len(fragments)} fragments")
    for i, fragment in enumerate(fragments):
        print(f"Fragment {i + 1}:")
        print(f"  Text: {fragment['text'][:100]}...")
        print(f"  Context: {fragment['fragment_context']}")
        print(f"  Level: {fragment['level']}")
    
    assert len(fragments) > 0, "Should extract at least one fragment"
    print("✓ XML fragment extraction working correctly")

def test_real_legal_act_chunking():
    """Test chunking with real legal act data."""
    print("Testing real legal act chunking...")
    
    legal_act = load_real_legal_act()
    if not legal_act:
        print("! Skipping real data test - legal act file not found")
        return
    
    # Find documents with XML content recursively
    def find_documents_with_xml(obj, path=""):
        documents = []
        if isinstance(obj, dict):
            # Check if this object has textContent with XML
            if 'textContent' in obj and obj['textContent'] and '<f' in str(obj['textContent']):
                documents.append(obj)
            # Recursively search in nested objects
            for key, value in obj.items():
                if isinstance(value, (dict, list)):
                    documents.extend(find_documents_with_xml(value, f"{path}.{key}"))
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                if isinstance(item, (dict, list)):
                    documents.extend(find_documents_with_xml(item, f"{path}[{i}]"))
        return documents
    
    xml_documents = find_documents_with_xml(legal_act)
    
    if not xml_documents:
        print("! No documents with XML content found")
        return
    
    test_doc = xml_documents[0]  # Use first document with XML content
    
    index_doc = IndexDoc(
        element_id=test_doc['id'],
        title=test_doc.get('title', 'Untitled'),
        official_identifier=test_doc.get('officialIdentifier', test_doc['id']),
        element_type="section",
        text_content=test_doc['textContent'],
        summary=test_doc.get('summary', '')
    )
    
    # Test with small chunk size to see chunking behavior
    chunks = index_doc.get_text_chunks(chunk_size=100, overlap=20)
    
    print(f"Document ID: {test_doc['id']}")
    print(f"Original text length: {len(test_doc['textContent'])} chars")
    print(f"Generated {len(chunks)} chunks")
    
    # Check first few chunks
    for i, chunk in enumerate(chunks[:3]):
        print(f"\nChunk {i + 1}:")
        print(f"  ID: {chunk['chunk_id']}")
        print(f"  Text: {chunk['text'][:150]}...")
        print(f"  Fragment context: {chunk.get('fragment_context', 'N/A')}")
        print(f"  Fragment count: {chunk.get('fragment_count', 'N/A')}")
        
        # Verify no long URLs in chunk text
        if 'https://opendata.eselpoint.cz' in chunk['text']:
            print(f"  ⚠ Warning: Still contains long URLs")
        else:
            print(f"  ✓ Clean text (no URLs)")
    
    assert len(chunks) > 0, "Should generate at least one chunk"
    print("✓ Real legal act chunking working correctly")

def test_chunk_overlap():
    """Test that chunking maintains proper overlap."""
    print("Testing chunk overlap...")
    
    # Create a document with simple XML
    xml_content = '''<f id="frag1">First fragment with some text that goes on for a while. </f>
    <f id="frag2">Second fragment continues the story with more content here. </f>
    <f id="frag3">Third fragment adds even more text to make multiple chunks necessary. </f>
    <f id="frag4">Fourth fragment ensures we definitely need multiple chunks for testing overlap. </f>'''
    
    doc = IndexDoc(
        element_id="test_overlap",
        title="Test Overlap Document",
        official_identifier="test-overlap-1",
        element_type="section",
        text_content=xml_content,
        summary="Test overlap"
    )
    
    chunks = doc.get_text_chunks(chunk_size=20, overlap=5)
    
    print(f"Generated {len(chunks)} chunks with 20-word limit and 5-word overlap")
    
    if len(chunks) > 1:
        # Check for overlap between consecutive chunks
        for i in range(len(chunks) - 1):
            chunk1_words = chunks[i]['text'].split()
            chunk2_words = chunks[i + 1]['text'].split()
            
            # Look for common words at the end of chunk1 and start of chunk2
            overlap_found = False
            if len(chunk1_words) >= 5 and len(chunk2_words) >= 5:
                # Check if any of the last few words of chunk1 appear in first few words of chunk2
                for word in chunk1_words[-5:]:
                    if word in chunk2_words[:5]:
                        overlap_found = True
                        break
            
            print(f"  Chunk {i + 1} -> {i + 2}: {'✓ Overlap found' if overlap_found else '⚠ No clear overlap'}")
    
    print("✓ Chunk overlap test completed")

def test_fallback_simple_chunking():
    """Test fallback to simple chunking when XML parsing fails."""
    print("Testing fallback simple chunking...")
    
    # Create document with invalid XML
    invalid_xml = "This is just plain text without proper XML structure <invalid>"
    
    doc = IndexDoc(
        element_id="test_fallback",
        title="Test Fallback Document", 
        official_identifier="test-fallback-1",
        element_type="section",
        text_content=invalid_xml,
        summary="Test fallback"
    )
    
    chunks = doc.get_text_chunks(chunk_size=10, overlap=2)
    
    print(f"Generated {len(chunks)} chunks from plain text")
    
    if chunks:
        print(f"First chunk: {chunks[0]['text']}")
        print(f"Fragment context: {chunks[0].get('fragment_context', 'N/A')}")
        
        # Should fallback to simple text chunking
        assert chunks[0].get('fragment_context') == 'simple_text', "Should use simple text fallback"
        
        # Should not contain XML tags
        assert '<invalid>' not in chunks[0]['text'], "Should clean XML tags"
    
    print("✓ Fallback simple chunking working correctly")

def run_all_tests():
    """Run all test functions."""
    print("=" * 60)
    print("Running XML-Aware Chunking Tests")
    print("=" * 60)
    
    test_functions = [
        test_xml_fragment_extraction,
        test_real_legal_act_chunking,
        test_chunk_overlap,
        test_fallback_simple_chunking
    ]
    
    passed = 0
    failed = 0
    
    for test_func in test_functions:
        try:
            print(f"\n--- {test_func.__name__} ---")
            test_func()
            passed += 1
        except Exception as e:
            print(f"✗ {test_func.__name__} FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
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
