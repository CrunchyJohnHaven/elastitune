# Elastic Product Store Benchmark

This benchmark pack turns an Elastic-owned sample app into a repeatable ElastiTune proof target.

The upstream target is:

- `elastic/elasticsearch-labs`
- `supporting-blog-content/hybrid-search-for-an-e-commerce-product-catalogue`

Why this target:

- Real React storefront + search API
- Local Elasticsearch/Kibana via Docker Compose
- Real product dataset with `931` docs
- Clear lexical and optional hybrid/vector search behavior
- Untuned enough to make a before/after relevance story credible

## What This Pack Adds

- A bootstrap script that clones the upstream Elastic repo into `.benchmarks`
- A local-index creation script that works with plain `http://localhost:9200`
- A product ingestion script for lexical or optional hybrid indexing
- A fixed eval set for benchmark-grade ElastiTune runs

## Prerequisites

- Docker Desktop with `docker compose`
- Python 3.11+
- Backend dependencies installed:

```bash
pip install -r backend/requirements.txt
```

For optional hybrid/vector indexing, also install:

```bash
pip install sentence-transformers
```

## 1. Clone the Upstream Elastic Sample

```bash
python benchmarks/elastic-product-store/setup_target.py
```

This clones the Elastic Labs repo into:

```bash
.benchmarks/elastic-product-store/elasticsearch-labs
```

## 2. Start Local Elasticsearch

```bash
cd .benchmarks/elastic-product-store/elasticsearch-labs/supporting-blog-content/hybrid-search-for-an-e-commerce-product-catalogue/product-store-search/docker
docker compose up -d
```

This should expose:

- Elasticsearch: `http://127.0.0.1:9200`
- Kibana: `http://127.0.0.1:5601`

## 3. Create the Benchmark Index

Lexical-only benchmark:

```bash
python benchmarks/elastic-product-store/create_index.py
```

Optional hybrid/vector benchmark:

```bash
python benchmarks/elastic-product-store/create_index.py --hybrid
```

## 4. Ingest the Product Dataset

Lexical-only ingest:

```bash
python benchmarks/elastic-product-store/ingest_products.py
```

Optional hybrid/vector ingest:

```bash
python benchmarks/elastic-product-store/ingest_products.py --hybrid
```

If you want a smaller smoke-test run:

```bash
python benchmarks/elastic-product-store/ingest_products.py --limit 200
```

## 5. Optional: Run the Upstream Product Store UI

Front-end:

```bash
cd .benchmarks/elastic-product-store/elasticsearch-labs/supporting-blog-content/hybrid-search-for-an-e-commerce-product-catalogue/app-product-store
npm install
npm start
```

The upstream API still expects additional local adaptation, so treat the UI as a visual companion, not the source of truth for benchmark measurement. ElastiTune should connect directly to the Elasticsearch index.

## 6. Run ElastiTune Against the Benchmark

Use ElastiTune live mode with:

- Elasticsearch URL: `http://127.0.0.1:9200`
- Index name: `products-catalog`
- API key: leave blank for local Docker

Then upload:

- `benchmarks/elastic-product-store/eval-set.json`

Recommended:

- Turn off auto-generated eval
- Run 30-60 experiments
- Keep the default lexical-first profile for the first pass

## Suggested Proof Queries

The fixed eval set focuses on intent that is easy to recognize in the UI:

- `lip pencil`
- `serum foundation`
- `mascara`
- `eye shadow palette`
- `bronzer`
- `foundation`
- `lip gloss`
- `liquid liner`

## Success Criteria

This benchmark is successful when we can show:

- Baseline score on the fixed eval set
- Improved score after ElastiTune optimization
- The search-profile diff that produced the lift
- Visible result ordering improvement for at least 3-5 benchmark queries
