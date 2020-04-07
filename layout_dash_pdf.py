# -*- coding: utf-8 -*-

from flask import Flask, send_from_directory
import base64
import dash
from dash.dependencies import Input, Output, State
import dash_core_components as dcc
import dash_html_components as html
from PDF_highlight import *
from urllib.parse import quote as urlquote
import os

UPLOAD_DIRECTORY = "/tmp/pdf_highlight/"

if not os.path.exists(UPLOAD_DIRECTORY):
    os.makedirs(UPLOAD_DIRECTORY)

server = Flask(__name__)

app = dash.Dash(__name__, server=server)

@server.route("/download/<path:path>")
def download(path):
    """Serve a file from the upload directory."""
    return send_from_directory(UPLOAD_DIRECTORY, path, as_attachment=True)

app.layout = html.Div([html.H1('Extraction des textes et images surlignés',
                              style={
                                  'textAlign': 'center'
                              }),
                       dcc.Upload(
                           id='upload-pdf',
                           children=html.Div([
                               'Déposer ou ',
                               html.A('Selectionner',
                                     style={
                                         'text-decoration': 'underline',
                                         'text-decoration-color': 'blue',
                                         'color': 'blue'
                                     }),
                               ' le fichier PDF avec biffures'
                           ]),
                           style={
                               'width': '100%',
                               'height': '60px',
                               'lineHeight': '60px',
                               'borderWidth': '12px',
                               'borderStyle': 'solid',
                               'borderRadius': '5px',
                               'textAlign': 'center',
                               'margin': '10px',
                               'borderColor': 'yellow'
                           },
                           multiple=False
                       ),
                       html.Div(id='output-button'),
                      ])


def save_file(name, content):
    #first, delete all other files in the directory
    for filename in os.listdir(UPLOAD_DIRECTORY):
        file_path = os.path.join(UPLOAD_DIRECTORY, filename)
        if os.path.isfile(file_path) or os.path.islink(file_path):
            os.unlink(file_path)
    """Decode and store a file uploaded with Plotly Dash."""
    data = content.encode("utf8").split(b";base64,")[1]
    with open(os.path.join(UPLOAD_DIRECTORY, name), "wb") as fp:
        fp.write(base64.decodebytes(data))


def parse_contents(filename):
    out_name,out_location=extract_highlight_odf(filename)
    location = "/download/{}".format(urlquote(out_name))
    print(location)
    return html.Div([html.H5(filename),
                     html.P(f'Fichier {out_name} généré, cliquez ci-dessous pour télécharger :'),
                     html.A(html.Button('Télécharger')
                            ,href=location,download=out_name)
                    ],
                   style={
                       'textAlign': 'center'
                   })

@app.callback(Output('output-button', 'children'),[Input('upload-pdf', 'contents')],[State('upload-pdf', 'filename')])
def update_output(file,name):
    if name is not None:
        save_file(name,file)
        children = [parse_contents(name)]
        return children

if __name__ == '__main__':
    
    app.run_server(host='0.0.0.0')