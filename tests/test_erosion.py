import pytest
import numpy as np
import pandas as pd
import pysand.exceptions as exc
import logging
from pysand.erosion import validate_inputs, bend, tee, straight_pipe, welded_joint, manifold, reducer, probes

def test_validate_inputs(caplog):

    # Testing input throws exception throws exception
    kwargs = {'v_m': 29.3, 'rho_m': 30, 'mu_m': 1.5e-5, 'Q_s': 2400*1000/86400/365}
    for inp in ['v_m', 'rho_m', 'mu_m', 'Q_S']:
        for non_number in [None, 'string', np.nan]:
            kwargs[inp] = non_number
            with pytest.raises(exc.FunctionInputFail) as excinfo:
                validate_inputs(**kwargs)

    # Test v_m boundaries
    kwargs = {'v_m': 1}
    for illegal_input in [-1, 201]:
        kwargs['v_m'] = illegal_input
        with caplog.at_level(logging.WARNING):
            validate_inputs(**kwargs)
            info = [record for record in caplog.records if record.levelname == 'WARNING']
            assert any(
                "Mix velocity, v_m, is outside RP-O501 model boundaries (0-200 m/s)."
                in s.message for s in info)

    # Test rho_m boundaries
    kwargs = {'rho_m': 1}
    for illegal_input in [-1, 1555]:
        kwargs['rho_m'] = illegal_input
        with caplog.at_level(logging.WARNING):
            validate_inputs(**kwargs)
            info = [record for record in caplog.records if record.levelname == 'WARNING']
            assert any(
                "Mix density, rho_m, is outside RP-O501 model boundaries (1-1500 kg/m3)."
                in s.message for s in info)

    # Test mu_m boundaries
    kwargs = {'mu_m': 1e-3}
    for illegal_input in [-1, 1]:
         kwargs['mu_m'] = illegal_input
         with caplog.at_level(logging.WARNING):
             validate_inputs(**kwargs)
             info = [record for record in caplog.records if record.levelname == 'WARNING']
             assert any(
                 "Mix viscosity, mu_m, is outside RP-O501 model boundaries (1e-6 - 1e-2 kg/ms)."
                 in s.message for s in info)

    # Test Q_s boundaries
    kwargs = {'Q_s': 1}
    for illegal_input in [-1, 555]:
        kwargs['Q_s'] = illegal_input
        with caplog.at_level(logging.WARNING):
            validate_inputs(**kwargs)
            info = [record for record in caplog.records if record.levelname == 'WARNING']
            assert any(
                "Sand production rate, Q_s, is outside RP-O501 model boundaries ( 0-500 ppmV)."
                in s.message for s in info)

    kwargs = {'R': 29.3, 'GF': 30, 'D': 1.5e-5, 'd_p': 1, 'h': 30, 'Dm': 30, 'D1': 30, 'D2': 30}
    for inp in ['R', 'GF', 'D', 'd_p', 'h', 'Dm', 'D1', 'D2']:
        for non_number in [None, 'string', np.nan, pd.Series().any()]:
            kwargs[inp] = non_number
            with pytest.raises(exc.FunctionInputFail) as excinfo:
                validate_inputs(**kwargs)

    # Test pipe inner diameter boundaries
    kwargs = {'D': 1, 'D1': 1, 'D2': 1}
    for inp in ['D', 'D1', 'D2']:
        for illegal_input in [0.005, 5]:
            kwargs[inp] = illegal_input
            with caplog.at_level(logging.WARNING):
                validate_inputs(**kwargs)
                info = [record for record in caplog.records if record.levelname == 'WARNING']
                assert any(
                    "Pipe inner diameter, {}, is outside RP-O501 model boundaries (0.01 - 1 m).".format(inp)
                    in s.message for s in info)

    # Test particle diameter boundaries
    kwargs = {'d_p': 1}
    for illegal_input in [0.01, 6]:
        kwargs['d_p'] = illegal_input
        with caplog.at_level(logging.WARNING):
            validate_inputs(**kwargs)
            info = [record for record in caplog.records if record.levelname == 'WARNING']
            assert any(
                "Particle diameter, d_p, is outside RP-O501 model boundaries (0.02 - 5 mm)." in s.message for s in info)

    # Test geometry factor limitations
    kwargs = {'GF': 6}
    with caplog.at_level(logging.WARNING):
        validate_inputs(**kwargs)
    assert "Geometry factor, GF, can only be 1, 2, 3 or 4" in str(caplog.records)

    # Test alpha boundaries
    kwargs = {'alpha': 1}
    for illegal_input in [-1, 91]:
        kwargs['alpha'] = illegal_input
        with caplog.at_level(logging.WARNING):
            validate_inputs(**kwargs)
            info = [record for record in caplog.records if record.levelname == 'WARNING']
            assert any(
                "Particle impact angle [degrees], alpha, is outside RP-O501 model boundaries (10-90 deg)."
                in s.message for s in info)

    # Test bend radius boundaries
    kwargs = {'R': 1}
    for illegal_input in [0.1, 51]:
        kwargs['R'] = illegal_input
        with caplog.at_level(logging.WARNING):
            validate_inputs(**kwargs)
            info = [record for record in caplog.records if record.levelname == 'WARNING']
            assert any(
                "Bend radius, R, is outside RP-O501 model boundaries." in s.message for s in info)

    # Test manifold diameter against branch pipe diameter
    kwargs = {'Dm': 0.5, 'D': 0.8}
    with caplog.at_level(logging.WARNING):
        validate_inputs(**kwargs)
    assert "Manifold diameter, Dm, is expected to be bigger than branch pipe diameter, D" in str(caplog.records)

    # Test height of the weld boundaries
    kwargs = {'h': 0.01, 'D': 0.8}
    for illegal_input in [-1, 1]:
        kwargs['h'] = illegal_input
        with caplog.at_level(logging.WARNING):
            validate_inputs(**kwargs)
            info = [record for record in caplog.records if record.levelname == 'WARNING']
            assert any(
                "Height of the weld, h, must positive number not exceeding pipe inner diameter size, D"
                in s.message for s in info)

# Pipe bends #
# Bend validation 1 based on the model validations in DNVGL RP-O501, Aug 2015
# Bend validation 2 to test all versions of gamma
# Bend validation 3 based on example in DNVGL RP-O501, Aug 2015, chapter 4.7
bend_validation = [(29.3, 30, 1.5e-5, 2400*1000/86400/365, 1.75, 1, 0.0978, 0.28, pytest.approx(0.6128002)),
                   (15, 2, 4e-4, .1, 1.5, 2, .1, .4, pytest.approx(0.0115661)),
                   (15, 333.3, 3.4e-4, 1e5/365/86400, 1.5, 1, 0.1, 0.25, pytest.approx(1.433187e-3))]
@pytest.mark.parametrize('v_m, rho_m, mu_m, Q_s, R, GF, D, d_p, E', bend_validation)
def test_bend(v_m, rho_m, mu_m, Q_s, R, GF, D, d_p, E):
    assert bend(v_m, rho_m, mu_m, Q_s, R, GF, D, d_p) == E  # mm/ton


# Blinded tees #
tee_validation = [(30, 400, 1e-3, .1, 2, 0.1, 0.3, pytest.approx(0.1704876))]
@pytest.mark.parametrize('v_m, rho_m, mu_m, Q_s, GF, D, d_p, E', tee_validation)
def test_tee(v_m, rho_m, mu_m, Q_s, GF, D, d_p, E):
    assert tee(v_m, rho_m, mu_m, Q_s, GF, D, d_p) == E


# Smooth and straight pipes #
pipe_validation = [(15, 4, 0.1, pytest.approx(0.0114245))]
@pytest.mark.parametrize('v_m, Q_s, D, E', pipe_validation)
def test_pipe(v_m, Q_s, D, E):
    assert straight_pipe(v_m, Q_s, D) == E


# Welded joints #
weld_validation = [(15, 150, 4, 0.1, 0.3, 0.023, (pytest.approx(2.72521), pytest.approx(0.358158))),
                   (30, 300, 4, 0.1, 0.8, 0.023, (pytest.approx(20.23594), pytest.approx(2.1714649)))]
@pytest.mark.parametrize('v_m, rho_m, Q_s, D, d_p, h, E', weld_validation)
def test_weld(v_m, rho_m, Q_s, D, d_p, h, E):
    assert welded_joint(v_m, rho_m, Q_s, D, d_p, h) == E


# Manifolds #
manifold_validation = [(29.3, 30, 1.5e-5, 2400*1000/86400/365, 1, 0.0978, 0.28, 0.2, pytest.approx(0.6476766)),
                       (30, 1.2, 1.5e-5, 9700*1000/86400/365, 1, 0.128, 0.25, 0.2, pytest.approx(1.8785739))]
@pytest.mark.parametrize('v_m, rho_m, mu_m, Q_s, GF, D, d_p, Dm, E', manifold_validation)
def test_manifold(v_m, rho_m, mu_m, Q_s, GF, D, d_p, Dm, E):
    assert manifold(v_m, rho_m, mu_m, Q_s, GF, D, d_p, Dm) == E


# Reducers #
reducer_validation = [(20, 80, 1, 0.15, 0.1, 0.3, 1, 50, pytest.approx(6.3947669)),
                      (20, 120, 1, 0.15, 0.1, 0.3, 1, 50, pytest.approx(5.8375968))]
@pytest.mark.parametrize('v_m, rho_m, Q_s, D1, D2, d_p, GF, alpha, E', reducer_validation)
def test_reducer(v_m, rho_m, Q_s, D1, D2, d_p, GF, alpha, E):
    assert reducer(v_m, rho_m, Q_s, D1, D2, d_p, GF, alpha) == E


# Erosion probes #
probe_validation = [(30, 80, 1, 0.15, 0.3, 50, pytest.approx(2.22837)),
                      (20, 120, 0.1, 0.15, 0.3, 30, pytest.approx(0.0494802))]
@pytest.mark.parametrize('v_m, rho_m, Q_s, D, d_p, alpha, E', probe_validation)
def test_probes(v_m, rho_m, Q_s, D, d_p, alpha, E):
    assert probes(v_m, rho_m, Q_s, D, d_p, alpha) == E