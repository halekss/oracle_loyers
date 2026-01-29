#!/usr/bin/env python3
"""
🧪 SCRIPT DE TEST COMPLET : ML → LLM Pipeline

Ce script teste :
1. La prédiction ML
2. L'injection du contexte dans le prompt
3. La réponse du LLM
4. La cohérence des données

Usage:
    python test_ml_llm_pipeline.py
"""

import requests
import json
import sys
from datetime import datetime

# Configuration
API_BASE_URL = "http://localhost:5000"
COLORS = {
    'GREEN': '\033[92m',
    'RED': '\033[91m',
    'YELLOW': '\033[93m',
    'BLUE': '\033[94m',
    'PURPLE': '\033[95m',
    'END': '\033[0m'
}

def print_color(text, color='GREEN'):
    """Affiche du texte en couleur"""
    print(f"{COLORS.get(color, '')}{text}{COLORS['END']}")

def print_section(title):
    """Affiche une section"""
    print("\n" + "="*70)
    print_color(f"  {title}", 'PURPLE')
    print("="*70 + "\n")

def test_health():
    """Test 1 : Vérifier que le backend est vivant"""
    print_section("TEST 1 : Health Check")
    
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print_color("✅ Backend opérationnel", 'GREEN')
            print(f"   - Modèle ML : {'✅' if data.get('model_loaded') else '❌'}")
            print(f"   - Données IMMO : {data.get('immo_data', 0)} annonces")
            print(f"   - Données POI : {data.get('poi_data', 0)} lieux")
            return True
        else:
            print_color(f"❌ Backend non disponible (code {response.status_code})", 'RED')
            return False
    except Exception as e:
        print_color(f"❌ Erreur connexion : {e}", 'RED')
        print_color("\n💡 Assure-toi que le backend tourne (docker-compose up ou python backend/app.py)", 'YELLOW')
        return False

def test_ml_prediction():
    """Test 2 : Tester une prédiction ML"""
    print_section("TEST 2 : Prédiction ML")
    
    test_cases = [
        {
            "name": "T2 Croix-Rousse",
            "latitude": 45.774,
            "longitude": 4.832,
            "surface": 45
        },
        {
            "name": "Studio Part-Dieu",
            "latitude": 45.760,
            "longitude": 4.859,
            "surface": 25
        },
        {
            "name": "T4 Vaise",
            "latitude": 45.780,
            "longitude": 4.805,
            "surface": 95
        }
    ]
    
    results = []
    
    for test in test_cases:
        print(f"\n📍 Test : {test['name']}")
        print(f"   Localisation : ({test['latitude']}, {test['longitude']})")
        print(f"   Surface : {test['surface']}m²")
        
        try:
            payload = {
                "latitude": test["latitude"],
                "longitude": test["longitude"],
                "surface": test["surface"]
            }
            
            response = requests.post(
                f"{API_BASE_URL}/api/predict",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                pred = data.get('prediction', {})
                loc = data.get('localisation', {})
                market = data.get('contexte_marche', {})
                prox = data.get('proximite', {})
                
                print_color(f"\n   ✅ Prédiction réussie", 'GREEN')
                print(f"      💰 Loyer estimé : {pred.get('loyer_estime')}€")
                print(f"      📐 Prix au m² : {pred.get('prix_m2')}€/m²")
                print(f"      🏠 Type : {pred.get('type_logement')}")
                print(f"      📍 Zone : {loc.get('zone')}, {loc.get('arrondissement')}")
                print(f"      📊 Écart médiane : {market.get('ecart_median')}")
                print(f"      🚇 Métro : {prox.get('metro_proche')} à {prox.get('distance_metro')}")
                
                results.append({
                    'test': test['name'],
                    'success': True,
                    'data': data
                })
            else:
                print_color(f"   ❌ Erreur API (code {response.status_code})", 'RED')
                print(f"   {response.text}")
                results.append({'test': test['name'], 'success': False})
        
        except Exception as e:
            print_color(f"   ❌ Erreur : {e}", 'RED')
            results.append({'test': test['name'], 'success': False})
    
    success_count = sum(1 for r in results if r['success'])
    print_color(f"\n📊 Résultat : {success_count}/{len(test_cases)} tests réussis", 
                'GREEN' if success_count == len(test_cases) else 'YELLOW')
    
    return results

def test_llm_without_context():
    """Test 3 : Tester le LLM sans contexte ML"""
    print_section("TEST 3 : LLM sans contexte (doit refuser poliment)")
    
    try:
        payload = {
            "message": "C'est cher ?",
            "ml_context": None
        }
        
        response = requests.post(
            f"{API_BASE_URL}/api/chat",
            json=payload,
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            llm_response = data.get('response', '')
            
            print_color("✅ LLM a répondu", 'GREEN')
            print(f"\n{'-'*70}")
            print_color(llm_response, 'BLUE')
            print(f"{'-'*70}\n")
            
            # Vérifier que le LLM refuse correctement
            if "scan" in llm_response.lower() or "lance" in llm_response.lower():
                print_color("✅ Le LLM refuse correctement (demande un scan)", 'GREEN')
                return True
            else:
                print_color("⚠️ Le LLM n'a pas refusé comme prévu", 'YELLOW')
                return False
        else:
            print_color(f"❌ Erreur API (code {response.status_code})", 'RED')
            print(response.text)
            return False
    
    except Exception as e:
        print_color(f"❌ Erreur : {e}", 'RED')
        if "1234" in str(e) or "Connection" in str(e):
            print_color("\n💡 LM Studio n'est pas accessible. Vérifie :", 'YELLOW')
            print("   1. LM Studio est lancé")
            print("   2. Un modèle est chargé")
            print("   3. Le serveur écoute sur http://localhost:1234")
        return False

def test_llm_with_context(ml_results):
    """Test 4 : Tester le LLM avec contexte ML"""
    print_section("TEST 4 : LLM avec contexte ML")
    
    if not ml_results or not any(r['success'] for r in ml_results):
        print_color("⚠️ Aucune prédiction ML réussie, test ignoré", 'YELLOW')
        return False
    
    # Prendre la première prédiction réussie
    ml_data = next(r['data'] for r in ml_results if r['success'])
    details = ml_data.get('details', {})
    
    questions = [
        {
            "q": "c'est cher ?",
            "expect": ["cher", "prix", "médiane", "€"]
        },
        {
            "q": "analyse",
            "expect": ["loyer", "zone", "métro", "facteur"]
        },
        {
            "q": "pourquoi ce prix ?",
            "expect": ["surface", "proximité", "impact"]
        }
    ]
    
    results = []
    
    for test in questions:
        print(f"\n❓ Question : \"{test['q']}\"")
        
        try:
            payload = {
                "message": test['q'],
                "ml_context": details
            }
            
            response = requests.post(
                f"{API_BASE_URL}/api/chat",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                llm_response = data.get('response', '')
                
                print_color("\n✅ Réponse reçue", 'GREEN')
                print(f"\n{'-'*70}")
                print_color(llm_response, 'BLUE')
                print(f"{'-'*70}\n")
                
                # Vérifier la qualité de la réponse
                keywords_found = [kw for kw in test['expect'] if kw.lower() in llm_response.lower()]
                
                if len(keywords_found) >= 2:
                    print_color(f"✅ Réponse pertinente (mots-clés : {', '.join(keywords_found)})", 'GREEN')
                    results.append(True)
                else:
                    print_color(f"⚠️ Réponse peu pertinente (seulement : {', '.join(keywords_found)})", 'YELLOW')
                    results.append(False)
            else:
                print_color(f"❌ Erreur API (code {response.status_code})", 'RED')
                results.append(False)
        
        except Exception as e:
            print_color(f"❌ Erreur : {e}", 'RED')
            results.append(False)
    
    success_rate = (sum(results) / len(results)) * 100
    print_color(f"\n📊 Taux de réussite : {success_rate:.0f}%", 
                'GREEN' if success_rate >= 70 else 'YELLOW')
    
    return success_rate >= 70

def main():
    """Fonction principale"""
    print("\n" + "="*70)
    print_color("  🧪 TEST SUITE : ML → LLM Pipeline", 'PURPLE')
    print_color(f"  Timestamp : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 'PURPLE')
    print("="*70)
    
    # Test 1 : Health Check
    if not test_health():
        print_color("\n❌ ÉCHEC : Backend non disponible", 'RED')
        sys.exit(1)
    
    # Test 2 : Prédictions ML
    ml_results = test_ml_prediction()
    
    # Test 3 : LLM sans contexte
    test_llm_without_context()
    
    # Test 4 : LLM avec contexte
    test_llm_with_context(ml_results)
    
    # Résumé final
    print_section("RÉSUMÉ FINAL")
    print_color("✅ Tests terminés", 'GREEN')
    print("\n💡 Si des tests ont échoué :")
    print("   1. Vérifie que LM Studio est lancé (port 1234)")
    print("   2. Vérifie que le modèle ML est entraîné (models/price_predictor.pkl)")
    print("   3. Vérifie les logs du backend pour plus de détails")
    print("\n")

if __name__ == '__main__':
    main()