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
from datetime import date, timedelta
#import plotly.express as px
import plotly.graph_objs as go
import re
import math
from dateutil.relativedelta import relativedelta


######### Fuctions #########

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
    pages_ref = ['Liste de courses', 'Produits',
                'Péremptions', 'Congélateur', 'Recettes de cuisine']

    ######### App #########
    st.sidebar.header("Liste de courses App")

    page = st.sidebar.radio("", options=pages_ref)
    
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
                    
                st.write('Liste de courses mise à jour !')


    elif page == pages_ref[1]:
        st.title("Ajouter un produit à acheter")
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


        st.title("Modifier / supprimer un produit")
        key_index = key_index + 10

        produit_a_modif = st.multiselect('Nom du produit', options=list(produits_ref['nom']))

        # get product's references from BDD
        if produit_a_modif:
            produit_a_modif = produit_a_modif[0]
            produit_a_modif = produit_a_modif.replace("'", "''")
            sql = "select * from public.produits_ref where nom = ('" + produit_a_modif + "') ;"
            produit_a_modif_ref = pd.read_sql_query(sql, conn)

            # print pre-filled widgets
            nom_produit_a_modif = st.text_input('Nouveau nom', list(produit_a_modif_ref['nom'])[0])
            nom_magasin_a_modif = st.selectbox('Magasin:',
                                                magasins_ref['nom'].unique(),
                                                index=int(produit_a_modif_ref['magasin'][0]) - 1,
                                                key=key_index+1
                                                )
            nom_rayon_a_modif = st.selectbox('Rayon où trouver le produit:',        
                                                produits_ref['categorie'].unique(),
                                                index=rayons.index(list(produit_a_modif_ref['categorie'])[0]),
                                                key=key_index+2
                                                )
            prix_a_modif = st.number_input('Prix:', value=float(produit_a_modif_ref['prix']), step=0.5, min_value=0.00, max_value=1000.00,
                                                key=key_index+3)

            #defining "product is modified" rules
            rule_product_name_is_modified = nom_produit_a_modif != list(produit_a_modif_ref['nom'])[0]
            rule_magasin_is_modified = list(magasins_ref[magasins_ref['nom'] == nom_magasin_a_modif]['id'])[0]\
                                        != produit_a_modif_ref['magasin'][0]
            rule_categorie_is_modified = nom_rayon_a_modif != list(produit_a_modif_ref['categorie'])[0]
            rule_prix_is_modified = prix_a_modif != float(produit_a_modif_ref['prix'])

            # Update product from referentiel
            if st.button("Modifier le produit", key=key_index+4):
                if (rule_magasin_is_modified or rule_categorie_is_modified or rule_prix_is_modified or rule_product_name_is_modified):
                    # Create update query
                    all_modified_variables = []
                    if rule_product_name_is_modified: all_modified_variables.append("nom = '" +nom_produit_a_modif.replace("'", "''") + "'")
                    if rule_magasin_is_modified: all_modified_variables.append("magasin = " + str(list(magasins_ref[magasins_ref['nom'] == nom_magasin_a_modif]['id'])[0]))
                    if rule_categorie_is_modified: all_modified_variables.append("categorie = '" +nom_rayon_a_modif  + "'")
                    if rule_prix_is_modified: all_modified_variables.append("prix = " + str(prix_a_modif))

                    # Execute update query
                    cur = conn.cursor()
                    sql = "UPDATE public.produits_ref SET " \
                            + ", ".join(all_modified_variables) \
                            + " WHERE produits_ref.nom = '" + produit_a_modif + "' ;"
                    cur.execute(sql)
                    conn.commit()
                    cur.close()
                    
                    st.write("Produit mis à jour !")
                else:
                    st.write("Rien n'a changé !")

            # delete products from referentiel
            if st.button("Supprimer le produit", key=key_index+5):
                cur = conn.cursor()
                sql = "DELETE FROM public.produits_ref WHERE produits_ref.nom = '" + produit_a_modif + "' ;"
                cur.execute(sql)
                conn.commit()
                cur.close()
                st.write("Produit supprimé !")


    elif page == pages_ref[2]:
        sql = "select * from public.produits_a_surveiller;"
        produits_a_surveiller = pd.read_sql_query(sql, conn)
        st.title("Produits en surveillance")

        
        if not produits_a_surveiller.empty:
            bin = [0, 0.5 , 1, 8, 15, 300]
            labels = ["0 - Aujourd'hui !!", "1 - Demain !", "2 - Dans la semaine", "3 - Dans les deux semaines",
                        "4 - Dans le mois"]
            colors = {labels[0]: 'red',
                        labels[1]: 'orange',
                        labels[2]: 'green',
                        labels[3]: 'blue',
                        labels[4]: 'lightgrey'}

            produits_a_surveiller['temps_restant'] = produits_a_surveiller['date_fin'].apply(lambda x:
                                        ( pd.to_datetime(x) - pd.to_datetime(date.today()) ).days)

            produits_a_surveiller = produits_a_surveiller.sort_values('temps_restant', ascending=False)
                    
            produits_a_surveiller['temps_restant_label'] = list(
                pd.cut(list(produits_a_surveiller.temps_restant), bins=bin, labels=labels, include_lowest=True)
            )

            height = int(math.exp(len(produits_a_surveiller)/21)*100+300)     
            bars = []
            for label, label_df in produits_a_surveiller.groupby('temps_restant_label') :#.sum().reset_index().sort_values('temps_restant'):  #.apply(pd.DataFrame.sort_values, 'temps_restant'):
                label_df_str = label_df.temps_restant.apply(lambda x: str(x))
                str(label_df.temps_restant)
                bars.append(go.Bar(x=label_df.date_fin,
                                y=label_df.nom,
                                #name=label,
                                text='  ' + label_df_str + ' j  ',                                
                                textposition='auto',
                                marker={'color': colors[label]},
                                orientation='h',
                                opacity=0.7))
            fig = go.FigureWidget(data=list(reversed(bars)))
            fig.update_layout(bargap=0.2,
                                height=height,
                                width=460,
                                showlegend=False,
                                xaxis=go.layout.XAxis( tickformat = '%d %B'),
                                xaxis_range = [(date.today() + timedelta(days=-1)) , (date.today() + timedelta(days=15))]
                                )
            st.plotly_chart(fig)

        st.header("Ajouter un produit à surveiller")
        nom_produit = st.text_input('Nom du produit:')
        date_peremption = st.date_input("Date de péremption", value=None )


        if nom_produit:
            if st.button("Ajouter"):
               
                #add suffix if products name already exists in BBD
                if nom_produit in list(produits_a_surveiller['nom']):
                    produits_a_surveiller['suffix'] = produits_a_surveiller[produits_a_surveiller['nom']\
                            .str.startswith(nom_produit)]['nom']\
                            .str.extract('(\d+)$')

                    produits_a_surveiller['suffix'] = produits_a_surveiller['suffix'].apply(lambda x: float(x))
                    
                    incr = produits_a_surveiller['suffix'].max()

                    if math.isnan(incr): incr = 0
                    else: incr = int(incr) + 1

                    nom_produit = nom_produit + str(incr)

                # insert new products to control
                produits_a_ajouter = pd.DataFrame( {
                    'nom':[nom_produit],
                    'date_debut':[date.today().strftime("%Y-%m-%d")],
                    'date_fin':[date_peremption.strftime("%Y-%m-%d")]
                } )

                produits_a_ajouter.to_sql('produits_a_surveiller', engine, if_exists='append', index=False)
                st.write('Produit mis en surveillance !')

        st.subheader("Enlever un produit en surveillance")
        #Pour le dev
        produits_a_enlever = {}
        #Pour le dev /
        for index, p in produits_a_surveiller.sort_values('date_fin').iterrows():
            produits_a_enlever[p['nom']] = st.checkbox(p['nom'] + " (" + str(p['date_fin']) + ")")

        if True in produits_a_enlever.values() :
            if st.button("Enlever"):
                produits_a_enlever_true = {key: value for key, value in produits_a_enlever.items() if value == True}
                # delete products to stop to control them
                produits_a_enlever_true = [x.replace("'", "''") if "'" in x else x for x in produits_a_enlever_true.keys()]
                cur = conn.cursor()
                sql = "DELETE FROM public.produits_a_surveiller WHERE produits_a_surveiller.nom IN ('" + "', '".join(produits_a_enlever_true) + "') ;"
                print(sql)
                cur.execute(sql)
                conn.commit()
                cur.close()

                st.write("Le produit n'est plus surveillé !")


    elif page == pages_ref[3]:

        sql = "select * from public.produits_au_congelateur;"
        produits_au_congelateur = pd.read_sql_query(sql, conn)
        st.title("Produit au congélateur")

        if not produits_au_congelateur.empty:
            bin = [0, 30 , 60, 180, 1000]
            labels = ["0 - Bientôt !!", "1 - Dans un mois !", "2 - Dans les deux mois", "3 - Dans les longtemps"]
            colors = {labels[0]: 'darkblue',
                        labels[1]: 'blue',
                        labels[2]: 'lightblue',
                        labels[3]: 'white'}

            produits_au_congelateur['temps_restant'] = produits_au_congelateur['date_fin'].apply(lambda x:
                                        ( pd.to_datetime(x) - pd.to_datetime(date.today()) ).days)

            produits_au_congelateur = produits_au_congelateur.sort_values('temps_restant', ascending=False)
                    
            produits_au_congelateur['temps_restant_label'] = list(
                pd.cut(list(produits_au_congelateur.temps_restant), bins=bin, labels=labels, include_lowest=True)
            )

            height = int(math.exp(len(produits_au_congelateur)/21)*100+300)     
            bars = []
            for label, label_df in produits_au_congelateur.groupby('temps_restant_label') :#.sum().reset_index().sort_values('temps_restant'):  #.apply(pd.DataFrame.sort_values, 'temps_restant'):
                label_df_str = label_df.temps_restant.apply(lambda x: str(x))
                str(label_df.temps_restant)
                bars.append(go.Bar(x=label_df.date_fin,
                                y=label_df.nom,
                                text='  ' + label_df_str + ' j  ',                                
                                textposition='auto',
                                marker={'color': colors[label]},
                                orientation='h',
                                opacity=0.7))
            fig = go.FigureWidget(data=list(reversed(bars)))
            fig.update_layout(bargap=0.2,
                                height=height,
                                width=460,
                                showlegend=False,
                                xaxis=go.layout.XAxis( tickformat = '%d %B'),
                                xaxis_range = [(date.today() + timedelta(days=-1)) , (date.today() + relativedelta(months=+6))]
                                )
            st.plotly_chart(fig)


        st.header("Ajouter un produit au congélateur")
        nom_produit = st.text_input('Nom du produit:')
        mois_conservation = st.number_input('Nombre de mois conseillé de conservation:', value=6, step=1, min_value=0, max_value=100)

        if nom_produit:
            if st.button("Ajouter"):
               
                #add suffix if products name already exists in BBD
                if nom_produit in list(produits_au_congelateur['nom']):
                    produits_au_congelateur['suffix'] = produits_au_congelateur[produits_au_congelateur['nom']\
                            .str.startswith(nom_produit)]['nom']\
                            .str.extract('(\d+)$')

                    produits_au_congelateur['suffix'] = produits_au_congelateur['suffix'].apply(lambda x: float(x))
                    
                    incr = produits_au_congelateur['suffix'].max()

                    if math.isnan(incr): incr = 0
                    else: incr = int(incr) + 1

                    nom_produit = nom_produit + str(incr)

                # insert new products to control
                produits_a_ajouter = pd.DataFrame( {
                    'nom':[nom_produit],
                    'date_debut':[date.today().strftime("%Y-%m-%d")],
                    'date_fin':[(date.today() + relativedelta(months=+mois_conservation)).strftime("%Y-%m-%d")]
                } )

                produits_a_ajouter.to_sql('produits_au_congelateur', engine, if_exists='append', index=False)
                st.write('Produit mis au congélateur !')


        st.subheader("Enlever un produit du congélateur")
        #Pour le dev
        produits_a_enlever = {}
        #Pour le dev /
        for index, p in produits_au_congelateur.sort_values('date_fin').iterrows():
            produits_a_enlever[p['nom']] = st.checkbox(p['nom'] + " (" + str(p['date_fin']) + ")")

        if True in produits_a_enlever.values() :
            if st.button("Enlever"):
                produits_a_enlever_true = {key: value for key, value in produits_a_enlever.items() if value == True}
                # delete products to stop to control them
                produits_a_enlever_true = [x.replace("'", "''") if "'" in x else x for x in produits_a_enlever_true.keys()]
                cur = conn.cursor()
                sql = "DELETE FROM public.produits_au_congelateur WHERE produits_au_congelateur.nom IN ('" + "', '".join(produits_a_enlever_true) + "') ;"
                print(sql)
                cur.execute(sql)
                conn.commit()
                cur.close()

                st.write("Le produit n'est plus au congélateur !")


    elif page == pages_ref[4]:

        sql = "select * from public.recettes;"
        recettes = pd.read_sql_query(sql, conn)
        st.title("Recettes de cuisine")

        recette_name_list = list(recettes['nom'].append(pd.Series(['Nouveau'])))
        selected_recette_name = st.radio("", options=recette_name_list)

        if selected_recette_name == recette_name_list[-1]:
            nom_a_modif = st.text_input('Nom de la recette')
            texte_a_modif = st.text_area('Recette')

            if st.button("Ajouter", key=key_index+40):
                if nom_a_modif and texte_a_modif:
                    # insert new recette
                    recette_a_ajouter = pd.DataFrame( {
                        'nom':[nom_a_modif],
                        'texte':[texte_a_modif]
                    } )

                    recette_a_ajouter.to_sql('recettes', engine, if_exists='append', index=False)
                    st.write('Recette ajoutée !')
                else:
                    st.write("Rien n'a changé !")

        else:
            selected_recette = recettes[recettes['nom'] == selected_recette_name]
            nom_a_modif = st.text_input('Nom de la recette:', list(selected_recette['nom'])[0])
            texte_a_modif = st.text_area('', list(selected_recette['texte'])[0])

            rule_nom_is_modified = nom_a_modif != selected_recette_name
            rule_texte_is_modified = texte_a_modif != list(selected_recette['texte'])[0]

            # Update recette
            if st.button("Modifier", key=key_index+40):
                if (rule_nom_is_modified or rule_texte_is_modified):
                    # Create update query
                    all_modified_variables = []
                    if rule_nom_is_modified: all_modified_variables.append("nom = '" + nom_a_modif.replace("'", "''") + "'")
                    if rule_texte_is_modified: all_modified_variables.append("texte = '" + texte_a_modif.replace("'", "''") + "'")

                    # Execute update query
                    cur = conn.cursor()
                    sql = "UPDATE public.recettes SET " \
                            + ", ".join(all_modified_variables) \
                            + " WHERE recettes.nom = '" + selected_recette_name + "' ;"
                    cur.execute(sql)
                    conn.commit()
                    cur.close()
                    
                    st.write("Recette mise à jour !")
                else:
                    st.write("Rien n'a changé !")



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
