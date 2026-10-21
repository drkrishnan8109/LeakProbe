"""LeakProbe entry point: live Nemotron by default; --scripted runs offline."""
import argparse
import json
from .generate_data import generate
from .tools import Investigation, dispatch
from .paths import ROOT, OUTPUTS


def run_scripted_demo():
    generate()
    session = Investigation()
    trace = []
    for name, args in [('get_observations',{}), ('get_network',{}), ('get_operation_records',{}),
                       ('compare_hypotheses',{}), ('recommend_measurement',{})]:
        result = dispatch(session,name,args)
        trace.append({'tool':name,'arguments':args,'result':result})
    point = trace[-1]['result']['recommended']
    if point:
        result = dispatch(session,'collect_demo_measurement',{'point':point})
        trace.append({'tool':'collect_demo_measurement','arguments':{'point':point},'result':result})
    after = dispatch(session,'compare_hypotheses',{})
    trace.append({'tool':'compare_hypotheses','arguments':{},'result':after})
    out = OUTPUTS/'traces'; out.mkdir(parents=True, exist_ok=True)
    (out/'scripted_trace.json').write_text(json.dumps(trace,indent=2), encoding='utf-8')
    print('\nSCRIPTED LOCAL DEMO — no LLM or API calls')
    print('\nBefore measurement:')
    for row in trace[3]['result']['ranking']:
        print(f"  {row['scenario']}: normalized RMSE {row['normalized_rmse']:.4f}")
    print(f'\nRecommended point: {point}')
    if point: print(f"Synthetic reading: {session.revealed[point]['pressure_head_m']:.3f} m")
    print('\nAfter measurement:')
    for row in after['ranking']:
        print(f"  {row['scenario']}: normalized RMSE {row['normalized_rmse']:.4f}")
    print('\nLower RMSE is better fit, NOT confidence. Synthetic branch evidence is not field confirmation.')
    print('Open data/demo/*.csv and outputs/traces/scripted_trace.json to inspect the calculations.')


def run_scripted_net3(case_id=None):
    from .net3_benchmark import generate_dataset, OUT
    from .net3_tools import Net3Investigation, dispatch_net3
    if not (OUT/'metadata.json').exists():
        generate_dataset()
    session = Net3Investigation(case_id)
    trace = []
    for name in ('get_observations','get_network','get_operation_records','compare_hypotheses','recommend_measurement'):
        result = dispatch_net3(session, name, {})
        trace.append({'tool':name,'arguments':{},'result':result})
    point = trace[-1]['result']['recommended']
    if point:
        result = dispatch_net3(session, 'collect_demo_measurement', {'point':point})
        trace.append({'tool':'collect_demo_measurement','arguments':{'point':point},'result':result})
    after = dispatch_net3(session, 'compare_hypotheses', {})
    trace.append({'tool':'compare_hypotheses','arguments':{},'result':after})
    output = OUTPUTS/'traces'; output.mkdir(parents=True, exist_ok=True)
    path = output/f'net3_{session.case_id}_scripted_trace.json'
    path.write_text(json.dumps(trace,indent=2), encoding='utf-8')
    print(f'\nSCRIPTED NET3 DEMO — no LLM or API calls — {session.case_id}')
    def shown(rows):
        visible = rows[:5]
        normal = next((row for row in rows if row['scenario'] == 'normal'), None)
        if normal and normal not in visible:
            visible.append(normal)
        return visible
    print('Before measurement:')
    for row in shown(trace[3]['result']['ranking']):
        label = 'normal' if row['scenario'] == 'normal' else f"pipe {row['leak_pipe']}"
        print(f"  {label}: normalized RMSE {row['normalized_rmse']:.3f}")
    if trace[3]['result']['leading_scenarios_are_close']:
        print('  Leading fits are close; the pipe ranking is ambiguous.')
    print(f'\nRecommended pressure point: {point}')
    if point:
        print(f"Synthetic reading: {session.revealed[point]['pressure_head_m']:.3f} m")
        print('\nAfter measurement:')
        for row in shown(after['ranking']):
            label = 'normal' if row['scenario'] == 'normal' else f"pipe {row['leak_pipe']}"
            print(f"  {label}: normalized RMSE {row['normalized_rmse']:.3f}")
        if after['leading_scenarios_are_close']:
            print('  Leading fits are close; the pipe ranking is ambiguous.')
    print('\nScores rank candidate pipes in the test set. They are not probabilities or field confirmation.')
    print(f'Open {path.relative_to(ROOT)} and data/net3/ to inspect the evidence.')


def main():
    parser = argparse.ArgumentParser(description='Investigate a synthetic water network with Nemotron.')
    parser.add_argument('--network', choices=('demo','net3'), default='demo')
    parser.add_argument('--case', help='Net3 case id; defaults to the first held-out test case.')
    parser.add_argument('--scripted', action='store_true', help='Run offline without an LLM API call.')
    args = parser.parse_args()
    if args.scripted:
        if args.network == 'demo':
            run_scripted_demo()
        else:
            run_scripted_net3(args.case)
    else:
        from .agent import run_live
        run_live(network=args.network, case_id=args.case)


if __name__ == '__main__': main()
