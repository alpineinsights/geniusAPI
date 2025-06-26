import time
import json
from anthropic import Anthropic
from logger import logger


def query_claude_for_ratios(client: Anthropic, gemini_output: str, company_name: str, annual_rent: str) -> str:
    """Query Claude 4 for financial ratio calculation from Gemini extracted data"""
    try:
        start_time = time.time()
        
        if not client:
            logger.error("Claude client not initialized")
            return "Error: Claude client not initialized"
        
        prompt = f"""CONTEXTE ET MISSION 

Vous êtes un analyste financier spécialisé dans le calcul de ratios comptables. Votre mission : Calculer tous les ratios financiers requis à partir des données financières fournies (sur les deux derniers exercices) et les retourner au format JSON structuré. 

IMPORTANT : Vous êtes uniquement responsable du calcul des ratios. Aucune analyse n'est demandée. 

INPUT ATTENDU 

Nom de l'entreprise : {company_name} 

Loyer payé par l'entreprise : {annual_rent} 

Données financières : {gemini_output} (Bilan comptable actif/passif et compte de résultat détaillé sur les deux derniers exercices) 

RATIOS À CALCULER 

IMPORTANT : Calculez UNIQUEMENT les ratios listés ci-dessous, pour les deux exercices disponibles en précisant l'année sauf pour ressources propres et ressources stables (seulement 2024). N'ajoutez aucun ratio supplémentaire. 

TABLEAU COMPLET DES FORMULES FINANCIÈRES 

STRUCTURE FINANCIÈRE 

Ratio 

Formule 

Ressources propres 

Capitaux propres + Amortissements cumulés + Emprunts et dettes auprès des établissements de crédit + Emprunts et dettes financières divers 

Ressources stables 

Capitaux propres + Amortissements cumulés 

Capital d'exploitation 

Total de l'actif circulant – Total du passif circulant (=avances et accomptes reçus sur commandes en cours +dettes fournisseurs et comptes rattachés + dettes fiscales et sociales + dettes sur immobilisations et comptes rattachés + autres dettes) 

Actif circulant d'exploitation 

Matières premières et marchandises + Avances et acomptes versés sur commandes + Clients et comptes rattachés + Autres créances + Charges constatées d'avance 

Actif circulant hors exploitation 

Capital souscrit appelé, non versé 

Dettes d'exploitation 

Avances et acomptes reçus sur commandes en cours + Dettes fournisseurs et comptes rattachés + Dettes fiscales et sociales 

Dettes hors exploitation 

Dettes sur immobilisations et comptes rattachés + autres dettes 

Surface financière (%) 

Capitaux propres / Total du passif 

Couverture des immobilisations par les fonds propres (%) 

Total brut des immobilisations / (Capitaux propres + Emprunts et dettes auprès des établissements de crédit + Emprunts et dettes financières divers) 

Couverture des emplois stables (%) 

(Capitaux propres + Emprunts et dettes auprès des établissements de crédit + Emprunts et dettes financières divers) / Total brut des immobilisations 

FRNG (Fonds de roulement net global) 

Capitaux propres + Emprunts et dettes auprès des établissements de crédit + Emprunts et dettes financières divers – Total brut des immobilisations 

BFR (Besoin en fonds de roulement) 

(Matières premières et marchandises + Avances et acomptes versés sur commandes + Clients et comptes rattachés + Autres créances + Charges constatées d'avance) + (Capital souscrit appelé, non versé) – (Avances et acomptes reçus sur commandes en cours + Dettes fournisseurs et comptes rattachés + Dettes fiscales et sociales) - (Dettes sur immobilisations et comptes rattachés + autres dettes) 

Trésorerie nette 

(Capitaux propres + Emprunts et dettes auprès des établissements de crédit + Emprunts et dettes financières divers – Total brut des immobilisations) – ((Matières premières et marchandises + Avances et acomptes versés sur commandes + Clients et comptes rattachés + Autres créances + Charges constatées d'avance) + (Capital souscrit appelé, non versé) – (Avances et acomptes reçus sur commandes en cours + Dettes fournisseurs et comptes rattachés + Dettes fiscales et sociales) - (Dettes sur immobilisations et comptes rattachés + autres dettes)) 

Indépendance financière (%) 

(Emprunts et dettes auprès des établissements de crédit + Emprunts et dettes financières divers ) / Capitaux propres 

Liquidité de l'entreprise (%) 

(Créances clients et comptes rattachés + disponibilités) /dettes fournisseurs et comptes rattachés 

ACTIVITÉ D'EXPLOITATION 

Ratio 

Formule 

Marge globale 

Chiffre d'affaires net – Achats de marchandises – Achats de matières premières et autres approvisionnements - variation de stocks (marchandises et matières premières) 

Valeur ajoutée 

Chiffre d'affaires net – Achats de marchandises – Achats de matières premières et autres approvisionnements - variation de stocks (marchandises et matières premières) + Production stockée + Production immobilisée – Autres achats et charges externes 

EBE (excédent brut d'exploitation) 

Chiffre d'affaires net – Achats de marchandises – Achats de matières premières et autres approvisionnements - variation de stocks (marchandises et matières premières) + Production stockée + Production immobilisée – Autres achats et charges externes + Subventions d'exploitation – Impôts, taxes et versements assimilés – Salaires et traitements – Charges sociales 

CAF (capacité d'auto financement) 

Chiffre d'affaires net – Achats de marchandises – Achats de matières premières et autres approvisionnements - variation de stocks (marchandises et matières premières) + Production stockée + Production immobilisée – Autres achats et charges externes + Subventions d'exploitation – Impôts, taxes et versements assimilés – Salaires et traitements – Charges sociales + total des produits financiers + total des produits exceptionnels – total des charges financières – total des charges exceptionnelles 

Charges de personnel / Valeur ajoutée (%) 

(Salaires et traitements + Charges sociales) / (Chiffre d'affaires net – Achats de marchandises – Achats de matières premières et autres approvisionnements - variation de stocks (marchandises et matières premières) + Production stockée + Production immobilisée – Autres achats et charges externes) 

Impôts / Valeur ajoutée (%) 

Impôts, taxes et versements assimilés / (Chiffre d'affaires net – Achats de marchandises – Achats de matières premières et autres approvisionnements - variation de stocks (marchandises et matières premières) + Production stockée + Production immobilisée – Autres achats et charges externes) 

Charges financières / Valeur ajoutée (%) 

Charges financières / (Chiffre d'affaires net – Achats de marchandises – Achats de matières premières et autres approvisionnements - variation de stocks (marchandises et matières premières) + Production stockée + Production immobilisée – Autres achats et charges externes) 

Taux de marge globale (%) 

Marge globale / (Ventes de marchandises + Production vendue de biens + production vendue de services) 

Taux de valeur ajoutée (%) 

(Chiffre d'affaires net – Achats de marchandises – Achats de matières premières et autres approvisionnements - variation de stocks (marchandises et matières premières) + Production stockée + Production immobilisée – Autres achats et charges externes) / Chiffre d'affaires net 

Taux de marge bénéficiaire (%) 

Résultat net comptable / Chiffre d'affaires net 

Taux de marge brute d'exploitation (%) 

(Chiffre d'affaires net – Achats de marchandises – Achats de matières premières et autres approvisionnements - variation de stocks (marchandises et matières premières) + Production stockée + Production immobilisée – Autres achats et charges externes + Subventions d'exploitation – Impôts, taxes et versements assimilés – Salaires et traitements – Charges sociales) / Chiffre d'affaires net 

Taux d'obsolescence (%) 

Dotations d'exploitation / Total des actifs immobilisés (Total II) 

RENTABILITÉ 

Ratio 

Formule 

Rentabilité des capitaux propres (%) 

Résultat net comptable / Capitaux propres 

Rentabilité économique (%) 

(Résultat net comptable + total des charges financières) / (Capitaux propres + Emprunts et dettes auprès des établissements de crédit + Emprunts et dettes financières divers) 

Rentabilité financière (%) 

Résultat net comptable / (Capitaux propres + Emprunts et dettes auprès des établissements de crédit + Emprunts et dettes financières divers) 

Rentabilité brute des ressources stables (%) 

(Chiffre d'affaires net – Achats de marchandises – Achats de matières premières et autres approvisionnements - variation de stocks (marchandises et matières premières) + Production stockée + Production immobilisée – Autres achats et charges externes + Subventions d'exploitation – Impôts, taxes et versements assimilés – Salaires et traitements – Charges sociales) / (Capitaux propres + Emprunts et dettes auprès des établissements de crédit + Emprunts et dettes financières divers) 

Rentabilité brute du capital d'exploitation (%) 

(Chiffre d'affaires net – Achats de marchandises – Achats de matières premières et autres approvisionnements - variation de stocks (marchandises et matières premières) + Production stockée + Production immobilisée – Autres achats et charges externes + Subventions d'exploitation – Impôts, taxes et versements assimilés – Salaires et traitements – Charges sociales) / (Total de l'actif circulant – Total du passif circulant) 

ÉVOLUTION 

Ratio 

Formule 

Taux de variation du chiffre d'affaires (%) 

(Chiffre d'affaires net N+1 – Chiffre d'affaires net N) / Chiffre d'affaires net N 

Taux de variation de la valeur ajoutée (%) 

(Valeur ajoutée N+1 – Valeur ajoutée N) / Valeur ajoutée N 

Taux de variation du résultat (%) 

(Résultat net comptable N+1 – Résultat net comptable N) / Résultat net comptable N 

Taux de variation des capitaux propres (%) 

(Capitaux propres N+1 – Capitaux propres N) / Capitaux propres N 

TRÉSORERIE & FINANCEMENT 

Ratio 

Formule 

Capacité à générer du cash 

Chiffre d'affaires net – Achats de marchandises – Achats de matières premières et autres approvisionnements - variation de stocks (marchandises et matières premières) + Production stockée + Production immobilisée – Autres achats et charges externes + Subventions d'exploitation – Impôts, taxes et versements assimilés – Salaires et traitements – Charges sociales + Produits financiers + Produits exceptionnels – Charges financières– Charges exceptionnelles 

Capacité de remboursement de la dette 

(Emprunts et dettes auprès des établissements de crédit + Emprunts et dettes financières divers) / (Chiffre d'affaires net – Achats de marchandises – Achats de matières premières et autres approvisionnements - variation de stocks (marchandises et matières premières) + Production stockée + Production immobilisée – Autres achats et charges externes + Subventions d'exploitation – Impôts, taxes et versements assimilés – Salaires et traitements – Charges sociales + Produits financiers + Produits exceptionnels – Charges financières– Charges exceptionnelles) 

Crédits bancaires courants / BFR 

(Emprunts et dettes auprès des établissements de crédit + Emprunts et dettes financières divers) / ((Matières premières et marchandises + Avances et acomptes versés sur commandes + Clients et comptes rattachés + Autres créances + Charges constatées d'avance) + (Capital souscrit appelé, non versé) – (Avances et acomptes reçus sur commandes en cours + Dettes fournisseurs et comptes rattachés + Dettes fiscales et sociales) - (Dettes sur immobilisations et comptes rattachés + autres dettes)) 

DÉLAIS DE PAIEMENT 

Ratio 

Formule 

Délai créance clients (en jours) 

(Clients et comptes rattachés / Chiffre d'affaires net) × 360 

Délai dettes fournisseurs (en jours) 

(Dettes fournisseurs et comptes rattachés / (Achats de marchandises + Autres achats et charges externes)) × 360 

 

CONSIGNES DE CALCUL 

À FAIRE UNIQUEMENT 

Extraire les données des états financiers fournis 

Calculer tous les ratios pour les deux exercices disponibles 

Arrondir à 2 décimales pour les pourcentages et nombres décimaux 

Indiquer "Non calculable" si une donnée manque pour un ratio 

EN CAS DE DONNÉES MANQUANTES 

Si un élément comptable n'apparaît pas dans les états financiers, indiquer uniquement "Donnée non disponible" et marquer le ratio comme "Non calculable". 

NOTES IMPORTANTES 

Si certains éléments des formules ne sont pas exactement les mêmes, prenez les éléments dont le sens et les mots se rapprochent le plus 

Si un ratio n'apparaît pas dans vos calculs, vous DEVEZ l'ajouter avec une valeur ou "Non calculable" 

Comptez : Structure Financière (15 ratios) + Activité d'Exploitation (12 ratios) + Rentabilité (5 ratios) + Évolution (4 ratios) + Trésorerie & Financement (3 ratios) + Délais de Paiement (2 ratios) = 41 ratios MINIMUM"""

        logger.info("Starting Claude ratio calculation...")
        
        # Debug the API call parameters
        logger.info(f"Making Claude API call with model: claude-sonnet-4-20250514")
        logger.info(f"Max tokens: 4096, Temperature: 0.1")
        logger.info(f"Prompt length: {len(prompt)} characters")
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            temperature=0.1,
            messages=[
                {
                    "role": "user", 
                    "content": prompt
                }
            ]
        )
        
        logger.info(f"Claude API call completed. Response object type: {type(response)}")
        
        total_time = time.time() - start_time
        logger.info(f"Claude ratio calculation completed in {total_time:.2f}s")
        
        if not response or not response.content:
            logger.error("Claude returned empty response")
            return "Error: Received an empty response from Claude."
        
        response_text = response.content[0].text if response.content else ""
        
        # Debug the response object structure
        logger.info(f"Claude response object: content length = {len(response.content) if response.content else 0}")
        if response.content:
            logger.info(f"First content item type: {type(response.content[0])}")
            logger.info(f"First content text length: {len(response.content[0].text) if hasattr(response.content[0], 'text') else 'No text attribute'}")
        
        # Validate JSON structure
        try:
            parsed_json = json.loads(response_text)
            logger.info("Claude returned valid JSON for ratio calculations")
        except json.JSONDecodeError as e:
            logger.error(f"Claude returned invalid JSON: {e}")
            logger.error(f"Response text length: {len(response_text)}")
            logger.error(f"Response text (first 200 chars): '{response_text[:200]}'")
            logger.debug(f"Raw Claude response (first 1000 chars): {response_text[:1000]}")
            
            # Try to extract JSON from the response if it's wrapped in text
            text = response_text.strip()
            
            if not text:
                logger.error("Claude returned completely empty response")
                return "Error: Claude returned empty response for ratio calculation"
            
            # Look for JSON object patterns
            start_idx = text.find('{')
            end_idx = text.rfind('}')
            
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                try:
                    json_part = text[start_idx:end_idx + 1]
                    parsed_json = json.loads(json_part)
                    logger.info("Successfully extracted JSON from Claude response")
                    return json.dumps(parsed_json, ensure_ascii=False)
                except json.JSONDecodeError as extract_error:
                    logger.error(f"Could not extract valid JSON from Claude response: {extract_error}")
                    logger.error(f"Attempted to parse: '{json_part[:200]}'")
            else:
                logger.error("No JSON object pattern found in Claude response")
            
            return f"Error: Claude returned malformed JSON: {str(e)}"
        
        return response_text

    except Exception as e:
        logger.error(f"Claude ratio calculation failed: {str(e)}", exc_info=True)
        return f"An error occurred during the Claude ratio calculation process: {str(e)}" 