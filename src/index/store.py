"""
Index storage and persistence management.

This module handles the storage, loading, and discovery of indexes on the file system,
providing a consistent interface for index persistence operations.
"""

import os
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from .domain import IndexDoc


class IndexMetadata:
    """Metadata for tracking index state and versioning."""
    
    def __init__(self, act_iri: str, snapshot_id: Optional[str] = None,
                 created_at: Optional[datetime] = None, 
                 document_count: int = 0,
                 index_types: Optional[List[str]] = None):
        """
        Initialize index metadata.
        
        Args:
            act_iri: IRI of the legal act
            snapshot_id: Snapshot version identifier
            created_at: Creation timestamp
            document_count: Number of documents indexed
            index_types: List of available index types
        """
        self.act_iri = act_iri
        self.snapshot_id = snapshot_id
        self.created_at = created_at or datetime.now()
        self.document_count = document_count
        self.index_types = index_types or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        return {
            'act_iri': self.act_iri,
            'snapshot_id': self.snapshot_id,
            'created_at': self.created_at.isoformat(),
            'document_count': self.document_count,
            'index_types': self.index_types
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IndexMetadata':
        """Create metadata from dictionary."""
        created_at = None
        if data.get('created_at'):
            created_at = datetime.fromisoformat(data['created_at'])
        
        return cls(
            act_iri=data['act_iri'],
            snapshot_id=data.get('snapshot_id'),
            created_at=created_at,
            document_count=data.get('document_count', 0),
            index_types=data.get('index_types', [])
        )


class IndexStore:
    """
    Manages index storage and retrieval on the file system.
    
    Provides methods for checking index existence, loading/saving metadata,
    and managing the standardized directory structure for indexes.
    """
    
    def __init__(self, base_output_dir: str = "./indexes"):
        """
        Initialize the index store.
        
        Args:
            base_output_dir: Base directory for storing indexes
        """
        self.base_output_dir = base_output_dir
        self._ensure_base_directory()
    
    def _ensure_base_directory(self) -> None:
        """Ensure the base output directory exists."""
        os.makedirs(self.base_output_dir, exist_ok=True)
    
    def get_act_directory(self, act_identifier: str) -> str:
        """
        Get the directory path for a specific legal act's indexes.
        
        Args:
            act_identifier: Identifier for the legal act
            
        Returns:
            Directory path for the act's indexes
        """
        # Sanitize the identifier for file system
        safe_identifier = act_identifier.replace(":", "_").replace("/", "_")
        return os.path.join(self.base_output_dir, safe_identifier)
    
    def get_index_directory(self, act_identifier: str, index_type: str) -> str:
        """
        Get the directory path for a specific index type.
        
        Args:
            act_identifier: Identifier for the legal act
            index_type: Type of index
            
        Returns:
            Directory path for the index
        """
        act_dir = self.get_act_directory(act_identifier)
        return os.path.join(act_dir, index_type)
    
    def index_exists(self, act_identifier: str, index_type: str,
                    required_files: List[str]) -> bool:
        """
        Check if an index exists by verifying all required files are present.
        
        Args:
            act_identifier: Identifier for the legal act
            index_type: Type of index
            required_files: List of required file paths
            
        Returns:
            True if all required files exist, False otherwise
        """
        for file_path in required_files:
            if not os.path.exists(file_path):
                return False
        return True
    
    def get_metadata_path(self, act_identifier: str) -> str:
        """
        Get the path to the metadata file for an act.
        
        Args:
            act_identifier: Identifier for the legal act
            
        Returns:
            Path to metadata file
        """
        act_dir = self.get_act_directory(act_identifier)
        return os.path.join(act_dir, "metadata.json")
    
    def load_metadata(self, act_identifier: str) -> Optional[IndexMetadata]:
        """
        Load metadata for an act's indexes.
        
        Args:
            act_identifier: Identifier for the legal act
            
        Returns:
            IndexMetadata or None if not found
        """
        metadata_path = self.get_metadata_path(act_identifier)
        
        if not os.path.exists(metadata_path):
            return None
        
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return IndexMetadata.from_dict(data)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Warning: Could not load metadata from {metadata_path}: {e}")
            return None
    
    def save_metadata(self, act_identifier: str, metadata: IndexMetadata) -> None:
        """
        Save metadata for an act's indexes.
        
        Args:
            act_identifier: Identifier for the legal act
            metadata: IndexMetadata to save
        """
        act_dir = self.get_act_directory(act_identifier)
        os.makedirs(act_dir, exist_ok=True)
        
        metadata_path = self.get_metadata_path(act_identifier)
        
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata.to_dict(), f, indent=2, ensure_ascii=False)
    
    def clear_act_indexes(self, act_identifier: str) -> None:
        """
        Clear all indexes for a specific act.
        
        Args:
            act_identifier: Identifier for the legal act
        """
        import shutil
        
        # Clear the act-specific directory which contains all index subdirectories
        act_dir = self.get_act_directory(act_identifier)
        if os.path.exists(act_dir):
            shutil.rmtree(act_dir)
    
    def get_act_identifiers(self) -> List[str]:
        """
        Get list of all act identifiers that have indexes.
        
        Returns:
            List of act identifiers
        """
        if not os.path.exists(self.base_output_dir):
            return []
        
        identifiers = []
        for item in os.listdir(self.base_output_dir):
            item_path = os.path.join(self.base_output_dir, item)
            if os.path.isdir(item_path):
                # Check if it has a metadata file
                metadata_path = os.path.join(item_path, "metadata.json")
                if os.path.exists(metadata_path):
                    identifiers.append(item)
        
        return identifiers
    
    def ensure_index_directory(self, act_identifier: str, index_type: str) -> str:
        """
        Ensure the directory for an index type exists.
        
        Args:
            act_identifier: Identifier for the legal act
            index_type: Type of index
            
        Returns:
            Directory path for the index
        """
        index_dir = self.get_index_directory(act_identifier, index_type)
        os.makedirs(index_dir, exist_ok=True)
        return index_dir
