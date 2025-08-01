from pydantic import AnyUrl
from typing import Optional

from .datasource import LegislationDataSource
from .domain import LegalAct, LegalStructuralElement
from .summarizer import LegislationSummarizer


class LegislationService:
    """
    Service class for managing legal acts and their structural elements.
    Provides high-level operations for retrieving legal acts and elements,
    with automatic summarization capabilities.
    """
    
    def __init__(self, datasource: LegislationDataSource, llm_model_identifier: str):
        """
        Initialize the legislation service.
        
        :param datasource: The datasource implementation to use for data access
        :param llm_model_identifier: String identifier of the LLM model for text processing
        """
        self.datasource = datasource
        self.summarizer = LegislationSummarizer(llm_model_identifier)
    
    def get_legal_act(self, legal_act_id: AnyUrl) -> LegalAct:
        """
        Retrieve a complete legal act by its unique identifier.
        If summaries are missing, they will be computed and the legal act will be stored.
        
        :param legal_act_id: Unique identifier for the legal act as IRI
        :return: LegalAct object with summaries
        """
        # Get the legal act from datasource
        legal_act = self.datasource.get_legal_act(legal_act_id)
        
        # Check if summaries are present
        if self._needs_summarization(legal_act):
            # Generate summaries
            legal_act = self.summarizer.summarize(legal_act)
            
            # Store the updated legal act with summaries
            self.datasource.store_legal_act(legal_act)
        
        return legal_act
    
    def get_legal_act_element(self, element_id: AnyUrl) -> LegalStructuralElement:
        """
        Retrieve a specific structural element of a legal act by its unique identifier.
        If summaries are missing for the containing legal act, they will be computed and stored.
        
        :param element_id: Unique identifier for the structural element as IRI
        :return: LegalStructuralElement object
        """
        # Get the element from datasource
        element = self.datasource.get_legal_act_element(element_id)
        
        # To check and compute summaries if needed, we need the whole legal act
        # Extract legal act ID from element ID and get the full legal act
        legal_act_id = self._extract_legal_act_id_from_element_id(element_id)
        legal_act = self.datasource.get_legal_act(legal_act_id)
        
        # Check if summaries are present
        if self._needs_summarization(legal_act):
            # Generate summaries for the whole legal act
            legal_act = self.summarizer.summarize(legal_act)
            
            # Store the updated legal act with summaries
            self.datasource.store_legal_act(legal_act)
            
            # Find and return the updated element
            updated_element = self._find_element_by_id(legal_act, str(element_id))
            if updated_element:
                return updated_element
        
        return element
    
    def _needs_summarization(self, legal_act: LegalAct) -> bool:
        """
        Check if a legal act or any of its elements need summarization.
        
        :param legal_act: The legal act to check
        :return: True if summarization is needed, False otherwise
        """
        return self._element_needs_summarization(legal_act)
    
    def _element_needs_summarization(self, element: LegalStructuralElement) -> bool:
        """
        Recursively check if an element or any of its sub-elements need summarization.
        
        :param element: The element to check
        :return: True if summarization is needed, False otherwise
        """
        # Check if this element needs a summary
        if (element.textContent or (element.elements and len(element.elements) > 0)) and not element.summary:
            return True
        
        # Check sub-elements recursively
        if element.elements:
            for sub_element in element.elements:
                if self._element_needs_summarization(sub_element):
                    return True
        
        return False
    
    def _extract_legal_act_id_from_element_id(self, element_id: AnyUrl) -> AnyUrl:
        """
        Extract the legal act ID from an element ID.
        
        :param element_id: The element identifier
        :return: The legal act identifier
        """
        element_id_str = str(element_id)
        
        # Handle section IDs (format: {legal_act_id}/par_{section_number})
        if '/par_' in element_id_str:
            return element_id_str.split('/par_')[0]
        
        # Handle other fragment IDs from SPARQL
        if 'esel-esb/eli/cz/sb/' in element_id_str:
            # Extract the base legal act URL
            parts = element_id_str.split('/')
            if len(parts) >= 7:
                return '/'.join(parts[:7])  # Get the base legal act URL
        
        # If we can't parse it, assume it's already a legal act ID or try direct lookup
        return element_id
    
    def _find_element_by_id(self, legal_act: LegalAct, element_id: str) -> Optional[LegalStructuralElement]:
        """
        Find an element by its ID within a legal act.
        
        :param legal_act: The legal act to search in
        :param element_id: The ID of the element to find
        :return: The found element or None
        """
        return self._search_element_by_id(legal_act, element_id)
    
    def _search_element_by_id(self, element: LegalStructuralElement, target_id: str) -> Optional[LegalStructuralElement]:
        """
        Recursively search for an element by its ID.
        
        :param element: The element to search in
        :param target_id: The ID to search for
        :return: The found element or None
        """
        if str(element.id) == target_id:
            return element
        
        if element.elements:
            for sub_element in element.elements:
                found = self._search_element_by_id(sub_element, target_id)
                if found:
                    return found
        
        return None
