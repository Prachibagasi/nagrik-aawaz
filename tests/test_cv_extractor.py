import collections
import io
import contextlib

import pytest

from agents.cv_extractor import CVExtractorAgent

SAMPLE = """Candidate Resume (ID: C9999)
Name: Jane Doe
Email: jane.doe@example.com
Phone: +1-555-1234
Education
BSc in Computer Science (2018-2022)
Work Experience
Backend Engineer at Acme (2022-2024)
Built APIs.
Skills
Python & APIs - Proficient in FastAPI, Flask and Django with hands-on
experience in building services.
Certifications
AWS Certified Developer - Validated cloud skills.
Tech Stack
Python, FastAPI, PostgreSQL
"""


@pytest.fixture
def agent(resumes_dir):
    return CVExtractorAgent(str(resumes_dir))


def test_name_comes_from_name_line_not_the_title(agent):
    cv = agent.parse_resume(SAMPLE)
    assert cv["name"] == "Jane Doe"
    assert cv["email"] == "jane.doe@example.com"
    assert cv["phone"] == "+1-555-1234"


def test_wrapped_line_starting_with_experience_does_not_truncate_skills(agent):
    """Regression: the old regex treated the wrapped word 'experience' as a new section."""
    cv = agent.parse_resume(SAMPLE)
    assert cv["skills"] == "Python & APIs"
    assert "Built APIs." in cv["work_experience"]
    assert "Python & APIs" not in cv["work_experience"]


def test_certifications_are_names_not_descriptions(agent):
    assert agent.parse_resume(SAMPLE)["certifications"] == "AWS Certified Developer"


def test_tech_stack_uses_explicit_section(agent):
    stack = agent.parse_resume(SAMPLE)["tech_stack"].split(", ")
    assert stack[:3] == ["Python", "FastAPI", "PostgreSQL"]


def test_name_falls_back_to_first_name_like_line(agent):
    cv = agent.parse_resume("Priya Sharma\npriya@example.com\n\nSkills\nPython, SQL\n")
    assert cv["name"] == "Priya Sharma"
    assert cv["skills"] == "Python, SQL"


def test_unparseable_name_is_unknown_not_a_title(agent):
    assert agent.parse_resume("Candidate Resume\n12345\n")["name"] == "Unknown"


def test_go_is_not_matched_inside_ordinary_words(agent):
    cv = agent.parse_resume("Jane Doe\nSkills\nI will go to the market and organise.\n")
    assert "Go" not in cv["tech_stack"].split(", ")


def test_all_bundled_resumes_parse_with_real_names(agent):
    with contextlib.redirect_stdout(io.StringIO()):
        cvs = agent.process_all_resumes()
    assert len(cvs) == 200
    names = [cv["name"] for cv in cvs]
    assert "Candidate Resume" not in names and "Unknown" not in names
    assert len(set(names)) > 150                       # real, mostly distinct people
    assert all("@" in cv["email"] for cv in cvs)
    assert all(cv["skills"] and cv["work_experience"] and cv["education"] for cv in cvs)


def test_scanned_pdf_warns_instead_of_crashing(tmp_path, capsys):
    import fitz_compat
    path = tmp_path / "scan.pdf"
    fitz_compat.blank_pdf(path)
    text = CVExtractorAgent(str(tmp_path)).extract_text_from_pdf(str(path))
    assert text.strip() == ""
    assert "no extractable text" in capsys.readouterr().out.lower()
