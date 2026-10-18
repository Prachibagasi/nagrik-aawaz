import pytest

from agents.matcher import MatcherAgent

JD = {"title": "Backend Developer",
      "summary": {"required_skills": ["Python", "SQL"], "education": "BSc",
                  "years_of_experience": "2 years", "certifications": [],
                  "responsibilities": ["Build APIs"],
                  "raw_jd": "We need Python and SQL and Docker experience."}}
GOOD_CV = {"name": "Good", "skills": "Python, SQL", "tech_stack": "Python, SQL, Docker",
           "work_experience": "Built Python APIs", "education": "BSc"}
WEAK_CV = {"name": "Weak", "skills": "Photoshop", "tech_stack": "", "work_experience": "Designed logos",
           "education": "BA"}


def test_relevant_cv_outscores_irrelevant_cv(embedder):
    m = MatcherAgent(embedding_util=embedder)
    assert m.calculate_match_score(JD, GOOD_CV) > m.calculate_match_score(JD, WEAK_CV)


def test_matches_are_sorted_best_first(embedder):
    m = MatcherAgent(embedding_util=embedder)
    result = m.match_jd_with_all_cvs(JD, [WEAK_CV, GOOD_CV])
    assert [cv["name"] for cv, _ in result] == ["Good", "Weak"]


def test_tech_overlap_score():
    assert MatcherAgent.tech_overlap_score(JD, GOOD_CV) == pytest.approx(100.0)
    # JD names Python, SQL, Docker -> weak CV has none of them
    assert MatcherAgent.tech_overlap_score(JD, WEAK_CV) == 0.0


def test_tech_overlap_is_none_when_jd_names_no_technologies():
    jd = {"title": "Designer", "summary": {"raw_jd": "Make things beautiful."}}
    assert MatcherAgent.tech_overlap_score(jd, GOOD_CV) is None


def test_skill_weight_zero_is_pure_embedding_score(embedder):
    pure = MatcherAgent(embedding_util=embedder).calculate_match_score(JD, WEAK_CV)
    zero = MatcherAgent(embedding_util=embedder, skill_weight=0.0).calculate_match_score(JD, WEAK_CV)
    assert pure == zero


def test_skill_weight_blends_scores(embedder):
    base = MatcherAgent(embedding_util=embedder).calculate_match_score(JD, WEAK_CV)
    blended = MatcherAgent(embedding_util=embedder, skill_weight=0.5).calculate_match_score(JD, WEAK_CV)
    assert blended == pytest.approx(0.5 * base + 0.5 * 0.0)


def test_invalid_skill_weight_rejected(embedder):
    with pytest.raises(ValueError):
        MatcherAgent(embedding_util=embedder, skill_weight=1.5)


def test_all_jds_by_all_cvs_embeds_each_text_once(fake_ollama):
    from utils.embeddings import EmbeddingUtil
    m = MatcherAgent(embedding_util=EmbeddingUtil(cache_path=""))
    jds = [dict(JD, title=f"Job {i}", summary=dict(JD["summary"], responsibilities=[f"task {i}"])) for i in range(3)]
    cvs = [dict(GOOD_CV, name=f"cv{i}", work_experience=f"exp {i}") for i in range(4)]
    m.match_all_jds_with_all_cvs(jds, cvs)
    assert len(fake_ollama) == 3 + 4      # not 3 * 4 * 2
