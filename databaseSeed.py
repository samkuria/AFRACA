import os
from neo4j import GraphDatabase
from datetime import datetime, timedelta

NEO4J_URL= os.getenv("NEO4J_URL","neo4j://localhost:7687")
NEO4J_USER= os.getenv("NEO4J_USER","neo4j")
NEO4J_PASSWORD= os.getenv("NEO4J_PASSWORD","15SaM373")

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
    def seed_data(self):
        with self.driver.session() as session:
            print("Seeding Environmental Risks in Regions...")

            session.run("""
                         MERGE (r1:Region {id: 'REG-MERU', name: 'Meru County', latitude: 0.0464, longitude: 37.6538})
                         MERGE (r2:Region {id: 'REG-MACH', name: 'Machakos', latitude: -1.5177, longitude: 37.2634})
                
                         MERGE (risk1:EnvironmentalRisk {id: 'RSK-01', type: 'Drought', intensityScore: 0.8, detectedDate: '2026-05-01'})
                         MERGE (r2)-[:EXPOSED_TO{distanceKm: 12.5}]->(risk1)""")
            
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
            session.run("""
                        UNWIND $transaction AS tx
                        MATCH (f:Farmer {id: tx.farmer})
                        MERGE(m:MpesaTransaction{receiptNumber: tx.receipt})
                        SET m.transactionType = tx.type, m.amountKES = tx.amt, m.timestamp = datetime()
                        
                        MERGE (f)-[:PERFORMED_TX]->(m)
                        WITH m, tx
                        CALL apoc.do.case([
                            tx.rel = 'PAID_TO', 'MATCH (tgt:AgriDealer {id: tx.target}) MERGE (m)-[:PAID_TO]->(tgt) RETURN tgt',
                            tx.rel = 'CONTRIBUTED_TO', 'MATCH (tgt:Chama {id: tx.target}) MERGE (m)-[:CONTRIBUTED_TO]->(tgt) RETURN tgt'
                        ], 'RETURN NULL', {m:m, tx:tx}) YIELD value
                        
                        RETURN count(*)""", transaction=transactions)

if __name__=="__main__":
    print("Initializing GraphSeeder...")
    seeder = GraphSeeder(NEO4J_URL, NEO4J_USER, NEO4J_PASSWORD)
    try:
        seeder.prepare_database()
        seeder.seed_data()
        print("Database seeding completed successfully.")
    except Exception as e:
        print(f"An error occurred during database seeding: {e}")
    finally:
        seeder.close()

