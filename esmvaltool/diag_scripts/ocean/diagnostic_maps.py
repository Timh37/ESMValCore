"""Python example diagnostic."""
import logging
import os
import sys

import iris
import iris.quickplot as qplt
import matplotlib.pyplot as plt

import diagnostic_tools as diagtools
from esmvaltool.diag_scripts.shared import run_diagnostic

# This part sends debug statements to stdout
logger = logging.getLogger(os.path.basename(__file__))
logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))


def map_plots(
        cfg,
        md,
        fn,
):
    """
        This function makes a simple map plot for an indivudual model.

        The cfg is the opened global config,
        md is the metadata dictionairy
        fn is the preprocessing model file.
        """
    # Load cube and set up units
    cube = iris.load_cube(fn)
    cube = diagtools.bgc_units(cube, md['short_name'])

    # Is this data is a multi-model dataset?
    multi_model = md['model'].find('MultiModel') > -1

    # Make a dict of cubes for each layer.
    cubes = diagtools.make_cube_layer_dict(cube)

    # Making plots for each layer
    for la, (layer, c) in enumerate(cubes.items()):
        layer = str(layer)

        qplt.contourf(c, 25)

        try:
            plt.gca().coastlines()
        except AttributeError:
            print('Not able to add coastlines')

        # Add title to plot
        title = ' '.join([md['model'], md['long_name']])
        if layer:
            title = ' '.join(
                [title, '(', layer,
                 str(c.coords('depth')[0].units), ')'])
        plt.title(title)

        # Determine png filename:
        if multi_model:
            path = diagtools.folder(
                cfg['plot_dir']) + os.path.basename(fn).replace(
                    '.nc', '_map_' + str(la) + '.png')
        else:
            path = diagtools.get_image_path(
                cfg,
                md,
                suffix='map_' + str(la),
                image_extention='png',
            )

        # Saving files:
        if cfg['write_plots']:

            logger.info('Saving plots to %s', path)
            plt.savefig(path)

        plt.close()


def main(cfg):
    """
        Main function to load the config file, and send it to the plot maker.

        The cfg is the opened global config.
        """
    ####
    for k in cfg.keys():
        print('CFG:\t', k, '\t', cfg[k])

    for i, metadatafilename in enumerate(cfg['input_files']):
        print(
            '\nmetadata filename:',
            metadatafilename,
        )

        metadata = diagtools.get_input_files(cfg, index=i)
        for filename in sorted(metadata.keys()):

            print('-----------------')
            print(
                'model filenames:\t',
                filename,
            )

            ######
            # Time series of individual model
            map_plots(cfg, metadata[filename], filename)

    logger.debug("\n\nThis works\n\n")
    print('Success')


if __name__ == '__main__':
    with run_diagnostic() as config:
        main(config)
