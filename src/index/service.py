"""
Index service providing unified access to index management.

This module provides the main public interface for building, loading, and managing
indexes for legal acts. It coordinates between the processor, registry, store, and
collection components to provide a clean, consistent API.
"""

import os
from pathlib import Path
from typing import List, Optional, Union
from .domain import IndexDoc
from .processor import DocumentProcessor
from .registry import IndexRegistry
from .store import IndexStore, IndexMetadata
from .collection import IndexCollection


class IndexService:
    """
    Main service for index management operations.
    
    Provides the primary public interface for the index module, coordinating
    between internal components to build, load, and manage indexes for legal acts.
    """
    
    def __init__(self, output_dir: str = "./indexes"):
        """
        Initialize the index service.
        
        Args:
            output_dir: Base directory for storing indexes
        """
        self.processor = DocumentProcessor()
        self.registry = IndexRegistry()
        self.store = IndexStore(output_dir)
        self.output_dir = output_dir
    
    def get_indexes(self, legal_act, force_rebuild: bool = False) -> IndexCollection:
        """
        Get all indexes for a legal act, building them if necessary.
        
        Args:
            legal_act: LegalAct domain object from legislation module
            force_rebuild: Whether to rebuild indexes even if they exist
            
        Returns:
            IndexCollection containing all available indexes
        """
        # Extract act identifier from legal act
        act_identifier = self._get_act_identifier(legal_act)
        act_iri = str(legal_act.id)
        
        # Create collection
        collection = IndexCollection(act_iri=act_iri)
        
        # Check if we need to build or can load existing indexes
        if force_rebuild or not self._all_indexes_exist(act_identifier):
            return self._build_all_indexes(legal_act, collection)
        else:
            return self._load_existing_indexes(act_identifier, collection)
    
    def build_indexes(self, legal_act, 
                     index_types: List[str] = None) -> IndexCollection:
        """
        Build specific indexes for a legal act.
        
        Args:
            legal_act: LegalAct domain object from legislation module
            index_types: List of index types to build, or None for all types
            
        Returns:
            IndexCollection containing the built indexes
        """
        act_identifier = self._get_act_identifier(legal_act)
        act_iri = str(legal_act.id)
        
        # Create collection
        collection = IndexCollection(act_iri=act_iri)
        
        # Get index types to build
        if index_types is None:
            index_types = self.registry.get_available_types()
        elif isinstance(index_types, str):
            index_types = [index_types]
        
        # Process legal act to documents
        documents = self.processor.process_legal_act(legal_act, act_iri=act_iri)
        collection.set_documents(documents)
        
        # Build each requested index type
        built_types = []
        for index_type in index_types:
            if self.registry.has_builder(index_type):
                index_instance = self._build_single_index(
                    index_type, documents, act_identifier
                )
                if index_instance:
                    collection.add_index(index_type, index_instance)
                    built_types.append(index_type)
        
        # Update metadata
        self._update_metadata(act_identifier, act_iri, documents, built_types)
        
        return collection
    
    def index_exists(self, legal_act, index_type: str) -> bool:
        """
        Check if a specific index exists for a legal act.
        
        Args:
            legal_act: LegalAct domain object from legislation module
            index_type: Type of index to check
            
        Returns:
            True if the index exists, False otherwise
        """
        act_identifier = self._get_act_identifier(legal_act)
        return self._index_type_exists(act_identifier, index_type)
    
    def clear_indexes(self, legal_act) -> None:
        """
        Clear all indexes for a legal act.
        
        Args:
            legal_act: LegalAct domain object from legislation module
        """
        act_identifier = self._get_act_identifier(legal_act)
        self.store.clear_act_indexes(act_identifier)
    
    def get_available_index_types(self) -> List[str]:
        """
        Get list of available index types.
        
        Returns:
            List of index type names
        """
        return self.registry.get_available_types()
    
    def _get_act_identifier(self, legal_act) -> str:
        """
        Extract a file-safe identifier from a legal act.
        
        Args:
            legal_act: LegalAct domain object
            
        Returns:
            Safe identifier for file system use in format: [NUMBER]-[YEAR]-[VALID-FROM-DATE]
        """
        # Use the ID from the legal act
        act_id = str(legal_act.id)
        
        # Extract the three key parts from the IRI pattern:
        # https://opendata.eselpoint.cz/esel-esb/eli/cz/sb/[ISSUE-YEAR]/[NUMBER]/[VALID-FROM-DATE]
        if "/" in act_id:
            parts = act_id.split("/")
            if len(parts) >= 3:
                # Get the last three parts: [ISSUE-YEAR], [NUMBER], [VALID-FROM-DATE]
                issue_year = parts[-3]
                number = parts[-2] 
                valid_from_date = parts[-1]
                # Format as [NUMBER]-[YEAR]-[VALID-FROM-DATE]
                safe_id = f"{number}-{issue_year}-{valid_from_date}"
                return safe_id
        
        # Fallback: use the last part and make it file-system safe
        if "/" in act_id:
            act_id = act_id.split("/")[-1]
        
        # Replace unsafe characters
        safe_id = act_id.replace(":", "_").replace("/", "_").replace("\\", "_")
        return safe_id
    
    def _all_indexes_exist(self, act_identifier: str) -> bool:
        """Check if all index types exist for an act."""
        for index_type in self.registry.get_available_types():
            if not self._index_type_exists(act_identifier, index_type):
                return False
        return True
    
    def _index_type_exists(self, act_identifier: str, index_type: str) -> bool:
        """Check if a specific index type exists for an act."""
        builder = self.registry.get_builder(index_type)
        if not builder:
            return False
        
        required_files = builder.get_index_files(self.output_dir, act_identifier)
        return self.store.index_exists(act_identifier, index_type, required_files)
    
    def _build_all_indexes(self, legal_act, collection: IndexCollection) -> IndexCollection:
        """Build all available index types."""
        return self.build_indexes(legal_act, index_types=None)
    
    def _load_existing_indexes(self, act_identifier: str, 
                             collection: IndexCollection) -> IndexCollection:
        """Load all existing indexes for an act."""
        # Load metadata to get document information
        metadata = self.store.load_metadata(act_identifier)
        
        # Load each available index type
        for index_type in self.registry.get_available_types():
            if self._index_type_exists(act_identifier, index_type):
                index_instance = self._load_single_index(index_type, act_identifier)
                if index_instance:
                    collection.add_index(index_type, index_instance)
        
        return collection
    
    def _build_single_index(self, index_type: str, documents: List[IndexDoc],
                           act_identifier: str) -> Optional[object]:
        """Build a single index type."""
        builder = self.registry.get_builder(index_type)
        if not builder:
            print(f"Warning: No builder available for index type '{index_type}'")
            return None
        
        try:
            # Ensure directory exists
            self.store.ensure_index_directory(act_identifier, index_type)
            
            # Build the index
            index_instance = builder.build(documents, self.output_dir, act_identifier)
            print(f"✓ Built {index_type} index for {act_identifier}")
            return index_instance
            
        except Exception as e:
            print(f"✗ Failed to build {index_type} index for {act_identifier}: {e}")
            return None
    
    def _load_single_index(self, index_type: str, act_identifier: str) -> Optional[object]:
        """Load a single index type."""
        builder = self.registry.get_builder(index_type)
        if not builder:
            return None
        
        try:
            index_dir = self.store.get_index_directory(act_identifier, index_type)
            
            # Construct the specific index path based on index type
            # This matches the path structure used in the build method
            if index_type == "bm25":
                index_path = os.path.join(index_dir, "bm25_index")
            elif index_type == "bm25_full":
                index_path = Path(index_dir) / "bm25_full_index"
            elif index_type == "faiss":
                index_path = os.path.join(index_dir, "faiss_index")
            elif index_type == "faiss_full":
                index_path = Path(index_dir) / "faiss_full_index"
            else:
                # Fallback to the directory itself
                index_path = index_dir
            
            index_instance = builder.load(index_path)
            return index_instance
            
        except Exception as e:
            print(f"Warning: Failed to load {index_type} index for {act_identifier}: {e}")
            return None
    
    def _update_metadata(self, act_identifier: str, act_iri: str,
                        documents: List[IndexDoc], built_types: List[str]) -> None:
        """Update metadata after building indexes."""
        # Load existing metadata or create new
        metadata = self.store.load_metadata(act_identifier)
        if metadata is None:
            metadata = IndexMetadata(act_iri=act_iri)
        
        # Update metadata
        metadata.document_count = len(documents)
        
        # Update index types (merge with existing)
        existing_types = set(metadata.index_types)
        new_types = set(built_types)
        metadata.index_types = list(existing_types.union(new_types))
        
        # Save updated metadata
        self.store.save_metadata(act_identifier, metadata)
