"""
Index registry for managing available index builders.

This module provides a registry of available index types and their corresponding
builder classes, enabling pluggable index architecture.
"""

from typing import Dict, List, Type, Any, Optional
from abc import ABC, abstractmethod
from .domain import IndexDoc


class IndexBuilder(ABC):
    """Abstract base class for index builders."""
    
    @abstractmethod
    def build(self, documents: List[IndexDoc], output_dir: str, 
              act_identifier: str) -> Any:
        """
        Build an index from documents.
        
        Args:
            documents: List of IndexDoc objects
            output_dir: Directory to save the index
            act_identifier: Identifier for the legal act
            
        Returns:
            Built index instance
        """
        pass
    
    @abstractmethod
    def load(self, index_path: str) -> Any:
        """
        Load an existing index.
        
        Args:
            index_path: Path to the index files
            
        Returns:
            Loaded index instance
        """
        pass
    
    @abstractmethod
    def get_index_files(self, output_dir: str, act_identifier: str) -> List[str]:
        """
        Get list of files that make up the index.
        
        Args:
            output_dir: Directory containing the index
            act_identifier: Identifier for the legal act
            
        Returns:
            List of file paths
        """
        pass


class BM25IndexBuilder(IndexBuilder):
    """Builder for BM25 keyword indexes."""
    
    def build(self, documents: List[IndexDoc], output_dir: str, 
              act_identifier: str) -> Any:
        """Build BM25 index."""
        from .bm25 import BM25SummaryIndex
        
        # Create BM25 index
        index = BM25SummaryIndex()
        index.build(documents)
        
        # Save to the correct location (act-based directory structure)
        import os
        index_dir = os.path.join(output_dir, act_identifier, "bm25")
        os.makedirs(index_dir, exist_ok=True)
        index_path = os.path.join(index_dir, "bm25_index")
        index.save(index_path)
        
        return index
    
    def load(self, index_path: str) -> Any:
        """Load BM25 index."""
        from .bm25 import BM25SummaryIndex
        
        index = BM25SummaryIndex()
        index.load(index_path)
        return index
    
    def get_index_files(self, output_dir: str, act_identifier: str) -> List[str]:
        """Get BM25 index files."""
        import os
        index_dir = os.path.join(output_dir, act_identifier, "bm25")
        base_path = os.path.join(index_dir, "bm25_index")
        return [
            f"{base_path}.pkl",
            f"{base_path}_docs.json"
        ]


class BM25FullIndexBuilder(IndexBuilder):
    """Builder for BM25 full-text indexes."""
    
    def build(self, documents: List[IndexDoc], output_dir: str, 
              act_identifier: str) -> Any:
        """Build BM25 full-text index."""
        from .bm25_full import BM25FullIndex
        
        # Create BM25 full index
        index = BM25FullIndex()
        index.build(documents)
        
        # Save to the correct location (act-based directory structure)
        import os
        from pathlib import Path
        index_dir = os.path.join(output_dir, act_identifier, "bm25_full")
        os.makedirs(index_dir, exist_ok=True)
        index_path = Path(index_dir) / "bm25_full_index"
        index.save(index_path)
        
        return index
    
    def load(self, index_path: str) -> Any:
        """Load BM25 full-text index."""
        from .bm25_full import BM25FullIndex
        
        index = BM25FullIndex()
        index.load(index_path)
        return index
    
    def get_index_files(self, output_dir: str, act_identifier: str) -> List[str]:
        """Get BM25 full-text index files."""
        import os
        index_dir = os.path.join(output_dir, act_identifier, "bm25_full")
        base_path = os.path.join(index_dir, "bm25_full_index")
        return [
            f"{base_path}.pkl",
            f"{base_path}_chunks.json"
        ]


class FAISSIndexBuilder(IndexBuilder):
    """Builder for FAISS semantic indexes."""
    
    def build(self, documents: List[IndexDoc], output_dir: str, 
              act_identifier: str) -> Any:
        """Build FAISS index."""
        from .faiss_index import FAISSSummaryIndex
        
        # Create FAISS index
        index = FAISSSummaryIndex()
        index.build(documents)
        
        # Save to the correct location (act-based directory structure)
        import os
        index_dir = os.path.join(output_dir, act_identifier, "faiss")
        os.makedirs(index_dir, exist_ok=True)
        index_path = os.path.join(index_dir, "faiss_index")
        index.save(index_path)
        
        return index
    
    def load(self, index_path: str) -> Any:
        """Load FAISS index."""
        from .faiss_index import FAISSSummaryIndex
        
        index = FAISSSummaryIndex()
        index.load(index_path)
        return index
    
    def get_index_files(self, output_dir: str, act_identifier: str) -> List[str]:
        """Get FAISS index files."""
        import os
        index_dir = os.path.join(output_dir, act_identifier, "faiss")
        base_path = os.path.join(index_dir, "faiss_index")
        return [
            f"{base_path}.index",
            f"{base_path}_docs.json"
        ]


class FAISSFullIndexBuilder(IndexBuilder):
    """Builder for FAISS full-text semantic indexes."""
    
    def build(self, documents: List[IndexDoc], output_dir: str, 
              act_identifier: str) -> Any:
        """Build FAISS full-text index."""
        from .faiss_full import FAISSFullIndex
        
        # Create FAISS full index
        index = FAISSFullIndex()
        index.build(documents)
        
        # Save to the correct location (act-based directory structure)
        import os
        from pathlib import Path
        index_dir = os.path.join(output_dir, act_identifier, "faiss_full")
        os.makedirs(index_dir, exist_ok=True)
        index_path = Path(index_dir) / "faiss_full_index"
        index.save(index_path)
        
        return index
    
    def load(self, index_path: str) -> Any:
        """Load FAISS full-text index."""
        from .faiss_full import FAISSFullIndex
        
        index = FAISSFullIndex()
        index.load(index_path)
        return index
    
    def get_index_files(self, output_dir: str, act_identifier: str) -> List[str]:
        """Get FAISS full-text index files."""
        import os
        index_dir = os.path.join(output_dir, act_identifier, "faiss_full")
        base_path = os.path.join(index_dir, "faiss_full_index")
        return [
            f"{base_path}.index",
            f"{base_path}_chunks.json"
        ]


class IndexRegistry:
    """
    Registry for available index types and their builders.
    
    Provides a pluggable architecture for different index types while maintaining
    a consistent interface for building and loading indexes.
    """
    
    def __init__(self):
        """Initialize the registry with default index builders."""
        self._builders: Dict[str, IndexBuilder] = {
            'bm25': BM25IndexBuilder(),
            'bm25_full': BM25FullIndexBuilder(),
            'faiss': FAISSIndexBuilder(),
            'faiss_full': FAISSFullIndexBuilder(),
        }
    
    def register_builder(self, index_type: str, builder: IndexBuilder) -> None:
        """
        Register a new index builder.
        
        Args:
            index_type: Type identifier for the index
            builder: IndexBuilder instance
        """
        self._builders[index_type] = builder
    
    def get_builder(self, index_type: str) -> Optional[IndexBuilder]:
        """
        Get a builder for the specified index type.
        
        Args:
            index_type: Type of index
            
        Returns:
            IndexBuilder instance or None if not found
        """
        return self._builders.get(index_type)
    
    def get_available_types(self) -> List[str]:
        """
        Get list of available index types.
        
        Returns:
            List of index type names
        """
        return list(self._builders.keys())
    
    def has_builder(self, index_type: str) -> bool:
        """
        Check if a builder exists for the index type.
        
        Args:
            index_type: Type of index
            
        Returns:
            True if builder exists, False otherwise
        """
        return index_type in self._builders
