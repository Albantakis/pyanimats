#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pyanimats.py

"""
PyAnimats
~~~~~~~~~
Evolve animats.

Usage:
    pyanimats.py run <experiment.yml> <output_file> [options]
    pyanimats.py resume <checkpoint.pkl> <output_file> [options]
    pyanimats.py -h | --help
    pyanimats.py -v | --version
    pyanimats.py --list

Arguments:
    run <experiment.yml>     Run an experiment.
    resume <checkpoint.pkl>  Resume from a checkpoint file.
    <output_file>            File where the output should be stored.

Command-line options override the parameters given in the experiment file.

If resuming from a checkpoint, only simulation and data options (listed below)
have an effect.

To generate output from a checkpoint immediately, without simulating any more
generations, resume from the checkpoint and pass the option `-n 0` (or any
value lower than the number of generations already simulated).

General options:
    --list                     List available fitness functions
    -h --help                  Show this
    -v --version               Show version
    -F --force                 Overwrite the output file.
    -P --profile=PATH          Profile performance and store results at PATH

Simulation options:
    -c --checkpoint=INT        Checkpoint interval (minutes)
    -C --checkpoint-file=PATH  Save to this checkpoint file (defaults to
                               `checkpoint.pkl` in the output directory)
    -s --status-interval=INT   Status-printing interval (generations)

Data options:
    -o --output-samples=INT    Number of animats to sample from evolution
    -b --logbook-interval=INT  Logbook recording interval (generations)
    -a --all-lineages          Save lineages of entire final population

Evolution options:
    -r --rng-seed=INT          Random number generator seed
    -f --fitness=FUNC          Fitness function
    -n INT --num-gen=NGEN      Number of generations to simulate
    -p --pop-size=INT          Population size
    -g --init-genome=PATH      Path to a lineage file for an intial genome
    -j --jumpstart=INT         Begin with this many start codons

Animat options:
    -e --num-sensors=INT       The number of sensors in an animat
    -i --num-hidden=INT        The number of hidden units in an animat
    -t --num-motors=INT        The number of motors in an animat

Environment options:
    -W --world-width=INT       The width of the animats' environment
    -H --world-height=INT      The height of the animats' environment

Genetic options:
    -m --mut-prob=FLOAT        Point mutation probability
    -U --dup-prob=FLOAT        Duplication probability
    -E --del-prob=FLOAT        Deletion probability
    -d --min-dup-del=INT       Minimum length of duplicated/deleted genome part
    -D --max-dup-del=INT       Maximum length of duplicated/deleted genome part
    -l --min-length=INT        Minimum genome length
    -L --max-length=INT        Maximum genome length
"""

import cProfile
import os
import pickle

from docopt import docopt

import fitness_functions
import utils
from __about__ import __version__
from evolve import Evolution
from experiment import Experiment

# Map CLI options to experiment parameter names and types.
cli_opt_to_param = {
    '--rng-seed':         ('rng_seed', int),
    '--checkpoint':       ('checkpoint_interval', float),
    '--status-interval':  ('status_interval', int),
    '--logbook-interval': ('logbook_interval', int),
    '--output-samples':   ('output_samples', int),
    '--fitness':          ('fitness_function', str),
    '--num-gen':          ('ngen', int),
    '--pop-size':         ('popsize', int),
    '--init-genome':      ('init_genome', str),
    '--jumpstart':        ('init_start_codons', int),
    '--num-sensors':      ('num_sensors', int),
    '--num-hidden':       ('num_hidden', int),
    '--num-motors':       ('num_motors', int),
    '--world-width':      ('world_width', int),
    '--world-height':     ('world_height', int),
    '--mut-prob':         ('mutation_prob', float),
    '--dup-prob':         ('duplication_prob', float),
    '--del-prob':         ('deletion_prob', float),
    '--min-dup-del':      ('min_dup_del_width', int),
    '--max-dup-del':      ('max_dup_del_width', int),
    '--min-length':       ('min_genome_length', int),
    '--max-length':       ('max_genome_length', int),
}


def main(args):
    # TODO make this an option for -h?
    # Print available fitness functions and their descriptions.
    if args['--list']:
        fitness_functions.print_functions()
        return 0

    # Final output will be written here.
    OUTPUT_FILE = args['<output_file>']
    # Don't overwrite the output file or without permission.
    if not args['--force'] and os.path.exists(OUTPUT_FILE):
        raise FileExistsError(
            'a file named `{}` already exists; not overwriting without the '
            '`--force` option.'.format(OUTPUT_FILE))
    # Ensure output directory exists.
    if os.path.dirname(OUTPUT_FILE):
        utils.ensure_exists(os.path.dirname(OUTPUT_FILE))
    # Checkpoints will be written here.
    CHECKPOINT_FILE = (args['--checkpoint-file'] or
                       args['<checkpoint.pkl>'] or
                       os.path.join(os.path.dirname(OUTPUT_FILE),
                                    'checkpoint.pkl'))
    # Ensure checkpoint directory exists.
    if os.path.dirname(CHECKPOINT_FILE):
        utils.ensure_exists(os.path.dirname(CHECKPOINT_FILE))

    # Parse the CLI options.
    cli_options = {param[0]: param[1](args[opt])
                   for opt, param in cli_opt_to_param.items()
                   if args[opt] is not None}

    # Either load from a checkpoint or start a new evolution.
    if args['resume']:
        # Load the checkpoint.
        print('Loading checkpoint from `{}`... '
              ''.format(args['<checkpoint.pkl>']),
              end='', flush=True)
        with open(args['<checkpoint.pkl>'], 'rb') as f:
            evolution = pickle.load(f)
        # Update the evolution experiment file with simulation parameters.
        # TODO split into evolution params and animat params
        evolution.experiment.update(cli_options)
        print('done.')
        print('Resuming evolution from generation '
              '{}...\n'.format(evolution.generation))
    else:
        experiment = Experiment(filepath=args['<experiment.yml>'],
                                override=cli_options)
        # Initialize the simulation.
        evolution = Evolution(experiment)
        print('Simulating {} generations...'.format(experiment.ngen))

    PROFILE_FILEPATH = args['--profile']
    if PROFILE_FILEPATH:
        utils.ensure_exists(os.path.dirname(PROFILE_FILEPATH))
        print('\nProfiling enabled.')
        pr = cProfile.Profile()
        pr.enable()

    # Run it!
    evolution.run(CHECKPOINT_FILE, ngen=cli_options.get('ngen'))

    if PROFILE_FILEPATH:
        pr.disable()
        print('\nSaving profile to `{}`... '.format(PROFILE_FILEPATH),
              end='', flush=True)
        pr.dump_stats(PROFILE_FILEPATH)
        print('done.')

    print('Simulated {} generations in {}.'.format(
        evolution.generation, utils.compress(evolution.elapsed)))
    print('\nSaving output to `{}`... '.format(OUTPUT_FILE),
          end='', flush=True)

    # Get the evolution results and write to disk.
    output = evolution.to_json(all_lineages=args['--all-lineages'])
    with open(OUTPUT_FILE, 'w') as f:
        utils.dump(output, f)

    print('done.')


if __name__ == '__main__':
    # Get command-line args from docopt.
    args = docopt(__doc__, version=__version__)
    main(args)
