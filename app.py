import os
from flask import Flask, jsonify
from flask_cors import CORS
from neo4j import GraphDatabase

app = Flask(__name__)
CORS(app)

NEO4J_URI="neo4j://localhost:7687"
NEO4J_USER="neo4j"
NEO4J_PASSWORD="15SaM373"

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

def calculate_credit_score(data):
    if not data:
        return 0
    
    # Base Score
    score = 30

    trust_pagerank = data.get('CommunityTrustScore') or 0.0
    economic_footprint = data.get('EconomicFootprint') or 0.0
    similar_peers = data.get('SimilarPeersCount') or 0
    climate_risk = data.get('ClimateRiskPenalty') or 0.0
    sim_age = data.get('SimAgeDays') or 0 

    # Replaces traditional CRB history.
    if trust_pagerank >= 0.5: 
        score += 25
    elif trust_pagerank >= 0.15: 
        score += 15

    # Replaces traditional bank statements.
    if economic_footprint >= 2.0: 
        score += 20
    elif economic_footprint > 0: 
        score += 10
    
    # Predictive modeling for thin-file youth farmers.
    if similar_peers >= 2: 
        score += 15
    elif similar_peers == 1: 
        score += 10

    # 4. Identity Stability (Sim Age) - Up to 10 points
    if sim_age > 1000: 
        score += 10
    
    # 5. Live Climate Risk Penalty - Subtract up to 15 points
    # Systemic risk protection using Open-Meteo data.
    penalty = int(climate_risk * 15)
    score -= penalty

    return min(max(score,0),100)

@app.route('/api/farmer/<farmer_id>/score', methods=['GET'])
def get_farmer_score(farmer_id):
    query = """
    // 1. Match the Farmer
    MATCH (f:Farmer {id: $farmer_id})
    
    // 2. Get Live Climate Risk
    OPTIONAL MATCH (f)-[:LOCATED_IN]->(reg:Region)-[:EXPOSED_TO]->(risk:EnvironmentalRisk)
    
    // 3. Count Look-alike peers from Node Similarity
    OPTIONAL MATCH (f)-[sim:SIMILAR_TO]->(peer:Farmer)
    
    // 4. Return traditional properties combined with GDS AI properties
    RETURN 
        f.name AS Applicant,
        COALESCE(f.mobileMoneySimCardAgeDays, f.simAge, 0) AS SimAgeDays,
        COALESCE(f.trust_pagerank, 0.0) AS CommunityTrustScore,
        COALESCE(f.economic_footprint, 0.0) AS EconomicFootprint,
        COALESCE(f.community_id, -1) AS LouvainCommunityId,
        count(sim) AS SimilarPeersCount,
        COALESCE(risk.intensityScore, 0.0) AS ClimateRiskPenalty,
        COALESCE(risk.type, 'Unknown') AS LiveClimateStatus
    """
    
    try:
        with driver.session() as session:
            result = session.run(query, farmer_id=farmer_id)
            record = result.single()
            
            if not record:
                return jsonify({"error": f"Farmer {farmer_id} not found"}), 404
                
            data = dict(record)
            final_score = calculate_credit_score(data)
            
            # Construct the final JSON payload for the frontend
            payload = {
                "farmerId": farmer_id,
                "name": data["Applicant"],
                "creditScore": final_score,
                "aiMetrics": {
                    "pageRankTrustScore": round(data["CommunityTrustScore"], 3),
                    "degreeCentralityFootprint": data["EconomicFootprint"],
                    "louvainRiskCommunityId": data["LouvainCommunityId"],
                    "knnSimilarEstablishedPeers": data["SimilarPeersCount"]
                },
                "traditionalMetrics": {
                    "simCardAgeDays": data["SimAgeDays"]
                },
                "environmentalRisk": {
                    "status": data["LiveClimateStatus"],
                    "penaltyScore": data["ClimateRiskPenalty"]
                }
            }
            
            return jsonify(payload), 200
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
if __name__ == '__main__':
    print("Starting The Invisible Farmer API on http://localhost:5000")
    app.run(debug=True, port=5000)
