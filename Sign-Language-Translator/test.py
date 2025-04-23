
import cv2
from cvzone.HandTrackingModule import HandDetector
from cvzone.ClassificationModule import Classifier
import numpy as np
import math
import pyttsx3  
from googletrans import Translator  
from gtts import gTTS  
import os  
from PIL import Image, ImageDraw, ImageFont  

# Initialize text-to-speech engine
engine = pyttsx3.init()

# Initialize Google Translator
translator = Translator()

# Set default language for translation (e.g., Hindi)
selected_language = 'hi'  

# Dictionary of language codes
language_codes = {
    'English': 'en',
    'Hindi': 'hi',
    'Tamil': 'ta',
    'Telugu': 'te',
    'Marathi': 'mr',
    'Malayalam': 'ml'
}

# Initialize camera
cap = cv2.VideoCapture(0)

# Initialize Hand Detector
detector = HandDetector(maxHands=1)

# Load classifiers
classifier2 = Classifier("/Users/sukhineshgopalan/Downloads/sign_lang/converted_keras (2)/keras_model2.h5",
                         "/Users/sukhineshgopalan/Downloads/sign_lang/converted_keras (2)/labels2.txt")  
classifier3 = Classifier("/Users/sukhineshgopalan/Downloads/sign_lang/converted_keras (3)/keras_model3.h5",
                         "/Users/sukhineshgopalan/Downloads/sign_lang/converted_keras (3)/labels3.txt") 
classifier4 = Classifier("/Users/sukhineshgopalan/Downloads/sign_lang/converted_keras (4)/keras_model4.h5",
                         "/Users/sukhineshgopalan/Downloads/sign_lang/converted_keras (4)/labels4.txt") 
classifier5 = Classifier("/Users/sukhineshgopalan/Downloads/sign_lang/converted_keras (5)/keras_model5.h5",
                         "/Users/sukhineshgopalan/Downloads/sign_lang/converted_keras (5)/labels5.txt")
# classifier6 = Classifier("/Users/sukhineshgopalan/Downloads/sign_lang/converted_keras (7)/keras_model7.h5",
#                          "/Users/sukhineshgopalan/Downloads/sign_lang/converted_keras (7)/labels7.txt")  


labels2 = ["I love you", "no"]
labels3 = ["hello", "C"]
labels4 = ["yes", "thanks"]
labels5 = ["please", "R"]
#labels6 = ["W", "V"]


offset = 20
imgSize = 300
last_prediction = None  
sentence = []  


def putTextPIL(img, text, position):
    """Draw text using PIL for Unicode support."""
    pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_img)

   
    font_path = "/System/Library/Fonts/Supplemental/Arial.ttf"  # Adjust for Windows/Linux
    try:
        font = ImageFont.truetype(font_path, 30)
    except:
        font = ImageFont.load_default()  # Fallback to default if font not found

    draw.text(position, text, font=font, fill=(0, 255, 0))
    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

while True:
    success, img = cap.read()
    if not success:
        continue  

    imgOutput = img.copy()
    hands, img = detector.findHands(img)

    if hands:
        hand = hands[0]
        x, y, w, h = hand['bbox']
        h_img, w_img, _ = img.shape
        x1, y1 = max(x - offset, 0), max(y - offset, 0)
        x2, y2 = min(x + w + offset, w_img), min(y + h + offset, h_img)

        imgWhite = np.ones((imgSize, imgSize, 3), np.uint8) * 255  
        imgCrop = img[y1:y2, x1:x2]  

        if imgCrop.size == 0:
            continue

        aspectRatio = h / w
        if aspectRatio > 1:
            k, wCal = imgSize / h, math.ceil((imgSize / h) * w)
            imgResize = cv2.resize(imgCrop, (wCal, imgSize))
            wGap = math.ceil((imgSize - wCal) / 2)
            imgWhite[:, wGap:wGap + wCal] = imgResize
        else:
            k, hCal = imgSize / w, math.ceil((imgSize / w) * h)
            imgResize = cv2.resize(imgCrop, (imgSize, hCal))
            hGap = math.ceil((imgSize - hCal) / 2)
            imgWhite[hGap:hGap + hCal, :] = imgResize

        # Get predictions
        predictions = [
            (classifier2.getPrediction(imgWhite, draw=False), labels2),
            (classifier3.getPrediction(imgWhite, draw=False), labels3),
            (classifier4.getPrediction(imgWhite, draw=False), labels4),
            (classifier5.getPrediction(imgWhite, draw=False), labels5),
            #(classifier6.getPrediction(imgWhite, draw=False), labels6)
        ]
        
        # Find best prediction
        best_confidence = 0
        final_label = None
        for (prediction, labels) in predictions:
            confidence, index = prediction
            if confidence[index] > best_confidence:
                best_confidence = confidence[index]
                final_label = labels[index]

        if final_label is None:
            continue  # Skip if no valid prediction

        print(f"Prediction: {final_label}")

        # Translate detected text only for audio
        try:
            translated_obj = translator.translate(final_label, dest=selected_language)
            translated_text = translated_obj.text if translated_obj else "Translation Error"
            translated_text = translated_text.encode('utf-8').decode()  # Ensure proper encoding
            print(f"Translated for Audio: {translated_text}")
        except Exception as e:
            print(f"Translation Error: {e}")
            translated_text = final_label  # Fallback to original text if translation fails

       
        if final_label != last_prediction:
            sentence.append(translated_text)

            try:
               
                tts = gTTS(translated_text, lang=language_codes.get(selected_language, 'en'))
                tts.save("output.mp3")
                
                
                os.system("afplay output.mp3")  
            except Exception as e:
                print(f"TTS Error: {e}")

            last_prediction = final_label

        
        cv2.rectangle(imgOutput, (x1, y1 - 70), (x1 + 200, y1 - 20), (0, 255, 0), cv2.FILLED)

       
        imgOutput = putTextPIL(imgOutput, final_label, (x1, y1 - 30))

        cv2.rectangle(imgOutput, (x1, y1), (x2, y2), (0, 255, 0), 4)

    cv2.imshow('Image', imgOutput)

    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break


final_sentence = " ".join(sentence)
print("\nFinal Sentence (Translated):", final_sentence)
try:
    translated_sentence = translator.translate(final_sentence, dest=selected_language).text
    print(f"Final Translated Sentence: {translated_sentence}")
    
    
    tts = gTTS(translated_sentence, lang=language_codes.get(selected_language, 'en'))
    tts.save("final_output.mp3")
    os.system("afplay final_output.mp3")  
except Exception as e:
    print(f"Final Translation Error: {e}")


cap.release()
cv2.destroyAllWindows()


