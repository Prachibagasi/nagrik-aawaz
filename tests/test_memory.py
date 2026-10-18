import threading

from db.memory import MemoryDB


def count(db, table):
    cur = db.get_cursor()
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    return cur.fetchone()[0]


def test_rerunning_does_not_duplicate_rows(tmp_path):
    db = MemoryDB(str(tmp_path / "t.db"))
    for _ in range(3):
        jd_id = db.insert_jd_summary("Dev", {"required_skills": ["Python"], "raw_jd": "x"})
        cv_id = db.insert_cv_data("a.pdf", {"name": "A", "email": "a@x.com"})
        match_id = db.insert_match_score(jd_id, cv_id, 77.0)
        db.insert_shortlisted(match_id, jd_id, cv_id, 77.0)
    assert [count(db, t) for t in ("jd_summaries", "cv_data", "match_scores", "shortlist")] == [1, 1, 1, 1]
    db.close()


def test_upsert_updates_values_and_keeps_ids_stable(tmp_path):
    db = MemoryDB(str(tmp_path / "t.db"))
    cv1 = db.insert_cv_data("a.pdf", {"name": "Old Name"})
    cv2 = db.insert_cv_data("a.pdf", {"name": "New Name"})
    assert cv1 == cv2
    assert db.get_cv_data(cv1)["name"] == "New Name"
    jd = db.insert_jd_summary("Dev", {})
    m1 = db.insert_match_score(jd, cv1, 60.0)
    m2 = db.insert_match_score(jd, cv1, 85.0)
    assert m1 == m2
    cur = db.get_cursor()
    cur.execute("SELECT score FROM match_scores WHERE id = ?", (m1,))
    assert cur.fetchone()[0] == 85.0
    db.close()


def test_reshortlisting_preserves_email_sent_status(tmp_path):
    db = MemoryDB(str(tmp_path / "t.db"))
    jd = db.insert_jd_summary("Dev", {})
    cv = db.insert_cv_data("a.pdf", {"name": "A"})
    match = db.insert_match_score(jd, cv, 90.0)
    sl = db.insert_shortlisted(match, jd, cv, 90.0)
    db.update_email_sent(sl, "2026-01-01T00:00:00")
    assert db.insert_shortlisted(match, jd, cv, 91.0) == sl
    cur = db.get_cursor()
    cur.execute("SELECT email_sent, score FROM shortlist WHERE id = ?", (sl,))
    row = cur.fetchone()
    assert row["email_sent"] == 1 and row["score"] == 91.0
    db.close()


def test_threads_can_write_concurrently(tmp_path):
    path = str(tmp_path / "t.db")
    MemoryDB(path).close()
    errors = []

    def worker(n):
        try:
            db = MemoryDB(path)
            db.insert_jd_summary(f"Job {n}", {"required_skills": [f"Skill-{n}"]})
            db.close()
        except Exception as e:  # pragma: no cover
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert not errors
    db = MemoryDB(path)
    assert count(db, "jd_summaries") == 5
    db.close()
