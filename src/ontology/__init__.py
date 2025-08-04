"""
Ontology Store, Modeling, & Validation Module

This module provides a simple in-memory ontology store for practical data modeling
focused on classes, properties, and basic relationships extracted from legal acts.

Public Interface:
- OntologyService: High-level service for all ontology operations

Private Components:
- OntologyStore: In-memory RDF store with semantic similarity
- Domain models: OntologyClass, OntologyProperty, etc.
"""

from .service import OntologyService

__all__ = ["OntologyService"]
