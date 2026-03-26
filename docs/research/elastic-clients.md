# Elastic Client Survey

ElastiTune currently uses custom HTTP code for Elasticsearch, so the official clients are the first obvious replacement candidates.

## JavaScript / TypeScript

- GitHub: https://github.com/elastic/elasticsearch-js
- Package: `@elastic/elasticsearch`
- Good fit for: server-side calls from Node-based tooling, typed request/response helpers, and future shared client code.
- Watch-outs: the client is primarily designed for Node environments, so browser calls still need a backend proxy.

## Python

- GitHub: https://github.com/elastic/elasticsearch-py
- Package: `elasticsearch`
- Good fit for: backend service code, tests, and lower-level index / query operations.
- Watch-outs: keep the major version aligned with the target Elasticsearch server release.

## Recommendation

For Elasticsearch 8.15, the safest path is to adopt the 8.x official clients on the backend first and keep the browser talking to the FastAPI API. That minimizes bundle size and keeps credentials off the client.

