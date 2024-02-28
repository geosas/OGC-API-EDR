# -*- coding: utf-8 -*-
"""
Created on Wed Dec 20 22:35:05 2023

@author: Tom
"""
import os
from flask import Flask, send_file, request, jsonify, url_for
from flasgger import Swagger, swag_from
import json

from baseEDR import edr_base
from test_api_edr_perso import TestApiEDR


app = Flask(__name__)
app.json.sort_keys = False

with open(
    os.path.dirname(os.path.abspath(__file__)) + "/base.json", "r", encoding="utf-8"
) as src:
    landing_page = json.load(src)

with open(
    os.path.dirname(os.path.abspath(__file__)) + "/config.json", "r", encoding="utf-8"
) as src:
    data_src = json.load(src)


SWAGGER_TEMPLATE = {
    "tags": [
        {
            "name": "Capabilities",
            "description": "Essential characteristics of the information available from the API.",
        },
        {
            "name": "Collection metadata",
            "description": "Description of the information available from the collections",
        },
        {"name": "Collection data queries", "description": "Data queries available."},
    ],
    "info": {
        "title": "Environmental Data Retrieval (EDR), GéoSAS SAFRAN-ISBA",
        "version": "0.000001",
        "description": "Api documentation for EDR SAFRAN-ISBA",
        "termsOfService": "https://www.etalab.gouv.fr/licence-ouverte-open-licence/",
    },
}
SWAGGER_CONFIG = {
    "uiversion": 3,
    "openapi": "3.0.3",
    "title": "API EDR GEOSAS",
    "swagger_version": "2.0",
    "hide_top_bar": True,
    "servers": [
        {
            "url": "https://api.geosas.fr/",
            "description": "Serveur en production",
        }
    ],
    "specs": [
        {
            "version": "0.1",
            "endpoint": "base",
            "route": "/openapi",
            # rule_filter is optional
            # it is a callable to filter the views to extract
        }
    ],
    "url_prefix": "/edr",
    "specs_route": "/apidocs/",
}

swagger = Swagger(app, template=SWAGGER_TEMPLATE, config=SWAGGER_CONFIG, merge=True)

instance = edr_base(data_src)
instance.open_zarr_set_config()


@app.route("/edr/", methods=["GET"])
@swag_from("documentation/landing.yml")
def base():
    return jsonify(landing_page)


@app.route("/edr/collections/", methods=["GET"])
@swag_from("documentation/collections.yml")
def collections():
    collec = instance.collection()
    return jsonify(collec)


@app.route("/edr/collections/<string:collectionId>/", methods=["GET"])
@swag_from("documentation/instance.yml")
def collection(collectionId):
    collec = instance.collection(collectionId)
    return jsonify(collec)


@app.route("/edr/collections/<string:collectionId>/cube", methods=["GET"])
@swag_from("documentation/cube.yml")
def cube(collectionId):
    try:
        arg = request.args.to_dict()

        if "bbox" not in arg:
            return jsonify({"error": "parametre bbox obligatoire"})
        arg["collection"] = collectionId
        print(arg)
        output = instance.cube_rqt(arg)
        print("rqt cube finish prepapre fichier")
        if isinstance(output, dict):
            return jsonify(output)
        if arg["f"] == "CSV":
            return send_file(output, download_name="extract.csv", as_attachment=True)

        return send_file(output, download_name="cube.nc", as_attachment=True)
    except:
        return jsonify(
            {
                "response": "erreur de syntaxe",
                "Plus d'information sur la syntaxe Cube": "https://docs.ogc.org/is/19-086r6/19-086r6.html#_fe30ac95-7038-4dd1-902d-f4fcd2f31c8d",
            }
        )


@app.route("/edr/collections/<string:collectionId>/position", methods=["GET"])
@swag_from("documentation/positions.yml")
def position(collectionId):
    try:
        arg = request.args.to_dict()
        if "coords" not in arg:
            return jsonify({"error": "parametre coords obligatoire"})
        arg["collection"] = collectionId
        print(arg)
        output = instance.position_rqt(arg)
        if isinstance(output, dict):
            return jsonify(output)
        if arg["f"] == "CSV":
            return send_file(output, download_name="extract.csv", as_attachment=True)

        return send_file(output, download_name="position.nc", as_attachment=True)
    except:
        return jsonify(
            {
                "response": "erreur de syntaxe",
                "Plus d'information sur la syntaxe Position": "https://docs.ogc.org/is/19-086r6/19-086r6.html#_bbda46d4-04c5-426b-bea3-230d592fe1c2",
            }
        )


@app.route("/edr/collections/<string:collectionId>/area", methods=["GET"])
@swag_from("documentation/area.yml")
def area(collectionId):
    arg = request.args.to_dict()
    if "coords" not in arg:
        return jsonify({"error": "parametre coords obligatoire"})
    arg["collection"] = collectionId
    print(arg)
    output = instance.area_rqt(arg)
    if isinstance(output, dict):
        return jsonify(output)
    if arg["f"] == "CSV":
        return send_file(output, download_name="extract.csv", as_attachment=True)

    return send_file(output, download_name="area.nc", as_attachment=True)


@app.route("/edr/test_api/", methods=["GET"])
def test_api():
    url_service = "https://api.geosas.fr/edr"
    testeur = TestApiEDR(url_service, instance.collection(), [60000, 2401000])
    retour = testeur.run_test()
    return jsonify(retour)
