import time
import json
from clients import initialize_claude
from logger import logger


def query_claude(company_name: str, gemini_output: str, conversation_context=None) -> str:
    """Call Claude API with Gemini output for final synthesis"""
    start_time = time.time()
    
    client = initialize_claude()
    if not client:
        return json.dumps({"status": "error", "message": "Error initializing Claude client"}, indent=2)

    try:
        # Create prompt for Claude
        prompt = f"""MISSION GLOBALE - ANALYSE FINANCIÈRE COMPLÈTE POUR ÉVALUATION LOCATAIRE

Vous devez réaliser une analyse financière complète en deux étapes successives :
1. ÉTAPE 1 : Calculer tous les ratios financiers requis (calcul interne)
2. ÉTAPE 2 : Analyser ces ratios pour évaluer la solvabilité locative (sortie finale)

Input : Bilan comptable (actif/passif) et compte de résultat détaillé sur les deux derniers exercices
Output final : Ratios clés JSON + Chiffres clés JSON + Analyse financière complète de 800 mots

IMPORTANT: Vous DEVEZ d'abord calculer TOUS les ratios de l'étape 1 avant de procéder à l'étape 2. Aucune analyse ne peut commencer sans avoir terminé tous les calculs.

═══════════════════════════════════════════════════════════════════════════════════

ÉTAPE 1 - CALCUL DES RATIOS FINANCIERS (CALCUL INTERNE)

CONTEXTE ET MISSION
Vous êtes un analyste financier spécialisé dans le calcul de ratios comptables.
Votre mission : Calculer tous les ratios financiers requis à partir des données financières fournies (sur les deux derniers exercices).
IMPORTANT : AUCUNE ANALYSE N'EST DEMANDÉE. CALCULEZ UNIQUEMENT LES RATIOS.

**Input reçu pour l'entreprise {company_name} :** {gemini_output}

RATIOS À CALCULER
IMPORTANT : Calculez UNIQUEMENT les ratios listés ci-dessous, pour les deux exercices disponibles en précisant l'année. N'ajoutez aucun ratio supplémentaire.

STRUCTURE FINANCIÈRE
Ratio | Formule
Ressources propres | Capitaux propres + Amortissements cumulés + Emprunts et dettes auprès des établissements de crédit + Emprunts et dettes financières divers
Ressources stables | Capitaux propres + Amortissements cumulés
Capital d'exploitation | Total de l'actif circulant – Total du passif circulant (=avances et accomptes reçus sur commandes en cours +dettes fournisseurs et comptes rattachés + dettes fiscales et sociales + dettes sur immobilisations et comptes rattachés + autres dettes)
Actif circulant d'exploitation | Matières premières et marchandises + Avances et acomptes versés sur commandes + Clients et comptes rattachés + Autres créances + Charges constatées d'avance
Actif circulant hors exploitation | Capital souscrit appelé, non versé
Dettes d'exploitation | Avances et acomptes reçus sur commandes en cours + Dettes fournisseurs et comptes rattachés + Dettes fiscales et sociales
Dettes hors exploitation | Dettes sur immobilisations et comptes rattachés + autres dettes
Surface financière (%) | Capitaux propres / Total du passif
Couverture des immobilisations par les fonds propres (%) | Total brut des immobilisations / Ressources propres
Couverture des emplois stables (%) | Ressources propres / Total brut des immobilisations
FRNG (Fonds de roulement net global) | Capitaux propres + Emprunts et dettes auprès des établissements de crédit + Emprunts et dettes financières divers – Total brut des immobilisations
BFR (Besoin en fonds de roulement) | Actif circulant d'exploitation + Actif circulant hors exploitation – Dettes d'exploitation - Dettes hors exploitation
Trésorerie nette | FRNG – BFR
Indépendance financière (%) | (Emprunts et dettes auprès des établissements de crédit + Emprunts et dettes financières divers ) / Capitaux propres
Liquidité de l'entreprise (%) | (créances clients et comptes rattachés + disponibilités)/dettes fournisseurs et comptes rattachés

ACTIVITÉ D'EXPLOITATION
Ratio | Formule
Marge globale | Chiffre d'affaires net – Achats de marchandises – Achats de matières premières et autres approvisionnements - variation de stocks (marchandises et matières premières)
Valeur ajoutée | Marge globale + Production stockée + Production immobilisée – Autres achats et charges externes
EBE (excédent brut d'exploitation) | Valeur ajoutée + Subventions d'exploitation – Impôts, taxes et versements assimilés – Salaires et traitements – Charges sociales
CAF (capacité d'auto financement) | EBE + total des produits financiers + total des produits exceptionnels – total des charges financières – total des charges exceptionnelles
Charges de personnel / Valeur ajoutée (%) | (Salaires et traitements + Charges sociales) / Valeur ajoutée
Impôts / Valeur ajoutée (%) | Impôts, taxes et versements assimilés / Valeur ajoutée
Charges financières / Valeur ajoutée (%) | Charges financières / Valeur ajoutée
Taux de marge globale (%) | Marge globale / (Ventes de marchandises + Production vendue de biens + production vendue de services)
Taux de valeur ajoutée (%) | Valeur ajoutée / Chiffre d'affaires net
Taux de marge bénéficiaire (%) | Résultat net comptable / Chiffre d'affaires net
Taux de marge brute d'exploitation (%) | EBE / Chiffre d'affaires net
Taux d'obsolescence (%) | Dotations d'exploitation / Total des actifs immobilisés (Total II)

RENTABILITÉ
Ratio | Formule
Rentabilité des capitaux propres (%) | Résultat net comptable / Capitaux propres
Rentabilité économique (%) | (Résultat net comptable + total des charges financières) / (Ressources propres)
Rentabilité financière (%) | Résultat net comptable / (Ressources propres)
Rentabilité brute des ressources stables (%) | EBE / (Ressources propres)
Rentabilité brute du capital d'exploitation (%) | EBE / (Total de l'actif circulant – Total du passif circulant)

ÉVOLUTION
Ratio | Formule
Taux de variation du chiffre d'affaires (%) | (Chiffre d'affaires net N+1 – Chiffre d'affaires net N) / Chiffre d'affaires net N
Taux de variation de la valeur ajoutée (%) | (Valeur ajoutée N+1 – Valeur ajoutée N) / Valeur ajoutée N
Taux de variation du résultat (%) | (Résultat net comptable N+1 – Résultat net comptable N) / Résultat net comptable N
Taux de variation des capitaux propres (%) | (Capitaux propres N+1 – Capitaux propres N) / Capitaux propres N

TRÉSORERIE & FINANCEMENT
Ratio | Formule
Capacité à générer du cash | EBE + Produits financiers + Produits exceptionnels – Charges financières– Charges exceptionnelles
Capacité de remboursement de la dette | (Emprunts et dettes auprès des établissements de crédit + Emprunts et dettes financières divers) / Capacité à générer du cash
Crédits bancaires courants / BFR | (Emprunts et dettes auprès des établissements de crédit + Emprunts et dettes financières divers) /BFR

DÉLAIS DE PAIEMENT
Ratio | Formule
Délai créance clients (en jours) | (Clients et comptes rattachés / Chiffre d'affaires net) × 360
Délai dettes fournisseurs (en jours) | (Dettes fournisseurs et comptes rattachés / (Achats de marchandises + Autres achats et charges externes)) × 360

Si certains éléments des formules ne sont pas exactement les mêmes, prenez les éléments dont le sens et les mots se rapprochent le plus. Evitez tout de même.

CONSIGNES DE CALCUL ÉTAPE 1
À FAIRE UNIQUEMENT
- Extraire les données des états financiers fournis
- Calculer tous les ratios pour les deux exercices disponibles
- Arrondir à 1 décimale pour les pourcentages et nombres décimaux
- Indiquer "Non calculable" si une donnée manque pour un ratio

EN CAS DE DONNÉES MANQUANTES
Si un élément comptable n'apparaît pas dans les états financiers, indiquer uniquement "Donnée non disponible" et marquer le ratio comme "Non calculable".

VÉRIFICATION OBLIGATOIRE AVANT ANALYSE
Avant de commencer l'analyse, vérifiez que tous les ratios listés ont été calculés (ou marqués 'Non calculable' si données manquantes). Aucune analyse ne peut débuter sans cette vérification complète.

═══════════════════════════════════════════════════════════════════════════════════

ÉTAPE 2 - ANALYSE FINANCIÈRE POUR ÉVALUATION LOCATAIRE (SORTIE FINALE)

CONTEXTE ET MISSION
Vous êtes un analyste financier senior spécialisé dans l'évaluation de solvabilité locative.
Votre mission : Analyser la solidité financière d'une entreprise candidate à la location d'un de nos locaux commerciaux à partir des ratios financiers déjà calculés à l'étape 1.
Input reçu : Ratios financiers calculés sur les deux derniers exercices.
Output attendu : Format JSON avec ratios clés + chiffres clés + analyse financière complète.
Objectif final : Déterminer la fiabilité de l'entreprise en tant que futur locataire et formuler une recommandation argumentée.

FORMAT DE SORTIE ÉTAPE 2 (SORTIE FINALE)
Votre réponse doit contenir exactement ces trois éléments dans cet ordre :

1. RATIOS CLÉS (Format JSON)
{{
  "rentabilite": {{
    "annee_n": {{
      "rentabilite_capitaux_propres_pct": "valeur",
      "rentabilite_economique_pct": "valeur",
      "rentabilite_financiere_pct": "valeur",
      "rentabilite_brute_ressources_stables_pct": "valeur",
      "rentabilite_brute_capital_exploitation_pct": "valeur"
    }},
    "annee_n_moins_1": {{
      "rentabilite_capitaux_propres_pct": "valeur",
      "rentabilite_economique_pct": "valeur",
      "rentabilite_financiere_pct": "valeur",
      "rentabilite_brute_ressources_stables_pct": "valeur",
      "rentabilite_brute_capital_exploitation_pct": "valeur"
    }}
  }},
  "evolution": {{
    "taux_variation_chiffre_affaires_pct": "valeur",
    "taux_variation_valeur_ajoutee_pct": "valeur", 
    "taux_variation_resultat_pct": "valeur",
    "taux_variation_capitaux_propres_pct": "valeur"
  }},
  "tresorerie_financement": {{
    "annee_n": {{
      "capacite_generer_cash": "valeur",
      "capacite_remboursement_dette": "valeur",
      "credits_bancaires_bfr": "valeur"
    }},
    "annee_n_moins_1": {{
      "capacite_generer_cash": "valeur", 
      "capacite_remboursement_dette": "valeur",
      "credits_bancaires_bfr": "valeur"
    }}
  }},
  "delais_paiement": {{
    "annee_n": {{
      "delai_creance_clients_jours": "valeur",
      "delai_dettes_fournisseurs_jours": "valeur"
    }},
    "annee_n_moins_1": {{
      "delai_creance_clients_jours": "valeur",
      "delai_dettes_fournisseurs_jours": "valeur"
    }}
  }}
}}

2. CHIFFRES CLÉS (Format JSON)
{{
  "chiffre_affaires_n": "valeur en K€",
  "chiffre_affaires_n_moins_1": "valeur en K€",
  "resultat_exploitation_n": "valeur en K€",
  "resultat_exploitation_n_moins_1": "valeur en K€",
  "marge_exploitation_n": "valeur en %",
  "marge_exploitation_n_moins_1": "valeur en %",
  "resultat_net_n": "valeur en K€",
  "resultat_net_n_moins_1": "valeur en K€",
  "capitaux_propres_n": "valeur en K€",
  "capitaux_propres_n_moins_1": "valeur en K€",
  "dette_financiere_n": "valeur en K€",
  "dette_financiere_n_moins_1": "valeur en K€"
}}

3. ANALYSE FINANCIÈRE (800 mots)

ANALYSE FINANCIÈRE À PRODUIRE
Objectif : Rédiger une analyse complète de 800 mots environ basée exclusivement sur les ratios calculés à l'étape 1.

STRUCTURE OBLIGATOIRE DE L'ANALYSE
1. Évolution des indicateurs clés
   • Évolution du chiffre d'affaires (taux de variation)
   • Évolution du résultat net (taux de variation)
   • Évolution des capitaux propres (taux de variation)
   • Tendance générale de l'activité

2. Structure financière
   • Solvabilité de l'entreprise (surface financière, ressources propres)
   • Niveau d'endettement (indépendance financière)
   • Équilibre financier (FRNG, BFR, trésorerie nette)
   • Couverture des immobilisations

3. Rentabilité
   • Rentabilité économique (performance opérationnelle)
   • Rentabilité financière (retour sur capitaux propres)
   • Rentabilité des ressources stables
   • Évolution des marges (globale, bénéficiaire, brute d'exploitation)

4. Capacité d'autofinancement et trésorerie
   • Analyse de la CAF et EBE
   • Capacité à générer du cash
   • Capacité de remboursement
   • Situation de trésorerie

5. Analyse de l'exploitation
   • Poids des charges de personnel sur la valeur ajoutée
   • Impact des impôts et taxes sur la valeur ajoutée
   • Charges financières sur la valeur ajoutée
   • Efficacité opérationnelle

6. Cycle d'exploitation
   • Délais clients (créances)
   • Délais fournisseurs (dettes)
   • Analyse du besoin en fonds de roulement
   • Gestion du cycle cash

7. Conclusion argumentée
   • Synthèse des forces et faiblesses financières
   • Évaluation du niveau de risque locatif (faible/moyen/élevé)
   • Recommandation finale motivée (favorable/réservée/défavorable)
   • Points de vigilance éventuels

CONSIGNES MÉTHODOLOGIQUES
À FAIRE
- Extraire les ratios clés et chiffres clés des calculs de l'étape 1 pour compléter les JSON
- Utiliser exclusivement les ratios calculés à l'étape 1 pour l'analyse
- Citer des valeurs précises et des pourcentages exacts
- Comparer l'évolution entre les deux exercices
- Adopter un ton professionnel et factuel
- Formuler une recommandation claire et argumentée
- Identifier les tendances (amélioration/dégradation/stabilité)

INTERDIT ABSOLU
- Référencer dans l'analyse des données ou ratios non calculés à l'étape 1
- Inventer ou extrapoler des données non fournies
- Faire référence à des éléments non présents dans les ratios calculés
- Donner des conseils opérationnels à l'entreprise
- Formuler des hypothèses non fondées sur les ratios

ÉVALUATION DU RISQUE LOCATAIRE
Critères d'évaluation à considérer :
- Stabilité et croissance du chiffre d'affaires
- Solidité de la structure financière
- Niveau d'endettement et indépendance financière
- Capacité de génération de trésorerie
- Évolution de la rentabilité
- Gestion du BFR et des délais de paiement

Niveaux de risque :
- Risque faible : Situation financière saine, recommandation favorable
- Risque moyen : Situation mitigée, recommandation avec réserves ou conditions
- Risque élevé : Situation préoccupante, recommandation défavorable

CLAUSE DE LIMITATION
Si un ratio n'est pas calculable ou manquant, l'indiquer clairement dans l'analyse. Pour les chiffres clés manquants, utiliser "Non disponible" dans le JSON. Préciser que l'évaluation est basée uniquement sur les ratios financiers disponibles et constitue un avis indicatif qui doit être complété par d'autres éléments d'appréciation (secteur d'activité, historique de paiement, garanties, etc.).

═══════════════════════════════════════════════════════════════════════════════════

INSTRUCTIONS FINALES
1. Calculez d'abord tous les ratios requis à l'étape 1 (calcul interne)
2. Vérifiez que tous les ratios sont calculés avant de procéder à l'analyse
3. Utilisez ces ratios et uniquement ces ratios pour produire l'analyse finale de l'étape 2
4. Ne montrez que la sortie de l'étape 2 : JSON ratios clés + JSON chiffres clés + Analyse de 800 mots

Ton : Professionnel, précis, factuel
Format : JSON ratios clés + JSON chiffres clés + analyse complète avec phrases courtes, données chiffrées, pourcentages précis
Conclusion : Recommandation claire avec niveau de risque explicite

Conclusion type à adapter dans l'analyse :
"Au regard de l'analyse des ratios financiers, l'entreprise présente un profil de risque [FAIBLE/MOYEN/ÉLEVÉ] en tant que locataire potentiel. [Synthèse en 2-3 phrases des points clés]. Cette évaluation, basée sur les seuls états financiers, devra être complétée par l'analyse d'autres critères (secteur, historique, garanties) pour une décision définitive."
"""

        logger.info("Starting Claude synthesis...")
        
        # Define the structured output schema
        response_schema = {
            "type": "object",
            "properties": {
                "ratios_cles": {
                    "type": "object",
                    "properties": {
                        "rentabilite": {
                            "type": "object",
                            "properties": {
                                "annee_n": {
                                    "type": "object",
                                    "properties": {
                                        "rentabilite_capitaux_propres_pct": {"type": ["number", "string"]},
                                        "rentabilite_economique_pct": {"type": ["number", "string"]},
                                        "rentabilite_financiere_pct": {"type": ["number", "string"]},
                                        "rentabilite_brute_ressources_stables_pct": {"type": ["number", "string"]},
                                        "rentabilite_brute_capital_exploitation_pct": {"type": ["number", "string"]}
                                    },
                                    "required": ["rentabilite_capitaux_propres_pct", "rentabilite_economique_pct", "rentabilite_financiere_pct", "rentabilite_brute_ressources_stables_pct", "rentabilite_brute_capital_exploitation_pct"]
                                },
                                "annee_n_moins_1": {
                                    "type": "object",
                                    "properties": {
                                        "rentabilite_capitaux_propres_pct": {"type": ["number", "string"]},
                                        "rentabilite_economique_pct": {"type": ["number", "string"]},
                                        "rentabilite_financiere_pct": {"type": ["number", "string"]},
                                        "rentabilite_brute_ressources_stables_pct": {"type": ["number", "string"]},
                                        "rentabilite_brute_capital_exploitation_pct": {"type": ["number", "string"]}
                                    },
                                    "required": ["rentabilite_capitaux_propres_pct", "rentabilite_economique_pct", "rentabilite_financiere_pct", "rentabilite_brute_ressources_stables_pct", "rentabilite_brute_capital_exploitation_pct"]
                                }
                            },
                            "required": ["annee_n", "annee_n_moins_1"]
                        },
                        "evolution": {
                            "type": "object",
                            "properties": {
                                "taux_variation_chiffre_affaires_pct": {"type": ["number", "string"]},
                                "taux_variation_valeur_ajoutee_pct": {"type": ["number", "string"]},
                                "taux_variation_resultat_pct": {"type": ["number", "string"]},
                                "taux_variation_capitaux_propres_pct": {"type": ["number", "string"]}
                            },
                            "required": ["taux_variation_chiffre_affaires_pct", "taux_variation_valeur_ajoutee_pct", "taux_variation_resultat_pct", "taux_variation_capitaux_propres_pct"]
                        },
                        "tresorerie_financement": {
                            "type": "object",
                            "properties": {
                                "annee_n": {
                                    "type": "object",
                                    "properties": {
                                        "capacite_generer_cash": {"type": ["number", "string"]},
                                        "capacite_remboursement_dette": {"type": ["number", "string"]},
                                        "credits_bancaires_bfr": {"type": ["number", "string"]}
                                    },
                                    "required": ["capacite_generer_cash", "capacite_remboursement_dette", "credits_bancaires_bfr"]
                                },
                                "annee_n_moins_1": {
                                    "type": "object",
                                    "properties": {
                                        "capacite_generer_cash": {"type": ["number", "string"]},
                                        "capacite_remboursement_dette": {"type": ["number", "string"]},
                                        "credits_bancaires_bfr": {"type": ["number", "string"]}
                                    },
                                    "required": ["capacite_generer_cash", "capacite_remboursement_dette", "credits_bancaires_bfr"]
                                }
                            },
                            "required": ["annee_n", "annee_n_moins_1"]
                        },
                        "delais_paiement": {
                            "type": "object",
                            "properties": {
                                "annee_n": {
                                    "type": "object",
                                    "properties": {
                                        "delai_creance_clients_jours": {"type": ["number", "string"]},
                                        "delai_dettes_fournisseurs_jours": {"type": ["number", "string"]}
                                    },
                                    "required": ["delai_creance_clients_jours", "delai_dettes_fournisseurs_jours"]
                                },
                                "annee_n_moins_1": {
                                    "type": "object",
                                    "properties": {
                                        "delai_creance_clients_jours": {"type": ["number", "string"]},
                                        "delai_dettes_fournisseurs_jours": {"type": ["number", "string"]}
                                    },
                                    "required": ["delai_creance_clients_jours", "delai_dettes_fournisseurs_jours"]
                                }
                            },
                            "required": ["annee_n", "annee_n_moins_1"]
                        }
                    },
                    "required": ["rentabilite", "evolution", "tresorerie_financement", "delais_paiement"]
                },
                "chiffres_cles": {
                    "type": "object",
                    "properties": {
                        "chiffre_affaires_n": {"type": "string"},
                        "chiffre_affaires_n_moins_1": {"type": "string"},
                        "resultat_exploitation_n": {"type": "string"},
                        "resultat_exploitation_n_moins_1": {"type": "string"},
                        "marge_exploitation_n": {"type": "string"},
                        "marge_exploitation_n_moins_1": {"type": "string"},
                        "resultat_net_n": {"type": "string"},
                        "resultat_net_n_moins_1": {"type": "string"},
                        "capitaux_propres_n": {"type": "string"},
                        "capitaux_propres_n_moins_1": {"type": "string"},
                        "dette_financiere_n": {"type": "string"},
                        "dette_financiere_n_moins_1": {"type": "string"}
                    },
                    "required": ["chiffre_affaires_n", "chiffre_affaires_n_moins_1", "resultat_exploitation_n", "resultat_exploitation_n_moins_1", "marge_exploitation_n", "marge_exploitation_n_moins_1", "resultat_net_n", "resultat_net_n_moins_1", "capitaux_propres_n", "capitaux_propres_n_moins_1", "dette_financiere_n", "dette_financiere_n_moins_1"]
                },
                "analyse_financiere": {
                    "type": "string",
                    "description": "Analyse financière complète de 800 mots suivant la structure obligatoire définie"
                }
            },
            "required": ["ratios_cles", "chiffres_cles", "analyse_financiere"]
        }
        
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,
            temperature=0.2,
            system="Vous êtes un analyste financier senior spécialisé dans l'évaluation de solvabilité locative.",
            messages=[
                {"role": "user", "content": prompt}
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "analyse_financiere_complete",
                    "description": "Analyse financière structurée avec ratios clés, chiffres clés et analyse textuelle",
                    "schema": response_schema
                }
            }
        )
        
        # Parse the structured response
        try:
            response_text = message.content[0].text
            parsed_response = json.loads(response_text)
            
            # Convert back to JSON string for consistent handling
            response_text = json.dumps(parsed_response, indent=2, ensure_ascii=False)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude JSON response: {e}")
            # Return error in expected format
            error_response = {
                "ratios_cles": {
                    "rentabilite": {"annee_n": {}, "annee_n_moins_1": {}},
                    "evolution": {},
                    "tresorerie_financement": {"annee_n": {}, "annee_n_moins_1": {}},
                    "delais_paiement": {"annee_n": {}, "annee_n_moins_1": {}}
                },
                "chiffres_cles": {
                    "chiffre_affaires_n": "Non disponible",
                    "chiffre_affaires_n_moins_1": "Non disponible",
                    "resultat_exploitation_n": "Non disponible",
                    "resultat_exploitation_n_moins_1": "Non disponible",
                    "marge_exploitation_n": "Non disponible",
                    "marge_exploitation_n_moins_1": "Non disponible",
                    "resultat_net_n": "Non disponible",
                    "resultat_net_n_moins_1": "Non disponible",
                    "capitaux_propres_n": "Non disponible",
                    "capitaux_propres_n_moins_1": "Non disponible",
                    "dette_financiere_n": "Non disponible",
                    "dette_financiere_n_moins_1": "Non disponible"
                },
                "analyse_financiere": f"Erreur lors du parsing de la réponse Claude: {e}"
            }
            response_text = json.dumps(error_response, indent=2, ensure_ascii=False)
        
        total_time = time.time() - start_time
        logger.info(f"Claude completed in {total_time:.2f}s")
        
        return response_text
        
    except Exception as e:
        logger.error(f"Claude API error: {str(e)}")
        return json.dumps({"status": "error", "message": f"Error calling Claude API: {str(e)}"}, indent=2) 