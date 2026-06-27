import os
import requests
from neo4j import GraphDatabase
from datetime import datetime, timedelta

NEO4J_URL= os.getenv("NEO4J_URL","neo4j://localhost:7687")
NEO4J_USER= os.getenv("NEO4J_USER","neo4j")
NEO4J_PASSWORD= os.getenv("NEO4J_PASSWORD","******")

class GraphSeeder:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    def close(self):
        self.driver.close()

    def prepare_database(self):
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")

            constraints = [
                "CREATE CONSTRAINT IF NOT EXISTS FOR (f:Farmer) REQUIRE f.id IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Chama) REQUIRE c.id IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (a:AgriCooperative) REQUIRE a.id IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (d:AgriDealer) REQUIRE d.id IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (m:MPesaTransaction) REQUIRE m.receiptNumber IS UNIQUE"
            ]
            for query in constraints:
                session.run(query)
                
    def fetch_live_climate_risk(self, lat, lon):
        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=soil_moisture_0_to_7cm,precipitation"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            soil_moisture = data.get("current", {}).get("soil_moisture_0_to_7cm", 0.5)
            
            if soil_moisture < 0.20:
                return {"type": "Severe Drought", "score": 0.9}
            elif soil_moisture < 0.35:
                return {"type": "Mild Drought", "score": 0.6}
            else:
                return {"type": "Optimal Condition", "score": 0.1}
                
        except Exception as e:
            print(f"Open-Meteo API Error: {e}. Defaulting to mock data.")
            return {"type": "Unknown", "score": 0.5}
    def seed_data(self):
        with self.driver.session() as session:
            print("Seeding Environmental Risks in Regions...")

            regions = [
                {"id": "REG-MERU", "name": "Meru County", "lat": 0.0464, "lon": 37.6538},
                {"id": "REG-MACH", "name": "Machakos", "lat": -1.5177, "lon": 37.2634}
            ]
            
            for r in regions:
                session.run("""
                    MERGE (reg:Region {id: $id})
                    SET reg.name = $name, reg.latitude = $lat, reg.longitude = $lon
                """, id=r["id"], name=r["name"], lat=r["lat"], lon=r["lon"])
                
                print(f"Fetching live climate data from Open-Meteo for {r['name']}...")
                live_risk = self.fetch_live_climate_risk(r["lat"], r["lon"])
                
                session.run("""
                    MATCH (reg:Region {id: $id})
                    MERGE (risk:EnvironmentalRisk {id: 'RSK-' + $id})
                    SET risk.type = $type, risk.intensityScore = $score, risk.detectedDate = date()
                    MERGE (reg)-[:EXPOSED_TO {distanceKm: 0.0}]->(risk)
                """, id=r["id"], type=live_risk["type"], score=live_risk["score"])
            
            print("Seeding Chamas, Cooperatives and Agridealers...")
            session.run("""
                        MERGE (c1:Chama {id: 'CHM-01', name: 'Bidii Women Table Banking', totalMembers: 25, monthlyContributionKES: 1000})
                        MERGE (coop1:AgriCooperative {id: 'COOP-DAIRY', name: 'Meru Dairy Cooperative', commodityType: 'Dairy', networkStrengthScore: 92.5})
                        MERGE (buyer1:MajorBuyer {id: 'BUY-01', name: 'Brookside Dairies'})
                        MERGE (dealer1:AgriDealer {id: 'DLR-01', businessName: 'Mavuno Fertilizer & Seeds', specialty: 'Fertilizer & Seeds', isRegistered: true})
                        
                        MERGE (coop1)-[:PARTNERED_WITH]->(buyer1)""")
            
            print("Seeding farmers...")
            farmers = [
                {"id": "F-101", "name": "Amina Wanjiku", "gender": "Female", "age": 24, "disabilityStatus": False, "simAge": 1200}, # Our target demo: Youth/Female
                {"id": "F-102", "name": "Kiprono Bett", "gender": "Male", "age": 45, "disabilityStatus": False, "simAge": 3500},    # Established Farmer
                {"id": "F-103", "name": "David Mutisya", "gender": "Male", "age": 32, "disabilityStatus": True, "simAge": 2100}     # PWD Farmer
            ]
            session.run("""
                        UNWIND $farmers AS f
                        MERGE (n:Farmer {id:f.id})
                        SET n.name = f.name, n.gender = f.gender, n.age = f.age, n.disabilityStatus = f.disabilityStatus, n.simAge = f.simAge
                        """, farmers=farmers)
            
            print("Wiring up the Trust Network (Relationships)...")
            session.run("""
                MATCH (amina:Farmer {id: 'F-101'})
                MATCH (kiprono:Farmer {id: 'F-102'})
                MATCH (david:Farmer {id: 'F-103'})
                
                MATCH (meru:Region {id: 'REG-MERU'})
                MATCH (machakos:Region {id: 'REG-MACH'})
                MATCH (chama:Chama {id: 'CHM-01'})
                MATCH (coop:AgriCooperative {id: 'COOP-DAIRY'})

                // Locations
                MERGE (amina)-[:LOCATED_IN]->(meru)
                MERGE (kiprono)-[:LOCATED_IN]->(meru)
                MERGE (david)-[:LOCATED_IN]->(machakos)

                // Social Collateral: Chama Memberships & Guarantorship
                MERGE (amina)-[:MEMBER_OF]->(chama)
                MERGE (kiprono)-[:MEMBER_OF]->(chama)
                
                // Kiprono (Established) Guarantees Amina (Youth) - Massive trust signal!
                MERGE (kiprono)-[:GUARANTEES {amountGuaranteedKES: 50000, status: 'Active'}]->(amina)

                // Production Collateral: Co-op Deliveries & Check-off History
                MERGE (amina)-[:DELIVERS_TO {frequency: 'Daily'}]->(coop)
                // The Cooperative vouches for Amina's check-off repayment history
                MERGE (coop)-[:REPORTS_REPAYMENT {total_advances: 4, defaulted_advances: 0, consistency_score: 1.0}]->(amina)
            """)

            print("Simulating M-Pesa Transaction Trails...")
            transactions = [
                # Amina buys fertilizer from the dealer
                {"receipt": "QA79LK2PR", "type": "BuyGoods", "amt": 4500, "farmer": "F-101", "target": "DLR-01", "rel": "PAID_TO"},
                # Amina makes her monthly Chama contribution
                {"receipt": "QB21MZ9XQ", "type": "PayBill", "amt": 1000, "farmer": "F-101", "target": "CHM-01", "rel": "CONTRIBUTED_TO"}
            ]
            for tx in transactions:
                if tx["rel"] == 'PAID_TO':
                    session.run("""
                        MATCH (f:Farmer {id: $farmer})
                        MATCH (tgt:AgriDealer {id: $target})
                        MERGE (m:MpesaTransaction {receiptNumber: $receipt})
                        SET m.transactionType = $type, m.amountKES = $amt, m.timestamp = datetime()
                        MERGE (f)-[:PERFORMED_TX]->(m)
                        MERGE (m)-[:PAID_TO]->(tgt)
                    """, farmer=tx["farmer"], target=tx["target"], receipt=tx["receipt"], type=tx["type"], amt=tx["amt"])
                elif tx["rel"] == 'CONTRIBUTED_TO':
                    session.run("""
                        MATCH (f:Farmer {id: $farmer})
                        MATCH (tgt:Chama {id: $target})
                        MERGE (m:MpesaTransaction {receiptNumber: $receipt})
                        SET m.transactionType = $type, m.amountKES = $amt, m.timestamp = datetime()
                        MERGE (f)-[:PERFORMED_TX]->(m)
                        MERGE (m)-[:CONTRIBUTED_TO]->(tgt)
                    """, farmer=tx["farmer"], target=tx["target"], receipt=tx["receipt"], type=tx["type"], amt=tx["amt"])
                    
 def run_gds_algorithms(self):
        with self.driver.session() as session:
            print("Running GDS PageRank for Trust Network...")

            session.run("CALL gds.graph.drop('trustGraph', false)")
            session.run("""
                 CALL gds.graph.project(
                        'trustGraph',
                        'Farmer',
                        'GUARANTEES'
                        )
                    """)
            
            session.run("""
                        CALL gds.pageRank.write('trustGraph', {
    
                            maxIterations: 20,
                            dampingFactor: 0.85,
                            writeProperty: 'trust_pagerank'
                        })""")
            
            session.run("CALL gds.graph.drop('trustGraph')")
            print("Trust scores written to Farmer nodes.")
            #Louvain Algorithm
            print("Running GDS Louvain algorithm for community detection ...")

            session.run("CALL gds.graph.drop('communityGraph', false)")

            session.run("""
                        CALL gds.graph.project(
                            'communityGraph',
                            ['Farmer', 'Chama', 'AgriCooperative'],
                            ['MEMBER_OF', 'DELIVERS_TO']
                        )
                        """)
            
            session.run("""
                        CALL gds.louvain.write('communityGraph',{
                            writeProperty: 'community_id'
                        })""")
            
            session.run("CALL gds.graph.drop('communityGraph')")
            print("Community IDs successfully written to nodes.")
            #Degree Centrality
            print("Running GDS Degree Centrality for economic footprint...")
            session.run("CALL gds.graph.drop('economicGraph', false)")

            session.run("""
                        CALL gds.graph.project(
                            'economicGraph',
                            ['Farmer', 'MPesaTransaction'],
                            ['PERFORMED_TX']
                        )
                        """)
            session.run("""
                        CALL gds.degree.write('economicGraph', {
                            writeProperty: 'economic_footprint'
                        })""")
            
            session.run("CALL gds.graph.drop('economicGraph')")
            print("Economic footprints successfully written to Farmer nodes.")


if __name__=="__main__":
    print("Initializing GraphSeeder...")
    seeder = GraphSeeder(NEO4J_URL, NEO4J_USER, NEO4J_PASSWORD)
    try:
        seeder.prepare_database()
        seeder.seed_data()
        seeder.run_gds_algorithms()
        print("Database seeding completed successfully.")
    except Exception as e:
        print(f"An error occurred during database seeding: {e}")
    finally:
        seeder.close()

