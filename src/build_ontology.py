import asyncio
from ontology_modeling_agent.ontology_modeling_multi_agent import OntologyArchitect

async def main():
    """Main function to run the agent."""
    architect = OntologyArchitect(legal_act_id="https://opendata.eselpoint.cz/esel-esb/eli/cz/sb/2001/56/2025-07-01")
    await architect.build_ontology()

if __name__ == "__main__":
    asyncio.run(main())