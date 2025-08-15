from typing import List, Dict, Any
from pydantic import AnyUrl

from agents import function_tool

from legislation.datasource_esel import DataSourceESEL
from legislation.service import LegislationService
from legislation.domain import LegalStructuralElement

DEFAULT_LLM_MODEL = "gpt-4.1-mini"

def _service() -> LegislationService:
	"""Factory for LegislationService (lazy to avoid cost until tool used)."""
	# We use the real ESEL datasource; summarization will run only if summaries
	# are missing and OPENAI_API_KEY is set. This keeps the tool simple.
	return LegislationService(DataSourceESEL(), DEFAULT_LLM_MODEL)

service = _service()


#@function_tool
async def list_child_elements(legal_element_iri: str) -> List[str]:
    element = service.get_legal_act_element(AnyUrl(legal_element_iri))
    children = element.elements or []

    return [
        _render(
            LegalStructuralElement(
                id=child.id,
                officialIdentifier=child.officialIdentifier,
                title=child.title,
                summary=child.summary,
                summary_names=child.summary_names,
                elementType=child.elementType
            )
        ) for child in children or []
    ]


#@function_tool
def get_element(legal_element_iri: str) -> str:
    element = service.get_legal_act_element(AnyUrl(legal_element_iri))

    return _render(element)

def _render(el, indent: int = 0) -> str:
    """Recursively render a LegalStructuralElement to an XML string.

    Produces the same structural style as `list_child_elements` but
    includes all relevant fields from legislation.domain.LegalStructuralElement.
    """
    ind = "\t" * indent
    lines: List[str] = []
    # Start element tag with id attribute
    lines.append(f'{ind}<{el.elementType} id="{str(el.id)}">')

    # Basic scalar fields
    lines.append(f'{ind}\t<officialIdentifier>{str(el.officialIdentifier or "")}</officialIdentifier>')
    lines.append(f'{ind}\t<title>{str(el.title or "")}</title>')
    lines.append(f'{ind}\t<summary>{str(el.summary or "")}</summary>')

    # summary_names may be a list
    sn = getattr(el, 'summary_names', None)
    if sn:
        lines.append(f'{ind}\t<terms>')
        for name in sn:
            lines.append(f'{ind}\t\t<term>{str(name)}</term>')
        lines.append(f'{ind}\t</terms>')

    # text content
    text_content = getattr(el, 'textContent', "")
    if (text_content != ""):
        lines.append(f'{ind}\t<text-with-fragments>{str(text_content)}</text-with-fragments>')

    # Nested elements (recursively render)
    children = getattr(el, 'elements', None) or []
    if children:
        for child in children:
            # child may already be a model instance
            lines.append(_render(child, indent + 1))

    # Close tag
    lines.append(f'{ind}</{el.elementType}>')
    return "\n".join(lines)