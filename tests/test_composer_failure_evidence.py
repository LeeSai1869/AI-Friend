from section_1_central_mind.mind.composer import Composer


def test_composer_preserves_failure_receipt_and_user_facing_output():
    receipt = {
        "candidate_applied": False,
        "checks": {"harness_acceptance": ["test_answer.py"], "model_generated": []},
    }
    combined = Composer().combine([{
        "status": "error",
        "error": "functional tests failed after the repair budget",
        "output": "No candidate was applied. test_answer.py::test_answer failed.",
        "execution_receipt": receipt,
    }])

    assert combined["status"] == "error"
    assert combined["execution_receipt"] == receipt
    assert "No candidate was applied" in combined["output"]
