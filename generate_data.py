"""Create reproducible synthetic fixtures; not a blind scientific benchmark."""
import json
from pathlib import Path
import numpy as np
from simulator import simulate

ROOT = Path(__file__).resolve().parent

def generate():
    data = ROOT / 'data'
    data.mkdir(exist_ok=True)
    for scenario in ('normal', 'leak_A', 'leak_B'):
        simulate(scenario).to_csv(data / f'prediction_{scenario}.csv', index=False)
    # Hidden-to-tools example truth: branch A, same solver, mild sensor noise.
    # This is deliberately easy. Do not claim sim-to-real validation.
    truth = simulate('leak_A')
    rng = np.random.default_rng(7)
    observed = truth[['timestamp_utc','F01_flow_lps','P01_pressure_m']].copy()
    observed['F01_flow_lps'] += rng.normal(0, .03, len(observed))
    observed['P01_pressure_m'] += rng.normal(0, .03, len(observed))
    observed.to_csv(data / 'observations.csv', index=False)
    # The tool reveals only the point selected within the measurement budget.
    fields = {point: {'pressure_head_m': round(float(truth[f'{point}_pressure_m'].iloc[-1])+.03,6),
                      'timestamp_utc':'2026-10-01T03:00:00Z',
                      'provenance':'synthetic measurement; steady conditions after 02:20 assumed'}
              for point in ('MA','MB')}
    (data/'demo_measurements.json').write_text(json.dumps(fields, indent=2), encoding='utf-8')
    notes = [
        {'id':'OP01','branch':'B','window':'02:15-03:00 UTC','text':'Flushing scheduled; execution not confirmed.'},
        {'id':'OP03','related_to':'OP01','timestamp':'01:55 UTC','text':'Flushing cancelled; crew reassigned.'},
    ]
    (data/'operations.json').write_text(json.dumps(notes, indent=2), encoding='utf-8')
    print('Generated 3 prediction CSVs, observations.csv, and 2 JSON fixtures in data/.')

if __name__ == '__main__': generate()
