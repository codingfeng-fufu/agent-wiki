# Raw Example Sources

This directory contains public, synthetic source documents that demonstrate what
LLM Wiki expects raw evidence to look like.

These files are not part of the active source registry and are not an ingest
queue. To try an ingest flow, copy one file into `raw/inbox/` and register it:

```bash
cp raw/examples/agent-memory-design-note.md raw/inbox/
llmw source add raw/inbox/agent-memory-design-note.md
llmw ingest packet <source_id>
```

The release package intentionally excludes raw example content. The GitHub
repository includes these files so visitors can inspect the expected source
shape without needing private data.

Chinese examples are available in [`zh-CN/`](zh-CN/README.md).
