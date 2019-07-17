"""Derivation of variable `SHIP_SO2_s`.

The variable 'SHIP_SO2_s' is an EMAC variable that is used for monitoring EMAC
output. It is here summed over all available levels. The variable is stored in
the EMAC CMIP6 channel 'import_grid'.

SHIP_SO2_s: Ship SO2, summed.

"""

from scipy.constants import N_A

from ._shared import sum_over_level


def derive(cubes):
    """Derive `SHIP_SO2_s`."""
    molar_mass_so2 = 64.066  # g mol-1
    mass_per_molecule_so2 = molar_mass_so2 / N_A * 1e-3  # kg
    return sum_over_level(cubes,
                          'SHIP_SO2',
                          scale_factor=mass_per_molecule_so2)
