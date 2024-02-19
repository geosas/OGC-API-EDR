#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jan  3 15:27:40 2024

@author: tloree
"""
import requests
import json
from dateutil.parser import parse
from datetime import timedelta
import pyproj

class TestApiEDR():
    def __init__(self,url_service, config_service,point_test=False):
        self.url_service = url_service
        #with open(config_service) as cf:
        #    self.config_service =json.load(cf)
        self.retour={}
        self.config_service={}
        self.point_test=point_test

    def accueil(self):
        self.retour['accueil']={}
        for i in ['','/']:
            r = requests.get(self.url_service+i)
            try:
                self.retour['accueil']['url '+i] = {"connexion": "ok", "type":r.headers['Content-Type'], "code": r.status_code,'rqt':self.url_service+i }
                if r.status_code in [200,201]:
                    print(self.url_service+i,"ok")
                else:
                    print(self.url_service+i,"error")
            except:
                self.retour['accueil']['url '+i] = {"format json": "error"}
                print(self.url_service+i,"erreur format json")

    def collection(self):
         self.retour['collection']={}
         for i in ['/collections','/collections/']:
            r = requests.get(self.url_service+i)
            try:
                self.retour['collection']['url '+i] = {"connexion": "ok", "type":r.headers['Content-Type'], "code": r.status_code, 'rqt':self.url_service+i }
                if r.status_code in [200,201]:
                    print(self.url_service+i,"ok")
                    self.config_service=r.json()['collections']
                else:
                    print(self.url_service+i,"error")
            except:
                self.retour['collection']['url '+i] = {"format json": "error"}
                print(self.url_service+i,"erreur format json")

    def collection_id(self):
        for i in self.config_service:
            instance=i['id']
            print(instance)
            for j in ['/collections/'+instance,'/collections/'+instance+'/']:
                r = requests.get(self.url_service+j)
                try:
                    self.retour['collection']['url '+j] = {"connexion": "ok", "type":r.headers['Content-Type'], "code": r.status_code, 'rqt':self.url_service+j }
                    if r.status_code in [200,201]:
                        print(self.url_service+j,"ok")
                    else:
                        print(self.url_service+j,"error")
                except:
                    self.retour['collection']['url '+j] = {"format json": "error"}
                    print(self.url_service+j,"erreur")

    def position(self):
        print("\ntest POSITION\n")
        for i in self.config_service:
            instance=i['id']
            print(instance)
            self.retour['position csv date unitaire']={}

            if self.point_test==False:
                pts='POINT(%s %s)' % (i['extent']['spatial']['bbox'][0][0],i['extent']['spatial']['bbox'][0][1])
            else:
                pts=f"POINT({self.point_test[0]} {self.point_test[1]})"
            instance=i['id']
            parameter=list(i['parameter_names'][0].keys())[0]
            formatage='CSV'
            dateF=i['extent']['temporal']['interval'][0][0]
            rqt=f"{self.url_service}/collections/{instance}/position?coords={pts}&parameter-name={parameter}&f={formatage}&datetime={dateF}"

            r = requests.get(rqt)
            print('requete CSV date unitaire')
            try:
                self.retour['position csv date unitaire'] = {"connexion": "ok", "type":r.headers['Content-Type'], "code": r.status_code, 'rqt':rqt }
                if r.status_code in [200,201]:
                    print("requete position csv ok")

                    if 'text/csv' in r.headers['Content-Type']:
                        print("hearder csv ok")
                    if parameter in r.text:
                        print("csv conforme")
                    if len(r.text.split('\n'))==2:
                        print('bug date unitaire ou pas de données')
                        self.retour['position csv date unitaire']['resultat rqt']='bug date unitaire ou pas de données'
                    elif len(r.text.split('\n'))>2:
                        print('date unitaire OK')
                        self.retour['position csv date unitaire']['resultat rqt']={
                            "value":{
                                "date":r.text.split('\n')[1].split(',')[0],
                                "result":r.text.split('\n')[1].split(',')[-1]
                                }
                            }
                else:
                    print("requete position csv date unitaire error")
            except:
                self.retour['position csv date unitaire'] = {"format json": "error"}
                print(rqt,"erreur")

            self.retour['position csv date multiple']={}
            date1=i['extent']['temporal']['interval'][0][0]
            date2 =parse(date1)+timedelta(days=10)
            date2=date2.strftime(format='%Y-%m-%dT%H:%M:%S')

            dateF=date1+"/"+date2
            rqt=f"{self.url_service}/collections/{instance}/position?coords={pts}&parameter-name={parameter}&f={formatage}&datetime={dateF}"

            r = requests.get(rqt)
            print('requete CSV date multiple')
            try:
                self.retour['position csv date multiple'] = {"connexion": "ok", "type":r.headers['Content-Type'], "code": r.status_code, 'rqt':rqt }
                if r.status_code in [200,201]:
                    print("requete position csv ok")

                    if 'text/csv' in r.headers['Content-Type']:
                        print("hearder csv ok")
                    if parameter in r.text:
                        print("csv conforme")
                    if len(r.text.split('\n'))==2:
                        print('bug date multiple ou pas de données')
                        self.retour['position csv date multiple']['resultat rqt']='bug date multiple ou pas de données'
                    elif len(r.text.split('\n'))>2:
                        print('date multiple OK')
                        self.retour['position csv date multiple']['resultat rqt']={
                            "value":{
                                "date":r.text.split('\n')[1].split(',')[0],
                                "result":r.text.split('\n')[1].split(',')[-1]
                                }
                            }
                else:
                    print("requete position csv date multiple error")
            except:
                self.retour['position csv date multiple'] = {"format json": "error"}
                print(rqt,"erreur")


            self.retour['position csv sans date']={}
            rqt=f"{self.url_service}/collections/{instance}/position?coords={pts}&parameter-name={parameter}&f={formatage}"
            r = requests.get(rqt)
            print('requete CSV sans date')
            try:
                self.retour['position csv sans date'] = {"connexion": "ok", "type":r.headers['Content-Type'], "code": r.status_code, 'rqt':rqt }
                if r.status_code in [200,201]:
                    print("requete position csv sans date ok")

                    if 'text/csv' in r.headers['Content-Type']:
                        print("hearder csv ok")
                    if parameter in r.text:
                        print("csv conforme")
                    if len(r.text.split('\n'))==2:
                        print('bug sans date ou pas de données')
                        self.retour['position csv sans date']['resultat rqt']='bug sans date ou pas de données'
                    elif len(r.text.split('\n'))>2:
                        print('sans date OK')
                        self.retour['position csv sans date']['resultat rqt']={
                            "value":{
                                "date":r.text.split('\n')[1].split(',')[0],
                                "result":r.text.split('\n')[1].split(',')[-1]
                                }
                            }
                else:
                    print("requete position csv sans date error")
            except:
                self.retour['position csv sans date'] = {"format json": "error"}
                print(rqt,"erreur")


            self.retour['position csv liste parametre']={}
            parameter=list(i['parameter_names'][0].keys())[0]+","+list(i['parameter_names'][1].keys())[0]

            rqt=f"{self.url_service}/collections/{instance}/position?coords={pts}&parameter-name={parameter}&f={formatage}&datetime={dateF}"
            r = requests.get(rqt)
            print('requete CSV liste parametre')
            try:
                self.retour['position csv liste parametre'] = {"connexion": "ok", "type":r.headers['Content-Type'], "code": r.status_code, 'rqt':rqt }
                if r.status_code in [200,201]:
                    print("requete position csv liste parametre ok")

                    if 'text/csv' in r.headers['Content-Type']:
                        print("hearder csv ok")
                    if parameter in r.text:
                        print("csv conforme")
                    if len(r.text.split('\n'))==2:
                        print('bug liste parametre ou pas de données')
                        self.retour['position csv liste parametre']['resultat rqt']='bug liste parametre ou pas de données'
                    elif len(r.text.split('\n'))>2:
                        print('liste parametre OK')
                        self.retour['position csv liste parametre']['resultat rqt']={
                            "value":{
                                "date":r.text.split('\n')[1].split(',')[0],
                                "result":r.text.split('\n')[1].split(',')[-1]
                                }
                            }
                else:
                    print("requete position csv liste parametre error")
            except:
                self.retour['position csv liste parametre'] = {"format json": "error"}
                print(rqt,"erreur")


            self.retour['position csv sans parametre']={}
            rqt=f"{self.url_service}/collections/{instance}/position?coords={pts}&f={formatage}&datetime={dateF}"
            r = requests.get(rqt)
            print('requete CSV sans parametre')
            try:
                self.retour['position csv sans parametre'] = {"connexion": "ok", "type":r.headers['Content-Type'], "code": r.status_code, 'rqt':rqt }
                if r.status_code in [200,201]:
                    print("requete position csv sans parametre ok")

                    if 'text/csv' in r.headers['Content-Type']:
                        print("hearder csv ok")
                    if parameter in r.text:
                        print("csv conforme")
                    if len(r.text.split('\n'))==2:
                        print('bug sans parametre ou pas de données')
                        self.retour['position csv sans parametre']['resultat rqt']='bug sans parametre ou pas de données'
                    elif len(r.text.split('\n'))>2:
                        print('sans parametre OK')
                        self.retour['position csv sans parametre']['resultat rqt']={
                            "value":{
                                "date":r.text.split('\n')[1].split(',')[0],
                                "result":r.text.split('\n')[1].split(',')[-1]
                                }
                            }
                else:
                    print("requete position csv sans parametre error")
            except:
                self.retour['position csv sans parametre'] = {"format json": "error"}
                print(rqt,"erreur")

            self.retour['position csv sans parametre et sans date']={}
            rqt=f"{self.url_service}/collections/{instance}/position?coords={pts}&f={formatage}"
            r = requests.get(rqt)
            print('requete CSV sans parametre et sans date')
            try:
                self.retour['position csv sans parametre et sans date'] = {"connexion": "ok", "type":r.headers['Content-Type'], "code": r.status_code, 'rqt':rqt }
                if r.status_code in [200,201]:
                    print("requete position csv sans parametre et sans date ok")

                    if 'text/csv' in r.headers['Content-Type']:
                        print("hearder csv ok")
                    if parameter in r.text:
                        print("csv conforme")
                    if len(r.text.split('\n'))==2:
                        print('bug sans parametre et sans date ou pas de données')
                        self.retour['position csv sans parametre et sans date']['resultat rqt']='bug sans parametre et sans date ou pas de données'
                    elif len(r.text.split('\n'))>2:
                        print('sans parametre et sans date OK')
                        self.retour['position csv sans parametre et sans date']['resultat rqt']={
                            "value":{
                                "date":r.text.split('\n')[1].split(',')[0],
                                "result":r.text.split('\n')[1].split(',')[-1]
                                }
                            }
                else:
                    print("requete position csv sans parametre et sans date error")
            except:
                self.retour['position csv sans parametre et sans date'] = {"format json": "error"}
                print(rqt,"erreur")


            print('requete csv CRS natif')
            crs=i['extent']['spatial']['crs']
            dateF=date1+"/"+date2
            parameter=list(i['parameter_names'][0].keys())[0]
            rqt=f"{self.url_service}/collections/{instance}/position?coords={pts}&crs={crs}&parameter-name={parameter}&f={formatage}&datetime={dateF}"

            r = requests.get(rqt)

            try:
                self.retour['position csv CRS natif'] = {"connexion": "ok", "type":r.headers['Content-Type'], "code": r.status_code, 'rqt':rqt }
                if r.status_code in [200,201]:
                    print("requete position csv ok")

                    if 'text/csv' in r.headers['Content-Type']:
                        print("hearder csv ok")
                    if parameter in r.text:
                        print("csv conforme")
                    if len(r.text.split('\n'))==2:
                        print('bug CRS natif ou pas de données')
                        self.retour['position csv CRS natif']['resultat rqt']='bug CRS natif ou pas de données'
                    elif len(r.text.split('\n'))>2:
                        print('CRS natif OK')
                        self.retour['position csv CRS natif']['resultat rqt']={
                            "value":{
                                "date":r.text.split('\n')[1].split(',')[0],
                                "result":r.text.split('\n')[1].split(',')[-1]
                                }
                            }
                else:
                    print("requete position csv CRS natif error")
            except:
                self.retour['position csv CRS natif'] = {"format json": "error"}
                print(rqt,"erreur")



            print('requete csv CRS convert')

            dateF=date1+"/"+date2
            parameter=list(i['parameter_names'][0].keys())[0]


            crs="EPSG:4326"
            lamb2e_to_latlon = pyproj.Transformer.from_crs(i['extent']['spatial']['crs'],crs)
            if self.point_test==False:
                y,x=lamb2e_to_latlon.transform(i['extent']['spatial']['bbox'][0][0], i['extent']['spatial']['bbox'][0][1])
            else:
                y,x=lamb2e_to_latlon.transform(self.point_test[0], self.point_test[1])
                pts=f"POINT( )"
            pts='POINT(%s %s)' % (x,y)

            rqt=f"{self.url_service}/collections/{instance}/position?coords={pts}&crs={crs}&parameter-name={parameter}&f={formatage}&datetime={dateF}"

            r = requests.get(rqt)

            try:
                self.retour['position csv CRS convert'] = {"connexion": "ok", "type":r.headers['Content-Type'], "code": r.status_code, 'rqt':rqt }
                if r.status_code in [200,201]:
                    print("requete position csv ok")

                    if 'text/csv' in r.headers['Content-Type']:
                        print("hearder csv ok")
                    if parameter in r.text:
                        print("csv conforme")
                    if len(r.text.split('\n'))==2:
                        print('bug CRS convert ou pas de données')
                        self.retour['position csv CRS convert']['resultat rqt']='bug CRS convert ou pas de données'
                    elif len(r.text.split('\n'))>2:
                        print('CRS convert OK')
                        self.retour['position csv CRS convert']['resultat rqt']={
                            "value":{
                                "date":r.text.split('\n')[1].split(',')[0],
                                "result":r.text.split('\n')[1].split(',')[-1]
                                }
                            }
                else:
                    print("requete position csv CRS convert error")
            except:
                self.retour['position csv CRS convert'] = {"format json": "error"}
                print(rqt,"erreur")


            formatage='CoverageJSON'
            rqt=f"{self.url_service}/collections/{instance}/position?coords={pts}&crs={crs}&parameter-name={parameter}&f={formatage}&datetime={dateF}"

            r = requests.get(rqt)

            try:
                self.retour['position CoverageJSON CRS convert'] = {"connexion": "ok", "type":r.headers['Content-Type'], "code": r.status_code, 'rqt':rqt }
                if r.status_code in [200,201]:
                    print("requete position CoverageJSON ok")
                    data=r.json()
                    if 'application/json' in r.headers['Content-Type']:
                        print("hearder CoverageJSON ok")
                    if parameter in data['parameters']:
                        print("CoverageJSON conforme")
                    if len(data['ranges'][parameter]['values'])==0:
                        print('bug CoverageJSON convert ou pas de données')
                        self.retour['position CoverageJSON CRS convert']['resultat rqt']='bug CRS convert ou pas de données'
                    elif len(data['ranges'][parameter]['values'])>0:
                        print('CoverageJSON  convert OK')
                        self.retour['position CoverageJSON CRS convert']['resultat rqt']={
                            "value":{
                                "date":data['domain']['axes']['t']['values'][0],
                                "result":data['ranges'][parameter]['values'][0]
                                }
                            }
                else:
                    print("requete position CoverageJSON CRS convert error")
            except:
                self.retour['position CoverageJSON CRS convert'] = {"format json": "error"}
                print(rqt,"erreur")


            break
    #tester un ou deux paramètre ou aucun
    def run_test(self):


        self.accueil()
        self.collection()
        self.collection_id()
        self.position()
        return self.retour
