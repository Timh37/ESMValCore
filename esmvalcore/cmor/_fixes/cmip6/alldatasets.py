"""Fixes for all datasets """
from ..shared import add_scalar_height_coord
from ..fix import Fix
import iris

class Abs550aer(Fix):
    """Fixes for abs550aer"""
    def fix_metadata(self, cubes):
        """
        Fix missing scalar dimension lambda550nm
        Parameters
        ----------
        cubes: iris CubeList
            List of cubes to fix
        Returns
        -------
        iris.cube.CubeList
        """
        lambda550nm = iris.coords.AuxCoord(550.0,
                                         standard_name='radiation_wavelength',
                                         long_name='Radiation Wavelength 550 nanometers',
                                         var_name='wavelength',
                                         units='nm',
                                         bounds=None)
        for cube in cubes:
            try:
                cube.add_aux_coord(lambda550nm)
            except ValueError:
                pass
        return cubes

class Od550aer(Fix):
    """Fixes for od550aer"""
    def fix_metadata(self, cubes):
        """
        Fix missing scalar dimension lambda550nm
        Parameters
        ----------
        cubes: iris CubeList
            List of cubes to fix
        Returns
        -------
        iris.cube.CubeList
        """
        lambda550nm = iris.coords.AuxCoord(550.0,
                                         standard_name='radiation_wavelength',
                                         long_name='Radiation Wavelength 550 nanometers',
                                         var_name='wavelength',
                                         units='nm',
                                         bounds=None)
        for cube in cubes:
            try:
                cube.add_aux_coord(lambda550nm)
            except ValueError:
                pass
        return cubes

class Od550lt1aer(Fix):
    """Fixes for od550lt1aer"""
    def fix_metadata(self, cubes):
        """
        Fix missing scalar dimension lambda550nm
        Parameters
        ----------
        cubes: iris CubeList
            List of cubes to fix
        Returns
        -------
        iris.cube.CubeList
        """
        lambda550nm = iris.coords.AuxCoord(550.0,
                                         standard_name='radiation_wavelength',
                                         long_name='Radiation Wavelength 550 nanometers',
                                         var_name='wavelength',
                                         units='nm',
                                         bounds=None)
        for cube in cubes:
            try:
                cube.add_aux_coord(lambda550nm)
            except ValueError:
                pass
        return cubes

class Mrsos(Fix):
    """Fixes for Mrsos"""
    def fix_metadata(self, cubes):
        """
        Fix missing scalar dimension sdepth1
        Parameters
        ----------
        cubes: iris CubeList
            List of cubes to fix
        Returns
        -------
        iris.cube.CubeList
        """
        sdepth1 = iris.coords.AuxCoord(0.05,
                                         standard_name='depth',
                                         long_name='depth',
                                         var_name='depth',
                                         units='m',
                                         bounds=[0.0, 0.1])
        for cube in cubes:
            try:
                cube.coord("depth")
            except iris.exceptions.CoordinateNotFoundError:
                cube.add_aux_coord(sdepth1)
        return cubes
