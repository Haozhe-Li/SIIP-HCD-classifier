from __future__ import annotations

import os
from typing import Any

import gradio as gr


def run(pdf_input: Any) -> str:
    """Main function to run the classifier

    Args:
        pdf_input (Any): progress report upload as PDF

    Returns:
        str: dataset result
    """
    return "Test!"


def create_interface() -> gr.Interface:
    """Gradio interface

    Returns:
        gr.Interface: titled
    """
    file_input = gr.File(label="Upload PDF", file_types=[".pdf"], type="filepath")
    text_output = gr.Textbox(label="Result", lines=3)
    return gr.Interface(
        fn=run, inputs=file_input, outputs=text_output, allow_flagging="never"
    )


demo = create_interface()


if __name__ == "__main__":
    demo.launch()
