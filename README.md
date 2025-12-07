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

1. Launch the REST API server:

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
