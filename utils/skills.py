"""Shared technology vocabulary and extraction helper.

Used by the CV extractor (tech stack) and the matcher (skill-overlap scoring)
so both agents agree on what counts as a technology.
"""
import re
from typing import List

TECH_KEYWORDS = [
    # Programming languages
    'Python', 'Java', 'JavaScript', 'C++', 'C#', 'Ruby', 'PHP', 'Go', 'Swift', 'Kotlin',
    'TypeScript', 'Scala', 'Rust', 'Perl', 'R', 'MATLAB',
    # Web technologies
    'HTML', 'CSS', 'React', 'Angular', 'Vue', 'Node.js', 'Express', 'Django', 'Flask',
    'Spring', 'Laravel', 'Ruby on Rails', 'jQuery', 'Bootstrap', 'Tailwind',
    # Databases
    'SQL', 'MySQL', 'PostgreSQL', 'MongoDB', 'Oracle', 'SQLite', 'Redis', 'Cassandra',
    'DynamoDB', 'Elasticsearch', 'Firebase',
    # Cloud platforms
    'AWS', 'Azure', 'GCP', 'Google Cloud', 'Heroku', 'Netlify', 'Vercel',
    # DevOps
    'Docker', 'Kubernetes', 'Jenkins', 'Git', 'GitHub', 'GitLab', 'Terraform', 'Ansible',
    'CI/CD', 'Continuous Integration', 'Continuous Deployment',
    # AI/ML
    'TensorFlow', 'PyTorch', 'Keras', 'scikit-learn', 'Pandas', 'NumPy', 'SciPy',
    'Machine Learning', 'Deep Learning', 'NLP', 'Computer Vision',
]

# Very short names are also ordinary words/letters, so match them case-sensitively
# ("go" in "go-to-market" is not the Go language).
_CASE_SENSITIVE = {'Go', 'R'}


def _build_pattern(keyword: str) -> str:
    body = re.escape(keyword)
    if keyword in _CASE_SENSITIVE:
        body = f'(?-i:{body})'
    # Lookarounds instead of \b so names ending in symbols (C++, C#) still match.
    return rf'(?<![\w+#.]){body}(?![\w+#])'


_PATTERNS = {kw: re.compile(_build_pattern(kw), re.IGNORECASE) for kw in TECH_KEYWORDS}


def extract_tech(text: str) -> List[str]:
    """Return the canonical technology names found in ``text`` (sorted, deduplicated)."""
    if not text:
        return []
    return sorted(kw for kw, pattern in _PATTERNS.items() if pattern.search(text))
