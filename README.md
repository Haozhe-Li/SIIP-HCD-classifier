# README

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)](https://www.python.org/) [![LangGraph](https://img.shields.io/badge/LangGraph-supported-7b61ff)](https://www.langgraph.dev/) [![LangChain](https://img.shields.io/badge/LangChain-supported-lightgrey?logo=langchain&logoColor=white)](https://github.com/langchain-ai/langchain) [![FastAPI](https://img.shields.io/badge/FastAPI-supported-00caff?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)

This project develops an LLM‑powered automation tool to support the Strategic Instructional Innovations Program (SIIP) project: [Redesigning Design: Incorporating HCD and the 3 C's in Capstone Design Courses](https://ae3.grainger.illinois.edu/programs/siip-grants/64451).

For a full design proposal and technical details, see our [design proposal](./docs/DESIGN.md).

## Get Started

1. Clone this repository: `git clone https://github.com/Haozhe-Li/SIIP-HCD-classifier.git`
2. Install dependencies: `pip install -r requirements.txt`
   - The pipeline uses [PyMuPDF](https://pymupdf.readthedocs.io/en/latest/) for PDF parsing, so make sure system packages required by PyMuPDF are available.
3. Update your LLM API Key in .env.example file. Change the following with the real API key:

```env
OPENAI_API_KEY=your-openai-api-key-here
```

4. Launch the REST API server:

```bash
uvicorn gradio_gui:app --host 0.0.0.0 --port 8001
```

### REST API usage

- Check server status:

   ```bash
   curl http://localhost:8001/health
   ```

- Classify a PDF report:

   ```bash
   curl -F "file=@data/progress_report_1.pdf" http://localhost:8001/classify
   ```

   The response contains the extracted student labels, model classifications, and final evaluation results as JSON.

## Extract Activities from Multi-page Program Report PDF

If your PDF has one program report per page, first extract all `Activity 1..n` items page-by-page with LangChain:

```bash
python data_extract_llm.py extract path/to/reports.pdf --output data/extracted_activities.jsonl
```

For testing, you can only process first X pages:

```bash
python data_extract_llm.py extract path/to/reports.pdf --max-pages 5 --output data/extracted_activities.jsonl
```

- Output format is JSONL (one line per page), for example:
   - `{"page": 1, "activities": ["...", "..."]}`
   - `{"page": 2, "activities": []}`
- Pages without activities are kept as empty lists for robustness.

After reviewing the extracted JSONL, insert non-empty activities into database table `labels(Activity)`:

```bash
python data_extract_llm.py insert --input data/extracted_activities.jsonl
```

Make sure the following environment variables are set before DB insertion:

- `D1_ACCOUNT_ID`
- `D1_API_TOKEN`
- `D1_DATABASE_ID`
