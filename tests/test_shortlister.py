from agents.shortlister import ShortlisterAgent


def cv(name, filename=None):
    return {"name": name, "filename": filename or f"{name}.pdf", "email": f"{name}@x.com", "phone": ""}


def test_threshold_is_inclusive():
    matches = {"Dev": [(cv("a"), 80.0), (cv("b"), 79.99)]}
    result = ShortlisterAgent(threshold=80.0).shortlist_candidates(matches)
    assert [c["name"] for c, _ in result["Dev"]] == ["a"]


def test_jobs_without_candidates_are_omitted():
    matches = {"Dev": [(cv("a"), 50.0)], "QA": [(cv("b"), 90.0)]}
    result = ShortlisterAgent(threshold=80.0).shortlist_candidates(matches)
    assert list(result) == ["QA"]


def test_top_n_keeps_best_scores_per_job():
    matches = {"Dev": [(cv("a"), 85.0), (cv("b"), 95.0), (cv("c"), 90.0)]}
    result = ShortlisterAgent(threshold=80.0, top_n=2).shortlist_candidates(matches)
    assert [c["name"] for c, _ in result["Dev"]] == ["b", "c"]


def test_top_n_never_lets_below_threshold_candidates_in():
    matches = {"Dev": [(cv("a"), 70.0), (cv("b"), 60.0)]}
    assert ShortlisterAgent(threshold=80.0, top_n=5).shortlist_candidates(matches) == {}


def test_shortlist_data_shape():
    shortlisted = {"Dev": [(cv("a", "a.pdf"), 91.5)]}
    data = ShortlisterAgent().get_shortlist_data(shortlisted)
    assert data == [{"job_title": "Dev", "cv_filename": "a.pdf", "name": "a",
                     "email": "a@x.com", "phone": "", "score": 91.5}]
