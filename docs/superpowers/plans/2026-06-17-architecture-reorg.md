# Project Architecture Reorg Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Consolidate the project into one main repository folder, absorb the external extraction and KG-alignment deliverables, and remove stale docs and duplicate root-level directories.

**Architecture:** Keep `kg_agent_app` as the only top-level project folder. Preserve runtime code under `src`, UI under `templates` and `static`, and data artifacts under `data/source`, `data/intermediate`, and `data/kg`. Move the reusable extraction scripts and reference files into the repo, then delete the external source folders and obsolete note files.

**Tech Stack:** Python, Flask, RDFLib, LangChain, LangGraph, Turtle/SPARQL, Git.

---

### Task 1: Consolidate external deliverables

**Files:**
- Move: `../关系抽取/*` -> `scripts/extraction/`, `data/intermediate/`, and `docs/extraction/`
- Move: `../知识图谱构建与外部对齐/*` -> `data/kg/` and `docs/kg_alignment/`

- [ ] **Step 1: Verify the destination folders exist**
- [ ] **Step 2: Move reusable scripts and reference files into the repo**
- [ ] **Step 3: Keep canonical data files inside `data/intermediate/` and `data/kg/`**
- [ ] **Step 4: Confirm the repo still has one source of truth for each artifact**

### Task 2: Remove stale root directories and unneeded docs

**Files:**
- Delete: `../agent/`
- Delete: `../关系抽取/`
- Delete: `../知识图谱构建与外部对齐/`
- Delete: `ALL_ROUTES_FIX.md`
- Delete: `FIX_NOTES.md`
- Delete: `PERFORMANCE_FIX.md`
- Delete: `MEMBER_D_NEXT_STEPS.md`
- Delete: `docs/team_deliverables_interface.md`
- Delete: `docs/member_sync_for_team.md`
- Delete: `docs/2026-06-15-yinren-frontend-motion-design.md`

- [ ] **Step 1: Remove obsolete note files**
- [ ] **Step 2: Remove the external duplicate folders**
- [ ] **Step 3: Check the repository root contains only the main project folder**

### Task 3: Verify and commit

**Files:**
- Modify: `README.md` if the new architecture needs a short note

- [ ] **Step 1: Run a directory check and git status**
- [ ] **Step 2: Run the relevant tests or smoke checks**
- [ ] **Step 3: Commit the reorganization**
