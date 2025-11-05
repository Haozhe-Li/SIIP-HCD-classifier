from __future__ import annotations

import os
from typing import Any

import gradio as gr
from core.preprocessing import PreProcessor
from core.processing import Processing
from core.postprocessing import FinalProcessing


def run(pdf_input: Any, progress=gr.Progress(track_tqdm=True)) -> str:
    final_processor = FinalProcessing()
    processor = Processing()
    preprocessor = PreProcessor()
    if not pdf_input:
        raise gr.Error("Please upload a PDF file before running the classifier.")

    progress(0.1, desc="Preprocessing PDF...")
    pdf_path = os.fspath(pdf_input)
    # Preprocess to get student labeled data
    student_table_data = preprocessor.invoke(pdf_path)
    print("Student Labeled Data:")
    preprocessor.display_list_data_table(student_table_data)

    # Process to get LLM labeled data
    progress(0.5, desc="Running classifier...")
    llm_table_data = processor.classify_table(student_table_data)
    print("\nLLM Labeled Data:")
    processor.display_list_data_table(llm_table_data)

    # Final evaluation
    progress(0.8, desc="Scoring results...")
    final_output = final_processor.final_eval(student_table_data, llm_table_data)
    print("\nFinal Evaluation Results:")
    res = final_processor.display_output_labels(final_output)

    progress(1.0, desc="Done")
    return res


def create_interface() -> gr.Blocks:
    with gr.Blocks(
        theme=gr.themes.Soft(primary_hue="blue", neutral_hue="slate")
    ) as demo:
        gr.HTML(
            """
            <div id="app-header">
                <div id="app-title">SIIP HCD Classifier</div>
                <div id="app-subtitle">Upload a student PDF to generate harmonized competency labels.</div>
            </div>
            """
        )

        with gr.Row(equal_height=True):
            with gr.Column(scale=5, min_width=320):
                gr.Markdown(
                    """
                    ### Step 1: Upload PDF
                    - Provide a single PDF generated from the SIIP evaluation workflow.
                    - The pipeline will extract student annotations, classify with HCD labels, and surface the final rubric.
                    """
                )
                file_input = gr.File(
                    label="PDF Upload",
                    file_types=[".pdf"],
                    type="filepath",
                    file_count="single",
                )
                with gr.Row():
                    submit_button = gr.Button("Run Classification", variant="primary")
                    clear_button = gr.Button("Clear", variant="secondary")
                gr.Markdown(
                    "💡 Need a sample? Try documents inside `data/` while experimenting.",
                )

            with gr.Column(scale=5, min_width=320):
                text_output = gr.Markdown(
                    value="Result preview will appear here after processing.",
                    elem_id="result-card",
                    label="Classification Result",
                )

        submit_button.click(run, inputs=file_input, outputs=text_output)
        clear_button.click(
            lambda: (None, "Result cleared."),
            inputs=[],
            outputs=[file_input, text_output],
        )

        return demo


demo = create_interface()


if __name__ == "__main__":
    demo.launch()
