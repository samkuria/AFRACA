# **The Invisible Farmer \- Credit Scoring Engine**

An alternative credit-scoring engine designed to assess the creditworthiness of unbanked Kenyan farmers. This project leverages a **Neo4j Graph Database**, **Python (Flask)**, and the **Open-Meteo API** to calculate risk based on social collateral, production history, transaction velocity, and live environmental data.

## **Features**

* **Graph-Based Risk Assessment:** Uses a Neo4j graph database to model complex relationships between Farmers, Chamas (savings groups), Agricultural Cooperatives, and AgriDealers.  
* **Social & Production Collateral:** Replaces traditional bank history with alternative metrics like Chama guarantorships and Cooperative "check-off" repayment histories.  
* **Live Climate Risk Integration:** Dynamically queries the live Open-Meteo API to adjust credit scores based on real-time soil moisture and drought risks in the farmer's region (e.g., Meru County, Machakos).  
* **Defensive Scoring Algorithm:** A robust Flask API that processes graph algorithms and safely handles missing data fields (using COALESCE and .get()) to return a mathematical credit score out of 100\.

## **Tech Stack**

* **Database:** Neo4j (Graph Database)  
* **Backend Framework:** Python / Flask  
* **External APIs:** Open-Meteo (Live Climate & Soil Data)  
* **Libraries:** neo4j, flask, flask-cors, requests

## **Project Structure**

* databaseSeed.py: A database provisioning script. It clears the local database, creates uniqueness constraints, fetches live environmental data, and seeds the graph with mock farmers, cooperatives, and M-Pesa transaction histories.  
* app.py: The Flask API backend. It connects to Neo4j, runs analytical Cypher queries to evaluate a specific farmer's network, applies the custom credit-scoring algorithm, and serves the data to the frontend via JSON.

## **Setup & Installation**

### **1\. Prerequisites**

* Python 3.x installed  
* Neo4j Desktop installed (or a free Neo4j AuraDB cloud instance)  
* Neo4j Database running locally on port 7687

### **2\. Install Dependencies**

Open your terminal and install the required Python packages:

pip install flask flask-cors neo4j requests

### **3\. Database Configuration**

In both databaseSeed.py and app.py, ensure your Neo4j credentials match your active instance:

NEO4J\_URI \= "bolt://localhost:7687"  
NEO4J\_USER \= "neo4j"  
NEO4J\_PASSWORD \= "YOUR\_ACTUAL\_PASSWORD\_HERE"

*(Note: If using Neo4j Desktop for the first time, you must open http://localhost:7474 in your browser to set your initial password before running the scripts).*

## **Running the Application**

### **Step 1: Seed the Database**

Run the seeding script to populate the graph with farmers and fetch the live Open-Meteo weather data:

python databaseSeed.py

*You should see a success message indicating the data was seeded and relationships were wired up.*

### **Step 2: Start the Flask API**

Run the backend server:

python app.py

*The server will start running on http://localhost:5000.*

## **API Documentation**

### **Get Farmer Credit Score**

Retrieves the complete graph analysis and calculated credit score for a specific farmer.

* **Endpoint:** /api/farmer/\<farmer\_id\>/score  
* **Method:** GET  
* **Available Test IDs:** F-101 (Amina), F-102 (Kiprono), F-103 (David)

**Example Request:**

curl http://localhost:5000/api/farmer/F-101/score

**Example Response:**

{  
  "creditScore": 91.0,  
  "environmentalRisk": {  
    "penaltyScore": 0.6,  
    "status": "Mild Drought"  
  },  
  "farmerId": "F-101",  
  "metrics": {  
    "cooperativeRepaymentScore": 1.0,  
    "guaranteedAmountKES": 50000,  
    "simCardAgeDays": 1200,  
    "totalCashFlowKES": 5500,  
    "transactionCount": 2  
  },  
  "name": "Amina Wanjiku"  
}  
