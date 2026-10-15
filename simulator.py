"""A small forward hydraulic model. All scenarios are synthetic, not field data."""
import math
import pandas as pd
import wntr

SCENARIOS = ('normal', 'leak_A', 'leak_B')
START = pd.Timestamp('2026-10-01T02:00:00Z')


def build_network():
    """SI units: meters, cubic meters/second, seconds."""
    net = wntr.network.WaterNetworkModel()
    net.options.time.duration = 2700
    net.options.time.hydraulic_timestep = 300
    net.options.time.report_timestep = 300
    net.options.hydraulic.demand_model = 'PDD'
    net.options.hydraulic.minimum_pressure = 0
    net.options.hydraulic.required_pressure = 20
    net.options.hydraulic.pressure_exponent = 0.5
    net.options.hydraulic.headloss = 'H-W'
    net.add_reservoir('R0', base_head=42, coordinates=(0, 1))
    for name, demand, coords in [('J1', 0, (0, 0)), ('J2', .005, (-1, -1)), ('J3', .005, (1, -1))]:
        net.add_junction(name, base_demand=demand, elevation=0, coordinates=coords)
    for name, start, end, length, diameter in [('P0','R0','J1',200,.15), ('PA','J1','J2',300,.1), ('PB','J1','J3',300,.1)]:
        net.add_pipe(name, start, end, length=length, diameter=diameter, roughness=130)
    return net


def simulate(scenario='normal', hole_diameter_mm=16.0):
    """Return ten predicted readings. Leak starts at 1200 seconds (02:20)."""
    if scenario not in SCENARIOS:
        raise ValueError(f'Scenario must be one of {SCENARIOS}')
    if isinstance(hole_diameter_mm, bool) or not math.isfinite(hole_diameter_mm) or not 0 < hole_diameter_mm <= 30:
        raise ValueError('Hole diameter must be finite and between 0 and 30 mm.')
    net = build_network()
    if scenario != 'normal':
        pipe = 'PA' if scenario == 'leak_A' else 'PB'
        net = wntr.morph.split_pipe(net, pipe, f'{pipe}_SECOND', 'LEAK', split_at_point=.5)
        net.get_node('LEAK').add_leak(net, area=math.pi*(hole_diameter_mm/2000)**2,
                                    discharge_coeff=.75, start_time=1200)
    results = wntr.sim.WNTRSimulator(net).run_sim(convergence_error=True)
    pressure, flow = results.node['pressure'], results.link['flowrate']
    return pd.DataFrame({
        'timestamp_utc': START + pd.to_timedelta(pressure.index, unit='s'),
        'F01_flow_lps': flow['P0'].to_numpy()*1000,
        'P01_pressure_m': pressure['J1'].to_numpy(),
        'MA_pressure_m': pressure['J2'].to_numpy(),
        'MB_pressure_m': pressure['J3'].to_numpy(),
    })
