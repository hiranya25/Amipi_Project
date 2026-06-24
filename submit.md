# Final Submission Guide & Video Script

This document contains your checklist of final deliverables and a step-by-step script for recording your project demo video.

## 📦 What You Need to Submit (Deliverables)

Before you hit submit, ensure you have these items ready:
1. **Source Code:** Either a link to your public GitHub repository OR a ZIP file containing your project folder. 
   *(Note: If creating a ZIP, do NOT include the `venv` folder or the `.env` file containing your real API key).*
2. **The README.md:** This must be at the root of your project (which we just perfected).
3. **Demo Video Link:** A link to a 2–4 minute screen recording (Loom, YouTube Unlisted, or Google Drive) demonstrating your project. Use the script below.

---

## 🎬 Demo Video Script

**Preparation before recording:**
- Have your code editor open to the project folder.
- Have a terminal open with your virtual environment activated.
- Start the web app by running `python3 web.py` before hitting record.
- Open your browser to `http://localhost:5000`.
- Have your two CSV files ready on your desktop to drag-and-drop.

### 1. Introduction (0:00 - 0:20)
* **Action:** Start with your screen showing the web interface in the browser.
* **Script:** "Hi, I'm [Your Name], and this is my submission for the Inventory Recommendation Tool project. I decided to go beyond a CLI script and built a full-stack, responsive web application — a 'Jewelry Command Center' — to make these recommendations highly actionable for retail buyers."

### 2. Architecture & The AI Boundary (0:20 - 0:50)
* **Action:** Quickly flip to your code editor showing `engine.py` and `ai_reason.py`.
* **Script:** "A major requirement was strict separation of concerns. In my codebase, `engine.py` handles all the mathematical formulas and priority classifications purely deterministically. There are absolutely no hard-coded row answers. The AI is completely walled off inside `ai_reason.py`—it never touches quantities or priorities. It only reads the deterministic output to generate a business justification."

### 3. Error Handling Demonstration (0:50 - 1:20)
* **Action:** Flip back to the browser. Drag `inventory_sales.csv` and drop it into the *wrong* box (the `event_multipliers` box).
* **Script:** "To demonstrate validation and error handling, if a user uploads the wrong file, the system doesn't crash with a Python traceback. Instead, the backend catches the schema mismatch instantly, and the frontend displays a localized, graceful error directly beneath the dropzone."
* **Action:** Now drag the correct files into their correct boxes. Select "JCK Vegas" from the dropdown.

### 4. Running the Engine (1:20 - 2:00)
* **Action:** Click "Generate recommendations". Watch the cards populate.
* **Script:** "Once we run the engine, the UI transforms the data into a priority-driven dashboard. We have our KPI metrics at the top, and the SKUs are rendered as dynamic cards, color-coded by their deterministic priority—red for High, yellow for Medium, green for Low."
* **Action:** Scroll through the cards briefly. 
* **Script:** "Notice the AI reasons on each card. They use specific jewelry-retail vocabulary like 'sell-through velocity' and 'JCK Vegas demand', and they perfectly align with the deterministic math without overriding it."

### 5. Transparency & Calculation Trace (2:00 - 2:30)
* **Action:** Click the "Details" button on one of the **High** priority SKUs to open the slide-over panel.
* **Script:** "Trust is critical in retail. If a buyer clicks 'Details', this slide-over panel reveals exactly how the system arrived at its conclusion. We expose the exact Calculation Trace step-by-step, proving the math is exact. We also display the isolated AI reasoning block right above it."

### 6. Exporting (2:30 - 2:50)
* **Action:** Click the "Build order sheet" button at the top right. Show the CSV downloading.
* **Script:** "Finally, the entire dataset containing all 10 required fields—including the generated AI reason—can be exported directly to a CSV order sheet with a single click."

### 7. Outro (2:50 - 3:00)
* **Action:** Leave the screen on the beautiful dashboard.
* **Script:** "The tool also supports full CLI execution, includes robust fallback templates if the Groq API goes offline, and processes everything dynamically. Thank you for reviewing my submission!"

---

## 🚀 Production Deployment Plan

If you need to answer questions about how you would take this from a local script to a live retail tool, use this deployment plan:

**1. Web Server Migration (WSGI)**
Currently, the app uses Flask's built-in development server. For production, we would wrap the Flask app with `gunicorn`, a robust production-grade WSGI HTTP Server. 
*Command:* `gunicorn -w 4 -b 0.0.0.0:5000 web:app`

**2. Containerization (Docker)**
We would write a `Dockerfile` that packages Python 3.10+, installs `requirements.txt`, and sets the `gunicorn` entrypoint. This ensures the app runs identically regardless of where it is hosted.

**3. Hosting (Render / Heroku / AWS)**
Since the application relies on lightweight, deterministic python calculations and rapid Groq API calls, it is essentially stateless (file uploads are processed in temporary memory and flushed). We can deploy the Docker container to a PaaS like Render or Heroku on a basic tier, pointing the environment variables to the production `GROQ_API_KEY`.

**4. Database Integration (Future Scaling)**
Right now, the tool relies on raw CSV uploads. A production next-step would be swapping `loader.py` to pull directly from the retailer's live ERP system (like NetSuite or Shopify) via API or SQL connection, entirely eliminating the need for manual CSV drops.
