"""Experimental Amber heating-only virtual flow; independent of reported COP."""
import argparse
import csv
import json
import math

import numpy as np

MODELS = {'amber65', 'amber95', 'amber120'}
FEATURES = ('frequency_hz', 'outside_c', 'supply_c', 'power_w')


def number(row, key):
    value = float(row[key])
    if not math.isfinite(value):
        raise ValueError(key)
    return value


def inputs(row):
    if row.get('power_source') != 'metered':
        raise ValueError('external metered active power required in v1')
    if row.get('mode') != 'heating' or str(row.get('defrost')) != '0' or str(row.get('buh')) != '0' or str(row.get('steady')) != '1':
        raise ValueError('not confirmed steady compressor-only heating')
    if row.get('model') not in MODELS:
        raise ValueError('unsupported model')
    x = [number(row, k) for k in FEATURES]
    delta = x[2] - number(row, 'return_c')
    if x[0] <= 0 or x[3] <= 0 or delta < 2:
        raise ValueError('invalid operating point or delta T below 2 K')
    return x, delta


def matrix(x):
    return np.column_stack((np.ones(len(x)), x))


def fit(rows, model):
    """Leave one complete installation out; fit a log-power baseline on the rest."""
    if model not in MODELS:
        raise ValueError('unsupported model')
    samples = []
    for row in rows:
        if row.get('model') != model:
            continue
        try:
            x, delta = inputs(row)
            flow = number(row, 'measured_flow_lh')
            factor = number(row, 'water_factor')
            if flow <= 0 or factor <= 0 or not row.get('installation_id'):
                continue
            samples.append((x, delta, flow, factor, row['installation_id']))
        except (KeyError, ValueError, TypeError):
            continue
    groups = sorted({s[4] for s in samples})
    if not groups or any(sum(s[4] == g for s in samples) < 30 for g in groups):
        raise ValueError('need >=30 eligible rows per installation; not a validation guarantee')
    X = np.array([s[0] for s in samples]); y = np.log([s[1]*s[2]*s[3] for s in samples])
    ids = np.array([s[4] for s in samples]); flow = np.array([s[2] for s in samples])
    denom = np.array([s[1]*s[3] for s in samples])

    def train(mask):
        xx = X[mask]; mean = xx.mean(axis=0); scale = xx.std(axis=0)
        scale[scale == 0] = 1
        a = matrix((xx-mean)/scale)
        penalty = np.diag([0., 1., 1., 1., 1.])
        # Equal total weight per installation, independent of sampling duration.
        w = np.array([1 / np.sum(ids[mask] == g) for g in ids[mask]])
        w *= len(w)/w.sum()
        beta = np.linalg.solve(a.T @ (w[:,None]*a) + penalty, a.T @ (w*y[mask]))
        return mean, scale, beta, xx.min(axis=0), xx.max(axis=0)

    reports = []; errors = []
    for g in groups if len(groups) > 1 else []:
        test = ids == g
        mean, scale, beta, lo, hi = train(~test)
        inside = test & np.all((X >= lo) & (X <= hi), axis=1)
        err = np.exp(matrix((X[inside]-mean)/scale) @ beta)/denom[inside]/flow[inside] - 1
        reports.append({'installation_id':g, 'eligible_rows':int(test.sum()), 'predicted_rows':int(inside.sum()), 'mae_pct':float(np.mean(abs(err))*100) if len(err) else None, 'bias_pct':float(np.mean(err)*100) if len(err) else None})
        if len(err):
            errors.append(float(np.quantile(abs(err), .9)))
    mean, scale, beta, lo, hi = train(np.ones(len(X), dtype=bool))
    return {'version':1, 'model':model, 'features':list(FEATURES), 'mean':mean.tolist(), 'scale':scale.tolist(), 'beta':beta.tolist(), 'min':lo.tolist(), 'max':hi.tolist(), 'installation_count':len(groups), 'validation':reports, 'error_fraction_p90_worst_installation':max(errors) if len(errors)==len(groups) else None}


def predict(row, artifact):
    """Return a separate estimate; never overwrite measured flow or authorize control."""
    try:
        if artifact['version'] != 1 or artifact['features'] != list(FEATURES) or row.get('model') != artifact['model']:
            raise ValueError('model mismatch')
        x, delta = inputs(row)
        x = np.array(x)
        if not np.all((x >= artifact['min']) & (x <= artifact['max'])):
            raise ValueError('outside training range')
        factor = number(row, 'water_factor')
        if factor <= 0:
            raise ValueError('invalid water factor')
        p = math.exp(float(np.r_[1., (x-artifact['mean'])/artifact['scale']] @ artifact['beta']))
        flow = p/(factor*delta)
        if not math.isfinite(flow):
            raise ValueError('invalid prediction')
        return {'source':'virtual_experimental', 'flow_lh':flow, 'thermal_w':p, 'cop_estimated':p/x[3], 'validation_error_fraction':artifact['error_fraction_p90_worst_installation'], 'reason':None}
    except (ValueError, KeyError, TypeError, OverflowError) as exc:
        return {'source':'unavailable', 'flow_lh':None, 'reason':str(exc)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['fit','predict'])
    parser.add_argument('csv_path')
    parser.add_argument('--model', choices=sorted(MODELS))
    parser.add_argument('--artifact', required=True)
    args = parser.parse_args()
    with open(args.csv_path, newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    if args.action == 'fit':
        result = fit(rows, args.model)
        with open(args.artifact, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, allow_nan=False)
    else:
        with open(args.artifact, encoding='utf-8') as f:
            artifact = json.load(f)
        for row in rows:
            print(json.dumps(predict(row, artifact), allow_nan=False))


if __name__ == '__main__':
    main()
