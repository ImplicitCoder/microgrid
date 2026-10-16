import pytest

from microgrid.components import Battery


@pytest.fixture
def battery() -> Battery:
    return Battery(capacity_kwh=10.0, max_power_kw=5.0, round_trip_efficiency=0.81)


def test_discharge_is_limited_by_max_power(battery: Battery) -> None:
    _, delivered = battery.step(stored_kwh=9.0, requested_kw=20.0, dt_hours=0.25)
    assert delivered == pytest.approx(5.0)


def test_discharge_stops_at_minimum_soc(battery: Battery) -> None:
    new_stored, delivered = battery.step(stored_kwh=1.0, requested_kw=5.0, dt_hours=1.0)
    assert delivered == pytest.approx(0.0)
    assert new_stored == pytest.approx(battery.min_energy_kwh)


def test_charge_is_limited_by_headroom(battery: Battery) -> None:
    new_stored, delivered = battery.step(
        stored_kwh=9.0, requested_kw=-5.0, dt_hours=1.0
    )
    assert new_stored == pytest.approx(battery.max_energy_kwh)
    assert delivered < 0


def test_round_trip_loses_energy_as_specified(battery: Battery) -> None:
    start_kwh = 2.0
    stored, charged_kw = battery.step(start_kwh, requested_kw=-2.0, dt_hours=1.0)
    energy_in_kwh = -charged_kw * 1.0

    # Discharge exactly the energy needed to return to the starting state of charge.
    one_way = battery.one_way_efficiency
    discharge_kw = (stored - start_kwh) * one_way
    final, delivered_kw = battery.step(stored, requested_kw=discharge_kw, dt_hours=1.0)

    assert final == pytest.approx(start_kwh)
    assert delivered_kw / energy_in_kwh == pytest.approx(battery.round_trip_efficiency)


def test_invalid_soc_window_is_rejected() -> None:
    with pytest.raises(ValueError, match="soc_min"):
        Battery(capacity_kwh=10, max_power_kw=5, soc_min=0.9, soc_max=0.5)
