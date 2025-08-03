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
from index.bm25_full import BM25FullIndex
from index.faiss_full import FAISSFullIndex

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
            text_content="Tento zákon upravuje základní pravidla a postupy pro správu a ochranu osobních údajů v České republice. Pod pojmem osobní údaje se rozumí veškeré informace o identifikované nebo identifikovatelné fyzické osobě. Zpracování osobních údajů musí být v souladu s právními předpisy a musí respektovat práva subjektů údajů.",
            level=1,
            element_type=ElementType.SECTION,
            act_iri="http://example.org/act/mock"
        ),
        IndexDoc(
            element_id="mock_2", 
            title="Práva subjektů údajů",
            official_identifier="§ 2",
            summary="Kapitola definuje práva fyzických osob při zpracování jejich osobních údajů, včetně práva na informace a přístup.",
            summary_names=["práva subjektů", "přístup k údajům", "informace"],
            text_content="Subjekt údajů má právo na informace o zpracování svých osobních údajů. Subjekt údajů má právo na přístup ke svým osobním údajům. Je povinen správce poskytnout subjektu údajů informace o účelech zpracování, kategorii osobních údajů a době uchování.",
            level=1,
            element_type=ElementType.SECTION,
            act_iri="http://example.org/act/mock"
        ),
        IndexDoc(
            element_id="mock_3",
            title="Povinnosti správce",
            official_identifier="§ 3", 
            summary="Ustanovení stanoví základní povinnosti správce osobních údajů při jejich zpracování a ochraně.",
            summary_names=["povinnosti správce", "zpracování údajů", "bezpečnost"],
            text_content="Správce je povinen zajistit bezpečnost zpracování osobních údajů. Správce musí implementovat vhodná technická a organizační opatření. Správce je povinen vést evidenci zpracovatelských činností a musí být schopen prokázat soulad s právními předpisy.",
            level=1,
            element_type=ElementType.SECTION,
            act_iri="http://example.org/act/mock"
        ),
        IndexDoc(
            element_id="mock_4",
            title="Přestupky a sankce",
            official_identifier="§ 4",
            summary="Vymezení přestupků proti ochraně osobních údajů a stanovení sankcí za jejich porušení.",
            summary_names=["přestupky", "sankce", "porušení"],
            text_content="Přestupku se dopustí ten, kdo poruší povinnosti stanovené tímto zákonem. Za přestupek lze uložit pokutu až do výše 10 000 000 Kč. Přestupky projednávají správní orgány podle zvláštních právních předpisů.",
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


def build_bm25_full_index(documents: List[IndexDoc], output_dir: str) -> None:
    """Build BM25 full-text index from documents."""
    print(f"\nBuilding BM25 full-text index with {len(documents)} documents...")
    
    # Filter documents that have text content
    docs_with_content = [doc for doc in documents if doc.text_content]
    if not docs_with_content:
        print("Warning: No documents with text content found for full-text indexing")
        return
    
    print(f"Found {len(docs_with_content)} documents with text content")
    
    # Create and build index
    index = BM25FullIndex()
    index.build(docs_with_content)
    
    # Save index
    bm25_full_dir = Path(output_dir) / "bm25_full"
    bm25_full_dir.mkdir(parents=True, exist_ok=True)
    index.save(bm25_full_dir)
    
    print(f"BM25 full-text index saved to {bm25_full_dir}")
    
    # Print statistics
    if index.metadata:
        print(f"BM25 Full-Text Index Statistics:")
        print(f"  - Source documents: {index.metadata.metadata.get('source_documents', 0)}")
        print(f"  - Total chunks: {index.metadata.metadata.get('total_chunks', 0)}")
        print(f"  - Chunk size: {index.metadata.metadata.get('chunk_size', 0)} words")
        print(f"  - Chunk overlap: {index.metadata.metadata.get('chunk_overlap', 0)} words")


def build_faiss_full_index(documents: List[IndexDoc], output_dir: str) -> None:
    """Build FAISS full-text index from documents."""
    print(f"\nBuilding FAISS full-text semantic index with {len(documents)} documents...")
    
    # Filter documents that have text content
    docs_with_content = [doc for doc in documents if doc.text_content]
    if not docs_with_content:
        print("Warning: No documents with text content found for full-text indexing")
        return
    
    print(f"Found {len(docs_with_content)} documents with text content")
    
    # Create and build index
    index = FAISSFullIndex()
    index.build(docs_with_content)
    
    # Save index
    faiss_full_dir = Path(output_dir) / "faiss_full"
    faiss_full_dir.mkdir(parents=True, exist_ok=True)
    index.save(faiss_full_dir)
    
    print(f"FAISS full-text index saved to {faiss_full_dir}")
    
    # Print statistics
    if index.metadata:
        print(f"FAISS Full-Text Index Statistics:")
        print(f"  - Source documents: {index.metadata.metadata.get('source_documents', 0)}")
        print(f"  - Total chunks: {index.metadata.metadata.get('total_chunks', 0)}")
        print(f"  - Embedding dimension: {index.metadata.metadata.get('embedding_dimension', 0)}")
        print(f"  - Chunk size: {index.metadata.metadata.get('chunk_size', 0)} words")


def build_full_text_indexes(documents: List[IndexDoc], output_dir: str) -> None:
    """Build both BM25 and FAISS full-text indexes."""
    print(f"\nBuilding both full-text indexes with {len(documents)} documents...")
    
    # Build BM25 full-text index
    build_bm25_full_index(documents, output_dir)
    
    # Build FAISS full-text index
    build_faiss_full_index(documents, output_dir)
    
    print(f"\nBoth full-text indexes built successfully in {output_dir}")


def build_all_indexes(documents: List[IndexDoc], output_dir: str) -> None:
    """Build all indexes: summary and full-text."""
    print(f"\nBuilding all indexes (summary + full-text) with {len(documents)} documents...")
    
    # Build summary indexes
    build_both_indexes(documents, output_dir)
    
    # Build full-text indexes
    build_full_text_indexes(documents, output_dir)
    
    print(f"\nAll indexes built successfully in {output_dir}")


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
        choices=["bm25", "faiss", "both", "bm25_full", "faiss_full", "full_text", "all"],
        default="both",
        help="Type of index to build: bm25 (summary), faiss (summary), both (summary), bm25_full, faiss_full, full_text (both full), all (summary+full)"
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
        elif args.type == "bm25_full":
            build_bm25_full_index(documents, args.output_dir)
        elif args.type == "faiss_full":
            build_faiss_full_index(documents, args.output_dir)
        elif args.type == "full_text":
            build_full_text_indexes(documents, args.output_dir)
        elif args.type == "all":
            build_all_indexes(documents, args.output_dir)
        
        print("\n✅ Index building completed successfully!")
        return 0
        
    except Exception as e:
        print(f"\n❌ Error building indexes: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
