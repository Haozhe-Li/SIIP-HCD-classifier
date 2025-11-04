import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain.chat_models import init_chat_model

from core.data_table import (
    Output_Label,
    LLM_HCD_Label,
    List_Student_HCD_Label,
    List_Output_Label,
)
from core.model_config import FINAL_EVAL_MODEL
from core.prompt import FINAL_EVAL_SYS_PROMPT


class FinalProcessing:
    """Post-processing helpers for final activity evaluation."""

    def __init__(self) -> None:
        """
        Initialize the FinalProcessing helper.

        Sets up the chat model using the final evaluation configuration and binds it to a structured output schema
        (`LLM_HCD_Label`) for consistent final activity classification results.
        """
        self._model = init_chat_model(FINAL_EVAL_MODEL)
        self.bound_model = self._model.with_structured_output(Output_Label)

    def final_eval(
        self,
        student_hcd_label: List_Student_HCD_Label,
        llm_hcd_label: list[LLM_HCD_Label],
    ) -> List_Output_Label:
        """Evaluate the final output labels against the student labels."""
        response = []
        for student_entry, llm_entry in zip(student_hcd_label.tables, llm_hcd_label):
            response.append(
                self.bound_model.invoke(
                    [
                        {"role": "system", "content": FINAL_EVAL_SYS_PROMPT},
                        {
                            "role": "user",
                            "content": (
                                "Evaluate the following student and LLM labels for the activity:\n\n"
                                f"Activity: {student_entry.activity}\n"
                                f"Student HCD Spaces: {', '.join(student_entry.HCD_Spaces)}\n"
                                f"Student HCD Subspaces: {', '.join(student_entry.HCD_Subspaces)}\n"
                                f"LLM HCD Spaces: {', '.join(llm_entry.HCD_Spaces)}\n"
                                f"LLM HCD Subspaces: {', '.join(llm_entry.HCD_Subspaces)}\n"
                                f"LLM Reason: {llm_entry.Reason}\n"
                            ),
                        },
                    ]
                )
            )
        return List_Output_Label(labels=response)

    def display_output_labels(
        self, output_labels: List_Output_Label | list[Output_Label]
    ) -> str:
        """Display the extracted Output_Label entries in a readable format."""
        res = ""

        entries = (
            output_labels.labels
            if isinstance(output_labels, List_Output_Label)
            else output_labels
        )

        header = "| Entry | Student Labeled Subspaces | Result |\n"
        separator = "| ---: | --- | ---: |\n"
        print(header.strip())
        res += header
        print(separator.strip())
        res += separator
        for idx, entry in enumerate(entries, start=1):
            subspaces = entry.student_labeled_subspaces
            safe_subspaces = subspaces.replace("|", "\\|")
            row = f"| {idx} | {safe_subspaces} | {entry.result} |\n"
            print(row.strip())
            res += row
        return res


if __name__ == "__main__":
    from core.preprocessing import PreProcessor
    from core.processing import Processing

    final_processor = FinalProcessing()
    processor = Processing()
    preprocessor = PreProcessor()
    pdf_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "data",
        "progress_report_example_1.pdf",
    )
    # Preprocess to get student labeled data
    student_table_data = preprocessor.invoke(pdf_path)
    print("Student Labeled Data:")
    preprocessor.display_list_data_table(student_table_data)

    # Process to get LLM labeled data
    llm_table_data = processor.classify_table(student_table_data)
    print("\nLLM Labeled Data:")
    processor.display_list_data_table(llm_table_data)

    # Final evaluation
    final_output = final_processor.final_eval(student_table_data, llm_table_data)
    print("\nFinal Evaluation Results:")
    final_processor.display_output_labels(final_output)
