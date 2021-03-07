#!/usr/bin/env python3
from http.server import HTTPServer, SimpleHTTPRequestHandler
import http.server
import xml.etree.ElementTree as ET
import os, io, socket, hashlib, base64
import binascii


update_version = "2.5.0.27"
port = 8000

response_ok = """<?xml version='1.0' encoding='UTF-8'?>
<response protocol="3.0" server="prod">
  <daystart elapsed_seconds="42548" elapsed_days="5179"/>
  <app status="ok" appid="{98DA7DF2-4E3E-4744-9DE6-EC931886ABAB}">
    <event status="ok"/>
    <ping status="ok"/>
  </app>
</response>
"""

response_template = """<?xml version="1.0" encoding="UTF-8"?>
 <response protocol="3.0" server="prod">
  <daystart elapsed_seconds="37145" elapsed_days="5179"/>
  <app status="ok" appid="{{98DA7DF2-4E3E-4744-9DE6-EC931886ABAB}}">
    <event status="ok"/>
    <updatecheck status="ok">
      <urls>
        <url codebase="{codebase_url}"/>
      </urls>
      <manifest version="{version}">
        <packages>
          <package required="true" hash="{update_sha1}" name="{update_name}" size="{update_size}"/>
        </packages>
        <actions>
          <action successsaction="default" sha256="{update_sha256}" event="postinstall" DisablePayloadBackoff="true"/>
        </actions>
      </manifest>
    </updatecheck>
    <ping status="ok"/>
  </app>
</response>
"""

def hostname():
    host = socket.gethostname()
    return f"http://{host}:{port}/"

def getupdateinfo(platform):
    if platform == "reMarkable2":
        update_name = "update_rm2"
    elif platform == "reMarkable":
        update_name =  "update_rm1"
    else:
        raise Exception("unknown platform")

    update_size = str(os.path.getsize(update_name))

    BUF_SIZE = 8192

    sha1 = hashlib.sha1()
    sha256 = hashlib.sha256()
    with open(update_name, 'rb') as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            sha1.update(data)
            sha256.update(data)
    update_sha1 = binascii.b2a_base64(sha1.digest(), newline=False).decode()
    update_sha256 = binascii.b2a_base64(sha256.digest(), newline=False).decode()
    return (update_name, update_sha1, update_sha256, update_size)


class MySimpleHTTPRequestHandler(SimpleHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get('Content-Length'))
        body = self.rfile.read(length).decode('utf-8')
        print(body)
        xml = ET.fromstring(body)
        event_node = xml.find('app/event')

        event_type = int(event_node.attrib["eventtype"])
        event_result = int(event_node.attrib["eventresult"])

        #post install status
        if event_result != 0:
            print("Update done")
            error_code = event_node.attrib["errorcode"]
            if error_code:
                print("With errorcode:", error_code)
            return


        #update done
        if event_type == 14:
            print("OK Response:")
            print(response_ok)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(response_ok.encode())
            return

        #check for update
        if event_type == 13 or event_type == 3:
            version = xml.attrib["version"]
            platform = xml.find('os').attrib['platform']
            print("requested: ", version)
            print("platform: ", platform)

            update_name, update_sha1, update_sha256, update_size = getupdateinfo(platform)
            host_name = hostname()
            params = {
                    "version": update_version,
                    "update_name": update_name,
                    "update_sha1": update_sha1,
                    "update_sha256": update_sha256,
                    "update_size" : update_size,
                    "codebase_url": host_name,
                    }

            response = response_template.format(**params)
            print("Response:")
            print(response)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(response.encode())
            return


httpd = HTTPServer(('0.0.0.0', port), MySimpleHTTPRequestHandler)
print(f"Starting fake updater: {port}")
httpd.serve_forever()