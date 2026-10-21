"""Create reproducible synthetic fixtures; not a blind scientific benchmark."""
import json
import argparse
import numpy as np
from .simulator import simulate
from .paths import DEMO_DATA

def generate():
    data = DEMO_DATA
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
    print('Generated demo prediction CSVs, observations.csv, and JSON fixtures in data/demo/.')

def main():
    parser = argparse.ArgumentParser(description='Generate the small demo or Net3 synthetic dataset.')
    parser.add_argument('--network', choices=('demo', 'net3'), default='demo')
    parser.add_argument('--cases', type=int, default=32, help='Total number of Net3 cases (at least 4).')
    parser.add_argument('--train-fraction', type=float, default=0.8,
                        help='Fraction of Net3 cases assigned to training (default: 0.8).')
    parser.add_argument('--seed', type=int, default=None, help='Reproducible Net3 generation seed.')
    parser.add_argument('--patterns-per-scenario', type=int, default=200,
                        help='Reference simulations per leak pipe and for normal operation (default: 200).')
    parser.add_argument('--patterns-only', action='store_true',
                        help='Refresh Net3 reference simulations while preserving existing cases.')
    args = parser.parse_args()
    if args.network == 'net3':
        from .net3_benchmark import generate_dataset, generate_hypotheses_only
        if args.patterns_only:
            generate_hypotheses_only(args.patterns_per_scenario, seed=args.seed)
        else:
            generate_dataset(case_count=args.cases,
                             seed=args.seed if args.seed is not None else 2026,
                             train_fraction=args.train_fraction,
                             patterns_per_scenario=args.patterns_per_scenario)
    else:
        if args.patterns_only:
            parser.error('--patterns-only requires --network net3.')
        generate()


if __name__ == '__main__':
    main()
