#!/usr/bin/env python3
"""
Script unificado para criar TODAS as tabelas necessárias no banco PROAtivo.
Substitui: create_feedback_table.py, create_missing_tables.py, create_upload_status_table.py
"""

import asyncio
import sys
import os
from pathlib import Path
from sqlalchemy import text

# Configurar paths
current_dir = Path(__file__).parent
project_dir = current_dir.parent.parent
sys.path.insert(0, str(project_dir))
os.environ['PYTHONPATH'] = str(project_dir)

from src.database.connection import db_connection, init_database
from src.database.models import Base


async def create_all_tables():
    """Cria todas as tabelas necessárias usando SQLAlchemy models."""
    print("🔧 Criando tabelas principais via SQLAlchemy...")
    
    await init_database()
    
    async with db_connection.engine.begin() as conn:
        # Cria todas as tabelas definidas nos models
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)
    
    print("✅ Tabelas principais criadas")


async def create_additional_tables():
    """Cria tabelas adicionais não cobertas pelos models."""
    print("🔧 Verificando tabelas adicionais...")
    
    # Nota: A tabela 'failures' agora é criada via SQLAlchemy models
    # Esta função é mantida para futuras extensões, mas não executa nada por enquanto
    
    print("✅ Nenhuma tabela adicional necessária - todas criadas via SQLAlchemy")


async def verify_tables():
    """Verifica se todas as tabelas essenciais foram criadas."""
    print("🔍 Verificando tabelas criadas...")
    
    check_sql = """
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
    ORDER BY table_name
    """
    
    async with db_connection.get_session() as session:
        result = await session.execute(text(check_sql))
        tables = [row[0] for row in result.fetchall()]
    
    essential_tables = [
        'equipments', 'maintenances', 'failures', 
        'user_feedback', 'upload_status'
    ]
    
    print(f"📊 {len(tables)} tabelas encontradas:")
    for table in sorted(tables):
        status = "✅" if table in essential_tables else "📄"
        print(f"   {status} {table}")
    
    missing = [t for t in essential_tables if t not in tables]
    if missing:
        print(f"⚠️  Tabelas essenciais ausentes: {missing}")
        return False
    
    print("✅ Todas as tabelas essenciais estão presentes")
    return True


async def main():
    """Função principal - cria todas as tabelas."""
    print("🚀 CRIAÇÃO UNIFICADA DE TABELAS")
    print("================================")
    
    try:
        # Etapa 1: Tabelas principais
        await create_all_tables()
        
        # Etapa 2: Tabelas adicionais
        await create_additional_tables()
        
        # Etapa 3: Verificação
        success = await verify_tables()
        
        if success:
            print("\n🎉 TODAS AS TABELAS CRIADAS COM SUCESSO!")
            return True
        else:
            print("\n❌ ALGUMAS TABELAS FALTANDO")
            return False
            
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 