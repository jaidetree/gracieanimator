# CLAUDE

See [AGENTS.md](./AGENTS.md) for agent skills configuration (issue tracker, triage labels, domain docs).

## Session Protocol

At the start of each session:

1. Run scan-knowledge.sh .gracie-vault/Knowledge (from the knowledge skill) to
   list hooks
2. Open only the notes relevant to the current task

At the end of each task or session:

1. Record new patterns, mistakes, domain knowledge, or open questions as
   standalone notes in .gracie-vault/Knowledge/ via the knowledge skill
2. Never edit another note's history — correct with a dated note
