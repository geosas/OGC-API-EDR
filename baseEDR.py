# -*- coding: utf-8 -*-
"""
Created on Wed Dec 20 22:35:05 2023

@author: Tom
"""
import io
import os
import json
import numpy as np
import pandas as pd
import pyproj
import rioxarray
import shapely.wkt
from shapely.ops import transform

# import tempfile
import xarray as xr
import scipy


# class zarr objet methode
class zarr_query:
    def __init__(self, collection, dico_args, path):
        self.collection = collection
        self.dico_args = dico_args
        self.ds = xr.open_zarr(path)
        self.time_field = "time"
        self.conversion = False
        self.polygon_coordinate = False

    def make_datetime(self, datetime_):
        """Make xarray datetime query as pygeoapi

        Args:
        datetime_(string): time requested

        Returns:
            xarray datetime query
        """
        datetime_ = datetime_.rstrip("Z").replace("Z/", "/")
        if "/" in datetime_:
            begin, end = datetime_.split("/")
            if np.datetime64(begin) < np.datetime64(end):
                return slice(begin, end)
            else:
                print("Reversing slicing from high to low")
                return slice(end, begin)
        else:
            return slice(datetime_, datetime_)

    def configure_bbox(self, bbox):
        """Return xmin, ymin, xmax, ymax for xarray query as pygeoapi, + convert crs if needed and apply a buffer to the bbox if needed

        Args:
            bbox (list): requested bounding box

        Returns:
            xmin, ymin, xmax, ymax (float): bounding box for xarray
        """
        xmin, ymin, xmax, ymax = 0, 1, 2, 3

        if self.ds["x"][0] > self.ds["x"][-1]:
            xmin, xmax = xmax, xmin
        if self.ds["y"][0] > self.ds["y"][-1]:
            ymin, ymax = ymax, ymin

        if "crs" in self.dico_args:
            crs_rqt = self.dico_args["crs"]
            crs_data = self.ds.crs
            if any(
                x in [crs_rqt, crs_rqt.lower()] for x in [crs_data.upper(), crs_data]
            ):
                print("crs identique continue")
                xmin, xmax = bbox[xmin], bbox[xmax]
                ymin, ymax = bbox[ymin], bbox[ymax]
            else:
                print("convert crs")
                lamb2e_to_latlon = pyproj.Transformer.from_crs(
                    crs_rqt, crs_data, always_xy=True
                )
                xmin, ymin = lamb2e_to_latlon.transform(bbox[xmin], bbox[ymin])
                xmax, ymax = lamb2e_to_latlon.transform(bbox[xmax], bbox[ymax])
        else:
            xmin, xmax = bbox[xmin], bbox[xmax]
            ymin, ymax = bbox[ymin], bbox[ymax]
        # check si cell_size suffisament grande pour éviter de planter si la grille est du type x =1 ,y = .... ou x = ... ,y = 1
        cell_size = (self.ds.y.data.max() - self.ds.y.data.min()) / self.ds.sizes["y"]
        if ymax - ymin < (2 * cell_size):
            ymax += cell_size
            ymin += -cell_size
        cell_size = (self.ds.x.data.max() - self.ds.x.data.min()) / self.ds.sizes["x"]
        if xmax - xmin < (2 * cell_size):
            xmax += cell_size
            xmin += -cell_size

        return xmin, ymin, xmax, ymax

    def conversion_crs_bbox(self):
        crs_rqt = self.dico_args["crs"]
        crs_data = self.ds.crs
        if not any(
            x in [crs_rqt, crs_rqt.lower()] for x in [crs_data.upper(), crs_data]
        ):
            print("crs different, conversion")
            self.ds.rio.write_crs(crs_data, inplace=True)
            self.ds = self.ds.rio.reproject(crs_rqt)
            self.ds.attrs["crs"] = crs_rqt
            self.conversion = True

    def conversion_pts(self, pts: str):
        """_summary_

        Args:
            pts (str): _description_

        Returns:
            _type_: _description_
        """
        crs_rqt = self.dico_args["crs"]
        crs_data = self.ds.crs

        if any(i in [crs_rqt, crs_rqt.lower()] for i in [crs_data.upper(), crs_data]):
            print("crs identique continue")
            x = pts.x
            y = pts.y

            return x, y
        else:
            print("convert crs")
            lamb2e_to_latlon = pyproj.Transformer.from_crs(
                crs_rqt, crs_data, always_xy=True
            )
            x, y = lamb2e_to_latlon.transform(pts.x, pts.y)
            return x, y

    def conversion_crs_pts_result(self):
        crs_rqt = self.dico_args["crs"]
        crs_data = self.ds.crs
        if (
            any(x in [crs_rqt, crs_rqt.lower()] for x in [crs_data.upper(), crs_data])
            == False
        ):
            lamb2e_to_latlon = pyproj.Transformer.from_crs(
                crs_data, crs_rqt, always_xy=True
            )
            xc = self.ds.x.data
            yc = self.ds.y.data
            x, y = lamb2e_to_latlon.transform(xc, yc)
            self.ds.x.data = x
            self.ds.y.data = y
            self.ds.attrs["crs"] = crs_rqt

    def conversion_from_wkt_geom(self, geom):
        crs_rqt = self.dico_args["crs"]
        crs_data = self.ds.crs

        if any(i in [crs_rqt, crs_rqt.lower()] for i in [crs_data.upper(), crs_data]):
            print("crs identique continue")
            return geom
        else:
            lamb2e_to_latlon = pyproj.Transformer.from_crs(
                crs_rqt, crs_data, always_xy=True
            )
            geom = transform(lamb2e_to_latlon.transform, geom)
            return geom

    def aggregation_mtd(self, data, mtd):
        # self.ds[variable].mean(dim=["x", "y"], skipna=True).values.flatten().tolist()
        result_out = []
        if mtd == "mode":
            for i in data:
                vals, counts = np.unique(i, return_counts=True)
                index = np.argmax(counts)
                result_out.append(int(vals[index]))
        return result_out

    def covGeojsonGenerator(self, domainType):
        if domainType == "cube":
            cov = {
                "type": "Coverage",
                "domain": {
                    "type": "Domain",
                    "domainType": "Grid",
                    "axes": {
                        "x": {
                            "start": float(self.ds.x.data.min()),
                            "stop": float(self.ds.x.data.max()),
                            "num": int(self.ds.sizes["x"]),
                        },
                        "y": {
                            "start": float(self.ds.y.data.min()),
                            "stop": float(self.ds.y.data.max()),
                            "num": int(self.ds.sizes["y"]),
                        },
                        "t": {
                            "start": str(self.ds.time.data.min()),
                            "stop": str(self.ds.time.data.max()),
                            "num": int(self.ds.sizes["time"]),
                        },
                    },
                    "referencing": [
                        {
                            "coordinates": ["x", "y"],
                            "system": {"type": "GeographicCRS", "id": self.ds.crs},
                        },
                        {
                            "coordinates": "t",
                            "system": {"type": "TemporalCRS", "calendar": "Gregorian"},
                        },
                    ],
                },
                "parameters": {},
                "ranges": {},
            }

        elif domainType == "area":
            cov = {
                "type": "Coverage",
                "domain": {
                    "type": "Domain",
                    "domainType": "PolygonSeries",
                    "axes": {
                        "composites": {
                            "dataType": "polygon",
                            "coordinates": ["x", "y"],
                            "values": [[self.polygon_coordinate]],
                        },
                        "t": {
                            "values": list(
                                self.ds.time.dt.strftime("%Y-%m-%dT%H-%M-%SZ").data
                            )
                        },
                    },
                    "referencing": [
                        {
                            "coordinates": ["x", "y"],
                            "system": {"type": "GeographicCRS", "id": self.ds.crs},
                        },
                        {
                            "coordinates": "t",
                            "system": {"type": "TemporalCRS", "calendar": "Gregorian"},
                        },
                    ],
                },
                "parameters": {},
                "ranges": {},
            }

        elif domainType == "point":
            cov = {
                "type": "Coverage",
                "domain": {
                    "type": "Domain",
                    "domainType": "Point",
                    "axes": {
                        "x": {"value": float(self.ds.x.data)},
                        "y": {"value": float(self.ds.y.data)},
                        "t": {
                            "values": list(
                                self.ds.time.dt.strftime("%Y-%m-%dT%H-%M-%SZ").data
                            ),
                        },
                    },
                    "referencing": [
                        {
                            "coordinates": ["x", "y"],
                            "system": {"type": "GeographicCRS", "id": self.ds.crs},
                        },
                        {
                            "coordinates": "t",
                            "system": {"type": "TemporalCRS", "calendar": "Gregorian"},
                        },
                    ],
                },
                "parameters": {},
                "ranges": {},
            }

        if domainType != "area":
            self.ds = self.ds.fillna(None)

        for variable in self.ds:
            parameter = {
                "type": "Parameter",
                "description": str(self.ds[variable].attrs["description"]),
                "unit": {
                    "label": str(self.ds[variable].attrs["unit"]["label"]),
                    "symbol": {
                        "type": str(self.ds[variable].attrs["unit"]["symbol"]["type"]),
                        "value": str(
                            self.ds[variable].attrs["unit"]["symbol"]["value"]
                        ),
                    },
                },
                "observedProperty": {
                    "id": str(self.ds[variable].attrs["observedProperty"]["id"]),
                    "label": str(self.ds[variable].attrs["observedProperty"]["label"]),
                },
            }
            cov["parameters"][variable] = parameter

            print("le replace nan vers null")
            # data = self.ds[variable].data
            # data = data.flatten()
            # aa=pd.DataFrame()
            # aa['data']=data
            # aa=aa.replace(to_replace=np.nan, value=None)
            # print("fin du replace nan vers null")

            if domainType in ["cube"]:
                shape_y = int(self.ds.sizes["y"])
                shape_x = int(self.ds.sizes["x"])
                shape_t = int(self.ds.sizes["time"])

                print(self.ds.dims)
                if self.conversion == True:
                    if len(self.ds.dims.mapping.keys()) == 2:
                        print("transpose data 2dim")
                        shape = (shape_y, shape_x)
                        val_out = np.reshape(self.ds[variable].values.flatten(), shape)
                        val_out = np.flipud(val_out)
                        val_out = val_out.flatten().tolist()

                    elif len(self.ds.dims.mapping.keys()) == 3:
                        print("transpose data 3dim")

                        shape = (shape_y, shape_x, shape_t)
                        print(shape)
                        val_out = np.reshape(self.ds[variable].values.flatten(), shape)
                        val_out = np.flipud(val_out)
                        val_out = val_out.flatten().tolist()

                else:
                    val_out = self.ds[variable].values.flatten().tolist()

                cov["ranges"][variable] = {
                    "type": "NdArray",
                    "dataType": str(self.ds[variable].data.dtype),
                    "axisNames": ["y", "x", "t"],
                    "shape": [
                        int(self.ds.sizes["y"]),
                        int(self.ds.sizes["x"]),
                        int(self.ds.sizes["time"]),
                    ],
                    #'values' : list(aa['data'])
                    #'values' : self.ds[variable].values.flatten().tolist()
                    "values": val_out,
                }
            elif domainType == "area":
                # json.dumps(list(aa['data']))
                cov["ranges"][variable] = {
                    "type": "NdArray",
                    "dataType": str(self.ds[variable].data.dtype),
                    "axisNames": ["t"],
                    "shape": [int(self.ds.sizes["time"])],
                    #'values' : list(aa['data'])
                    "values": self.aggregation_mtd(self.ds[variable].values, "mode"),
                }
            elif domainType == "point":
                # json.dumps(list(aa['data']))
                cov["ranges"][variable] = {
                    "type": "NdArray",
                    "dataType": str(self.ds[variable].data.dtype),
                    "axisNames": ["t"],
                    "shape": [int(self.ds.sizes["time"])],
                    #'values' : list(aa['data'])
                    "values": self.ds[variable].values.flatten().tolist(),
                }
        return cov

    def netcdfGenerator(self):
        encoder = {}
        # encoding={'air': {'_FillValue': -999.0},'x': {'_FillValue': -999.0},'y': {'_FillValue': -999.0}}
        for i in self.ds:
            if "categoryEncoding" in self.ds[i].attrs:
                self.ds[i].attrs["observedProperty"] = json.dumps(
                    self.ds[i].attrs["observedProperty"]
                )
                self.ds[i].attrs["categoryEncoding"] = json.dumps(
                    self.ds[i].attrs["categoryEncoding"]
                )
            else:
                self.ds[i].attrs["observedProperty"] = self.ds[i].attrs[
                    "observedProperty"
                ]["id"]

            encoder[i] = {"_FillValue": -999.0}
            self.ds[i].attrs["unit label"] = self.ds[i].attrs["unit"]["label"]
            self.ds[i].attrs["unit"] = self.ds[i].attrs["unit"]["symbol"]["value"]
            del self.ds[i].attrs["measurementType"]
            # si netcdf 4 ou 5 peut gérer dict ou list
            # self.ds.FF_Q.attrs['measurementType']=[(k,v) for k,v in self.ds.FF_Q.attrs['measurementType'].items()]
            # self.ds.FF_Q.attrs['observedProperty']=[(k,v) for k,v in self.ds.FF_Q.attrs['observedProperty'].items()]
            # self.ds.FF_Q.attrs['unit']=[(k,v) for k,v in self.ds.FF_Q.attrs['unit'].items()]

            encoder["x"] = {"_FillValue": -999.0}
            encoder["y"] = {"_FillValue": -999.0}
            del self.ds.attrs["extent"]
            del self.ds.attrs["keywords"]

            for i in self.ds.attrs["links"]:
                self.ds.attrs["rel"] = i["href"]
            del self.ds.attrs["links"]

        netcdf_out = self.ds.to_netcdf(engine="scipy", encoding=encoder)

        return netcdf_out

    def cube(self):
        # z=False, formatage=False
        print("methode cube")
        dico_query = {}

        bbox = [float(i) for i in self.dico_args["bbox"].split(",")]
        xmin, ymin, xmax, ymax = self.configure_bbox(bbox)

        dico_query["x"] = slice(xmin, xmax)
        dico_query["y"] = slice(ymin, ymax)

        if "datetime" in self.dico_args:
            dico_query["time"] = self.make_datetime(self.dico_args["datetime"])

        print(dico_query)
        if "parameter-name" in self.dico_args:
            self.ds = self.ds[self.dico_args["parameter-name"].split(",")]

        # selection
        self.ds = self.ds.sel(dico_query)
        print("x", self.ds.sizes["x"])  # pour débugage à enlever après
        print("y", self.ds.sizes["y"])  # pour débugage à enlever après

        print("check crs")
        if "crs" in self.dico_args:
            self.conversion_crs_bbox()

        print("check dims")
        for i in self.ds.dims:
            if self.ds.sizes[i] == 0:
                print(i, "no data")
                return {
                    "response": "no data for " + i,
                    "informations": "l'api est encore mode béta, si vous pensez qu'il y a un bug ou que vous rencontrez des difficultés, ouvrez une issues sur notre github",
                    "github": "https://github.com/geosas/OGC-API-EDR",
                }

        print("check format")
        if "f" in self.dico_args:
            print(self.dico_args["f"])
            if self.dico_args["f"] == "CoverageJSON":
                # où sont gérer les nulls ?
                cov = self.covGeojsonGenerator("cube")
                print("geojson finish")
                return cov

            elif self.dico_args["f"] == "CSV":  # faire une fonction....
                df = self.ds.to_dataframe()
                df = df.dropna()
                if "spatial_ref" in df.columns:
                    df = df.drop(columns="spatial_ref")
                df_response = io.BytesIO()
                df.to_csv(df_response)
                df_response.seek(0)
                print("csv finish")
                return df_response
            else:
                # p2 =  tempfile.TemporaryFile()
                p2 = io.BytesIO()
                netcdf_out = self.netcdfGenerator()

                p2.write(netcdf_out)
                p2.seek(0)
                return p2
        else:
            # p2 =  tempfile.TemporaryFile()
            p2 = io.BytesIO()
            netcdf_out = self.netcdfGenerator()

            p2.write(netcdf_out)
            p2.seek(0)
            return p2

    def position(self):
        print("methode position")
        dico_query = {}
        time_query = {}
        pts = shapely.wkt.loads(self.dico_args["coords"])

        if "crs" in self.dico_args:
            x, y = self.conversion_pts(pts)
        else:
            x = pts.x
            y = pts.y

        dico_query["x"] = x
        dico_query["y"] = y

        if "datetime" in self.dico_args:
            time_query["time"] = self.make_datetime(self.dico_args["datetime"])

        print(dico_query)
        if "parameter-name" in self.dico_args:
            self.ds = self.ds[self.dico_args["parameter-name"].split(",")]
        try:
            self.ds = self.ds.sel(time_query).sel(
                x=dico_query["x"], y=dico_query["y"], method="nearest"
            )
        except:
            return {
                "response": "no data here",
                "informations": "l'api est encore mode béta, si vous pensez qu'il y a un bug ou que vous rencontrez des difficultés, ouvrez une issues sur notre github",
                "github": "https://github.com/geosas/OGC-API-EDR",
            }  # à changer par csv vide

        for i in self.ds.dims:
            if self.ds.sizes[i] == 0:
                print(i, "no data")
                return {
                    "response": "no data here for " + i,
                    "informations": "l'api est encore mode béta, si vous pensez qu'il y a un bug ou que vous rencontrez des difficultés, ouvrez une issues sur notre github",
                    "github": "https://github.com/geosas/OGC-API-EDR",
                }

        print("check crs")
        if "crs" in self.dico_args:
            print("verifie crs si conversion")
            self.conversion_crs_pts_result()

        print("mise en forme selon choix user")
        if "f" in self.dico_args:
            print("mise en forme", self.dico_args["f"])
            if self.dico_args["f"] == "CoverageJSON":
                cov = self.covGeojsonGenerator("point")
                return cov

            elif self.dico_args["f"] == "CSV":
                df = self.ds.to_dataframe()
                df = df.dropna()
                df_response = io.BytesIO()
                df.to_csv(df_response)
                df_response.seek(0)
                print("csv finish")
                return df_response
            else:
                # p2 =  tempfile.TemporaryFile()
                p2 = io.BytesIO()
                netcdf_out = self.netcdfGenerator()

                p2.write(netcdf_out)
                p2.seek(0)
                return p2
        else:
            # p2 =  tempfile.TemporaryFile()
            p2 = io.BytesIO()
            netcdf_out = self.netcdfGenerator()

            p2.write(netcdf_out)
            p2.seek(0)
            return p2

    def area(self):
        print("methode area")
        dico_query = {}
        time_query = {}
        poly = shapely.wkt.loads(self.dico_args["coords"])

        if "crs" in self.dico_args:
            crs_rqt = self.dico_args["crs"]
            poly = self.conversion_from_wkt_geom(poly)

        if "datetime" in self.dico_args:
            time_query["time"] = self.make_datetime(self.dico_args["datetime"])

        print(dico_query)
        if "parameter-name" in self.dico_args:
            self.ds = self.ds[self.dico_args["parameter-name"].split(",")]

        x = poly.exterior.coords.xy[0]
        y = poly.exterior.coords.xy[1]
        try:
            crs_data = self.ds.crs
            self.ds.rio.write_crs(self.ds.crs, inplace=True)
            self.ds.attrs["crs"] = crs_data
            self.ds = self.ds.sel(time_query)
            self.ds = self.ds.sel(
                x=slice(min(x), max(x), None), y=slice(min(y), max(y), None)
            )
            # list(zip(*poly.exterior.coords.xy)
            poly = []
            for i in range(len(x)):
                poly.append([x[i], y[i]])

            geometries = [{"type": "Polygon", "coordinates": [poly]}]
            self.ds = self.ds.rio.clip(geometries, self.ds.crs)
        except Exception as e:
            print(str(e))
            return {
                "response": "no data here",
                "informations": "l'api est encore mode béta, si vous pensez qu'il y a un bug ou que vous rencontrez des difficultés, ouvrez une issues sur notre github",
                "github": "https://github.com/geosas/OGC-API-EDR",
            }  # à changer par csv vide

        for i in self.ds.dims:
            if self.ds.sizes[i] == 0:
                print(i, "no data")
                return {
                    "response": "no data here for " + i,
                    "informations": "l'api est encore mode béta, si vous pensez qu'il y a un bug ou que vous rencontrez des difficultés, ouvrez une issues sur notre github",
                    "github": "https://github.com/geosas/OGC-API-EDR",
                }

        print("check crs")
        if "crs" in self.dico_args:
            self.conversion_crs_bbox()

        print("mise en forme selon choix user")
        if "f" in self.dico_args:
            print("mise en forme", self.dico_args["f"])
            if self.dico_args["f"] == "CoverageJSON":
                self.polygon_coordinate = poly
                cov = self.covGeojsonGenerator("area")
                return cov

            elif self.dico_args["f"] == "CSV":
                df = self.ds.to_dataframe()
                df = df.dropna()
                df_response = io.BytesIO()
                df.to_csv(df_response)
                df_response.seek(0)
                print("csv finish")
                return df_response
            else:
                # p2 =  tempfile.TemporaryFile()
                p2 = io.BytesIO()
                netcdf_out = self.netcdfGenerator()

                p2.write(netcdf_out)
                p2.seek(0)
                return p2
        else:
            # p2 =  tempfile.TemporaryFile()
            p2 = io.BytesIO()
            netcdf_out = self.netcdfGenerator()

            p2.write(netcdf_out)
            p2.seek(0)
            return p2

    def radius(self, variable, point, distance, date=False, z=False, formatage=False):
        print("methode radius")

    def line(self, variable, line, date=False, z=False, formatage=False):
        print("methode line")


class edr_base:
    def __init__(self, configJson, apiUrl):
        self.configJson = configJson
        self.apiUrl = apiUrl

    def open_zarr_set_config(self):
        for i in self.configJson:
            try:
                # open zarr et test si les metadata obligatoire sont présente
                print(i)
                ds = xr.open_zarr(self.configJson[i]["path"])
                self.configJson[i]["id"] = i
                self.configJson[i]["title"] = ds.attrs["title"]
                self.configJson[i]["description"] = ds.attrs["description"]
                self.configJson[i]["keywords"] = ds.attrs["keywords"]
                self.configJson[i]["links"] = ds.attrs["links"]
                self.configJson[i]["links"].append(
                    {
                        "href": f"{self.apiUrl}collections/{i}",
                        "rel": "service",
                        "type": "application/json",
                    }
                )
                self.configJson[i]["extent"] = ds.attrs["extent"]
                self.configJson[i]["crs"] = ds.attrs["crs"]

                self.configJson[i]["parameter_names"] = []
                for z in ds:
                    dico_variable = {z: {}}
                    for attr in ds[z].attrs:
                        dico_variable[z][attr] = ds[z].attrs[attr]

                    self.configJson[i]["parameter_names"].append(dico_variable)
                    # if no units error, écrit rapport et saute cette variable
            except:
                print(i, "error in this zarr")
        print("write config")
        with open(
            os.path.dirname(os.path.abspath(__file__))
            + "/config_api/config_en_cours.json",
            "w",
            encoding="utf8",
        ) as outfile:
            outfile.write(json.dumps(self.configJson, indent=4, ensure_ascii=False))

    def collection(self, name=False):
        if name != False:
            collec = {}
            for key in self.configJson[name]:
                if key == "path":
                    continue
                collec[key] = self.configJson[name][key]

        else:
            collec = {"collections": []}
            for i in self.configJson:
                obj = {}
                for key in self.configJson[i]:
                    if key == "path":
                        continue
                    obj[key] = self.configJson[i][key]
                collec["collections"].append(obj)

        return collec

    def cube_rqt(self, dict_input):
        collection = dict_input["collection"]  # from url
        path = self.configJson[collection]["path"]
        rqt = zarr_query(collection, dict_input, path)
        return rqt.cube()

    def position_rqt(self, dict_input):
        collection = dict_input["collection"]  # from url
        path = self.configJson[collection]["path"]
        rqt = zarr_query(collection, dict_input, path)
        return rqt.position()

    def area_rqt(self, dict_input):
        collection = dict_input["collection"]  # from url
        path = self.configJson[collection]["path"]
        rqt = zarr_query(collection, dict_input, path)
        return rqt.area()
