#!/usr/bin/env python3
"""
Interactive CLI for the Hybrid Search Engine

This CLI allows you to experiment with the HybridSearchEngine using the 56/2001 legal act.
It provides an intuitive interface to try different search strategies, configurations,
and explore the search capabilities of the system.

Usage:
    cd src
    python hybrid_search_engine_cli.py

Commands:
    # Summary Layer Search Commands (titles + summaries)
    keyword_summary <query> [--types TYPE1,TYPE2]    - BM25 keyword search on summaries
    semantic_summary <query> [--types TYPE1,TYPE2]   - FAISS semantic search on summaries  
    hybrid_summary <query> [strategy] [--types]      - Hybrid search on summaries
    
    # Full-text Layer Search Commands (complete document content)
    keyword_fulltext <query> [--types TYPE1,TYPE2]   - BM25 keyword search on full text
    semantic_fulltext <query> [--types TYPE1,TYPE2]  - FAISS semantic search on full text
    hybrid_fulltext <query> [strategy] [--types]     - Hybrid search on full text
    
    # Special Search Commands
    exact "<phrase>" [--types TYPE1,TYPE2]           - Search for exact phrase in full text
    
    # Analysis Commands
    compare <query> [--types TYPE1,TYPE2]            - Compare all search strategies
    quick [number]                                   - Run predefined example queries
    
    # Configuration Commands  
    config                                           - Show current configuration
    config <param> <value>                          - Change configuration parameter
    stats                                           - Show index statistics
    help                                            - Show this help message
    exit / quit                                     - Exit the CLI

Hybrid Strategies:
    semantic_first (default) - Semantic → keyword reranking (balanced general default)
    keyword_first            - Keyword → semantic reranking (short/specific queries)  
    parallel                 - Parallel execution + score fusion (diversity)

Element Types:
    act, part, chapter, division, section, unknown

Search Layer Guide:
    Summary Layer    - Fast, conceptual, good for topical discovery & navigation
    Full-text Layer  - Slower, granular, good for precise citation & phrase search

Examples:
    keyword_summary registrace vozidel
    semantic_summary technická kontrola --types section
    hybrid_summary povinné ručení semantic_first --types section
    keyword_fulltext dopravní přestupky --types section,division
    hybrid_fulltext registrace vozidel parallel --types section
    exact "musí být" --types section
    compare technická kontrola --types chapter
    quick 1
    config max_results 15
    stats

Short Commands:
    kws, sems, hybs, kwf, semf, hybf, comp, cfg, stat, h, q
"""

import re
import sys
import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

# Add the current directory to the path
sys.path.append(str(Path(__file__).parent))

try:
    # New unified interfaces
    from index import IndexService
    from search.service import SearchService
    from search.domain import SearchStrategy, SearchOptions, SearchResults, SearchResultItem
    from legislation.service import LegislationService
    from legislation.datasource_esel import DataSourceESEL
    
    # Legacy imports for backward compatibility
    from index.domain import ElementType
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure you're running this from the src directory")
    sys.exit(1)

# Suppress warnings for cleaner output
logging.getLogger().setLevel(logging.ERROR)


class HybridSearchCLI:
    """Interactive CLI for the Unified Search Engine."""
    
    def __init__(self):
        self.search_service: Optional[SearchService] = None
        self.index_service: Optional[IndexService] = None
        self.legal_act = None
        self.act_iri = "https://opendata.eselpoint.cz/esel-esb/eli/cz/sb/2001/56/2025-07-01"
        
        # Set index path to project root's data/indexes directory
        project_root = Path(__file__).parent.parent
        self.index_base_path = project_root / "data" / "indexes"
        
        # Configuration
        self.config = {
            'max_results': 10,
            'element_types': None,
            'include_summary': True,
            'include_full_text': True
        }
        
        # Command mappings
        self.commands = {
            # Summary-layer search commands
            'keyword_summary': self.cmd_keyword_summary_search,
            'kws': self.cmd_keyword_summary_search,
            'semantic_summary': self.cmd_semantic_summary_search,
            'sems': self.cmd_semantic_summary_search,
            'hybrid_summary': self.cmd_hybrid_summary_search,
            'hybs': self.cmd_hybrid_summary_search,
            # Full-text layer search commands
            'keyword_fulltext': self.cmd_keyword_fulltext_search,
            'kwf': self.cmd_keyword_fulltext_search,
            'semantic_fulltext': self.cmd_semantic_fulltext_search,
            'semf': self.cmd_semantic_fulltext_search,
            'hybrid_fulltext': self.cmd_hybrid_fulltext_search,
            'hybf': self.cmd_hybrid_fulltext_search,
            # Phrase search
            'exact': self.cmd_exact_search,
            # Analysis and utility commands
            'compare': self.cmd_compare,
            'comp': self.cmd_compare,
            'quick': self.cmd_quick_examples,
            'build': self.cmd_build_indexes,
            # Configuration commands
            'config': self.cmd_config,
            'cfg': self.cmd_config,
            'stats': self.cmd_stats,
            'stat': self.cmd_stats,
            'help': self.cmd_help,
            'h': self.cmd_help,
            '?': self.cmd_help,
            'exit': self.cmd_exit,
            'quit': self.cmd_exit,
            'q': self.cmd_exit,
        }
        
        # Keep track of last query for convenience
        self.last_query = None
        
    def initialize(self):
        """Initialize the search service and load indexes."""
        print("🚀 Initializing Unified Search Engine CLI")
        print("=" * 60)
        
        # Load legal act
        print("📖 Loading legal act...")
        try:
            data_source = DataSourceESEL()
            legislation_service = LegislationService(data_source, llm_model_identifier="gpt-4.1-mini")
            self.legal_act = legislation_service.get_legal_act(self.act_iri)
            
            if not self.legal_act:
                print("❌ Failed to load legal act")
                return False
            
            print(f"✅ Loaded legal act: {self.legal_act.title}")
        except Exception as e:
            print(f"❌ Failed to load legal act: {e}")
            return False
        
        # Initialize IndexService
        print("🔧 Initializing IndexService...")
        try:
            self.index_service = IndexService(str(self.index_base_path))
            print("✅ IndexService initialized")
        except Exception as e:
            print(f"❌ Failed to initialize IndexService: {e}")
            return False
        
        # Check if indexes exist
        print("📂 Checking for existing indexes...")
        try:
            collection = self.index_service.get_indexes(self.legal_act)
            available_indexes = collection.get_available_indexes()
            
            if available_indexes:
                print(f"✅ Found indexes: {', '.join(available_indexes)}")
                print(f"📊 Document count: {collection.get_document_count()}")
            else:
                print("⚠️  No indexes found! Building indexes automatically...")
                print("🔧 This may take a few minutes...")
                
                # Build basic indexes
                index_types = ["bm25", "faiss"]
                collection = self.index_service.build_indexes(self.legal_act, index_types)
                print(f"✅ Built indexes: {', '.join(collection.get_available_indexes())}")
                
        except Exception as e:
            print(f"❌ Failed to check/build indexes: {e}")
            return False
        
        # Initialize SearchService
        print("🔍 Initializing SearchService...")
        try:
            self.search_service = SearchService(self.index_service, self.legal_act)
            print("✅ SearchService initialized")
            
            # Get and display stats
            info = self.search_service.get_index_info()
            print(f"📊 Available search strategies: {', '.join(info['available_indexes'])}")
            print(f"📋 Total documents: {info['document_count']}")
            
        except Exception as e:
            print(f"❌ Failed to initialize SearchService: {e}")
            return False
        
        print("\n🎉 CLI ready! Type 'help' for available commands.")
        return True
    def run(self):
        """Run the interactive CLI."""
        if not self.initialize():
            return
        
        print("\n" + "=" * 60)
        print("🔍 HYBRID SEARCH ENGINE CLI")
        print("=" * 60)
        print("Type 'help' for commands or 'exit' to quit")
        print("Try: keyword_summary registrace vozidel")
        print("     hybrid_summary technická kontrola semantic_first")
        print("")
        
        while True:
            try:
                command_line = input("hybrid> ").strip()
                
                if not command_line:
                    continue
                
                # Parse command and arguments
                parts = command_line.split()
                command = parts[0].lower()
                args = parts[1:] if len(parts) > 1 else []
                
                # Handle quoted strings for exact search
                if command == 'exact' and '"' in command_line:
                    # Extract quoted phrase and any remaining arguments
                    start_quote = command_line.find('"')
                    end_quote = command_line.rfind('"')
                    if start_quote != -1 and end_quote != -1 and start_quote != end_quote:
                        phrase = command_line[start_quote+1:end_quote]
                        # Check for additional arguments after the quoted phrase
                        remaining = command_line[end_quote+1:].strip()
                        if remaining:
                            remaining_parts = remaining.split()
                            args = [phrase] + remaining_parts
                        else:
                            args = [phrase]
                
                # Execute command
                if command in self.commands:
                    self.commands[command](args)
                else:
                    print(f"❌ Unknown command: {command}")
                    print("Type 'help' for available commands")
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except EOFError:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
    
    def _parse_search_args(self, args: List[str]) -> tuple[str, Optional[List[ElementType]]]:
        """Parse search arguments including optional element type filters."""
        query_parts = []
        element_types = None
        
        i = 0
        while i < len(args):
            if args[i] == '--types' and i + 1 < len(args):
                # Parse element types
                type_str = args[i + 1]
                try:
                    type_names = [name.strip().lower() for name in type_str.split(',')]
                    element_types = []
                    for name in type_names:
                        if name in [e.value for e in ElementType]:
                            element_types.append(ElementType(name))
                        else:
                            print(f"⚠️  Invalid element type: '{name}'")
                    
                    if element_types:
                        print(f"🎯 Filtering by element types: {', '.join([t.value for t in element_types])}")
                    else:
                        print(f"⚠️  No valid element types found in: {type_str}")
                        print(f"Valid types: {', '.join([e.value for e in ElementType])}")
                except ValueError as e:
                    print(f"⚠️  Invalid element type: {e}")
                    print(f"Valid types: {', '.join([e.value for e in ElementType])}")
                i += 2
            else:
                query_parts.append(args[i])
                i += 1
        
        query_text = ' '.join(query_parts)
        return query_text, element_types

    def cmd_exact_search(self, args: List[str]):
        """Search for exact phrases."""
        if not args:
            print('Usage: exact "<phrase>" [--types TYPE1,TYPE2,...]')
            print('Example: exact "musí být" --types section')
            print("Types: act, part, chapter, division, section, unknown")
            return
        
        # For exact search, we need to handle the phrase differently
        # The phrase should be the first argument(s) until we hit --types
        phrase_parts = []
        element_types = None
        
        i = 0
        while i < len(args):
            if args[i] == '--types' and i + 1 < len(args):
                # Parse element types
                type_str = args[i + 1]
                try:
                    type_names = [name.strip().lower() for name in type_str.split(',')]
                    element_types = []
                    for name in type_names:
                        if name in [e.value for e in ElementType]:
                            element_types.append(ElementType(name))
                        else:
                            print(f"⚠️  Invalid element type: '{name}'")
                    
                    if element_types:
                        print(f"🎯 Filtering by element types: {', '.join([t.value for t in element_types])}")
                    else:
                        print(f"⚠️  No valid element types found in: {type_str}")
                        print(f"Valid types: {', '.join([e.value for e in ElementType])}")
                except ValueError as e:
                    print(f"⚠️  Invalid element type: {e}")
                    print(f"Valid types: {', '.join([e.value for e in ElementType])}")
                break
            else:
                phrase_parts.append(args[i])
                i += 1
        
        phrase = " ".join(phrase_parts)
        print(f"🎯 Exact phrase search: '{phrase}'")
        
        try:
            # Use fulltext search for exact phrases
            options = SearchOptions(
                max_results=self.config['max_results'],
                element_types=element_types
            )
            # Add quotes to make it an exact phrase search
            exact_query = f'"{phrase}"'
            results = self.search_service.search_keyword_fulltext(exact_query, options)
            self._display_results(results, f"Exact Phrase: '{phrase}'")
        except Exception as e:
            print(f"❌ Exact phrase search failed: {e}")

    # New explicit search command methods
    def cmd_keyword_summary_search(self, args: List[str]):
        """Perform keyword search on summaries explicitly."""
        if not args:
            print("Usage: keyword_summary <query> [--types TYPE1,TYPE2,...]")
            print("Performs BM25 keyword search on document summaries")
            print("Types: act, part, chapter, division, section, unknown")
            return
        
        query_text, element_types = self._parse_search_args(args)
        print(f"🔑📋 Keyword Summary search: '{query_text}'")
        
        try:
            options = SearchOptions(
                max_results=self.config['max_results'],
                element_types=element_types if element_types else None
            )
            results = self.search_service.search_keyword_summary(query_text, options)
            self._display_results(results, "Keyword Summary Search")
        except Exception as e:
            print(f"❌ Keyword summary search failed: {e}")

    def cmd_semantic_summary_search(self, args: List[str]):
        """Perform semantic search on summaries explicitly."""
        if not args:
            print("Usage: semantic_summary <query> [--types TYPE1,TYPE2,...]")
            print("Performs FAISS semantic search on document summaries")
            print("Types: act, part, chapter, division, section, unknown")
            return
        
        query_text, element_types = self._parse_search_args(args)
        print(f"🧠📋 Semantic Summary search: '{query_text}'")
        
        try:
            options = SearchOptions(
                max_results=self.config['max_results'],
                element_types=element_types if element_types else None
            )
            results = self.search_service.search_semantic_summary(query_text, options)
            self._display_results(results, "Semantic Summary Search")
        except Exception as e:
            print(f"❌ Semantic summary search failed: {e}")

    def cmd_hybrid_summary_search(self, args: List[str]):
        """Perform hybrid search on summaries explicitly."""
        if not args:
            print("Usage: hybrid_summary <query> [strategy] [--types TYPE1,TYPE2,...]")
            print("Strategies: semantic_first (default), keyword_first, parallel")
            print("Performs hybrid search on document summaries")
            print("Types: act, part, chapter, division, section, unknown")
            return
        
        # Parse strategy if provided
        strategy = "semantic_first"  # default
        strategy_args = []
        remaining_args = []
        
        for i, arg in enumerate(args):
            if arg in ["semantic_first", "keyword_first", "parallel"]:
                strategy = arg
            else:
                remaining_args.append(arg)
        
        query_text, element_types = self._parse_search_args(remaining_args)
        print(f"🔀📋 Hybrid Summary search ({strategy}): '{query_text}'")
        
        try:
            options = SearchOptions(
                max_results=self.config['max_results'],
                element_types=element_types if element_types else None
            )
            results = self.search_service.search_hybrid_summary(query_text, strategy, options)
            self._display_results(results, f"Hybrid Summary Search ({strategy})")
        except Exception as e:
            print(f"❌ Hybrid summary search failed: {e}")

    def cmd_keyword_fulltext_search(self, args: List[str]):
        """Perform keyword search on full text explicitly."""
        if not args:
            print("Usage: keyword_fulltext <query> [--types TYPE1,TYPE2,...]")
            print("Performs BM25 keyword search on full document text")
            print("Types: act, part, chapter, division, section, unknown")
            return
        
        query_text, element_types = self._parse_search_args(args)
        print(f"🔑📄 Keyword Full-text search: '{query_text}'")
        
        try:
            options = SearchOptions(
                max_results=self.config['max_results'],
                element_types=element_types if element_types else None
            )
            results = self.search_service.search_keyword_fulltext(query_text, options)
            self._display_results(results, "Keyword Full-text Search")
        except Exception as e:
            print(f"❌ Keyword fulltext search failed: {e}")

    def cmd_semantic_fulltext_search(self, args: List[str]):
        """Perform semantic search on full text explicitly."""
        if not args:
            print("Usage: semantic_fulltext <query> [--types TYPE1,TYPE2,...]")
            print("Performs FAISS semantic search on full document text")
            print("Types: act, part, chapter, division, section, unknown")
            return
        
        query_text, element_types = self._parse_search_args(args)
        print(f"🧠📄 Semantic Full-text search: '{query_text}'")
        
        try:
            options = SearchOptions(
                max_results=self.config['max_results'],
                element_types=element_types if element_types else None
            )
            results = self.search_service.search_semantic_fulltext(query_text, options)
            self._display_results(results, "Semantic Full-text Search")
        except Exception as e:
            print(f"❌ Semantic fulltext search failed: {e}")

    def cmd_hybrid_fulltext_search(self, args: List[str]):
        """Perform hybrid search on full text explicitly."""
        if not args:
            print("Usage: hybrid_fulltext <query> [strategy] [--types TYPE1,TYPE2,...]")
            print("Strategies: semantic_first (default), keyword_first, parallel")
            print("Performs hybrid search on full document text")
            print("Types: act, part, chapter, division, section, unknown")
            return
        
        # Parse strategy if provided
        strategy = "semantic_first"  # default
        remaining_args = []
        
        for i, arg in enumerate(args):
            if arg in ["semantic_first", "keyword_first", "parallel"]:
                strategy = arg
            else:
                remaining_args.append(arg)
        
        query_text, element_types = self._parse_search_args(remaining_args)
        print(f"🔀📄 Hybrid Full-text search ({strategy}): '{query_text}'")
        
        try:
            options = SearchOptions(
                max_results=self.config['max_results'],
                element_types=element_types if element_types else None
            )
            results = self.search_service.search_hybrid_fulltext(query_text, strategy, options)
            self._display_results(results, f"Hybrid Full-text Search ({strategy})")
        except Exception as e:
            print(f"❌ Hybrid fulltext search failed: {e}")
    
    def cmd_config(self, args: List[str]):
        """Show or modify configuration."""
        if not args:
            self._show_config()
            return
        
        if len(args) == 1:
            param = args[0]
            if param in self.config:
                value = self.config[param]
                print(f"{param}: {value}")
            else:
                print(f"❌ Unknown parameter: {param}")
                self._show_config_params()
        elif len(args) == 2:
            param, value_str = args
            if param in self.config:
                try:
                    # Try to convert to appropriate type
                    current_value = self.config[param]
                    if isinstance(current_value, bool):
                        value = value_str.lower() in ('true', '1', 'yes', 'on')
                    elif isinstance(current_value, int):
                        value = int(value_str)
                    elif isinstance(current_value, float):
                        value = float(value_str)
                    elif isinstance(current_value, list):
                        if value_str.lower() == 'none':
                            value = None
                        else:
                            value = [item.strip() for item in value_str.split(',')]
                    else:
                        value = value_str
                    
                    self.config[param] = value
                    print(f"✅ {param} = {value}")
                    
                except ValueError as e:
                    print(f"❌ Invalid value for {param}: {e}")
            else:
                print(f"❌ Unknown parameter: {param}")
                self._show_config_params()
        else:
            print("Usage: config [param] [value]")
    
    def cmd_stats(self, args: List[str]):
        """Show index statistics."""
        if not self.engine:
            print("❌ Engine not initialized")
            return
        
        print("📊 Index Statistics")
        print("=" * 40)
        
        try:
            info = self.search_service.get_index_info()
            
            print(f"� Search Service Status:")
            print(f"   Available indexes: {', '.join(info['available_indexes'])}")
            print(f"   Total documents: {info['document_count']}")
            print(f"   Legal act: {self.legal_act.title if self.legal_act else 'N/A'}")
            
            # Show configuration
            print(f"\n⚙️ Configuration:")
            print(f"   Max results: {self.config['max_results']}")
            print(f"   Include summary: {self.config['include_summary']}")
            print(f"   Include full text: {self.config['include_full_text']}")
            
        except Exception as e:
            print(f"❌ Error getting statistics: {e}")
    
    def cmd_help(self, args: List[str]):
        """Show help information."""
        print("\n📖 Hybrid Search Engine CLI Help")
        print("=" * 50)
        print("\n🔍 Summary Layer Search Commands (titles + summaries):")
        print("  keyword_summary <query> [--types]     - BM25 keyword search on summaries (kws)")
        print("  semantic_summary <query> [--types]    - FAISS semantic search on summaries (sems)")
        print("  hybrid_summary <query> [strategy] [--types] - Hybrid search on summaries (hybs)")
        print("\n� Full-text Layer Search Commands (complete document content):")
        print("  keyword_fulltext <query> [--types]    - BM25 keyword search on full text (kwf)")
        print("  semantic_fulltext <query> [--types]   - FAISS semantic search on full text (semf)")
        print("  hybrid_fulltext <query> [strategy] [--types] - Hybrid search on full text (hybf)")
        print("\n🎯 Special Search Commands:")
        print('  exact "<phrase>" [--types]             - Exact phrase search in full text')
        print("\n🎯 Hybrid Strategies:")
        print("  semantic_first (default) - Semantic → keyword reranking (balanced general default)")
        print("  keyword_first            - Keyword → semantic reranking (short/specific queries)")
        print("  parallel                 - Parallel execution + score fusion (diversity)")
        print("\n�️  Element Type Filtering:")
        print("  Available types: act, part, chapter, division, section, unknown")
        print("  Examples:")
        print("    keyword_summary registrace --types section,division")
        print("    semantic_summary technická kontrola --types chapter")
        print("    hybrid_fulltext registrace semantic_first --types section")
        print('    exact "musí být" --types section')
        print("    semantic_fulltext kategorie M1 --types part")
        print("\n🔧 Analysis Commands:")
        print("  compare <query> [--types]             - Compare all search strategies for a query")
        print("  compare                               - Compare strategies for last query")
        print("  quick [number]                        - Run predefined example queries")
        print("  build [force]                         - Build missing indexes (all types)")
        print("  build <index_type>                    - Build specific index (bm25/faiss/bm25_full/faiss_full)")
        print("\n⚙️  Configuration Commands:")
        print("  config                                - Show current configuration")
        print("  config <param> <value>                - Change configuration parameter")
        print("  stats                                 - Show index statistics")
        print("\n🚪 Other Commands:")
        print("  help / h / ?                          - Show this help")
        print("  exit / quit / q                       - Exit the CLI")
        print("\n💡 Example Queries for Vehicle Law 56/2001:")
        print("  keyword_summary registrace vozidel")
        print("  semantic_summary technická kontrola --types section")
        print("  hybrid_summary povinné ručení semantic_first --types section")
        print("  keyword_fulltext dopravní přestupky --types section,division")
        print("  hybrid_fulltext registrace vozidel parallel --types section")
        print('  exact "musí být" --types section')
        print("  compare registrace vozidel --types section")
        print("  quick 1")
        print("\n⚙️  Configuration Examples:")
        print("  config max_results 15                 - Show 15 results instead of default")
        print("  config element_types section,chapter  - Set default element filter")
        print("\n🔤 Short Commands:")
        print("  kws, sems, hybs, kwf, semf, hybf, comp, cfg, stat, h, q")
        print("\n� Search Layer Guide:")
        print("  Summary Layer   - Fast, conceptual, good for topical discovery & navigation")
        print("  Full-text Layer - Slower, granular, good for precise citation & phrase search")
        print("  Hybrid methods  - Combine BM25 + FAISS for best of both approaches")
    
    def cmd_exit(self, args: List[str]):
        """Exit the CLI."""
        print("👋 Goodbye!")
        sys.exit(0)
    
    def cmd_compare(self, args: List[str]):
        """Compare results from different search strategies for the same query."""
        if not args:
            if self.last_query:
                query_text = self.last_query
                element_types = None  # Use last query without element types for simplicity
                print(f"🔄 Comparing strategies for last query: '{query_text}'")
            else:
                print("Usage: compare <query> [--types TYPE1,TYPE2,...]")
                print("Or use 'compare' after running a search to compare strategies for the last query")
                print("Types: act, part, chapter, division, section, unknown")
                return
        else:
            query_text, element_types = self._parse_search_args(args)
            self.last_query = query_text
            print(f"🔄 Comparing strategies for: '{query_text}'")
        
        print("=" * 80)
        
        try:
            options = SearchOptions(
                max_results=5,  # Limit to 5 for comparison
                element_types=element_types
            )
            
            strategies = [
                ("keyword_summary", "🔑📋 Keyword Summary Search"),
                ("semantic_summary", "🧠📋 Semantic Summary Search"),
                ("hybrid_summary", "🔀📋 Hybrid Summary Search"),
                ("keyword_fulltext", "🔑📄 Keyword Full-text Search"),
                ("semantic_fulltext", "🧠📄 Semantic Full-text Search"),
                ("hybrid_fulltext", "🔀📄 Hybrid Full-text Search")
            ]
            
            for strategy, title in strategies:
                print(f"\n{title}")
                print("-" * 50)
                
                try:
                    if strategy == "keyword_summary":
                        results = self.search_service.search_keyword_summary(query_text, options)
                    elif strategy == "semantic_summary":
                        results = self.search_service.search_semantic_summary(query_text, options)
                    elif strategy == "hybrid_summary":
                        results = self.search_service.search_hybrid_summary(query_text, "semantic_first", options)
                    elif strategy == "keyword_fulltext":
                        results = self.search_service.search_keyword_fulltext(query_text, options)
                    elif strategy == "semantic_fulltext":
                        results = self.search_service.search_semantic_fulltext(query_text, options)
                    elif strategy == "hybrid_fulltext":
                        results = self.search_service.search_hybrid_fulltext(query_text, "semantic_first", options)
                    
                    if results.items:
                        for i, result in enumerate(results.items[:3], 1):  # Show top 3
                            print(f"#{i} | {result.score:.3f} | {result.title}")
                        print(f"Total: {len(results.items)} results in {results.search_time_ms:.1f}ms")
                    else:
                        print("No results")
                except Exception as e:
                    print(f"❌ {strategy} failed: {e}")
                    
        except Exception as e:
            print(f"❌ Comparison failed: {e}")
    
    def cmd_quick_examples(self, args: List[str]):
        """Show quick examples and run sample queries."""
        print("\n🚀 Quick Examples for Vehicle Law 56/2001")
        print("=" * 60)
        
        examples = [
            ("registrace vozidel", "vehicle registration", None),
            ("technická kontrola --types section", "technical inspection (sections only)", ["section"]),
            ("dopravní přestupky --types section,division", "traffic violations (sections and divisions)", ["section", "division"]),
            ("povinné ručení", "mandatory insurance", None),
            ("řidičské oprávnění --types chapter", "driving license (chapters only)", ["chapter"])
        ]
        
        print("Available example queries:")
        for i, (query, english, types) in enumerate(examples, 1):
            type_info = f" (filtered by: {', '.join(types)})" if types else ""
            print(f"  {i}. {query} - {english}{type_info}")
        
        if not args:
            print("\nUsage: quick [number] - Run example query by number")
            print("Example: quick 1")
            print("\n💡 These examples demonstrate both regular and type-filtered searches")
            return
        
        try:
            choice = int(args[0]) - 1
            if 0 <= choice < len(examples):
                query_text, description, element_types = examples[choice]
                print(f"\n🔍 Running example: '{query_text}' ({description})")
                
                # Parse the query to extract command arguments
                if "--types" in query_text:
                    self.cmd_search(query_text.split())
                else:
                    self.cmd_search([query_text])
            else:
                print(f"❌ Invalid choice. Use 1-{len(examples)}")
        except ValueError:
            print("❌ Please provide a number")
    
    def _determine_element_type(self, official_identifier: str, level: int = 0) -> ElementType:
        """
        Determine element type from official identifier and level.
        
        Args:
            official_identifier: The official identifier (e.g., "§ 1", "Část 1", etc.)
            level: Hierarchical level in the document
            
        Returns:
            Appropriate ElementType
        """
        if not official_identifier:
            return ElementType.UNKNOWN
        
        identifier = official_identifier.strip().lower()
        
        # Check for sections (paragraphs)
        if identifier.startswith('§') or identifier.startswith('par'):
            return ElementType.SECTION
        
        # Check for parts
        if identifier.startswith('část') or identifier.startswith('part'):
            return ElementType.PART
        
        # Check for chapters
        if (identifier.startswith('hlava') or identifier.startswith('chapter') or 
            identifier.startswith('kapitola')):
            return ElementType.CHAPTER
        
        # Check for divisions/subdivisions  
        if (identifier.startswith('oddíl') or identifier.startswith('division') or
            identifier.startswith('pododdíl') or identifier.startswith('subdivision')):
            return ElementType.DIVISION
        
        # Check for articles
        if identifier.startswith('čl.') or identifier.startswith('článek') or identifier.startswith('article'):
            return ElementType.SECTION  # Articles are similar to sections in legal context
        
        # Use level-based heuristics for unknown identifiers
        if level == 0:
            return ElementType.ACT
        elif level == 1:
            return ElementType.PART
        elif level == 2:
            return ElementType.CHAPTER
        elif level == 3:
            return ElementType.DIVISION
        else:
            return ElementType.SECTION

    def cmd_build_indexes(self, args: List[str]):
        """Build missing indexes (both summary and full-text)."""
        print("\n🔧 Building Missing Indexes")
        print("=" * 60)
        
        try:
            # Import required modules
            from index.bm25 import BM25SummaryIndex
            from index.faiss import FAISSSummaryIndex
            from index.bm25_full import BM25FullIndex
            from index.faiss_full import FAISSFullIndex
            from index.domain import IndexDoc
            import json
            
            # Load legal act data
            data_file = Path(__file__).parent.parent / "data" / "legal_acts" / "56-2001-2025-07-01.json"
            if not data_file.exists():
                print(f"❌ Data file not found: {data_file}")
                print("Please ensure the legal act data file exists at the expected location.")
                return
            
            print("📖 Loading legal act data...")
            with open(data_file, 'r', encoding='utf-8') as f:
                act_data = json.load(f)
            
            # Extract documents
            documents = []
            def extract_docs(element_data, level=0, parent_id=None):
                if element_data.get('textContent') or element_data.get('summary'):
                    official_identifier = element_data.get('officialIdentifier', '')
                    element_type = self._determine_element_type(official_identifier, level)
                    
                    doc = IndexDoc(
                        element_id=str(element_data['id']),
                        title=element_data.get('title', ''),
                        summary=element_data.get('summary', ''),
                        summary_names=element_data.get('summary_names', []),
                        official_identifier=official_identifier,
                        text_content=element_data.get('textContent', ''),
                        level=level,
                        element_type=element_type,
                        parent_id=parent_id,
                        act_iri=act_data.get('id', ''),
                        snapshot_id='2025-07-01'
                    )
                    documents.append(doc)
                if 'elements' in element_data:
                    for child in element_data['elements']:
                        extract_docs(child, level + 1, element_data['id'])
            
            extract_docs(act_data)
            
            # Separate documents for different index types
            docs_with_summary = [doc for doc in documents if doc.summary or doc.title]
            docs_with_content = [doc for doc in documents if doc.text_content]
            
            print(f"📄 Found {len(docs_with_summary)} documents with summaries for summary indexes")
            print(f"📄 Found {len(docs_with_content)} documents with text content for full-text indexes")
            
            # Check what needs to be built
            bm25_path = self.index_base_path / "bm25"
            faiss_path = self.index_base_path / "faiss"
            bm25_full_path = self.index_base_path / "bm25_full"
            faiss_full_path = self.index_base_path / "faiss_full"
            
            # Determine what to build
            force_rebuild = args and args[0] == 'force'
            specific_index = args and len(args) > 0 and args[0] in ['bm25', 'faiss', 'bm25_full', 'faiss_full']
            
            if force_rebuild:
                print("🔄 Force rebuild requested for all indexes")
                build_bm25 = True
                build_faiss = True
                build_bm25_full = True
                build_faiss_full = True
            elif specific_index:
                build_bm25 = 'bm25' in args and 'bm25_full' not in args
                build_faiss = 'faiss' in args and 'faiss_full' not in args
                build_bm25_full = 'bm25_full' in args
                build_faiss_full = 'faiss_full' in args
            else:
                # Build only missing indexes
                build_bm25 = not bm25_path.exists()
                build_faiss = not faiss_path.exists()
                build_bm25_full = not bm25_full_path.exists()
                build_faiss_full = not faiss_full_path.exists()
            
            if not any([build_bm25, build_faiss, build_bm25_full, build_faiss_full]):
                print("✅ All indexes already exist. Use 'build force' to rebuild all indexes.")
                print("💡 Or specify specific index: 'build bm25', 'build faiss', 'build bm25_full', 'build faiss_full'")
                return
            
            # Create index directory if it doesn't exist
            self.index_base_path.mkdir(exist_ok=True)
            
            # Build BM25 summary index
            if build_bm25:
                print("\n🔧 Building BM25 summary index...")
                bm25_summary = BM25SummaryIndex()
                bm25_summary.build(docs_with_summary)
                bm25_summary.save(bm25_path)
                print("✅ BM25 summary index built and saved")
            
            # Build FAISS summary index
            if build_faiss:
                print("\n🧠 Building FAISS summary index...")
                print("   (This may take a few minutes for embeddings generation...)")
                faiss_summary = FAISSSummaryIndex()
                faiss_summary.build(docs_with_summary)
                faiss_summary.save(faiss_path)
                print("✅ FAISS summary index built and saved")
            
            # Build BM25 full-text index
            if build_bm25_full:
                if docs_with_content:
                    print("\n🔧 Building BM25 full-text index...")
                    bm25_full = BM25FullIndex()
                    bm25_full.build(docs_with_content)
                    bm25_full.save(bm25_full_path)
                    print("✅ BM25 full-text index built and saved")
                else:
                    print("\n⚠️  No documents with text content found for BM25 full-text index")
            
            # Build FAISS full-text index
            if build_faiss_full:
                if docs_with_content:
                    print("\n🧠 Building FAISS full-text index...")
                    print("   (This may take a few minutes for embeddings generation...)")
                    faiss_full = FAISSFullIndex()
                    faiss_full.build(docs_with_content)
                    faiss_full.save(faiss_full_path)
                    print("✅ FAISS full-text index built and saved")
                else:
                    print("\n⚠️  No documents with text content found for FAISS full-text index")
            
            # Show what was built
            built_indexes = []
            if build_bm25:
                built_indexes.append("BM25 Summary")
            if build_faiss:
                built_indexes.append("FAISS Summary")
            if build_bm25_full and docs_with_content:
                built_indexes.append("BM25 Full-text")
            if build_faiss_full and docs_with_content:
                built_indexes.append("FAISS Full-text")
            
            if built_indexes:
                print(f"\n🎉 Built indexes: {', '.join(built_indexes)}")
                print("🔄 Restart CLI to load the new indexes.")
            else:
                print("\n⚠️  No indexes were built.")
            
        except Exception as e:
            print(f"❌ Failed to build indexes: {e}")
            import traceback
            traceback.print_exc()
    
    
    def _display_results(self, results, title: str):
        """Display search results in a formatted way."""
        if not results or not results.items:
            print("❌ No results found")
            return
        
        print(f"\n📋 {title}")
        print("=" * 60)
        print(f"Found {results.total_found} results in {results.search_time_ms:.2f}ms")
        
        for i, result in enumerate(results.items, 1):
            print(f"\n#{i:2d} | Score: {result.score:.4f}")
            print(f"     📋 {result.title}")
            print(f"     🆔 {result.element_id}")
            
            # Show summary if available
            if hasattr(result, 'summary') and result.summary:
                summary_preview = result.summary[:200] + "..." if len(result.summary) > 200 else result.summary
                print(f"     💭 Summary: {summary_preview}")
            
            # Show highlighted_text if available
            if hasattr(result, 'highlighted_text') and result.highlighted_text:
                print(f"     🎯 Highlighted text: {result.highlighted_text}")

            # Show element type if available
            if hasattr(result, 'element_type') and result.element_type:
                print(f"     📂 Type: {result.element_type}")

            # Show text_content if available
            if hasattr(result, 'text_content') and result.text_content:
                # Remove XML tags and their attributes for display
                cleaned_text = re.sub(r'<[^>]+>', '', result.text_content)
                print(f"     📄 Content: {cleaned_text[:100]}{'...' if len(cleaned_text) > 100 else ''}")

        if len(results.items) < results.total_found:
            print(f"\n... and {results.total_found - len(results.items)} more results")
    
    def _parse_search_args(self, args: List[str]) -> tuple[str, Optional[List[str]]]:
        """Parse search arguments and return query and element types."""
        query_parts = []
        element_types = None
        
        i = 0
        while i < len(args):
            if args[i] == '--types' and i + 1 < len(args):
                # Parse element types
                type_str = args[i + 1]
                try:
                    type_names = [name.strip().lower() for name in type_str.split(',')]
                    element_types = []
                    valid_types = ['act', 'part', 'chapter', 'division', 'section', 'unknown']
                    
                    for name in type_names:
                        if name in valid_types:
                            element_types.append(name)
                        else:
                            print(f"⚠️  Invalid element type: '{name}'")
                    
                    if element_types:
                        print(f"🎯 Filtering by element types: {', '.join(element_types)}")
                    else:
                        print(f"⚠️  No valid element types found in: {type_str}")
                        print(f"Valid types: {', '.join(valid_types)}")
                except ValueError as e:
                    print(f"⚠️  Invalid element type: {e}")
                    print(f"Valid types: {', '.join(valid_types)}")
                break
            else:
                query_parts.append(args[i])
                i += 1
        
        query = " ".join(query_parts)
        return query, element_types
    
    def _show_config(self):
        """Show current configuration."""
        print("\n⚙️  Current Configuration")
        print("=" * 40)
        print(f"max_results: {self.config['max_results']} (number of results to return)")
        print(f"element_types: {self.config['element_types']} (filter by element types)")
        print(f"include_summary: {self.config['include_summary']} (include summary search)")
        print(f"include_full_text: {self.config['include_full_text']} (include full-text search)")
    
    def _show_config_params(self):
        """Show available configuration parameters."""
        print("\n⚙️  Available Parameters:")
        print("max_results, element_types, include_summary, include_full_text")


def main():
    """Main entry point."""
    print(__doc__)
    
    cli = HybridSearchCLI()
    cli.run()


if __name__ == "__main__":
    main()
