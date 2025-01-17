# -*- coding: utf-8 -*-
"""pretarined.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1nbw_2L8E0VNCBdl8Tb1dJs3fwMtTwe4h
"""

from zipfile import ZipFile
file_name = './New_Data.zip'

with ZipFile(file_name, 'r') as zip:
  zip.extractall()
  print('Done')

import os
import torch
import torchvision
import tarfile
from torchvision.datasets.utils import download_url
from torch.utils.data import random_split
from torchvision.datasets import ImageFolder
import torchvision.transforms as T
import numpy as np
from torch.utils.data.dataloader import DataLoader

DATA_DIR = './New_Data/'

img_size = 1024
imagenet_stats = ([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
dataset = ImageFolder(DATA_DIR, T.Compose([T.Resize(img_size),
                                           T.Pad(8, padding_mode='reflect'),
                                           T.RandomCrop(img_size),
                                           T.ToTensor(),
                                           T.Normalize(*imagenet_stats)]))

# Commented out IPython magic to ensure Python compatibility.
import matplotlib
import matplotlib.pyplot as plt
from torchvision.utils import make_grid
# %matplotlib inline

matplotlib.rcParams['figure.facecolor'] = '#ffffff'

def show_example(img):
    plt.imshow(img.detach().cpu().permute(1, 2, 0))

def denorm(img_tensors):
    return img_tensors * imagenet_stats[1][0] + imagenet_stats[0][0]

train_dl = DataLoader(dataset, batch_size = 16, shuffle = True)

for images, i in train_dl:
    print(i)
    show_example(denorm(images[0]))
    break

import torch.nn as nn
import torch.nn.functional as F

from torchvision import models

class Resnet(nn.Module):
    def __init__(self, pretrained = True):
        super().__init__()
        self.network = models.resnet34(pretrained = pretrained)
        self.network.fc = nn.Sequential(
            nn.Linear(self.network.fc.in_features, 1024),
            nn.LeakyReLU(0.2),
            nn.Linear(1024, 1024),
            nn.LeakyReLU(0.2),
            nn.Linear(1024, 512),
            nn.LeakyReLU(0.2),
            nn.Linear(512, 512),
            nn.LeakyReLU(0.2),
            nn.Linear(512, 128),
            nn.LeakyReLU(0.2),
            nn.Linear(128, 64),
            nn.LeakyReLU(0.2),
            nn.Linear(64, 16),
            nn.LeakyReLU(0.2),
            nn.Linear(16, 1),
            nn.Sigmoid()
            )

    def forward(self, x):
        return self.network(x)

resnet = Resnet()

def get_default_device():
    """Pick GPU if available, else CPU"""
    if torch.cuda.is_available():
        return torch.device('cuda')
    else:
        return torch.device('cpu')

def to_device(data, device):
    """Move tensor(s) to chosen device"""
    if isinstance(data, (list,tuple)):
        return [to_device(x, device) for x in data]
    return data.to(device, non_blocking=True)

class DeviceDataLoader():
    """Wrap a dataloader to move data to a device"""
    def __init__(self, dl, device):
        self.dl = dl
        self.device = device

    def __iter__(self):
        """Yield a batch of data after moving it to device"""
        for b in self.dl:
            yield to_device(b, self.device)

    def __len__(self):
        """Number of batches"""
        return len(self.dl)

device = get_default_device()
device

resnet = resnet.to(device = device)
train_dl = DeviceDataLoader(train_dl, device)

def accuracy(outputs, labels):
    preds = torch.round(outputs)
    return torch.tensor(torch.sum(preds.float() == labels.float()).item() / len(preds))

from tqdm.notebook import tqdm

def fit(epochs, lr, model, traindataloader):
    loss_history = []
    acc_history = []
    optimizer = torch.optim.Adam(model.parameters(), lr, betas = (0.5, 0.9))
    # optimizer = opt_func(model.parameters(), lr)
    for epoch in range(epochs):
        model.train()
        train_losses = []
        train_accuracy = []

        for batch in tqdm(traindataloader):
            images, labels = batch
            out = model(images)
            out = torch.flatten(out)
            loss = F.binary_cross_entropy(out.float(), labels.float())
            train_losses.append(loss.item())
            train_accuracy.append(accuracy(out, labels))


            loss.backward()
            optimizer.step()
            optimizer.zero_grad()
        acc_history.append(np.mean(train_accuracy))
        loss_history.append(np.mean(train_losses))
        print("Train_Loss: ", np.round(np.mean(train_losses), 3), "  Train_Acc: ", np.round(np.mean(train_accuracy), 3))
        # evaluate(model, valdataloader)

    return loss_history, acc_history

loss, acc = fit(10, 1e-4, resnet, train_dl)

!pip install opendatasets

url = 'https://www.kaggle.com/competitions/induction-task-2025/data'

import opendatasets as od
od.download(url)

import os

import torch
from tqdm import tqdm
from torchvision.datasets import ImageFolder
from torchvision.transforms import v2
from PIL import Image
import pandas as pd
import matplotlib.pyplot as plt

resnet.eval()
transforms = v2.Compose([
    v2.Resize((512,512)),
    v2.ToTensor(),
])

test_ds = ImageFolder("./induction-task-2025/test/test", transform= transforms)
image, _ = test_ds[12]

def denormalize(images, means, stds):
    means = torch.tensor(means).reshape(1, 3, 1, 1)
    stds = torch.tensor(stds).reshape(1, 3, 1, 1)
    return images * stds + means


def preprocess_image_pytorch(img_path, target_size=(512, 512)):
    preprocess = transforms
    img = Image.open(img_path).convert('RGB')
    img_tensor = preprocess(img)
    img_tensor = img_tensor.unsqueeze(0)
    return img_tensor


def predict_and_save_csv_pytorch(model, images_dir, output_csv='./predictions.csv', target_size=(512, 512), device='cpu'):
    image_names = []
    predicted_labels = []

    # Example class labels
    class_labels = ['AI', 'Real']
    labels_pred = []
    for filename in os.listdir(images_dir):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
            img_path = os.path.join(images_dir, filename)
            try:

                img_tensor = preprocess_image_pytorch(img_path, target_size).to(device)
                with torch.no_grad():
                    outputs = model(img_tensor)
                    labels_pred.append((outputs))
                    if outputs>0.5:
                        outputs = 1
                    else:
                        outputs = 0
                    predicted_class = outputs
                predicted_label = class_labels[predicted_class]
                image_names.append(filename)
                predicted_labels.append(predicted_label)
                print(f"Predicted {predicted_label} for {filename}")
            except Exception as e:
                print(f"Error processing {filename}: {e}")
    print(labels_pred)
    try:
        # Create a DataFrame
        image_names = file_names_without_extension = [os.path.splitext(file)[0] for file in image_names]
        df = pd.DataFrame({
            'Id': image_names,
            'Label': predicted_labels
        })
        print("DataFrame created successfully.")
        # Debug Statement
        df['num_part'] = df['Id'].str.extract('(\d+)').astype(int)

        # Sort and clean DataFrame
        df_sorted = df.sort_values(by='num_part').reset_index(drop=True)
        df_sorted = df_sorted.drop(['num_part'], axis=1)
        # Save to CSV
        df_sorted.to_csv(output_csv, index=False)
        print(f"Predictions saved to {os.path.abspath(output_csv)}")  # Debug Statement
    except Exception as e:
        print(f"Error saving CSV: {e}")

    print(f"Predictions saved to {os.path.abspath(output_csv)}")

predict_and_save_csv_pytorch(resnet, "./induction-task-2025/test/test/Test_Images", device = device)