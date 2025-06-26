import time
import json
from clients import initialize_claude
from logger import logger


def query_claude(company_name: str, claude_ratio_output: str, annual_rent: str, conversation_context=None) -> str:
    """Call Claude API with Claude ratio output for final financial analysis"""
    start_time = time.time()
    
    client = initialize_claude()
    if not client:
        return json.dumps({"status": "error", "message": "Error initializing Claude client"}, indent=2)

    try:
        # Create prompt for Claude
        prompt = f"""CONTEXTE ET MISSION

Vous êtes un analyste financier senior spécialisé dans l'évaluation de solvabilité locative. Votre mission : Analyser la solidité financière d'une entreprise candidate à la location d'un local commercial à partir des ratios financiers et données brutes calculés par l'Agent 1.

Input reçu : JSON complet contenant tous les ratios financiers calculés sur les deux derniers exercices et les données brutes essentielles.

Output attendu : Format JSON avec ratios (recopiés de l'input) + chiffres clés (recopiés de l'input) + analyse financière complète de 800 mots.

Objectif final : Déterminer la fiabilité de l'entreprise en tant que futur locataire et formuler une recommandation argumentée en tenant compte du montant du loyer.

INPUT ATTENDU

{{  "claude_ratio service output": {claude_ratio_output}, 
  "company_name": "{company_name}", 
  "loyer": "{annual_rent}" 
}}

INSTRUCTIONS CRITIQUES POUR LE FORMAT DE SORTIE

1. Votre réponse DOIT être un JSON valide UNIQUEMENT
2. Aucun texte avant ou après le JSON
3. Aucun markdown, aucune explication, SEULEMENT le JSON
4. L'analyse de 800 mots doit être une STRING dans le champ "analyse_financiere"

FORMAT DE SORTIE OBLIGATOIRE

Votre réponse doit être un JSON unique contenant ces trois sections :

{{ "companyName": "Nom de l'entreprise", "annualRent": "Chiffre d'affaires annuel en K€", "annee_n": "année", "annee_n_moins_1": "année", "ratios": {{ "structure_financiere": {{ "annee_n": {{ "ressources_propres": "valeur", "ressources_stables": "valeur", "capital_exploitation": "valeur", "actif_circulant_exploitation": "valeur", "actif_circulant_hors_exploitation": "valeur", "dettes_exploitation": "valeur", "dettes_hors_exploitation": "valeur", "surface_financiere_pct": "valeur", "couverture_immobilisations_fonds_propres_pct": "valeur", "couverture_emplois_stables_pct": "valeur", "frng": "valeur", "bfr": "valeur", "tresorerie_nette": "valeur", "independance_financiere_pct": "valeur", "liquidite_entreprise_pct": "valeur" }}, "annee_n_moins_1": {{ "ressources_propres": "valeur", "ressources_stables": "valeur", "capital_exploitation": "valeur", "actif_circulant_exploitation": "valeur", "actif_circulant_hors_exploitation": "valeur", "dettes_exploitation": "valeur", "dettes_hors_exploitation": "valeur", "surface_financiere_pct": "valeur", "couverture_immobilisations_fonds_propres_pct": "valeur", "couverture_emplois_stables_pct": "valeur", "frng": "valeur", "bfr": "valeur", "tresorerie_nette": "valeur", "independance_financiere_pct": "valeur", "liquidite_entreprise_pct": "valeur" }} }}, "activite_exploitation": {{ "annee_n": {{ "marge_globale": "valeur", "valeur_ajoutee": "valeur", "ebe": "valeur", "caf": "valeur", "charges_personnel_valeur_ajoutee_pct": "valeur", "impots_valeur_ajoutee_pct": "valeur", "charges_financieres_valeur_ajoutee_pct": "valeur", "taux_marge_globale_pct": "valeur", "taux_valeur_ajoutee_pct": "valeur", "taux_marge_beneficiaire_pct": "valeur", "taux_marge_brute_exploitation_pct": "valeur", "taux_obsolescence_pct": "valeur" }}, "annee_n_moins_1": {{ "marge_globale": "valeur", "valeur_ajoutee": "valeur", "ebe": "valeur", "caf": "valeur", "charges_personnel_valeur_ajoutee_pct": "valeur", "impots_valeur_ajoutee_pct": "valeur", "charges_financieres_valeur_ajoutee_pct": "valeur", "taux_marge_globale_pct": "valeur", "taux_valeur_ajoutee_pct": "valeur", "taux_marge_beneficiaire_pct": "valeur", "taux_marge_brute_exploitation_pct": "valeur", "taux_obsolescence_pct": "valeur" }} }}, "rentabilite": {{ "annee_n": {{ "rentabilite_capitaux_propres_pct": "valeur", "rentabilite_economique_pct": "valeur", "rentabilite_financiere_pct": "valeur", "rentabilite_brute_ressources_stables_pct": "valeur", "rentabilite_brute_capital_exploitation_pct": "valeur" }}, "annee_n_moins_1": {{ "rentabilite_capitaux_propres_pct": "valeur", "rentabilite_economique_pct": "valeur", "rentabilite_financiere_pct": "valeur", "rentabilite_brute_ressources_stables_pct": "valeur", "rentabilite_brute_capital_exploitation_pct": "valeur" }} }}, "evolution": {{ "taux_variation_chiffre_affaires_pct": "valeur", "taux_variation_valeur_ajoutee_pct": "valeur", "taux_variation_resultat_pct": "valeur", "taux_variation_capitaux_propres_pct": "valeur" }}, "tresorerie_financement": {{ "annee_n": {{ "capacite_generer_cash": "valeur", "capacite_remboursement_dette": "valeur", "credits_bancaires_bfr": "valeur" }}, "annee_n_moins_1": {{ "capacite_generer_cash": "valeur", "capacite_remboursement_dette": "valeur", "credits_bancaires_bfr": "valeur" }} }}, "delais_paiement": {{ "annee_n": {{ "delai_creance_clients_jours": "valeur", "delai_dettes_fournisseurs_jours": "valeur" }}, "annee_n_moins_1": {{ "delai_creance_clients_jours": "valeur", "delai_dettes_fournisseurs_jours": "valeur" }} }} }}, "chiffres_cles": {{ "chiffre_affaires_n": "valeur en K€", "chiffre_affaires_n_moins_1": "valeur en K€", "marge_globale_n": "valeur en K€", "marge_globale_n_moins_1": "valeur en K€", "taux_marge_globale_n": "valeur en %", "taux_marge_globale_n_moins_1": "valeur en %", "valeur_ajoutee_n": "valeur en K€", "valeur_ajoutee_n_moins_1": "valeur en K€", "taux_valeur_ajoutee_n": "valeur en %", "taux_valeur_ajoutee_n_moins_1": "valeur en %", "ebe_n": "valeur en K€", "ebe_n_moins_1": "valeur en K€", "resultat_exploitation_n": "valeur en K€", "resultat_exploitation_n_moins_1": "valeur en K€", "resultat_financier_n": "valeur en K€", "resultat_financier_n_moins_1": "valeur en K€", "resultat_courant_n": "valeur en K€", "resultat_courant_n_moins_1": "valeur en K€", "resultat_exercice_n": "valeur en K€", "resultat_exercice_n_moins_1": "valeur en K€", "marge_exploitation_n": "valeur en %", "marge_exploitation_n_moins_1": "valeur en %", "resultat_net_n": "valeur en K€", "resultat_net_n_moins_1": "valeur en K€", "capitaux_propres_n": "valeur en K€", "capitaux_propres_n_moins_1": "valeur en K€", "dette_financiere_n": "valeur en K€", "dette_financiere_n_moins_1": "valeur en K€" }}, "analyse_financiere": "Texte de l'analyse complète de 800 mots" }}

ANALYSE FINANCIÈRE À PRODUIRE

Objectif : Rédiger une analyse complète de 800 mots environ basée exclusivement sur les ratios et données reçus de l'Agent 1.

STRUCTURE OBLIGATOIRE DE L'ANALYSE

1. Évolution des indicateurs clés

Évolution du chiffre d'affaires (taux de variation)

Évolution du résultat net (taux de variation)

Évolution des capitaux propres (taux de variation)

Tendance générale de l'activité

2. Structure financière

Solvabilité de l'entreprise (surface financière, ressources propres)

Niveau d'endettement (indépendance financière)

Équilibre financier (FRNG, BFR, trésorerie nette)

Couverture des immobilisations

3. Rentabilité

Rentabilité économique (performance opérationnelle)

Rentabilité financière (retour sur capitaux propres)

Rentabilité des ressources stables

Évolution des marges (globale, bénéficiaire, brute d'exploitation)

4. Capacité d'autofinancement et trésorerie

Analyse de la CAF et EBE

Capacité à générer du cash

Capacité de remboursement

Situation de trésorerie

5. Analyse de l'exploitation

Poids des charges de personnel sur la valeur ajoutée

Impact des impôts et taxes sur la valeur ajoutée

Charges financières sur la valeur ajoutée

Efficacité opérationnelle

6. Cycle d'exploitation

Délais clients (créances)

Délais fournisseurs (dettes)

Analyse du besoin en fonds de roulement

Gestion du cycle cash

7. Conclusion argumentée

Synthèse des forces et faiblesses financières

Évaluation du niveau de risque locatif (faible/moyen/élevé)

Recommandation finale motivée (favorable/réservée/défavorable)

Points de vigilance éventuels

CONSIGNES MÉTHODOLOGIQUES

À FAIRE

Recopier exactement tous les ratios calculés reçus de l'Agent 1 dans la section "ratios"

Extraire les données brutes reçues pour compléter le JSON

Utiliser exclusivement les ratios et données fournis par l'Agent 1 pour l'analyse

Intégrer le montant du loyer dans l'analyse de solvabilité locative

Calculer le ratio loyer/chiffre d'affaires et loyer/EBE pour évaluer la capacité de paiement

Citer des valeurs précises et des pourcentages exacts

Comparer l'évolution entre les deux exercices

Adopter un ton professionnel et factuel

Formuler une recommandation claire et argumentée

Identifier les tendances (amélioration/dégradation/stabilité)

INTERDIT ABSOLU

Référencer dans l'analyse des données ou ratios non fournis par l'Agent 1

Inventer ou extrapoler des données non fournies

Faire référence à des éléments non présents dans les ratios reçus

Donner des conseils opérationnels à l'entreprise

Formuler des hypothèses non fondées sur les ratios

ÉVALUATION DU RISQUE LOCATAIRE

Critères d'évaluation à considérer :

Stabilité et croissance du chiffre d'affaires

Solidité de la structure financière

Niveau d'endettement et indépendance financière

Capacité de génération de trésorerie

Évolution de la rentabilité

Gestion du BFR et des délais de paiement

Capacité de paiement du loyer (ratio loyer/CA, loyer/EBE, loyer/résultat net)

Niveaux de risque :

Risque faible : Situation financière saine, recommandation favorable

Risque moyen : Situation mitigée, recommandation avec réserves ou conditions

Risque élevé : Situation préoccupante, recommandation défavorable

CLAUSE DE LIMITATION

Si un ratio n'est pas calculable ou manquant dans les données reçues, l'indiquer clairement dans l'analyse. Pour les chiffres clés manquants, utiliser "Non disponible" dans le JSON. Préciser que l'évaluation est basée uniquement sur les ratios financiers disponibles et constitue un avis indicatif qui doit être complété par d'autres éléments d'appréciation (secteur d'activité, historique de paiement, garanties, etc.).

CONCLUSION TYPE À ADAPTER

"Au regard de l'analyse des ratios financiers, l'entreprise présente un profil de risque [FAIBLE/MOYEN/ÉLEVÉ] en tant que locataire potentiel. [Synthèse en 2-3 phrases des points clés]. Cette évaluation, basée sur les seuls états financiers, devra être complétée par l'analyse d'autres critères (secteur, historique, garanties) pour une décision définitive."

INSTRUCTIONS FINALES

Utilisez UNIQUEMENT les ratios et données fournis par l'Agent 1

Recopiez exactement tous les ratios calculés dans la section "ratios" du JSON de sortie

Intégrez le montant du loyer dans votre analyse de solvabilité

Retournez UNIQUEMENT le JSON structuré avec les trois sections : ratios, chiffres_cles (recopie des données brutes), analyse_financiere

Contrôle qualité : Votre analyse doit référencer des ratios concrets présents dans les données reçues

RÈGLE ABSOLUE : Votre réponse doit être un JSON valide et complet, sans aucun texte avant ou après le JSON

Ton pour l'analyse : Professionnel, précis, factuel

Format de l'analyse : Texte de 800 mots avec phrases courtes, données chiffrées, pourcentages précis

Conclusion : Recommandation claire avec niveau de risque explicite

IMPORTANT : Commencez votre réponse directement par {{ et terminez par }}. Aucun texte explicatif."""

        logger.info(f"Calling Claude for final financial analysis for {company_name}")

        logger.info(f"Making Claude API call for final analysis")

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,
            temperature=0.2,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        if not response or not response.content:
            logger.error("Claude returned empty response")
            return json.dumps({"status": "error", "message": "Empty response from Claude"}, indent=2)
        
        response_text = response.content[0].text
        
        total_time = time.time() - start_time
        logger.info(f"Claude analysis completed in {total_time:.2f}s")
        
        # Try to parse and validate the JSON response
        try:
            parsed_response = json.loads(response_text)
            logger.info("Claude returned valid JSON for financial analysis")
            return json.dumps(parsed_response, ensure_ascii=False, indent=2)
        except json.JSONDecodeError as e:
            logger.error(f"Claude returned invalid JSON: {e}")
            logger.error(f"Response text length: {len(response_text)}")
            logger.error(f"Response text (first 200 chars): '{response_text[:200]}'")
            logger.debug(f"Raw response (first 1000 chars): {response_text[:1000]}")
            
            # Try to extract JSON from the response if it's wrapped in text
            text = response_text.strip()
            
            if not text:
                logger.error("Claude returned completely empty response")
                return json.dumps({
                    "status": "error", 
                    "message": "Claude returned empty response for final analysis"
                }, indent=2)
            
            # Look for JSON object patterns  
            start_idx = text.find('{')
            end_idx = text.rfind('}')
            
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                try:
                    json_part = text[start_idx:end_idx + 1]
                    parsed_json = json.loads(json_part)
                    logger.info("Successfully extracted JSON from Claude response")
                    return json.dumps(parsed_json, ensure_ascii=False, indent=2)
                except json.JSONDecodeError as extract_error:
                    logger.error(f"Could not extract valid JSON from Claude response: {extract_error}")
                    logger.error(f"Attempted to parse: '{json_part[:200]}'")
            else:
                logger.error("No JSON object pattern found in Claude response")
            
            # If JSON extraction fails, return the error in a structured format
            return json.dumps({
                "status": "error", 
                "message": f"Claude returned malformed JSON: {str(e)}",
                "raw_response": response_text[:500]
            }, indent=2)
        
    except Exception as e:
        logger.error(f"Claude analysis failed: {str(e)}", exc_info=True)
        total_time = time.time() - start_time
        return json.dumps({
            "status": "error",
            "message": f"Error during Claude analysis: {str(e)}",
            "processing_time": total_time
        }, indent=2) 