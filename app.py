from flask import Flask, request, jsonify, render_template, send_file
import os
import io
import requests
import json
from werkzeug.utils import secure_filename
import datetime

app = Flask(__name__)

def get_access_token():
    token_url = 'https://accounts.zoho.com/oauth/v2/token'
    client_id = '1000.G3X5I57SWHT75F7LTYOYIAMELEBZCU'
    client_secret = '66c51517e1fcc097e8ea84ec4da8aff23f2db1095c'
    refresh_token = '1000.a209b7cc3fd66681b82712c6f76443fc.c58a139c51b92f8226b908fe646f8808'
    scope = 'ZohoSign.documents.ALL,ZohoSign.templates.ALL'

    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {
        'refresh_token': refresh_token,
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'refresh_token',
        'scope': scope
    }

    try:
        response = requests.post(token_url, headers=headers, data=data)
        response_data = response.json()
        if 'access_token' in response_data:
            return response_data['access_token']
        else:
            print('Access token not found in response:', response_data)
            return None
    except requests.exceptions.RequestException as e:
        print('Error fetching access token:', e)
        return None
    
def get_all_documents(access_token):
    headers = {
        'Authorization': 'Zoho-oauthtoken ' + access_token,
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    params = {
        'data': json.dumps({
            "page_context": {
                "row_count": 30,
                "start_index": 0,
                "search_columns": {},
                "sort_column": "",
                "sort_order": ""
            }
        })
    }

    url = 'https://sign.zoho.com/api/v1/requests'
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        documents = response.json()['requests']

        extracted_documents = []
        for document in documents:
            timestamp_ms =  document['created_time']
            timestamp_seconds = int(timestamp_ms) / 1000

            # Convert Unix timestamp to datetime object
            dt_object = datetime.datetime.fromtimestamp(timestamp_seconds)
            print('dt_object: ', dt_object)
            extracted_document = {
                'request_name': document['request_name'],
                'document_ids': document['document_ids'][0]['document_id'],
                'document_name': document['document_ids'][0]['document_name'],
                'request_status': document['request_status'],
                'reminder_period': document['reminder_period'],
                'expiration_days': document['expiration_days'],
                'templates_used': document['templates_used'],
                'request_id': document['request_id'],
                'created_time': dt_object,
                'owner_fullname': document['owner_first_name'] + ' ' + document['owner_last_name'],
            }
            extracted_documents.append(extracted_document)

        return extracted_documents

    except requests.exceptions.RequestException as e:
        print('Error fetching documents:', e)
        return []

@app.route('/download-document', methods=['POST'])
def download_document():
    try:
        document_id = request.form['document_id']
        access_token = get_access_token()

        headers = {
            'Authorization': 'Zoho-oauthtoken ' + access_token,
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        url = f'https://sign.zoho.com/api/v1/requests/{document_id}/pdf'

            # Construct the URL to the document hosted on Zoho Sign
        document_url = requests.Request('GET', url, headers=headers).prepare().url

        # Return the document URL
        return jsonify({'document_url': document_url})

    except Exception as e:
        return f"Error: {str(e)}", 500


def create_document(access_token, recipient_name, recipient_email, file_data):
    recipientName = recipient_name
    recipientEmail = recipient_email

    requestPayload = {
        "request_name": "test doc",
        "expiration_days": 10,
        "is_sequential": True,
        "notes": "Sign the document"
    }

    request = {
        "requests": requestPayload
    }

    data = json.dumps(request)
    files = {'file': file_data}

    url = "https://sign.zoho.com/api/v1/requests"
    headers = {
        'Authorization': 'Zoho-oauthtoken ' + access_token,
    }

    try:
        response = requests.post(url, headers=headers, files=files, data={'data': data})
        jsonbody = response.json()

        if response.status_code == 200 and jsonbody['status'] == "success":
            requestId = jsonbody['requests']['request_id']
            document_id = jsonbody['requests']['document_ids'][0]['document_id']

            actionsJson = {
                "action_type": "SIGN",
                "recipient_name": recipientName,
                "recipient_email": recipientEmail,
                "verify_recipient": False,
                "verification_type": "EMAIL",
                "signing_order": 0,
                "fields": [
                    {
                        "field_name": "Signature",
                        "field_label": "Text - 1",
                        "field_type_name": "Signature",
                        "field_category": "Signature",
                        "document_id": document_id,
                        "action_id": requestId,
                        "is_mandatory": True,
                        "x_coord": 100,
                        "y_coord": 100,
                        "abs_width": 40,
                        "abs_height": 30,
                        "page_no": 0,
                        "default_value": True,
                        "is_read_only": False,
                    }
                ]
            }

            dataJson = {
                "actions": [actionsJson]
            }

            request = {
                "requests": dataJson
            }

            data = json.dumps(request)

            submit_url = f"https://sign.zoho.com/api/v1/requests/{requestId}/submit"
            submit_headers = {
                'Authorization': 'Zoho-oauthtoken ' + access_token,
                'Content-Type': 'application/json'
            }

            submit_response = requests.post(submit_url, headers=submit_headers, data=data)
            submit_jsonbody = submit_response.json()

            if submit_response.status_code == 200 and submit_jsonbody['status'] == "success":
                return {
                    'status': submit_jsonbody['status'],
                    'request_id': submit_jsonbody['requests']['request_id'],
                    'request_status': submit_jsonbody['requests']['request_status'],
                    'owner_first_name': submit_jsonbody['requests']['owner_first_name'],
                    'owner_email': submit_jsonbody['requests']['owner_email']
                }
            else:
                return {
                    'status': 'error',
                    'message': submit_jsonbody['message']
                }
        else:
            return {
                'status': 'error',
                'message': jsonbody['message']
            }
    except requests.exceptions.RequestException as e:
        return {
            'status': 'error',
            'message': f"Error creating document: {str(e)}"
        }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get-data')
def get_data():
    access_token = get_access_token()
    if access_token:
        documents = get_all_documents(access_token)
        print('documents: ', documents)
        return jsonify({'data': documents})
    else:
        return jsonify({'error': 'Failed to obtain access token.'})
    
    

@app.route('/submit-form', methods=['POST'])
def submit_form():
    try:
        recipient_name = request.form["recipient_name"]
        recipient_email = request.form["recipient_email"]
        private_notes = request.form.get("private_notes", "")
        print('private_notes: ', private_notes)
        uploaded_file = request.files['file']
        print('uploaded_file: ', uploaded_file.filename)
        access_token = get_access_token()

        if access_token:
            file_data = (secure_filename(uploaded_file.filename), uploaded_file.stream, uploaded_file.content_type)
            document_status = create_document(access_token, recipient_name, recipient_email, file_data)
            if document_status['status'] == 'success':
                return jsonify(document_status), 200
            else:
                return jsonify(document_status), 500
        else:
            return jsonify({'status': 'error', 'message': 'Failed to get access token'}), 500

    except Exception as e:
        error_message = f"Error processing form data: {str(e)}"
        return jsonify({'status': 'error', 'message': error_message}), 500




if __name__ == '__main__':
    app.run(host='10.10.100.102', port=9090, debug=True)
