from papermatrix.domain.question_migrations import migrate_questions


def test_migrates_v1_question_evidence_without_source_item_id() -> None:
    source = {
        "schema_version": 1,
        "questions": [
            {
                "question": "What supports the result?",
                "evidence": [
                    {
                        "evidence_id": "11111111-1111-4111-8111-111111111111",
                        "source_item_id": "legacy-item-id",
                    }
                ],
            }
        ],
    }

    migrated = migrate_questions(source)

    assert source["schema_version"] == 1
    assert migrated["schema_version"] == 2
    assert "source_item_id" not in migrated["questions"][0]["evidence"][0]
