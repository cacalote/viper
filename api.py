#!/usr/bin/env python
# This file is part of Viper - https://github.com/botherder/viper
# See the file 'LICENSE' for copying permission.

import os
import json
import argparse
import tempfile

from bottle import route, request, response, run
from bottle import HTTPError

from viper.common.objects import File
from viper.core.storage import store_sample, get_sample_path
from viper.core.database import Database

db = Database()

def jsonize(data):
    return json.dumps(data, sort_keys=False, indent=4)

@route('/test', method='GET')
def test():
    return jsonize({'message' : 'test'})

@route('/file/add', method='POST')
def add_file():
    tags = request.forms.get('tags')
    upload = request.files.get('file')

    tf = tempfile.NamedTemporaryFile()
    tf.write(upload.file.read())
    tf.flush()
    tf_obj = File(tf.name)
    tf_obj.name = upload.filename

    new_path = store_sample(tf_obj)

    success = False
    if new_path:
        # Add file to the database.
        success = db.add(obj=tf_obj, tags=tags)

    if success:
        return jsonize({'message' : 'added'})
    else:
        return HTTPError(500, 'Unable to store file')

@route('/file/get/<file_hash>', method='GET')
def get_file(file_hash):
    key = ''
    if len(file_hash) == 32:
        key = 'md5'
    elif len(file_hash) == 64:
        key = 'sha256'
    else:
        return HTTPError(400, 'Invalid hash format (use md5 or sha256)')

    db = Database()
    rows = db.find(key=key, value=file_hash)

    if not rows:
        raise HTTPError(404, 'File not found in the database')

    path = get_sample_path(rows[0].sha256)
    if not path:
        raise HTTPError(404, 'File not found in the repository')

    response.content_length = os.path.getsize(path)
    response.content_type = 'application/octet-stream; charset=UTF-8'
    data = ''
    for chunk in File(path).get_chunks():
        data += chunk

    return data

#Delete funtion
#TODO check for notes to be deleted as well
@route('/file/delete/<file_hash>', method='GET')
def delete_file(file_hash):
    success = False
    key = ''
    if len(file_hash) == 32:
        key = 'md5'
    elif len(file_hash) == 64:
        key = 'sha256'
    else:
        return HTTPError(400, 'Invalid hash format (use md5 or sha256)')

    db = Database()
    rows = db.find(key=key, value=file_hash)

    if not rows:
        raise HTTPError(404, 'File not found in the database')
	
    if rows:
		malware_id = rows[0].id
		path = get_sample_path(rows[0].sha256)
		if db.delete(malware_id):
			success = True
		else:
			raise HTTPError(404, 'File not found in repository')

    path = get_sample_path(rows[0].sha256)
    if not path:
        raise HTTPError(404, 'File not found in file system')
    else:	
        success=os.remove(path)
    
    if success:
        return jsonize({'message' : 'deleted'})
    else:
        return HTTPError(500, 'Unable to delete file')





@route('/file/find', method='POST')
def find_file():
    def details(row):
        tags = []
        for tag in row.tag:
            tags.append(tag.tag)

        entry = dict(
            id=row.id,
            name=row.name,
            type=row.type,
            size=row.size,
            md5=row.md5,
            sha1=row.sha1,
            sha256=row.sha256,
            sha512=row.sha512,
            crc32=row.crc32,
            ssdeep=row.ssdeep,
            created_at=row.created_at.__str__(),
            tags=tags
        )

        return entry

    for entry in ['md5', 'sha256', 'ssdeep', 'tag', 'name', 'all']:
        value = request.forms.get(entry)
        if value:
            key = entry
            break

    if not value:
        raise HTTPError(400, 'Invalid search term')

    rows = db.find(key=key, value=value)

    results = []
    for row in rows:
        entry = details(row)
        results.append(entry)

    return jsonize(results)

@route('/tags/list', method='GET')
def list_tags():
    rows = db.list_tags()

    results = []
    for row in rows:
        results.append(row.tag)

    return jsonize(results)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-H', '--host', help='Host to bind the API server on', default='localhost', action='store', required=False)
    parser.add_argument('-p', '--port', help='Port to bind the API server on', default=8080, action='store', required=False)
    args = parser.parse_args()

    run(host=args.host, port=args.port)
