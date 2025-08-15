from typing import List, Dict, Any
from collections import defaultdict
from pydantic import AnyUrl

from legislation.datasource_esel import DataSourceESEL
from legislation.service import LegislationService
from legislation.domain import LegalAct, LegalStructuralElement

DEFAULT_LLM_MODEL = "gpt-4.1-mini"

def _legislation_service() -> LegislationService:
    """Factory for LegislationService (lazy to avoid cost until tool used)."""
    return LegislationService(DataSourceESEL(), DEFAULT_LLM_MODEL)

# Initialize services
legislation_service = _legislation_service()


#@function_tool
def get_seed_terms(legal_act_id: str, k: int = 10, normalize_case: bool = False) -> List[Dict[str, Any]]:
    """
    Returns K most frequently appearing terms (seed terms) from a legal act.
    
    Seed terms are terms frequently occurring in the legal act, calculated
    based on term frequency with hierarchical weighting:
    - LegalSection: 1x weight
    - LegalDivision: 2x weight  
    - LegalChapter: 4x weight
    - LegalPart: 8x weight
    - LegalAct: 16x weight
    
    Term frequency TF(t,act) = f(t,act) / sum(f(t',act)) for all terms t'
    
    Args:
        legal_act_id: The IRI identifier of the legal act
        k: Number of top terms to return (default: 10)
        normalize_case: If True, combine terms that differ only in case (default: False)
        
    Returns:
        List of dictionaries containing term and frequency information:
        [{"term": str, "frequency": float, "raw_count": int}, ...]
    """
    # Get the legal act
    legal_act = legislation_service.get_legal_act(AnyUrl(legal_act_id))
    
    # Calculate weighted term frequencies
    term_counts = _calculate_weighted_term_frequencies(legal_act)
    
    # Optionally normalize case
    if normalize_case:
        term_counts = _normalize_case(term_counts)
    
    # Calculate total count for normalization
    total_count = sum(term_counts.values())
    
    if total_count == 0:
        return []
    
    # Calculate normalized frequencies and create result list
    term_frequencies = []
    for term, count in term_counts.items():
        frequency = count / total_count
        term_frequencies.append({
            "term": term,
            "frequency": frequency,
            "raw_count": count
        })
    
    # Sort by frequency (descending) and return top K
    term_frequencies.sort(key=lambda x: x["frequency"], reverse=True)
    return term_frequencies[:k]


def _normalize_case(term_counts: Dict[str, int]) -> Dict[str, int]:
    """
    Normalize term counts by combining terms that differ only in case.
    Keeps the most frequent case variant as the canonical form.
    
    Args:
        term_counts: Dictionary mapping terms to their counts
        
    Returns:
        Dictionary with case-normalized terms
    """
    # Group terms by lowercase version
    case_groups = defaultdict(list)
    for term, count in term_counts.items():
        case_groups[term.lower()].append((term, count))
    
    # For each group, pick the most frequent case variant
    normalized_counts = {}
    for lowercase_term, variants in case_groups.items():
        # Sort by count (descending) to get the most frequent variant first
        variants.sort(key=lambda x: x[1], reverse=True)
        
        # Use the most frequent case variant as canonical form
        canonical_term = variants[0][0]
        total_count = sum(count for term, count in variants)
        
        normalized_counts[canonical_term] = total_count
    
    return normalized_counts


def _calculate_weighted_term_frequencies(element: LegalStructuralElement) -> Dict[str, int]:
    """
    Recursively calculate weighted term frequencies from an element and its children.
    
    Args:
        element: The legal structural element to process
        
    Returns:
        Dictionary mapping terms to their weighted counts
    """
    term_counts = defaultdict(int)
    
    # Get the weight for this element type
    weight = _get_element_weight(element.elementType)
    
    # Add terms from this element's summary_names with appropriate weight
    if element.summary_names:
        for term in element.summary_names:
            if term and term.strip():  # Only count non-empty terms
                term_counts[term.strip()] += weight
    
    # Recursively process child elements
    if element.elements:
        for child in element.elements:
            child_counts = _calculate_weighted_term_frequencies(child)
            for term, count in child_counts.items():
                term_counts[term] += count
    
    return dict(term_counts)


def _get_element_weight(element_type: str) -> int:
    """
    Get the hierarchical weight for an element type.
    
    Args:
        element_type: The type of the legal element
        
    Returns:
        Weight multiplier (1, 2, 4, 8, or 16)
    """
    weight_map = {
        "LegalSection": 1,      # 2^0
        "LegalDivision": 2,     # 2^1  
        "LegalChapter": 4,      # 2^2
        "LegalPart": 8,         # 2^3
        "LegalAct": 16          # 2^4
    }
    
    return weight_map.get(element_type, 1)  # Default to 1 for unknown types
