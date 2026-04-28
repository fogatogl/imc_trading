"""Permissive multi-flag classifier (round-5).

Parallel pipeline that reads the legacy ``round5/reports/<FAMILY>/`` CSVs and
emits per-product multi-flag classification + per-family ranking. The legacy
``round5/archetypes.py`` priority-ordered classifier stays in place; this
module never modifies it or its outputs.

See ``round5/permissive/README.md`` for the flag taxonomy and run instructions.
"""
