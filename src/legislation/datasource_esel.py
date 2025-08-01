import json
import os
import re
from typing import List
from rdflib import Graph
from pydantic import AnyUrl
from .domain import LegalAct, LegalStructuralElement, LegalSection, LegalPart, LegalChapter, LegalDivision, create_legal_element
from .datasource import LegislationDataSource

class DataSourceESEL(LegislationDataSource):
    """
    Implementation of LegislationDataSource for the Czech legislation data source.
    """
    def __init__(self):
        """
        Initializes the data source with the SPARQL endpoint URL where the Czech legislation data can be accessed in RDF representation.
        """
        self.sparql_endpoint = "https://opendata.eselpoint.cz/sparql"

    def get_legal_act(self, legal_act_id: AnyUrl) -> LegalAct:
        """
        Retrieve a legal act by its unique identifier either from a local cache or from the SPARQL endpoint.
        If the legal act is not found in the local cache, it will be fetched from the SPARQL endpoint and stored in the cache.
        
        :param legal_act_id: Unique identifier for the legal act as IRI
        :return: LegalAct object
        """
        # Extract year, number, and date from the legal_act_id
        match = re.match(r"https://opendata\.eselpoint\.cz/esel-esb/eli/cz/sb/(\d{4})/(\d+)/(\d{4}-\d{2}-\d{2})", legal_act_id)
        if not match:
            raise ValueError(f"Invalid legal_act_id format: {legal_act_id}")
        year, number, date = match.groups()

        # Construct the file path relative to the workspace root
        workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
        file_name = f"{number}-{year}-{date}.json"
        file_path = os.path.join(workspace_root, "data", "legal_acts", file_name)

        # Check if the JSON file exists
        if os.path.exists(file_path):
            try:
                print(f"Debug: Loading file from: {file_path}")
                with open(file_path, "r", encoding="utf-8") as file:
                    data = json.load(file)
                    
                    # Use the factory function to properly parse nested objects with correct types
                    legal_act = create_legal_element(data)
                    
                    return legal_act
            except Exception as e:
                raise RuntimeError(f"Failed to load legal act from file: {e}")
        else:
            # If the file does not exist, fetch the data from the SPARQL endpoint
            legal_act = self._load_legal_act_from_esel(legal_act_id)

            # Save the fetched data to a JSON file
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            try:
                with open(file_path, "w", encoding="utf-8") as file:
                    file.write(legal_act.model_dump_json(indent=2))
            except Exception as e:
                raise RuntimeError(f"Failed to save legal act to file: {e}")

            return legal_act

    def _load_legal_act_from_esel(self, legal_act_id: str) -> LegalAct:
        """
        Fetches a legal act by its ID from the SPARQL endpoint.

        :param legal_act_id: The ID of the legal act to fetch
        :return: An instance of LegalAct containing the fetched data
        """
        title = self._load_legal_act_name_from_esel(legal_act_id)

        # Extract year and number from the legal_act_id
        match = re.match(r"https://opendata\.eselpoint\.cz/esel-esb/eli/cz/sb/(\d{4})/(\d+)/.*", legal_act_id)
        if not match:
            raise ValueError(f"Invalid legal_act_id format: {legal_act_id}")
        year, number = match.groups()
        officialIdentifier = f"{number}/{year}"

        legal_act = LegalAct(
            id=legal_act_id,
            title=title,
            officialIdentifier=officialIdentifier,
            elements=[]
        )

        return self._load_legal_act_content_from_esel(legal_act)

    def _load_legal_act_name_from_esel(self, legal_act_id: str) -> str:
        """
        Loads the name of a legal act from the SPARQL endpoint using the provided query.

        :return: The name of the legal act
        """
        g = Graph()
        sparql_str = f"""
            PREFIX esel: <https://slovník.gov.cz/datový/sbírka/pojem/>

            SELECT ?nazev
            WHERE {{
                SERVICE <{self.sparql_endpoint}> {{
                    <{legal_act_id}> esel:má-fragment-znění ?fragment .

                    ?fragment esel:obsahuje-fragment ?fragment_s_nazvem .

                    ?fragment_s_nazvem esel:má-typ-fragmentu <https://opendata.eselpoint.cz/esel-esb/cis-esb-typ-fragmentu/položka/Prefix_Title> ;
                    esel:text-fragmentu ?nazev .
                }}
            }}
        """
        try:
            results = g.query(sparql_str)
            name = ""
            for row in results:
                name = str(row.nazev)
            return name
        except Exception as e:
            raise RuntimeError(f"Failed to load legal act name: {e}")
    
    def _load_legal_act_content_from_esel(self, legal_act: LegalAct) -> LegalAct:
        """
        Loads the content of a legal act from the SPARQL endpoint using the provided query.

        :param legal_act_id: The ID of the legal act to fetch
        :return: An instance of LegalAct containing the fetched data
        """
        g = Graph()
        sparql_str = f"""
            PREFIX esel: <https://slovník.gov.cz/datový/sbírka/pojem/>

            SELECT ?fragment_id ?citace ?hierarchie ?poradi ?obsah
            WHERE {{
                SERVICE <{self.sparql_endpoint}> {{
                    <{legal_act.id}> esel:má-fragment-znění ?fragment_id .

                    {{
                        ?fragment_id esel:citace-označení-fragmentu-znění-právního-aktu ?citace ;
                            esel:hierarchie-fragmentu-znění-právního-aktu ?hierarchie ;
                            esel:pořadí-fragmentu-znění-právního-aktu ?poradi ;
                            esel:obsahuje-fragment/esel:text-fragmentu ?obsah .
                    }} UNION {{
                        ?fragment_id 
                            esel:hierarchie-fragmentu-znění-právního-aktu ?hierarchie ;
                            esel:pořadí-fragmentu-znění-právního-aktu ?poradi ;
                            esel:obsahuje-fragment ?fragment_s_textem .
                        ?fragment_s_textem esel:text-fragmentu ?obsah ;
                            esel:má-typ-fragmentu <https://opendata.eselpoint.cz/esel-esb/cis-esb-typ-fragmentu/položka/Nadpis_pod>
                        BIND("Nadpis" AS ?citace)
                    }}
                }}
            }}
            ORDER BY ?poradi
        """

        try:
            results = g.query(sparql_str)

            current_parent = legal_act
            last_element = None
            legal_elements = {}

            sections_data = {}
            section_hierarchy_prefix = None
            
            for row in results: # !!!!!!!!! par 7g u 56/2001 nezpracujeme správně - není jako fragment, ale jako text přímo
                citace = str(row.citace)
                fragment_id = str(row.fragment_id)
                hierarchie = str(row.hierarchie)
                obsah = str(row.obsah)
                                
                # Check if the citation is a part of the legal act
                part_match = re.match(r"^Část\s+(\d+[a-z]*)$", citace)
                if part_match:
                    part_number = part_match.group(1)
                    
                    new_legal_part = LegalPart(
                        id=fragment_id,
                        officialIdentifier=citace,
                        title=citace,
                        elements=[],
                        textContent=None,
                    )

                    # A part is a top-level element, so we reset to legal_act
                    current_parent = legal_act
                    current_parent.elements.append(new_legal_part)
                    current_parent = new_legal_part
                    legal_elements[f"Část {part_number}"] = new_legal_part
                    last_element = new_legal_part
                    continue
                
                # Check if the citation is a chapter of the legal act
                chapter_match = re.match(r"^Část\s+(\d+[a-z]*)\s+Hlava\s+(\d+[a-z]*)$", citace)
                if chapter_match:
                    part_number = chapter_match.group(1)
                    chapter_number = chapter_match.group(2)
                    
                    new_legal_chapter = LegalChapter(
                        id=fragment_id,
                        officialIdentifier=citace,
                        title=citace,
                        elements=[],
                        textContent=None,
                    )

                    # A chapter is a sub-element of a part, so we need to find the part
                    current_parent = legal_elements.get(f"Část {part_number}", legal_act)
                    current_parent.elements.append(new_legal_chapter)
                    current_parent = new_legal_chapter
                    legal_elements[f"Část {part_number} Hlava {chapter_number}"] = new_legal_chapter
                    last_element = new_legal_chapter
                    continue
                
                # Check if the citation is a division of the legal act
                division_match = re.match(r"^Část\s+(\d+[a-z]*)\s+Hlava\s+(\d+[a-z]*)\s+Díl\s+(\d+[a-z]*)$", citace)
                if division_match:
                    part_number = division_match.group(1)
                    chapter_number = division_match.group(2)
                    division_number = division_match.group(3)
                    
                    new_legal_division = LegalDivision(
                        id=fragment_id,
                        officialIdentifier=citace,
                        title=citace,
                        elements=[],
                        textContent=None,
                    )

                    # A division is a sub-element of a chapter, so we need to find the chapter
                    current_parent = legal_elements.get(f"Část {part_number} Hlava {chapter_number}", legal_act)
                    current_parent.elements.append(new_legal_division)
                    current_parent = new_legal_division
                    legal_elements[f"Část {part_number} Hlava {chapter_number} Díl {division_number}"] = new_legal_division
                    last_element = new_legal_division
                    continue
                
                # Handle section fragments (§)
                section_match = re.match(r"^§\s*(\d+[a-z]*).*", citace)
                if section_match:
                    section_number = section_match.group(1)
                    
                    # Initialize section data if not exists
                    if section_number not in sections_data:
                        sections_data[section_number] = {
                            'fragments': [],
                            'title': None,
                            'parent': current_parent,
                            'section_id': fragment_id,
                        }
                        last_element = sections_data[section_number]
                        section_hierarchy_prefix = hierarchie

                    # Cut the section_hierarchy_prefix from hierarchie if present
                    if section_hierarchy_prefix and hierarchie.startswith(section_hierarchy_prefix):
                        hierarchie = hierarchie[len(section_hierarchy_prefix):]
                        if hierarchie.startswith('/'):
                            hierarchie = hierarchie[1:]

                    hierarchie = "1/" + hierarchie.strip('/')
                    
                    # Store fragment data for later processing
                    sections_data[section_number]['fragments'].append({
                        'hierarchie': hierarchie, # We need to cut the prefix that is common for all fragments in the same section. It is the value of 'hierarchie' property of the first fragment in the section.
                        'obsah': obsah,
                        'citace': citace,
                        'fragment_id': fragment_id
                    })
                    continue

                title_match = re.match(r"^Nadpis$", citace)
                if title_match:
                    # If the fragment is a title, we set it as the title of the current element
                    if last_element:
                        if isinstance(last_element, LegalStructuralElement):
                            last_element.title = obsah.strip()
                        else:
                            last_element['title'] = obsah.strip()
                    continue
            
            # Process collected sections and add them to their respective parents
            for section_number, section_data in sections_data.items():
                fragments = section_data['fragments']
                title = section_data['title']
                parent_element = section_data['parent']
                section_id = section_data['section_id']
                
                # Build hierarchical XML structure for section content
                xml_content = self._build_hierarchical_xml(fragments)
                
                new_section = LegalSection(
                    id=section_id,
                    officialIdentifier=f"§ {section_number}",
                    title=title if title else f"§ {section_number}",
                    textContent=xml_content,
                    elements=[],
                )
                
                parent_element.elements.append(new_section)
            
            return legal_act
        except Exception as e:
            raise RuntimeError(f"Failed to load legal act: {e}")
    
    def _build_hierarchical_xml(self, fragments):
        """
        Build hierarchical XML structure from fragments based on their hierarchy.
        """
        
        # Build hierarchy tree
        hierarchy_tree = {}
        
        for fragment in fragments:
            hierarchie = fragment['hierarchie']
            hierarchy_parts = hierarchie.strip('/').split('/')
            
            # Navigate to the correct position in the tree
            current_level = hierarchy_tree
            for part in hierarchy_parts[:-1]:
                if part not in current_level:
                    current_level[part] = {'children': {}, 'content': '', 'id': ''}
                current_level = current_level[part]['children']
            
            # Add the fragment at the final level
            final_part = hierarchy_parts[-1]
            if final_part not in current_level:
                current_level[final_part] = {'children': {}, 'content': '', 'id': ''}
            
            # Clean HTML from content
            clean_content = re.sub(r"<[^>]*>", "", fragment['obsah'])
            current_level[final_part]['content'] = clean_content
            current_level[final_part]['id'] = fragment['fragment_id']

        return self._tree_to_xml(hierarchy_tree)
    
    def _tree_to_xml(self, tree, level=0):
        """
        Convert hierarchy tree to XML string.
        """
        xml_parts = []
        
        for key in tree.keys():
            node = tree[key]
            indent = "  " * level
            
            if node['content'] or node['children']:
                xml_parts.append(f"{indent}<f id=\"{node['id']}\">")
                
                if node['content']:
                    # Add content with proper indentation
                    content_lines = node['content'].strip().split('\n')
                    for line in content_lines:
                        if line.strip():
                            xml_parts.append(f"{indent}  {line.strip()}")
                
                if node['children']:
                    xml_parts.append(self._tree_to_xml(node['children'], level + 1))
                
                xml_parts.append(f"{indent}</f>")
        
        return '\n'.join(xml_parts)

    def get_legal_act_element(self, element_id: AnyUrl) -> LegalStructuralElement:
        """
        Retrieve a legal act structural element by its unique identifier.
        This method finds the element within the cached legal acts.
        
        :param element_id: Unique identifier for the structural element as IRI
        :return: LegalStructuralElement object
        """
        # Extract the legal act ID from the element ID
        # Element IDs are typically in format: {legal_act_id}/par_{section_number} or similar
        element_id_str = str(element_id)
        
        # Try to extract legal act ID from element ID
        if '/par_' in element_id_str:
            legal_act_id = element_id_str.split('/par_')[0]
        else:
            # If it's not a section, try to find the legal act ID in other ways
            # For now, assume the element_id is the fragment_id from SPARQL
            legal_act_id = self._extract_legal_act_id_from_fragment(element_id_str)
        
        # Get the legal act first
        legal_act = self.get_legal_act(legal_act_id)
        
        # Search for the element within the legal act
        found_element = self._find_element_by_id(legal_act, element_id_str)
        if found_element:
            return found_element
        else:
            raise ValueError(f"Legal structural element with ID {element_id} not found")
    
    def store_legal_act(self, legal_act: LegalAct) -> None:
        """
        Store a legal act as a JSON file in the data/legal_acts directory.
        
        :param legal_act: LegalAct object to store
        """
        # Extract year, number, and date from the legal_act_id
        legal_act_id = str(legal_act.id)
        match = re.match(r"https://opendata\.eselpoint\.cz/esel-esb/eli/cz/sb/(\d{4})/(\d+)/(\d{4}-\d{2}-\d{2})", legal_act_id)
        if not match:
            raise ValueError(f"Invalid legal_act_id format: {legal_act_id}")
        year, number, date = match.groups()

        # Construct the file path relative to the workspace root
        workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
        file_name = f"{number}-{year}-{date}.json"
        file_path = os.path.join(workspace_root, "data", "legal_acts", file_name)

        # Save the legal act to a JSON file
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        try:
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(legal_act.model_dump_json(indent=2))
        except Exception as e:
            raise RuntimeError(f"Failed to save legal act to file: {e}")
    
    def _extract_legal_act_id_from_fragment(self, fragment_id: str) -> str:
        """
        Extract legal act ID from a fragment ID by querying SPARQL.
        
        :param fragment_id: Fragment identifier
        :return: Legal act identifier
        """
        # This is a simplified implementation - in practice, you might need
        # to query SPARQL to find which legal act contains this fragment
        # For now, we'll try to parse it from common patterns
        if 'esel-esb/eli/cz/sb/' in fragment_id:
            # Extract the base legal act URL
            parts = fragment_id.split('/')
            if len(parts) >= 7:
                return '/'.join(parts[:7])  # Get the base legal act URL
        
        raise ValueError(f"Cannot extract legal act ID from fragment ID: {fragment_id}")
    
    def _find_element_by_id(self, element: LegalStructuralElement, target_id: str) -> LegalStructuralElement:
        """
        Recursively search for an element by its ID within a legal structure.
        
        :param element: The element to search in
        :param target_id: The ID to search for
        :return: The found element or None
        """
        if str(element.id) == target_id:
            return element
        
        if element.elements:
            for sub_element in element.elements:
                found = self._find_element_by_id(sub_element, target_id)
                if found:
                    return found
        
        return None
