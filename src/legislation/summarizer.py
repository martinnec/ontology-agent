import os
import re
from typing import List
from dotenv import load_dotenv
from openai import OpenAI

from .domain import LegalAct, LegalStructuralElement


load_dotenv()

summarization_system_prompt = """<ROLE>You are a helpful assistant that summarizes legal texts.</ROLE>
<TASK>Your task is to generate a concise summary of the provided legal text content.</TASK>
<INSTRUCTIONS>
- The summary must capture the main real-world semantic concepts and relationships defined, described or constrained by the original text.
- The summary must be concise, ideally up to 100 words.
- The summary must first briefly mention core semantic concepts and relationships, then provide a more detailed explanation of the text if there is some space left.
- The summary must directly summarize the text. It is prohibited to:
  --- refer to the original text as "the text" or "the document"
  --- start with "Summary of" or similar phrases,
  --- include text such as "Short summary of", "Detailed explanation of", etc.
  --- include legal jargon, citations, or references.
- The summary must be in the same language as the given text.
</INSTRUCTIONS>"""
summarization_user_prompt = """<TEXT-TO-SUMMARIZE>{text}</TEXT-TO-SUMMARIZE>"""

concept_list_system_prompt = """<ROLE>You are a helpful assistant that finds important semantic concepts and relationships between them in legal texts.</ROLE>
<TASK>Your task is to identify important semantic concepts and relationships in the provided legal text content and list their names.</TASK>
<INSTRUCTIONS>
- The concepts and relationships must be directly extracted from the text.
- The names must be concise, ideally 1-3 words but no more than 5 words each.
- The names must be in their basic form (singular and first case for nouns, singular present tense for verbs, etc.)
- The names must be in the same language as the given text.
- Separate names by newlines.
</INSTRUCTIONS>"""
concept_list_user_prompt = """<TEXT-TO-EXTRACT-CONCEPTS>{text}</TEXT-TO-EXTRACT-CONCEPTS>"""

class LegislationSummarizer:
    """
    This class is responsible for summarizing structural elements of legal acts.
    """

    def __init__(self, model: str):
        """
        Initialize the summarizer with a specific language model for text summarization.

        :param model: The language model to use for summarization
        :raises ValueError: If the OPENAI_API_KEY is not found in environment variables
        """
        self.model = model
        self.open_api_key = os.getenv("OPENAI_API_KEY")
        if not self.open_api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        self.client = OpenAI(api_key=self.open_api_key)

    def summarize(self, legal_act: LegalAct) -> LegalAct:
        """
        Generate summaries for parts, chapters, divisions, and sections of a legal act.
        Traverses the structural elements in depth-first order and generates summaries
        in bottom-up order.

        :param legal_act: LegalAct object to summarize
        :return: LegalAct object with summaries
        """
        # Directly modify the original legal_act instead of copying
        summarized_act = legal_act
        
        # Perform depth-first traversal and bottom-up summarization
        self._summarize_element(summarized_act)
        
        return summarized_act
    
    def _summarize_element(self, element: LegalStructuralElement) -> str:
        """
        Recursively summarize a structural element and its sub-elements.
        Performs depth-first traversal and bottom-up summarization.
        Also extracts concept names for each element.
        
        :param element: The structural element to summarize
        :return: The summary of the element
        """
        summaries = []
        
        # First, traverse all sub-elements (depth-first)
        if element.elements:
            for sub_element in element.elements:
                # Recursively summarize sub-elements first (depth-first)
                sub_summary = self._summarize_element(sub_element)
                summaries.append(sub_summary)
        
        # Now summarize the current element (bottom-up)
        content_for_processing = None
        
        if element.textContent and not summaries:
            # Leaf element with text content - summarize based on text
            content_for_processing = element.textContent
            element.summary = self._summarize_text(element.textContent)
        elif summaries:
            # Non-leaf element - summarize based on sub-element summaries
            combined_summaries = " ".join(summaries)
            content_for_processing = combined_summaries
            element.summary = self._summarize_text(combined_summaries)
        elif element.textContent:
            # Element has both text content and sub-elements
            all_content = element.textContent + " " + " ".join(summaries)
            content_for_processing = all_content
            element.summary = self._summarize_text(all_content)
        else:
            # Element has no content to summarize
            element.summary = f"Summary of {element.title}"
            content_for_processing = element.title

        # Extract concept names if we have content to process
        if content_for_processing:
            element.summary_names = self._extract_concept_names(content_for_processing)
        else:
            element.summary_names = []

        print(f"Summarized element ID: {element.officialIdentifier}, Summary: {element.summary}")
        print(f"Extracted concept names: {element.summary_names}")

        return element.summary
    
    def _summarize_text(self, text: str) -> str:
        """
        Helper method to generate a summary of the given text content.
        
        :param text: The text content to summarize
        :return: A summary of the text
        """
        if not text or not text.strip():
            raise ValueError("No content available for summary")
        
        messages=[
            {"role": "system", "content": summarization_system_prompt},
            {"role": "user", "content": summarization_user_prompt.format(text=text)}
        ]
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=1000,  # Adjust as needed for summary length
            temperature=0.2  # Adjust for creativity in summarization
        )
        if response.choices:
            return response.choices[0].message.content.strip()
        else:
            raise ValueError("No summary generated from the text content")
    
    def _extract_concept_names(self, text: str) -> List[str]:
        """
        Helper method to extract names of important concepts and relationships from the given text content.
        
        :param text: The text content to extract concepts from
        :return: A list of concept names
        """
        if not text or not text.strip():
            return []
        
        messages=[
            {"role": "system", "content": concept_list_system_prompt},
            {"role": "user", "content": concept_list_user_prompt.format(text=text)}
        ]
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=500,  # Adjust as needed for concept list length
            temperature=0.1  # Lower temperature for more consistent concept extraction
        )
        
        if response.choices:
            concept_text = response.choices[0].message.content.strip()
            # Parse the response to extract individual concept names
            # Assuming the LLM returns concepts separated by newlines or commas
            concepts = []
            for line in concept_text.split('\n'):
                line = line.strip()
                if line:
                    # Remove bullet points, numbers, or other formatting
                    line = re.sub(r'^[-•*\d+\.\)]\s*', '', line)
                    # Split by commas if multiple concepts are on one line
                    if ',' in line:
                        concepts.extend([c.strip() for c in line.split(',') if c.strip()])
                    else:
                        concepts.append(line)
            
            # Filter out empty strings and duplicates while preserving order
            seen = set()
            filtered_concepts = []
            for concept in concepts:
                if concept and concept not in seen:
                    seen.add(concept)
                    filtered_concepts.append(concept)
            
            return filtered_concepts
        else:
            return []
