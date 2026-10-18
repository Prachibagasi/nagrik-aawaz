import csv
import os
import re
from typing import Dict, List, Any
import ollama
import json

class JDSummarizerAgent:
    """Agent to parse and summarize job descriptions into structured data"""
    
    def __init__(self, csv_path: str = "job_description.csv"):
        """Initialize JD Summarizer Agent
        
        Args:
            csv_path: Path to the CSV file containing job descriptions
        """
        self.csv_path = csv_path
        # A chat-capable model is required for LLM extraction. (nomic-embed-text is an
        # embedding model and cannot chat.) Override with $OLLAMA_CHAT_MODEL.
        self.chat_model = os.environ.get("OLLAMA_CHAT_MODEL", "llama3")
        self._llm_available = True  # flips to False after the first failure, so we don't retry per JD
        
    def load_jds(self) -> List[Dict[str, str]]:
        """Load job descriptions from CSV file
        
        Returns:
            List of dictionaries containing job title and description
        """
        job_descriptions = []
        # Try different encodings
        encodings = ['utf-8', 'latin-1', 'cp1252']
        
        for encoding in encodings:
            try:
                with open(self.csv_path, 'r', encoding=encoding) as file:
                    reader = csv.DictReader(file)
                    for row in reader:
                        if 'Job Title' in row and 'Job Description' in row:
                            job_descriptions.append({
                                'title': row['Job Title'].strip(),
                                'description': row['Job Description'].strip()
                            })
                # If we get here without error, break the loop
                print(f"Successfully read CSV with {encoding} encoding")
                return job_descriptions
            except UnicodeDecodeError:
                # Try next encoding
                continue
            except Exception as e:
                print(f"Error loading job descriptions: {str(e)}")
        
        # If we've tried all encodings and still failed
        if not job_descriptions:
            print("Could not read the CSV file with any of the attempted encodings")
        
        return job_descriptions
    
    def summarize_jd(self, jd: Dict[str, str]) -> Dict[str, Any]:
        """Parse and summarize a job description
        
        Args:
            jd: Dictionary containing job title and description
            
        Returns:
            Dictionary with structured data extracted from the job description
        """
        try:
            # Using Ollama to extract structured information
            prompt = f"""
            Extract the following information from this job description and format as JSON:
            1. Required Skills (as a list of strings)
            2. Years of Experience (extract numbers and text)
            3. Education (degrees required)
            4. Certifications (if any, as a list)
            5. Responsibilities (as a list of strings)
            
            Job Title: {jd['title']}
            Job Description: {jd['description']}
            
            Format your response as a valid JSON object with these keys:
            required_skills, years_of_experience, education, certifications, responsibilities
            """
            
            extracted_data = None
            if self._llm_available:
                try:
                    response = ollama.chat(
                        model=self.chat_model,
                        messages=[{"role": "user", "content": prompt}],
                        format="json",  # ask Ollama to return valid JSON
                    )
                    response_text = response['message']['content']
                    
                    # Some models still wrap JSON in a markdown fence
                    json_match = re.search(r'```json\n(.*?)\n```', response_text, re.DOTALL)
                    if json_match:
                        response_text = json_match.group(1)
                    
                    extracted_data = self._normalize_llm_output(json.loads(response_text))
                    extracted_data['extraction_method'] = 'llm'
                except Exception as e:
                    self._llm_available = False
                    print(f"LLM extraction unavailable with model '{self.chat_model}' ({str(e)}). "
                          f"Using rule-based extraction for all job descriptions. "
                          f"(Run `ollama pull {self.chat_model}` or set OLLAMA_CHAT_MODEL.)")
            
            if extracted_data is None:
                extracted_data = self._rule_based_extraction(jd)
                extracted_data['extraction_method'] = 'rules'
                
            # Add the raw JD for reference
            extracted_data['raw_jd'] = jd['description']
            return extracted_data
            
        except Exception as e:
            print(f"Error summarizing job description: {str(e)}")
            return {
                'required_skills': [],
                'years_of_experience': 'N/A',
                'education': 'N/A',
                'certifications': [],
                'responsibilities': [],
                'raw_jd': jd['description']
            }
    
    @staticmethod
    def _normalize_llm_output(data: Any) -> Dict[str, Any]:
        """Coerce LLM output into the shape the rest of the pipeline expects.

        Models sometimes return a list where a string is expected (or vice versa);
        the database layer and embedding formatter assume the types below.
        """
        if not isinstance(data, dict):
            raise ValueError("LLM did not return a JSON object")

        def as_list(value):
            if value is None or value == "":
                return []
            if isinstance(value, list):
                return [str(v).strip() for v in value if str(v).strip()]
            return [part.strip() for part in str(value).split(",") if part.strip()]

        def as_text(value):
            if isinstance(value, list):
                return ", ".join(str(v) for v in value)
            return "" if value is None else str(value)

        return {
            'required_skills': as_list(data.get('required_skills')),
            'years_of_experience': as_text(data.get('years_of_experience')) or 'N/A',
            'education': as_text(data.get('education')) or 'N/A',
            'certifications': as_list(data.get('certifications')),
            'responsibilities': as_list(data.get('responsibilities')),
        }
    
    def _rule_based_extraction(self, jd: Dict[str, str]) -> Dict[str, Any]:
        """Rule-based extraction of JD data as fallback
        
        Args:
            jd: Dictionary containing job title and description
            
        Returns:
            Dictionary with structured data extracted from the job description
        """
        description = jd['description']
        
        # Extract skills (look for technical terms and skill keywords)
        skills_pattern = r'(?:skills|proficiency in|experience with|knowledge of).*?(?:\.|\n)'
        skills_matches = re.findall(skills_pattern, description, re.IGNORECASE)
        skills = []
        for match in skills_matches:
            # Extract individual skills
            tech_skills = re.findall(r'([A-Z][a-zA-Z\+\#]+(?:\.[a-zA-Z\+\#]+)?|\b[Pp]ython\b|\b[Jj]ava\b|\b[Cc]\+\+\b|\bSQL\b|\bAWS\b|\bGCP\b|\bDocker\b|\bKubernetes\b|\bTensorFlow\b|\bPyTorch\b)', match)
            skills.extend(tech_skills)
        
        # Extract years of experience
        years_pattern = r'(\d+[\+]?(?:\s*-\s*\d+)?)\s*(?:years|yrs)(?:\s*of)?(?:\s*experience)?'
        years_match = re.search(years_pattern, description, re.IGNORECASE)
        years_experience = years_match.group(0) if years_match else "N/A"
        
        # Extract education requirements
        education_pattern = r"(?:Bachelor'?s?|Master'?s?|PhD|Doctorate|degree)(?:[^.]*(?:in|of)[^.]*?)(?:\.|;|\n)"
        education_match = re.search(education_pattern, description, re.IGNORECASE)
        education = education_match.group(0).strip() if education_match else "N/A"
        
        # Extract certifications
        cert_pattern = r'(?:certifications?|certified)(?:[^.]*?)(?:\.|;|\n)'
        cert_match = re.search(cert_pattern, description, re.IGNORECASE)
        certifications = []
        if cert_match:
            cert_text = cert_match.group(0)
            specific_certs = re.findall(r'([A-Z0-9\+\#]+(?:[^\s,.])*)', cert_text)
            certifications = [cert for cert in specific_certs if len(cert) > 2]
        
        # Extract responsibilities
        resp_section = None
        if 'Responsibilities:' in description:
            resp_section = description.split('Responsibilities:')[1].split('Qualifications:')[0]
        elif 'Responsibilities' in description:
            resp_section = description.split('Responsibilities')[1].split('Qualifications')[0]
        
        responsibilities = []
        if resp_section:
            # Look for bullet points or numbered lists
            resp_items = re.findall(r'(?:•|\*|\d+\.|\-)\s*(.*?)(?=(?:•|\*|\d+\.|\-|$))', resp_section)
            if resp_items:
                responsibilities = [item.strip() for item in resp_items if item.strip()]
            else:
                # Split by sentences if no bullet points
                resp_sentences = re.findall(r'([^.\n]+\.[^\n]*)', resp_section)
                responsibilities = [sent.strip() for sent in resp_sentences if sent.strip()]
        
        return {
            'required_skills': list(set(skills)),
            'years_of_experience': years_experience,
            'education': education,
            'certifications': certifications,
            'responsibilities': responsibilities
        }
    
    def process_all_jds(self) -> List[Dict[str, Any]]:
        """Process all job descriptions from the CSV file
        
        Returns:
            List of dictionaries with summarized job data
        """
        jds = self.load_jds()
        summarized_jds = []
        
        for jd in jds:
            print(f"Summarizing JD: {jd['title']}")
            summary = self.summarize_jd(jd)
            summarized_jds.append({
                'title': jd['title'],
                'summary': summary
            })
        
        return summarized_jds 