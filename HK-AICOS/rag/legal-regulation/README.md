# HK-AICOS Legal Regulation RAG
## 香港工程法規 RAG 知識庫

---

## Overview

This directory contains Hong Kong government regulations and legal documents for construction projects.

**Purpose:** Provide AI Agents with official Hong Kong construction regulations and legal references.

**Phase:** Phase 1.5 - Folder structure and documentation framework

**Status:** Folder structure created, documents to be downloaded in Phase 1.5 Part 2 & 3

---

## Directory Structure

```
legal-regulation/
├── README.md                    ← This file
├── EMSD/                        ← Electrical and Mechanical Services Department
├── BD/                          ← Buildings Department
├── EPD/                         ← Environmental Protection Department
├── Labour/                      ← Labour Department
├── FSD/                         ← Fire Services Department
├── WSD/                         ← Water Supplies Department
├── LandsD/                      ← Lands Department
├── HyD/                         ← Highways Department
├── CEDD/                        ← Civil Engineering and Development Department
├── DSD/                         ← Drainage Services Department
├── TD/                          ← Transport Department
└── Legal/                       ← General Legal and Contract Compliance
```

---

## Department Overview

| Department | Abbreviation | Priority | Key Regulations |
|-----------|--------------|----------|-----------------|
| Labour Department | Labour | ⭐⭐⭐ | Occupational Safety, Construction Site Safety |
| Electrical and Mechanical Services Department | EMSD | ⭐⭐⭐ | Electricity, Gas, Lifts |
| Buildings Department | BD | ⭐⭐⭐ | Building Control, Structural Safety |
| Highways Department | HyD | ⭐⭐⭐ | Road Opening, Excavation Permit |
| Fire Services Department | FSD | ⭐⭐ | Fire Safety, Dangerous Goods |
| Civil Engineering and Development Department | CEDD | ⭐⭐ | Geotechnical, Slope Safety |
| Drainage Services Department | DSD | ⭐⭐ | Drainage, Sewerage |
| Transport Department | TD | ⭐⭐ | Traffic Management |
| Environmental Protection Department | EPD | ⭐⭐ | Environmental Protection, Noise Control |
| Water Supplies Department | WSD | ⭐ | Water Supply, Plumbing |
| Lands Department | LandsD | ⭐ | Land Administration |
| Legal Layer | Legal | ⭐⭐⭐ | Contract Law, Dispute Resolution |

---

## Document Classification

Each department folder contains:

### ordinance/
Hong Kong Ordinances and Regulations (法例)

### code-of-practice/
Official Codes of Practice (作業守則)

### practice-note/
Practice Notes and Technical Circulars (作業備考)

### guideline/
Technical Guidelines and Manuals (技術指引)

### forms/
Application Forms and Templates (表格)

### README.md
Department overview and document index

---

## Language Priority

**Priority 1:** English Version (Official technical version)
- Hong Kong construction industry primarily uses English technical documents
- Code of Practice are officially published in English
- Better for AI RAG technical analysis
- English versions are usually updated faster

**Priority 2:** Bilingual version (English + Chinese)

**Priority 3:** Chinese version (Reference only)

---

## Document Naming Convention

**Keep original official English filename.**

Examples:
- `Code_of_Practice_Electricity_Work.pdf`
- `PNAP_APP_151.pdf`
- `Excavation_Permit_Guideline.pdf`

**Do NOT translate filenames.**

---

## Applicable AI Agents

| Agent | Primary Departments |
|-------|-------------------|
| Engineering Agent | BD, EMSD, CEDD, HyD, DSD |
| Safety Agent | Labour, FSD, EMSD, BD |
| Material Agent | EMSD, WSD, BD |
| QS Agent | BD, Legal |
| PM Agent | All departments |
| Legal Agent | Legal, Labour, BD, all high-risk matters |
| Foreman Agent | Labour, EPD, HyD |
| Surveying Agent | LandsD, CEDD, BD |

---

## Phase 1.5 Progress

### Part 1: Folder Structure ✅
- [x] Create legal-regulation/ directory
- [x] Create 12 department subdirectories
- [x] Create 5 classification folders per department
- [x] Create README.md for each department

### Part 2: Download Tracker (Next)
- [ ] Create RAG_DOWNLOAD_TRACKER.md
- [ ] List all priority documents
- [ ] Record official sources and links

### Part 3: Document Research (Next)
- [ ] Search official Hong Kong government websites
- [ ] Identify priority documents
- [ ] Record document metadata
- [ ] Await user confirmation before download

---

## Important Notes

⚠️ **Only download from official Hong Kong government websites**

⚠️ **Verify document version and effective date**

⚠️ **Check for superseded documents**

⚠️ **English version preferred for technical documents**

⚠️ **All AI recommendations must be verified by qualified Hong Kong professionals**

---

## Next Steps

1. Complete Phase 1.5 Part 2: Create RAG_DOWNLOAD_TRACKER.md
2. Complete Phase 1.5 Part 3: Research and list official documents
3. Await user confirmation
4. Download approved documents
5. Organize documents into appropriate folders
6. Update README.md with downloaded document list

---

## Version Control

- Created: 2026-05-13
- Phase: 1.5 Part 1
- Status: Folder structure completed
- Documents Downloaded: 0
- Next: Part 2 - Download Tracker

---

## Risk Reminder

⚠️ **AI cannot replace qualified professionals**

⚠️ **All legal, structural, electrical, fire safety, and other technical matters must be verified by registered professionals in Hong Kong**

⚠️ **This RAG system provides reference only, not professional advice**
