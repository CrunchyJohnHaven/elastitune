# Research Notes

This page captures a short shortlist for the items assigned to GH-1 through GH-4.

## GH-1: Relevant Open Source Projects

### 1. `elastic/search-ui`

GitHub: [https://github.com/elastic/search-ui](https://github.com/elastic/search-ui)

Why it matters:

- Official Elastic search UI library
- Good reference for search state, result rendering, and URL synchronization
- Useful if ElastiTune ever wants a lighter-weight search app shell

### 2. `searchkit/searchkit`

GitHub: [https://github.com/searchkit/searchkit](https://github.com/searchkit/searchkit)

Why it matters:

- Search UI for Elasticsearch and OpenSearch
- Useful reference for faceted search patterns and polished search interactions
- Could inspire a future benchmark or comparison view

### 3. `deepset-ai/haystack`

GitHub: [https://github.com/deepset-ai/haystack](https://github.com/deepset-ai/haystack)

Why it matters:

- Strong retrieval pipeline abstraction
- Helpful for thinking about document loaders, retrievers, and evaluation loops
- Good reference if ElastiTune grows into a broader RAG or search orchestration tool

### 4. `run-llama/llama_index`

GitHub: [https://github.com/run-llama/llama_index](https://github.com/run-llama/llama_index)

Why it matters:

- Strong ecosystem for document ingestion and retrieval abstractions
- Useful for future document-centric workflows and persona-driven feedback loops

### 5. `Channel-Labs/synthetic-conversation-generation`

GitHub: [https://github.com/Channel-Labs/synthetic-conversation-generation](https://github.com/Channel-Labs/synthetic-conversation-generation)

Why it matters:

- Directly relevant to persona and conversation simulation
- Provides a concrete pattern for generating diverse synthetic agents and interactions

## GH-2: Elastic Clients

### Official Python Client

Docs: [Elastic Python client](https://www.elastic.co/docs/reference/elasticsearch/clients/python)

GitHub: [elastic/elasticsearch-py](https://github.com/elastic/elasticsearch-py)

Recommendation:

- Best fit for the backend `ESService`
- Replaces handwritten HTTP calls with a supported, versioned client
- Works well for search, index management, and cluster APIs

### Official JavaScript Client

Docs: [Elastic JavaScript client](https://www.elastic.co/docs/reference/elasticsearch/clients/javascript)

GitHub: [elastic/elasticsearch-js](https://github.com/elastic/elasticsearch-js)

Recommendation:

- Best fit if the frontend ever needs a thin proxy or server-side helper in Node
- Not the primary replacement for the current Python backend service

### Optional DSL Layer

GitHub: [elastic/elasticsearch-dsl-py](https://github.com/elastic/elasticsearch-dsl-py)

Recommendation:

- Useful if ElastiTune wants a more declarative query-building layer in Python
- Good for higher-level search profile experiments, but the low-level client should remain the foundation

## GH-3: Document Parsing Libraries

### Apache Tika

Official site: [https://tika.apache.org/](https://tika.apache.org/)

Python binding: [chrismattmann/tika-python](https://github.com/chrismattmann/tika-python)

Pros:

- Handles many file types through one interface
- Good for mixed office document corpora
- Strong fallback option when format-specific parsers fail

Cons:

- Usually requires a running Tika service or Java dependency
- Heavier operational footprint than a pure-Python parser

### pdfplumber

GitHub: [jsvine/pdfplumber](https://github.com/jsvine/pdfplumber)

Pros:

- Excellent for detailed PDF text and layout extraction
- Very useful when committee docs are generated from PDFs and layout matters

Cons:

- PDF-focused only
- Not a universal office-document parser

### python-docx

GitHub: [python-openxml/python-docx](https://github.com/python-openxml/python-docx)

Pros:

- Strong choice for `.docx` extraction and manipulation
- Lightweight and well understood

Cons:

- DOCX only
- Not useful for PDFs or slides

### python-pptx

GitHub: [scanny/python-pptx](https://github.com/scanny/python-pptx)

Pros:

- Good for PowerPoint slide extraction and preserving slide structure

Cons:

- PowerPoint only
- Not enough on its own for a mixed-document parser stack

## GH-4: UI Component Libraries

### Material UI

Docs: [mui.com/material-ui](https://mui.com/material-ui/)

Pros:

- Full component suite
- Fastest path to polished enterprise UI patterns
- Good defaults for forms, dialogs, tables, and navigation

Cons:

- Heavier visual opinion than the current custom styling
- Migration would be broader because the repo already uses handcrafted layout and theme tokens

### Radix Primitives

Docs: [Radix Primitives](https://www.radix-ui.com/primitives/docs/overview/introduction)

Pros:

- Accessibility-first primitives
- Lower-level and easier to mix with the current custom design language
- Better fit if ElastiTune wants to keep its own look while improving keyboard and focus behavior

Cons:

- Requires more styling work than a full component library
- Does not provide a ready-made visual system

### Recommendation

For ElastiTune, Radix is the safer incremental choice if the goal is accessibility and clean primitives without losing the current brand. MUI is better if the team wants to trade design freedom for speed and a large standard component set.
