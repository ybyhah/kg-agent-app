# Spatial Overview And Network Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a book-opening splash screen, an immersive overview hero with the provided painting as background and floating vertical calligraphy, and a free-drag spatial exhibition canvas for the relationship network page.

**Architecture:** Keep the existing Flask + server-rendered HTML/CSS/JS structure and preserve the current top navigation. Limit the redesign to the overview hero, opening screen, and relationship network stage so the information architecture remains stable while the visual and interaction layer becomes spatial.

**Tech Stack:** Flask templates, vanilla JavaScript, CSS animations, SVG graph rendering, existing Lucide/Three.js includes, Python unittest frontend render check.

---

### Task 1: Lock The New Render Markers

**Files:**
- Modify: `D:/cxdownload/kg agent/kg_agent_app/tests/test_frontend_render.py`
- Test: `D:/cxdownload/kg agent/kg_agent_app/tests/test_frontend_render.py`

- [ ] **Step 1: Add assertions for the new overview and network markers**

```python
self.assertIn("overviewImmersiveLayer", html)
self.assertIn("heroVerticalTexts", html)
self.assertIn("networkGalleryStage", html)
self.assertIn("networkSpatialHint", html)
```

- [ ] **Step 2: Run the single frontend render test and confirm it fails before implementation**

Run: `python -m pytest tests/test_frontend_render.py -q`
Expected: FAIL because the new marker strings are not in the rendered HTML yet.

### Task 2: Rebuild The Opening And Overview Atmosphere

**Files:**
- Modify: `D:/cxdownload/kg agent/kg_agent_app/templates/index.html`
- Modify: `D:/cxdownload/kg agent/kg_agent_app/static/styles.css`
- Create: `D:/cxdownload/kg agent/kg_agent_app/static/images/overview-immersive-bg.png`

- [ ] **Step 1: Add structural HTML for the book-opening splash and immersive overview layers**

Add:
- a decorative `opening-screen__book` structure inside the splash screen
- an `overviewImmersiveLayer` wrapper around the overview hero
- a `heroVerticalTexts` container with several low-opacity vertical text strips

- [ ] **Step 2: Add CSS for the book-opening animation and overview depth layers**

Implement:
- book cover / page / spine animation
- full-bleed overview background using `overview-immersive-bg.png`
- foreground and background floating calligraphy columns
- safe text scrims so the main copy remains readable

- [ ] **Step 3: Re-run the frontend render test**

Run: `python -m pytest tests/test_frontend_render.py -q`
Expected: PASS for the new overview markers.

### Task 3: Turn The Relationship Network Into A Spatial Gallery

**Files:**
- Modify: `D:/cxdownload/kg agent/kg_agent_app/templates/index.html`
- Modify: `D:/cxdownload/kg agent/kg_agent_app/static/styles.css`

- [ ] **Step 1: Add the network gallery shell markers in the template**

Add:
- `networkGalleryStage`
- `networkSpatialHint`
- one or more decorative background layers around the SVG canvas

- [ ] **Step 2: Update the JavaScript graph stage behavior**

Implement:
- larger roaming canvas dimensions
- stronger free-drag camera behavior in both axes
- immersive default camera framing
- a spatial backdrop rendered behind the graph
- preserved node/edge click behavior and inspector updates

- [ ] **Step 3: Update CSS for the spatial exhibition look**

Implement:
- a larger stage
- floating backdrop layers
- low-noise HUD styling
- stronger depth and exhibition-space framing without blocking data

- [ ] **Step 4: Re-run the frontend render test**

Run: `python -m pytest tests/test_frontend_render.py -q`
Expected: PASS for the network gallery markers.

### Task 4: Verify End-To-End Rendering

**Files:**
- Modify: `D:/cxdownload/kg agent/kg_agent_app/templates/index.html`
- Modify: `D:/cxdownload/kg agent/kg_agent_app/static/styles.css`

- [ ] **Step 1: Run the frontend render test suite**

Run: `python -m pytest tests/test_frontend_render.py -q`
Expected: PASS.

- [ ] **Step 2: Run the app health check through Flask test rendering**

Run:

```powershell
@'
from pathlib import Path
from src.bootstrap import create_app
app = create_app(Path(r"D:\cxdownload\kg agent\kg_agent_app"))
client = app.test_client()
resp = client.get("/")
print(resp.status_code)
print("overviewImmersiveLayer" in resp.get_data(as_text=True))
print("networkGalleryStage" in resp.get_data(as_text=True))
'@ | python -
```

Expected:
- `200`
- `True`
- `True`
