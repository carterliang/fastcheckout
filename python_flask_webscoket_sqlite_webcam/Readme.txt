
=========
[Installation]
pip install -r requirements.txt

[Directory layout]
tree /F

├─appmain.py
│─db.py
│─sql_cmd.py
│─sqllite_utils.py
├─Readme.txt
├─requirements.txt
│─ post.py
├─templates/
│      html5_camera_1_1.html
│      html5_camera_2.html
│      index.html
│      viewreport02.html
│
└─upload/
│        20221114-190224.png
└─web/index.html

        


[Run Flask]
python appmain.py


[Test it]

http://127.0.0.1:3000

#main function

http://127.0.0.1:3000

#send a camera image (base64)

http://127.0.0.1:3000/video


#Referencs docs
[Flask User’s Guide]
https://flask.palletsprojects.com/en/2.2.x/
