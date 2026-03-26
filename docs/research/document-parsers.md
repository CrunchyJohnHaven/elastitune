# Document Parser Survey

The committee-mode parser could be strengthened with a few mature libraries.

## Apache Tika

- GitHub: https://github.com/apache/tika
- License: Apache-2.0
- Strengths: broad file-format support, especially for mixed enterprise documents.
- Tradeoffs: heavier runtime footprint and a more server-like integration pattern.

## pdfplumber

- GitHub: https://github.com/jsvine/pdfplumber
- License: MIT
- Strengths: excellent for structured PDF extraction and fine-grained text inspection.
- Tradeoffs: PDF-first only; it does not solve DOCX or PPTX by itself.

## Mammoth

- GitHub: https://github.com/mwilliamson/mammoth.js
- License: MIT
- Strengths: clean DOCX-to-HTML/text extraction with a bias toward readable output.
- Tradeoffs: less useful for PDF and slide-heavy material.

## PyMuPDF

- GitHub: https://github.com/pymupdf/PyMuPDF
- License: AGPL / commercial dual licensing
- Strengths: strong PDF extraction and layout handling.
- Tradeoffs: licensing is more restrictive than Apache- or MIT-licensed options.

## Recommendation

For ElastiTune, the best low-risk improvement is likely `pdfplumber` for PDF inspection and Apache Tika only if the project needs one parser that can ingest many enterprise file types behind a service boundary.

