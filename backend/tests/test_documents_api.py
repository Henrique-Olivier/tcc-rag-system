import pytest

from app.db.models import Document

pytestmark = pytest.mark.integration


def _pdf(tag: str) -> tuple[str, bytes, str]:
    return (f"{tag}.pdf", b"%PDF-1.4\n" + tag.encode(), "application/pdf")


def _upload(client, *files):
    response = client.post("/documents", files=[("files", f) for f in files])
    assert response.status_code == 200
    return response.json()


def test_multiple_upload_returns_result_per_file(client):
    results = _upload(client, _pdf("a"), _pdf("b"), ("nota.txt", b"texto", "text/plain"))

    assert [(r["filename"], r["outcome"]) for r in results] == [("a.pdf", "new"), ("b.pdf", "new"), ("nota.txt", "rejected")]
    assert results[2]["message"] == "o arquivo não é um PDF"


def test_queue_position_counts_only_active_pending_created_before(client, db_session):
    ids = [r["document_id"] for r in _upload(client, _pdf("1"), _pdf("2"), _pdf("3"), _pdf("4"))]
    db_session.get(Document, ids[0]).status = "processing"
    db_session.commit()
    client.delete(f"/documents/{ids[1]}")

    positions = {d["id"]: d["queue_position"] for d in client.get("/documents").json()}
    assert positions == {ids[0]: None, ids[2]: 1, ids[3]: 2}
    assert client.get(f"/documents/{ids[3]}").json()["queue_position"] == 2


def test_file_is_served_only_for_active_documents(client):
    [result] = _upload(client, _pdf("artigo"))
    doc_id = result["document_id"]

    response = client.get(f"/documents/{doc_id}/file")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content == _pdf("artigo")[1]

    assert client.delete(f"/documents/{doc_id}").status_code == 204
    assert client.get("/documents").json() == []
    assert client.get(f"/documents/{doc_id}").status_code == 404
    assert client.get(f"/documents/{doc_id}/file").status_code == 404
    assert client.delete(f"/documents/{doc_id}").status_code == 404


def test_reupload_after_removal_reactivates(client):
    [first] = _upload(client, _pdf("volta"))
    client.delete(f"/documents/{first['document_id']}")

    [again] = _upload(client, _pdf("volta"))

    assert (again["outcome"], again["document_id"]) == ("reactivated", first["document_id"])
    assert [d["id"] for d in client.get("/documents").json()] == [first["document_id"]]
