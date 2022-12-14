import os
from typing import List
import imutils as imutils
import numpy as np
import cv2
import easyocr

os.environ["KERAS_OCR_CACHE_DIR"] = "./models"
os.environ["EASYOCR_MODULE_PATH"] = "./models"


def pill_imprint_prediction(file_path):
    # Try running prediction on sample image
    
    # temp pill run

    #test_file_path = "C:\Users\lgvii\Desktop\pills\ocr_test.jpg"
    predictions = output_predictions(file_path)
    print(predictions)

    return predictions

#!wget https://data.lhncbc.nlm.nih.gov/public/Pills/PillProjectDisc1/images/!_4!DFN2-E8ODAOMKCG28FS3M8OQLX.JPG -O pill.jpg


def generate_ocr(model_path=None, gpu=True):
    """
    Creates the EasyOCR object that will be used to generate text predictions.

    :param model_path: storage directory in which the downloaded detection and
                       recognition models will be placed.  If not specified,
                       models will be read from a directory as defined by the
                       environment variable EASYOCR_MODULE_PATH (preferred),
                       MODULE_PATH (if defined), or ~/.EasyOCR/.
    :param gpu: True if the GPU should be used for predictions, False if not,
                defaults to True
    :return: EasyOCR object used to generate text predictions
    """
    return easyocr.Reader(["en"], gpu=gpu, model_storage_directory=model_path)


def _create_image(image_file: str) -> np.ndarray:
    image = cv2.imread(image_file)
    # No need to convert back to RGB, easyocr can handle BGR
    return image


def _sharpen_image(image) -> np.ndarray:
    kernel = np.array([[0, -1, 0],
                       [-1, 5, -1],
                       [0, -1, 0]])
    image_sharp = cv2.filter2D(image, -1, kernel)
    return image_sharp


def _generate_single_prediction_set(reader: easyocr.Reader, image: np.ndarray) -> List[str]:
    # By default, easyocr outputs list format with each element being a tuple of
    # ([bounding box 2D array], text, confidence)
    full_prediction = reader.readtext(image)
    predictions = []
    for word in full_prediction:
        conf = word[2]
        text = word[1]
        if conf > 0 and len(text) > 0:
            predictions.append(text)
    return predictions


def generate_predictions(ocr, image_file: str, rotate: bool = False) -> List[List[str]]:
    """
    Generates predictions from the specified image file, optionally rotating it by 90, 180, and 270 degrees (useful for
    testing accuracy against test images).

    Note that the OCR object is assumed to be created by the caller.  This is to facilitate batch testing, so the OCR
    object doesn't get reinitialized for each image tested.

    Note that the returned object will NOT be an empty List if no text is recognized.  It will instead contain one or
    more empty Lists, each from a permutation of the supplied image.

    :param ocr: OCR library object used to generate predictions, created/initialized outside this method so that batch
                testing doesn't have to recreate it for each image tested
    :param image_file: path of the image file to check for text
    :param rotate: True if predictions should also be generated for the image at 90, 180, and 270 degrees, intended
                   for use with batch testing of stock images that may be rotated, defaults to False
    :return: List containing prediction groups for each image permutation, where each prediction group is itself a
             List of text strings.  Note that if no text is found, this will NOT be an empty List, but will instead
             contain multiple empty Lists
    """
    base_image = _create_image(image_file)
    image_sharp = _sharpen_image(base_image)
    images = [base_image, image_sharp]
    all_predictions = []
    for image in images:
        # Rotate the image across 0, 90, 180, and 270, in case the pill is rotated, to improve readability
        if rotate:
            for angle in [0, 90, 180, 270]:
                if angle == 0:
                    rotated = image
                else:
                    rotated = imutils.rotate_bound(image, angle)
                all_predictions.append(_generate_single_prediction_set(ocr, rotated))
        else:
            all_predictions.append(_generate_single_prediction_set(ocr, image))

    return all_predictions


def output_predictions(image_file: str, output_file: str = None, rotate: bool = False, delimiter: str = ";") -> str:
    """
    Creates an easyocr pipeline and generates text predictions on the specified image file, optionally writing the
    output to a specified output file.

    Output will consist of multiple lines, each terminated with "\n", where each line contains all predictions from a
    single permutation of the image (original, sharpened, rotated, etc) concatenated together using the specified
    delimiter. (The default delimiter is chosen specifically for use with pill imprints, as the imprint text itself
    uses the same delimiter.)  If no text was detected, output will contain one or more empty lines.

    :param image_file: path to the image on which OCR predictions should be generated
    :param output_file: path of an output text file to which the generated OCR predictions should be written, will
                        overwrite any previous content of the file, defaults to None
    :param rotate: True if additional rotational permutations of the image should be generated when predicting text,
                   False if only the image (and any sharpening or other operation permutations) should be used,
                   defaults to False
    :param delimiter: delimiter used to separate the text groups predicted from a single image permutation,
                      defaults to ";"
    :return: string containing predictions from all permutations, with the text from each permutation prediction
             concatenated to a single line using the specified delimiter, and each permutation line separated by "\n"
    """
    pipeline = generate_ocr()
    all_predictions = generate_predictions(pipeline, image_file, rotate)

    result = ""
    for prediction_group in all_predictions:
        output = delimiter.join(prediction_group)
        result = result + output + "\n"

    if output_file:
        with open(output_file, "w") as file:
            file.write(f"{result}\n")

    return result
