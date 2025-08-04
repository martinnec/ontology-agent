"""
Domain models for indexing and retrieval.

This module defines the core data structures used for indexing legal act elements
and managing search operations.
"""

from pydantic import BaseModel, Field, AnyUrl
from typing import Optional, List, Dict, Any
from enum import Enum
import xml.etree.ElementTree as ET
import re


class ElementType(str, Enum):
    """Types of legal structural elements."""
    LEGAL_ACT = "legal_act"
    PART = "part"
    CHAPTER = "chapter"
    DIVISION = "division"
    SECTION = "section"
    UNKNOWN = "unknown"


class IndexDoc(BaseModel):
    """
    A searchable document representing a legal act element.
    
    This class extracts and structures the searchable content from legal act elements
    for use in BM25 and FAISS indexes.
    """
    
    element_id: str = Field(..., description="Unique identifier for the element")
    title: str = Field(..., description="Title/heading of the element")
    summary: Optional[str] = Field(None, description="AI-generated summary of the element")
    summary_names: Optional[List[str]] = Field(None, description="Names of important concepts and relationships identified in the content")
    official_identifier: str = Field(..., description="Official legal identifier (e.g., '§ 2', 'čl. 15')")
    text_content: Optional[str] = Field(None, description="Full text content of the element")
    
    # Metadata for filtering and ranking
    level: int = Field(0, description="Hierarchical level in the document structure")
    element_type: ElementType = Field(ElementType.UNKNOWN, description="Type of legal element")
    parent_id: Optional[str] = Field(None, description="ID of parent element")
    child_ids: List[str] = Field(default_factory=list, description="IDs of child elements")
    
    # Additional metadata
    act_iri: Optional[str] = Field(None, description="IRI of the legal act this element belongs to")
    snapshot_id: Optional[str] = Field(None, description="Snapshot version of the source data")
    
    @classmethod
    def from_legal_element(cls, 
                          legal_element: Any,  # LegalStructuralElement from legislation.domain
                          level: int = 0,
                          element_type: ElementType = ElementType.UNKNOWN,
                          parent_id: Optional[str] = None,
                          act_iri: Optional[str] = None,
                          snapshot_id: Optional[str] = None) -> 'IndexDoc':
        """
        Extract searchable content from a legal act element.
        
        Args:
            legal_element: A LegalStructuralElement instance
            level: Hierarchical level in the document
            element_type: Type of the legal element
            parent_id: ID of the parent element
            act_iri: IRI of the legal act
            snapshot_id: Version snapshot identifier
            
        Returns:
            IndexDoc instance ready for indexing
        """
        # Extract child IDs if elements exist
        child_ids = []
        if hasattr(legal_element, 'elements') and legal_element.elements:
            child_ids = [str(child.id) for child in legal_element.elements]
        
        return cls(
            element_id=str(legal_element.id),
            title=legal_element.title,
            summary=legal_element.summary,
            summary_names=legal_element.summary_names,
            official_identifier=legal_element.officialIdentifier,
            text_content=legal_element.textContent,
            level=level,
            element_type=element_type,
            parent_id=parent_id,
            child_ids=child_ids,
            act_iri=act_iri,
            snapshot_id=snapshot_id
        )
    
    def get_searchable_text(self, include_content: bool = False) -> str:
        """
        Get the combined searchable text for this document.
        
        Args:
            include_content: Whether to include full text content
            
        Returns:
            Combined searchable text
        """
        parts = []
        
        # Add official identifier
        if self.official_identifier:
            parts.append(self.official_identifier)
        
        # Add title (weighted higher in search)
        if self.title:
            parts.append(self.title)
        
        # Add summary (weighted highest in search)
        if self.summary:
            parts.append(self.summary)
        
        # Optionally add full text content
        if include_content and self.text_content:
            parts.append(self.text_content)
        
        return " ".join(parts)
    
    def get_text_chunks(self, chunk_size: int = 500, overlap: int = 50) -> List[Dict[str, str]]:
        """
        Split text content into overlapping chunks for full-text indexing.
        
        For legal documents, handles two cases:
        1. Plain text: Uses simple word-based chunking
        2. Hierarchical XML: Extracts leaf fragments with full ancestral context
        
        Args:
            chunk_size: Maximum number of words per chunk
            overlap: Number of words to overlap between chunks
            
        Returns:
            List of dictionaries with chunk text and metadata
        """
        if not self.text_content:
            return []
        
        # Try to parse as hierarchical XML structure
        leaf_sequences = self._extract_leaf_sequences_from_xml(self.text_content)
        
        if not leaf_sequences:
            # Fallback to simple text chunking for non-structured content
            return self._create_simple_text_chunks(self.text_content, chunk_size, overlap)
        
        # Create chunks from hierarchical leaf sequences
        return self._create_hierarchical_chunks(leaf_sequences, chunk_size, overlap)
    
    def _extract_leaf_sequences_from_xml(self, xml_content: str) -> List[Dict[str, Any]]:
        """
        Extract leaf fragment sequences with full ancestral context.
        
        Each leaf fragment defines a text sequence T containing:
        - Text content of all ancestors from root to leaf
        - Text content of the leaf fragment itself
        - Ordered list of fragment IDs from root to leaf
        
        Args:
            xml_content: XML content with hierarchical <f> elements
            
        Returns:
            List of leaf sequence dictionaries with full context
        """
        try:
            # Wrap in root element if not already wrapped
            if not xml_content.strip().startswith('<'):
                return []
            
            # Parse XML
            root = ET.fromstring(xml_content)
            leaf_sequences = []
            
            def extract_leaf_sequences(element, ancestor_path=[]):
                """Recursively find leaf fragments and build their full context."""
                current_path = ancestor_path[:]
                
                # Add current element to path if it's an <f> element
                if element.tag == 'f':
                    fragment_id = element.get('id', '')
                    fragment_context = self._extract_fragment_context(fragment_id)
                    
                    current_path.append({
                        'id': fragment_id,
                        'context': fragment_context,
                        'text': self._extract_direct_text_from_element(element)
                    })
                
                # Check if this is a leaf <f> element (no <f> children)
                child_f_elements = [child for child in element if child.tag == 'f']
                
                if element.tag == 'f' and not child_f_elements:
                    # This is a leaf fragment - create sequence with full ancestral context
                    full_text_parts = []
                    fragment_ids = []
                    fragment_contexts = []
                    
                    # Collect text and IDs from root to leaf
                    for path_element in current_path:
                        if path_element['text'].strip():
                            full_text_parts.append(path_element['text'].strip())
                        fragment_ids.append(path_element['id'])
                        if path_element['context']:
                            fragment_contexts.append(path_element['context'])
                    
                    # Create the complete text sequence for this leaf
                    full_text = ' '.join(full_text_parts)
                    full_text = re.sub(r'\s+', ' ', full_text).strip()
                    
                    if full_text:
                        leaf_sequences.append({
                            'text': full_text,
                            'fragment_ids': fragment_ids,
                            'fragment_contexts': fragment_contexts,
                            'leaf_id': fragment_ids[-1] if fragment_ids else '',
                            'leaf_context': fragment_contexts[-1] if fragment_contexts else '',
                            'depth': len(fragment_ids),
                            'sequence_index': len(leaf_sequences)
                        })
                else:
                    # Continue recursion for non-leaf elements
                    for child in element:
                        extract_leaf_sequences(child, current_path)
            
            extract_leaf_sequences(root)
            return leaf_sequences
            
        except ET.ParseError:
            # If XML parsing fails, return empty list to fallback to simple chunking
            return []
    
    def _extract_direct_text_from_element(self, element) -> str:
        """
        Extract only the direct text content of an element (not from children).
        
        Args:
            element: XML element to extract text from
            
        Returns:
            Direct text content of the element
        """
        text_parts = []
        
        # Get direct text content (before any child elements)
        if element.text:
            text_parts.append(element.text.strip())
        
        # Get tail text after each child element (but not the child's content)
        for child in element:
            if child.tail:
                text_parts.append(child.tail.strip())
        
        # Join and clean up the text
        full_text = ' '.join(part for part in text_parts if part)
        full_text = re.sub(r'\s+', ' ', full_text).strip()
        
        return full_text
    
    def _extract_fragment_context(self, fragment_id: str) -> str:
        """
        Extract meaningful context from fragment ID URL.
        
        Args:
            fragment_id: Full fragment ID URL
            
        Returns:
            Simplified context string (e.g., "par_48_odst_1")
        """
        if not fragment_id:
            return ""
        
        # Extract the fragment part after the last '/'
        if '#' in fragment_id:
            context = fragment_id.split('#')[-1]
        else:
            context = fragment_id.split('/')[-1]
        
        # Keep only the structural part (remove long URL parts)
        # e.g., "cast_4/hlava_1/par_48/odst_1" -> "par_48_odst_1"
        parts = context.split('/')
        meaningful_parts = []
        for part in parts:
            if any(keyword in part for keyword in ['par', 'odst', 'pism', 'bod', 'cast', 'hlava']):
                meaningful_parts.append(part)
        
        return '_'.join(meaningful_parts[-2:]) if len(meaningful_parts) >= 2 else context
    
    def _create_hierarchical_chunks(self, leaf_sequences: List[Dict[str, Any]], 
                                  chunk_size: int, overlap: int) -> List[Dict[str, str]]:
        """
        Create chunks from hierarchical leaf sequences.
        
        Each leaf sequence represents the full context from root to leaf.
        Chunks maintain the hierarchical fragment ID path.
        
        Args:
            leaf_sequences: List of leaf sequence dictionaries
            chunk_size: Maximum words per chunk
            overlap: Words to overlap between chunks
            
        Returns:
            List of chunk dictionaries with hierarchical metadata
        """
        if not leaf_sequences:
            return []
        
        all_chunks = []
        global_chunk_num = 0
        
        for seq_idx, sequence in enumerate(leaf_sequences):
            sequence_text = sequence['text']
            words = sequence_text.split()
            
            if len(words) <= chunk_size:
                # Single chunk for this sequence
                chunk_dict = {
                    'text': sequence_text,
                    'chunk_id': f"{self.element_id}_seq_{seq_idx}_chunk_0",
                    'start_word': 0,
                    'end_word': len(words),
                    'element_id': self.element_id,
                    'sequence_index': seq_idx,
                    'fragment_ids': sequence['fragment_ids'],
                    'fragment_contexts': sequence['fragment_contexts'],
                    'leaf_fragment_id': sequence['leaf_id'],
                    'leaf_fragment_context': sequence['leaf_context'],
                    'depth': sequence['depth'],
                    'global_chunk_index': global_chunk_num
                }
                all_chunks.append(chunk_dict)
                global_chunk_num += 1
            else:
                # Multiple chunks for this sequence
                start = 0
                chunk_num = 0
                
                while start < len(words):
                    end = min(start + chunk_size, len(words))
                    chunk_text = " ".join(words[start:end])
                    
                    chunk_dict = {
                        'text': chunk_text,
                        'chunk_id': f"{self.element_id}_seq_{seq_idx}_chunk_{chunk_num}",
                        'start_word': start,
                        'end_word': end,
                        'element_id': self.element_id,
                        'sequence_index': seq_idx,
                        'fragment_ids': sequence['fragment_ids'],
                        'fragment_contexts': sequence['fragment_contexts'],
                        'leaf_fragment_id': sequence['leaf_id'],
                        'leaf_fragment_context': sequence['leaf_context'],
                        'depth': sequence['depth'],
                        'global_chunk_index': global_chunk_num
                    }
                    all_chunks.append(chunk_dict)
                    
                    if end >= len(words):
                        break
                        
                    start = end - overlap
                    chunk_num += 1
                    global_chunk_num += 1
        
        return all_chunks
    
    def _create_simple_text_chunks(self, text_content: str, chunk_size: int, 
                                 overlap: int) -> List[Dict[str, str]]:
        """
        Fallback method for simple text chunking when XML parsing fails.
        
        Args:
            text_content: Raw text content
            chunk_size: Maximum words per chunk
            overlap: Words to overlap
            
        Returns:
            List of chunk dictionaries
        """
        # Clean the text content by removing XML tags if present
        clean_text = re.sub(r'<[^>]+>', ' ', text_content)
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        
        if not clean_text:
            return []
        
        words = clean_text.split()
        if len(words) <= chunk_size:
            return [{
                'text': clean_text,
                'chunk_id': f"{self.element_id}_chunk_0",
                'start_word': 0,
                'end_word': len(words),
                'element_id': self.element_id,
                'sequence_index': 0,
                'fragment_ids': [],
                'fragment_contexts': ['simple_text'],
                'leaf_fragment_id': '',
                'leaf_fragment_context': 'simple_text',
                'depth': 0,
                'global_chunk_index': 0
            }]
        
        chunks = []
        start = 0
        chunk_num = 0
        
        while start < len(words):
            end = min(start + chunk_size, len(words))
            chunk_text = " ".join(words[start:end])
            
            chunks.append({
                'text': chunk_text,
                'chunk_id': f"{self.element_id}_chunk_{chunk_num}",
                'start_word': start,
                'end_word': end,
                'element_id': self.element_id,
                'sequence_index': 0,
                'fragment_ids': [],
                'fragment_contexts': ['simple_text'],
                'leaf_fragment_id': '',
                'leaf_fragment_context': 'simple_text',
                'depth': 0,
                'global_chunk_index': chunk_num
            })
            
            if end >= len(words):
                break
                
            start = end - overlap
            chunk_num += 1
        
        return chunks
    
    def get_weighted_fields(self) -> Dict[str, str]:
        """
        Get fields with their intended search weights.
        
        Returns:
            Dictionary mapping field names to their content
        """
        # Convert summary_names list to space-separated string
        summary_names_text = ""
        if self.summary_names:
            summary_names_text = " ".join(self.summary_names)
            
        return {
            'official_identifier': self.official_identifier or "",
            'title': self.title or "",
            'summary': self.summary or "",
            'summary_names': summary_names_text
        }


class TextChunk(BaseModel):
    """A chunk of text content for full-text indexing."""
    
    chunk_id: str = Field(..., description="Unique identifier for this chunk")
    element_id: str = Field(..., description="ID of the parent element")
    text: str = Field(..., description="The chunk text content")
    start_word: int = Field(..., description="Starting word position in original text")
    end_word: int = Field(..., description="Ending word position in original text")
    
    # Inherited metadata from parent element
    title: str = Field(..., description="Title of the parent element")
    summary: Optional[str] = Field(None, description="Summary of the parent element")
    official_identifier: str = Field(..., description="Official identifier of the parent element")
    level: int = Field(0, description="Hierarchical level of the parent element")
    element_type: ElementType = Field(ElementType.UNKNOWN, description="Type of the parent element")
    
    @classmethod
    def from_chunk_data(cls, chunk_data: Dict[str, str], parent_doc: IndexDoc) -> 'TextChunk':
        """Create TextChunk from chunk data and parent document."""
        return cls(
            chunk_id=chunk_data['chunk_id'],
            element_id=chunk_data['element_id'],
            text=chunk_data['text'],
            start_word=chunk_data['start_word'],
            end_word=chunk_data['end_word'],
            title=parent_doc.title,
            summary=parent_doc.summary,
            official_identifier=parent_doc.official_identifier,
            level=parent_doc.level,
            element_type=parent_doc.element_type
        )


class SearchResult(BaseModel):
    """Result from a search operation."""
    
    doc: IndexDoc = Field(..., description="The matched document")
    score: float = Field(..., description="Relevance score")
    rank: int = Field(..., description="Rank in the result list")
    
    # Additional search metadata
    matched_fields: List[str] = Field(default_factory=list, description="Fields that matched the query")
    snippet: Optional[str] = Field(None, description="Text snippet showing the match")


class SearchQuery(BaseModel):
    """A search query with parameters."""
    
    query: str = Field(..., description="The search query text")
    max_results: int = Field(10, description="Maximum number of results to return")
    
    # Filtering options
    element_types: Optional[List[ElementType]] = Field(None, description="Filter by element types")
    min_level: Optional[int] = Field(None, description="Minimum hierarchical level")
    max_level: Optional[int] = Field(None, description="Maximum hierarchical level")
    official_identifier_pattern: Optional[str] = Field(None, description="Regex pattern for official identifier")
    
    # Search strategy options
    use_semantic: bool = Field(True, description="Use semantic (FAISS) search")
    use_keyword: bool = Field(True, description="Use keyword (BM25) search")
    semantic_weight: float = Field(0.6, description="Weight for semantic search (0-1)")
    keyword_weight: float = Field(0.4, description="Weight for keyword search (0-1)")


class IndexMetadata(BaseModel):
    """Metadata about an index."""
    
    act_iri: str = Field(..., description="IRI of the indexed legal act")
    snapshot_id: str = Field(..., description="Snapshot version of the source data")
    created_at: str = Field(..., description="ISO timestamp when index was created")
    document_count: int = Field(..., description="Number of documents in the index")
    index_type: str = Field(..., description="Type of index (bm25, faiss, hybrid)")
    
    # Index-specific metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional index-specific metadata")
