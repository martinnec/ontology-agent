"""
Test for the corrected hierarchical chunking strategy.
This test verifies that the chunking correctly handles:
1. Plain text (fallback to simple chunking)
2. Hierarchical XML (leaf sequences with full ancestral context)

HOW TO RUN:
From the src directory, run:
    python -m index.test_hierarchical_chunking

The test demonstrates the correct behavior on § 61.
"""

import os
import json
from pathlib import Path

# Set environment for testing
os.environ["OPENAI_API_KEY"] = "dummy-for-testing"

from .domain import IndexDoc

def load_section_61():
    """Load § 61 from the legal act data."""
    current_dir = Path(__file__).parent
    data_dir = current_dir.parent.parent / "data" / "legal_acts"
    legal_act_file = data_dir / "56-2001-2025-07-01.json"
    
    if not legal_act_file.exists():
        return None
    
    with open(legal_act_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Find § 61 (the first one, not § 61a)
    def find_section_61(obj):
        if isinstance(obj, dict):
            if (obj.get('officialIdentifier') == '§ 61' and 
                obj.get('title') == '§ 61'):
                return obj
            for value in obj.values():
                if isinstance(value, (dict, list)):
                    result = find_section_61(value)
                    if result:
                        return result
        elif isinstance(obj, list):
            for item in obj:
                if isinstance(item, (dict, list)):
                    result = find_section_61(item)
                    if result:
                        return result
        return None
    
    return find_section_61(data)

def test_hierarchical_structure():
    """Test that hierarchical XML is correctly parsed into leaf sequences."""
    print("Testing hierarchical structure parsing...")
    
    # Create a simple hierarchical XML example
    hierarchical_xml = '''<f id="root_par_61">
        § 61
        <f id="root_par_61_odst_1">
            (1) Professional certificate text
        </f>
        <f id="root_par_61_odst_2">
            (2) Ministry extends validity
            <f id="root_par_61_odst_2_pism_a">
                a) completed course
            </f>
            <f id="root_par_61_odst_2_pism_b">
                b) meets conditions
            </f>
        </f>
    </f>'''
    
    doc = IndexDoc(
        element_id="test_hierarchical",
        title="Test Hierarchical",
        official_identifier="test-hier-1",
        element_type="section",
        text_content=hierarchical_xml,
        summary="Test hierarchical structure"
    )
    
    # Extract leaf sequences
    leaf_sequences = doc._extract_leaf_sequences_from_xml(hierarchical_xml)
    
    print(f"Found {len(leaf_sequences)} leaf sequences")
    
    for i, seq in enumerate(leaf_sequences):
        print(f"\n--- Leaf Sequence {i+1} ---")
        print(f"Text: {seq['text']}")
        print(f"Fragment IDs: {[id.split('/')[-1] for id in seq['fragment_ids']]}")
        print(f"Depth: {seq['depth']}")
        print(f"Leaf context: {seq['leaf_context']}")
    
    # Should have 3 leaf sequences:
    # 1. § 61 (1) Professional certificate text
    # 2. § 61 (2) Ministry extends validity a) completed course  
    # 3. § 61 (2) Ministry extends validity b) meets conditions
    expected_sequences = 3
    assert len(leaf_sequences) == expected_sequences, f"Expected {expected_sequences} sequences, got {len(leaf_sequences)}"
    
    # Each sequence should contain full ancestral context
    for seq in leaf_sequences:
        assert "§ 61" in seq['text'], "Each sequence should contain root text"
        assert len(seq['fragment_ids']) >= 2, "Each sequence should have at least 2 fragment IDs"
    
    print("✓ Hierarchical structure parsing working correctly")

def test_plain_text_fallback():
    """Test that plain text falls back to simple chunking."""
    print("Testing plain text fallback...")
    
    plain_text = "This is just plain text without any XML structure. It should use simple chunking strategy."
    
    doc = IndexDoc(
        element_id="test_plain",
        title="Test Plain Text",
        official_identifier="test-plain-1", 
        element_type="section",
        text_content=plain_text,
        summary="Test plain text"
    )
    
    chunks = doc.get_text_chunks(chunk_size=10, overlap=2)
    
    print(f"Generated {len(chunks)} chunks from plain text")
    
    # Should use simple chunking
    assert len(chunks) > 0, "Should generate chunks"
    assert chunks[0]['fragment_contexts'] == ['simple_text'], "Should use simple text strategy"
    assert chunks[0]['fragment_ids'] == [], "Should have no fragment IDs"
    
    print("✓ Plain text fallback working correctly")

def test_real_section_61():
    """Test the corrected chunking on real § 61 data."""
    print("Testing corrected chunking on real § 61...")
    
    section_61 = load_section_61()
    if not section_61:
        print("! Skipping real data test - § 61 not found")
        return
    
    doc = IndexDoc(
        element_id=section_61['id'],
        title=section_61.get('title', '§ 61'),
        official_identifier=section_61.get('officialIdentifier', '§ 61'),
        element_type="section",
        text_content=section_61['textContent'],
        summary=section_61.get('summary', '')
    )
    
    # Test leaf sequence extraction
    leaf_sequences = doc._extract_leaf_sequences_from_xml(section_61['textContent'])
    print(f"Found {len(leaf_sequences)} leaf sequences")
    
    # Test chunking
    chunks = doc.get_text_chunks(chunk_size=100, overlap=20)
    print(f"Generated {len(chunks)} chunks")
    
    if leaf_sequences:
        print(f"\nFirst few leaf sequences:")
        for i, seq in enumerate(leaf_sequences[:3]):
            print(f"\nSequence {i+1}:")
            print(f"  Text (first 100 chars): {seq['text'][:100]}...")
            print(f"  Fragment path: {' → '.join(seq['fragment_contexts'])}")
            print(f"  Depth: {seq['depth']}")
    
    if chunks:
        print(f"\nFirst few chunks:")
        for i, chunk in enumerate(chunks[:3]):
            print(f"\nChunk {i+1}:")
            print(f"  Text (first 100 chars): {chunk['text'][:100]}...")
            print(f"  Fragment IDs count: {len(chunk.get('fragment_ids', []))}")
            print(f"  Leaf context: {chunk.get('leaf_fragment_context', 'N/A')}")
            print(f"  Sequence index: {chunk.get('sequence_index', 'N/A')}")
    
    assert len(chunks) > 0, "Should generate chunks"
    print("✓ Real § 61 chunking working correctly")

def test_hierarchical_vs_old_strategy():
    """Compare the new hierarchical strategy with the old approach."""
    print("Comparing new hierarchical vs old fragment-based strategy...")
    
    section_61 = load_section_61()
    if not section_61:
        print("! Skipping comparison - § 61 not found")
        return
    
    doc = IndexDoc(
        element_id=section_61['id'],
        title=section_61.get('title', '§ 61'),
        official_identifier=section_61.get('officialIdentifier', '§ 61'),
        element_type="section",
        text_content=section_61['textContent'],
        summary=section_61.get('summary', '')
    )
    
    # New hierarchical approach
    leaf_sequences = doc._extract_leaf_sequences_from_xml(section_61['textContent'])
    hierarchical_chunks = doc.get_text_chunks(chunk_size=100, overlap=20)
    
    # Old fragment-based approach (simulate)
    old_chunks = doc._create_simple_text_chunks(section_61['textContent'], 100, 20)
    
    print(f"\n📊 Comparison Results:")
    print(f"   🆕 New hierarchical: {len(hierarchical_chunks)} chunks from {len(leaf_sequences)} sequences")
    print(f"   🗂️ Old simple: {len(old_chunks)} chunks")
    
    if hierarchical_chunks:
        has_fragment_ids = sum(1 for c in hierarchical_chunks if c.get('fragment_ids'))
        print(f"   🏷️ Chunks with fragment IDs: {has_fragment_ids}/{len(hierarchical_chunks)}")
        
        # Show structure of first chunk
        first_chunk = hierarchical_chunks[0]
        if first_chunk.get('fragment_ids'):
            print(f"   📍 First chunk fragment path: {len(first_chunk['fragment_ids'])} levels")
            print(f"   📄 First chunk text preview: {first_chunk['text'][:100]}...")
    
    print("✓ Hierarchical strategy comparison completed")

def run_all_tests():
    """Run all test functions."""
    print("=" * 60)
    print("Running Corrected Hierarchical Chunking Tests")
    print("=" * 60)
    
    test_functions = [
        test_hierarchical_structure,
        test_plain_text_fallback,
        test_real_section_61,
        test_hierarchical_vs_old_strategy
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
