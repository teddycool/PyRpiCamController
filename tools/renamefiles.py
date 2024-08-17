import datetime
import os
folder = "/home/psk/Dropbox/dev/bee_cv/TestHosJessica/TillJessica/Innekamera/2023-05-12"
for file in os.listdir(folder):
    old_name = os.path.join(folder, file)
        # get file name without extension
    old_ts = os.path.splitext(file)[0]
    new_time_name = datetime.datetime.fromtimestamp(int(old_ts))
    new_filename = new_time_name.strftime('%Y%m%d_%H%M%S')  + os.path.splitext(file)[1]
    
    new_name = os.path.join(folder, new_filename)
    print(new_name)
 
    os.rename(old_name, new_name)

# remove every second file
import datetime
import os
folder = "/home/psk/Dropbox/dev/bee_cv/TestHosJessica/TillJessica/Utekamera/2023-05-12"
remove = True
import os
# Get list of all files in a given directory sorted by name
list_of_files = sorted( filter( lambda x: os.path.isfile(os.path.join(folder, x)),
                        os.listdir(folder) ) )
filecount = 0
for file in list_of_files:
    filecount = filecount+1
    filename = os.path.join(folder, file)
    if filecount%4==0:
        os.remove(filename)
        print("File removed: " + file)
        remove = not remove
    else:
        remove = not remove
        print("File not removed: " + file)
    
   