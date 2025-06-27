#!/usr/bin/env python3
"""
Script direto para verificar status do banco
"""

import asyncio
import asyncpg
import os

async def check_database():
    """Verifica status do banco diretamente"""
    
    # Conectar ao banco
    conn = await asyncpg.connect(
        host="localhost",
        port=5432,
        database="proativo_db",
        user="proativo_user",
        password="proativo_pass"
    )
    
    try:
        # Contar equipamentos
        count_equip = await conn.fetchval("SELECT COUNT(*) FROM equipments")
        print(f"✅ Equipamentos: {count_equip}")
        
        # Contar manutenções
        count_maint = await conn.fetchval("SELECT COUNT(*) FROM maintenances")
        print(f"✅ Manutenções: {count_maint}")
        
        # Mostrar alguns equipamentos
        equipments = await conn.fetch("""
            SELECT equipment_code, name, criticality 
            FROM equipments 
            ORDER BY equipment_code 
            LIMIT 10
        """)
        
        print("\n📋 Equipamentos no banco:")
        for eq in equipments:
            print(f"  - {eq['equipment_code']}: {eq['name']} ({eq['criticality']})")
            
        # Mostrar algumas manutenções se existirem
        if count_maint > 0:
            maintenances = await conn.fetch("""
                SELECT m.maintenance_code, m.title, e.equipment_code
                FROM maintenances m
                JOIN equipments e ON m.equipment_id = e.id
                ORDER BY m.maintenance_code
                LIMIT 10
            """)
            
            print("\n🔧 Manutenções no banco:")
            for maint in maintenances:
                print(f"  - {maint['maintenance_code']}: {maint['title']} (Equip: {maint['equipment_code']})")
    
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(check_database()) 