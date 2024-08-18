<?php
/* This file is an example of a receiving-script for images posted by the PyCam software.
    
    In the http request the cpuid of the camera is one key and then a second key is created from the timestamp when the 
    call was received to the server. All files are stored in a structure with camera cpuid at the top and one folder for each date.
    It saves the received high-res image as a jpg-file with a 'sibbling' json-file containing the meta-data for that image.
    In the date-folder a 'thumbs' folder is also created and all images are scaled down and saved here for easy viewing from a 
    webpage (or something else).
    It also saves the latest image at the top of the folder-structure for easy viewing
*/

//Create the individual image-key as a timestamp for the arrival-time
//NOTE: the meta-data contains the exact time for the exposure if this is needed
$date=date_create();
$timestamp = date_timestamp_get($date);

//Get the cpuid and the meta-data from the url
$cpuid  = isset($_GET['cpu'])     ? $_GET['cpu']     : 'id_na';
$metadata = isset($_GET['meta'])     ? $_GET['meta']     : '{}';

//Set the size of the thumb-nails
$t_width= 300; 
$t_height =200;

//Define folder structure on the server
$target_dir = $_SERVER['DOCUMENT_ROOT']. '/cvimages/'. $cpuid . '/';
$target_dir_date = $_SERVER['DOCUMENT_ROOT']. '/cvimages/'. $cpuid . '/' . date("Y-m-d") .'/';
$target_dir_thumbs= $_SERVER['DOCUMENT_ROOT']. '/cvimages/'. $cpuid . '/' . date("Y-m-d") .'/'. "thumbs/";

//Create the folders where needed
if (!file_exists($target_dir)) {
    mkdir($target_dir, 0777, true);    
}
if (!file_exists($target_dir_date)) {
    mkdir($target_dir_date, 0777, true);
}
if (!file_exists($target_dir_thumbs)) {
    mkdir($target_dir_thumbs, 0777, true);
}

$latest_file = $target_dir. '/latest.jpg';
$target_file = $target_dir_date . $timestamp . ".jpg"; 
$meta_file = $target_dir_date . $timestamp . ".json";
$target_thumb_file = $target_dir_thumbs . $timestamp . ".jpg";

//grab and store the image-file        
move_uploaded_file($_FILES["media"]["tmp_name"], $target_file);
//copy image to latest-file
copy($target_file, $latest_file);
//Store the provided meta-data as a json file
file_put_contents($meta_file, $metadata);

//Now resize and save a thumb for this image..
list($width, $height, $type, $attr) = getimagesize( $target_file );
$src = imagecreatefromstring( file_get_contents( $target_file ) );
$dst = imagecreatetruecolor( $t_width, $t_height );
imagecopyresampled( $dst, $src, 0, 0, 0, 0, $t_width, $t_height, $width, $height );
imagejpeg( $dst, $target_thumb_file );
//Free image resources
imagedestroy( $dst );
imagedestroy( $src );