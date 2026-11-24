# Troubleshooting without overwriting evidence

| Observation | Interpretation and next action |
|---|---|
| Output directory already exists | The command must fail before replacing evidence. Preserve that directory and choose a new path for a separately identified attempt. |
| Kit manifest is absent or mismatched | Use the complete sealed candidate. Do not disable verification for a reviewer result. The explicit unsealed option is internal development evidence only. |
| A child times out | Read its receipt and retained logs. The timeout is a failure observation; do not extend limits automatically or silently rerun. |
| Summary reports missing or unstarted checks | Report the incomplete scope. Planned counts are not completed counts. |
| A checker returns REJECT or INDETERMINATE | These are normal semantic reports. The test expectation decides whether the check passes; process exit alone is insufficient. |
| Alias control fails | Compare the exact source_pointer token and aliases key with profiles/ALIAS_GRAMMAR_V1.json. Alias resolution is one hop and must end in a direct pointer. Preserve raw inputs and reports. |
| Another Python version fails | Retain executable/version, command and logs. The available executed profile does not imply support for untested minor versions. |
| Windows cleanup differs | Native Windows is unqualified. A direct-child fallback is not proof of process-tree containment. |
| A hash differs after editing a file | The edited tree is a new candidate. Do not present it as the original sealed kit or change the earlier manifest to conceal the difference. |

The accompanying data archive contains the retained qualification history; the software distribution provides the current executable sources and reviewer commands. Historical absolute execution paths identify the environment in which evidence was produced; they are not portable command paths.
