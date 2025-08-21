"""
In-memory RDF store for practical ontology management.

This store provides basic CRUD operations for classes and properties,
along with semantic similarity capabilities for concept discovery.
"""

from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from rdflib import Graph, URIRef, Literal, Namespace, RDF, RDFS, OWL
from sentence_transformers import SentenceTransformer

from .domain import OntologyClass, OntologyProperty, OntologyStats
from .similarity import SemanticSimilarity


class OntologyStore:
    """Simple in-memory RDF store for practical ontologies."""
    
    def __init__(self):
        # RDF graphs for different stages
        self.working_graph = Graph()    # draft ontology under development
        self.published_graph = Graph()  # validated and approved ontology
        
        # Namespace management
        self.ex = Namespace("https://example.org/ontology/")
        self.owl = Namespace("http://www.w3.org/2002/07/owl#")
        self.rdfs = Namespace("http://www.w3.org/2000/01/rdf-schema#")
        self.skos = Namespace("http://www.w3.org/2004/02/skos/core#")
        self.xsd = Namespace("http://www.w3.org/2001/XMLSchema#")
        
        # Bind namespaces to graphs
        self._init_namespaces()
        
        # Semantic similarity components (optional)
        self.embedder: Optional[SentenceTransformer] = None
        self.similarity_engine: Optional[SemanticSimilarity] = None
        self.class_embeddings: Dict[str, np.ndarray] = {}
        self.property_embeddings: Dict[str, np.ndarray] = {}
        
        self._init_similarity_engine()
    
    def _init_namespaces(self):
        """Initialize namespace bindings for both graphs."""
        for graph in [self.working_graph, self.published_graph]:
            graph.bind("ex", self.ex)
            graph.bind("owl", self.owl)
            graph.bind("rdfs", self.rdfs)
            graph.bind("skos", self.skos)
            graph.bind("xsd", self.xsd)
    
    def _init_similarity_engine(self):
        """Initialize the semantic similarity engine."""
        try:
            # Use the same multilingual model as the indexing module
            self.embedder = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            self.similarity_engine = SemanticSimilarity(self.embedder)
        except Exception as e:
            print(f"Warning: Could not initialize similarity engine: {e}")
            self.embedder = None
            self.similarity_engine = None
    
    def get_whole_ontology(self) -> Dict[str, Any]:
        """Retrieve complete working ontology for agent overview."""
        classes = []
        object_properties = []
        datatype_properties = []
        
        # Get all classes from working graph
        for class_iri in self.working_graph.subjects(RDF.type, OWL.Class):
            ontology_class = self.get_class(class_iri)
            if ontology_class:
                classes.append(self._class_to_dict(ontology_class))
        
        # Get all object properties
        for prop_iri in self.working_graph.subjects(RDF.type, OWL.ObjectProperty):
            ontology_prop = self.get_property_details(prop_iri)
            if ontology_prop:
                object_properties.append(self._property_to_dict(ontology_prop))
        
        # Get all datatype properties
        for prop_iri in self.working_graph.subjects(RDF.type, OWL.DatatypeProperty):
            ontology_prop = self.get_property_details(prop_iri)
            if ontology_prop:
                datatype_properties.append(self._property_to_dict(ontology_prop))
        
        return {
            "classes": classes,
            "object_properties": object_properties,
            "datatype_properties": datatype_properties,
            "stats": self._get_ontology_stats()
        }
    
    def get_class(self, class_iri: URIRef) -> Optional[OntologyClass]:
        """Retrieve basic class information."""
        # Check if class exists in working graph
        if (class_iri, RDF.type, OWL.Class) not in self.working_graph:
            return None
        
        # Extract labels (skos:prefLabel)
        labels = {}
        for obj in self.working_graph.objects(class_iri, self.skos.prefLabel):
            if isinstance(obj, Literal) and obj.language:
                labels[obj.language] = str(obj)
        
        # Extract definitions (skos:definition)
        definitions = {}
        for obj in self.working_graph.objects(class_iri, self.skos.definition):
            if isinstance(obj, Literal) and obj.language:
                definitions[obj.language] = str(obj)
        
        # Extract comments (rdfs:comment)
        comments = {}
        for obj in self.working_graph.objects(class_iri, self.rdfs.comment):
            if isinstance(obj, Literal) and obj.language:
                comments[obj.language] = str(obj)
        
        # Extract parent classes (rdfs:subClassOf)
        parent_classes = list(self.working_graph.objects(class_iri, RDFS.subClassOf))
        
        # Extract subclasses (classes that have this as rdfs:subClassOf)
        subclasses = list(self.working_graph.subjects(RDFS.subClassOf, class_iri))
        
        # Extract datatype properties (properties with this class as domain)
        datatype_properties = []
        for prop in self.working_graph.subjects(RDFS.domain, class_iri):
            if (prop, RDF.type, OWL.DatatypeProperty) in self.working_graph:
                datatype_properties.append(prop)
        
        # Extract outgoing object properties
        object_properties_out = []
        for prop in self.working_graph.subjects(RDFS.domain, class_iri):
            if (prop, RDF.type, OWL.ObjectProperty) in self.working_graph:
                object_properties_out.append(prop)
        
        # Extract incoming object properties
        object_properties_in = []
        for prop in self.working_graph.subjects(RDFS.range, class_iri):
            if (prop, RDF.type, OWL.ObjectProperty) in self.working_graph:
                object_properties_in.append(prop)
        
        # Extract source elements (simplified - stored as rdfs:comment for now)
        source_elements = []
        for obj in self.working_graph.objects(class_iri, self.ex.sourceElement):
            source_elements.append(str(obj))
        
        return OntologyClass(
            iri=class_iri,
            prefLabels=labels,
            definitions=definitions,
            comments=comments,
            parent_classes=parent_classes,
            subclasses=subclasses,
            datatype_properties=datatype_properties,
            object_properties_out=object_properties_out,
            object_properties_in=object_properties_in,
            source_elements=source_elements
        )
    
    def get_class_with_surroundings(self, class_iri: URIRef) -> Dict[str, Any]:
        """Get class with connected classes via properties.
        
        Returns:
            Dict with:
            - connected_classes: Dict[str, OntologyClass] 
            - connecting_properties: Dict[str, OntologyProperty]
        """
        connected_classes = {}
        connecting_properties = {}
        
        # Get the target class
        target_class = self.get_class(class_iri)
        if not target_class:
            return {"connected_classes": {}, "connecting_properties": {}}
        
        # Find connected classes via outgoing object properties
        for prop_iri in target_class.object_properties_out:
            # Get the property details
            prop = self.get_property_details(prop_iri)
            if prop and prop.range:
                connecting_properties[str(prop_iri)] = prop
                # Get the target class of this property
                target_class_obj = self.get_class(prop.range)
                if target_class_obj:
                    connected_classes[str(prop.range)] = target_class_obj
        
        # Find connected classes via incoming object properties
        for prop_iri in target_class.object_properties_in:
            # Get the property details
            prop = self.get_property_details(prop_iri)
            if prop and prop.domain:
                connecting_properties[str(prop_iri)] = prop
                # Get the source class of this property
                source_class_obj = self.get_class(prop.domain)
                if source_class_obj:
                    connected_classes[str(prop.domain)] = source_class_obj
        
        # Find connected classes via inheritance (parent classes)
        for parent_iri in target_class.parent_classes:
            parent_class = self.get_class(parent_iri)
            if parent_class:
                connected_classes[str(parent_iri)] = parent_class
        
        # Find connected classes via inheritance (subclasses)
        for subclass_iri in target_class.subclasses:
            subclass = self.get_class(subclass_iri)
            if subclass:
                connected_classes[str(subclass_iri)] = subclass
        
        return {
            "connected_classes": connected_classes,
            "connecting_properties": connecting_properties
        }
    
    def get_property_details(self, property_iri: URIRef) -> Optional[OntologyProperty]:
        """Get property with domain/range details."""
        # Check if property exists (either ObjectProperty or DatatypeProperty)
        is_object_prop = (property_iri, RDF.type, OWL.ObjectProperty) in self.working_graph
        is_datatype_prop = (property_iri, RDF.type, OWL.DatatypeProperty) in self.working_graph
        
        if not (is_object_prop or is_datatype_prop):
            return None
        
        property_type = "ObjectProperty" if is_object_prop else "DatatypeProperty"
        
        # Extract labels (skos:prefLabel)
        labels = {}
        for obj in self.working_graph.objects(property_iri, self.skos.prefLabel):
            if isinstance(obj, Literal) and obj.language:
                labels[obj.language] = str(obj)
        
        # Extract definitions (skos:definition)
        definitions = {}
        for obj in self.working_graph.objects(property_iri, self.skos.definition):
            if isinstance(obj, Literal) and obj.language:
                definitions[obj.language] = str(obj)
        
        # Extract comments (rdfs:comment)
        comments = {}
        for obj in self.working_graph.objects(property_iri, self.rdfs.comment):
            if isinstance(obj, Literal) and obj.language:
                comments[obj.language] = str(obj)
        
        # Extract domain
        domain = None
        for obj in self.working_graph.objects(property_iri, RDFS.domain):
            domain = obj
            break  # Take first domain
        
        # Extract range
        range_obj = None
        for obj in self.working_graph.objects(property_iri, RDFS.range):
            range_obj = obj
            break  # Take first range
        
        # Extract source elements
        source_elements = []
        for obj in self.working_graph.objects(property_iri, self.ex.sourceElement):
            source_elements.append(str(obj))
        
        return OntologyProperty(
            iri=property_iri,
            prefLabels=labels,
            definitions=definitions,
            comments=comments,
            property_type=property_type,
            domain=domain,
            range=range_obj,
            source_elements=source_elements
        )
    
    def get_class_hierarchy(self, class_iri: URIRef) -> Dict[str, List[URIRef]]:
        """Get parent and subclasses.
        
        Returns:
            Dict with 'parents' and 'subclasses' lists
        """
        # Check if class exists
        if (class_iri, RDF.type, OWL.Class) not in self.working_graph:
            return {"parents": [], "subclasses": []}
        
        # Get parent classes (rdfs:subClassOf)
        parents = list(self.working_graph.objects(class_iri, RDFS.subClassOf))
        
        # Get subclasses (classes that have this as rdfs:subClassOf)
        subclasses = list(self.working_graph.subjects(RDFS.subClassOf, class_iri))
        
        return {
            "parents": parents,
            "subclasses": subclasses
        }
    
    def find_similar_classes(self, class_iri: URIRef, limit: int = 10) -> List[Tuple[URIRef, float]]:
        """Find semantically similar classes using labels/definitions."""
        if not self.similarity_engine:
            return []
        
        # Get the target class
        target_class = self.get_class(class_iri)
        if not target_class:
            return []
        
        # Get or compute embedding for target class
        target_iri_str = str(class_iri)
        target_embedding = self.class_embeddings.get(target_iri_str)
        
        if target_embedding is None:
            target_embedding = self.similarity_engine.compute_class_embedding(
                target_class.prefLabels,
                target_class.definitions,
                target_class.comments
            )
            if target_embedding is None:
                return []
            # Cache the embedding
            self.class_embeddings[target_iri_str] = target_embedding
        
        # Ensure all other classes have embeddings computed
        self._ensure_all_class_embeddings()
        
        # Find similar classes (excluding the target class itself)
        candidate_embeddings = {
            iri: embedding for iri, embedding in self.class_embeddings.items()
            if iri != target_iri_str
        }
        
        if not candidate_embeddings:
            return []
        
        # Use similarity engine to find most similar
        similar_iris_scores = self.similarity_engine.find_similar_embeddings(
            target_embedding, candidate_embeddings, limit
        )
        
        # Convert string IRIs back to URIRef and return
        result = []
        for iri_str, score in similar_iris_scores:
            try:
                result.append((URIRef(iri_str), score))
            except Exception as e:
                print(f"Warning: Could not convert IRI {iri_str}: {e}")
                continue
        
        return result
    
    def add_class(self, ontology_class: OntologyClass) -> bool:
        """Add simple class to working graph."""
        try:
            # Add class type declaration
            self.working_graph.add((ontology_class.iri, RDF.type, OWL.Class))
            
            # Add labels
            for lang, label in ontology_class.prefLabels.items():
                self.working_graph.add((ontology_class.iri, self.skos.prefLabel, Literal(label, lang=lang)))
            
            # Add definitions
            for lang, definition in ontology_class.definitions.items():
                self.working_graph.add((ontology_class.iri, self.skos.definition, Literal(definition, lang=lang)))
            
            # Add comments
            for lang, comment in ontology_class.comments.items():
                self.working_graph.add((ontology_class.iri, self.rdfs.comment, Literal(comment, lang=lang)))
            
            # Add parent class relationships
            for parent_iri in ontology_class.parent_classes:
                self.working_graph.add((ontology_class.iri, RDFS.subClassOf, parent_iri))
            
            # Add source elements
            for source_element in ontology_class.source_elements:
                self.working_graph.add((ontology_class.iri, self.ex.sourceElement, Literal(source_element)))
            
            # Compute and cache embedding if possible
            if self.similarity_engine:
                embedding = self.similarity_engine.compute_class_embedding(
                    ontology_class.prefLabels,
                    ontology_class.definitions,
                    ontology_class.comments
                )
                if embedding is not None:
                    self.class_embeddings[str(ontology_class.iri)] = embedding
            
            return True
            
        except Exception as e:
            print(f"Error adding class {ontology_class.iri}: {e}")
            return False
    
    def add_property(self, ontology_property: OntologyProperty) -> bool:
        """Add simple property to working graph."""
        try:
            # Add property type declaration
            if ontology_property.property_type == "ObjectProperty":
                self.working_graph.add((ontology_property.iri, RDF.type, OWL.ObjectProperty))
            else:
                self.working_graph.add((ontology_property.iri, RDF.type, OWL.DatatypeProperty))
            
            # Add labels
            for lang, label in ontology_property.prefLabels.items():
                self.working_graph.add((ontology_property.iri, self.skos.prefLabel, Literal(label, lang=lang)))
            
            # Add definitions
            for lang, definition in ontology_property.definitions.items():
                self.working_graph.add((ontology_property.iri, self.skos.definition, Literal(definition, lang=lang)))
            
            # Add comments
            for lang, comment in ontology_property.comments.items():
                self.working_graph.add((ontology_property.iri, self.rdfs.comment, Literal(comment, lang=lang)))
            
            # Add domain
            if ontology_property.domain:
                self.working_graph.add((ontology_property.iri, RDFS.domain, ontology_property.domain))
            
            # Add range
            if ontology_property.range:
                self.working_graph.add((ontology_property.iri, RDFS.range, ontology_property.range))
            
            # Add source elements
            for source_element in ontology_property.source_elements:
                self.working_graph.add((ontology_property.iri, self.ex.sourceElement, Literal(source_element)))
            
            return True
            
        except Exception as e:
            print(f"Error adding property {ontology_property.iri}: {e}")
            return False
    
    def update_class(self, ontology_class: OntologyClass) -> bool:
        """Update existing class in working graph.
        
        This removes all existing triples for the class and adds the new ones.
        
        Args:
            ontology_class: Updated class information
            
        Returns:
            True if successfully updated, False otherwise
        """
        try:
            # Check if class exists first
            existing_class = self.get_class(ontology_class.iri)
            if not existing_class:
                return False
            
            # First remove existing class data
            if not self.remove_class(ontology_class.iri):
                return False
            
            # Then add the updated class
            return self.add_class(ontology_class)
            
        except Exception as e:
            print(f"Error updating class {ontology_class.iri}: {e}")
            return False
    
    def update_property(self, ontology_property: OntologyProperty) -> bool:
        """Update existing property in working graph.
        
        This removes all existing triples for the property and adds the new ones.
        
        Args:
            ontology_property: Updated property information
            
        Returns:
            True if successfully updated, False otherwise
        """
        try:
            # Check if property exists first
            existing_property = self.get_property_details(ontology_property.iri)
            if not existing_property:
                return False
            
            # First remove existing property data
            if not self.remove_property(ontology_property.iri):
                return False
            
            # Then add the updated property
            return self.add_property(ontology_property)
            
        except Exception as e:
            print(f"Error updating property {ontology_property.iri}: {e}")
            return False
    
    def remove_class(self, class_iri: URIRef) -> bool:
        """Remove class and all its related triples from working graph.
        
        Args:
            class_iri: IRI of the class to remove
            
        Returns:
            True if successfully removed, False otherwise
        """
        try:
            # Remove all triples where this class is the subject
            triples_to_remove = list(self.working_graph.triples((class_iri, None, None)))
            for triple in triples_to_remove:
                self.working_graph.remove(triple)
            
            # Remove all triples where this class is the object (e.g., subclass relationships)
            triples_to_remove = list(self.working_graph.triples((None, None, class_iri)))
            for triple in triples_to_remove:
                self.working_graph.remove(triple)
            
            # Remove cached embedding if it exists
            class_iri_str = str(class_iri)
            if class_iri_str in self.class_embeddings:
                del self.class_embeddings[class_iri_str]
            
            return True
            
        except Exception as e:
            print(f"Error removing class {class_iri}: {e}")
            return False
    
    def remove_property(self, property_iri: URIRef) -> bool:
        """Remove property and all its related triples from working graph.
        
        Args:
            property_iri: IRI of the property to remove
            
        Returns:
            True if successfully removed, False otherwise
        """
        try:
            # Remove all triples where this property is the subject
            triples_to_remove = list(self.working_graph.triples((property_iri, None, None)))
            for triple in triples_to_remove:
                self.working_graph.remove(triple)
            
            # Remove all triples where this property is the predicate
            triples_to_remove = list(self.working_graph.triples((None, property_iri, None)))
            for triple in triples_to_remove:
                self.working_graph.remove(triple)
            
            # Remove all triples where this property is the object
            triples_to_remove = list(self.working_graph.triples((None, None, property_iri)))
            for triple in triples_to_remove:
                self.working_graph.remove(triple)
            
            # Remove cached embedding if it exists
            property_iri_str = str(property_iri)
            if property_iri_str in self.property_embeddings:
                del self.property_embeddings[property_iri_str]
            
            return True
            
        except Exception as e:
            print(f"Error removing property {property_iri}: {e}")
            return False
    
    def _get_ontology_stats(self) -> OntologyStats:
        """Get basic statistics about the ontology."""
        # Count triples by type in working graph
        total_triples = len(self.working_graph)
        
        # Count classes (subjects that are owl:Class)
        classes_query = list(self.working_graph.subjects(RDF.type, OWL.Class))
        total_classes = len(classes_query)
        
        # Count object properties
        obj_props_query = list(self.working_graph.subjects(RDF.type, OWL.ObjectProperty))
        total_object_properties = len(obj_props_query)
        
        # Count datatype properties
        data_props_query = list(self.working_graph.subjects(RDF.type, OWL.DatatypeProperty))
        total_datatype_properties = len(data_props_query)
        
        # Count classes with definitions
        classes_with_definitions = 0
        for class_iri in self.working_graph.subjects(RDF.type, OWL.Class):
            if list(self.working_graph.objects(class_iri, self.skos.definition)):
                classes_with_definitions += 1
        
        # Count properties with domain and range
        properties_with_domain_range = 0
        all_properties = (list(self.working_graph.subjects(RDF.type, OWL.ObjectProperty)) + 
                         list(self.working_graph.subjects(RDF.type, OWL.DatatypeProperty)))
        
        for prop_iri in all_properties:
            has_domain = bool(list(self.working_graph.objects(prop_iri, RDFS.domain)))
            has_range = bool(list(self.working_graph.objects(prop_iri, RDFS.range)))
            if has_domain and has_range:
                properties_with_domain_range += 1
        
        return OntologyStats(
            total_classes=total_classes,
            total_object_properties=total_object_properties,
            total_datatype_properties=total_datatype_properties,
            total_triples=total_triples,
            classes_with_definitions=classes_with_definitions,
            properties_with_domain_range=properties_with_domain_range
        )
    
    def _compute_class_embedding(self, ontology_class: OntologyClass) -> Optional[np.ndarray]:
        """Compute embedding for a class from its textual content."""
        if not self.similarity_engine:
            return None
        
        return self.similarity_engine.compute_class_embedding(
            ontology_class.prefLabels,
            ontology_class.definitions,
            ontology_class.comments
        )
    
    def _ensure_all_class_embeddings(self):
        """Ensure all classes in the ontology have embeddings computed."""
        if not self.similarity_engine:
            return
        
        # Get all classes from the working graph
        for class_iri in self.working_graph.subjects(RDF.type, OWL.Class):
            class_iri_str = str(class_iri)
            
            # Skip if embedding already exists
            if class_iri_str in self.class_embeddings:
                continue
            
            # Get the class and compute embedding
            ontology_class = self.get_class(class_iri)
            if ontology_class:
                embedding = self.similarity_engine.compute_class_embedding(
                    ontology_class.prefLabels,
                    ontology_class.definitions,
                    ontology_class.comments
                )
                if embedding is not None:
                    self.class_embeddings[class_iri_str] = embedding

    def _ensure_class_embedding(self, class_iri: URIRef) -> Optional[np.ndarray]:
        """Ensure a specific class has its embedding computed and return it.
        
        Args:
            class_iri: URI reference of the class
            
        Returns:
            The embedding vector or None if computation failed
        """
        if not self.similarity_engine:
            return None
        
        class_iri_str = str(class_iri)
        
        # Return existing embedding if available
        if class_iri_str in self.class_embeddings:
            return self.class_embeddings[class_iri_str]
        
        # Compute and cache new embedding
        ontology_class = self.get_class(class_iri)
        if ontology_class:
            embedding = self.similarity_engine.compute_class_embedding(
                ontology_class.prefLabels,
                ontology_class.definitions,
                ontology_class.comments
            )
            if embedding is not None:
                self.class_embeddings[class_iri_str] = embedding
                return embedding
        
        return None
    
    def _class_to_dict(self, ontology_class: OntologyClass) -> Dict[str, Any]:
        """Convert OntologyClass to dictionary representation."""
        return {
            "iri": str(ontology_class.iri),
            "prefLabels": ontology_class.prefLabels,
            "definitions": ontology_class.definitions,
            "comments": ontology_class.comments,
            "parent_classes": [str(iri) for iri in ontology_class.parent_classes],
            "subclasses": [str(iri) for iri in ontology_class.subclasses],
            "datatype_properties": [str(iri) for iri in ontology_class.datatype_properties],
            "object_properties_out": [str(iri) for iri in ontology_class.object_properties_out],
            "object_properties_in": [str(iri) for iri in ontology_class.object_properties_in],
            "source_elements": ontology_class.source_elements
        }
    
    def _property_to_dict(self, ontology_property: OntologyProperty) -> Dict[str, Any]:
        """Convert OntologyProperty to dictionary representation."""
        return {
            "iri": str(ontology_property.iri),
            "prefLabels": ontology_property.prefLabels,
            "definitions": ontology_property.definitions,
            "comments": ontology_property.comments,
            "property_type": ontology_property.property_type,
            "domain": str(ontology_property.domain) if ontology_property.domain else None,
            "range": str(ontology_property.range) if ontology_property.range else None,
            "source_elements": ontology_property.source_elements
        }
