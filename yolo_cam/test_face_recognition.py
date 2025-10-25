#from face_recognition_worker import load_known_faces, run_face_recognition
from test_face_recog import load_known_faces, run_face_recognition
person_id = 1  # change to any Person_Id you have in your folder
load_known_faces()
# --- Run face recognition on all images for this person ---
#photo_id=251005131045849 #UnknownEram
photo_id=251011131758373 #Sajid
run_face_recognition(photo_id)