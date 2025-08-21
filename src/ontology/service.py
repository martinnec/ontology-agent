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
    
    def add_class(self, 
                  iri: str,
                  name_cs: str = "", 
                  name_en: str = "",
                  definition_cs: str = "",
                  definition_en: str = "",
                  comment_cs: str = "",
                  comment_en: str = "",
                  parent_class: str = "",
                  source_element: str = "agent-extracted") -> bool:
        """Add a new class to the ontology.
        
        Args:
            iri: IRI for the class (if empty, will be generated from name_en or name_cs)
            name_cs: Czech name/label for the class
            name_en: English name/label for the class
            definition_cs: Czech definition of the class
            definition_en: English definition of the class
            comment_cs: Czech comment about the class
            comment_en: English comment about the class
            parent_class: IRI of parent class (optional)
            source_element: Source reference for the class
            
        Returns:
            True if successfully added, False otherwise
        """
        try:
            # Generate IRI if not provided
            if not iri:
                name = name_en or name_cs
                if not name:
                    print("Error: Must provide either iri or at least one name (name_en/name_cs)")
                    return False
                clean_name = "".join(c for c in name if c.isalnum())
                iri = f"https://example.org/ontology/{clean_name}"
            
            class_iri = URIRef(iri)
            
            # Check if class already exists
            if self.store.get_class(class_iri):
                print(f"Class {iri} already exists")
                return False
            
            # Build labels
            labels = {}
            if name_cs:
                labels["cs"] = name_cs
            if name_en:
                labels["en"] = name_en
            
            # Build definitions
            definitions = {}
            if definition_cs:
                definitions["cs"] = definition_cs
            if definition_en:
                definitions["en"] = definition_en
            
            # Build comments
            comments = {}
            if comment_cs:
                comments["cs"] = comment_cs
            if comment_en:
                comments["en"] = comment_en
            
            # Handle parent class
            parent_classes = []
            if parent_class:
                parent_classes.append(URIRef(parent_class))
            
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
                source_elements=[source_element]
            )
            
            return self.store.add_class(ontology_class)
            
        except Exception as e:
            print(f"Error adding class: {e}")
            return False

    def update_class(self,
                     iri: str,
                     name_cs: str = None, 
                     name_en: str = None,
                     definition_cs: str = None,
                     definition_en: str = None,
                     comment_cs: str = None,
                     comment_en: str = None,
                     parent_class: str = None,
                     source_element: str = None) -> bool:
        """Update an existing class in the ontology.
        
        Args:
            iri: IRI of the class to update
            name_cs: Czech name/label for the class (None = don't change)
            name_en: English name/label for the class (None = don't change)
            definition_cs: Czech definition of the class (None = don't change)
            definition_en: English definition of the class (None = don't change)
            comment_cs: Czech comment about the class (None = don't change)
            comment_en: English comment about the class (None = don't change)
            parent_class: IRI of parent class (None = don't change, "" = remove parent)
            source_element: Source reference for the class (None = don't change)
            
        Returns:
            True if successfully updated, False otherwise
        """
        try:
            class_iri = URIRef(iri)
            
            # Check if class exists
            existing_class = self.store.get_class(class_iri)
            if not existing_class:
                print(f"Class {iri} does not exist")
                return False
            
            # Update labels
            labels = existing_class.labels.copy()
            if name_cs is not None:
                if name_cs:
                    labels["cs"] = name_cs
                elif "cs" in labels:
                    del labels["cs"]
            if name_en is not None:
                if name_en:
                    labels["en"] = name_en
                elif "en" in labels:
                    del labels["en"]
            
            # Update definitions
            definitions = existing_class.definitions.copy()
            if definition_cs is not None:
                if definition_cs:
                    definitions["cs"] = definition_cs
                elif "cs" in definitions:
                    del definitions["cs"]
            if definition_en is not None:
                if definition_en:
                    definitions["en"] = definition_en
                elif "en" in definitions:
                    del definitions["en"]
            
            # Update comments
            comments = existing_class.comments.copy()
            if comment_cs is not None:
                if comment_cs:
                    comments["cs"] = comment_cs
                elif "cs" in comments:
                    del comments["cs"]
            if comment_en is not None:
                if comment_en:
                    comments["en"] = comment_en
                elif "en" in comments:
                    del comments["en"]
            
            # Update parent class
            parent_classes = existing_class.parent_classes.copy()
            if parent_class is not None:
                parent_classes = []
                if parent_class:  # non-empty string
                    parent_classes.append(URIRef(parent_class))
            
            # Update source elements
            source_elements = existing_class.source_elements.copy()
            if source_element is not None:
                if source_element not in source_elements:
                    source_elements.append(source_element)
            
            # Create updated ontology class
            updated_class = OntologyClass(
                iri=class_iri,
                labels=labels,
                definitions=definitions,
                comments=comments,
                parent_classes=parent_classes,
                subclasses=existing_class.subclasses,
                datatype_properties=existing_class.datatype_properties,
                object_properties_out=existing_class.object_properties_out,
                object_properties_in=existing_class.object_properties_in,
                source_elements=source_elements
            )
            
            return self.store.update_class(updated_class)
            
        except Exception as e:
            print(f"Error updating class: {e}")
            return False

    def remove_class(self, iri: str) -> bool:
        """Remove a class from the ontology.
        
        Args:
            iri: IRI of the class to remove
            
        Returns:
            True if successfully removed, False otherwise
        """
        try:
            class_iri = URIRef(iri)
            
            # Check if class exists
            if not self.store.get_class(class_iri):
                print(f"Class {iri} does not exist")
                return False
            
            return self.store.remove_class(class_iri)
            
        except Exception as e:
            print(f"Error removing class: {e}")
            return False

    def add_property(self,
                     iri: str,
                     property_type: str,
                     name_cs: str = "", 
                     name_en: str = "",
                     definition_cs: str = "",
                     definition_en: str = "",
                     comment_cs: str = "",
                     comment_en: str = "",
                     domain: str = "",
                     range_iri: str = "",
                     source_element: str = "agent-extracted") -> bool:
        """Add a new property to the ontology.
        
        Args:
            iri: IRI for the property (if empty, will be generated from name_en or name_cs)
            property_type: "ObjectProperty" or "DatatypeProperty"
            name_cs: Czech name/label for the property
            name_en: English name/label for the property
            definition_cs: Czech definition of the property
            definition_en: English definition of the property
            comment_cs: Czech comment about the property
            comment_en: English comment about the property
            domain: IRI of domain class
            range_iri: IRI of range class or datatype
            source_element: Source reference for the property
            
        Returns:
            True if successfully added, False otherwise
        """
        try:
            # Validate property type
            if property_type not in ["ObjectProperty", "DatatypeProperty"]:
                print(f"Error: Invalid property type '{property_type}'. Must be 'ObjectProperty' or 'DatatypeProperty'")
                return False
            
            # Generate IRI if not provided
            if not iri:
                name = name_en or name_cs
                if not name:
                    print("Error: Must provide either iri or at least one name (name_en/name_cs)")
                    return False
                clean_name = "".join(c for c in name if c.isalnum())
                iri = f"https://example.org/ontology/{clean_name}"
            
            prop_iri = URIRef(iri)
            
            # Check if property already exists
            if self.store.get_property_details(prop_iri):
                print(f"Property {iri} already exists")
                return False
            
            # Build labels
            labels = {}
            if name_cs:
                labels["cs"] = name_cs
            if name_en:
                labels["en"] = name_en
            
            # Build definitions
            definitions = {}
            if definition_cs:
                definitions["cs"] = definition_cs
            if definition_en:
                definitions["en"] = definition_en
            
            # Build comments
            comments = {}
            if comment_cs:
                comments["cs"] = comment_cs
            if comment_en:
                comments["en"] = comment_en
            
            # Handle domain and range
            domain_uri = URIRef(domain) if domain else URIRef("")
            
            # For datatype properties, handle XSD types
            if property_type == "DatatypeProperty" and range_iri and not range_iri.startswith("http"):
                range_iri = f"http://www.w3.org/2001/XMLSchema#{range_iri}"
            
            range_uri = URIRef(range_iri) if range_iri else URIRef("")
            
            # Create ontology property
            ontology_property = OntologyProperty(
                iri=prop_iri,
                labels=labels,
                definitions=definitions,
                comments=comments,
                property_type=property_type,
                domain=domain_uri,
                range=range_uri,
                source_elements=[source_element]
            )
            
            return self.store.add_property(ontology_property)
            
        except Exception as e:
            print(f"Error adding property: {e}")
            return False

    def update_property(self,
                        iri: str,
                        property_type: str = None,
                        name_cs: str = None, 
                        name_en: str = None,
                        definition_cs: str = None,
                        definition_en: str = None,
                        comment_cs: str = None,
                        comment_en: str = None,
                        domain: str = None,
                        range_iri: str = None,
                        source_element: str = None) -> bool:
        """Update an existing property in the ontology.
        
        Args:
            iri: IRI of the property to update
            property_type: "ObjectProperty" or "DatatypeProperty" (None = don't change)
            name_cs: Czech name/label for the property (None = don't change)
            name_en: English name/label for the property (None = don't change)
            definition_cs: Czech definition of the property (None = don't change)
            definition_en: English definition of the property (None = don't change)
            comment_cs: Czech comment about the property (None = don't change)
            comment_en: English comment about the property (None = don't change)
            domain: IRI of domain class (None = don't change, "" = remove domain)
            range_iri: IRI of range class or datatype (None = don't change, "" = remove range)
            source_element: Source reference for the property (None = don't change)
            
        Returns:
            True if successfully updated, False otherwise
        """
        try:
            prop_iri = URIRef(iri)
            
            # Check if property exists
            existing_property = self.store.get_property_details(prop_iri)
            if not existing_property:
                print(f"Property {iri} does not exist")
                return False
            
            # Validate property type if provided
            updated_property_type = property_type or existing_property.property_type
            if updated_property_type not in ["ObjectProperty", "DatatypeProperty"]:
                print(f"Error: Invalid property type '{updated_property_type}'")
                return False
            
            # Update labels
            labels = existing_property.labels.copy()
            if name_cs is not None:
                if name_cs:
                    labels["cs"] = name_cs
                elif "cs" in labels:
                    del labels["cs"]
            if name_en is not None:
                if name_en:
                    labels["en"] = name_en
                elif "en" in labels:
                    del labels["en"]
            
            # Update definitions
            definitions = existing_property.definitions.copy()
            if definition_cs is not None:
                if definition_cs:
                    definitions["cs"] = definition_cs
                elif "cs" in definitions:
                    del definitions["cs"]
            if definition_en is not None:
                if definition_en:
                    definitions["en"] = definition_en
                elif "en" in definitions:
                    del definitions["en"]
            
            # Update comments
            comments = existing_property.comments.copy()
            if comment_cs is not None:
                if comment_cs:
                    comments["cs"] = comment_cs
                elif "cs" in comments:
                    del comments["cs"]
            if comment_en is not None:
                if comment_en:
                    comments["en"] = comment_en
                elif "en" in comments:
                    del comments["en"]
            
            # Update domain
            updated_domain = existing_property.domain
            if domain is not None:
                updated_domain = URIRef(domain) if domain else URIRef("")
            
            # Update range
            updated_range = existing_property.range
            if range_iri is not None:
                if range_iri:
                    # For datatype properties, handle XSD types
                    if updated_property_type == "DatatypeProperty" and not range_iri.startswith("http"):
                        range_iri = f"http://www.w3.org/2001/XMLSchema#{range_iri}"
                    updated_range = URIRef(range_iri)
                else:
                    updated_range = URIRef("")
            
            # Update source elements
            source_elements = existing_property.source_elements.copy()
            if source_element is not None:
                if source_element not in source_elements:
                    source_elements.append(source_element)
            
            # Create updated ontology property
            updated_property = OntologyProperty(
                iri=prop_iri,
                labels=labels,
                definitions=definitions,
                comments=comments,
                property_type=updated_property_type,
                domain=updated_domain,
                range=updated_range,
                source_elements=source_elements
            )
            
            return self.store.update_property(updated_property)
            
        except Exception as e:
            print(f"Error updating property: {e}")
            return False

    def remove_property(self, iri: str) -> bool:
        """Remove a property from the ontology.
        
        Args:
            iri: IRI of the property to remove
            
        Returns:
            True if successfully removed, False otherwise
        """
        try:
            prop_iri = URIRef(iri)
            
            # Check if property exists
            if not self.store.get_property_details(prop_iri):
                print(f"Property {iri} does not exist")
                return False
            
            return self.store.remove_property(prop_iri)
            
        except Exception as e:
            print(f"Error removing property: {e}")
            return False
