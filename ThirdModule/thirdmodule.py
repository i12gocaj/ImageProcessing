# -*- coding: utf-8 -*-
"""ThirdModule.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1vb_H6Qjk-4qoGlXFq7wpOEj9XHzah0eo
"""

import os
import numpy as np
from PIL import Image

def load_grayscale_image(path):
    # Opens an image from the given path, converts it to grayscale ('L'), and returns it as a uint8 numpy array.
    img = Image.open(path).convert('L')
    return np.array(img, dtype=np.uint8)

def save_mask(mask, path):
    # Saves a binary mask (True/False) as an image to the specified path.
    # Multiplying the mask by 255 converts [False=0, True=1] to [0,255].
    Image.fromarray((mask.astype(np.uint8)*255)).save(path)

def otsu_threshold(img):
    # Implements Otsu's thresholding method to automatically find the best threshold between foreground and background.
    # Compute the histogram of the image in 256 levels (0 to 255).
    hist, _ = np.histogram(img, bins=256, range=(0,256))

    # 'total' is the total number of pixels in the image.
    total = img.size
    # 'sum_all' is the weighted sum of all intensity values (index * frequency).
    sum_all = np.dot(np.arange(256), hist)
    sum_b = 0
    w_b = 0
    var_max = 0
    threshold = 0

    # Iterate through all possible intensity values to find the one that maximizes the between-class variance.
    for t in range(256):
        w_b += hist[t]
        if w_b == 0:
            continue
        w_f = total - w_b
        if w_f == 0:
            break
        sum_b += t*hist[t]
        m_b = sum_b / w_b           # Background mean
        m_f = (sum_all - sum_b) / w_f  # Foreground mean
        var_between = w_b * w_f * (m_b - m_f)**2  # Between-class variance

        # If a higher variance is found, update the threshold.
        if var_between > var_max:
            var_max = var_between
            threshold = t

    # Generate a binary mask by applying the threshold.
    mask = img > threshold
    return mask

def region_growing(img, seed=None, threshold=5):
    # Region growing segmentation.
    # If no seed is provided, use the center of the image.
    if seed is None:
        seed = (img.shape[0]//2, img.shape[1]//2)

    # 'visited' controls which pixels have been visited.
    visited = np.zeros_like(img, dtype=bool)
    # 'mask' will store the resulting region.
    mask = np.zeros_like(img, dtype=bool)

    # The value of the seed pixel. The region will expand to nearby pixels with similar intensity.
    seed_value = img[seed]
    # Use a stack (list) to traverse the region.
    stack = [seed]
    visited[seed] = True

    # While there are pixels on the stack:
    while stack:
        x, y = stack.pop()
        mask[x, y] = True

        # 4-connected neighbors (up, down, left, right).
        for dx, dy in [(1,0),(-1,0),(0,1),(0,-1)]:
            nx, ny = x+dx, y+dy
            # Check that the neighbor is within image boundaries.
            if 0 <= nx < img.shape[0] and 0 <= ny < img.shape[1]:
                if not visited[nx, ny]:
                    # If the neighbor’s value is within the given threshold range, add it to the stack.
                    if abs(int(img[nx, ny]) - int(seed_value)) < threshold:
                        stack.append((nx, ny))
                    visited[nx, ny] = True
    return mask

def simple_watershed(img):
    # A very simplified version of a watershed algorithm.
    # Create a marker matrix (32-bit integer) to label regions.
    markers = np.zeros_like(img, dtype=np.int32)
    # Mark a pixel in the top-left corner with label 1.
    markers[0,0] = 1
    # Mark a pixel in the bottom-right corner with label 2.
    markers[-1,-1] = 2

    # The 'frontier' is a simple queue (here a list) starting from the two marked pixels.
    frontier = [(img[0,0], (0,0)), (img[-1,-1], (img.shape[0]-1, img.shape[1]-1))]
    # 'visited' to control which pixels have been explored.
    visited = np.zeros_like(img, dtype=bool)
    visited[0,0] = True
    visited[-1,-1] = True

    # Expand the region from the initial markers.
    while frontier:
        # Take the first element (Note: This is not a real priority queue, just extracting the first).
        val, (x,y) = frontier.pop(0)
        label = markers[x,y]

        # Expand to 4-connected neighbors.
        for dx, dy in [(1,0),(-1,0),(0,1),(0,-1)]:
            nx, ny = x+dx, y+dy
            if 0 <= nx < img.shape[0] and 0 <= ny < img.shape[1]:
                if not visited[nx, ny]:
                    markers[nx, ny] = label
                    visited[nx, ny] = True
                    frontier.append((img[nx, ny], (nx, ny)))

    # The resulting mask corresponds to label 1.
    mask = (markers == 1)
    return mask

def compute_confusion_matrix(gt, pred):
    # Compute the confusion matrix between ground truth (gt) and prediction (pred).
    # TP: True Positives, FP: False Positives, FN: False Negatives, TN: True Negatives.
    TP = np.sum((pred == 1) & (gt == 1))
    FP = np.sum((pred == 1) & (gt == 0))
    FN = np.sum((pred == 0) & (gt == 1))
    TN = np.sum((pred == 0) & (gt == 0))
    return TP, FP, FN, TN

def pixel_accuracy(TP, FP, FN, TN):
    # Pixel accuracy: (TP+TN)/(TP+FP+FN+TN).
    return (TP+TN)/(TP+FP+FN+TN) if (TP+FP+FN+TN)>0 else 0

def mean_accuracy(TP, FP, FN, TN):
    # Mean accuracy: average of foreground and background accuracies.
    acc_fg = TP/(TP+FN) if (TP+FN)>0 else 0
    acc_bg = TN/(TN+FP) if (TN+FP)>0 else 0
    return (acc_fg + acc_bg)/2

def iou(TP, FP, FN):
    # Intersection over Union (IoU): TP/(TP+FP+FN).
    return TP/(TP+FP+FN) if (TP+FP+FN)>0 else 0

def precision(TP, FP):
    # Precision: TP/(TP+FP).
    return TP/(TP+FP) if (TP+FP)>0 else 0

def recall(TP, FN):
    # Recall (Sensitivity): TP/(TP+FN).
    return TP/(TP+FN) if (TP+FN)>0 else 0

def f_measure(prec, rec):
    # F1-score: (2*Prec*Rec)/(Prec+Rec).
    return (2*prec*rec)/(prec+rec) if (prec+rec)>0 else 0

if __name__ == "__main__":
    # Input, ground truth, and output directories.
    input_folder = "human_ht29_colon_cancer_2_images"
    gt_folder = "human_ht29_colon_cancer_2_foreground"
    out_folder = "output_masks"
    os.makedirs(out_folder, exist_ok=True)

    # List the image files with '.tif' extension in the input folder.
    image_files = [f for f in os.listdir(input_folder) if f.endswith('.tif')]

    # Lists to store metrics for each method.
    metrics_threshold = []
    metrics_region = []
    metrics_watershed = []

    for img_name in image_files:
        # Load the image and its ground truth.
        img_path = os.path.join(input_folder, img_name)
        gt_path = os.path.join(gt_folder, img_name)

        img = load_grayscale_image(img_path)
        gt = load_grayscale_image(gt_path)
        # Convert the GT to binary (True/False) using a threshold of 127.
        gt_bin = gt > 127

        # Method 1: Otsu Thresholding
        mask_th = otsu_threshold(img)
        save_mask(mask_th, os.path.join(out_folder, img_name+"_threshold.png"))

        # Method 2: Region Growing
        mask_rg = region_growing(img, seed=None, threshold=5)
        save_mask(mask_rg, os.path.join(out_folder, img_name+"_region.png"))

        # Method 3: Simple Watershed
        mask_ws = simple_watershed(img)
        save_mask(mask_ws, os.path.join(out_folder, img_name+"_watershed.png"))

        # Compute metrics for each method and store them.
        for method_mask, metrics_list in zip([mask_th, mask_rg, mask_ws],
                                             [metrics_threshold, metrics_region, metrics_watershed]):
            TP, FP, FN, TN = compute_confusion_matrix(gt_bin, method_mask)
            pa = pixel_accuracy(TP, FP, FN, TN)
            ma = mean_accuracy(TP, FP, FN, TN)
            iou_val = iou(TP, FP, FN)
            prec = precision(TP, FP)
            rec = recall(TP, FN)
            f1 = f_measure(prec, rec)
            metrics_list.append((pa, ma, iou_val, prec, rec, f1))

    def avg_metrics(m_list):
        # Compute the average of accumulated metrics.
        arr = np.array(m_list)
        return np.mean(arr, axis=0) if len(arr)>0 else (0,0,0,0,0,0)

    # Compute the average metrics for each method.
    avg_thresh = avg_metrics(metrics_threshold)
    avg_region = avg_metrics(metrics_region)
    avg_water = avg_metrics(metrics_watershed)

    # Print the average results.
    print("Average Threshold (PA, MA, IoU, Prec, Rec, F1):", avg_thresh)
    print("Average Region Growing (PA, MA, IoU, Prec, Rec, F1):", avg_region)
    print("Average Watershed (PA, MA, IoU, Prec, Rec, F1):", avg_water)