"""One-command local demo. Scripted orchestration, NOT an LLM response."""
import json
from pathlib import Path
from generate_data import generate
from tools import Investigation, dispatch

ROOT = Path(__file__).resolve().parent

def main():
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
    out = ROOT/'outputs'; out.mkdir(exist_ok=True)
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
    print('Open data/*.csv and outputs/scripted_trace.json to inspect the calculations.')

if __name__ == '__main__': main()
