# SNP — Signal Normalization Protocol

The single canonical message contract for the Basis stack. Everything passes
through SNP; nothing talks directly to anything else. In v1 SNP is a **library,
not a service**: a schema, a static encoding registry, and validate/normalize
functions. It does message-level work only and **never interprets vector
meaning** (the opaque-vector rule).

## Message shape

```json
{
  "node_id": "brain_1",
  "timestamp": 1730000000000,
  "signal_type": "motor",
  "payload": {
    "vector": [0.42, 0.15, 0.38, 0.19, 0.41, 0.22],
    "confidence": 1.0,
    "paradigm": "motor_imagery_lr",
    "encoding": "mi.c3czc4.mubeta.v1"
  }
}
```

- `vector` is bare positional floats; its meaning is described **by reference**
  via `encoding`, never inline, so messages stay small and SNP stays stateless.
- `encoding` is its own field (not derived from `paradigm`) so channel count can
  scale without changing task identity.

## Encoding registry

`snp/encodings.py` maps a versioned `encoding` id to its `Layout`
(`channels`, `bands`, `rate_hz`, `window_s`, `length`). Ids follow
`domain.specifics.layout.version` and are namespaced by producer:

- `mi.*` — Basis Brain (motor imagery). v1: `mi.c3czc4.mubeta.v1` (3 ch x 2 bands = 6 floats).
- `env.*` — Basis Locus (environment perception). e.g. `env.room.pose_visible.v1`.

Scaling channels or adding a modality = add one registry entry; nothing
downstream changes because the infra treats the vector as opaque and reads only
its length.

## Usage

```python
import snp

msg = snp.validate(raw_dict)          # raises SchemaError / UnknownEncodingError / VectorLengthError
canonical = snp.normalize_validated(raw_dict)  # validate + canonical dict form
ok = snp.is_valid(raw_dict)           # bool
```

## Develop / test

```bash
pip install -e ".[dev]"
pytest -q
```
