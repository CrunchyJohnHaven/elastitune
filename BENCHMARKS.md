# Benchmark Harness

ElastiTune ships with several benchmark packs, but the `elastic-product-store` pack is the clearest end-to-end demo target.

## Product Store benchmark

### 1. Clone the upstream sample

```bash
python benchmarks/elastic-product-store/setup_target.py
```

This clones the Elastic Labs sample into `.benchmarks/elastic-product-store/elasticsearch-labs`.

### 2. Start Elasticsearch

```bash
cd .benchmarks/elastic-product-store/elasticsearch-labs/supporting-blog-content/hybrid-search-for-an-e-commerce-product-catalogue/product-store-search/docker
docker compose up -d
```

### 3. Create the index

```bash
python benchmarks/elastic-product-store/create_index.py
```

Use `--hybrid` if you want the vector-enabled variant.

### 4. Ingest the dataset

```bash
python benchmarks/elastic-product-store/ingest_products.py
```

The sample dataset contains 931 documents. Use `--limit` for a smaller smoke test, or `--hybrid` for the vector variant.

### 5. Run ElastiTune

Connect the app with:

- Elasticsearch URL: `http://127.0.0.1:9200`
- Index name: `products-catalog`
- API key: leave blank for local Docker

Upload `benchmarks/elastic-product-store/eval-set.json` or keep auto-generated eval disabled.

## Interpreting `eval-set.json`

The eval set is a fixed list of query / relevant-document pairs. ElastiTune uses it to measure nDCG@10 before and after tuning.

- Query text is the user intent.
- `relevantDocIds` identifies the expected hits.
- Optional `difficulty` and `personaHint` fields help the UI and the report explain why a query matters.

## Adding a custom benchmark

1. Create a folder under `benchmarks/<your-benchmark>/`.
2. Provide:
   - a setup script that creates the index,
   - an ingest script,
   - an `eval-set.json`,
   - and a short README.
3. Add the benchmark to `benchmarks/setup.py`.
4. Add the index name and setup command to `backend/api/routes_connect.py` so the connect screen can surface it.
5. Update the README and benchmark table if you want it advertised in the UI.
