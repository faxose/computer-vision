
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import torch
import torch.optim as optim
import torchvision.datasets as datasets
import torchvision.transforms as transforms

from tqdm import tqdm
import datetime
import argparse
import matplotlib.pyplot as plt
import numpy as np
import os
import models
from loss import iic

from dataset import mnist


def display_sample_mnist(img):
    plt.imshow(img.squeeze(), cmap='gray')
    plt.show()


def train(args,
          model,
          device,
          train_loader,
          optimizer,
          epoch,
          ma_et = 1.):
    model.train()
    dataset = train_loader.dataset
    log_interval = len(dataset) // args.batch_size
    log_interval //= 5
    datalen = 0
    for i, data in enumerate(train_loader):
        # data[0] is pair of 2 images + 1 label
        xy, y = data[0], data[1]
        jx1 = xy[0].to(device)
        jx2 = xy[1].to(device)

        z, zt = model(jx1, jx2)
        loss = iic(z, zt)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        datalen += len(xy[0])
        if (i + 1) % log_interval == 0 or datalen == len(dataset):
            print('Epoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f}'.format(
                  epoch,
                  datalen,
                  len(dataset),
                  100. * datalen / len(dataset),
                  loss.item()))



def test(args, model, device, test_loader):
    model.eval()
    backbone = model.backbone
    with torch.no_grad():
        for data in test_loader:
            inputs, labels = data[0].to(device), data[1].to(device)
            outputs = backbone(inputs).cpu().numpy()
            labels = labels.cpu().numpy()
            print(outputs, labels)


def get_data_loaders(args):
    use_cuda = not args.no_cuda and torch.cuda.is_available()
    kwargs = {'num_workers': 4} if use_cuda else {}
    transform1 = transforms.Compose([transforms.ToTensor()])
    affine = transforms.RandomAffine(5,
                                     shear=(10, 10, 10, 10),
                                     translate=(0.2,0.2))
    transform2 = transforms.Compose([affine, transforms.ToTensor()])

    x_train = mnist.SiameseMNIST(root='./data',
                                 train=True,
                                 download=True,
                                 transform=transform1,
                                 siamese_transform=transform2)

    DataLoader = torch.utils.data.DataLoader
    train_loader = DataLoader(x_train,
                              shuffle=True,
                              batch_size=args.batch_size,
                              **kwargs)

    x_test = datasets.MNIST(root='./data',
                            train=False,
                            download=True,
                            transform=transform1)

    test_loader = DataLoader(x_test,
                             shuffle=True,
                             batch_size=args.batch_size,
                             **kwargs)


    print("Train dataset size:", len(x_train))
    print("Test dataset size:", len(x_test))

    return train_loader, test_loader


def main():
    parser = argparse.ArgumentParser(description='PyTorch MNIST Example')
    parser.add_argument('--no-cuda',
                        action='store_true',
                        default=False,
                        help='disables CUDA training')
    parser.add_argument('--seed',
                        type=int,
                        default=1,
                        metavar='S',
                        help='random seed (default: 1)')
    parser.add_argument('--batch-size',
                        type=int,
                        default=128,
                        metavar='N',
                        help='input batch size for training (default: 128)')
    parser.add_argument('--epochs',
                        type=int,
                        default=40,
                        metavar='N',
                        help='number of epochs to train (default: 10)')
    parser.add_argument('--save-weights',
                        #action='store_true',
                        default=None,
                        help='Save current model weights')


    args = parser.parse_args()
    use_cuda = not args.no_cuda and torch.cuda.is_available()
    # torch.manual_seed(args.seed)


    train_loader, test_loader = get_data_loaders(args)

    device = torch.device("cuda" if use_cuda else "cpu")
    model = models.Model().to(device)
    if torch.cuda.device_count() > 1:
        print("Available GPUs:", torch.cuda.device_count())
        # model = nn.DataParallel(model)
    print(model)
    print(device)
    optimizer = optim.Adam(model.parameters())

    start_time = datetime.datetime.now()
    for epoch in tqdm(range(args.epochs)):
        train(args,
              model,
              device,
              train_loader,
              optimizer,
              epoch)
    elapsed_time = datetime.datetime.now() - start_time
    print("Elapsed time (train): %s" % elapsed_time)
    if args.save_weights is not None:
        folder = "weights"
        os.makedirs(folder, exist_ok=True) 
        path = os.path.join(folder, args.save_weights)
        torch.save(model.backbone.state_dict(), path)

    # test(args, model, device, test_loader)

if __name__ == '__main__':
    main()
