# Date: 2020-03
# Author: G35878
# Project: liste_de_course


import streamlit as st
import pandas as pd
from pandas import DataFrame
import numpy as np
import os
import sys
import psycopg2
from sqlalchemy import create_engine
from configparser import ConfigParser


######### Parameters #########
#produits = pd.read_csv(r"produits_a_acheter.csv", sep=";", encoding='UTF-8')


def config(filename='config.ini', section='postgresql'):
    parser = ConfigParser()
    parser.read(filename)
 
    db = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            db[param[0]] = param[1]
            
    else:
        raise Exception('Section {0} not found in the {1} file'.format(section, filename))
 
    return db


def ihm_builder(conn, engine) :
    ######### Parameters ########
    key_index = 1000
    rayons = ['Rayon sec', 'Rayon frais', 'Rayon surgele', 'Non alimentaire']

    ######### App #########
    st.sidebar.header("Liste de courses App")
    pages = ['Listes de course', 'Ajouter un produit', 'Visualisations']
    page = st.sidebar.radio("", options=pages)


    ######## Page 1 #######
    if page == pages[0]:

        sql = "select * from public.produits_a_acheter;"
        produits_a_acheter = pd.read_sql_query(sql, conn)

        sql = "select * from public.produits_ref;"
        produits_ref = pd.read_sql_query(sql, conn)

        sql = "select * from public.magasins_ref;"
        magasins_ref = pd.read_sql_query(sql, conn)

        # One section for each Magasin
        for index, m_ref in magasins_ref.iterrows():
            st.header(m_ref['nom'])
            m_id = m_ref['id']

            key_index = key_index + 10

            produits_a_acheter_maj = []
            # One multiselect bar for each categorie in the Magasin
            for cat in rayons:
                if m_ref[cat] == 1:
                    produits_multiselect = list(produits_a_acheter[
                        (produits_a_acheter['magasin'] == m_id) &
                        (produits_a_acheter['categorie'] == cat)
                        ]['nom'])
                    
                    produits_possible = list(produits_ref[
                        (produits_ref['magasin'] == m_id) &
                        (produits_ref['categorie'] == cat)
                        ]['nom'])

                    produits_multiselect = st.multiselect(cat,
                                                    produits_possible,
                                                    default=produits_multiselect,
                                                        key=key_index)                                                        
                    produits_a_acheter_maj += produits_multiselect

            if st.button("Enregistrer l'avancement", key=key_index+1):                
                if produits_a_acheter_maj:
                    # delete magasin's products
                    cur = conn.cursor()
                    sql = "DELETE FROM public.produits_a_acheter WHERE produits_a_acheter.magasin = '" + str(m_id) + "' ;"
                    cur.execute(sql)
                    conn.commit()
                    cur.close()

                    # get new products's IDs in ref table
                    sql = "select * from public.produits_ref WHERE nom IN ('" + "', '".join(produits_a_acheter_maj) + "') ;"
                    produits_a_acheter_maj_details = pd.read_sql_query(sql, conn)

                    # insert new products to buy
                    produits_a_acheter_maj_details.to_sql('produits_a_acheter', engine, if_exists='append', index=False)
                    
                st.write('Liste de course mise à jour !')



if __name__ == "__main__":
    args = sys.argv[1:]

    if args:
        #Connect to the PostgreSQL database server
        conn = None
        engine = None
        
        try:
            print('Connecting to the PostgreSQL database...')
            if args[0] == 'dev':
                params = config()
                conn = psycopg2.connect(**params)
                DATABASE_URI = 'postgres+psycopg2://' + params['user'] + ':' + params['password'] + '@' + params['host'] + ':5432/' + params['database']
                engine = create_engine(DATABASE_URI)
            elif args[0] == 'prod':
                DATABASE_URL = os.environ['DATABASE_URL']
                conn = psycopg2.connect(DATABASE_URL, sslmode='require')
                engine = create_engine(DATABASE_URL)
            else:
                sys.stderr.write('ERROR: The script needs 1 argument: dev or prod')
                sys.exit(1)

            sql = "select * from public.produits_ref;"
            df = pd.read_sql_query(sql, conn)

            # build the IHM !
            ihm_builder(conn, engine)

        except (Exception, psycopg2.DatabaseError) as error:
            print(error)

        finally:
            if conn is not None:
                conn.close()
                print('Database connection closed.')