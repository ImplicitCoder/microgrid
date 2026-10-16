from dataclasses import dataclass
from math import sqrt


@dataclass(frozen=True, slots=True)
class Battery:
    """Battery energy storage with symmetric charge/discharge efficiency.

    Power sign convention (generator-style): positive = discharging to the
    microgrid bus, negative = charging from it.
    """

    capacity_kwh: float
    max_power_kw: float
    round_trip_efficiency: float = 0.90
    soc_min: float = 0.10
    soc_max: float = 0.95

    def __post_init__(self) -> None:
        if self.capacity_kwh <= 0 or self.max_power_kw <= 0:
            raise ValueError("capacity and max power must be positive")
        if not 0 < self.round_trip_efficiency <= 1:
            raise ValueError("round-trip efficiency must be in (0, 1]")
        if not 0 <= self.soc_min < self.soc_max <= 1:
            raise ValueError("require 0 <= soc_min < soc_max <= 1")

    @property
    def one_way_efficiency(self) -> float:
        # Splitting the round trip evenly: eta_charge * eta_discharge = eta_rt.
        return sqrt(self.round_trip_efficiency)

    @property
    def min_energy_kwh(self) -> float:
        return self.soc_min * self.capacity_kwh

    @property
    def max_energy_kwh(self) -> float:
        return self.soc_max * self.capacity_kwh

    def step(
        self, stored_kwh: float, requested_kw: float, dt_hours: float
    ) -> tuple[float, float]:
        """Advance one time step.

        Returns ``(new_stored_kwh, delivered_kw)``. ``delivered_kw`` is the power
        actually exchanged at the bus after applying power, energy, and SoC limits,
        so it may be smaller in magnitude than ``requested_kw``.
        """
        eta = self.one_way_efficiency

        if requested_kw >= 0:
            available_kw = (stored_kwh - self.min_energy_kwh) * eta / dt_hours
            delivered_kw = max(0.0, min(requested_kw, self.max_power_kw, available_kw))
            return stored_kwh - delivered_kw * dt_hours / eta, delivered_kw

        headroom_kw = (self.max_energy_kwh - stored_kwh) / (eta * dt_hours)
        absorbed_kw = max(0.0, min(-requested_kw, self.max_power_kw, headroom_kw))
        return stored_kwh + absorbed_kw * dt_hours * eta, -absorbed_kw
