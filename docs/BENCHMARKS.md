# Benchmarks

ElastiTune ships with a small benchmark harness so the app can be demoed against known datasets and repeatable eval sets.

## How The Harness Works

The top-level entry point is `benchmarks/setup.py`.

It can:

- create the benchmark index
- ingest the fixture dataset
- verify the document count
- report whether the local Elasticsearch instance is ready

Run everything at once:

```bash
python3 benchmarks/setup.py
```

Reset and reload the indexes:

```bash
python3 benchmarks/setup.py --reset
```

Set up only one benchmark:

```bash
python3 benchmarks/setup.py --only products-catalog
```

## Elastic Product Store

The most complete proof target is `benchmarks/elastic-product-store/`.

The workflow is:

1. Bootstrap the upstream Elastic sample app.
2. Start the sample app's local Elasticsearch and Kibana stack.
3. Create the `products-catalog` index.
4. Ingest the product dataset.
5. Upload `benchmarks/elastic-product-store/eval-set.json` into ElastiTune.

```bash
python3 benchmarks/elastic-product-store/setup_target.py
python3 benchmarks/elastic-product-store/create_index.py
python3 benchmarks/elastic-product-store/ingest_products.py
```

For hybrid search experiments:

```bash
python3 benchmarks/elastic-product-store/create_index.py --hybrid
python3 benchmarks/elastic-product-store/ingest_products.py --hybrid
```

## Reading `eval-set.json`

The `eval-set.json` files contain the fixed evaluation queries and relevance judgments used by ElastiTune.

Each item generally includes:

- `id`
- `query`
- `relevantDocIds`
- optional `personaHint`
- optional `difficulty`

The eval set is intentionally fixed so improvements can be compared across runs and across code changes.

## Adding A Custom Benchmark

To add a new benchmark pack:

1. Create a new directory under `benchmarks/`.
2. Add `create_index.py` and `ingest_*.py` scripts.
3. Add a fixed `eval-set.json`.
4. Register the benchmark in `benchmarks/setup.py`.
5. Update the README or internal docs with the new index name and expected document count.

Recommended shape for a benchmark pack:

- one index name
- one ingest script
- one eval set
- one setup note for any external sample app or dataset source

## Interpreting Results

The benchmark is useful when it answers these questions:

- Did the baseline score move in the right direction?
- Which query patterns improved?
- Which profile change produced the lift?
- Is the result stable enough to present live?

For the product-store benchmark, a good demo usually shows:

1. Baseline search results.
2. A few experiments.
3. The final report.
4. A visible change in ranking for the fixed eval queries.
