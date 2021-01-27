import argparse
import torch
from torchvision import datasets, transforms
from sklearn.metrics import roc_curve
from sklearn.metrics import roc_auc_score

import os
import numpy as np
import matplotlib.pyplot as plt

from models.vanilla import ConvVAE
from models.vanilla_ped1 import ConvVAE_ped1
from models.resnet18 import ResNet18VAE
from models.resnet18_enc_only import ResNet18VAE_2

import OneClassMnist
import Ped1_loader
import MVTec_loader as mvtec

import cv2
from PIL import Image
from torchvision.utils import save_image, make_grid

import matplotlib.pyplot as plt

# Initialize AUROC parameters
test_steps = 1600 # Choose a very high number to test the whole dataset
score_range = 50 # How many threshold do you want to test?
scores = np.zeros((score_range, 4)) # TP, TN, FP, FN
plot_ROC = False # Plot the ROC curve or not

save_gcam_image = True
norm_gcam_image = True

def save_cam(image, filename, gcam):
    """
    Saves the attention maps generated by the model.
    Inputs:
        image - original image
        filename - name of to be saved file
        gcam - generated attention map of image
    """
    # Normalize 
    if norm_gcam_image:
        gcam = gcam - np.min(gcam)
        gcam = gcam / np.max(gcam)
    else:
        # Divide by a hand-chosen maximum value
        gcam = gcam / 255
        gcam = np.clip(gcam, 0.0, 1.0)

    # Save image
    if save_gcam_image:
        h, w, d = image.shape
        save_gcam = cv2.resize(gcam, (w, h))
        save_gcam = cv2.applyColorMap(np.uint8(255 * save_gcam), cv2.COLORMAP_JET)
        save_gcam = np.asarray(save_gcam, dtype=np.float) + np.asarray(image, dtype=np.float)
        save_gcam = np.uint8(save_gcam)
        # cv2.imwrite(filename, save_gcam) # Uncomment to save the images

        # gcam = gcam - np.min(gcam)
        # gcam = gcam / np.max(gcam)
    return gcam

def main(args):
    """
    Main Function for testing and saving attention maps.
    Inputs:
        args - Namespace object from the argument parser
    """
    # Load dataset
    if args.dataset == 'mnist':
        # test_dataset = OneClassMnist.OneMNIST('./data', args.one_class, train=False, transform=transforms.ToTensor())
        print("Not implemented yet")
        return
    elif args.dataset == 'ucsd_ped1':
        test_dataset = Ped1_loader.UCSDAnomalyDataset('data/UCSD_Anomaly_Dataset.v1p2/UCSDped1/', train=False, resize=96)
    elif args.dataset == 'mvtec_ad':
        # class_name = mvtec.CLASS_NAMES[5]
        # test_dataset = mvtec.MVTecDataset(class_name=class_name, is_train=False, grayscale=False)
        print("Not implemented yet")
        return

    kwargs = {'num_workers': args.num_workers, 'pin_memory': True} if device == "cuda" else {}
    test_loader = torch.utils.data.DataLoader(
        test_dataset, batch_size=args.batch_size, shuffle=False, **kwargs)

    prediction_stack = np.zeros((test_steps * args.batch_size, args.image_size, args.image_size))
    gt_mask_stack = np.zeros((test_steps * args.batch_size, args.image_size, args.image_size))

    # Generate attention maps
    for batch_idx, (x, y) in enumerate(test_loader):

        # Normalize x
        x = x - torch.min(x)
        x = x / torch.max(x)

        # Visualize and save attention maps
        for i in range(x.size(0)):

            # for every image in batch
            ndarr = x[i,0].cpu().numpy() * 255
            file_path = os.path.join(args.result_dir, "{}-{}-attmap.png".format(batch_idx, i))

            # Load average VAE generation
            avg_gen = np.asarray(Image.open('reconstructions/ucsd_ped1_1.png').convert('L'))

            # Make prediction
            pred = np.abs(avg_gen - ndarr)

            # # Save heatmap
            # stacked_im = np.tile(np.expand_dims(ndarr, axis=2), 1)
            # pred = save_cam(stacked_im, file_path, pred)

            # # Compute the correct and incorrect mask scores for all thresholds
            # for j, score in enumerate(scores):

            #     threshold = (j) / (score_range - 1)

            # Apply the threshold
            # pred_bin = (pred > threshold)
            gt_mask = y[i,:,:,:].numpy()
            
            # Add to the stacks
            prediction_stack[batch_idx*args.batch_size + i] = pred
            gt_mask_stack[batch_idx*args.batch_size + i] = gt_mask

        # Stop parameter
        if batch_idx == (test_steps - 1):
            print("Reached the maximum number of steps")
            break

    auc = roc_auc_score(gt_mask_stack.flatten().astype(np.uint8), prediction_stack.astype(np.uint8).flatten())
    print(f"AUROC score: {auc}")

    if plot_ROC:
        tpr, tnr, _ =  roc_curve(gt_mask_stack.astype(np.uint8).flatten(), prediction_stack.astype(np.uint8).flatten())
        plt.plot(tpr, tnr, label="ROC")
        plt.xlabel("FPR")
        plt.ylabel("TPR")
        plt.legend()
        plt.show()
    return


if __name__ == '__main__':

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print("using device", device)

    parser = argparse.ArgumentParser(description='Explainable VAE')
    parser.add_argument('--result_dir', type=str, default='test_results', metavar='DIR',
                        help='output directory')
    parser.add_argument('--batch_size', type=int, default=4, metavar='N',
                        help='input batch size for training (default: 128)')
    parser.add_argument('--seed', type=int, default=1, metavar='S',
                        help='random seed (default: 1)')
    parser.add_argument('--num_workers', default=1, type=int,
                        help='Number of workers to use in the data loaders.')

    # Dataset parameters
    parser.add_argument('--dataset', type=str, default='ucsd_ped1',
                        help='select one of the following datasets: mnist, ucsd_ped1, mvtec_ad')
    parser.add_argument('--image_size', type=int, default=100,
                        help='Select an image size')

    args = parser.parse_args()

    main(args)
