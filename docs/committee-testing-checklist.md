# Committee Mode Testing Checklist

Use this for the first human QA pass of the new committee workflow.

## Suggested Test Input

- Primary sample: `backend/data/demo/committee_demo_brief.txt`
- Optional: a real `PDF`, `PPTX`, or `DOCX` pitch deck

## Startup

1. Install backend dependencies from `backend/requirements.txt`
2. Run `python3 backend/scripts/smoke_app.py`
3. Start the app
4. Open `/committee`

## Setup Screen Checks

1. Upload the sample document
2. Leave the audience box blank for automatic committee inference, or enable seeded SBA personas if you want the fixed SBA room
3. Confirm `Start Committee Run` enables immediately after the file is selected
4. Optionally click `Preview Committee`
5. Confirm the parsed preview shows:
   - document summary
   - section list
   - persona list
6. Start the committee run directly from the setup screen

## Live Run Checks

1. Confirm the header updates consensus, rewrites, delta, and elapsed time while the run is still in progress
2. Confirm the left rail fills with rewrite attempts
3. Confirm the center panel uses the document-centered fish-tank visualization and shows:
   - document hub in the center
   - committee members arranged around it
   - quote fragments / reaction snippets
   - an active section indicator
5. Confirm warnings surface visibly if parsing or scoring falls back to compatibility / heuristic mode
4. Confirm the right rail shows:
   - document info
   - detected industry
   - AI coverage
   - score timeline
   - persona list
   - persona detail with objections and section scores
5. Confirm the run completes and the report button appears

## Report Checks

1. Open the committee report
2. Confirm summary metrics look reasonable
3. Confirm optimized sections are shown
4. Confirm persona outcomes render
5. Confirm rewrite log is populated
6. Click `Download Export JSON`

## Regression Checks

1. Return to `/`
2. Start the original search demo mode
3. Confirm the search run still starts and updates normally

## Known First-Pass Expectations

- Committee scoring and rewriting can run heuristically without an LLM key
- Export is currently JSON/report oriented, not native slide-perfect deck regeneration
- The center “committee space” is functional but still a good candidate for visual polish
