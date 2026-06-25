import os
from flask import Flask, jsonify
from flask_cors import CORS
from neo4j import GraphDatabase

app = Flask(__name__)
CORS(app)

NEO4J_URI="neo4j://localhost:7687"
NEO4J_USER="neo4j"
NEO4J_PASSWORD="********"

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

def calculate_credit_score(data):
    if not data:
        return 0
    
    # Base Score
    score = 40

    sim_age = data.get('SimAgeDays') or 0
    tx_velocity = data.get('TxVelocity') or 0
    coop_score = data.get('CoopRepaymentScore') or 0
    social_col = data.get('SocialCollateralValue') or 0
    climate_risk = data.get('ClimateRiskPenalty') or 0 

    # Sim Card Age
    if data['SimAgeDays'] > 1000:
        score += 20
    elif data['SimAgeDays'] > 365:
        score += 10

    # Financial Velocity
    if data['TxVelocity'] >2:
        score += 15
    
    # Production Reliability
    score += (data['CoopRepaymentScore']*20)

    # Guarantors
    if data['SocialCollateralValue']>10000:
        score += 20
    elif data['SocialCollateralValue']>0:
        score += 10
    
    # Climate Risk Penalty
    penalty = int(data['ClimateRiskPenalty']*15)
    score -= penalty

    return min(max(score,0),100)

@app.route('/api/farmer/<farmer_id>/score', methods = ['GET'])
def get_farmer_score(farmer_id):
    query = """
    MATCH (f:Farmer {id: $farmer_id})
    OPTIONAL MATCH (f)-[:LOCATED_IN]->(reg:Region)-[:EXPOSED_TO]->(risk:EnvironmentalRisk)
    OPTIONAL MATCH (f)<-[rep:REPORTS_REPAYMENT]-(coop:AgriCooperative)
    OPTIONAL MATCH (guarantor:Farmer)-[g:GUARANTEES]->(f)
    OPTIONAL MATCH (f)-[:PERFORMED_TX]->(tx:MpesaTransaction)
    
    WITH f, reg, risk, rep, 
         sum(g.amountGuaranteedKES) AS TotalGuaranteedAmount,
         count(tx) AS TotalTransactions,
         sum(tx.amountKES) AS TotalCashFlowKES
         
    RETURN 
        f.name AS Applicant,
        COALESCE(f.mobileMoneySimCardAgeDays, f.simAge, 0) AS SimAgeDays,
        COALESCE(TotalTransactions, 0) AS TxVelocity,
        COALESCE(TotalCashFlowKES, 0) AS TotalCashFlow,
        COALESCE(rep.consistency_score, 0.0) AS CoopRepaymentScore,
        COALESCE(TotalGuaranteedAmount, 0) AS SocialCollateralValue,
        COALESCE(risk.intensityScore, 0.5) AS ClimateRiskPenalty,
        risk.type AS LiveClimateStatus
    """
    
    try:
        with driver.session() as session:
            result = session.run(query, farmer_id=farmer_id)
            record = result.single()
            
            if not record:
                return jsonify({"error": "Farmer not found"}), 404
                
            data = dict(record)
            final_score = calculate_credit_score(data)
            
            # Format the payload for the frontend UI
            payload = {
                "farmerId": farmer_id,
                "name": data["Applicant"],
                "creditScore": final_score,
                "metrics": {
                    "simCardAgeDays": data["SimAgeDays"],
                    "transactionCount": data["TxVelocity"],
                    "totalCashFlowKES": data["TotalCashFlow"],
                    "cooperativeRepaymentScore": data["CoopRepaymentScore"],
                    "guaranteedAmountKES": data["SocialCollateralValue"]
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
