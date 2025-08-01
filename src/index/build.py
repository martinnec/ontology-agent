"""
CLI tool for building BM25 and other indexes from legal acts.

This module provides command-line interface for building search indexes
from legal act data retrieved via the legislation service.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path to allow imports
sys.path.append(str(Path(__file__).parent.parent))

from index.bm25 import BM25SummaryIndex
from index.builder import DocumentExtractor
from index.domain import IndexDoc

# Import will be conditional since we might not have legislation service configured
try:
    from legislation.service import LegislationService
    from legislation.datasource_esel import EselDataSource
    LEGISLATION_AVAILABLE = True
except ImportError:
    LEGISLATION_AVAILABLE = False


def build_bm25_index(act_iri: str, 
                    output_dir: str,
                    llm_model: str = "gpt-3.5-turbo") -> None:
    """
    Build BM25 summary index for a legal act.
    
    Args:
        act_iri: IRI of the legal act to index
        output_dir: Directory to save the index
        llm_model: LLM model identifier for summarization
    """
    print(f"Building BM25 index for legal act: {act_iri}")
    
    if not LEGISLATION_AVAILABLE:
        print("ERROR: Legislation module not available.")
        print("Cannot retrieve legal act data.")
        return
    
    try:
        # Initialize legislation service
        print("Initializing legislation service...")
        datasource = EselDataSource()
        service = LegislationService(datasource, llm_model)
        
        # Retrieve legal act
        print("Retrieving legal act...")
        legal_act = service.get_legal_act(act_iri)
        print(f"Retrieved: {legal_act.title}")
        
        # Extract documents
        print("Extracting documents for indexing...")
        documents = DocumentExtractor.extract_from_act(
            legal_act=legal_act,
            act_iri=act_iri,
            snapshot_id="manual-build"
        )
        print(f"Extracted {len(documents)} documents")
        
        # Show document statistics
        stats = DocumentExtractor.get_document_stats(documents)
        print(f"Document statistics:")
        print(f"  - Total: {stats['total_count']}")
        print(f"  - With summaries: {stats['with_summary']}")
        print(f"  - With content: {stats['with_content']}")
        print(f"  - By type: {dict(stats['by_type'])}")
        
        # Filter documents with summaries for indexing
        indexable_docs = DocumentExtractor.filter_documents(
            documents, has_summary=True
        )
        print(f"Indexable documents (with summaries): {len(indexable_docs)}")
        
        if not indexable_docs:
            print("WARNING: No documents with summaries found. Index will be empty.")
            return
        
        # Build BM25 index
        print("Building BM25 index...")
        index = BM25SummaryIndex()
        index.build(indexable_docs)
        
        # Save index
        print(f"Saving index to: {output_dir}")
        index.save(output_dir)
        
        # Show index statistics
        index_stats = index.get_stats()
        print(f"Index statistics:")
        print(f"  - Documents: {index_stats['document_count']}")
        print(f"  - Vocabulary size: {index_stats['vocabulary_size']}")
        print(f"  - Total tokens: {index_stats['total_tokens']}")
        print(f"  - Avg doc length: {index_stats['average_document_length']:.1f}")
        
        print("✓ BM25 index built successfully!")
        
    except Exception as e:
        print(f"ERROR building index: {e}")
        raise


def build_with_mock_data(output_dir: str) -> None:
    """
    Build BM25 index with mock data for testing.
    
    Args:
        output_dir: Directory to save the index
    """
    print("Building BM25 index with mock data...")
    
    # Create mock documents
    mock_docs = [
        IndexDoc(
            element_id="http://example.org/act/1",
            title="Zákon o ochraně osobních údajů",
            official_identifier="Zákon č. 110/2019 Sb.",
            summary="Zákon upravuje ochranu osobních údajů fyzických osob a stanoví práva a povinnosti při zpracování osobních údajů.",
            level=0,
            element_type="act",
            act_iri="http://example.org/act/1"
        ),
        IndexDoc(
            element_id="http://example.org/act/1/section/1",
            title="Základní pojmy",
            official_identifier="§ 1",
            summary="Definice základních pojmů používaných v zákoně o ochraně osobních údajů, včetně definice osobních údajů, zpracování a správce.",
            level=1,
            element_type="section",
            act_iri="http://example.org/act/1"
        ),
        IndexDoc(
            element_id="http://example.org/act/1/section/2",
            title="Předmět úpravy",
            official_identifier="§ 2", 
            summary="Vymezení předmětu úpravy zákona, který se vztahuje na zpracování osobních údajů fyzických osob.",
            level=1,
            element_type="section",
            act_iri="http://example.org/act/1"
        ),
        IndexDoc(
            element_id="http://example.org/act/1/section/3",
            title="Práva subjektů údajů",
            official_identifier="§ 3",
            summary="Ustanovení o právech fyzických osob, jejichž osobní údaje jsou zpracovávány, včetně práva na informace a opravu.",
            level=1,
            element_type="section",
            act_iri="http://example.org/act/1"
        ),
        IndexDoc(
            element_id="http://example.org/act/1/section/4",
            title="Povinnosti správců",
            official_identifier="§ 4",
            summary="Povinnosti správců osobních údajů při zpracování, včetně zajištění bezpečnosti a oznámení porušení.",
            level=1,
            element_type="section",
            act_iri="http://example.org/act/1"
        )
    ]
    
    print(f"Created {len(mock_docs)} mock documents")
    
    # Build index
    print("Building BM25 index...")
    index = BM25SummaryIndex()
    index.build(mock_docs)
    
    # Save index
    print(f"Saving index to: {output_dir}")
    index.save(output_dir)
    
    # Show statistics
    stats = index.get_stats()
    print(f"Index statistics:")
    print(f"  - Documents: {stats['document_count']}")
    print(f"  - Vocabulary size: {stats['vocabulary_size']}")
    print(f"  - Total tokens: {stats['total_tokens']}")
    print(f"  - Avg doc length: {stats['average_document_length']:.1f}")
    
    print("✓ Mock BM25 index built successfully!")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Build BM25 search index for legal acts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Build index for a specific legal act
  python -m index.build http://example.org/act/1 --output ./indexes/act1
  
  # Build with mock data for testing
  python -m index.build --mock --output ./indexes/mock
  
  # Build with custom LLM model
  python -m index.build http://example.org/act/1 --output ./indexes/act1 --llm-model gpt-4
        """)
    
    parser.add_argument("act_iri", nargs="?", 
                       help="IRI of the legal act to index")
    parser.add_argument("--output", "-o", required=True,
                       help="Output directory for the index")
    parser.add_argument("--llm-model", default="gpt-3.5-turbo",
                       help="LLM model for summarization (default: gpt-3.5-turbo)")
    parser.add_argument("--mock", action="store_true",
                       help="Build index with mock data instead of real legal act")
    
    args = parser.parse_args()
    
    if args.mock:
        if args.act_iri:
            print("WARNING: --mock flag provided, ignoring act_iri argument")
        build_with_mock_data(args.output)
    else:
        if not args.act_iri:
            print("ERROR: act_iri is required when not using --mock")
            parser.print_help()
            sys.exit(1)
        build_bm25_index(args.act_iri, args.output, args.llm_model)


if __name__ == "__main__":
    main()
