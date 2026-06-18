"""Generate practical, structured site follow-up actions."""

from __future__ import annotations

from .analysis_models import FollowUpSuggestion, ImageCategory
from .image_classifier import normalize_image_category


def generate_followups(
    category: ImageCategory | str,
    observations: list[str] | None = None,
    risks: list[str] | None = None,
) -> list[FollowUpSuggestion]:
    category = normalize_image_category(category)
    observations = observations or []
    risks = risks or []
    reason = (risks or observations or ["需要確認圖片內容及現場狀況"])[0]

    hot_work_followups = [
        FollowUpSuggestion("核實熱工許可", "確認工序是否需要熱工許可證，並在開工前完成審批。", "high", "管工／安全主任／許可證簽發人", "開工前", reason),
        FollowUpSuggestion("清理及遮蓋可燃物", "清走或以防火物料遮蓋附近可燃物，並保護門框、牆身及已完成飾面。", "high", "管工／分判商", "開工前", "火花可能引燃物料或損壞完成面。"),
        FollowUpSuggestion("配置防火設備", "放置合適滅火筒及防火氈，按需要安排防火監察及工後巡查。", "high", "安全主任／防火監察人", "施工期間及完工後", "熱工需要可即時使用的滅火及監察安排。"),
        FollowUpSuggestion("覆核 PPE 及工具", "確認眼罩或面罩、手套、長袖及適合該工具的 PPE，並檢查護罩及電線。", "high", "管工／安全主任", "開工前", "火花、碎屑及工具反彈可能造成眼面及割傷風險。"),
        FollowUpSuggestion("保存跟進證據", "拍攝整改、防火措施及工後狀況照片作記錄。", "medium", "管工／地盤記錄人員", "同日內", "保留措施及完成狀況的可核實記錄。"),
    ]

    templates: dict[ImageCategory, list[FollowUpSuggestion]] = {
        ImageCategory.HOT_WORK: hot_work_followups,
        ImageCategory.CUTTING_GRINDING: hot_work_followups,
        ImageCategory.FIRE_RISK: hot_work_followups,
        ImageCategory.PPE_ISSUE: [
            FollowUpSuggestion("覆核個人防護裝備", "按實際工序確認眼、面、手部、聽覺及身體防護要求。", "high", "管工／安全主任", "開工前", reason),
            FollowUpSuggestion("記錄 PPE 覆核", "拍攝已確認的 PPE 及工具防護裝置，未能從相片確認的項目須現場核實。", "medium", "管工", "同日內", "相片只可證明清晰可見的裝備。"),
        ],
        ImageCategory.SAFETY_ISSUE: [
            FollowUpSuggestion("即時安全隔離", "停止受影響範圍工作、設置圍封及通知安全主任。", "urgent", "安全主任／地盤主管", "立即", reason),
            FollowUpSuggestion("現場復核及記錄", "由合資格人員到場核實，拍攝整改前後照片並更新風險評估。", "high", "安全主任", "同日內", "安全事項須由現場人員確認，不可只依賴圖片判斷。"),
        ],
        ImageCategory.CONSTRUCTION_DEFECT: [
            FollowUpSuggestion("缺陷檢查", "標記缺陷位置、量度範圍，並與圖則及規格核對。", "high", "地盤工程師／品質主任", "24 小時內", reason),
            FollowUpSuggestion("制定修補方案", "確認成因及修補方法，未獲批准前避免遮蓋或進行後續工序。", "medium", "項目經理／分判商", "下一工序前", "避免缺陷被後續工序遮蓋。"),
        ],
        ImageCategory.MATERIAL_DELIVERY: [
            FollowUpSuggestion("核對送貨資料", "核對送貨單、規格、數量、批次及認可材料清單。", "medium", "物料主管／品質主任", "收貨當日", reason),
            FollowUpSuggestion("隔離不合格材料", "如包裝、標籤或狀況有異常，先隔離並提出材料檢查。", "high", "物料主管", "使用前", "防止未驗收材料投入施工。"),
        ],
        ImageCategory.ATTENDANCE_OR_TIMESHEET: [
            FollowUpSuggestion("核對工時記錄", "核對日期、人員、工種、出入記錄及主管簽認。", "medium", "地盤文員／管工", "下一個工作天", reason),
        ],
        ImageCategory.HANDWRITTEN_RECORD: [
            FollowUpSuggestion("人工覆核手寫內容", "由記錄提交人確認日期、位置、姓名及未清事項。", "medium", "地盤文員／記錄提交人", "24 小時內", "手寫 OCR 容易出現誤讀。"),
        ],
        ImageCategory.GENERAL_SITE_PHOTO: [
            FollowUpSuggestion("補充現場資料", "加入拍攝日期、位置、工序及需要跟進的重點。", "low", "拍攝者／地盤主管", "方便時", reason),
        ],
        ImageCategory.UNKNOWN: [
            FollowUpSuggestion("人工分類", "確認圖片類型及跟進目的，必要時重新拍攝較清晰照片。", "low", "地盤主管", "方便時", reason),
        ],
    }
    return templates[category]
