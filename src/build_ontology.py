import asyncio
from ontology_modeling_agent.ontology_modeling_agent import OntologyModelingAgent

async def main():
    """Main function to run the agent."""
    agent = OntologyModelingAgent(legal_act_id="https://opendata.eselpoint.cz/esel-esb/eli/cz/sb/2001/56/2025-07-01")
    await agent.build_ontology()

if __name__ == "__main__":
    asyncio.run(main())