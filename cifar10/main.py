import torch
import torch.nn as nn
import torch.optim as optim

import random
import numpy as np

import argparse

import utils
import models

# Format [time, batch, diff, vector]

def main(argv=None):

    parser = argparse.ArgumentParser(
        description="Train a model for the cifar classification task"
    )

    parser.add_argument(
        '--model',
        choices=[
            'hbnode', 'ghbnode', 'sonode',
            'anode', 'node', 'adamnode'
        ],
        default='adamnode',
        help="Determines which Neural ODE algorithm is used"
    )

    parser.add_argument(
        '--tol',
        type=float,
        default=1e-3,
        help="The error tolerance for the ODE solver"
    )

    parser.add_argument(
        '--xres',
        type=float,
        default=1.5
    )

    parser.add_argument(
        '--adjoint',
        type=eval,
        default=True
    )

    parser.add_argument(
        '--visualize',
        type=eval,
        default=True
    )

    parser.add_argument(
        '--niters',
        type=int,
        default=10,
        help='The number of iterations/epochs'
    )

    parser.add_argument(
        '--lr',
        type=float,
        default=0.001,
        help='The learning rate for the optimizer'
    )

    parser.add_argument(
        '--gpu',
        type=int,
        default=1,
        help='The GPU device number'
    )

    parser.add_argument(
        '--weight_decay',
        type=float,
        default=0.00,
        help='Weight decay in the optimizer'
    )

    parser.add_argument(
        '--timescale',
        type=int,
        default=1
    )

    parser.add_argument(
        '--seed',
        type=int,
        default=7
    )

    parser.add_argument(
        '--dim_size',
        type=int,
        default=12
    )

    parser.add_argument(
        '--hidden_size',
        type=int,
        default=31
    )

    parser.add_argument(
        '--alpha',
        type=float,
        default=3.0
    )

    parser.add_argument(
        '--beta',
        type=float,
        default=3.0
    )

    parser.add_argument(
        '--sqrt',
        choices=[
            'sigmoid', 'softplus', 'tanh'
        ],
        default='sigmoid',
    )

    # make a parser
    args = parser.parse_args(argv)

    randomSeed = args.seed
    torch.manual_seed(randomSeed)
    torch.cuda.manual_seed(randomSeed)
    torch.cuda.manual_seed_all(randomSeed)  # if use multi-GPU
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    np.random.seed(randomSeed)
    random.seed(randomSeed)

    # shape: [time, batch, derivatives, channel, x, y]
    trdat, tsdat = utils.cifar(batch_size=64)

    # Some hypers
    thetaact = nn.Tanh()
    gamma = nn.Parameter(torch.tensor([0.0]))
    
    hidden_size = args.hidden_size
    sqrt = args.sqrt
    alpha = args.alpha 
    beta = args.beta
    dim_size = args.dim_size

    if args.model == 'ghbnode':
        dim = 12
        hidden = 51
        args.xres = 1.5
        df = models.DF(dim, hidden, args=args)
        model_layer = models.NODElayer(models.HeavyBallNODE(df, None, thetaact=thetaact, timescale=args.timescale), args=args) 
        iv = models.initial_velocity(3, dim, hidden)
        model = nn.Sequential(
            iv,
            model_layer,
            models.predictionlayer(dim)
            ).to(device=f'cuda:{args.gpu}')
    elif args.model == 'hbnode':
        dim = 12
        hidden = 51
        args.xres = 0
        df = models.DF(dim, hidden, args=args)
        iv = models.initial_velocity(3, dim, hidden)
        model_layer = models.NODElayer(models.HeavyBallNODE(df, None, thetaact=None, timescale=args.timescale), args=args)
        # create the model
        model = nn.Sequential(
            iv,
            model_layer,
            models.predictionlayer(dim)
            ).to(device=f'cuda:{args.gpu}')
    elif args.model == 'anode':
        dim = 13
        hidden = 64
        df = models.DF(dim, hidden, args=args)
        model_layer = models.NODElayer(models.NODE(df), args=args)
        iv = models.anode_initial_velocity(3, aug=dim, args=args)
        # create the model
        model = nn.Sequential(
            iv,
            model_layer,
            models.predictionlayer(dim)
            ).to(device=f'cuda:{args.gpu}')
            
    elif args.model == 'node':
        dim = 3
        hidden = 125
        df = models.DF(dim, hidden, args=args)
        model_layer = models.NODElayer(models.NODE(df), args=args)
        iv = models.anode_initial_velocity(3, aug=dim, args=args)
        # create the model
        model = nn.Sequential(
            iv,
            model_layer,
            models.predictionlayer(dim)
            ).to(device=f'cuda:{args.gpu}')

    elif args.model == 'sonode':
        dim = 12
        hidden = 50
        df = models.DF(dim, hidden, args=args)
        model_layer = models.NODElayer(models.SONODE(df), args=args)
        iv = models.initial_velocity(3, dim, hidden)

        # create the model
        model = nn.Sequential(
            iv,
            model_layer,
            models.predictionlayer(dim)
            ).to(device=f'cuda:{args.gpu}')
    elif args.model == 'adamnode':
        dim = dim_size
        hidden = hidden_size
        args.xres = 0
        df = models.DF(dim, hidden, args=args)
        iv = models.initial_velocity_adam(3, dim, hidden)
        model_layer = models.NODElayer(models.AdamNODE(df, None, thetaact=None, sqrt=sqrt, alpha = alpha, beta = beta, timescale=args.timescale), args=args)
        # create the model
        model = nn.Sequential(
            iv,
            model_layer,
            models.predictionlayer(dim)
            ).to(device=f'cuda:{args.gpu}')

    # optimizer
    optimizer = optim.Adam(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)

    # print some summary information
    print(f'Error Tolerance: {args.tol}')
    print('Model Parameter Count:', utils.count_parameters(model))

    # train the model
    utils.train(model, optimizer, trdat, tsdat, args=args)
    
if __name__ == "__main__":
    main()
