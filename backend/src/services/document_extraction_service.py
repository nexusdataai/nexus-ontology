"""
Document Extraction Service

Extracts structured fields from uploaded documents (PDF, Excel, CSV) using:
1. PyMuPDF for digital PDF text extraction
2. AWS Textract for scanned/image-based PDFs
3. openpyxl for Excel files
4. OpenAI LLM for structured field extraction from raw text
"""

import io
import json
import os
import time
from typing import Any, Dict, Optional

from loguru import logger

doc_logger = logger.bind(component="doc-extraction")

FIELD_SCHEMAS: Dict[str, Dict[str, str]] = {
    "invoice": {
        "Vendor_Name_Extracted": "string - vendor/supplier name",
        "Invoice_Number_Extracted": "string - invoice reference number",
        "Amount_Extracted": "number - total invoice amount",
        "Line_Items": "string - summary of line items (e.g. '5 items: widgets, bolts...')",
        "Matched_PO_ID": "string - purchase order ID if mentioned, else empty",
        "Validation_Status": "one of: Pending, Validated, Needs_Review, Rejected",
    },
    "lab_report": {
        "Material_ID": "string - material/sample ID tested",
        "Batch_ID": "string - batch/lot number",
        "Tests_Extracted": "string - summary of tests performed (e.g. '5 tests')",
        "Results": "string - summary of results (e.g. 'All pass' or '2 deviations noted')",
        "Spec_Compliance": "boolean - true if all specs met, false otherwise",
        "Inspector_Name": "string - inspector or analyst name if mentioned",
    },
    "contract": {
        "Vendor_ID": "string - vendor/supplier identifier",
        "Effective_Date": "date string YYYY-MM-DD",
        "Expiry_Date": "date string YYYY-MM-DD",
        "Contracted_Price": "number - price per unit or total contract value",
        "Volume_Commitment": "integer - committed volume/quantity",
        "SLA_Terms": "string - key SLA terms summary",
        "Penalty_Clauses": "string - penalty clause summary",
        "Auto_Renewal": "boolean - true if auto-renewal mentioned",
    },
    "sustainability_report": {
        "Report_Type": "one of: Annual, Quarterly, Audit",
        "Period": "string - reporting period (e.g. '2025-Q1')",
        "KPIs_Extracted": "string - comma-separated KPIs found",
        "Targets": "string - sustainability targets mentioned",
        "Actuals": "string - actual performance metrics",
        "Framework": "one of: GRI, SASB, CDP, TCFD or empty if unknown",
    },
}

MAX_RETRIES = 3
LLM_TIMEOUT = 45.0


def _build_extraction_prompt(raw_text: str, document_type: str) -> str:
    schema = FIELD_SCHEMAS.get(document_type, {})
    fields_desc = "\n".join(f'  "{k}": {v}' for k, v in schema.items())

    return (
        "You are a document extraction specialist. Extract structured fields from the document text below.\n\n"
        "Return ONLY a valid JSON object with these fields:\n"
        "{\n" + fields_desc + "\n}\n\n"
        "Rules:\n"
        "- Return valid JSON only, no markdown fences or explanation.\n"
        "- Use empty string for fields you cannot find.\n"
        "- For boolean fields, use true/false.\n"
        "- For number fields, return the numeric value without currency symbols.\n\n"
        "Document text:\n"
        + raw_text[:4000]
    )


class DocumentExtractionService:

    def __init__(self, model: str = "gpt-4o-mini"):
        self._model = model

    def _extract_text_pdf(self, content: bytes) -> str:
        try:
            import fitz
            pdf = fitz.open(stream=content, filetype="pdf")
            text = "\n".join(page.get_text() for page in pdf)
            pdf.close()
            if len(text.strip()) >= 50:
                doc_logger.info(f"PyMuPDF extracted {len(text)} chars from PDF")
                return text.strip()
            doc_logger.info("PyMuPDF extracted too little text, PDF may be scanned")
            return ""
        except ImportError:
            doc_logger.warning("PyMuPDF not available")
            return ""
        except Exception as e:
            doc_logger.warning(f"PyMuPDF extraction failed: {e}")
            return ""

    def _extract_text_textract(self, s3_bucket: str, s3_key: str) -> str:
        try:
            import boto3
            client = boto3.client("textract", region_name=os.getenv("AWS_REGION", "us-east-1"))
            response = client.detect_document_text(
                Document={"S3Object": {"Bucket": s3_bucket, "Name": s3_key}}
            )
            lines = [
                block["Text"]
                for block in response.get("Blocks", [])
                if block["BlockType"] == "LINE" and "Text" in block
            ]
            text = "\n".join(lines)
            doc_logger.info(f"Textract extracted {len(lines)} lines, {len(text)} chars")
            return text
        except Exception as e:
            doc_logger.warning(f"Textract extraction failed: {e}")
            return ""

    def _extract_text_excel(self, content: bytes) -> str:
        try:
            from openpyxl import load_workbook
            wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
            lines = []
            for sheet in wb.sheetnames[:3]:
                ws = wb[sheet]
                lines.append(f"Sheet: {sheet}")
                for row in ws.iter_rows(max_row=200, values_only=True):
                    vals = [str(c) if c is not None else "" for c in row]
                    if any(vals):
                        lines.append(" | ".join(vals))
            wb.close()
            text = "\n".join(lines)
            doc_logger.info(f"Excel extracted {len(lines)} lines from {len(wb.sheetnames)} sheets")
            return text
        except ImportError:
            doc_logger.warning("openpyxl not available")
            return ""
        except Exception as e:
            doc_logger.warning(f"Excel extraction failed: {e}")
            return ""

    def _extract_text(self, content: bytes, filename: str, s3_bucket: str, s3_key: str) -> str:
        lower = filename.lower()
        if lower.endswith((".xlsx", ".xls")):
            return self._extract_text_excel(content)
        if lower.endswith(".csv"):
            return content.decode("utf-8", errors="ignore")[:10000]

        text = self._extract_text_pdf(content)
        if text:
            return text
        if s3_bucket and s3_key:
            return self._extract_text_textract(s3_bucket, s3_key)
        return ""

    def _extract_fields_llm(self, raw_text: str, document_type: str) -> Dict[str, Any]:
        if not raw_text.strip():
            return {}

        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            try:
                from src.config.config_provider import get_config
                api_key = get_config().openai_api_key or ""
            except Exception:
                pass
        if not api_key:
            doc_logger.warning("No OpenAI API key — returning empty extraction")
            return {}

        try:
            import openai
            client = openai.OpenAI(api_key=api_key, timeout=LLM_TIMEOUT)
        except ImportError:
            doc_logger.warning("openai package not installed")
            return {}

        prompt = _build_extraction_prompt(raw_text, document_type)

        for attempt in range(MAX_RETRIES):
            try:
                response = client.chat.completions.create(
                    model=self._model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=800,
                )
                content = response.choices[0].message.content.strip()
                if content.startswith("```"):
                    content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
                fields = json.loads(content)
                doc_logger.info(f"LLM extracted {len(fields)} fields for {document_type}")
                return fields
            except Exception as e:
                doc_logger.warning(f"LLM extraction attempt {attempt + 1} failed: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
        return {}

    def _compute_confidence(self, extracted: Dict[str, Any], document_type: str) -> float:
        expected = FIELD_SCHEMAS.get(document_type, {})
        if not expected:
            return 50.0
        filled = sum(1 for k in expected if k in extracted and extracted[k] not in ("", None))
        return round((filled / len(expected)) * 100, 1)

    async def extract_document(
        self, content: bytes, filename: str,
        document_type: str, s3_bucket: str = "", s3_key: str = "",
    ) -> Dict[str, Any]:
        doc_logger.info(f"Starting extraction: {filename} ({document_type}, {len(content)} bytes)")

        raw_text = self._extract_text(content, filename, s3_bucket, s3_key)
        if not raw_text:
            doc_logger.warning(f"No text extracted from {filename}")
            return {"Extraction_Confidence": 0.0, "_raw_text": "", "_extraction_status": "no_text"}

        fields = self._extract_fields_llm(raw_text, document_type)
        confidence = self._compute_confidence(fields, document_type)
        fields["Extraction_Confidence"] = confidence

        doc_logger.info(f"Extraction complete: {filename} -> {len(fields)} fields, {confidence}% confidence")
        return fields
