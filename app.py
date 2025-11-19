# from flask import Flask, request, jsonify
# from flask_cors import CORS
# import os, uuid
# from PIL import Image
# import face_recognition
# import base64
# import smtplib
# from email.message import EmailMessage
# from flasgger import Swagger

# app = Flask(__name__)
# CORS(app)
# swagger = Swagger(app)

# DATA_DIR = 'data'
# os.makedirs(DATA_DIR, exist_ok=True)

# # Simple in-memory DB
# SUBMISSIONS = {}  # id -> {name,email,contact,photo_path,accuracy,approved}
# REF_ENCODINGS = {}  # ref_id -> face encoding

# # Helper: save uploaded file
# def save_upload(file_storage, prefix='file'):
#     fname = f"{prefix}_{uuid.uuid4().hex}.jpg"
#     path = os.path.join(DATA_DIR, fname)
#     file_storage.save(path)
#     return path

# # ==================== Guest Registration ====================
# @app.route('/api/guest/register', methods=['POST'])
# def guest_register():
#     """
#     Register a guest
#     ---
#     tags:
#       - Guest
#     consumes:
#       - multipart/form-data
#     parameters:
#       - in: formData
#         name: name
#         type: string
#         required: true
#       - in: formData
#         name: email
#         type: string
#         required: true
#       - in: formData
#         name: contact
#         type: string
#         required: true
#       - in: formData
#         name: photo
#         type: file
#         required: true
#     responses:
#       200:
#         description: Guest registered successfully
#     """
#     name = request.form.get('name')
#     email = request.form.get('email')
#     contact = request.form.get('contact')
#     photo = request.files.get('photo')

#     if not all([name, email, contact, photo]):
#         return jsonify({'error': 'missing parameters'}), 400

#     pid = uuid.uuid4().hex
#     photo_path = save_upload(photo, prefix='guest')

#     # Load image and encode face
#     try:
#         img = face_recognition.load_image_file(photo_path)
#         encodings = face_recognition.face_encodings(img)

#         if len(encodings) == 0:
#             return jsonify({'error': 'no face detected in photo'}), 400

#         REF_ENCODINGS[pid] = encodings[0]  # store face encoding for later match
#     except Exception as e:
#         print(f"Error encoding face: {e}")
#         return jsonify({'error': 'failed to process photo'}), 500

#     SUBMISSIONS[pid] = {
#         'id': pid,
#         'name': name,
#         'email': email,
#         'contact': contact,
#         'photo': photo_path,
#         'accuracy': None,
#         'status': 'pending',
#         'matched_faces': []  # ✅ Changed to list for multiple photos
#     }

#     print(f"✅ Guest registered: {pid} - {name}")
#     print(f"   Total submissions: {len(SUBMISSIONS)}")

#     return jsonify({'status': 'ok', 'id': pid})

# # ==================== Group Photo Upload ====================
# @app.route('/api/photo/group', methods=['POST'])
# def upload_group():
#     """
#     Upload one or multiple group photos and check if guest appears
#     ---
#     tags:
#       - Photo
#     consumes:
#       - multipart/form-data
#     parameters:
#       - name: guest_id
#         in: formData
#         type: string
#         required: true
#         description: The ID of the registered guest to match in the uploaded group photos
#       - name: group
#         in: formData
#         type: array
#         items:
#           type: file
#         required: true
#         description: One or more group photos to check for the guest
#     responses:
#       200:
#         description: Matching results for each uploaded photo
#     """
#     MATCH_THRESHOLD = 0.6

#     guest_id = request.form.get('guest_id')
#     group_files = request.files.getlist('group')

#     if not guest_id or not group_files:
#         return jsonify({'error': 'guest_id and group photos required'}), 400

#     if guest_id not in REF_ENCODINGS:
#         return jsonify({'error': 'invalid guest_id'}), 400

#     if guest_id not in SUBMISSIONS:
#         return jsonify({'error': 'guest not found in submissions'}), 400

#     ref_enc = REF_ENCODINGS[guest_id]
#     results = []
#     matched_photos = []  # ✅ Store ONLY matched photos
#     best_accuracy = 0

#     print(f"🔍 Processing {len(group_files)} photos for guest {guest_id}")

#     for group_file in group_files:
#         result = {
#             'file_name': group_file.filename,
#             'matched': False,
#             'accuracy': 0,
#             'matchedImage': None
#         }

#         group_path = save_upload(group_file, prefix='group')
#         photo_matched = False  # ✅ Track if THIS photo matched

#         try:
#             group_img = face_recognition.load_image_file(group_path)
#             face_locations = face_recognition.face_locations(group_img)
#             face_encodings = face_recognition.face_encodings(group_img, known_face_locations=face_locations)

#             print(f"   📸 {group_file.filename}: Found {len(face_encodings)} faces")

#             best_idx = None
#             best_dist = MATCH_THRESHOLD + 0.01

#             # Check each face in the photo
#             for i, enc in enumerate(face_encodings):
#                 dist = face_recognition.face_distance([ref_enc], enc)[0]
#                 if dist <= MATCH_THRESHOLD and dist < best_dist:
#                     best_dist = dist
#                     best_idx = i

#             # If a match was found in THIS photo
#             if best_idx is not None:
#                 accuracy = round((1.0 - best_dist) * 100.0, 2)
#                 result['matched'] = True
#                 result['accuracy'] = accuracy
#                 photo_matched = True  # ✅ Mark this photo as matched

#                 # Track best accuracy across all photos
#                 if accuracy > best_accuracy:
#                     best_accuracy = accuracy

#                 # ✅ Store ONLY matched photos with their accuracy
#                 matched_photos.append({
#                     'path': group_path,
#                     'accuracy': accuracy,
#                     'filename': group_file.filename
#                 })

#                 print(f"   ✅ MATCH in {group_file.filename}: {accuracy}% accuracy")

#                 # Crop matched face for display
#                 top, right, bottom, left = face_locations[best_idx]
#                 pil = Image.fromarray(group_img)
#                 crop = pil.crop((left, top, right, bottom))
#                 import io
#                 buf = io.BytesIO()
#                 crop.save(buf, format='JPEG')
#                 b64 = base64.b64encode(buf.getvalue()).decode('ascii')
#                 result['matchedImage'] = f"data:image/jpeg;base64,{b64}"
            
#             # ✅ Delete non-matching photos immediately
#             if not photo_matched:
#                 try:
#                     if os.path.exists(group_path):
#                         os.remove(group_path)
#                         print(f"   🗑️  NO MATCH - Deleted: {group_file.filename}")
#                 except Exception as e:
#                     print(f"   ⚠️  Could not delete {group_path}: {e}")

#         except Exception as e:
#             print(f"   ❌ Error processing {group_file.filename}: {e}")
#             # Delete photo if processing failed
#             try:
#                 if os.path.exists(group_path):
#                     os.remove(group_path)
#             except:
#                 pass

#         results.append(result)

#     # ✅ Update SUBMISSIONS with ONLY matched photos
#     if matched_photos:
#         # Initialize matched_faces if it doesn't exist, or append to existing
#         if 'matched_faces' not in SUBMISSIONS[guest_id]:
#             SUBMISSIONS[guest_id]['matched_faces'] = []
        
#         # Append new matches to existing ones
#         SUBMISSIONS[guest_id]['matched_faces'].extend(matched_photos)
#         SUBMISSIONS[guest_id]['accuracy'] = best_accuracy
        
#         print(f"✅ Total matches for {guest_id}: {len(matched_photos)} new, {len(SUBMISSIONS[guest_id]['matched_faces'])} total")
#         print(f"   Best accuracy this batch: {best_accuracy}%")
#         for idx, match in enumerate(matched_photos, 1):
#             print(f"   Match {idx}: {match['accuracy']}% - {match['filename']}")
#     else:
#         print(f"❌ No matches found for {guest_id} in this batch")

#     return jsonify({'results': results})


# # ==================== Admin List ====================
# @app.route('/api/admin/list', methods=['GET'])
# def admin_list():
#     """
#     Get all submissions for admin
#     ---
#     tags:
#       - Admin
#     responses:
#       200:
#         description: Admin list
#     """
#     out = []
#     for sid, s in SUBMISSIONS.items():
#         photo_b64 = None
#         if s['photo'] and os.path.exists(s['photo']):
#             try:
#                 with open(s['photo'], 'rb') as f:
#                     photo_b64 = "data:image/jpeg;base64," + base64.b64encode(f.read()).decode('ascii')
#             except Exception as e:
#                 print(f"Error reading photo for {sid}: {e}")
        
#         matched_faces = s.get('matched_faces', [])
        
#         out.append({
#             'id': sid,
#             'name': s['name'],
#             'email': s['email'],
#             'contact': s['contact'],
#             'photo': photo_b64,
#             'accuracy': s.get('accuracy') or 0,
#             'status': s.get('status', 'pending'),
#             'matched_count': len(matched_faces)  # ✅ Count ONLY matched photos
#         })
    
#     print(f"📋 Admin list requested: {len(out)} submissions")
#     for submission in out:
#         print(f"   {submission['name']}: {submission['matched_count']} matched photos")
    
#     return jsonify(out)

# # ==================== Email Helper ====================
# def send_approval_email(to_email, name, attachment_paths=None):
#     """
#     Send approval email with multiple photo attachments
#     """
#     SMTP_HOST = 'smtp.gmail.com'
#     SMTP_PORT = 587
#     SMTP_USER = 'harishmurali1289@gmail.com'
#     SMTP_PASS = 'mxsmfewatohrezmc'  # Google App Password

#     msg = EmailMessage()
#     msg['Subject'] = 'Registration Approved'
#     msg['From'] = SMTP_USER
#     msg['To'] = to_email
    
#     # Update message to mention multiple photos
#     photo_count = len(attachment_paths) if attachment_paths else 0
#     msg.set_content(
#         f"Hello {name},\n\n"
#         f"Thank you for attending this event!\n\n"
#         f"We found {photo_count} photo(s) with you in them. "
#         f"Please find them attached to this email.\n\n"
#         f"Best regards,\nEvent Team"
#     )

#     #  Attach ALL photos
#     if attachment_paths:
#         for idx, path in enumerate(attachment_paths, 1):
#             if os.path.exists(path):
#                 try:
#                     with open(path, 'rb') as f:
#                         data = f.read()
#                     msg.add_attachment(
#                         data,
#                         maintype='image',
#                         subtype='jpeg',
#                         filename=f"photo_{idx}_{os.path.basename(path)}"
#                     )
#                     print(f"Attached photo {idx}: {path}")
#                 except Exception as e:
#                     print(f"Error attaching photo {idx}: {e}")

#     try:
#         with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
#             s.starttls()
#             s.login(SMTP_USER, SMTP_PASS)
#             s.send_message(msg)
#         print(f"Email sent to {to_email} with {photo_count} attachment(s)")
#     except Exception as e:
#         print(f"Failed to send email: {e}")
#         raise

# # ==================== Admin Action ====================
# @app.route('/api/admin/action', methods=['POST'])
# def admin_action():
#     """
#     Perform admin action (approve/reject/complete)
#     ---
#     tags:
#       - Admin
#     consumes:
#       - application/json
#     parameters:
#       - in: body
#         name: body
#         required: true
#         schema:
#           type: object
#           properties:
#             id:
#               type: string
#             action:
#               type: string
#               enum: [approve,reject,complete]
#     responses:
#       200:
#         description: Action performed
#     """
#     data = request.json
#     sid = data.get('id')
#     action = data.get('action')

#     print(f"🔍 Admin action request:")
#     print(f"   ID: {sid}")
#     print(f"   Action: {action}")

#     if not sid or not action:
#         return jsonify({'error': 'missing id or action'}), 400

#     if sid not in SUBMISSIONS:
#         print(f"❌ ID {sid} not found in submissions!")
#         return jsonify({'error': 'not found'}), 404

#     s = SUBMISSIONS[sid]

#     if action == 'approve':
#         s['status'] = 'approved'
        
#         # ✅ Get ALL matched photos
#         matched_faces = s.get('matched_faces', [])
        
#         if matched_faces:
#             # Extract just the paths from the list of dicts
#             photo_paths = [match['path'] for match in matched_faces]
#             print(f"📧 Sending email with {len(photo_paths)} matched photo(s):")
#         else:
#             # Fallback to guest's registration photo
#             photo_paths = [s['photo']]
#             print(f"📧 No matches found, sending registration photo")
        
#         try:
#             send_approval_email(s['email'], s['name'], photo_paths)
#             print(f"✅ Approved: {s['name']} ({sid})")
#             return jsonify({
#                 'message': f'Approved and email sent with {len(photo_paths)} photo(s)'
#             })
#         except Exception as e:
#             print(f"❌ Email failed but status updated: {e}")
#             return jsonify({
#                 'message': 'Approved but email failed',
#                 'error': str(e)
#             }), 207

#     elif action == 'reject':
#         s['status'] = 'rejected'
#         print(f"❌ Rejected: {s['name']} ({sid})")
#         return jsonify({'message': 'Rejected'})

#     elif action == 'complete':
#         s['status'] = 'completed'
#         print(f"✅ Completed: {s['name']} ({sid})")
#         return jsonify({'message': 'Marked completed'})

#     else:
#         return jsonify({'error': 'unknown action'}), 400

# # ==================== Debug Endpoint ====================
# @app.route('/api/debug/status', methods=['GET'])
# def debug_status():
#     """Check system status"""
#     return jsonify({
#         'total_submissions': len(SUBMISSIONS),
#         'total_encodings': len(REF_ENCODINGS),
#         'submission_ids': list(SUBMISSIONS.keys()),
#         'data_dir_exists': os.path.exists(DATA_DIR),
#         'submissions_detail': {
#             sid: {
#                 'name': s['name'],
#                 'status': s['status'],
#                 'matched_photos': len(s.get('matched_faces', []))
#             }
#             for sid, s in SUBMISSIONS.items()
#         }
#     })

# # ==================== Run App ====================
# if __name__ == '__main__':
#     print("🚀 Starting Flask server...")
#     print(f"📁 Data directory: {DATA_DIR}")
#     app.run(debug=True)


# from flask import Flask, request, jsonify
# from flask_cors import CORS
# import os, uuid
# from PIL import Image
# import face_recognition
# import base64
# import smtplib
# from email.message import EmailMessage
# from flasgger import Swagger
# import config  # Import the config module

# app = Flask(__name__)
# CORS(app)
# swagger = Swagger(app)

# DATA_DIR = 'data'
# os.makedirs(DATA_DIR, exist_ok=True)

# # Simple in-memory DB
# SUBMISSIONS = {}  # id -> {name,email,contact,photo_path,accuracy,approved}
# REF_ENCODINGS = {}  # ref_id -> face encoding

# # Helper: save uploaded file
# def save_upload(file_storage, prefix='file'):
#     fname = f"{prefix}_{uuid.uuid4().hex}.jpg"
#     path = os.path.join(DATA_DIR, fname)
#     file_storage.save(path)
#     return path

# # ==================== Guest Registration ====================
# @app.route('/api/guest/register', methods=['POST'])
# def guest_register():
#     """
#     Register a guest
#     ---
#     tags:
#       - Guest
#     consumes:
#       - multipart/form-data
#     parameters:
#       - in: formData
#         name: name
#         type: string
#         required: true
#       - in: formData
#         name: email
#         type: string
#         required: true
#       - in: formData
#         name: contact
#         type: string
#         required: true
#       - in: formData
#         name: photo
#         type: file
#         required: true
#     responses:
#       200:
#         description: Guest registered successfully
#     """
#     name = request.form.get('name')
#     email = request.form.get('email')
#     contact = request.form.get('contact')
#     photo = request.files.get('photo')

#     if not all([name, email, contact, photo]):
#         return jsonify({'error': 'missing parameters'}), 400

#     pid = uuid.uuid4().hex
#     photo_path = save_upload(photo, prefix='guest')

#     # Load image and encode face
#     try:
#         img = face_recognition.load_image_file(photo_path)
#         encodings = face_recognition.face_encodings(img)

#         if len(encodings) == 0:
#             return jsonify({'error': 'no face detected in photo'}), 400

#         REF_ENCODINGS[pid] = encodings[0]  # store face encoding for later match
#     except Exception as e:
#         print(f"Error encoding face: {e}")
#         return jsonify({'error': 'failed to process photo'}), 500

#     SUBMISSIONS[pid] = {
#         'id': pid,
#         'name': name,
#         'email': email,
#         'contact': contact,
#         'photo': photo_path,
#         'accuracy': None,
#         'status': 'pending',
#         'matched_faces': []
#     }

#     print(f"✅ Guest registered: {pid} - {name} ({email})")
#     print(f"   Total submissions: {len(SUBMISSIONS)}")

#     return jsonify({'status': 'ok', 'id': pid})

# # ==================== Group Photo Upload ====================
# @app.route('/api/photo/group', methods=['POST'])
# def upload_group():
#     """
#     Upload one or multiple group photos and check if guest appears
#     ---
#     tags:
#       - Photo
#     consumes:
#       - multipart/form-data
#     parameters:
#       - name: guest_id
#         in: formData
#         type: string
#         required: true
#         description: The ID of the registered guest to match in the uploaded group photos
#       - name: group
#         in: formData
#         type: array
#         items:
#           type: file
#         required: true
#         description: One or more group photos to check for the guest
#     responses:
#       200:
#         description: Matching results for each uploaded photo
#     """
#     MATCH_THRESHOLD = 0.5

#     guest_id = request.form.get('guest_id')
#     group_files = request.files.getlist('group')

#     if not guest_id or not group_files:
#         return jsonify({'error': 'guest_id and group photos required'}), 400

#     if guest_id not in REF_ENCODINGS:
#         return jsonify({'error': 'invalid guest_id'}), 400

#     if guest_id not in SUBMISSIONS:
#         return jsonify({'error': 'guest not found in submissions'}), 400

#     ref_enc = REF_ENCODINGS[guest_id]
#     results = []
#     matched_photos = []
#     best_accuracy = 0

#     print(f"🔍 Processing {len(group_files)} photos for guest {guest_id}")

#     for group_file in group_files:
#         result = {
#             'file_name': group_file.filename,
#             'matched': False,
#             'accuracy': 0,
#             'matchedImage': None
#         }

#         group_path = save_upload(group_file, prefix='group')
#         photo_matched = False

#         try:
#             group_img = face_recognition.load_image_file(group_path)
#             face_locations = face_recognition.face_locations(group_img)
#             face_encodings = face_recognition.face_encodings(group_img, known_face_locations=face_locations)

#             print(f"   📸 {group_file.filename}: Found {len(face_encodings)} faces")

#             best_idx = None
#             best_dist = MATCH_THRESHOLD + 0.01

#             for i, enc in enumerate(face_encodings):
#                 dist = face_recognition.face_distance([ref_enc], enc)[0]
#                 if dist <= MATCH_THRESHOLD and dist < best_dist:
#                     best_dist = dist
#                     best_idx = i

#             if best_idx is not None:
#                 accuracy = round((1.0 - best_dist) * 100.0, 2)
#                 result['matched'] = True
#                 result['accuracy'] = accuracy
#                 photo_matched = True

#                 if accuracy > best_accuracy:
#                     best_accuracy = accuracy

#                 matched_photos.append({
#                     'path': group_path,
#                     'accuracy': accuracy,
#                     'filename': group_file.filename
#                 })

#                 print(f"   ✅ MATCH in {group_file.filename}: {accuracy}% accuracy")

#                 top, right, bottom, left = face_locations[best_idx]
#                 pil = Image.fromarray(group_img)
#                 crop = pil.crop((left, top, right, bottom))
#                 import io
#                 buf = io.BytesIO()
#                 crop.save(buf, format='JPEG')
#                 b64 = base64.b64encode(buf.getvalue()).decode('ascii')
#                 result['matchedImage'] = f"data:image/jpeg;base64,{b64}"
            
#             if not photo_matched:
#                 try:
#                     if os.path.exists(group_path):
#                         os.remove(group_path)
#                         print(f"   🗑️  NO MATCH - Deleted: {group_file.filename}")
#                 except Exception as e:
#                     print(f"   ⚠️  Could not delete {group_path}: {e}")

#         except Exception as e:
#             print(f"   ❌ Error processing {group_file.filename}: {e}")
#             try:
#                 if os.path.exists(group_path):
#                     os.remove(group_path)
#             except:
#                 pass

#         results.append(result)

#     if matched_photos:
#         if 'matched_faces' not in SUBMISSIONS[guest_id]:
#             SUBMISSIONS[guest_id]['matched_faces'] = []
        
#         SUBMISSIONS[guest_id]['matched_faces'].extend(matched_photos)
#         SUBMISSIONS[guest_id]['accuracy'] = best_accuracy
        
#         print(f"✅ Total matches for {guest_id}: {len(matched_photos)} new, {len(SUBMISSIONS[guest_id]['matched_faces'])} total")
#     else:
#         print(f"❌ No matches found for {guest_id} in this batch")

#     return jsonify({'results': results})


# # ==================== Admin List ====================
# @app.route('/api/admin/list', methods=['GET'])
# def admin_list():
#     """
#     Get all submissions for admin
#     ---
#     tags:
#       - Admin
#     responses:
#       200:
#         description: Admin list
#     """
#     out = []
#     for sid, s in SUBMISSIONS.items():
#         photo_b64 = None
#         if s['photo'] and os.path.exists(s['photo']):
#             try:
#                 with open(s['photo'], 'rb') as f:
#                     photo_b64 = "data:image/jpeg;base64," + base64.b64encode(f.read()).decode('ascii')
#             except Exception as e:
#                 print(f"Error reading photo for {sid}: {e}")
        
#         matched_faces = s.get('matched_faces', [])
        
#         out.append({
#             'id': sid,
#             'name': s['name'],
#             'email': s['email'],
#             'contact': s['contact'],
#             'photo': photo_b64,
#             'accuracy': s.get('accuracy') or 0,
#             'status': s.get('status', 'pending'),
#             'matched_count': len(matched_faces)
#         })
    
#     return jsonify(out)

# ==================== Email Helper (UPDATED WITH DYNAMIC SUPPORT) ====================
# def send_approval_email(to_email, name, attachment_paths=None):
#     """
#     Send approval email with multiple photo attachments
#     Supports both dynamic emails (production) and dummy emails (testing)
#     """
#     # Get the actual recipient (same as original in production, mapped in test mode)
#     original_email = to_email
#     actual_recipient = config.get_recipient_email(to_email)
    
#     # Determine if this is a "no photos found" email
#     has_photos = attachment_paths and len(attachment_paths) > 0

#     # Log email details
#     if config.LOG_EMAILS:
#         print(f"\n📧 ===== EMAIL DETAILS =====")
#         print(f"   Mode: {'TEST' if config.is_test_mode() else 'PRODUCTION'}")
#         print(f"   Original Email: {original_email}")
#         print(f"   Sending To: {actual_recipient}")
#         print(f"   Recipient Name: {name}")
#         print(f"   Email Type: {'PHOTOS FOUND' if has_photos else 'NO PHOTOS FOUND'}")
#         print(f"   Attachments: {len(attachment_paths) if attachment_paths else 0}")
        
#         if config.is_test_mode() and original_email != actual_recipient:
#             print(f"   🧪 TEST MODE: Email redirected")
#         print(f"========================\n")

#     msg = EmailMessage()
#     msg['Subject'] = 'Registration Approved - Your Event Photos'
#     msg['From'] = config.SMTP_CONFIG['user']
#     msg['To'] = actual_recipient
    
#     photo_count = len(attachment_paths) if attachment_paths else 0
    
#     # Add test mode note (only in test mode)
#     test_note = ""
#     if config.is_test_mode():
#         test_note = f"\n\n{'='*50}\n[TEST MODE]\nOriginal: {original_email}\nSent to: {actual_recipient}\n{'='*50}"
    
#     if has_photos:
#         # Email with photos found
#         photo_count = len(attachment_paths)
#         msg['Subject'] = 'Registration Approved - Your Event Photos'

#     msg.set_content(
#         f"Hello {name},\n\n"
#         f"Thank you for attending our event!\n\n"
#         f"Great news! We found {photo_count} photo(s) featuring you. "
#         f"{'All photos are attached to this email.' if photo_count > 0 else ''}\n\n"
#         f"We hope you had a wonderful time!\n\n"
#         f"Best regards,\n"
#         f"Event Team"
#         f"{test_note}"
#     )

#     # Attach ALL photos
#     if attachment_paths:
#         for idx, path in enumerate(attachment_paths, 1):
#             if os.path.exists(path):
#                 try:
#                     with open(path, 'rb') as f:
#                         data = f.read()
                    
#                     msg.add_attachment(
#                         data,
#                         maintype='image',
#                         subtype='jpeg',
#                         filename=f"event_photo_{idx}.jpg"
#                     )
#                     print(f"   📎 Attached photo {idx}/{photo_count}")
#                 except Exception as e:
#                     print(f"   ❌ Error attaching photo {idx}: {e}")

#     else:
#         # Email for no photos found
#         msg['Subject'] = 'Registration Update - No Photos Found'
        
#         msg.set_content(
#             f"Hello {name},\n\n"
#             f"Thank you for attending our event!\n\n"
#             f"We've processed your registration, but unfortunately we couldn't find any photos "
#             f"matching your reference image in our event photo collection.\n\n"
#             f"This could happen if:\n"
#             f"- You weren't captured in the group photos\n"
#             f"- The photo angles or lighting made matching difficult\n"
#             f"- The photos are still being processed\n\n"
#             f"If you believe this is an error or if you have any questions, please feel free to contact us.\n\n"
#             f"We hope you had a wonderful time at the event!\n\n"
#             f"Best regards,\n"
#             f"Event Team"
#             f"{test_note}"
#         )

#     # Send email
#     try:
#         with smtplib.SMTP(config.SMTP_CONFIG['host'], config.SMTP_CONFIG['port']) as server:
#             server.starttls()
#             server.login(config.SMTP_CONFIG['user'], config.SMTP_CONFIG['password'])
#             server.send_message(msg)
#         email_type = "photos found" if has_photos else "no photos found"
#         print(f"   ✅ Email sent successfully to {actual_recipient}")
#         return True
        
#     except Exception as e:
#         print(f"   ❌ Failed to send email: {e}")
#         raise

# # ==================== Admin Action ====================
# # ==================== Admin Action ====================
# @app.route('/api/admin/action', methods=['POST'])
# def admin_action():
#     """
#     Perform admin action (approve/reject/complete)
#     ---
#     tags:
#       - Admin
#     consumes:
#       - application/json
#     parameters:
#       - in: body
#         name: body
#         required: true
#         schema:
#           type: object
#           properties:
#             id:
#               type: string
#             action:
#               type: string
#               enum: [approve,reject,complete]
#     responses:
#       200:
#         description: Action performed
#     """
#     data = request.json
#     sid = data.get('id')
#     action = data.get('action')

#     print(f"🔍 Admin action request:")
#     print(f"   ID: {sid}")
#     print(f"   Action: {action}")

#     if not sid or not action:
#         return jsonify({'error': 'missing id or action'}), 400

#     if sid not in SUBMISSIONS:
#         print(f"❌ ID {sid} not found in submissions!")
#         return jsonify({'error': 'not found'}), 404

#     s = SUBMISSIONS[sid]

#     if action == 'approve':
#         s['status'] = 'approved'
        
#         # Get ALL matched photos
#         matched_faces = s.get('matched_faces', [])
        
#         if matched_faces:
#             # Extract just the paths from the list of dicts
#             photo_paths = [match['path'] for match in matched_faces]
#             print(f"📧 Sending email with {len(photo_paths)} matched photo(s):")
#         else:
#             # Fallback to guest's registration photo
#             photo_paths = []
#             print(f"📧 No matches found, sending 'no photos found' email")
        
#         try:
#             send_approval_email(s['email'], s['name'], photo_paths)
#             if photo_paths:
#                 message = f'Approved and email sent with {len(photo_paths)} photo(s)'
#                 print(f"✅ Approved: {s['name']} ({sid})")

#             else:
#                  message = 'Approved and "no photos found" email sent'
#                  print(f"✅ Approved without photos: {s['name']} ({sid})")
#             return jsonify({
#                 'message': message})
            
#         except Exception as e:
#             print(f"❌ Email failed but status updated: {e}")
#             return jsonify({
#                 'message': 'Approved but email failed',
#                 'error': str(e)
#             }), 207

#     elif action == 'reject':
#         s['status'] = 'rejected'
#         print(f"❌ Rejected: {s['name']} ({sid})")
#         return jsonify({'message': 'Rejected'})

#     elif action == 'complete':
#         s['status'] = 'completed'
#         print(f"✅ Completed: {s['name']} ({sid})")
#         return jsonify({'message': 'Marked completed'})

#     else:
#         return jsonify({'error': 'unknown action'}), 400

# ==================== Email Helper (FIXED VERSION) ====================
# def send_approval_email(to_email, name, attachment_paths=None):
#     """
#     Send approval email with multiple photo attachments
#     Supports both dynamic emails (production) and dummy emails (testing)
#     """
#     # Get the actual recipient (same as original in production, mapped in test mode)
#     original_email = to_email
#     actual_recipient = config.get_recipient_email(to_email)
    
#     # Determine if this is a "no photos found" email
#     has_photos = attachment_paths and len(attachment_paths) > 0

#     # Log email details
#     if config.LOG_EMAILS:
#         print(f"\n📧 ===== EMAIL DETAILS =====")
#         print(f"   Mode: {'TEST' if config.is_test_mode() else 'PRODUCTION'}")
#         print(f"   Original Email: {original_email}")
#         print(f"   Sending To: {actual_recipient}")
#         print(f"   Recipient Name: {name}")
#         print(f"   Email Type: {'PHOTOS FOUND' if has_photos else 'NO PHOTOS FOUND'}")
#         print(f"   Attachments: {len(attachment_paths) if attachment_paths else 0}")
        
#         if config.is_test_mode() and original_email != actual_recipient:
#             print(f"   🧪 TEST MODE: Email redirected")
#         print(f"========================\n")

#     msg = EmailMessage()
#     msg['From'] = config.SMTP_CONFIG['user']
#     msg['To'] = actual_recipient
    
#     # Add test mode note (only in test mode)
#     test_note = ""
#     if config.is_test_mode():
#         test_note = f"\n\n{'='*50}\n[TEST MODE]\nOriginal: {original_email}\nSent to: {actual_recipient}\n{'='*50}"
    
#     if has_photos:
#         # Email with photos found
#         photo_count = len(attachment_paths)
#         msg['Subject'] = 'Registration Approved - Your Event Photos'
        
#         msg.set_content(
#             f"Hello {name},\n\n"
#             f"Thank you for attending our event!\n\n"
#             f"Great news! We found {photo_count} photo(s) featuring you. "
#             f"All photos are attached to this email.\n\n"
#             f"We hope you had a wonderful time!\n\n"
#             f"Best regards,\n"
#             f"Event Team"
#             f"{test_note}"
#         )

#         # Attach ALL photos
#         for idx, path in enumerate(attachment_paths, 1):
#             if os.path.exists(path):
#                 try:
#                     with open(path, 'rb') as f:
#                         data = f.read()
                    
#                     msg.add_attachment(
#                         data,
#                         maintype='image',
#                         subtype='jpeg',
#                         filename=f"event_photo_{idx}.jpg"
#                     )
#                     print(f"   📎 Attached photo {idx}/{photo_count}")
#                 except Exception as e:
#                     print(f"   ❌ Error attaching photo {idx}: {e}")
#     else:
#         # Email for no photos found
#         msg['Subject'] = 'Registration Update - No Photos Found'
        
#         msg.set_content(
#             f"Hello {name},\n\n"
#             f"Thank you for attending our event!\n\n"
#             f"We've processed your registration, but unfortunately we couldn't find any photos "
#             f"matching your reference image in our event photo collection.\n\n"
#             f"This could happen if:\n"
#             f"- You weren't captured in the group photos\n"
#             f"- The photo angles or lighting made matching difficult\n"
#             f"- The photos are still being processed\n\n"
#             f"If you believe this is an error or if you have any questions, please feel free to contact us.\n\n"
#             f"We hope you had a wonderful time at the event!\n\n"
#             f"Best regards,\n"
#             f"Event Team"
#             f"{test_note}"
#         )
    

#     # Send email
#     try:
#         with smtplib.SMTP(config.SMTP_CONFIG['host'], config.SMTP_CONFIG['port']) as server:
#             server.starttls()
#             server.login(config.SMTP_CONFIG['user'], config.SMTP_CONFIG['password'])
#             server.send_message(msg)
        
#         email_type = "photos found" if has_photos else "no photos found"
#         print(f"   ✅ Email sent successfully ({email_type}) to {actual_recipient}")
#         return True
        
#     except Exception as e:
#         print(f"   ❌ Failed to send email: {e}")
#         raise


# # ==================== Admin Action (CORRECTED) ====================
# @app.route('/api/admin/action', methods=['POST'])
# def admin_action():
#     """
#     Perform admin action (approve/reject/complete)
#     ---
#     tags:
#       - Admin
#     consumes:
#       - application/json
#     parameters:
#       - in: body
#         name: body
#         required: true
#         schema:
#           type: object
#           properties:
#             id:
#               type: string
#             action:
#               type: string
#               enum: [approve,reject,complete]
#     responses:
#       200:
#         description: Action performed
#     """
#     data = request.json
#     sid = data.get('id')
#     action = data.get('action')

#     print(f"🔍 Admin action request:")
#     print(f"   ID: {sid}")
#     print(f"   Action: {action}")

#     if not sid or not action:
#         return jsonify({'error': 'missing id or action'}), 400

#     if sid not in SUBMISSIONS:
#         print(f"❌ ID {sid} not found in submissions!")
#         return jsonify({'error': 'not found'}), 404

#     s = SUBMISSIONS[sid]

#     if action == 'approve':
#         s['status'] = 'approved'
        
#         # Get ALL matched photos from group photos ONLY
#         matched_faces = s.get('matched_faces', [])
        
#         if matched_faces:
#             # Extract just the paths from the list of dicts
#             photo_paths = [match['path'] for match in matched_faces]
#             print(f"📧 Sending email with {len(photo_paths)} matched photo(s) from group photos")
#         else:
#             # No matches found - send empty list (NO reference photo)
#             photo_paths = []
#             print(f"📧 No matches found in group photos, sending 'no photos found' email")
        
#         try:
#             send_approval_email(s['email'], s['name'], photo_paths)
            
#             if photo_paths:
#                 message = f'Approved and email sent with {len(photo_paths)} photo(s)'
#                 print(f"✅ Approved with photos: {s['name']} ({sid})")
#             else:
#                 message = 'Approved and "no photos found" email sent'
#                 print(f"✅ Approved without photos: {s['name']} ({sid})")
            
#             return jsonify({'message': message})
            
#         except Exception as e:
#             print(f"❌ Email failed but status updated: {e}")
#             return jsonify({
#                 'message': 'Approved but email failed',
#                 'error': str(e)
#             }), 207

#     elif action == 'reject':
#         s['status'] = 'rejected'
#         print(f"❌ Rejected: {s['name']} ({sid})")
#         return jsonify({'message': 'Rejected'})

#     elif action == 'complete':
#         s['status'] = 'completed'
#         print(f"✅ Completed: {s['name']} ({sid})")
#         return jsonify({'message': 'Marked completed'})

#     else:
#         return jsonify({'error': 'unknown action'}), 400
    
# # ==================== Email Configuration Endpoints ====================
# @app.route('/api/admin/email-config', methods=['GET'])
# def get_email_config():
#     """
#     Get current email configuration
#     ---
#     tags:
#       - Admin
#     responses:
#       200:
#         description: Email configuration details
#     """
#     return jsonify({
#         'test_mode': config.TEST_MODE,
#         'mode_description': 'Test Mode (Dummy Emails)' if config.TEST_MODE else 'Production Mode (Real Emails)',
#         'use_single_email': config.USE_SINGLE_TEST_EMAIL if config.TEST_MODE else None,
#         'single_test_email': config.SINGLE_TEST_EMAIL if config.TEST_MODE else None,
#         'dummy_mappings_count': len(config.DUMMY_EMAIL_MAPPING) if config.TEST_MODE else 0,
#         'smtp_user': config.SMTP_CONFIG['user'],
#         'smtp_host': config.SMTP_CONFIG['host'],
#         'log_emails': config.LOG_EMAILS
#     })

# @app.route('/api/admin/email-config/toggle-test-mode', methods=['POST'])
# def toggle_test_mode():
#     """
#     Toggle between test mode and production mode
#     ---
#     tags:
#       - Admin
#     responses:
#       200:
#         description: Test mode toggled
#     """
#     config.TEST_MODE = not config.TEST_MODE
    
#     mode = 'Test Mode (Dummy Emails)' if config.TEST_MODE else 'Production Mode (Real Emails)'
    
#     print(f"🔄 Email mode changed to: {mode}")
    
#     return jsonify({
#         'test_mode': config.TEST_MODE,
#         'mode': mode,
#         'message': f"Switched to {mode}",
#         'warning': 'Emails will now be sent to REAL addresses!' if not config.TEST_MODE else 'Emails will be redirected to test addresses'
#     })

# @app.route('/api/admin/test-email', methods=['POST'])
# def test_email():
#     """
#     Send a test email to verify configuration
#     ---
#     tags:
#       - Admin
#     consumes:
#       - application/json
#     parameters:
#       - in: body
#         name: body
#         required: true
#         schema:
#           type: object
#           properties:
#             email:
#               type: string
#               description: Email to test
#             name:
#               type: string
#               description: Name for the test email
#     responses:
#       200:
#         description: Test email sent
#     """
#     data = request.json
#     email = data.get('email')
#     name = data.get('name', 'Test User')
    
#     if not email:
#         return jsonify({'error': 'Email address required'}), 400
    
#     try:
#         # Get actual recipient based on mode
#         actual_recipient = config.get_recipient_email(email)
        
#         # Send test email without attachments
#         send_approval_email(email, name, attachment_paths=None)
        
#         return jsonify({
#             'success': True,
#             'message': 'Test email sent successfully',
#             'original_email': email,
#             'actual_recipient': actual_recipient,
#             'test_mode': config.TEST_MODE,
#             'mode': 'Test Mode' if config.TEST_MODE else 'Production Mode'
#         })
#     except Exception as e:
#         return jsonify({
#             'success': False,
#             'error': str(e),
#             'message': 'Failed to send test email'
#         }), 500

# # ==================== Run App ====================
# if __name__ == '__main__':
#     print("🚀 Starting Flask server...")
#     print(f"📁 Data directory: {DATA_DIR}")
#     print(f"📧 Email mode: {'TEST MODE' if config.TEST_MODE else 'PRODUCTION MODE'}")
#     if config.TEST_MODE:
#         print(f"   ⚠️  Emails will be redirected to test addresses")
#     else:
#         print(f"   ✅ Emails will be sent to REAL recipient addresses")
#     print(f"📡 Server starting on http://127.0.0.1:5000")
#     print(f"📖 Swagger docs: http://127.0.0.1:5000/apidocs")
#     app.run(debug=True)

from flask import Flask, request, jsonify
from flask_cors import CORS
import os, uuid
from PIL import Image
import face_recognition
import base64
import smtplib
from email.message import EmailMessage
from flasgger import Swagger
import config  # Import the config module

app = Flask(__name__)
CORS(app)
swagger = Swagger(app)

DATA_DIR = 'data'
os.makedirs(DATA_DIR, exist_ok=True)

# Simple in-memory DB
SUBMISSIONS = {}  # id -> {name,email,contact,photo_path,accuracy,approved}
REF_ENCODINGS = {}  # ref_id -> face encoding

# Helper: save uploaded file
def save_upload(file_storage, prefix='file'):
    fname = f"{prefix}_{uuid.uuid4().hex}.jpg"
    path = os.path.join(DATA_DIR, fname)
    file_storage.save(path)
    return path

# ==================== Guest Registration ====================
@app.route('/api/guest/register', methods=['POST'])
def guest_register():
    """
    Register a guest
    ---
    tags:
      - Guest
    consumes:
      - multipart/form-data
    parameters:
      - in: formData
        name: name
        type: string
        required: true
      - in: formData
        name: email
        type: string
        required: true
      - in: formData
        name: contact
        type: string
        required: true
      - in: formData
        name: photo
        type: file
        required: true
    responses:
      200:
        description: Guest registered successfully
    """
    name = request.form.get('name')
    email = request.form.get('email')
    contact = request.form.get('contact')
    photo = request.files.get('photo')

    if not all([name, email, contact, photo]):
        return jsonify({'error': 'missing parameters'}), 400

    pid = uuid.uuid4().hex
    photo_path = save_upload(photo, prefix='guest')

    # Load image and encode face
    try:
        img = face_recognition.load_image_file(photo_path)
        encodings = face_recognition.face_encodings(img)

        if len(encodings) == 0:
            return jsonify({'error': 'no face detected in photo'}), 400

        REF_ENCODINGS[pid] = encodings[0]  # store face encoding for later match
    except Exception as e:
        print(f"Error encoding face: {e}")
        return jsonify({'error': 'failed to process photo'}), 500

    SUBMISSIONS[pid] = {
        'id': pid,
        'name': name,
        'email': email,
        'contact': contact,
        'photo': photo_path,
        'accuracy': None,
        'status': 'pending',
        'matched_faces': []
    }

    print(f"✅ Guest registered: {pid} - {name} ({email})")
    print(f"   Total submissions: {len(SUBMISSIONS)}")

    return jsonify({'status': 'ok', 'id': pid})

# ==================== Group Photo Upload ====================
@app.route('/api/photo/group', methods=['POST'])
def upload_group():
    """
    Upload one or multiple group photos and check if guest appears
    ---
    tags:
      - Photo
    consumes:
      - multipart/form-data
    parameters:
      - name: guest_id
        in: formData
        type: string
        required: true
        description: The ID of the registered guest to match in the uploaded group photos
      - name: group
        in: formData
        type: array
        items:
          type: file
        required: true
        description: One or more group photos to check for the guest
    responses:
      200:
        description: Matching results for each uploaded photo
    """
    MATCH_THRESHOLD = 0.5

    guest_id = request.form.get('guest_id')
    group_files = request.files.getlist('group')

    if not guest_id or not group_files:
        return jsonify({'error': 'guest_id and group photos required'}), 400

    if guest_id not in REF_ENCODINGS:
        return jsonify({'error': 'invalid guest_id'}), 400

    if guest_id not in SUBMISSIONS:
        return jsonify({'error': 'guest not found in submissions'}), 400

    ref_enc = REF_ENCODINGS[guest_id]
    results = []
    matched_photos = []
    best_accuracy = 0

    print(f"🔍 Processing {len(group_files)} photos for guest {guest_id}")

    for group_file in group_files:
        result = {
            'file_name': group_file.filename,
            'matched': False,
            'accuracy': 0,
            'matchedImage': None
        }

        group_path = save_upload(group_file, prefix='group')
        photo_matched = False

        try:
            group_img = face_recognition.load_image_file(group_path)
            face_locations = face_recognition.face_locations(group_img)
            face_encodings = face_recognition.face_encodings(group_img, known_face_locations=face_locations)

            print(f"   📸 {group_file.filename}: Found {len(face_encodings)} faces")

            best_idx = None
            best_dist = MATCH_THRESHOLD + 0.01

            for i, enc in enumerate(face_encodings):
                dist = face_recognition.face_distance([ref_enc], enc)[0]
                if dist <= MATCH_THRESHOLD and dist < best_dist:
                    best_dist = dist
                    best_idx = i

            if best_idx is not None:
                accuracy = round((1.0 - best_dist) * 100.0, 2)
                result['matched'] = True
                result['accuracy'] = accuracy
                photo_matched = True

                if accuracy > best_accuracy:
                    best_accuracy = accuracy

                matched_photos.append({
                    'path': group_path,
                    'accuracy': accuracy,
                    'filename': group_file.filename
                })

                print(f"   ✅ MATCH in {group_file.filename}: {accuracy}% accuracy")

                top, right, bottom, left = face_locations[best_idx]
                pil = Image.fromarray(group_img)
                crop = pil.crop((left, top, right, bottom))
                import io
                buf = io.BytesIO()
                crop.save(buf, format='JPEG')
                b64 = base64.b64encode(buf.getvalue()).decode('ascii')
                result['matchedImage'] = f"data:image/jpeg;base64,{b64}"
            
            if not photo_matched:
                try:
                    if os.path.exists(group_path):
                        os.remove(group_path)
                        print(f"   🗑️  NO MATCH - Deleted: {group_file.filename}")
                except Exception as e:
                    print(f"   ⚠️  Could not delete {group_path}: {e}")

        except Exception as e:
            print(f"   ❌ Error processing {group_file.filename}: {e}")
            try:
                if os.path.exists(group_path):
                    os.remove(group_path)
            except:
                pass

        results.append(result)

    if matched_photos:
        if 'matched_faces' not in SUBMISSIONS[guest_id]:
            SUBMISSIONS[guest_id]['matched_faces'] = []
        
        SUBMISSIONS[guest_id]['matched_faces'].extend(matched_photos)
        SUBMISSIONS[guest_id]['accuracy'] = best_accuracy
        
        print(f"✅ Total matches for {guest_id}: {len(matched_photos)} new, {len(SUBMISSIONS[guest_id]['matched_faces'])} total")
    else:
        print(f"❌ No matches found for {guest_id} in this batch")

    return jsonify({'results': results})


# ==================== Admin List ====================
@app.route('/api/admin/list', methods=['GET'])
def admin_list():
    """
    Get all submissions for admin
    ---
    tags:
      - Admin
    responses:
      200:
        description: Admin list
    """
    out = []
    for sid, s in SUBMISSIONS.items():
        photo_b64 = None
        if s['photo'] and os.path.exists(s['photo']):
            try:
                with open(s['photo'], 'rb') as f:
                    photo_b64 = "data:image/jpeg;base64," + base64.b64encode(f.read()).decode('ascii')
            except Exception as e:
                print(f"Error reading photo for {sid}: {e}")
        
        matched_faces = s.get('matched_faces', [])
        
        out.append({
            'id': sid,
            'name': s['name'],
            'email': s['email'],
            'contact': s['contact'],
            'photo': photo_b64,
            'accuracy': s.get('accuracy') or 0,
            'status': s.get('status', 'pending'),
            'matched_count': len(matched_faces)
        })
    
    return jsonify(out)

# ==================== Email Helpers ====================
def send_approval_email_with_photos(to_email, name, attachment_paths):
    """
    Send approval email WITH matched photos
    """
    original_email = to_email
    actual_recipient = config.get_recipient_email(to_email)
    
    if config.LOG_EMAILS:
        print(f"\n📧 ===== EMAIL: PHOTOS FOUND =====")
        print(f"   Mode: {'TEST' if config.is_test_mode() else 'PRODUCTION'}")
        print(f"   Original Email: {original_email}")
        print(f"   Sending To: {actual_recipient}")
        print(f"   Recipient Name: {name}")
        print(f"   Attachments: {len(attachment_paths)}")
        if config.is_test_mode() and original_email != actual_recipient:
            print(f"   🧪 TEST MODE: Email redirected")
        print(f"================================\n")

    msg = EmailMessage()
    msg['Subject'] = '🎉 Your Event Photos Are Here!'
    msg['From'] = config.SMTP_CONFIG['user']
    msg['To'] = actual_recipient
    
    photo_count = len(attachment_paths)
    
    test_note = ""
    if config.is_test_mode():
        test_note = f"\n\n{'='*50}\n[TEST MODE]\nOriginal: {original_email}\nSent to: {actual_recipient}\n{'='*50}"
    
    msg.set_content(
        f"Hello {name},\n\n"
        f"Thank you for attending our event!\n\n"
        f"🎊 Great news! We found {photo_count} photo(s) featuring you.\n"
        f"All your photos are attached to this email.\n\n"
        f"We hope you had a wonderful time!\n\n"
        f"Best regards,\n"
        f"Event Team"
        f"{test_note}"
    )

    # Attach ALL photos
    for idx, path in enumerate(attachment_paths, 1):
        if os.path.exists(path):
            try:
                with open(path, 'rb') as f:
                    data = f.read()
                
                msg.add_attachment(
                    data,
                    maintype='image',
                    subtype='jpeg',
                    filename=f"event_photo_{idx}.jpg"
                )
                print(f"   📎 Attached photo {idx}/{photo_count}")
            except Exception as e:
                print(f"   ❌ Error attaching photo {idx}: {e}")

    # Send email
    try:
        with smtplib.SMTP(config.SMTP_CONFIG['host'], config.SMTP_CONFIG['port']) as server:
            server.starttls()
            server.login(config.SMTP_CONFIG['user'], config.SMTP_CONFIG['password'])
            server.send_message(msg)
        
        print(f"   ✅ Email sent successfully to {actual_recipient}")
        return True
        
    except Exception as e:
        print(f"   ❌ Failed to send email: {e}")
        raise


def send_no_photos_email(to_email, name):
    """
    Send email when NO photos were found
    """
    original_email = to_email
    actual_recipient = config.get_recipient_email(to_email)
    
    if config.LOG_EMAILS:
        print(f"\n📧 ===== EMAIL: NO PHOTOS FOUND =====")
        print(f"   Mode: {'TEST' if config.is_test_mode() else 'PRODUCTION'}")
        print(f"   Original Email: {original_email}")
        print(f"   Sending To: {actual_recipient}")
        print(f"   Recipient Name: {name}")
        if config.is_test_mode() and original_email != actual_recipient:
            print(f"   🧪 TEST MODE: Email redirected")
        print(f"===================================\n")

    msg = EmailMessage()
    msg['Subject'] = 'Event Registration - No Photos Found'
    msg['From'] = config.SMTP_CONFIG['user']
    msg['To'] = actual_recipient
    
    test_note = ""
    if config.is_test_mode():
        test_note = f"\n\n{'='*50}\n[TEST MODE]\nOriginal: {original_email}\nSent to: {actual_recipient}\n{'='*50}"
    
    msg.set_content(
        f"Hello {name},\n\n"
        f"Thank you for attending our event!\n\n"
        f"We've reviewed all the event photos, but unfortunately we couldn't find any photos featuring you.\n\n"
        f"This could be because:\n"
        f"• You weren't captured in the group photos taken\n"
        f"We hope you had a wonderful time at the event!\n\n"
        f"Best regards,\n"
        f"Event Team"
        f"{test_note}"
    )

    # Send email (no attachments)
    try:
        with smtplib.SMTP(config.SMTP_CONFIG['host'], config.SMTP_CONFIG['port']) as server:
            server.starttls()
            server.login(config.SMTP_CONFIG['user'], config.SMTP_CONFIG['password'])
            server.send_message(msg)
        
        print(f"   ✅ Email sent successfully to {actual_recipient}")
        return True
        
    except Exception as e:
        print(f"   ❌ Failed to send email: {e}")
        raise


# ==================== Admin Action ====================
@app.route('/api/admin/action', methods=['POST'])
def admin_action():
    """
    Perform admin action (approve/reject/complete)
    ---
    tags:
      - Admin
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            id:
              type: string
            action:
              type: string
              enum: [approve,reject,complete]
    responses:
      200:
        description: Action performed
    """
    data = request.json
    sid = data.get('id')
    action = data.get('action')

    print(f"🔍 Admin action request:")
    print(f"   ID: {sid}")
    print(f"   Action: {action}")

    if not sid or not action:
        return jsonify({'error': 'missing id or action'}), 400

    if sid not in SUBMISSIONS:
        print(f"❌ ID {sid} not found in submissions!")
        return jsonify({'error': 'not found'}), 404

    s = SUBMISSIONS[sid]

    if action == 'approve':
        s['status'] = 'approved'
        
        # Get ALL matched photos
        matched_faces = s.get('matched_faces', [])
        
        try:
            if matched_faces and len(matched_faces) > 0:
                # SCENARIO 1: Photos found - send with attachments
                photo_paths = [match['path'] for match in matched_faces]
                print(f"📧 Sending email with {len(photo_paths)} matched photo(s)")
                send_approval_email_with_photos(s['email'], s['name'], photo_paths)
                
                return jsonify({
                    'success': True,
                    'message': f'✅ Approved! Email sent with {len(photo_paths)} photo(s)',
                    'scenario': 'photos_found',
                    'photo_count': len(photo_paths)
                })
            else:
                # SCENARIO 2: No photos found - send notification
                print(f"📧 Sending 'no photos found' email")
                send_no_photos_email(s['email'], s['name'])
                
                return jsonify({
                    'success': True,
                    'message': '✅ Approved! Email sent - No photos found',
                    'scenario': 'no_photos_found',
                    'photo_count': 0
                })
                
        except Exception as e:
            print(f"❌ Email failed but status updated: {e}")
            return jsonify({
                'success': False,
                'message': 'Approved but email failed',
                'error': str(e)
            }), 207

    elif action == 'reject':
        s['status'] = 'rejected'
        print(f"❌ Rejected: {s['name']} ({sid})")
        return jsonify({'message': 'Rejected'})

    elif action == 'complete':
        s['status'] = 'completed'
        print(f"✅ Completed: {s['name']} ({sid})")
        return jsonify({'message': 'Marked completed'})

    else:
        return jsonify({'error': 'unknown action'}), 400


# ==================== Email Configuration Endpoints ====================
@app.route('/api/admin/email-config', methods=['GET'])
def get_email_config():
    """
    Get current email configuration
    ---
    tags:
      - Admin
    responses:
      200:
        description: Email configuration details
    """
    return jsonify({
        'test_mode': config.TEST_MODE,
        'mode_description': 'Test Mode (Dummy Emails)' if config.TEST_MODE else 'Production Mode (Real Emails)',
        'use_single_email': config.USE_SINGLE_TEST_EMAIL if config.TEST_MODE else None,
        'single_test_email': config.SINGLE_TEST_EMAIL if config.TEST_MODE else None,
        'dummy_mappings_count': len(config.DUMMY_EMAIL_MAPPING) if config.TEST_MODE else 0,
        'smtp_user': config.SMTP_CONFIG['user'],
        'smtp_host': config.SMTP_CONFIG['host'],
        'log_emails': config.LOG_EMAILS
    })

@app.route('/api/admin/email-config/toggle-test-mode', methods=['POST'])
def toggle_test_mode():
    """
    Toggle between test mode and production mode
    ---
    tags:
      - Admin
    responses:
      200:
        description: Test mode toggled
    """
    config.TEST_MODE = not config.TEST_MODE
    
    mode = 'Test Mode (Dummy Emails)' if config.TEST_MODE else 'Production Mode (Real Emails)'
    
    print(f"🔄 Email mode changed to: {mode}")
    
    return jsonify({
        'test_mode': config.TEST_MODE,
        'mode': mode,
        'message': f"Switched to {mode}",
        'warning': 'Emails will now be sent to REAL addresses!' if not config.TEST_MODE else 'Emails will be redirected to test addresses'
    })

@app.route('/api/admin/test-email', methods=['POST'])
def test_email():
    """
    Send a test email to verify configuration
    ---
    tags:
      - Admin
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            email:
              type: string
              description: Email to test
            name:
              type: string
              description: Name for the test email
            scenario:
              type: string
              enum: [photos_found, no_photos]
              description: Which email scenario to test
    responses:
      200:
        description: Test email sent
    """
    data = request.json
    email = data.get('email')
    name = data.get('name', 'Test User')
    scenario = data.get('scenario', 'no_photos')
    
    if not email:
        return jsonify({'error': 'Email address required'}), 400
    
    try:
        actual_recipient = config.get_recipient_email(email)
        
        if scenario == 'photos_found':
            # Test with mock attachment path (use registration photo if available)
            send_approval_email_with_photos(email, name, [])
            scenario_msg = 'with photos'
        else:
            # Test no photos scenario
            send_no_photos_email(email, name)
            scenario_msg = 'no photos found'
        
        return jsonify({
            'success': True,
            'message': f'Test email sent successfully ({scenario_msg})',
            'original_email': email,
            'actual_recipient': actual_recipient,
            'test_mode': config.TEST_MODE,
            'scenario': scenario
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to send test email'
        }), 500

# ==================== Run App ====================
if __name__ == '__main__':
    print("🚀 Starting Flask server...")
    print(f"📁 Data directory: {DATA_DIR}")
    print(f"📧 Email mode: {'TEST MODE' if config.TEST_MODE else 'PRODUCTION MODE'}")
    if config.TEST_MODE:
        print(f"   ⚠️  Emails will be redirected to test addresses")
    else:
        print(f"   ✅ Emails will be sent to REAL recipient addresses")
    print(f"📡 Server starting on http://127.0.0.1:5000")
    print(f"📖 Swagger docs: http://127.0.0.1:5000/apidocs")
    app.run(debug=True)