"""Fixes for EC-Earth3 model."""
from ..fix import Fix


class siconca(Fix):
    """Fixes for siconca."""

    def fix_data(self, cube):
        """
        Fix data.

        Fixes discrepancy between declared units and real units

        Parameters
        ----------
        cube: iris.cube.Cube

        Returns
        -------
        iris.cube.Cube

        """
        cube.data = cube.core_data() * 100.
        return cube