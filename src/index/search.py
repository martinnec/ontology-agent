"""
Search interface for BM25 and other indexes.

This module provides search functionality over built indexes,
supporting both command-line and programmatic interfaces.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

# Add parent directory to path to allow imports
sys.path.append(str(Path(__file__).parent.parent))

from index.bm25 import BM25SummaryIndex
from index.faiss_index import FAISSSummaryIndex
from index.domain import SearchQuery, SearchResult, ElementType


class SearchEngine:
    """
    High-level search engine that can work with different index types.
    """
    
    def __init__(self):
        self.bm25_index: Optional[BM25SummaryIndex] = None
        self.faiss_index: Optional[FAISSSummaryIndex] = None
        self.index_path: Optional[str] = None
        self.index_type: Optional[str] = None
    
    def load_bm25_index(self, index_path: str) -> None:
        """
        Load a BM25 index from disk.
        
        Args:
            index_path: Path to the index directory
        """
        self.bm25_index = BM25SummaryIndex()
        self.bm25_index.load(index_path)
        self.index_path = index_path
        self.index_type = "bm25"
        print(f"Loaded BM25 index from: {index_path}")
        
        # Show index info
        metadata = self.bm25_index.get_metadata()
        stats = self.bm25_index.get_stats()
        print(f"Index info:")
        print(f"  - Act: {metadata.act_iri}")
        print(f"  - Created: {metadata.created_at}")
        print(f"  - Documents: {stats['document_count']}")
        print(f"  - Vocabulary: {stats['vocabulary_size']} terms")
    
    def load_faiss_index(self, index_path: str) -> None:
        """
        Load a FAISS index from disk.
        
        Args:
            index_path: Path to the index directory
        """
        self.faiss_index = FAISSSummaryIndex()
        self.faiss_index.load(index_path)
        self.index_path = index_path
        self.index_type = "faiss"
        print(f"Loaded FAISS index from: {index_path}")
        
        # Show index info
        metadata = self.faiss_index.get_metadata()
        stats = self.faiss_index.get_stats()
        print(f"Index info:")
        print(f"  - Act: {metadata.act_iri}")
        print(f"  - Created: {metadata.created_at}")
        print(f"  - Documents: {stats['document_count']}")
        print(f"  - Model: {stats['model_name']}")
        print(f"  - Valid embeddings: {stats['valid_embeddings']}")
    
    def load_index(self, index_path: str, index_type: str = "auto") -> None:
        """
        Load an index from disk, auto-detecting type if needed.
        
        Args:
            index_path: Path to the index directory
            index_type: Type of index ("bm25", "faiss", or "auto")
        """
        if index_type == "auto":
            # Try to detect index type by checking for files
            path_obj = Path(index_path)
            if (path_obj / "bm25_model.pkl").exists():
                index_type = "bm25"
            elif (path_obj / "faiss_index.bin").exists():
                index_type = "faiss"
            else:
                raise ValueError(f"Cannot detect index type in {index_path}")
        
        if index_type == "bm25":
            self.load_bm25_index(index_path)
        elif index_type == "faiss":
            self.load_faiss_index(index_path)
        else:
            raise ValueError(f"Unknown index type: {index_type}")
    
    def search(self, query_text: str, 
              max_results: int = 10,
              element_types: Optional[List[str]] = None,
              min_level: Optional[int] = None,
              max_level: Optional[int] = None,
              official_id_pattern: Optional[str] = None) -> List[SearchResult]:
        """
        Search the loaded index.
        
        Args:
            query_text: Search query
            max_results: Maximum number of results
            element_types: Filter by element types
            min_level: Minimum hierarchical level
            max_level: Maximum hierarchical level
            official_id_pattern: Regex pattern for official identifier
            
        Returns:
            List of search results
        """
        if self.bm25_index is None and self.faiss_index is None:
            raise ValueError("No index loaded. Call load_index() first.")
        
        # Convert string element types to enum
        enum_types = None
        if element_types:
            enum_types = []
            for et in element_types:
                try:
                    enum_types.append(ElementType(et.lower()))
                except ValueError:
                    print(f"WARNING: Unknown element type '{et}', skipping")
        
        # Create search query
        query = SearchQuery(
            query=query_text,
            max_results=max_results,
            element_types=enum_types,
            min_level=min_level,
            max_level=max_level,
            official_identifier_pattern=official_id_pattern
        )
        
        # Perform search with the available index
        if self.bm25_index is not None:
            return self.bm25_index.search(query)
        elif self.faiss_index is not None:
            return self.faiss_index.search(query)
        else:
            return []
    
    def get_index_info(self) -> dict:
        """Get information about the loaded index."""
        if self.bm25_index is None and self.faiss_index is None:
            return {"error": "No index loaded"}
        
        if self.bm25_index is not None:
            metadata = self.bm25_index.get_metadata()
            stats = self.bm25_index.get_stats()
            return {
                "index_type": "bm25",
                "path": self.index_path,
                "metadata": metadata.model_dump(),
                "stats": stats
            }
        elif self.faiss_index is not None:
            metadata = self.faiss_index.get_metadata()
            stats = self.faiss_index.get_stats()
            return {
                "index_type": "faiss",
                "path": self.index_path,
                "metadata": metadata.model_dump(),
                "stats": stats
            }
        
        return {}
    
    def get_similar_documents(self, element_id: str, k: int = 5) -> List[tuple]:
        """
        Get documents similar to the specified document (FAISS only).
        
        Args:
            element_id: ID of the reference document
            k: Number of similar documents to return
            
        Returns:
            List of (document, similarity_score) tuples
        """
        if self.faiss_index is None:
            raise ValueError("Similar document search requires FAISS index")
        
        return self.faiss_index.get_similar_documents(element_id, k)
        
        metadata = self.bm25_index.get_metadata()
        stats = self.bm25_index.get_stats()
        
        return {
            "index_path": self.index_path,
            "metadata": metadata.model_dump(),
            "statistics": stats
        }


def print_search_results(results: List[SearchResult], show_snippets: bool = True) -> None:
    """
    Print search results in a human-readable format.
    
    Args:
        results: List of search results
        show_snippets: Whether to show text snippets
    """
    if not results:
        print("No results found.")
        return
    
    print(f"\nFound {len(results)} results:")
    print("=" * 60)
    
    for result in results:
        doc = result.doc
        print(f"#{result.rank} [{doc.element_type.value.upper()}] {doc.official_identifier}")
        print(f"Title: {doc.title}")
        print(f"Score: {result.score:.3f}")
        print(f"Level: {doc.level}")
        if result.matched_fields:
            print(f"Matched fields: {', '.join(result.matched_fields)}")
        
        if show_snippets and result.snippet:
            print(f"Snippet: {result.snippet}")
        
        print("-" * 40)


def interactive_search(search_engine: SearchEngine) -> None:
    """
    Start an interactive search session.
    
    Args:
        search_engine: Configured search engine
    """
    print("\nInteractive Search Mode")
    print("Commands:")
    print("  <query>                 - Search for query")
    print("  sections <query>        - Search only sections")
    print("  acts <query>           - Search only acts")
    print("  level <min-max> <query> - Search specific levels (e.g., 'level 1-2 základní pojmy')")
    print("  info                   - Show index information")
    print("  quit                   - Exit")
    print()
    
    while True:
        try:
            user_input = input("search> ").strip()
            
            if not user_input or user_input.lower() == "quit":
                break
            
            if user_input.lower() == "info":
                info = search_engine.get_index_info()
                print(json.dumps(info, indent=2, ensure_ascii=False))
                continue
            
            # Parse special commands
            max_results = 10
            element_types = None
            min_level = None
            max_level = None
            query_text = user_input
            
            # Handle "sections <query>"
            if user_input.startswith("sections "):
                element_types = ["section"]
                query_text = user_input[9:]
            
            # Handle "acts <query>"
            elif user_input.startswith("acts "):
                element_types = ["act"]
                query_text = user_input[5:]
            
            # Handle "level <min-max> <query>"
            elif user_input.startswith("level "):
                parts = user_input[6:].split(" ", 1)
                if len(parts) == 2:
                    level_range, query_text = parts
                    if "-" in level_range:
                        try:
                            min_str, max_str = level_range.split("-")
                            min_level = int(min_str.strip())
                            max_level = int(max_str.strip())
                        except ValueError:
                            print("Invalid level range. Use format: level 1-2 <query>")
                            continue
                    else:
                        try:
                            min_level = max_level = int(level_range)
                        except ValueError:
                            print("Invalid level. Use format: level 1 <query> or level 1-2 <query>")
                            continue
                else:
                    print("Invalid level command. Use format: level 1-2 <query>")
                    continue
            
            if not query_text.strip():
                print("Please provide a search query.")
                continue
            
            # Perform search
            results = search_engine.search(
                query_text=query_text,
                max_results=max_results,
                element_types=element_types,
                min_level=min_level,
                max_level=max_level
            )
            
            print_search_results(results)
            
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Search BM25 or FAISS index for legal acts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive search (auto-detect index type)
  python -m index.search --index ./indexes/act1
  
  # Single query with BM25
  python -m index.search --index ./indexes/act1_bm25 --query "základní pojmy"
  
  # Single query with FAISS semantic search
  python -m index.search --index ./indexes/act1_faiss --query "definice pojmů"
  
  # Search only sections
  python -m index.search --index ./indexes/act1 --query "definice" --types section
  
  # Search specific levels
  python -m index.search --index ./indexes/act1 --query "práva" --min-level 1 --max-level 2
  
  # Search with pattern matching
  python -m index.search --index ./indexes/act1 --query "povinnosti" --pattern "^§"
  
  # Find similar documents (FAISS only)
  python -m index.search --index ./indexes/act1_faiss --similar-to <element_id>
        """)
    
    parser.add_argument("--index", "-i", required=True,
                       help="Path to the index directory")
    parser.add_argument("--index-type", choices=["bm25", "faiss", "auto"], default="auto",
                       help="Type of index to load (default: auto-detect)")
    parser.add_argument("--query", "-q",
                       help="Search query (if not provided, starts interactive mode)")
    parser.add_argument("--similar-to",
                       help="Find documents similar to this element ID (FAISS only)")
    parser.add_argument("--max-results", "-n", type=int, default=10,
                       help="Maximum number of results (default: 10)")
    parser.add_argument("--types", nargs="+",
                       choices=["act", "part", "chapter", "division", "section", "unknown"],
                       help="Filter by element types")
    parser.add_argument("--min-level", type=int,
                       help="Minimum hierarchical level")
    parser.add_argument("--max-level", type=int,
                       help="Maximum hierarchical level")
    parser.add_argument("--pattern",
                       help="Regex pattern for official identifier")
    parser.add_argument("--no-snippets", action="store_true",
                       help="Don't show text snippets in results")
    parser.add_argument("--json", action="store_true",
                       help="Output results as JSON")
    
    args = parser.parse_args()
    
    try:
        # Initialize search engine
        search_engine = SearchEngine()
        search_engine.load_index(args.index, args.index_type)
        
        if args.similar_to:
            # Similar document search (FAISS only)
            if search_engine.index_type != "faiss":
                print("ERROR: Similar document search requires FAISS index")
                sys.exit(1)
            
            similar_docs = search_engine.get_similar_documents(args.similar_to, args.max_results)
            
            if args.json:
                json_results = []
                for doc, score in similar_docs:
                    json_results.append({
                        "element_id": doc.element_id,
                        "title": doc.title,
                        "official_identifier": doc.official_identifier,
                        "similarity_score": score,
                        "element_type": doc.element_type.value,
                        "level": doc.level
                    })
                print(json.dumps(json_results, ensure_ascii=False, indent=2))
            else:
                print(f"\nDocuments similar to {args.similar_to}:")
                print("=" * 60)
                for i, (doc, score) in enumerate(similar_docs):
                    print(f"#{i+1} [{doc.element_type.value.upper()}] {doc.official_identifier}")
                    print(f"Title: {doc.title}")
                    print(f"Similarity: {score:.3f}")
                    print(f"Level: {doc.level}")
                    print("-" * 40)
                    
        elif args.query:
            # Single query mode
            results = search_engine.search(
                query_text=args.query,
                max_results=args.max_results,
                element_types=args.types,
                min_level=args.min_level,
                max_level=args.max_level,
                official_id_pattern=args.pattern
            )
            
            if args.json:
                # Output as JSON
                json_results = []
                for result in results:
                    json_results.append({
                        "rank": result.rank,
                        "score": result.score,
                        "element_id": result.doc.element_id,
                        "title": result.doc.title,
                        "official_identifier": result.doc.official_identifier,
                        "element_type": result.doc.element_type.value,
                        "level": result.doc.level,
                        "matched_fields": result.matched_fields,
                        "snippet": result.snippet
                    })
                print(json.dumps(json_results, ensure_ascii=False, indent=2))
            else:
                # Human-readable output
                print_search_results(results, show_snippets=not args.no_snippets)
        else:
            # Interactive mode
            interactive_search(search_engine)
    
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
