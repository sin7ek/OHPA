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
