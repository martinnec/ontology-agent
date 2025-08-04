"""
High-level ontology service providing the public interface for all ontology operations.

This is the only public interface into the ontology module. All other components
are private implementation details.
"""

from typing import Dict, List, Any, Optional
from rdflib import URIRef

from .domain import OntologyClass, OntologyProperty, ClassNeighborhood, SimilarClass, OntologyStats
from .store import OntologyStore


class OntologyService:
    """High-level interface for ontology operations focused on practical data modeling."""
    
    def __init__(self, store: Optional[OntologyStore] = None):
        """Initialize the ontology service.
        
        Args:
            store: Optional ontology store. If None, creates a new one.
        """
        self.store = store if store is not None else OntologyStore()
    
    def get_working_ontology(self) -> Dict[str, Any]:
        """Get complete ontology overview for agent.
        
        Returns:
            Dict containing:
            - classes: List of all classes
            - object_properties: List of all object properties  
            - datatype_properties: List of all datatype properties
            - stats: Ontology statistics
        """
        return self.store.get_whole_ontology()
    
    def get_class_neighborhood(self, class_iri: str) -> ClassNeighborhood:
        """Get class with its immediate neighborhood of connected classes.
        
        Args:
            class_iri: IRI of the target class
            
        Returns:
            ClassNeighborhood with target class and all connected classes via properties
            
        Raises:
            ValueError: If class not found
        """
        class_uri = URIRef(class_iri)
        target_class = self.store.get_class(class_uri)
        if not target_class:
            raise ValueError(f"Class not found: {class_iri}")
            
        neighborhood_data = self.store.get_class_with_surroundings(class_uri)
        
        return ClassNeighborhood(
            target_class=target_class,
            connected_classes=neighborhood_data["connected_classes"],
            connecting_properties=neighborhood_data["connecting_properties"]
        )
    
    def get_similar_classes(self, class_iri: str, limit: int = 10) -> List[SimilarClass]:
        """Find classes semantically similar to the specified class.
        
        Args:
            class_iri: IRI of the target class
            limit: Maximum number of similar classes to return
            
        Returns:
            List of SimilarClass objects ordered by similarity score (descending)
            
        Raises:
            ValueError: If class not found
        """
        class_uri = URIRef(class_iri)
        target_class = self.store.get_class(class_uri)
        if not target_class:
            raise ValueError(f"Class not found: {class_iri}")
            
        similar_pairs = self.store.find_similar_classes(class_uri, limit)
        
        similar_classes = []
        for similar_iri, score in similar_pairs:
            similar_class = self.store.get_class(similar_iri)
            if similar_class:
                similar_classes.append(SimilarClass(
                    class_info=similar_class,
                    similarity_score=score,
                    similarity_basis="combined"  # labels + definitions + comments
                ))
        
        return similar_classes
    
    def get_property_details(self, property_iri: str) -> OntologyProperty:
        """Get property with domain/range details.
        
        Args:
            property_iri: IRI of the property
            
        Returns:
            OntologyProperty with complete details
            
        Raises:
            ValueError: If property not found
        """
        property_uri = URIRef(property_iri)
        prop = self.store.get_property_details(property_uri)
        if not prop:
            raise ValueError(f"Property not found: {property_iri}")
        return prop
    
    def get_class_hierarchy(self, class_iri: str) -> Dict[str, List[URIRef]]:
        """Get parent and subclasses of the specified class.
        
        Args:
            class_iri: IRI of the target class
            
        Returns:
            Dict with 'parents' and 'subclasses' lists
            
        Raises:
            ValueError: If class not found
        """
        class_uri = URIRef(class_iri)
        target_class = self.store.get_class(class_uri)
        if not target_class:
            raise ValueError(f"Class not found: {class_iri}")
            
        return self.store.get_class_hierarchy(class_uri)
    
    def search_by_concept(self, concept_text: str) -> List[Dict[str, Any]]:
        """Find classes/properties matching a concept using semantic similarity.
        
        Args:
            concept_text: Text describing the concept to search for (in Czech or English)
            
        Returns:
            List of matching classes and properties with relevance scores, sorted by relevance.
            Each item contains:
            {
                "type": "class|property",
                "iri": "concept_iri", 
                "score": relevance_score,
                "labels": {"cs": "...", "en": "..."},
                "definitions": {"cs": "...", "en": "..."},
                "additional_info": {...}  # class/property specific info
            }
        """
        if not concept_text.strip():
            return []
        
        results = []
        
        # Search classes using semantic similarity
        class_results = self._search_classes_by_concept(concept_text)
        results.extend(class_results)
        
        # Search properties using text matching and semantic similarity
        property_results = self._search_properties_by_concept(concept_text)
        results.extend(property_results)
        
        # Sort by relevance score (highest first)
        results.sort(key=lambda x: x["score"], reverse=True)
        
        return results
    
    def _search_classes_by_concept(self, concept_text: str) -> List[Dict[str, Any]]:
        """Search classes using semantic similarity.
        
        Args:
            concept_text: Text to search for
            
        Returns:
            List of matching classes with scores
        """
        results = []
        
        if not self.store.similarity_engine:
            # Fallback to text matching if no similarity engine
            return self._search_classes_by_text_matching(concept_text)
        
        try:
            # Use the similarity engine to find concepts
            # We'll create a temporary "query class" to find similar existing classes
            query_embedding = self.store.similarity_engine.compute_text_embedding(concept_text)
            
            if query_embedding is None:
                return self._search_classes_by_text_matching(concept_text)
            
            # Get all classes and compute similarities
            ontology = self.store.get_whole_ontology()
            classes = ontology.get("classes", [])
            
            for class_info in classes:
                class_iri = URIRef(class_info["iri"])
                ontology_class = self.store.get_class(class_iri)
                
                if not ontology_class:
                    continue
                
                # Get or compute class embedding
                class_embedding = self.store._ensure_class_embedding(class_iri)
                if class_embedding is None:
                    continue
                
                # Compute similarity
                similarity = self.store.similarity_engine.compute_similarity(
                    query_embedding, class_embedding
                )
                
                # Only include if similarity is above threshold
                if similarity >= 0.3:  # Configurable threshold
                    results.append({
                        "type": "class",
                        "iri": str(class_iri),
                        "score": float(similarity),
                        "labels": ontology_class.labels,
                        "definitions": ontology_class.definitions,
                        "additional_info": {
                            "parent_classes": [str(p) for p in ontology_class.parent_classes],
                            "subclasses": [str(s) for s in ontology_class.subclasses],
                            "source_elements": ontology_class.source_elements
                        }
                    })
            
        except Exception as e:
            print(f"Error in semantic search: {e}")
            return self._search_classes_by_text_matching(concept_text)
        
        return results
    
    def _search_classes_by_text_matching(self, concept_text: str) -> List[Dict[str, Any]]:
        """Fallback text matching for classes when semantic similarity is not available.
        
        Args:
            concept_text: Text to search for
            
        Returns:
            List of matching classes with text-based scores
        """
        results = []
        concept_lower = concept_text.lower()
        
        ontology = self.store.get_whole_ontology()
        classes = ontology.get("classes", [])
        
        for class_info in classes:
            class_iri = URIRef(class_info["iri"])
            ontology_class = self.store.get_class(class_iri)
            
            if not ontology_class:
                continue
            
            # Check labels and definitions for text matches
            score = 0.0
            
            # Check labels
            for label in ontology_class.labels.values():
                if concept_lower in label.lower():
                    score += 0.8  # High score for label match
                elif any(word in label.lower() for word in concept_lower.split()):
                    score += 0.4  # Medium score for word match
            
            # Check definitions
            for definition in ontology_class.definitions.values():
                if concept_lower in definition.lower():
                    score += 0.6  # Medium-high score for definition match
                elif any(word in definition.lower() for word in concept_lower.split()):
                    score += 0.2  # Low score for word match
            
            if score > 0:
                results.append({
                    "type": "class",
                    "iri": str(class_iri),
                    "score": min(score, 1.0),  # Cap at 1.0
                    "labels": ontology_class.labels,
                    "definitions": ontology_class.definitions,
                    "additional_info": {
                        "parent_classes": [str(p) for p in ontology_class.parent_classes],
                        "subclasses": [str(s) for s in ontology_class.subclasses],
                        "source_elements": ontology_class.source_elements
                    }
                })
        
        return results
    
    def _search_properties_by_concept(self, concept_text: str) -> List[Dict[str, Any]]:
        """Search properties using text matching.
        
        Args:
            concept_text: Text to search for
            
        Returns:
            List of matching properties with scores
        """
        results = []
        concept_lower = concept_text.lower()
        
        ontology = self.store.get_whole_ontology()
        all_properties = ontology.get("object_properties", []) + ontology.get("datatype_properties", [])
        
        for prop_info in all_properties:
            prop_iri = URIRef(prop_info["iri"])
            ontology_property = self.store.get_property_details(prop_iri)
            
            if not ontology_property:
                continue
            
            # Check labels and definitions for text matches
            score = 0.0
            
            # Check labels
            for label in ontology_property.labels.values():
                if concept_lower in label.lower():
                    score += 0.8  # High score for label match
                elif any(word in label.lower() for word in concept_lower.split()):
                    score += 0.4  # Medium score for word match
            
            # Check definitions
            for definition in ontology_property.definitions.values():
                if concept_lower in definition.lower():
                    score += 0.6  # Medium-high score for definition match
                elif any(word in definition.lower() for word in concept_lower.split()):
                    score += 0.2  # Low score for word match
            
            if score > 0:
                results.append({
                    "type": "property",
                    "iri": str(prop_iri),
                    "score": min(score, 1.0),  # Cap at 1.0
                    "labels": ontology_property.labels,
                    "definitions": ontology_property.definitions,
                    "additional_info": {
                        "property_type": ontology_property.property_type,
                        "domain": str(ontology_property.domain),
                        "range": str(ontology_property.range),
                        "source_elements": ontology_property.source_elements
                    }
                })
        
        return results
    
    def add_extraction_results(self, extracted_concepts: List[Dict[str, Any]]) -> bool:
        """Add LLM-extracted concepts as simple classes/properties.
        
        Args:
            extracted_concepts: List of extracted concept dictionaries from LLM
                Expected format for classes:
                {
                    "type": "class",
                    "name_cs": "Czech name",
                    "name_en": "English name", 
                    "definition_cs": "Czech definition",
                    "definition_en": "English definition",
                    "comment_cs": "Czech comment",
                    "comment_en": "English comment",
                    "parent_class": "parent_iri_or_null",
                    "source_element": "source_reference"
                }
                Expected format for properties:
                {
                    "type": "property",
                    "property_type": "ObjectProperty|DatatypeProperty", 
                    "name_cs": "Czech name",
                    "name_en": "English name",
                    "definition_cs": "Czech definition", 
                    "definition_en": "English definition",
                    "comment_cs": "Czech comment",
                    "comment_en": "English comment",
                    "domain": "domain_class_iri",
                    "range": "range_class_or_datatype_iri",
                    "source_element": "source_reference"
                }
            
        Returns:
            True if successfully added, False otherwise
        """
        try:
            added_count = 0
            
            for concept in extracted_concepts:
                concept_type = concept.get("type", "").lower()
                
                if concept_type == "class":
                    success = self._add_extracted_class(concept)
                    if success:
                        added_count += 1
                elif concept_type == "property":
                    success = self._add_extracted_property(concept)
                    if success:
                        added_count += 1
                else:
                    print(f"Warning: Unknown concept type '{concept_type}', skipping")
                    continue
            
            print(f"Successfully added {added_count}/{len(extracted_concepts)} extracted concepts")
            return added_count > 0
            
        except Exception as e:
            print(f"Error adding extraction results: {e}")
            return False
    
    def _add_extracted_class(self, concept: Dict[str, Any]) -> bool:
        """Add a single extracted class to the ontology.
        
        Args:
            concept: Dictionary containing class information
            
        Returns:
            True if successfully added, False otherwise
        """
        try:
            # Generate IRI from name
            name_en = concept.get("name_en", concept.get("name_cs", ""))
            if not name_en:
                print("Error: Class must have at least name_en or name_cs")
                return False
                
            # Create a clean IRI from the name
            clean_name = "".join(c for c in name_en if c.isalnum())
            class_iri = URIRef(f"https://example.org/ontology/{clean_name}")
            
            # Check if class already exists
            if self.store.get_class(class_iri):
                print(f"Class {class_iri} already exists, skipping")
                return False
            
            # Build labels
            labels = {}
            if concept.get("name_cs"):
                labels["cs"] = concept["name_cs"]
            if concept.get("name_en"):
                labels["en"] = concept["name_en"]
            
            # Build definitions
            definitions = {}
            if concept.get("definition_cs"):
                definitions["cs"] = concept["definition_cs"]
            if concept.get("definition_en"):
                definitions["en"] = concept["definition_en"]
            
            # Build comments
            comments = {}
            if concept.get("comment_cs"):
                comments["cs"] = concept["comment_cs"]
            if concept.get("comment_en"):
                comments["en"] = concept["comment_en"]
            
            # Handle parent class
            parent_classes = []
            if concept.get("parent_class"):
                parent_classes.append(URIRef(concept["parent_class"]))
            
            # Create ontology class
            ontology_class = OntologyClass(
                iri=class_iri,
                labels=labels,
                definitions=definitions,
                comments=comments,
                parent_classes=parent_classes,
                subclasses=[],
                datatype_properties=[],
                object_properties_out=[],
                object_properties_in=[],
                source_elements=[concept.get("source_element", "llm-extraction")]
            )
            
            # Add to store
            return self.store.add_class(ontology_class)
            
        except Exception as e:
            print(f"Error adding extracted class: {e}")
            return False
    
    def _add_extracted_property(self, concept: Dict[str, Any]) -> bool:
        """Add a single extracted property to the ontology.
        
        Args:
            concept: Dictionary containing property information
            
        Returns:
            True if successfully added, False otherwise
        """
        try:
            # Generate IRI from name
            name_en = concept.get("name_en", concept.get("name_cs", ""))
            if not name_en:
                print("Error: Property must have at least name_en or name_cs")
                return False
                
            # Create a clean IRI from the name
            clean_name = "".join(c for c in name_en if c.isalnum())
            prop_iri = URIRef(f"https://example.org/ontology/{clean_name}")
            
            # Check if property already exists
            if self.store.get_property_details(prop_iri):
                print(f"Property {prop_iri} already exists, skipping")
                return False
            
            # Validate property type
            property_type = concept.get("property_type", "")
            if property_type not in ["ObjectProperty", "DatatypeProperty"]:
                print(f"Error: Invalid property type '{property_type}'")
                return False
            
            # Build labels
            labels = {}
            if concept.get("name_cs"):
                labels["cs"] = concept["name_cs"]
            if concept.get("name_en"):
                labels["en"] = concept["name_en"]
            
            # Build definitions
            definitions = {}
            if concept.get("definition_cs"):
                definitions["cs"] = concept["definition_cs"]
            if concept.get("definition_en"):
                definitions["en"] = concept["definition_en"]
            
            # Build comments
            comments = {}
            if concept.get("comment_cs"):
                comments["cs"] = concept["comment_cs"]
            if concept.get("comment_en"):
                comments["en"] = concept["comment_en"]
            
            # Handle domain and range
            domain = URIRef(concept.get("domain", ""))
            range_uri = concept.get("range", "")
            
            # For datatype properties, range might be XSD type
            if property_type == "DatatypeProperty" and not range_uri.startswith("http"):
                range_uri = f"http://www.w3.org/2001/XMLSchema#{range_uri}"
            
            range_ref = URIRef(range_uri)
            
            # Create ontology property
            ontology_property = OntologyProperty(
                iri=prop_iri,
                labels=labels,
                definitions=definitions,
                comments=comments,
                property_type=property_type,
                domain=domain,
                range=range_ref,
                source_elements=[concept.get("source_element", "llm-extraction")]
            )
            
            # Add to store
            return self.store.add_property(ontology_property)
            
        except Exception as e:
            print(f"Error adding extracted property: {e}")
            return False
