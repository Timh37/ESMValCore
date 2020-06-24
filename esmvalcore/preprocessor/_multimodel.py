"""multimodel statistics.

Functions for multi-model operations
supports a multitude of multimodel statistics
computations; the only requisite is the ingested
cubes have (TIME-LAT-LON) or (TIME-PLEV-LAT-LON)
dimensions; and obviously consistent units.

It operates on different (time) spans:
- full: computes stats on full dataset time;
- overlap: computes common time overlap between datasets;

"""

import logging
from datetime import datetime
from functools import reduce

import cf_units
import iris
import numpy as np

logger = logging.getLogger(__name__)


def _plev_fix(dataset, pl_idx):
    """Extract valid plev data.

    this function takes care of situations
    in which certain plevs are completely
    masked due to unavailable interpolation
    boundaries.
    """
    if np.ma.is_masked(dataset):
        # keep only the valid plevs
        if not np.all(dataset.mask[pl_idx]):
            statj = np.ma.array(dataset[pl_idx], mask=dataset.mask[pl_idx])
        else:
            logger.debug('All vals in plev are masked, ignoring.')
            statj = None
    else:
        mask = np.zeros_like(dataset[pl_idx], bool)
        statj = np.ma.array(dataset[pl_idx], mask=mask)

    return statj


def _compute_statistic(data, statistic_name):
    """Compute multimodel statistic."""
    data = np.ma.array(data)
    statistic = data[0]

    if statistic_name == 'median':
        statistic_function = np.ma.median
    elif statistic_name == 'mean':
        statistic_function = np.ma.mean
    elif statistic_name == 'std':
        statistic_function = np.ma.std
    elif statistic_name == 'max':
        statistic_function = np.ma.max
    elif statistic_name == 'min':
        statistic_function = np.ma.min
    else:
        raise NotImplementedError

    # no plevs
    if len(data[0].shape) < 3:
        # get all NOT fully masked data - u_data
        # data is per time point
        # so we can safely NOT compute stats for single points
        if data.ndim == 1:
            u_datas = [d for d in data]
        else:
            u_datas = [d for d in data if not np.all(d.mask)]
        if len(u_datas) > 1:
            statistic = statistic_function(data, axis=0)
        else:
            statistic.mask = True
        return statistic

    # plevs
    for j in range(statistic.shape[0]):
        plev_check = []
        for cdata in data:
            fixed_data = _plev_fix(cdata, j)
            if fixed_data is not None:
                plev_check.append(fixed_data)

        # check for nr datasets
        if len(plev_check) > 1:
            plev_check = np.ma.array(plev_check)
            statistic[j] = statistic_function(plev_check, axis=0)
        else:
            statistic.mask[j] = True

    return statistic


def _put_in_cube(template_cube, cube_data, statistic, t_axis):
    """Quick cube building and saving."""
    tunits = cf_units.Unit("days since 1850-01-01", calendar="standard")
    times = iris.coords.DimCoord(t_axis, standard_name='time', units=tunits)

    coord_names = [c.long_name for c in template_cube.coords()]
    coord_names.extend([c.standard_name for c in template_cube.coords()])
    if 'latitude' in coord_names:
        lats = template_cube.coord('latitude')
    else:
        lats = None
    if 'longitude' in coord_names:
        lons = template_cube.coord('longitude')
    else:
        lons = None

    # no plevs
    if len(template_cube.shape) == 3:
        cspec = [(times, 0), (lats, 1), (lons, 2)]
    # plevs
    elif len(template_cube.shape) == 4:
        plev = template_cube.coord('air_pressure')
        cspec = [(times, 0), (plev, 1), (lats, 2), (lons, 3)]
    elif len(template_cube.shape) == 1:
        cspec = [
            (times, 0),
        ]
    elif len(template_cube.shape) == 2:
        # If you're going to hardwire air_pressure into this,
        # might as well have depth here too.
        plev = template_cube.coord('depth')
        cspec = [
            (times, 0),
            (plev, 1),
        ]

    # correct dspec if necessary
    fixed_dspec = np.ma.fix_invalid(cube_data, copy=False, fill_value=1e+20)
    # put in cube
    stats_cube = iris.cube.Cube(fixed_dspec,
                                dim_coords_and_dims=cspec,
                                long_name=statistic)
    coord_names = [coord.name() for coord in template_cube.coords()]
    if 'air_pressure' in coord_names:
        if len(template_cube.shape) == 3:
            stats_cube.add_aux_coord(template_cube.coord('air_pressure'))

    stats_cube.var_name = template_cube.var_name
    stats_cube.long_name = template_cube.long_name
    stats_cube.standard_name = template_cube.standard_name
    stats_cube.units = template_cube.units
    return stats_cube


def _set_common_calendar(cubes):
    """
    Make sure all cubes' use the same standard calendar.

    Cubes may have different calendars. This function extracts the date
    information from the cube and re-constructs a default calendar,
    resetting the actual dates to the 15th of the month or 1st of july for
    yearly data (consistent with `regrid_time`), so that there are no
    mismatches in the time arrays.

    Doesn't work for (sub)daily data, because different calendars may have
    different number of days in the year.
    """
    # The default time unit
    t_unit = cf_units.Unit("days since 1850-01-01", calendar="standard")

    for cube in cubes:
        # Extract date info from cube
        years = [cell.point.year for cell in cube.coord('time').cells()]
        months = [cell.point.month for cell in cube.coord('time').cells()]

        # Reconstruct default calendar
        if not 0 in np.diff(years):
            # yearly data
            dates = [datetime(year, 7, 1) for year in years]

        elif not 0 in np.diff(months):
            # monthly data
            dates = [datetime(year, month, 15)
                     for year, month in zip(years, months)]
        else:
            # (sub)daily data
            raise ValueError("Multimodel only supports yearly or monthly data")

        # Update the cubes' time coordinate (both point values and the units!)
        cube.coord('time').points = [t_unit.date2num(date) for date in dates]
        cube.coord('time').units = t_unit
        # Reset bounds
        cube.coord('time').bounds = None
        cube.coord('time').guess_bounds()
        # Remove aux coords that may differ
        for auxcoord in cube.aux_coords:
            if auxcoord.long_name in ['day_of_month', 'day_of_year']:
                cube.remove_coord(auxcoord)


def _get_time_slice(cubes, time):
    """Fill time slice array with cubes' data if time in cube, else mask."""
    time_slice = []
    for cube in cubes:
        cube_time = cube.coord('time').points
        if time in cube_time:
            idx = int(np.argwhere(cube_time == time))
            subset = cube[idx].data
        else:
            subset = np.ma.empty(list(cubes[0].shape[1:]))
            subset.mask = True
        time_slice.append(subset)
    return time_slice


def _assemble_data(cubes, statistic, span='overlap'):
    """Get statistical data in iris cubes."""
    # New time array representing the union or intersection of all cubes
    time_spans = [cube.coord('time').points for cube in cubes]
    if span == 'overlap':
        new_times = reduce(np.intersect1d, time_spans)
    elif span == 'full':
        new_times = reduce(np.union1d, time_spans)
    n_times = len(new_times)

    # Target array to populate with computed statistics
    new_shape = [n_times] + list(cubes[0].shape[1:])
    stats_data = np.ma.zeros(new_shape)

    # Make time slices and compute stats
    for i, time in enumerate(new_times):
        time_data = _get_time_slice(cubes, time)
        stats_data[i] = _compute_statistic(time_data, statistic)

    template = cubes[0][:n_times]
    stats_cube = _put_in_cube(template, stats_data, statistic, new_times)
    return stats_cube


def multi_model_statistics(products, span, statistics, output_products=None):
    """
    Compute multi-model statistics.

    Multimodel statistics computed along the time axis. Can be
    computed across a common overlap in time (set span: overlap)
    or across the full length in time of each model (set span: full).
    Restrictive computation is also available by excluding any set of
    models that the user will not want to include in the statistics
    (set exclude: [excluded models list]).

    Restrictions needed by the input data:
    - model datasets must have consistent shapes,
    - higher dimensional data is not supported (ie dims higher than four:
    time, vertical axis, two horizontal axes).

    Parameters
    ----------
    products: list
        list of data products or cubes to be used in multimodel stat
        computation;
        cube attribute of product is the data cube for computing the stats.
    span: str
        overlap or full; if overlap stas are computed on common time-span;
        if full stats are computed on full time spans.
    output_products: dict
        dictionary of output products.
    statistics: str
        statistical measure to be computed. Available options: mean, median,
        max, min, std
    Returns
    -------
    list
        list of data products or cubes containing the multimodel stats
        computed.
    Raises
    ------
    ValueError
        If span is neither overlap nor full.

    """
    logger.debug('Multimodel statistics: computing: %s', statistics)
    if len(products) < 2:
        logger.info("Single dataset in list: will not compute statistics.")
        return products
    if output_products:
        cubes = [cube for product in products for cube in product.cubes]
        statistic_products = set()
    else:
        cubes = products
        statistic_products = {}

    # Make cubes share the same calendar, so time points are comparable
    _set_common_calendar(cubes)

    if span == 'overlap':
        # check if we have any time overlap
        times = [cube.coord('time').points for cube in cubes]
        overlap = reduce(np.intersect1d, times)
        if len(overlap) <= 1:
            logger.info("Time overlap between cubes is none or a single point."
                        "check datasets: will not compute statistics.")
            return products
        logger.debug("Using common time overlap between "
                     "datasets to compute statistics.")
    elif span == 'full':
        logger.debug("Using full time spans to compute statistics.")
    else:
        raise ValueError(
            "Unexpected value for span {}, choose from 'overlap', 'full'".
            format(span))

    for statistic in statistics:
        # Compute statistic
        statistic_cube = _assemble_data(cubes, statistic, span)
        statistic_cube.data = np.ma.array(statistic_cube.data,
                                          dtype=np.dtype('float32'))

        if output_products:
            # Add to output product and log provenance
            statistic_product = output_products[statistic]
            statistic_product.cubes = [statistic_cube]
            for product in products:
                statistic_product.wasderivedfrom(product)
            logger.info("Generated %s", statistic_product)
            statistic_products.add(statistic_product)
        else:
            statistic_products[statistic] = statistic_cube

    if output_products:
        products |= statistic_products
        return products
    return statistic_products
