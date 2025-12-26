# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.


__author__ = 'teddycool'

# creating timelapse from still images (jpg) to mp4 using ffmpeg
# https://superuser.com/questions/1499968/creating-timelapse-from-still-images-jpg-to-mp4-using-ffmpeg

# ffmpeg -framerate 10 -pattern_type glob -i "*.jpg" -c:v libx264 -crf 0 output.mp4

from datetime import datetime
import cv2
import glob
import os

#Settings:
rawimageroot = "/home/psk/Dropbox/dev/timelapse/beebirth"
processimageroot = "/home/psk/Dropbox/dev/timelapse/result-hdr/beebirth2"
timelapseresultroot = "/home/psk/Dropbox/dev/timelapse/result-hdr/outside-sum"
imagetype = "jpg"

watermarktext = "(C) Biwebben.se" # Add a watermark with the date and time of the image

# Set resulting resolution for the video    
# Full HD: 1920x108, HD-ready 1280x720 
width =1280
height = 720


# All files and directories ending with .jpg and that don't begin with a dot:
imagefiles = (glob.glob(rawimageroot + "/*.jpg")) 

filecount = str(len(imagefiles))
counter = 0

for imagepath in imagefiles:  
    counter = counter + 1
    filename = imagepath.split("/")[-1].split(".")[0]
    print("Processing: " + filename + " " + str(counter) + "[" + filecount + "]"  )    

    # convert the timestamp to a datetime object in the local timezone
    filedate = str(datetime.fromtimestamp(int(filename)))
    #crop 

    img=cv2.imread(imagepath)   

    cropped_image = img[450:450+720, 1100:1100+1280] # Slicing to crop the image


    #resize

    #resized_image = cv2.resize(cropped_image, (width, height))

    # font 
    font = cv2.FONT_HERSHEY_SIMPLEX 
    
    # org 
    org = (50, 50) 
    
    # fontScale 
    fontScale = 1
    
    # Blue color in BGR 
    color = (255, 0, 0) 
    
    # Line thickness of 2 px 
    thickness = 2
    
    # Using cv2.putText() method 
    #add text with time
    image = cv2.putText(cropped_image, watermarktext + " \n" + filedate, org, font,  
                    fontScale, color, thickness, cv2.LINE_AA)     
   
    #Save the image
    cv2.imwrite('/home/psk/Dropbox/dev/timelapse/result-hdr/beebirth2/' + filename + '.jpg', cropped_image)


#Create the actual timelapse...
os.system("cat " + processimageroot +"/*.jpg | ffmpeg -framerate 10 -i - -c:v libx264 -crf 0 " + timelapseresultroot + ".mp4")

