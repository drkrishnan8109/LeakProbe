LeakProbe diagrams

The hand-drawn workflow and status diagrams are archived illustrations of an earlier demo. They include a two-branch walkthrough and sparse/full comparisons; they are not current workflow or benchmark references. Use `outputs/evaluations/net3_full_pipes_comparison.md` for current full-channel high-signal metrics.

leakprobe-workflow-hand-drawn.png is the original workflow illustration showing the full data and tool-call flow. Keep it as the precise workflow reference. Its generation prompt is in generation-prompt.txt.

leakprobe-current-status-hand-drawn.png is an older status summary for the prior 500-case benchmark. Do not rebuild or present it as current. The original builder reports the old rejection threshold and sparse/full cutoffs.

    python outputs/diagrams/build_leakprobe_workflow_diagram.py

Both images describe generated benchmark results, not field performance.

The planner uses pressure spread across leading scenarios as a simple heuristic. It is not a formal expected-information-gain method.
