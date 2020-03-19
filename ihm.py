# Date: 2020-03
# Author: G35878
# Project: liste_de_course


import streamlit as st
import pandas as pd
from pandas import DataFrame


######### Parameters #########
produits = pd.read_csv(r"produits_a_acheter.csv", sep=";", encoding='UTF-8')
key_index = 1000


######### App #########
st.sidebar.header("Liste de courses App")
pages = ['Listes de course', 'Ajouter un produit', 'Visualisations']
page = st.sidebar.radio("", options=pages)


######## Page 1 #######
if page == pages[0]:

    for m in produits.magasin.unique():
        st.header(m)

        key_index = key_index + 10

        for cat in produits.categorie.unique():

            produits_multiselect = list(produits[(produits['magasin'] == m) & (produits['categorie'] == cat)]['nom'])
            if produits_multiselect:
                produits_multiselect = st.multiselect(cat,
                                                   produits_multiselect,
                                                   default=produits_multiselect,
                                                    key=key_index)

            st.write("You selected ", produits_multiselect)

        if st.button("Enregistrer l'avancement", key=key_index+1):
            st.write('Liste de course mise à jour !')
            csv = produits.to_csv("produits_a_acheter.csv", sep=';', encoding='utf-8', index=None)

    produits

