# ElastiTune Kibana Plugin Prototype

This is a starter Kibana plugin scaffold for surfacing ElastiTune history inside Kibana.

## Current scope

- Registers an `ElastiTune` application entry
- Fetches run history from the ElastiTune REST API
- Renders a minimal improvement table for recent search runs
- Leaves authentication, styling hardening, and embeddable panel registration as follow-up work

## Follow-up TODOs

- Replace the direct fetch with authenticated route proxies or Kibana server-side APIs
- Register an embeddable panel instead of an app-only view
- Add Lens-compatible saved object generation
- Style with Elastic UI (EUI)
