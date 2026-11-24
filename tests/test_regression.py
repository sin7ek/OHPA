import numpy as np
import pytest
import regression
def test_hac_fit():
    x=np.arange(48,dtype=float)/4+5
    y=0.4*x-0.3+0.1*np.sin(x)
    m=regression.fit(y,[x],['delta_t'],np.arange(48)*3600)
    assert m['heat_loss_w_per_k']==pytest.approx(400,abs=15)
    assert m['heat_loss_ci95_w_per_k'][0]<=m['heat_loss_w_per_k']<=m['heat_loss_ci95_w_per_k'][1]
    assert len(m['predicted_kw'])==48
def test_rank_failure():
    x=np.arange(48,dtype=float)
    assert regression.fit(x,[x,x],['delta_t','wind'],np.arange(48)*3600) is None

def test_diagnostics_and_interaction():
    x=np.linspace(6,22,240);w=2+np.sin(np.arange(240)*.2)
    y=1+.2*x+.1*w+.03*x*w
    cols=[x,w,x*w];names=['delta_t','wind','delta_wind'];times=np.arange(240)*3600
    m=regression.fit(y,cols,names,times)
    assert m['coefficients']['delta_wind']==pytest.approx(.03)
    d=regression.diagnostics(y,cols,names,times,m)
    assert d['cv']['rmse_kw']<.001
    assert d['cv']['test_hours']>0
    assert len(d['correlations']['matrix'])==4
    assert d['residual_acf'][0]['pairs']==239
    assert len(d['rolling_7d'])>0
