# Full-channel high-signal data and workbench

## Completed in this change

- [x] Make the 500-case high-signal Net3 feed the only active dataset.
- [x] Require exactly 92 pressure and 117 flow columns for cases, comparisons, evaluation, and classifier features.
- [x] Regenerate the high-signal observations with the existing case IDs, split, and candidate-pipe assignments.
- [x] Build a full-channel reference bank using the same high-signal parameter ranges.
- [x] Remove the two-branch and sparse Net3 paths from the CLI and Streamlit app.
- [x] Rerun the saved recall-led classifier benchmark on the full-channel high-signal data.
- [x] Update user documentation to identify the sole active data source.

## Next requested UI work

- [ ] Present an employee workflow and alert-dashboard plan for review.
- [ ] Wait for approval of that plan before changing the broader dashboard flow.

## Hosting

- [ ] Complete Streamlit Community Cloud setup for the authorized repository.
- [ ] Verify the hosted URL after deployment.
