import time
import asyncio
import functools
from google import genai
from google.genai import types
from logger import logger


async def query_gemini_with_pdf(client: genai.Client, pdf_content: bytes, company_name: str) -> str:
    """Query Gemini 2.5 Flash with PDF content for comprehensive financial ratio calculation"""
    try:
        start_time = time.time()
        
        if not client:
            logger.error("Gemini client not initialized")
            return "Error: Gemini client not initialized"
        
        model = "gemini-2.5-flash"
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_bytes(
                        mime_type="application/pdf",
                        data=pdf_content
                    ),
                    types.Part.from_text(text="""CALCUL DES RATIOS FINANCIERS 

CONTEXTE ET MISSION 

Vous êtes un analyste financier spécialisé dans le calcul de ratios comptables. 

Votre mission : Calculer tous les ratios financiers requis à partir des documents comptables fournis (bilan et compte de résultat sur les deux derniers exercices). 

Input attendu : Bilan comptable (actif/passif) et compte de résultat détaillé sur les deux derniers exercices. 

Output attendu : liste complète de tous les ratios calculés avec leurs valeurs numériques. Pour les % et nombres décimaux, arrondir à un chiffre apès la virgule.  

 

RATIOS À CALCULER 

IMPORTANT : Calculez UNIQUEMENT les ratios listés ci-dessous. N'ajoutez aucun ratio supplémentaire. 

STRUCTURE FINANCIÈRE 

Ratio 

Formule 

Ressources propres 

Capitaux propres + Amortissements cumulés + Emprunts et dettes financières 

Ressources stables 

Capitaux propres + Amortissements cumulés 

Capital d'exploitation 

Total de l'actif circulant – Total du passif circulant 

Actif circulant d'exploitation 

Matières premières et marchandises + Avances et acomptes versés sur commandes + Clients et comptes rattachés + Autres créances + Charges constatées d'avance 

Actif circulant hors exploitation 

Capital souscrit appelé, non versé 

Dettes d'exploitation 

Avances et acomptes reçus sur commandes en cours + Dettes fournisseurs et comptes rattachés + Autres dettes 

Dettes hors exploitation 

Dettes sur immobilisations et comptes rattachés + Autres dettes 

Surface financière 

Capitaux propres / Total du passif 

Couverture des immobilisations par les fonds propres 

Total brut des immobilisations / Ressources propres 

Couverture des emplois stables 

Ressources propres / Total brut des immobilisations 

FRNG (Fonds de roulement net global) 

Ressources propres – Total brut des immobilisations 

BFR (Besoin en fonds de roulement) 

Actif circulant – Passif circulant 

Trésorerie nette 

Ressources propres – Total brut des immobilisations – Besoin en fonds de roulement 

Indépendance financière 

Emprunts et dettes financières / Capitaux propres 

ACTIVITÉ D'EXPLOITATION 

Ratio 

Formule 

Marge globale 

Chiffre d'affaires net – Achats de marchandises et matières premières (nets de variation de stocks) 

Valeur ajoutée 

Marge globale + Autres produits – Autres achats et charges externes 

EBE 

Valeur ajoutée + Subventions d'exploitation – Impôts, taxes et versements assimilés – Salaires et traitements – Charges sociales 

CAF 

EBE + Produits financiers + Produits exceptionnels – Charges financières – Charges exceptionnelles 

Charges de personnel / Valeur ajoutée 

(Salaires et traitements + Charges sociales) / Valeur ajoutée 

Impôts / Valeur ajoutée 

Impôts, taxes et versements assimilés / Valeur ajoutée 

Charges financières / Valeur ajoutée 

Intérêts et charges assimilées / Valeur ajoutée 

Taux de marge globale 

Marge globale / (Ventes de marchandises + Production vendue de biens et services) 

Taux de valeur ajoutée 

Valeur ajoutée / (Production de l'exercice + Ventes de marchandises) 

Taux de marge bénéficiaire 

Résultat net comptable / Chiffre d'affaires net 

Taux de marge brute d'exploitation 

Excédent Brut d'Exploitation / Chiffre d'affaires net 

Taux d'obsolescence 

Dotations aux amortissements / Total brut des immobilisations 

Marge brute d'autofinancement 

Résultat courant avant impôts + Dotations aux amortissements et provisions – Reprises sur provisions et transferts de charges 

RENTABILITÉ 

Ratio 

Formule 

Rentabilité des capitaux propres 

Résultat net comptable / Capitaux propres 

Rentabilité économique 

(Résultat net comptable + Intérêts et charges assimilées) / (Capitaux propres + Amortissements cumulés) 

Rentabilité financière 

Résultat net comptable / (Capitaux propres + Amortissements cumulés) 

Rentabilité brute des ressources stables 

Excédent Brut d'Exploitation / (Capitaux propres + Amortissements cumulés) 

Rentabilité brute du capital d'exploitation 

Excédent Brut d'Exploitation / (Total de l'actif circulant – Total du passif circulant) 

Rentabilité nette du capital d'exploitation 

Résultat d'exploitation / (Total de l'actif circulant – Total du passif circulant) 

ÉVOLUTION 

Ratio 

Formule 

Taux de variation du chiffre d'affaires 

(Chiffre d'affaires net N+1 – Chiffre d'affaires net N) / Chiffre d'affaires net N 

Taux de variation de la valeur ajoutée 

(Valeur ajoutée N+1 – Valeur ajoutée N) / Valeur ajoutée N 

Taux de variation du résultat 

(Résultat net comptable N+1 – Résultat net comptable N) / Résultat net comptable N 

Taux de variation des capitaux propres 

(Capitaux propres N+1 – Capitaux propres N) / Capitaux propres N 

TRÉSORERIE & FINANCEMENT 

Ratio 

Formule 

Capacité à générer du cash 

Excédent Brut d'Exploitation + Produits financiers + Produits exceptionnels – Intérêts et charges assimilées – Charges exceptionnelles 

Capacité à générer du cash (alternative) 

Capacité d'autofinancement / (Ventes de marchandises + Production vendue de biens et services) 

Capacité de remboursement 

Total des emprunts financiers / Capacité à générer du cash 

Crédits bancaires courants / BFR 

Concours bancaires courants / (Actif circulant – Passif circulant) 

DÉLAIS DE PAIEMENT 

Ratio 

Formule 

Délai créance clients (en jours) 

(Clients et comptes rattachés / Chiffre d'affaires net) × 360 

Délai dettes fournisseurs (en jours) 

(Dettes fournisseurs et comptes rattachés / (Achats de marchandises + Autres achats et charges externes)) × 360 

 

  

CONSIGNES DE CALCUL 

À FAIRE 

Utiliser exclusivement les données des états financiers fournis 

Calculer tous les ratios pour les deux exercices disponibles 

Arrondir à 1 décimale pour les pourcentages 

Préciser \"Non calculable\" si une donnée manque 

À ÉVITER 

Inventer ou extrapoler des données manquantes 

Ajouter des ratios non listés 

Faire des calculs approximatifs 

Omettre des ratios de la liste 

EN CAS DE DONNÉES MANQUANTES 

Si un élément comptable n'apparaît pas dans les états financiers, indiquer clairement \"Donnée non disponible\" et marquer le ratio comme \"Non calculable\". """)
                ]
            )
        ]
        
        generate_content_config = types.GenerateContentConfig(
            temperature=0.1,
            thinking_config=types.ThinkingConfig(
                thinking_budget=8000,
            ),
            response_mime_type="application/json",
            response_schema=genai.types.Schema(
                type=genai.types.Type.OBJECT,
                required=["structure_financiere", "activite_exploitation", "rentabilite", "evolution", "tresorerie_financement", "delais_paiement"],
                properties={
                    "structure_financiere": genai.types.Schema(
                        type=genai.types.Type.OBJECT,
                        properties={
                            "ressources_propres_N": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "ressources_propres_N_1": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "ressources_stables_N": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "ressources_stables_N_1": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "capital_exploitation_N": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "capital_exploitation_N_1": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "actif_circulant_exploitation_N": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "actif_circulant_exploitation_N_1": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "actif_circulant_hors_exploitation_N": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "actif_circulant_hors_exploitation_N_1": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "dettes_exploitation_N": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "dettes_exploitation_N_1": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "dettes_hors_exploitation_N": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "dettes_hors_exploitation_N_1": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "surface_financiere_N": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "surface_financiere_N_1": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "couverture_immobilisations_fonds_propres_N": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "couverture_immobilisations_fonds_propres_N_1": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "couverture_emplois_stables_N": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "couverture_emplois_stables_N_1": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "frng_N": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "frng_N_1": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "bfr_N": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "bfr_N_1": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "tresorerie_nette_N": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "tresorerie_nette_N_1": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "independance_financiere_N": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "independance_financiere_N_1": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                        },
                    ),
                    "activite_exploitation": genai.types.Schema(
                        type=genai.types.Type.OBJECT,
                        properties={
                            "marge_globale_N": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "marge_globale_N_1": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "valeur_ajoutee_N": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "valeur_ajoutee_N_1": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "ebe_N": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "ebe_N_1": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "caf_N": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "caf_N_1": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "charges_personnel_valeur_ajoutee_N": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "charges_personnel_valeur_ajoutee_N_1": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "impots_valeur_ajoutee_N": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "impots_valeur_ajoutee_N_1": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "charges_financieres_valeur_ajoutee_N": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "charges_financieres_valeur_ajoutee_N_1": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "taux_marge_globale_N": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "taux_marge_globale_N_1": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "taux_valeur_ajoutee_N": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "taux_valeur_ajoutee_N_1": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "taux_marge_beneficiaire_N": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "taux_marge_beneficiaire_N_1": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "taux_marge_brute_exploitation_N": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "taux_marge_brute_exploitation_N_1": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "taux_obsolescence_N": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "taux_obsolescence_N_1": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "marge_brute_autofinancement_N": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "marge_brute_autofinancement_N_1": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                        },
                    ),
                    "rentabilite": genai.types.Schema(
                        type=genai.types.Type.OBJECT,
                        properties={
                            "rentabilite_capitaux_propres_N": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "rentabilite_capitaux_propres_N_1": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "rentabilite_economique_N": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "rentabilite_economique_N_1": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "rentabilite_financiere_N": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "rentabilite_financiere_N_1": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "rentabilite_brute_ressources_stables_N": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "rentabilite_brute_ressources_stables_N_1": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "rentabilite_brute_capital_exploitation_N": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "rentabilite_brute_capital_exploitation_N_1": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "rentabilite_nette_capital_exploitation_N": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "rentabilite_nette_capital_exploitation_N_1": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                        },
                    ),
                    "evolution": genai.types.Schema(
                        type=genai.types.Type.OBJECT,
                        properties={
                            "taux_variation_chiffre_affaires": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "taux_variation_valeur_ajoutee": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "taux_variation_resultat": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "taux_variation_capitaux_propres": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                        },
                    ),
                    "tresorerie_financement": genai.types.Schema(
                        type=genai.types.Type.OBJECT,
                        properties={
                            "capacite_generer_cash_N": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "capacite_generer_cash_N_1": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "capacite_generer_cash_alternative_N": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "capacite_generer_cash_alternative_N_1": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "capacite_remboursement_N": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "capacite_remboursement_N_1": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "credits_bancaires_courants_bfr_N": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "credits_bancaires_courants_bfr_N_1": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                        },
                    ),
                    "delais_paiement": genai.types.Schema(
                        type=genai.types.Type.OBJECT,
                        properties={
                            "delai_creance_clients_jours_N": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "delai_creance_clients_jours_N_1": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "delai_dettes_fournisseurs_jours_N": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                            "delai_dettes_fournisseurs_jours_N_1": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                            ),
                        },
                    ),
                    "donnees_non_calculables": genai.types.Schema(
                        type=genai.types.Type.ARRAY,
                        description="Liste des ratios marqués comme 'Non calculable' en raison de données manquantes",
                        items=genai.types.Schema(
                            type=genai.types.Type.STRING,
                        ),
                    ),
                    "analyse_detaillee": genai.types.Schema(
                        type=genai.types.Type.STRING,
                        description="Analyse détaillée de la situation financière basée sur les ratios calculés",
                    ),
                },
            ),
        )
        
        logger.info("Starting Gemini analysis with comprehensive ratio calculation...")
        
        loop = asyncio.get_running_loop()
        generate_func = functools.partial(
            client.models.generate_content,
            model=model,
            contents=contents,
            config=generate_content_config
        )
        
        response = await loop.run_in_executor(None, generate_func)
        
        total_time = time.time() - start_time
        logger.info(f"Gemini completed in {total_time:.2f}s")
        
        if not response or not response.text:
            logger.error("Gemini returned empty response")
            return "Error: Received an empty response from Gemini."
        
        # Log Gemini output in clean ASCII format
        try:
            gemini_output_clean = response.text.encode('ascii', 'replace').decode('ascii')
            logger.info("=== GEMINI OUTPUT ===")
            logger.info(gemini_output_clean)
            logger.info("=== END GEMINI OUTPUT ===")
        except Exception:
            logger.warning("Could not log Gemini output in ASCII format")
        
        return response.text

    except Exception as e:
        logger.error(f"Gemini analysis failed: {str(e)}")
        return f"An error occurred during the Gemini analysis process: {str(e)}" 