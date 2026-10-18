import os
import re
try:
    import pymupdf as fitz  # PyMuPDF >= 1.24.3
except ImportError:  # older PyMuPDF only exposes the legacy name
    import fitz  # type: ignore
from typing import Dict, List, Any, Optional

from utils.skills import TECH_KEYWORDS, extract_tech

# Resumes with less extractable text than this are treated as scanned images.
MIN_TEXT_CHARS = 50

# A line that is *exactly* one of these (case-insensitive, optional trailing colon)
# starts a new section. Matching whole lines avoids the old bug where a wrapped
# line beginning with "experience ..." cut the previous section short.
SECTION_HEADINGS = {
    'education': {'education', 'academic background', 'academic qualification',
                  'academic qualifications'},
    'experience': {'experience', 'work experience', 'professional experience',
                   'work history', 'employment', 'employment history'},
    'skills': {'skills', 'technical skills', 'core competencies'},
    'certifications': {'certifications', 'certification', 'certificates',
                       'professional certifications'},
    'projects': {'projects'},
    'achievements': {'achievements', 'awards'},
    'tech_stack': {'tech stack', 'technologies', 'technical stack'},
}
_HEADING_LOOKUP = {h: key for key, names in SECTION_HEADINGS.items() for h in names}

# Lines that are document titles, not names.
_TITLE_LINES = {'candidate resume', 'resume', 'curriculum vitae', 'cv', 'candidate cv'}

class CVExtractorAgent:
    """Agent to extract structured data from PDF resumes"""
    
    def __init__(self, resumes_dir: str = "resumes"):
        """Initialize CV Extractor Agent
        
        Args:
            resumes_dir: Directory containing resume PDFs
        """
        self.resumes_dir = resumes_dir
    
    def get_resume_files(self) -> List[str]:
        """Get list of PDF files in the resumes directory
        
        Returns:
            List of PDF filenames
        """
        resume_files = []
        try:
            for file in os.listdir(self.resumes_dir):
                if file.lower().endswith('.pdf'):
                    resume_files.append(file)
        except Exception as e:
            print(f"Error listing resume files: {str(e)}")
        
        return resume_files
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text content from PDF
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Extracted text from the PDF
        """
        text = ""
        try:
            doc = fitz.open(pdf_path)
            for page in doc:
                text += page.get_text()
            if len(text.strip()) < MIN_TEXT_CHARS:
                text = self._ocr_fallback(doc, pdf_path, text)
            doc.close()
        except Exception as e:
            print(f"Error extracting text from PDF {pdf_path}: {str(e)}")
        
        return text

    def _ocr_fallback(self, doc, pdf_path: str, current_text: str) -> str:
        """Try OCR for image-only (scanned) PDFs; warn clearly if that isn't possible.

        OCR needs the Tesseract engine installed on the machine (PyMuPDF calls it).
        """
        try:
            ocr_text = ""
            for page in doc:
                textpage = page.get_textpage_ocr(full=True)
                ocr_text += page.get_text(textpage=textpage)
            if len(ocr_text.strip()) >= MIN_TEXT_CHARS:
                print(f"  (OCR used for {os.path.basename(pdf_path)})")
                return ocr_text
        except Exception:
            pass
        print(f"Warning: no extractable text in {os.path.basename(pdf_path)}. "
              f"It may be a scanned PDF; install Tesseract to enable OCR.")
        return current_text
    
    def parse_resume(self, resume_text: str) -> Dict[str, Any]:
        """Parse resume text into structured data
        
        Args:
            resume_text: Text content of the resume
            
        Returns:
            Dictionary with structured data extracted from resume
        """
        sections = self._split_sections(resume_text)
        name = self._extract_name(resume_text)
        
        # Extract email
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', resume_text)
        email = email_match.group(0) if email_match else ""
        
        # Extract phone number
        phone_pattern = r'(?:\+\d{1,3}[-.\s]?)?(?:\d{3}[-.\s]?)?\d{3}[-.\s]?\d{4}'
        phone_match = re.search(phone_pattern, resume_text)
        phone = phone_match.group(0) if phone_match else ""
        
        # Extract education
        education_section = sections.get('education') or self._extract_section(resume_text, 
            ['education', 'academic background', 'academic qualification'], 
            ['experience', 'skills', 'projects'])
        
        # Extract work experience
        experience_section = sections.get('experience') or self._extract_section(resume_text, 
            ['experience', 'work history', 'professional experience', 'employment'], 
            ['education', 'skills', 'projects', 'certification'])
        
        # Extract skills
        skills_section = sections.get('skills') or self._extract_section(resume_text, 
            ['skills', 'technical skills', 'core competencies'], 
            ['experience', 'education', 'projects', 'certification'])
        
        # Parse individual skills
        skills = self._extract_skills(skills_section)
        
        # Extract certifications
        cert_section = sections.get('certifications') or self._extract_section(resume_text, 
            ['certifications', 'certificates', 'professional certifications'], 
            ['experience', 'education', 'skills', 'projects'])
        
        # Parse individual certifications
        certifications = self._extract_certifications(cert_section)
        
        # Extract tech stack
        tech_stack = self._extract_tech_stack(resume_text, sections.get('tech_stack', ''))
        
        return {
            'name': name,
            'email': email,
            'phone': phone,
            'education': education_section,
            'work_experience': experience_section,
            'skills': ", ".join(skills) if skills else "",
            'certifications': ", ".join(certifications) if certifications else "",
            'tech_stack': ", ".join(tech_stack) if tech_stack else "",
            'raw_text': resume_text
        }
    
    def _extract_name(self, text: str) -> str:
        """Find the candidate's name.

        Prefers an explicit "Name: ..." line, then falls back to the first line that
        looks like a person's name (skipping titles such as "Candidate Resume").
        """
        explicit = re.search(r'(?im)^\s*name\s*:\s*(.+?)\s*$', text)
        if explicit:
            return explicit.group(1).strip()

        name_like = re.compile(r"^[A-Z][a-zA-Z'\-\.]+(?: [A-Z][a-zA-Z'\-\.]+)+$")
        for line in text.splitlines()[:10]:
            candidate = line.strip()
            if not candidate or candidate.lower() in _TITLE_LINES:
                continue
            if name_like.match(candidate):
                return candidate
        return "Unknown"

    def _split_sections(self, text: str) -> Dict[str, str]:
        """Split resume text into sections using whole-line headings."""
        sections: Dict[str, List[str]] = {}
        current = None
        for line in text.splitlines():
            heading = _HEADING_LOOKUP.get(line.strip().rstrip(':').strip().lower())
            if heading:
                current = heading
                sections.setdefault(current, [])
            elif current:
                sections[current].append(line)
        return {key: "\n".join(lines).strip() for key, lines in sections.items()}

    @staticmethod
    def _entry_labels(section: str) -> List[str]:
        """For entries like "Cybersecurity - Skilled in ...", return the labels
        ("Cybersecurity"). Returns [] when the section isn't written that way."""
        labels = []
        for line in section.splitlines():
            m = re.match(r'^\s*(?:[•*]\s*)?(.{2,80}?)\s+[-–—]\s+\S', line)
            if m:
                labels.append(m.group(1).strip())
        return labels

    def _extract_section(self, text: str, section_headers: List[str], next_section_headers: List[str]) -> str:
        """Extract text for a specific section from resume
        
        Args:
            text: Full resume text
            section_headers: Possible headers for the target section
            next_section_headers: Possible headers for the next sections
            
        Returns:
            Extracted section text
        """
        # Create regex patterns
        section_pattern = '|'.join([rf'(?:{header})' for header in section_headers])
        next_section_pattern = '|'.join([rf'(?:{header})' for header in next_section_headers])
        
        # Try to find section with various formatting
        for pattern in [
            rf'(?i)({section_pattern})[:\s]*\n+(.*?)(?:\n+(?:{next_section_pattern})[:\s]*|$)',
            rf'(?i)({section_pattern})[:\s]*(.*?)(?:(?:{next_section_pattern})[:\s]*|$)'
        ]:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                return match.group(2).strip()
        
        return ""
    
    def _extract_skills(self, skills_section: str) -> List[str]:
        """Extract individual skills from skills section
        
        Args:
            skills_section: Text from the skills section
            
        Returns:
            List of skills
        """
        if not skills_section:
            return []
        
        # "Label - description" entries: keep just the labels
        labels = self._entry_labels(skills_section)
        if labels:
            return labels

        # Try different patterns to extract skills
        # Look for lists (comma-separated, bullet points, etc.)
        skills = []
        
        # Try comma-separated list
        if ',' in skills_section:
            skills = [s.strip() for s in skills_section.split(',') if s.strip()]
        
        # Try bullet points or line-by-line
        if not skills:
            bullet_skills = re.findall(r'(?:•|\*|\-|\d+\.)\s*([^•\*\-\n]+)', skills_section)
            if bullet_skills:
                skills = [s.strip() for s in bullet_skills if s.strip()]
        
        # Try line by line if still no skills found
        if not skills:
            line_skills = [line.strip() for line in skills_section.split('\n') if line.strip()]
            skills = line_skills
        
        return skills
    
    def _extract_certifications(self, cert_section: str) -> List[str]:
        """Extract individual certifications from certification section
        
        Args:
            cert_section: Text from the certifications section
            
        Returns:
            List of certifications
        """
        if not cert_section:
            return []
        
        # "Label - description" entries: keep just the certification names
        labels = self._entry_labels(cert_section)
        if labels:
            return labels

        # Similar approach as skills extraction
        certs = []
        
        # Try comma-separated list
        if ',' in cert_section:
            certs = [c.strip() for c in cert_section.split(',') if c.strip()]
        
        # Try bullet points
        if not certs:
            bullet_certs = re.findall(r'(?:•|\*|\-|\d+\.)\s*([^•\*\-\n]+)', cert_section)
            if bullet_certs:
                certs = [c.strip() for c in bullet_certs if c.strip()]
        
        # Try line by line if still no certs found
        if not certs:
            line_certs = [line.strip() for line in cert_section.split('\n') if line.strip()]
            certs = line_certs
            
        return certs
    
    def _extract_tech_stack(self, text: str, tech_section: str = "") -> List[str]:
        """Extract tech stack from resume text

        Uses the resume's own "Tech Stack" section when present, and adds any
        technologies from the shared vocabulary found elsewhere in the text.
        
        Args:
            text: Full resume text
            tech_section: Text of the "Tech Stack" section, if the resume has one
            
        Returns:
            List of technologies
        """
        explicit = [item.strip() for item in re.split(r'[,\n]', tech_section) if item.strip()]
        found = list(explicit)
        for tech in extract_tech(text):
            # Skip vocabulary hits already covered by an explicit entry ("Azure" in "Azure DevOps")
            if not any(tech.lower() in item.lower() for item in explicit):
                found.append(tech)
        return found
    
    def process_resume(self, filename: str) -> Dict[str, Any]:
        """Process a single resume file
        
        Args:
            filename: Name of the resume PDF file
            
        Returns:
            Dictionary with structured data extracted from the resume
        """
        pdf_path = os.path.join(self.resumes_dir, filename)
        
        try:
            print(f"Processing resume: {filename}")
            text = self.extract_text_from_pdf(pdf_path)
            parsed_data = self.parse_resume(text)
            parsed_data['filename'] = filename
            return parsed_data
        except Exception as e:
            print(f"Error processing resume {filename}: {str(e)}")
            return {
                'filename': filename,
                'name': 'Error',
                'email': '',
                'phone': '',
                'education': '',
                'work_experience': '',
                'skills': '',
                'certifications': '',
                'tech_stack': '',
                'raw_text': ''
            }
    
    def process_all_resumes(self) -> List[Dict[str, Any]]:
        """Process all resume files in the directory
        
        Returns:
            List of dictionaries with parsed resume data
        """
        resume_files = self.get_resume_files()
        parsed_resumes = []
        
        for filename in resume_files:
            parsed_resume = self.process_resume(filename)
            parsed_resumes.append(parsed_resume)
        
        return parsed_resumes 