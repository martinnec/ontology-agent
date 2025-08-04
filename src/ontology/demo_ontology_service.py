"""
Comprehensive demo script for the Ontology Service module.

This script showcases the complete functionality of the ontology module
and its usage by developers of other modules. It demonstrates all phases
of implementation: core operations, retrieval, and semantic similarity.

HOW TO RUN:
The virtual environment .venv should be activated before running.

From the src directory, run:
    python -m ontology.demo_ontology_service

Or from the project root:
    cd src; python -m ontology.demo_ontology_service

This demo covers:
- Creating and managing ontology classes and properties
- Relationship navigation and neighborhood discovery  
- Semantic similarity for concept discovery
- Complete ontology overview and statistics
- Integration examples for AI agent usage
"""

import os
# Set environment variable for demo
os.environ["OPENAI_API_KEY"] = "dummy-api-key-for-demo"

from .service import OntologyService
from .domain import OntologyClass, OntologyProperty
from rdflib import URIRef


def demo_basic_ontology_operations():
    """Demonstrate basic CRUD operations for classes and properties."""
    print("="*70)
    print("1. BASIC ONTOLOGY OPERATIONS")
    print("="*70)
    
    # Initialize service
    service = OntologyService()
    print("✓ OntologyService initialized")
    
    # Create sample classes with Czech legal terminology
    print("\n📝 Creating ontology classes...")
    
    # Vehicle class
    vehicle_class = OntologyClass(
        iri=URIRef("https://example.org/ontology/Vehicle"),
        labels={"cs": "Vozidlo", "en": "Vehicle"},
        definitions={"cs": "Dopravní prostředek určený k přepravě osob nebo nákladu na pozemních komunikacích"},
        comments={"cs": "Podle zákona č. 56/2001 Sb., o podmínkách provozu vozidel na pozemních komunikacích"},
        parent_classes=[],
        subclasses=[],
        datatype_properties=[],
        object_properties_out=[],
        object_properties_in=[],
        source_elements=["https://opendata.eselpoint.cz/esel-esb/eli/cz/sb/2001/56/2025-07-01#section-2"]
    )
    
    # Road vehicle subclass
    road_vehicle_class = OntologyClass(
        iri=URIRef("https://example.org/ontology/RoadVehicle"),
        labels={"cs": "Silniční vozidlo", "en": "Road Vehicle"},
        definitions={"cs": "Vozidlo určené k provozu na pozemních komunikacích"},
        comments={"cs": "Kategorie vozidel registrovaných pro provoz na silnicích"},
        parent_classes=[URIRef("https://example.org/ontology/Vehicle")],
        subclasses=[],
        datatype_properties=[],
        object_properties_out=[],
        object_properties_in=[],
        source_elements=["https://opendata.eselpoint.cz/esel-esb/eli/cz/sb/2001/56/2025-07-01#section-2"]
    )
    
    # Owner class
    owner_class = OntologyClass(
        iri=URIRef("https://example.org/ontology/VehicleOwner"),
        labels={"cs": "Vlastník vozidla", "en": "Vehicle Owner"},
        definitions={"cs": "Fyzická nebo právnická osoba, která má vlastnické právo k vozidlu"},
        comments={"cs": "Osoba uvedená v technickém průkazu vozidla"},
        parent_classes=[],
        subclasses=[],
        datatype_properties=[],
        object_properties_out=[],
        object_properties_in=[],
        source_elements=["https://opendata.eselpoint.cz/esel-esb/eli/cz/sb/2001/56/2025-07-01#section-3"]
    )
    
    # Add classes to ontology
    success1 = service.store.add_class(vehicle_class)
    success2 = service.store.add_class(road_vehicle_class)
    success3 = service.store.add_class(owner_class)
    
    print(f"  ✓ Vehicle class added: {success1}")
    print(f"  ✓ Road vehicle class added: {success2}")
    print(f"  ✓ Owner class added: {success3}")
    
    # Create properties
    print("\n📝 Creating ontology properties...")
    
    # Object property: owns
    owns_property = OntologyProperty(
        iri=URIRef("https://example.org/ontology/owns"),
        labels={"cs": "vlastní", "en": "owns"},
        definitions={"cs": "Vztah vlastnictví mezi osobou a vozidlem"},
        comments={"cs": "Vlastnické právo k vozidlu"},
        property_type="ObjectProperty",
        domain=URIRef("https://example.org/ontology/VehicleOwner"),
        range=URIRef("https://example.org/ontology/Vehicle"),
        source_elements=["https://opendata.eselpoint.cz/esel-esb/eli/cz/sb/2001/56/2025-07-01#section-3"]
    )
    
    # Datatype property: registration number
    registration_property = OntologyProperty(
        iri=URIRef("https://example.org/ontology/registrationNumber"),
        labels={"cs": "registrační značka", "en": "registration number"},
        definitions={"cs": "Jedinečný identifikátor vozidla přidělený při registraci"},
        comments={"cs": "SPZ podle vyhlášky o registračních značkách"},
        property_type="DatatypeProperty",
        domain=URIRef("https://example.org/ontology/Vehicle"),
        range=URIRef("http://www.w3.org/2001/XMLSchema#string"),
        source_elements=["https://opendata.eselpoint.cz/esel-esb/eli/cz/sb/2001/56/2025-07-01#section-4"]
    )
    
    # Add properties
    prop_success1 = service.store.add_property(owns_property)
    prop_success2 = service.store.add_property(registration_property)
    
    print(f"  ✓ Owns property added: {prop_success1}")
    print(f"  ✓ Registration property added: {prop_success2}")
    
    return service


def demo_retrieval_operations(service: OntologyService):
    """Demonstrate class and property retrieval operations."""
    print("\n" + "="*70)
    print("2. RETRIEVAL OPERATIONS")
    print("="*70)
    
    # Get complete ontology overview
    print("\n📊 Getting complete ontology overview...")
    ontology = service.get_working_ontology()
    
    print(f"Classes: {len(ontology['classes'])}")
    print(f"Object properties: {len(ontology['object_properties'])}")
    print(f"Datatype properties: {len(ontology['datatype_properties'])}")
    
    stats = ontology['stats']
    print(f"\nStatistics:")
    print(f"  Total triples: {stats.total_triples}")
    print(f"  Classes with definitions: {stats.classes_with_definitions}")
    print(f"  Properties with domain/range: {stats.properties_with_domain_range}")
    
    # Get class neighborhood
    print("\n🏘️  Getting class neighborhood...")
    try:
        neighborhood = service.get_class_neighborhood("https://example.org/ontology/Vehicle")
        print(f"Target class: {neighborhood.target_class.labels['cs']}")
        print(f"Connected classes: {len(neighborhood.connected_classes)}")
        print(f"Connecting properties: {len(neighborhood.connecting_properties)}")
        
        for iri, connected_class in neighborhood.connected_classes.items():
            print(f"  → {connected_class.labels.get('cs', 'N/A')} ({iri})")
            
    except Exception as e:
        print(f"Error getting neighborhood: {e}")
    
    # Get class hierarchy
    print("\n🌳 Getting class hierarchy...")
    try:
        hierarchy = service.get_class_hierarchy("https://example.org/ontology/RoadVehicle")
        print(f"Parents: {len(hierarchy['parents'])}")
        print(f"Subclasses: {len(hierarchy['subclasses'])}")
        
        for parent in hierarchy['parents']:
            parent_class = service.store.get_class(parent)
            if parent_class:
                print(f"  ↑ Parent: {parent_class.labels.get('cs', 'N/A')}")
                
    except Exception as e:
        print(f"Error getting hierarchy: {e}")
    
    # Get property details
    print("\n🔗 Getting property details...")
    try:
        prop = service.get_property_details("https://example.org/ontology/owns")
        print(f"Property: {prop.labels['cs']} ({prop.property_type})")
        print(f"Domain: {prop.domain}")
        print(f"Range: {prop.range}")
        print(f"Definition: {prop.definitions.get('cs', 'N/A')}")
        
    except Exception as e:
        print(f"Error getting property: {e}")


def demo_semantic_similarity(service: OntologyService):
    """Demonstrate semantic similarity functionality."""
    print("\n" + "="*70)
    print("3. SEMANTIC SIMILARITY")
    print("="*70)
    
    # Check if similarity engine is available
    if not service.store.similarity_engine:
        print("⚠️  Similarity engine not available - skipping demo")
        return
    
    # Add more classes for similarity testing
    print("\n📝 Adding more classes for similarity testing...")
    
    additional_classes = [
        {
            "iri": "https://example.org/ontology/Car",
            "labels": {"cs": "Osobní automobil", "en": "Car"},
            "definitions": {"cs": "Silniční motorové vozidlo určené k přepravě nejvýše 9 osob včetně řidiče"},
            "comments": {"cs": "Kategorie M1 podle směrnice EU"}
        },
        {
            "iri": "https://example.org/ontology/Truck", 
            "labels": {"cs": "Nákladní automobil", "en": "Truck"},
            "definitions": {"cs": "Silniční motorové vozidlo určené k přepravě nákladu"},
            "comments": {"cs": "Kategorie N podle směrnice EU"}
        },
        {
            "iri": "https://example.org/ontology/Motorcycle",
            "labels": {"cs": "Motocykl", "en": "Motorcycle"},
            "definitions": {"cs": "Dvoukolové nebo tříkolové motorové vozidlo"},
            "comments": {"cs": "Kategorie L podle směrnice EU"}
        },
        {
            "iri": "https://example.org/ontology/License",
            "labels": {"cs": "Řidičský průkaz", "en": "Driving License"},
            "definitions": {"cs": "Úředně vydaný doklad opravňující k řízení motorových vozidel"},
            "comments": {"cs": "Dokument podle zákona o podmínkách řízení"}
        }
    ]
    
    for class_data in additional_classes:
        ontology_class = OntologyClass(
            iri=URIRef(class_data["iri"]),
            labels=class_data["labels"],
            definitions=class_data["definitions"],
            comments=class_data["comments"],
            parent_classes=[],
            subclasses=[],
            datatype_properties=[],
            object_properties_out=[],
            object_properties_in=[],
            source_elements=["demo-source"]
        )
        service.store.add_class(ontology_class)
    
    print(f"  ✓ Added {len(additional_classes)} additional classes")
    
    # Test similarity search
    print("\n🔍 Finding similar classes...")
    
    test_targets = [
        ("https://example.org/ontology/Vehicle", "Vehicle (general concept)"),
        ("https://example.org/ontology/Car", "Car (specific vehicle)"),
        ("https://example.org/ontology/License", "License (non-vehicle concept)")
    ]
    
    for target_iri, description in test_targets:
        print(f"\n🎯 Similar to {description}:")
        try:
            similar_classes = service.get_similar_classes(target_iri, limit=4)
            
            if similar_classes:
                for i, similar_class in enumerate(similar_classes, 1):
                    class_info = similar_class.class_info
                    score = similar_class.similarity_score
                    cs_label = class_info.labels.get('cs', 'N/A')
                    en_label = class_info.labels.get('en', 'N/A')
                    
                    print(f"  {i}. {cs_label} ({en_label}) - Score: {score:.3f}")
                    print(f"     {class_info.definitions.get('cs', 'No definition')}")
            else:
                print("  No similar classes found")
                
        except Exception as e:
            print(f"  Error: {e}")


def demo_ai_agent_usage_patterns(service: OntologyService):
    """Demonstrate typical usage patterns for AI agents with real ontology data."""
    print("\n" + "="*70)
    print("4. AI AGENT USAGE PATTERNS")
    print("="*70)
    
    print("\n🤖 AI Agent Complex Workflow Simulation:")
    print("Scenario: Agent is processing a new legal text about vehicle registration")
    print("and wants to understand existing concepts before extracting new ones.")
    
    # 1. Agent checks current ontology state
    print("\n1️⃣  Agent checks current ontology state...")
    ontology = service.get_working_ontology()
    print(f"   Current ontology has {len(ontology['classes'])} classes and {len(ontology['object_properties']) + len(ontology['datatype_properties'])} properties")
    
    # Show what concepts already exist
    print("   Existing concepts:")
    for cls in ontology['classes'][:3]:  # Show first 3 classes
        cs_label = cls.get('labels', {}).get('cs', 'N/A')
        en_label = cls.get('labels', {}).get('en', 'N/A')
        print(f"     • {cs_label} ({en_label})")
    
    # 2. Agent explores specific concept neighborhood for context
    print("\n2️⃣  Agent explores Vehicle concept for context...")
    try:
        vehicle_iri = "https://example.org/ontology/Vehicle"
        neighborhood = service.get_class_neighborhood(vehicle_iri)
        print(f"   Vehicle has {len(neighborhood.connected_classes)} connected concepts:")
        
        for iri, connected_class in neighborhood.connected_classes.items():
            cs_label = connected_class.labels.get('cs', 'N/A')
            print(f"     → {cs_label}")
        
        print(f"   Connected via {len(neighborhood.connecting_properties)} properties:")
        for prop in neighborhood.connecting_properties:
            if hasattr(prop, 'labels'):
                prop_label = prop.labels.get('cs', prop.labels.get('en', 'N/A'))
                prop_type = getattr(prop, 'property_type', 'Property')
                print(f"     🔗 {prop_label} ({prop_type})")
            else:
                # Handle case where prop might be a string or different object
                print(f"     🔗 {str(prop)}")
            
    except Exception as e:
        print(f"   Error exploring neighborhood: {e}")
    
    # 3. Agent checks class hierarchy before adding subclasses
    print("\n3️⃣  Agent checks Vehicle hierarchy for classification...")
    try:
        hierarchy = service.get_class_hierarchy("https://example.org/ontology/RoadVehicle")
        print("   RoadVehicle hierarchy:")
        
        for parent_iri in hierarchy['parents']:
            parent_class = service.store.get_class(parent_iri)
            if parent_class:
                print(f"     ↑ Parent: {parent_class.labels.get('cs', 'N/A')}")
        
        print(f"     → Current: Silniční vozidlo")
        
        if hierarchy['subclasses']:
            print("     ↓ Subclasses:")
            for sub_iri in hierarchy['subclasses']:
                sub_class = service.store.get_class(sub_iri)
                if sub_class:
                    print(f"       • {sub_class.labels.get('cs', 'N/A')}")
        else:
            print("     ↓ No subclasses yet (good place to add new vehicle types)")
            
    except Exception as e:
        print(f"   Error checking hierarchy: {e}")
    
    # 4. Agent searches for similar concepts to avoid duplication
    print("\n4️⃣  Agent searches for similar concepts before extraction...")
    if service.store.similarity_engine:
        try:
            # Simulate agent found "Auto" in text, checks if it's similar to existing "Car"
            print("   Scenario: Found 'Auto' in legal text, checking similarity to existing concepts...")
            
            car_iri = "https://example.org/ontology/Car"
            similar = service.get_similar_classes(car_iri, limit=3)
            
            if similar:
                print("   Similar concepts found (helps avoid duplicates):")
                for i, similar_class in enumerate(similar, 1):
                    class_info = similar_class.class_info
                    score = similar_class.similarity_score
                    cs_label = class_info.labels.get('cs', 'N/A')
                    print(f"     {i}. {cs_label} (similarity: {score:.3f})")
                    
                if similar[0].similarity_score > 0.8:
                    print("   🔍 High similarity detected - likely refers to existing concept")
                else:
                    print("   ➕ Low similarity - likely a new concept to extract")
            else:
                print("   No similar concepts found - proceeding with extraction")
                
        except Exception as e:
            print(f"   Similarity search error: {e}")
    else:
        print("   ⚠️  Similarity engine not available")
    
    # 5. Agent validates property relationships
    print("\n5️⃣  Agent validates property relationships...")
    try:
        owns_property = service.get_property_details("https://example.org/ontology/owns")
        print(f"   Property: {owns_property.labels.get('cs', 'N/A')}")
        
        # Check domain class
        domain_class = service.store.get_class(owns_property.domain)
        range_class = service.store.get_class(owns_property.range)
        
        if domain_class and range_class:
            domain_label = domain_class.labels.get('cs', 'N/A')
            range_label = range_class.labels.get('cs', 'N/A')
            print(f"   Relationship: {domain_label} → {owns_property.labels.get('cs', 'N/A')} → {range_label}")
            print("   ✓ Domain and range classes exist - relationship is valid")
        else:
            print("   ⚠️  Missing domain or range class")
            
    except Exception as e:
        print(f"   Property validation error: {e}")
    
    # 6. Agent gets complete context for decision making
    print("\n6️⃣  Agent gets complete context for extraction decisions...")
    stats = ontology['stats']
    print(f"   Decision context:")
    print(f"     • Total knowledge: {stats.total_classes} classes, {stats.total_triples} triples")
    print(f"     • Quality metrics: {stats.classes_with_definitions}/{stats.total_classes} classes have definitions")
    print(f"     • Relationship coverage: {stats.properties_with_domain_range} properties with domain/range")
    
    # 7. Simulate agent making informed decisions
    print("\n7️⃣  Agent makes informed extraction decisions...")
    print("   Based on ontology analysis:")
    print("   ✓ Vehicle concepts well established - can extend with new vehicle types")
    print("   ✓ Ownership relationships defined - can add new ownership patterns")
    print("   ✓ Registration properties exist - can add related administrative concepts")
    print("   ➡️  Recommendation: Focus on extracting specific vehicle categories and regulations")
    
    # 8. Show preparation for Phase 4 integration
    print("\n8️⃣  Preparing for LLM extraction integration...")
    print("   [Phase 4] Ready to integrate:")
    print("   • add_extraction_results(llm_results) → Add AI-extracted concepts")
    print("   • search_by_concept(natural_query) → Find relevant existing concepts")
    print("   • Context: Agent now has full ontology awareness for smart extraction")
    
    print("\n✅ Complex AI Agent workflow demonstrated with real ontology data")


def demo_phase4_llm_integration(service: OntologyService):
    """Demonstrate Phase 4 LLM integration capabilities."""
    print("\n" + "="*70)
    print("6. PHASE 4 - LLM INTEGRATION & AGENT WORKFLOW")
    print("="*70)
    
    print("\n🤖 LLM Integration Demo:")
    print("Simulating AI agent receiving LLM extraction results and processing them...")
    
    # Simulate LLM extraction results from processing legal text
    print("\n📝 Processing LLM extraction results...")
    extraction_results = [
        {
            "type": "class",
            "name_cs": "Autobus",
            "name_en": "Bus",
            "definition_cs": "Velkoobjemové vozidlo pro hromadnou dopravu osob",
            "definition_en": "Large capacity vehicle for public passenger transport",
            "comment_cs": "Kategorie M3 podle EU směrnice",
            "parent_class": "https://example.org/ontology/Vehicle",
            "source_element": "https://opendata.eselpoint.cz/esel-esb/eli/cz/sb/2001/56/2025-07-01#section-10"
        },
        {
            "type": "class",
            "name_cs": "Taxislužba",
            "name_en": "Taxi Service",
            "definition_cs": "Komerční přeprava osob na objednávku",
            "definition_en": "Commercial passenger transport on demand",
            "comment_cs": "Zvláštní druh silniční dopravy",
            "source_element": "https://opendata.eselpoint.cz/esel-esb/eli/cz/sb/2001/56/2025-07-01#section-11"
        },
        {
            "type": "property",
            "property_type": "DatatypeProperty",
            "name_cs": "maximální hmotnost",
            "name_en": "maximum weight",
            "definition_cs": "Největší povolená hmotnost vozidla v kg",
            "definition_en": "Maximum permitted vehicle weight in kg",
            "domain": "https://example.org/ontology/Vehicle",
            "range": "integer",
            "source_element": "https://opendata.eselpoint.cz/esel-esb/eli/cz/sb/2001/56/2025-07-01#section-12"
        },
        {
            "type": "property",
            "property_type": "ObjectProperty",
            "name_cs": "poskytuje službu",
            "name_en": "provides service",
            "definition_cs": "Vztah mezi vozidlem a poskytovanou službou",
            "definition_en": "Relationship between vehicle and provided service",
            "domain": "https://example.org/ontology/Vehicle",
            "range": "https://example.org/ontology/TaxiService",
            "source_element": "https://opendata.eselpoint.cz/esel-esb/eli/cz/sb/2001/56/2025-07-01#section-13"
        }
    ]
    
    # Add LLM extraction results
    success = service.add_extraction_results(extraction_results)
    print(f"   ✓ LLM extraction integration: {success}")
    
    if success:
        print(f"   Added {len(extraction_results)} concepts from LLM extraction")
        
        # Show updated ontology stats
        ontology = service.get_working_ontology()
        stats = ontology['stats']
        print(f"   Updated ontology: {stats.total_classes} classes, {stats.total_triples} triples")
    
    # Demonstrate natural language concept search
    print("\n🔍 Natural Language Concept Search:")
    
    search_queries = [
        ("autobus", "Czech: bus-related concepts"),
        ("taxi", "English: taxi-related concepts"),
        ("hmotnost", "Czech: weight-related concepts"),
        ("transport service", "English: transport service concepts"),
        ("vozidlo doprava", "Czech: vehicle transport concepts")
    ]
    
    for query, description in search_queries:
        print(f"\n   Query: '{query}' ({description})")
        
        try:
            results = service.search_by_concept(query)
            
            if results:
                print(f"   Found {len(results)} relevant concepts:")
                
                # Show top 3 results
                for i, result in enumerate(results[:3], 1):
                    labels = result.get('labels', {})
                    cs_label = labels.get('cs', 'N/A')
                    en_label = labels.get('en', 'N/A')
                    score = result.get('score', 0.0)
                    result_type = result.get('type', 'unknown')
                    
                    print(f"     {i}. {cs_label} ({en_label}) - {result_type}, score: {score:.3f}")
            else:
                print("     No relevant concepts found")
                
        except Exception as e:
            print(f"     Search error: {e}")
    
    # Demonstrate agent decision making with search
    print("\n🎯 Agent Decision Making with Concept Search:")
    
    # Scenario: Agent found "bus" in new text, checks for existing concepts
    print("\n   Scenario: Agent processing text containing 'městský autobus'...")
    
    bus_search = service.search_by_concept("městský autobus")
    print(f"   Found {len(bus_search)} related concepts")
    
    if bus_search:
        top_result = bus_search[0]
        if top_result['score'] > 0.7:
            print("   🔍 High similarity found - likely duplicate concept, skipping extraction")
            print(f"     Most similar: {top_result['labels'].get('cs', 'N/A')} (score: {top_result['score']:.3f})")
        else:
            print("   ➕ Low similarity - proceed with new concept extraction")
            print(f"     Most similar: {top_result['labels'].get('cs', 'N/A')} (score: {top_result['score']:.3f})")
    else:
        print("   ➕ No similar concepts found - proceed with new concept extraction")
    
    print("\n✅ Phase 4 LLM Integration & Agent Workflow demonstrated")


def demo_performance_and_caching():
    """Demonstrate performance characteristics and caching."""
    print("\n" + "="*70)
    print("5. PERFORMANCE & CACHING")
    print("="*70)
    
    service = OntologyService()
    
    print("\n⚡ Performance characteristics:")
    
    # Embedding caching
    if service.store.similarity_engine:
        print("✓ Semantic embeddings are computed once and cached")
        print("✓ Subsequent similarity searches use cached embeddings")
        print(f"✓ Current cache size: {len(service.store.class_embeddings)} class embeddings")
    else:
        print("⚠️  Semantic similarity not available")
    
    # RDF operations
    print("✓ RDF operations use in-memory graphs for fast access")
    print("✓ SPARQL-like queries for relationship traversal")
    print("✓ Namespace management for clean IRIs")
    
    # Memory usage
    ontology = service.get_working_ontology()
    print(f"✓ Current memory usage: {len(ontology['classes'])} classes in working graph")


def main():
    """Main demo function showcasing all ontology service capabilities."""
    print("="*70)
    print("ONTOLOGY SERVICE - COMPREHENSIVE FUNCTIONALITY DEMO")
    print("="*70)
    print("This demo showcases the complete ontology module for developers")
    print("of other modules (search, legislation, agent, etc.)")
    
    # Phase 1 & 2: Basic operations and retrieval
    service = demo_basic_ontology_operations()
    demo_retrieval_operations(service)
    
    # Phase 3: Semantic similarity
    demo_semantic_similarity(service)
    
    # Integration patterns for other modules
    demo_ai_agent_usage_patterns(service)
    
    # Phase 4: LLM Integration & Agent Workflow
    demo_phase4_llm_integration(service)
    
    # Performance characteristics
    demo_performance_and_caching()
    
    print("\n" + "="*70)
    print("DEMO SUMMARY - ONTOLOGY SERVICE CAPABILITIES")
    print("="*70)
    print("✅ PHASE 1: Core Foundation")
    print("   • Domain models (OntologyClass, OntologyProperty)")
    print("   • In-memory RDF store with namespace management")
    print("   • Service interface with proper error handling")
    
    print("\n✅ PHASE 2: Core Retrieval Operations")
    print("   • Complete CRUD operations for classes and properties")
    print("   • Relationship navigation and neighborhood discovery")
    print("   • Class hierarchy traversal (parent/child classes)")
    print("   • Property domain/range analysis")
    print("   • Complete ontology overview with statistics")
    
    print("\n✅ PHASE 3: Semantic Similarity")
    print("   • Multilingual embedding computation (384-dimensional)")
    print("   • Cosine similarity for concept discovery")
    print("   • Automatic embedding caching for performance")
    print("   • Cross-language concept matching")
    
    print("\n✅ PHASE 4: LLM Integration & Agent Workflow")
    print("   • LLM extraction result integration (add_extraction_results)")
    print("   • Natural language concept search (search_by_concept)")
    print("   • Semantic similarity-based deduplication")
    print("   • Agent decision support for concept extraction")
    print("   • Automated ontology building from LLM outputs")
    
    print("\n🔌 INTEGRATION READY FOR:")
    print("   • AI Agent: Context retrieval and concept deduplication")
    print("   • Search Module: Ontology-aware result ranking") 
    print("   • Legislation Module: Concept extraction validation")
    print("   • Index Module: Semantic concept enhancement")
    
    print("\n📋 PUBLIC INTERFACE (OntologyService only):")
    print("   • get_working_ontology() → Complete overview")
    print("   • get_class_neighborhood(iri) → Connected concepts")
    print("   • get_similar_classes(iri, limit) → Semantic discovery")
    print("   • get_property_details(iri) → Property information")
    print("   • get_class_hierarchy(iri) → Parent/child navigation")
    print("   • add_extraction_results(llm_results) → LLM integration")
    print("   • search_by_concept(natural_query) → Natural language search")
    
    print(f"\n🎯 ONTOLOGY MODULE COMPLETE - ALL 4 PHASES IMPLEMENTED!")
    print("Ready for integration with AI agent, search, legislation, and index modules.")


if __name__ == "__main__":
    main()
