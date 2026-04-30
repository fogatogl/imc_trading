"""Round 5 ML research workstream.

Per-family ML models for forward-return prediction and toxicity classification.
Linear (Ridge / Lasso) + tree-based (LightGBM, RF) only.

Reuses round5.research_lib for data loading and microstructure features.
Outputs land in round5/reports/<FAMILY>/ml/ to match the existing report tree.
"""
