"""
Repositories para acesso aos dados usando padrão Repository.

Implementa a camada de abstração entre os modelos SQLAlchemy e a lógica de negócio,
fornecendo operações CRUD e consultas específicas do domínio.
"""

import logging
from typing import List, Optional, Dict, Any, Sequence
from datetime import datetime, date, timedelta
from decimal import Decimal

from sqlalchemy import select, update, delete, func, and_, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError, NoResultFound

from .models import Equipment, Maintenance, Failure, UserFeedback, UploadStatus

logger = logging.getLogger(__name__)


class BaseRepository:
    """Classe base para repositories com operações CRUD comuns."""
    
    def __init__(self, session: AsyncSession, model_class):
        """Inicializa o repository.
        
        Args:
            session: Sessão async do SQLAlchemy
            model_class: Classe do modelo SQLAlchemy
        """
        self.session = session
        self.model_class = model_class
    
    async def create(self, **kwargs) -> Any:
        """Cria um novo registro.
        
        Args:
            **kwargs: Dados para criação
            
        Returns:
            Instância do modelo criado
            
        Raises:
            IntegrityError: Se há violação de constraints
        """
        try:
            instance = self.model_class(**kwargs)
            self.session.add(instance)
            await self.session.flush()
            await self.session.refresh(instance)
            logger.debug(f"Criado {self.model_class.__name__} com ID: {instance.id}")
            return instance
        except IntegrityError as e:
            await self.session.rollback()
            logger.error(f"Erro ao criar {self.model_class.__name__}: {e}")
            raise
    
    async def get_by_id(self, id: str) -> Optional[Any]:
        """Busca um registro por ID.
        
        Args:
            id: ID do registro
            
        Returns:
            Instância do modelo ou None se não encontrado
        """
        result = await self.session.execute(
            select(self.model_class).where(self.model_class.id == id)
        )
        return result.scalar_one_or_none()
    
    async def update(self, id: str, **kwargs) -> Optional[Any]:
        """Atualiza um registro por ID.
        
        Args:
            id: ID do registro
            **kwargs: Dados para atualização
            
        Returns:
            Instância atualizada ou None se não encontrado
        """
        try:
            instance = await self.get_by_id(id)
            if not instance:
                return None
            
            for key, value in kwargs.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)
            
            await self.session.flush()
            await self.session.refresh(instance)
            logger.debug(f"Atualizado {self.model_class.__name__} ID: {id}")
            return instance
        except IntegrityError as e:
            await self.session.rollback()
            logger.error(f"Erro ao atualizar {self.model_class.__name__} ID {id}: {e}")
            raise
    
    async def delete(self, id: str) -> bool:
        """Remove um registro por ID.
        
        Args:
            id: ID do registro
            
        Returns:
            True se removido, False se não encontrado
        """
        result = await self.session.execute(
            delete(self.model_class).where(self.model_class.id == id)
        )
        deleted = result.rowcount > 0
        if deleted:
            logger.debug(f"Removido {self.model_class.__name__} ID: {id}")
        return deleted
    
    async def list_all(self, limit: int = 100, offset: int = 0) -> List[Any]:
        """Lista todos os registros com paginação.
        
        Args:
            limit: Número máximo de registros
            offset: Número de registros para pular
            
        Returns:
            Lista de instâncias do modelo
        """
        result = await self.session.execute(
            select(self.model_class)
            .offset(offset)
            .limit(limit)
            .order_by(asc(self.model_class.created_at))
        )
        return list(result.scalars().all())
    
    async def count(self) -> int:
        """Conta o total de registros.
        
        Returns:
            Número total de registros
        """
        result = await self.session.execute(
            select(func.count(self.model_class.id))
        )
        return result.scalar() or 0


class EquipmentRepository(BaseRepository):
    """Repository para equipamentos."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, Equipment)
    
    async def get_by_code(self, code: str) -> Optional[Equipment]:
        """Busca equipamento por código.
        
        Args:
            code: Código do equipamento
            
        Returns:
            Equipamento ou None se não encontrado
        """
        result = await self.session.execute(
            select(Equipment).where(Equipment.code == code)
        )
        return result.scalar_one_or_none()
    
    async def list_by_type(self, equipment_type: str) -> List[Equipment]:
        """Lista equipamentos por tipo.
        
        Args:
            equipment_type: Tipo do equipamento
            
        Returns:
            Lista de equipamentos
        """
        result = await self.session.execute(
            select(Equipment)
            .where(Equipment.equipment_type == equipment_type)
            .order_by(Equipment.code)
        )
        return list(result.scalars().all())
    
    async def list_by_criticality(self, criticality: str) -> List[Equipment]:
        """Lista equipamentos por criticidade.
        
        Args:
            criticality: Nível de criticidade (High, Medium, Low)
            
        Returns:
            Lista de equipamentos
        """
        result = await self.session.execute(
            select(Equipment)
            .where(Equipment.criticality == criticality)
            .order_by(Equipment.name)
        )
        return list(result.scalars().all())
    
    async def list_by_location(self, location: str) -> List[Equipment]:
        """Lista equipamentos por localização.
        
        Args:
            location: Localização do equipamento
            
        Returns:
            Lista de equipamentos
        """
        result = await self.session.execute(
            select(Equipment)
            .where(Equipment.location.ilike(f"%{location}%"))
            .order_by(Equipment.code)
        )
        return list(result.scalars().all())
    
    async def list_by_substation(self, substation: str) -> List[Equipment]:
        """Lista equipamentos por subestação.
        
        Args:
            substation: Nome da subestação
            
        Returns:
            Lista de equipamentos
        """
        result = await self.session.execute(
            select(Equipment)
            .where(Equipment.substation.ilike(f"%{substation}%"))
            .order_by(Equipment.code)
        )
        return list(result.scalars().all())
    
    async def list_critical_equipment(self) -> List[Equipment]:
        """Lista equipamentos críticos.
        
        Returns:
            Lista de equipamentos críticos
        """
        result = await self.session.execute(
            select(Equipment)
            .where(Equipment.is_critical == True)
            .order_by(Equipment.criticality, Equipment.code)
        )
        return list(result.scalars().all())
    
    async def search(self, query: str) -> List[Equipment]:
        """Busca equipamentos por texto.
        
        Args:
            query: Texto para busca (nome, código, descrição)
            
        Returns:
            Lista de equipamentos encontrados
        """
        search_pattern = f"%{query}%"
        result = await self.session.execute(
            select(Equipment)
            .where(
                or_(
                    Equipment.code.ilike(search_pattern),
                    Equipment.name.ilike(search_pattern),
                    Equipment.description.ilike(search_pattern)
                )
            )
            .order_by(Equipment.code)
        )
        return list(result.scalars().all())
    
    async def get_with_maintenances(self, equipment_id: str) -> Optional[Equipment]:
        """Busca equipamento com suas manutenções carregadas.
        
        Args:
            equipment_id: ID do equipamento
            
        Returns:
            Equipamento com manutenções ou None
        """
        result = await self.session.execute(
            select(Equipment)
            .options(selectinload(Equipment.maintenances))
            .where(Equipment.id == equipment_id)
        )
        return result.scalar_one_or_none()
    
    async def get_stats_by_type(self) -> List[Dict[str, Any]]:
        """Estatísticas de equipamentos por tipo.
        
        Returns:
            Lista com estatísticas por tipo
        """
        result = await self.session.execute(
            select(
                Equipment.equipment_type,
                func.count(Equipment.id).label('total'),
                func.count(
                    func.nullif(Equipment.is_critical, False)
                ).label('critical_count')
            )
            .group_by(Equipment.equipment_type)
            .order_by(Equipment.equipment_type)
        )
        return [
            {
                'equipment_type': row.equipment_type,
                'total': row.total,
                'critical_count': row.critical_count
            }
            for row in result.all()
        ]


class MaintenanceRepository(BaseRepository):
    """Repository para manutenções."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, Maintenance)
    
    async def list_by_equipment(self, equipment_id: str) -> List[Maintenance]:
        """Lista manutenções de um equipamento.
        
        Args:
            equipment_id: ID do equipamento
            
        Returns:
            Lista de manutenções
        """
        result = await self.session.execute(
            select(Maintenance)
            .where(Maintenance.equipment_id == equipment_id)
            .order_by(desc(Maintenance.scheduled_date))
        )
        return list(result.scalars().all())
    
    async def list_by_type(self, maintenance_type: str) -> List[Maintenance]:
        """Lista manutenções por tipo.
        
        Args:
            maintenance_type: Tipo da manutenção
            
        Returns:
            Lista de manutenções
        """
        result = await self.session.execute(
            select(Maintenance)
            .where(Maintenance.maintenance_type == maintenance_type)
            .order_by(desc(Maintenance.scheduled_date))
        )
        return list(result.scalars().all())
    
    async def list_by_status(self, status: str) -> List[Maintenance]:
        """Lista manutenções por status.
        
        Args:
            status: Status da manutenção
            
        Returns:
            Lista de manutenções
        """
        result = await self.session.execute(
            select(Maintenance)
            .where(Maintenance.status == status)
            .order_by(asc(Maintenance.scheduled_date))
        )
        return list(result.scalars().all())
    
    async def list_by_priority(self, priority: str) -> List[Maintenance]:
        """Lista manutenções por prioridade.
        
        Args:
            priority: Prioridade da manutenção
            
        Returns:
            Lista de manutenções
        """
        result = await self.session.execute(
            select(Maintenance)
            .where(Maintenance.priority == priority)
            .order_by(asc(Maintenance.scheduled_date))
        )
        return list(result.scalars().all())
    
    async def list_scheduled_between(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[Maintenance]:
        """Lista manutenções programadas em um período.
        
        Args:
            start_date: Data inicial
            end_date: Data final
            
        Returns:
            Lista de manutenções
        """
        result = await self.session.execute(
            select(Maintenance)
            .where(
                and_(
                    Maintenance.scheduled_date >= start_date,
                    Maintenance.scheduled_date <= end_date
                )
            )
            .order_by(asc(Maintenance.scheduled_date))
        )
        return list(result.scalars().all())
    
    async def list_overdue(self, current_date: datetime) -> List[Maintenance]:
        """Lista manutenções em atraso.
        
        Args:
            current_date: Data atual para comparação
            
        Returns:
            Lista de manutenções em atraso
        """
        result = await self.session.execute(
            select(Maintenance)
            .where(
                and_(
                    Maintenance.scheduled_date < current_date,
                    Maintenance.status.in_(['Planned', 'InProgress'])
                )
            )
            .order_by(asc(Maintenance.scheduled_date))
        )
        return list(result.scalars().all())
    
    async def list_requiring_followup(self) -> List[Maintenance]:
        """Lista manutenções que requerem acompanhamento.
        
        Returns:
            Lista de manutenções para follow-up
        """
        result = await self.session.execute(
            select(Maintenance)
            .where(Maintenance.requires_followup == True)
            .order_by(asc(Maintenance.followup_date))
        )
        return list(result.scalars().all())
    
    async def get_with_equipment(self, maintenance_id: str) -> Optional[Maintenance]:
        """Busca manutenção com equipamento carregado.
        
        Args:
            maintenance_id: ID da manutenção
            
        Returns:
            Manutenção com equipamento ou None
        """
        result = await self.session.execute(
            select(Maintenance)
            .options(selectinload(Maintenance.equipment))
            .where(Maintenance.id == maintenance_id)
        )
        return result.scalar_one_or_none()
    
    async def get_cost_summary_by_period(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict[str, Any]:
        """Resumo de custos de manutenção por período.
        
        Args:
            start_date: Data inicial
            end_date: Data final
            
        Returns:
            Dicionário com estatísticas de custos
        """
        result = await self.session.execute(
            select(
                func.count(Maintenance.id).label('total_maintenances'),
                func.sum(Maintenance.estimated_cost).label('total_estimated'),
                func.sum(Maintenance.actual_cost).label('total_actual'),
                func.avg(Maintenance.actual_cost).label('avg_cost')
            )
            .where(
                and_(
                    Maintenance.completion_date >= start_date,
                    Maintenance.completion_date <= end_date,
                    Maintenance.status == 'Completed'
                )
            )
        )
        row = result.one_or_none()
        return {
            'total_maintenances': row.total_maintenances or 0,
            'total_estimated': float(row.total_estimated or 0),
            'total_actual': float(row.total_actual or 0),
            'avg_cost': float(row.avg_cost or 0)
        } if row else {}
    
    async def get_stats_by_type(self) -> List[Dict[str, Any]]:
        """Estatísticas de manutenções por tipo.
        
        Returns:
            Lista com estatísticas por tipo
        """
        result = await self.session.execute(
            select(
                Maintenance.maintenance_type,
                func.count(Maintenance.id).label('total'),
                func.count(
                    func.nullif(Maintenance.status != 'Completed', False)
                ).label('completed')
            )
            .group_by(Maintenance.maintenance_type)
            .order_by(Maintenance.maintenance_type)
        )
        return [
            {
                'maintenance_type': row.maintenance_type,
                'total': row.total,
                'completed': row.completed,
                'completion_rate': round((row.completed / row.total) * 100, 2) if row.total > 0 else 0
            }
            for row in result.all()
        ]


class FailureRepository(BaseRepository):
    """Repository para registros de falhas."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, Failure)
    
    async def list_by_equipment(
        self, 
        equipment_id: str, 
        limit: int = 100,
        offset: int = 0
    ) -> List[Failure]:
        """Lista falhas de um equipamento.
        
        Args:
            equipment_id: ID do equipamento
            limit: Número máximo de registros
            offset: Número de registros para pular
            
        Returns:
            Lista de registros de falhas
        """
        result = await self.session.execute(
            select(Failure)
            .where(Failure.equipment_id == equipment_id)
            .order_by(desc(Failure.failure_date))
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def list_by_failure_type(self, failure_type: str) -> List[Failure]:
        """Lista falhas por tipo.
        
        Args:
            failure_type: Tipo de falha
            
        Returns:
            Lista de registros
        """
        result = await self.session.execute(
            select(Failure)
            .where(Failure.failure_type == failure_type)
            .order_by(desc(Failure.failure_date))
        )
        return list(result.scalars().all())
    
    async def list_by_source(self, data_source: str) -> List[Failure]:
        """Lista falhas por fonte de dados.
        
        Args:
            data_source: Fonte dos dados
            
        Returns:
            Lista de registros
        """
        result = await self.session.execute(
            select(Failure)
            .where(Failure.data_source == data_source)
            .order_by(desc(Failure.failure_date))
        )
        return list(result.scalars().all())
    
    async def list_by_severity(self, severity: str) -> List[Failure]:
        """Lista falhas por severidade.
        
        Args:
            severity: Severidade da falha
            
        Returns:
            Lista de registros
        """
        result = await self.session.execute(
            select(Failure)
            .where(Failure.severity == severity)
            .order_by(desc(Failure.failure_date))
        )
        return list(result.scalars().all())
    
    async def list_by_impact_level(self, impact_level: str) -> List[Failure]:
        """Lista falhas por nível de impacto.
        
        Args:
            impact_level: Nível de impacto
            
        Returns:
            Lista de registros
        """
        result = await self.session.execute(
            select(Failure)
            .where(Failure.impact_level == impact_level)
            .order_by(desc(Failure.failure_date))
        )
        return list(result.scalars().all())
    
    async def list_by_status(self, status: str) -> List[Failure]:
        """Lista falhas por status.
        
        Args:
            status: Status da falha
            
        Returns:
            Lista de registros
        """
        result = await self.session.execute(
            select(Failure)
            .where(Failure.status == status)
            .order_by(desc(Failure.failure_date))
        )
        return list(result.scalars().all())
    
    async def list_in_period(
        self, 
        start_date: datetime, 
        end_date: datetime,
        equipment_id: Optional[str] = None
    ) -> List[Failure]:
        """Lista falhas em um período específico.
        
        Args:
            start_date: Data inicial
            end_date: Data final
            equipment_id: ID do equipamento (opcional)
            
        Returns:
            Lista de registros no período
        """
        query = select(Failure).where(
            and_(
                Failure.failure_date >= start_date,
                Failure.failure_date <= end_date
            )
        )
        
        if equipment_id:
            query = query.where(Failure.equipment_id == equipment_id)
        
        query = query.order_by(desc(Failure.failure_date))
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def list_unvalidated(self) -> List[Failure]:
        """Lista falhas não validadas.
        
        Returns:
            Lista de registros não validados
        """
        result = await self.session.execute(
            select(Failure)
            .where(Failure.is_validated == False)
            .order_by(desc(Failure.failure_date))
        )
        return list(result.scalars().all())
    
    async def list_unresolved(self) -> List[Failure]:
        """Lista falhas não resolvidas.
        
        Returns:
            Lista de falhas em aberto
        """
        result = await self.session.execute(
            select(Failure)
            .where(Failure.status.in_(["Reported", "InProgress"]))
            .order_by(desc(Failure.failure_date))
        )
        return list(result.scalars().all())
    
    async def get_latest_by_equipment(self, equipment_id: str) -> Optional[Failure]:
        """Busca a falha mais recente de um equipamento.
        
        Args:
            equipment_id: ID do equipamento
            
        Returns:
            Falha mais recente ou None
        """
        result = await self.session.execute(
            select(Failure)
            .where(Failure.equipment_id == equipment_id)
            .order_by(desc(Failure.failure_date))
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def get_by_incident_id(self, incident_id: str) -> Optional[Failure]:
        """Busca falha por ID do incidente.
        
        Args:
            incident_id: ID do incidente
            
        Returns:
            Falha encontrada ou None
        """
        result = await self.session.execute(
            select(Failure)
            .where(Failure.incident_id == incident_id)
        )
        return result.scalar_one_or_none()
    
    async def get_critical_failures(
        self,
        equipment_id: Optional[str] = None,
        days_back: int = 30
    ) -> List[Failure]:
        """Busca falhas críticas recentes.
        
        Args:
            equipment_id: ID do equipamento (opcional)
            days_back: Número de dias para buscar (padrão: 30)
            
        Returns:
            Lista de falhas críticas
        """
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        query = select(Failure).where(
            and_(
                Failure.severity == "Critical",
                Failure.failure_date >= cutoff_date
            )
        )
        
        if equipment_id:
            query = query.where(Failure.equipment_id == equipment_id)
        
        query = query.order_by(desc(Failure.failure_date))
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_failure_stats(
        self,
        equipment_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Calcula estatísticas de falhas.
        
        Args:
            equipment_id: ID do equipamento (opcional)
            start_date: Data inicial (opcional)
            end_date: Data final (opcional)
            
        Returns:
            Dicionário com estatísticas
        """
        from sqlalchemy import func, case
        
        query = select(
            func.count(Failure.id).label('total_failures'),
            func.avg(Failure.downtime_hours).label('avg_downtime'),
            func.sum(Failure.downtime_hours).label('total_downtime'),
            func.avg(Failure.cost).label('avg_cost'),
            func.sum(Failure.cost).label('total_cost'),
            func.sum(
                case(
                    (Failure.severity == 'Critical', 1),
                    else_=0
                )
            ).label('critical_count'),
            func.sum(
                case(
                    (Failure.severity == 'High', 1),
                    else_=0
                )
            ).label('high_count'),
            func.sum(
                case(
                    (Failure.severity == 'Medium', 1),
                    else_=0
                )
            ).label('medium_count'),
            func.sum(
                case(
                    (Failure.severity == 'Low', 1),
                    else_=0
                )
            ).label('low_count')
        )
        
        # Aplicar filtros
        if equipment_id:
            query = query.where(Failure.equipment_id == equipment_id)
        if start_date:
            query = query.where(Failure.failure_date >= start_date)
        if end_date:
            query = query.where(Failure.failure_date <= end_date)
        
        result = await self.session.execute(query)
        row = result.first()
        
        return {
            'total_failures': row.total_failures or 0,
            'avg_downtime_hours': float(row.avg_downtime) if row.avg_downtime else 0.0,
            'total_downtime_hours': float(row.total_downtime) if row.total_downtime else 0.0,
            'avg_cost': float(row.avg_cost) if row.avg_cost else 0.0,
            'total_cost': float(row.total_cost) if row.total_cost else 0.0,
            'critical_count': row.critical_count or 0,
            'high_count': row.high_count or 0,
            'medium_count': row.medium_count or 0,
            'low_count': row.low_count or 0
        }
    
    async def bulk_create(self, failure_records: List[Dict[str, Any]]) -> List[Failure]:
        """Criação em lote de registros de falhas.
        
        Args:
            failure_records: Lista de dicionários com dados de falhas
            
        Returns:
            Lista de registros criados
        """
        try:
            instances = [Failure(**record) for record in failure_records]
            self.session.add_all(instances)
            await self.session.flush()
            
            # Refresh all instances to get the IDs
            for instance in instances:
                await self.session.refresh(instance)
            
            logger.info(f"Criados {len(instances)} registros de Failure em lote")
            return instances
        except IntegrityError as e:
            await self.session.rollback()
            logger.error(f"Erro ao criar registros de falhas em lote: {e}")
            raise
    
    async def get_data_quality_stats(self) -> Dict[str, Any]:
        """Estatísticas de qualidade dos dados de falhas.
        
        Returns:
            Dicionário com estatísticas de qualidade
        """
        result = await self.session.execute(
            select(
                func.count(Failure.id).label('total_records'),
                func.count(
                    func.nullif(Failure.is_validated, False)
                ).label('validated_count'),
                func.count(
                    func.nullif(Failure.validation_status != 'Valid', False)
                ).label('valid_count')
            )
        )
        row = result.one_or_none()
        return {
            'total_records': row.total_records or 0,
            'validated_count': row.validated_count or 0,
            'validation_rate': round((row.validated_count / row.total_records) * 100, 2) if row.total_records > 0 else 0,
            'valid_count': row.valid_count or 0
        } if row else {}


class UserFeedbackRepository(BaseRepository):
    """Repository para feedback dos usuários."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, UserFeedback)
    
    async def list_by_session(self, session_id: str) -> List[UserFeedback]:
        """Lista feedback por sessão."""
        result = await self.session.execute(
            select(UserFeedback)
            .where(UserFeedback.session_id == session_id)
            .order_by(desc(UserFeedback.created_at))
        )
        return list(result.scalars().all())
    
    async def list_helpful(self, helpful: bool) -> List[UserFeedback]:
        """Lista feedback por útil/não útil."""
        result = await self.session.execute(
            select(UserFeedback)
            .where(UserFeedback.helpful == helpful)
            .order_by(desc(UserFeedback.created_at))
        )
        return list(result.scalars().all())
    
    async def get_stats_summary(self) -> Dict[str, Any]:
        """Resumo geral das estatísticas de feedback."""
        result = await self.session.execute(
            select(
                func.count(UserFeedback.id).label('total_feedback'),
                func.count(
                    func.nullif(UserFeedback.helpful != True, False)
                ).label('positive_feedback'),
                func.avg(UserFeedback.rating).label('avg_rating')
            )
        )
        row = result.one_or_none()
        
        if not row or row.total_feedback == 0:
            return {
                'total_feedback': 0,
                'positive_feedback': 0,
                'negative_feedback': 0,
                'satisfaction_rate': 0.0,
                'avg_rating': 0.0
            }
        
        negative_feedback = row.total_feedback - row.positive_feedback
        satisfaction_rate = (row.positive_feedback / row.total_feedback) * 100 if row.total_feedback > 0 else 0
        
        return {
            'total_feedback': row.total_feedback,
            'positive_feedback': row.positive_feedback,
            'negative_feedback': negative_feedback,
            'satisfaction_rate': round(satisfaction_rate, 2),
            'avg_rating': round(float(row.avg_rating or 0), 2)
        }
    
    async def get_by_message_id(self, message_id: str) -> Optional[UserFeedback]:
        """Busca feedback por ID da mensagem."""
        result = await self.session.execute(
            select(UserFeedback)
            .where(UserFeedback.message_id == message_id)
        )
        return result.scalar_one_or_none()


class UploadStatusRepository(BaseRepository):
    """Repository para status de uploads."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, UploadStatus)
    
    async def get_by_upload_id(self, upload_id: str) -> Optional[UploadStatus]:
        """Busca upload pelo upload_id.
        
        Args:
            upload_id: ID único do upload
            
        Returns:
            Status do upload ou None se não encontrado
        """
        result = await self.session.execute(
            select(UploadStatus).where(UploadStatus.upload_id == upload_id)
        )
        return result.scalar_one_or_none()
    
    async def update_status(self, upload_id: str, status: str, **kwargs) -> Optional[UploadStatus]:
        """Atualiza status e outros campos de um upload.
        
        Args:
            upload_id: ID do upload
            status: Novo status
            **kwargs: Outros campos para atualizar
            
        Returns:
            Upload atualizado ou None se não encontrado
        """
        try:
            upload_record = await self.get_by_upload_id(upload_id)
            if not upload_record:
                return None
            
            # Atualiza status
            upload_record.status = status
            
            # Atualiza outros campos fornecidos
            for key, value in kwargs.items():
                if hasattr(upload_record, key):
                    setattr(upload_record, key, value)
            
            await self.session.flush()
            await self.session.refresh(upload_record)
            logger.debug(f"Status do upload {upload_id} atualizado para: {status}")
            return upload_record
            
        except IntegrityError as e:
            await self.session.rollback()
            logger.error(f"Erro ao atualizar upload {upload_id}: {e}")
            raise
    
    async def list_by_status(self, status: str, limit: int = 50) -> List[UploadStatus]:
        """Lista uploads por status.
        
        Args:
            status: Status para filtrar
            limit: Limite de resultados
            
        Returns:
            Lista de uploads
        """
        result = await self.session.execute(
            select(UploadStatus)
            .where(UploadStatus.status == status)
            .order_by(desc(UploadStatus.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def list_by_user(self, user_id: str, limit: int = 50) -> List[UploadStatus]:
        """Lista uploads de um usuário.
        
        Args:
            user_id: ID do usuário
            limit: Limite de resultados
            
        Returns:
            Lista de uploads do usuário
        """
        result = await self.session.execute(
            select(UploadStatus)
            .where(UploadStatus.user_id == user_id)
            .order_by(desc(UploadStatus.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Obtém estatísticas de uploads.
        
        Returns:
            Dicionário com estatísticas
        """
        # Contagem total
        total_result = await self.session.execute(
            select(func.count(UploadStatus.id))
        )
        total = total_result.scalar() or 0
        
        # Contagem por status
        status_result = await self.session.execute(
            select(UploadStatus.status, func.count(UploadStatus.id))
            .group_by(UploadStatus.status)
        )
        status_counts = dict(status_result.all())
        
        # Estatísticas de processamento
        processing_result = await self.session.execute(
            select(
                func.avg(UploadStatus.records_processed),
                func.sum(UploadStatus.records_valid),
                func.sum(UploadStatus.records_invalid)
            )
            .where(UploadStatus.status == 'completed')
        )
        avg_processed, total_valid, total_invalid = processing_result.first()
        
        return {
            'total_uploads': total,
            'by_status': status_counts,
            'avg_records_processed': float(avg_processed or 0),
            'total_records_valid': int(total_valid or 0),
            'total_records_invalid': int(total_invalid or 0),
            'success_rate': (status_counts.get('completed', 0) / total * 100) if total > 0 else 0
        }


class RepositoryManager:
    """Gerenciador centralizado de repositories."""
    
    def __init__(self, session: AsyncSession):
        """Inicializa o gerenciador com uma sessão.
        
        Args:
            session: Sessão async do SQLAlchemy
        """
        self.session = session
        self.equipment = EquipmentRepository(session)
        self.maintenance = MaintenanceRepository(session)
        self.failures = FailureRepository(session)
        self.user_feedback = UserFeedbackRepository(session)
        self.upload_status = UploadStatusRepository(session)
    
    async def commit(self):
        """Confirma todas as transações pendentes."""
        await self.session.commit()
    
    async def rollback(self):
        """Desfaz todas as transações pendentes."""
        await self.session.rollback()
    
    async def close(self):
        """Fecha a sessão."""
        await self.session.close() 