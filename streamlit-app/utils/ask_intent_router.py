"""Deterministic intent routing for Ask AICOS context selection."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


INTENT_LABELS = {
    "recent_image_question": "最近相片跟進",
    "project_memory_question": "工程記憶查詢",
    "followup_question": "跟進事項查詢",
    "safety_definition_question": "安全定義 / 知識查詢",
    "legal_source_question": "法例 / 官方來源查詢",
    "sop_howto_question": "SOP / 操作流程查詢",
    "general_safety_question": "一般安全查詢",
    "unknown": "一般查詢",
}

_IMAGE_TERMS = ("這張相", "呢張相", "張相", "相片", "圖片", "剛才相", "頭先相")
_RECENT_UPLOAD_TERMS = ("剛才上載", "頭先上載", "剛才分析", "頭先分析")
_RECENT_TERMS = ("剛才", "頭先", "這張", "呢張", "上載")
_IMAGE_EVIDENCE_TERMS = ("磨機", "火花", "切割", "相", "圖片")
_UNSAFE_BEHAVIOUR_TERMS = ("有冇不安全行為", "有沒有不安全行為", "不安全行為")
_DEFINITION_MARKERS = ("定義", "乜嘢係", "咩係", "什麼是", "甚麼是", "點定義", "有咩要求", "有什麼要求")
_SAFETY_TOPICS = (
    "高空工作", "高處工作", "離地工作", "熱工", "熱工序", "hot work", "火花", "明火",
    "電焊", "氣焊", "焊接", "燒焊", "切割", "打磨", "磨機", "砂輪機", "熱工許可",
    "防火監察", "防火氈", "滅火筒", "工後巡查", "密閉空間", "竹棚", "棚架",
    "臨邊", "洞口", "防墮", "working at height", "hot work", "confined space",
)
_LEGAL_TERMS = ("法例", "條例", "守則", "官方", "勞工處", "章節", "第幾條", "來源")
_SOP_TERMS = ("點做", "怎樣做", "如何做", "要做咩", "要做什麼", "做咩", "要準備", "流程", "許可", "檢查", "表格", "跟程序")
_FOLLOWUP_TERMS = ("跟進", "未完成", "要處理", "邊個負責", "誰負責", "close out", "整改")
_MEMORY_TERMS = ("之前", "上次", "最近", "這個工程", "呢個工程", "有冇重複", "有沒有重複", "記錄")
_GENERAL_SAFETY_TERMS = ("安全", "風險", "危險", "防護", "ppe", "墮下", "火警", *_SAFETY_TOPICS)


@dataclass(frozen=True)
class AskIntent:
    intent_type: str
    label: str
    matched_keywords: list[str] = field(default_factory=list)
    use_recent_upload: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def classify_ask_intent(question: str, has_recent_upload: bool = False) -> AskIntent:
    """Classify one question without an LLM or external service."""
    text = " ".join(str(question or "").lower().split())
    image_hits = _hits(text, _IMAGE_TERMS)
    recent_upload_hits = _hits(text, _RECENT_UPLOAD_TERMS)
    recent_hits = _hits(text, _RECENT_TERMS)
    evidence_hits = _hits(text, _IMAGE_EVIDENCE_TERMS)
    unsafe_hits = _hits(text, _UNSAFE_BEHAVIOUR_TERMS)
    if image_hits or recent_upload_hits or (recent_hits and evidence_hits) or (unsafe_hits and has_recent_upload):
        return _intent("recent_image_question", [*image_hits, *recent_upload_hits, *recent_hits, *evidence_hits, *unsafe_hits], True)

    legal_hits = _hits(text, _LEGAL_TERMS)
    if legal_hits:
        return _intent("legal_source_question", legal_hits)

    topic_hits = _hits(text, _SAFETY_TOPICS)
    definition_hits = _hits(text, _DEFINITION_MARKERS)
    if definition_hits and topic_hits:
        return _intent("safety_definition_question", [*definition_hits, *topic_hits])

    sop_hits = _hits(text, _SOP_TERMS)
    if sop_hits:
        return _intent("sop_howto_question", [*sop_hits, *topic_hits])

    followup_hits = _hits(text, _FOLLOWUP_TERMS)
    if followup_hits:
        return _intent("followup_question", [*followup_hits, *recent_hits], bool(recent_hits))

    memory_hits = _hits(text, _MEMORY_TERMS)
    if memory_hits:
        return _intent("project_memory_question", memory_hits)

    safety_hits = _hits(text, _GENERAL_SAFETY_TERMS)
    if safety_hits:
        return _intent("general_safety_question", safety_hits)
    return _intent("unknown", [])


def _intent(intent_type: str, keywords: list[str], use_recent_upload: bool = False) -> AskIntent:
    return AskIntent(
        intent_type=intent_type,
        label=INTENT_LABELS[intent_type],
        matched_keywords=list(dict.fromkeys(item for item in keywords if item))[:12],
        use_recent_upload=use_recent_upload,
    )


def _hits(text: str, terms) -> list[str]:
    return [term for term in terms if term in text]
