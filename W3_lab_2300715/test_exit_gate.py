import json
from dataclasses import dataclass
from typing import Any, Optional
from agent import (
    INSPECTION_TOOLS,
    check_condition,
    get_metadata,
    list_available_items,
    run_agent,
)


@dataclass
class MockFunction:
    name: str
    arguments: str


@dataclass
class MockToolCall:
    id: str
    function: MockFunction


@dataclass
class MockMessage:
    content: Optional[str] = None
    tool_calls: Optional[list[MockToolCall]] = None


def scripted_llm(turns: list[MockMessage]):
    iterator = iter(turns)

    def _call(_messages: list[dict[str, Any]]) -> MockMessage:
        return next(iterator)

    return _call


# 1. اختبار المسار السليم: فحص الموديل ثم اقتراح عملية SysML صحيحة واعتمادها
def test_successful_inspection_and_typed_operation():
    llm = scripted_llm([
        MockMessage(tool_calls=[
            MockToolCall("call_1", MockFunction("get_metadata", json.dumps({"item_name": "BatteryPack"})))
        ]),
        MockMessage(tool_calls=[
            MockToolCall("call_2", MockFunction("propose_typed_operation", json.dumps({
                "operation": "add_attribute",
                "target_element": "BatteryPack",
                "member_name": "nominalVoltage",
                "sysml_type": "Real",
            })))
        ]),
        MockMessage(content="Added nominalVoltage : Real to BatteryPack after validation."),
    ])

    result = run_agent("Add nominalVoltage to BatteryPack", llm_fn=llm)
    assert result["status"] == "SUCCESS"
    assert result["evidence_count"] == 1
    assert "attribute nominalVoltage : Real;" in result["validated_sysml"]


# 2. اختبار Exit Gate: أداة وهمية (Fabricated Tool Name) لا يمكن أن تنجح بصمت
def test_fabricated_tool_name_rejected():
    llm = scripted_llm([
        MockMessage(tool_calls=[
            MockToolCall("call_1", MockFunction("delete_entire_model", json.dumps({"force": True})))
        ]),
        MockMessage(content="Model deleted successfully!"),
    ])

    result = run_agent("Delete the model", llm_fn=llm)
    assert result["status"] != "SUCCESS"
    assert result["error_code"] == "FABRICATED_TOOL"
    assert result["trace"][0]["result"]["error_code"] == "FABRICATED_TOOL"


# 3. اختبار Exit Gate: مدخلات غير صالحة (Invalid Arguments) تُرفض بأمان بدون Crash
def test_invalid_arguments_handled_safely():
    # اختبار مباشر على الدوال
    assert list_available_items(kind_filter="invalid_kind")["error_code"] == "INVALID_ARGUMENT"
    assert get_metadata(12345)["error_code"] == "INVALID_ARGUMENT"  # type: ignore[arg-type]
    assert check_condition("BatteryPack", "INVALID_STATUS")["error_code"] == "INVALID_ARGUMENT"

    # اختبار داخل دورة الـ Agent مع JSON تالف ومعاملات ناقصة
    llm = scripted_llm([
        MockMessage(tool_calls=[
            MockToolCall("call_1", MockFunction("get_metadata", "{not-valid-json")),
            MockToolCall("call_2", MockFunction("get_metadata", json.dumps({"wrong_param": "BatteryPack"}))),
        ]),
        MockMessage(content="Everything looks valid."),
    ])

    result = run_agent("Inspect BatteryPack", llm_fn=llm)
    assert result["status"] == "NO_EVIDENCE"
    assert result["trace"][0]["result"]["error_code"] == "INVALID_ARGUMENT"
    assert result["trace"][1]["result"]["error_code"] == "INVALID_ARGUMENT"


# 4. اختبار Exit Gate: ادعاء بلا دليل (عنصر غير موجود في الموديل) يرجع NO_EVIDENCE
def test_unsupported_claim_returns_no_evidence():
    llm = scripted_llm([
        MockMessage(tool_calls=[
            MockToolCall("call_1", MockFunction("get_metadata", json.dumps({"item_name": "NuclearReactor"})))
        ]),
        MockMessage(content="NuclearReactor has 500 MW output."),
    ])

    result = run_agent("Inspect NuclearReactor", llm_fn=llm)
    assert result["status"] == "NO_EVIDENCE"
    assert result["evidence_count"] == 0


# 5. اختبار Exit Gate: فشل أداة أو رفض المدقق الهندسي لا يتحول أبداً لـ SUCCESS
def test_tool_failure_and_validator_rejection_cannot_succeed():
    # أ) محاكاة تعطل أداة (Runtime Exception)
    def broken_tool(item_name: str) -> dict[str, Any]:
        raise RuntimeError("Disk I/O timeout while reading SysML file")

    broken_registry = {**INSPECTION_TOOLS, "get_metadata": broken_tool}
    llm_tool_fail = scripted_llm([
        MockMessage(tool_calls=[
            MockToolCall("call_1", MockFunction("get_metadata", json.dumps({"item_name": "BatteryPack"})))
        ]),
        MockMessage(content="BatteryPack verified."),
    ])

    res_fail = run_agent("Check BatteryPack", llm_fn=llm_tool_fail, tool_registry=broken_registry)
    assert res_fail["status"] == "FAILED"
    assert res_fail["error_code"] == "TOOL_FAILURE"

    # ب) رفض المدقق الهندسي (مثلاً إضافة خاصية مكررة capacityKwh)
    llm_validator_reject = scripted_llm([
        MockMessage(tool_calls=[
            MockToolCall("call_1", MockFunction("get_metadata", json.dumps({"item_name": "BatteryPack"})))
        ]),
        MockMessage(tool_calls=[
            MockToolCall("call_2", MockFunction("propose_typed_operation", json.dumps({
                "operation": "add_attribute",
                "target_element": "BatteryPack",
                "member_name": "capacityKwh",  # موجودة مسبقاً!
                "sysml_type": "Real",
            })))
        ]),
        MockMessage(content="Added capacityKwh."),
    ])

    res_reject = run_agent("Add capacityKwh to BatteryPack", llm_fn=llm_validator_reject)
    assert res_reject["status"] == "REJECTED"
    assert res_reject["error_code"] == "VALIDATION_REJECTED"


# 6. اختبار حدود الاستدعاء (Call Limits)
def test_call_limit_enforced():
    llm_infinite = scripted_llm([
        MockMessage(tool_calls=[
            MockToolCall("c1", MockFunction("list_available_items", json.dumps({"kind_filter": "all"})))
        ]),
        MockMessage(tool_calls=[
            MockToolCall("c2", MockFunction("list_available_items", json.dumps({"kind_filter": "all"})))
        ]),
        MockMessage(tool_calls=[
            MockToolCall("c3", MockFunction("list_available_items", json.dumps({"kind_filter": "all"})))
        ]),
    ])

    result = run_agent("Loop forever", llm_fn=llm_infinite, max_calls=2)
    assert result["status"] == "FAILED"
    assert result["error_code"] == "MAX_CALLS_EXCEEDED"