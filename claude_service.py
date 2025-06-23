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
        prompt = f"""# PROMPT AGENT 2 - ANALYSE FINANCIÈRE POUR ÉVALUATION LOCATAIRE

## CONTEXTE ET MISSION

Vous êtes un **analyste financier senior** spécialisé dans l'évaluation de solvabilité locative. 

**Votre mission :** Analyser la solidité financière de l'entreprise {company_name} candidate à la location d'un de nos locaux commerciaux à partir des ratios financiers déjà calculés.

**Input reçu :** {gemini_output}

**Output attendu :** Format JSON avec chiffres clés + analyse financière complète.

**Objectif final :** Déterminer la fiabilité de l'entreprise en tant que futur locataire et formuler une recommandation argumentée.

---

## FORMAT DE SORTIE ATTENDU

Votre réponse doit contenir exactement ces deux éléments dans cet ordre :

### **1. CHIFFRES CLÉS (Format JSON)**

```json
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
```

### **2. ANALYSE FINANCIÈRE (800 mots)**

[Analyse complète selon la structure définie ci-dessous]

---

## ANALYSE FINANCIÈRE À PRODUIRE

**Objectif :** Rédiger une analyse complète de **800 mots environ** basée exclusivement sur les ratios fournis.

### **STRUCTURE OBLIGATOIRE DE L'ANALYSE**

1. **Évolution des indicateurs clés**
   - Évolution du chiffre d'affaires (taux de variation)
   - Évolution du résultat net (taux de variation)
   - Évolution des capitaux propres (taux de variation)
   - Tendance générale de l'activité

2. **Structure financière**
   - Solvabilité de l'entreprise (surface financière, ressources propres)
   - Niveau d'endettement (indépendance financière)
   - Équilibre financier (FRNG, BFR, trésorerie nette)
   - Couverture des immobilisations

3. **Rentabilité**
   - Rentabilité économique (performance opérationnelle)
   - Rentabilité financière (retour sur capitaux propres)
   - Rentabilité des ressources stables
   - Évolution des marges (globale, bénéficiaire, brute d'exploitation)

4. **Capacité d'autofinancement et trésorerie**
   - Analyse de la CAF et EBE
   - Capacité à générer du cash
   - Capacité de remboursement
   - Situation de trésorerie

5. **Analyse de l'exploitation**
   - Poids des charges de personnel sur la valeur ajoutée
   - Impact des impôts et taxes sur la valeur ajoutée
   - Charges financières sur la valeur ajoutée
   - Efficacité opérationnelle

6. **Cycle d'exploitation**
   - Délais clients (créances)
   - Délais fournisseurs (dettes)
   - Analyse du besoin en fonds de roulement
   - Gestion du cycle cash

7. **Conclusion argumentée**
   - Synthèse des forces et faiblesses financières
   - Évaluation du niveau de risque locatif (faible/moyen/élevé)
   - Recommandation finale motivée (favorable/réservée/défavorable)
   - Points de vigilance éventuels

---

## CONSIGNES MÉTHODOLOGIQUES

### **À FAIRE**
- Extraire les chiffres clés des ratios fournis pour compléter le JSON
- Utiliser exclusivement les ratios fournis en input pour l'analyse
- Citer des valeurs précises et des pourcentages exacts
- Comparer l'évolution entre les deux exercices
- Adopter un ton professionnel et factuel
- Formuler une recommandation claire et argumentée
- Identifier les tendances (amélioration/dégradation/stabilité)

### **EXTRACTION DES CHIFFRES CLÉS**
- **Chiffre d'affaires :** Utiliser les données de base ou calculer à partir des ratios de variation
- **Résultat d'exploitation :** Extraire des données fournies
- **Marge d'exploitation :** Calculer (Résultat d'exploitation / Chiffre d'affaires) × 100
- **Résultat net :** Extraire des données fournies  
- **Capitaux propres :** Extraire des ratios de structure financière
- **Dette financière :** Extraire des ratios d'endettement ou calculer à partir de l'indépendance financière

### **À ÉVITER**
- Inventer ou extrapoler des données non fournies
- Faire référence à des éléments non présents dans les ratios
- Donner des conseils opérationnels à l'entreprise
- Formuler des hypothèses non fondées sur les ratios

### **ÉVALUATION DU RISQUE LOCATAIRE**

**Critères d'évaluation à considérer :**
- Stabilité et croissance du chiffre d'affaires
- Solidité de la structure financière
- Niveau d'endettement et indépendance financière
- Capacité de génération de trésorerie
- Évolution de la rentabilité
- Gestion du BFR et des délais de paiement

**Niveaux de risque :**
- **Risque faible :** Situation financière saine, recommandation favorable
- **Risque moyen :** Situation mitigée, recommandation avec réserves ou conditions
- **Risque élevé :** Situation préoccupante, recommandation défavorable

### **CLAUSE DE LIMITATION**
Si un ratio n'est pas calculable ou manquant, l'indiquer clairement dans l'analyse. Pour les chiffres clés manquants, utiliser "Non disponible" dans le JSON. Préciser que l'évaluation est basée uniquement sur les ratios financiers disponibles et constitue un avis indicatif qui doit être complété par d'autres éléments d'appréciation (secteur d'activité, historique de paiement, garanties, etc.).

**Ton :** Professionnel, précis, factuel
**Format :** JSON + analyse complète avec phrases courtes, données chiffrées, pourcentages précis
**Conclusion :** Recommandation claire avec niveau de risque explicite

Répondez avec le JSON des chiffres clés suivi de l'analyse financière de 800 mots."""

        logger.info("Starting Claude synthesis...")
        
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,
            temperature=0.1,
            system="Vous êtes un analyste financier senior spécialisé dans l'évaluation de solvabilité locative.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        response_text = message.content[0].text
        total_time = time.time() - start_time
        logger.info(f"Claude completed in {total_time:.2f}s")
        
        # Log Claude output in clean ASCII format
        try:
            claude_output_clean = response_text.encode('ascii', 'replace').decode('ascii')
            logger.info("=== CLAUDE OUTPUT ===")
            logger.info(claude_output_clean)
            logger.info("=== END CLAUDE OUTPUT ===")
        except Exception:
            logger.warning("Could not log Claude output in ASCII format")
        
        return response_text
        
    except Exception as e:
        logger.error(f"Claude API error: {str(e)}")
        return json.dumps({"status": "error", "message": f"Error calling Claude API: {str(e)}"}, indent=2) 