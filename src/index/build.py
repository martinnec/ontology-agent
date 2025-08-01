#!/usr/bin/env python3
"""
CLI tool for building BM25 and FAISS indexes from legal acts.

This script provides functionality to:
1. Build BM25 keyword-based index
2. Build FAISS semantic index  
3. Build both indexes simultaneously
4. Support mock data for testing

Usage:
    python -m index.build --type bm25 --output-dir ./indexes
    python -m index.build --type faiss --output-dir ./indexes
    python -m index.build --type both --output-dir ./indexes
    python -m index.build --mock --type both --output-dir ./test_indexes
"""

import argparse
import os
import sys
from pathlib import Path
from typing import List

# Add the src directory to the path so we can import from other modules
src_dir = Path(__file__).parent.parent
sys.path.insert(0, str(src_dir))

from index.domain import IndexDoc, ElementType, IndexMetadata
from index.bm25 import BM25SummaryIndex
from index.faiss_index import FAISSSummaryIndex

# Optional imports for legislation service
try:
    from legislation.service import LegislationService
    from legislation.datasource_esel import EselDatasource
    LEGISLATION_AVAILABLE = True
except ImportError:
    LEGISLATION_AVAILABLE = False
    print("Warning: Legislation service not available. Use --mock for testing.")


def create_mock_documents() -> List[IndexDoc]:
    """Create mock documents for testing purposes."""
    return [
        IndexDoc(
            element_id="mock_1",
            title="Základní ustanovení",
            official_identifier="§ 1",
            summary="Tento zákon upravuje základní pravidla a postupy pro správu a ochranu osobních údajů v České republice.",
            summary_names=["osobní údaje", "ochrana", "správa"],
            level=1,
            element_type=ElementType.SECTION,
            act_iri="http://example.org/act/mock"
        ),
        IndexDoc(
            element_id="mock_2",
            title="Definice pojmů",
            official_identifier="§ 2",
            summary="Pro účely tohoto zákona se rozumí osobními údaji veškeré informace o identifikované nebo identifikovatelné fyzické osobě.",
            summary_names=["definice", "osobní údaje", "fyzická osoba"],
            level=1,
            element_type=ElementType.SECTION,
            act_iri="http://example.org/act/mock"
        ),
        IndexDoc(
            element_id="mock_3",
            title="Práva subjektů údajů",
            official_identifier="§ 3",
            summary="Subjekt údajů má právo na přístup ke svým osobním údajům, jejich opravu, výmaz nebo omezení zpracování.",
            summary_names=["práva subjektů", "přístup", "oprava", "výmaz"],
            level=1,
            element_type=ElementType.SECTION,
            act_iri="http://example.org/act/mock"
        ),
        IndexDoc(
            element_id="mock_4",
            title="Povinnosti správce",
            official_identifier="§ 4",
            summary="Správce osobních údajů je povinen zajistit odpovídající technická a organizační opatření k ochraně údajů.",
            summary_names=["povinnosti správce", "technická opatření", "organizační opatření"],
            level=1,
            element_type=ElementType.SECTION,
            act_iri="http://example.org/act/mock"
        ),
        IndexDoc(
            element_id="mock_5",
            title="Sankce",
            official_identifier="§ 5",
            summary="Za porušení povinností stanovených tímto zákonem lze uložit pokutu až do výše 20 milionů EUR.",
            summary_names=["sankce", "pokuta", "porušení povinností"],
            level=1,
            element_type=ElementType.SECTION,
            act_iri="http://example.org/act/mock"
        )
    ]


def get_documents_from_service() -> List[IndexDoc]:
    """Get documents from the legislation service."""
    if not LEGISLATION_AVAILABLE:
        raise RuntimeError("Legislation service not available. Use --mock option.")
    
    print("Loading documents from legislation service...")
    datasource = EselDatasource()
    service = LegislationService(datasource)
    
    # Get all legal acts and extract documents
    acts = service.get_legal_acts()
    print(f"Found {len(acts)} legal acts")
    
    all_documents = []
    for act in acts:
        # Get the full act with all elements
        full_act = service.get_legal_act(act.iri)
        if full_act and full_act.elements:
            documents = service.create_index_documents(full_act)
            all_documents.extend(documents)
            print(f"Processed {len(documents)} documents from {act.identifier}")
    
    print(f"Total documents loaded: {len(all_documents)}")
    return all_documents


def build_bm25_index(documents: List[IndexDoc], output_dir: str) -> None:
    """Build BM25 index from documents."""
    print(f"\nBuilding BM25 index with {len(documents)} documents...")
    
    # Create and build index
    index = BM25SummaryIndex()
    index.build(documents)
    
    # Save index
    bm25_dir = Path(output_dir) / "bm25"
    bm25_dir.mkdir(parents=True, exist_ok=True)
    index.save(str(bm25_dir))
    
    print(f"BM25 index saved to {bm25_dir}")
    
    # Print statistics
    stats = index.get_stats()
    print(f"BM25 Index Statistics:")
    print(f"  - Documents: {stats.get('document_count', 0)}")
    print(f"  - Vocabulary size: {stats.get('vocabulary_size', 0)}")
    print(f"  - Average document length: {stats.get('avg_doc_length', 0):.2f}")


def build_faiss_index(documents: List[IndexDoc], output_dir: str) -> None:
    """Build FAISS index from documents."""
    print(f"\nBuilding FAISS semantic index with {len(documents)} documents...")
    
    # Create and build index
    index = FAISSSummaryIndex()
    index.build(documents)
    
    # Save index
    faiss_dir = Path(output_dir) / "faiss"
    faiss_dir.mkdir(parents=True, exist_ok=True)
    index.save(str(faiss_dir))
    
    print(f"FAISS index saved to {faiss_dir}")
    
    # Print statistics
    stats = index.get_stats()
    print(f"FAISS Index Statistics:")
    print(f"  - Documents: {stats.get('document_count', 0)}")
    print(f"  - Embedding dimension: {stats.get('embedding_dimension', 0)}")
    print(f"  - Valid embeddings: {stats.get('valid_embeddings', 0)}")


def build_both_indexes(documents: List[IndexDoc], output_dir: str) -> None:
    """Build both BM25 and FAISS indexes."""
    print(f"\nBuilding both indexes with {len(documents)} documents...")
    
    # Build BM25 index
    build_bm25_index(documents, output_dir)
    
    # Build FAISS index
    build_faiss_index(documents, output_dir)
    
    print(f"\nBoth indexes built successfully in {output_dir}")


def build_with_mock_data(index_type: str, output_dir: str) -> None:
    """Build indexes using mock data for testing."""
    print("Using mock data for testing...")
    documents = create_mock_documents()
    
    if index_type == "bm25":
        build_bm25_index(documents, output_dir)
    elif index_type == "faiss":
        build_faiss_index(documents, output_dir)
    elif index_type == "both":
        build_both_indexes(documents, output_dir)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Build BM25 and/or FAISS indexes from legal acts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Build BM25 index from real data
  python -m index.build --type bm25 --output-dir ./indexes
  
  # Build FAISS index from real data
  python -m index.build --type faiss --output-dir ./indexes
  
  # Build both indexes from real data
  python -m index.build --type both --output-dir ./indexes
  
  # Build with mock data for testing
  python -m index.build --mock --type both --output-dir ./test_indexes
  
  # Build from specific legal act file
  python -m index.build --type both --output-dir ./indexes --input-file data/legal_acts/56-2001-2025-07-01.json
        """
    )
    
    parser.add_argument(
        "--type",
        choices=["bm25", "faiss", "both"],
        default="both",
        help="Type of index to build (default: both)"
    )
    
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory where to save the built indexes"
    )
    
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock data instead of real legislation data"
    )
    
    parser.add_argument(
        "--input-file",
        help="Path to a specific legal act JSON file to index"
    )
    
    parser.add_argument(
        "--embedding-model",
        default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        help="Sentence transformer model for FAISS embeddings"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.input_file and args.mock:
        parser.error("Cannot use both --input-file and --mock options")
    
    try:
        # Get documents
        if args.mock:
            print("Building indexes with mock data...")
            documents = create_mock_documents()
        elif args.input_file:
            print(f"Building indexes from file: {args.input_file}")
            # TODO: Add support for loading from specific file
            if not LEGISLATION_AVAILABLE:
                raise RuntimeError("Legislation service required for file input. Use --mock instead.")
            documents = get_documents_from_service()  # For now, use service
        else:
            print("Building indexes from legislation service...")
            documents = get_documents_from_service()
        
        if not documents:
            print("Error: No documents found to index")
            return 1
        
        # Create output directory
        output_path = Path(args.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Build indexes based on type
        if args.type == "bm25":
            build_bm25_index(documents, args.output_dir)
        elif args.type == "faiss":
            # Configure embedding model if building FAISS
            original_model = None
            if hasattr(FAISSSummaryIndex, '_default_model'):
                original_model = FAISSSummaryIndex._default_model
            
            # This is a bit hacky, but allows customizing the model
            FAISSSummaryIndex._default_model = args.embedding_model
            
            try:
                build_faiss_index(documents, args.output_dir)
            finally:
                # Restore original model
                if original_model:
                    FAISSSummaryIndex._default_model = original_model
        elif args.type == "both":
            build_both_indexes(documents, args.output_dir)
        
        print("\n✅ Index building completed successfully!")
        return 0
        
    except Exception as e:
        print(f"\n❌ Error building indexes: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
