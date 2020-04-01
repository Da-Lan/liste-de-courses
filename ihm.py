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
from datetime import date
#import plotly.express as px
import plotly.graph_objs as go


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
    pages_ref = ['Listes de course', 'Ajouter un produit', 'Tendances',
                'Gérer péremptions', 'Recettes de cuisine']

    ######### App #########
    st.sidebar.header("Liste de courses App")

    pages = pages_ref[:3]
    page = st.sidebar.empty()
    page_peremption = st.sidebar.checkbox('Gérer maison')

    if page_peremption:
        pages = pages_ref[3:]

    page = page.radio("", options=pages)
    
    hide_streamlit_style = """
            <style>
            footer {visibility: hidden;}
            </style>
            """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True) 

    sql = "select * from public.produits_a_acheter;"
    produits_a_acheter = pd.read_sql_query(sql, conn)

    sql = "select * from public.produits_ref;"
    produits_ref = pd.read_sql_query(sql, conn)

    sql = "select * from public.magasins_ref;"
    magasins_ref = pd.read_sql_query(sql, conn)

    #st.write(str(page) + ' is selected among ' + str(pages))
    
    ######## Page 1 #######
    if page == pages_ref[0]:

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

                    produits_a_acheter_maj = [x.replace("'", "''") if "'" in x else x for x in produits_a_acheter_maj]
                    # get new products's IDs in ref table
                    sql = "select * from public.produits_ref WHERE nom IN ('" + "', '".join(produits_a_acheter_maj) + "') ;"
                    produits_a_acheter_maj_details = pd.read_sql_query(sql, conn)

                    # insert new products to buy
                    produits_a_acheter_maj_details.to_sql('produits_a_acheter', engine, if_exists='append', index=False)
                    
                st.write('Liste de course mise à jour !')


    elif page == pages_ref[1]:
        st.header("Ajouter un produit à acheter")
        nom_produit = st.text_input('Nom du produit:')
        nom_magasin = st.selectbox('Magasin:', magasins_ref['nom'].unique())
        nom_rayon = st.selectbox('Rayon où trouver le produit:', produits_ref['categorie'].unique())
        prix = st.number_input('Prix:', value=3.00, step=0.5, min_value=0.00, max_value=1000.00)
        
        if nom_produit:
            if st.button("Enregistrer l'avancement"):

                # insert new products to buy
                produits_a_ajouter = pd.DataFrame( {
                    'nom':[nom_produit],
                    'magasin':[ int(magasins_ref[ magasins_ref['nom'] == nom_magasin]['id']) ],
                    'categorie':[nom_rayon],
                    'prix':[prix]
                } )

                produits_a_ajouter.to_sql('produits_ref', engine, if_exists='append', index=False)
                sql = "select * from public.produits_ref;"
                produits_ref = pd.read_sql_query(sql, conn)

                st.write('Produit ajouté à la base de donnée !')

        st.subheader("Les 3 derniers produits ajoutés sont:")
        st.write(produits_ref.tail(3))

        st.subheader("Rechercher un produit existant:")
        st.multiselect('', options=list(produits_ref['nom']))  


    elif page == pages_ref[3]:
        sql = "select * from public.produits_a_surveiller;"
        produits_a_surveiller = pd.read_sql_query(sql, conn)
        
        if not produits_a_surveiller.empty:

            fig = go.Figure(go.Bar(
                x=produits_a_surveiller["date_fin"],
                y=produits_a_surveiller["nom"],
                orientation='h'))
            fig.update_layout(bargap=0.7)
            st.plotly_chart(fig)

        st.header("Ajouter un produit à surveiller")
        nom_produit = st.text_input('Nom du produit:')
        date_peremption = st.date_input("Date de péremption", value=None )

        if nom_produit:
            if st.button("Ajouter"):
                st.write('Produit mis en surveillance !')

                # insert new products to buy
                produits_a_ajouter = pd.DataFrame( {
                    'nom':[nom_produit],
                    'date_debut':[date.today().strftime("%d/%m/%Y")],
                    'date_fin':[date_peremption]
                } )
                produits_a_ajouter
                produits_a_ajouter.to_sql('produits_a_surveiller', engine, if_exists='append', index=False)
        
        st.subheader("Enlever un produit en surveillance")
        #Pour le dev
        produits_enlevables = ['a', 'b', 'c', 'd','e','f']
        produits_a_enlever = {}
        #Pour le dev /
        for p in produits_enlevables:
            produits_a_enlever[p] = st.checkbox(p)

        if produits_a_enlever :
            if st.button("Enlever"):
                st.write("Le produit n'est plus surveillé !")



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