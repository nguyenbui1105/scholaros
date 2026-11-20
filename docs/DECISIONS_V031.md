# v0.3.1 research decisions

1. We will not claim to have collected or legally reused 50–100 live scholarship pages when robots/terms/provider rights are not checked.
2. We will not fabricate two independent reviewers; unresolved cases remain unscored. Double-human labeling and third adjudication are required for disputed labels.
3. Model predictions and human gold are separate inputs and must not be derived from one another.
4. A source content hash authenticates **bytes**, not the institutional author. Quotes cannot automatically establish scholarship rule meaning.
5. A real source **index** with hundreds of individual listings is one URL, not hundreds of independently collected pages.
6. Missing ground truth makes accuracy **undefined** (JSON null), not 100%.
7. Offline latency/throughput and LLM cost estimates are never marketed as live production latency or real API costs.
8. Captured public HTML is stored locally, not bundled in the open-source repository without licensing rights.
