# SIIP HCD Classifier API Documentation

This API provides services for classifying Human-Centered Design (HCD) activities from PDF documents and managing manual labeling of activities.

**Base URL**: `http://<host>:<port>` (e.g., `http://localhost:8000`)

---

## endpoints

### 1. Health Check
Checks if the API is running.

- **URL**: `/health`
- **Method**: `GET`
- **Auth**: None
- **Response**:
  ```json
  {
    "status": "ok"
  }
  ```

### 2. Root Info
Returns basic API information and available endpoints.

- **URL**: `/`
- **Method**: `GET`
- **Auth**: None
- **Response**:
  ```json
  {
    "message": "SIIP HCD Classifier API",
    "endpoints": {
      "health": "/health",
      "classify": "/classify",
      "docs": "/docs"
    }
  }
  ```

### 3. Classify PDF
Upload a PDF file to extract and classify HCD activities. This is the main core feature.

- **URL**: `/classify`
- **Method**: `POST`
- **Auth**: None
- **Content-Type**: `multipart/form-data`
- **Request Body**:
  - `file`: The PDF file to be classified (binary).
- **Response**: `ClassificationResponse` object.

  ```json
  {
    "student_labels": {
      "tables": [
        {
          "activity": "Interviewed users about their needs",
          "HCD_Spaces": ["observation"],
          "HCD_Subspaces": ["user research"]
        }
      ]
    },
    "llm_labels": [
      {
        "activity": "Interviewed users about their needs",
        "HCD_Spaces": ["observation"],
        "HCD_Subspaces": ["user research"]
      }
    ],
    "final_labels": {
      "labels": [
        {
          "activity": "Interviewed users about their needs",
          "student_labeled_spaces": ["observation"],
          "student_labeled_subspaces": ["user research"],
          "result": [1],
          "Reason": "Correctly identified as user research."
        }
      ]
    }
  }
  ```

### 4. Fetch Unlabeled Activity
Retrieves a single unlabeled activity from the database for manual labeling.

- **URL**: `/fetch-unlabeled`
- **Method**: `GET`
- **Auth**: None
- **Response**:
  ```json
  {
    "rowid": 123,
    "Activity": "Conducted a survey on campus."
  }
  ```
  *Returns `{"rowid": null, "Activity": null}` if no unlabeled activities are found.*

### 5. Label Activity
Submit a manual label for a specific activity.

- **URL**: `/label-activity`
- **Method**: `POST`
- **Auth**: None
- **Content-Type**: `application/json`
- **Request Body**:
  ```json
  {
    "rowid": 123,
    "HCD_Space": "Observation",
    "HCD_Subspace": "User Research",
    "Reason": "Explicit mention of survey.",
    "Annotator": "jdoe"
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "message": "Activity 123 labeled successfully"
  }
  ```

---

## Data Models

### Student_HCD_Label
Structured representation of an activity extracted from the PDF.
| Field | Type | Description |
|---|---|---|
| `activity` | string | Description of the activity. |
| `HCD_Spaces` | list[string] | List of HCD spaces identified. |
| `HCD_Subspaces` | list[string] | List of HCD subspaces identified. |

### Output_Label
Final evaluation of the classification.
| Field | Type | Description |
|---|---|---|
| `activity` | string | Original activity description. |
| `student_labeled_spaces` | list[string] | Normalized spaces from the student. |
| `student_labeled_subspaces` | list[string] | Normalized subspaces from the student. |
| `result` | list[int] | Evaluation result per subspace (1: Correct, 0: Not enough evidence, -1: Incorrect). |
| `Reason` | string | Explanation for the evaluation result. |
