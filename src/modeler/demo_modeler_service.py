"""
Demo script for the ModelerService showcasing ontology modeling functionality.

This demo demonstrates how to use the ModelerService to model an ontology
from a legal act text using automated analysis and LLM processing.

HOW TO RUN:
The virtual environment .venv should be activated before running the demo.

From the src directory, run:
    python -m modeler.demo_modeler_service

Or from the project root:
    cd src; python -m modeler.demo_modeler_service

The demo requires:
- OPENAI_API_KEY environment variable to be set
- Pre-built indexes for the legal act (run build_indexes.py if needed)
"""

import os
from .service import ModelerService

def demo_model_ontology():
    """
    Demonstrate the ontology modeling functionality.
    """
    print("=" * 60)
    print("ModelerService Demo - Ontology Modeling")
    print("=" * 60)
    
    # Legal act configuration
    legal_act_id = "https://opendata.eselpoint.cz/esel-esb/eli/cz/sb/2001/56/2025-07-01"
    llm_model = "gpt-4.1-mini"  # Using the project's standard model
    
    print(f"Legal Act ID: {legal_act_id}")
    print(f"LLM Model: {llm_model}")
    print()
    
    try:
        # Initialize the ModelerService
        print("Initializing ModelerService...")
        modeler_service = ModelerService(legal_act_id, llm_model)
        print("✓ ModelerService initialized successfully")
        print()
        
        # Display basic information about the legal act
        print("Legal Act Information:")
        print(f"  Title: {modeler_service.legal_act.title}")
        print(f"  ID: {modeler_service.legal_act.id}")
        print(f"  Element Type: {modeler_service.legal_act.elementType}")
        print()
        
        # Get and display seed terms
        print("Getting seed terms from the legal act...")
        seed_terms = modeler_service._get_top_k_seed_terms(k=10)
        print(f"Found {len(seed_terms)} seed terms:")
        for i, term_data in enumerate(seed_terms, 1):
            print(f"  {i:2d}. {term_data['term']} (freq: {term_data['frequency']:.4f}, count: {term_data['raw_count']})")
        print()
        
        # Model the ontology
        print("Starting ontology modeling process...")
        print("This will process each seed term and find relevant legal sections...")
        print()
        
        owl_ontology = modeler_service.model_ontology()
        
        print("Ontology modeling completed!")
        print(f"Generated OWL ontology length: {len(owl_ontology)} characters")
        
        if owl_ontology:
            print("\nGenerated OWL Ontology:")
            print("-" * 40)
            print(owl_ontology)
        else:
            print("\nNote: The current implementation returns an empty ontology.")
            print("This is expected as the method is still under development.")
        
    except Exception as e:
        print(f"✗ Error during ontology modeling: {e}")
        import traceback
        traceback.print_exc()

def main():
    """
    Main function to run the demo.
    """
    # Check for required environment variables
    if not os.getenv("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY environment variable not set.")
        print("Setting dummy value for demo purposes...")
        os.environ["OPENAI_API_KEY"] = "dummy-key-for-demo"
    
    try:
        demo_model_ontology()
        print("\n" + "=" * 60)
        print("Demo completed successfully!")
        return 0
    except Exception as e:
        print(f"\n✗ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
