"""
Domain models for the ontology module.

These models represent the core ontology entities and their relationships
for practical data modeling extracted from legal acts.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Any
from rdflib import URIRef


@dataclass
class OntologyClass:
    """Represents a class in the ontology with all its properties and relationships."""
    
    iri: URIRef
    labels: Dict[str, str]              # language -> label (e.g., {"cs": "Vozidlo", "en": "Vehicle"})
    definitions: Dict[str, str]         # language -> definition
    comments: Dict[str, str]            # language -> additional comments
    parent_classes: List[URIRef]        # parent classes (rdfs:subClassOf)
    subclasses: List[URIRef]           # child classes
    datatype_properties: List[URIRef]   # properties with literal values
    object_properties_out: List[URIRef] # relationships to other classes (outgoing)
    object_properties_in: List[URIRef]  # incoming relationships from other classes
    source_elements: List[str]          # provenance to legal elements (IRIs)


@dataclass 
class OntologyProperty:
    """Represents a property (object or datatype) in the ontology."""
    
    iri: URIRef
    labels: Dict[str, str]              # language -> label
    definitions: Dict[str, str]         # language -> definition
    comments: Dict[str, str]            # language -> comments
    property_type: str                  # "ObjectProperty" | "DatatypeProperty"
    domain: Optional[URIRef]            # source class
    range: Optional[URIRef]             # target class or datatype
    source_elements: List[str]          # provenance to legal elements (IRIs)


@dataclass
class ClassNeighborhood:
    """Represents a class with its immediate neighborhood of connected classes."""
    
    target_class: OntologyClass
    connected_classes: Dict[str, OntologyClass]      # IRI -> connected class
    connecting_properties: Dict[str, OntologyProperty]  # IRI -> connecting property


@dataclass
class SimilarClass:
    """Represents a class similar to a target class with similarity score."""
    
    class_info: OntologyClass
    similarity_score: float             # 0.0 to 1.0
    similarity_basis: str               # "labels", "definitions", "combined"


@dataclass
class OntologyStats:
    """Statistics about the ontology content."""
    
    total_classes: int
    total_object_properties: int
    total_datatype_properties: int
    total_triples: int
    classes_with_definitions: int
    properties_with_domain_range: int
