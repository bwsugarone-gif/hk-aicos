"""Test script to generate a sample PDF report."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from utils.report_generator import generate_pdf_report, save_report

analysis = """## 工程分析

根據相片分析，工地現場存在以下安全問題：

- 工人未有佩戴安全帽，違反工地安全規定
- 現場地面有散亂物料，存在絆倒風險
- 高空作業區域未見安全網或防墮設施

## 安全風險分析

- 未佩戴個人防護裝備 (PPE) 屬嚴重安全違規
- 地面雜亂可能導致工人絆倒受傷
- 高空墮物風險需即時處理

## 法規與合規提醒

- 根據《工廠及工業經營條例》，僱主須確保工人佩戴適當 PPE
- 違反安全規定可能導致工地被勒令停工
- 安全主任須即時記錄及跟進

## 建議跟進事項

- 即時要求所有工人佩戴安全帽及安全靴
- 清理地面散亂物料，保持通道暢通
- 安裝安全網及防墮設施後方可繼續高空作業
- 安全主任須進行工地安全巡查並記錄

## 需要人工確認事項

- 安全主任須親身到場評估現場風險
- 如有工傷事故，須按《僱員補償條例》申報
"""

pdf = generate_pdf_report(
    analysis_type="工地安全分析",
    question="呢張相有無不安全行為？",
    risk_level="中風險",
    analysis_result=analysis,
    filename_hint="site_photo_001.jpg",
    professionals_required=["註冊安全主任 (RSO)", "項目經理"],
    project_ref="TEST-2026",
)
path = save_report(pdf, "TEST-MOBILE-20260514")
print("PDF generated:", path)
print("Size:", len(pdf), "bytes")
print("OK")
