LeakProbe diagrams

leakprobe-workflow-hand-drawn.png is the original workflow illustration showing the full data and tool-call flow. Keep it as the precise workflow reference. Its generation prompt is in generation-prompt.txt.

leakprobe-current-status-hand-drawn.png is the status summary for the current 500-case benchmark. Rebuild it with:

    python outputs/diagrams/build_leakprobe_workflow_diagram.py

It reports the full-observation held-out rejection-threshold results and the distinct sparse/full cutoffs. The builder writes only to the current-status filename so it does not replace the original workflow image. Both diagrams describe generated benchmark results, not field performance.

The planner uses pressure spread across leading scenarios as a simple heuristic. It is not a formal expected-information-gain method.
