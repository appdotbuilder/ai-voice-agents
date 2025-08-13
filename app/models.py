from sqlmodel import SQLModel, Field, Relationship, JSON, Column
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from enum import Enum


# Enums for service types and status
class ServiceType(str, Enum):
    TTS = "tts"
    STT = "stt"
    LLM = "llm"


class AgentStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"


class TestSessionStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


# Persistent models (stored in database)
class User(SQLModel, table=True):
    __tablename__ = "users"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, max_length=255, regex=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
    username: str = Field(unique=True, max_length=50)
    full_name: str = Field(max_length=100)
    password_hash: str = Field(max_length=255)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    agents: List["Agent"] = Relationship(back_populates="user")
    test_sessions: List["TestSession"] = Relationship(back_populates="user")


class AIService(SQLModel, table=True):
    __tablename__ = "ai_services"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)
    service_type: ServiceType = Field()
    provider: str = Field(max_length=100)  # e.g., "Google", "OpenAI", "Azure"
    is_active: bool = Field(default=True)
    description: str = Field(default="", max_length=500)
    default_config: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    agent_configurations: List["AgentServiceConfig"] = Relationship(back_populates="service")


class Agent(SQLModel, table=True):
    __tablename__ = "agents"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    name: str = Field(max_length=100)
    description: str = Field(default="", max_length=500)
    system_message: str = Field(default="", max_length=2000)
    status: AgentStatus = Field(default=AgentStatus.DRAFT)

    # Voice configuration
    voice_pitch: Decimal = Field(default=Decimal("1.0"), ge=0.1, le=2.0)  # Range 0.1 to 2.0
    voice_speed: Decimal = Field(default=Decimal("1.0"), ge=0.1, le=3.0)  # Range 0.1 to 3.0
    voice_volume: Decimal = Field(default=Decimal("1.0"), ge=0.1, le=2.0)  # Range 0.1 to 2.0

    # Additional configuration
    response_timeout: int = Field(default=30, ge=5, le=300)  # seconds
    max_conversation_length: int = Field(default=50, ge=1, le=1000)  # number of exchanges

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    user: User = Relationship(back_populates="agents")
    service_configs: List["AgentServiceConfig"] = Relationship(back_populates="agent")
    api_keys: List["APIKey"] = Relationship(back_populates="agent")
    test_sessions: List["TestSession"] = Relationship(back_populates="agent")


class AgentServiceConfig(SQLModel, table=True):
    __tablename__ = "agent_service_configs"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    agent_id: int = Field(foreign_key="agents.id")
    service_id: int = Field(foreign_key="ai_services.id")

    # Service-specific configuration
    config: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    is_primary: bool = Field(default=False)  # Primary service for this type

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    agent: Agent = Relationship(back_populates="service_configs")
    service: AIService = Relationship(back_populates="agent_configurations")


class APIKey(SQLModel, table=True):
    __tablename__ = "api_keys"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    agent_id: int = Field(foreign_key="agents.id")
    key_hash: str = Field(unique=True, max_length=255)  # Hashed API key for security
    key_preview: str = Field(max_length=20)  # First few chars for display
    name: str = Field(max_length=100)  # User-friendly name for the key
    is_active: bool = Field(default=True)
    usage_count: int = Field(default=0, ge=0)
    last_used_at: Optional[datetime] = Field(default=None)
    expires_at: Optional[datetime] = Field(default=None)

    # Rate limiting
    rate_limit_per_hour: Optional[int] = Field(default=None, ge=1)
    rate_limit_per_day: Optional[int] = Field(default=None, ge=1)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    agent: Agent = Relationship(back_populates="api_keys")


class TestSession(SQLModel, table=True):
    __tablename__ = "test_sessions"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    agent_id: int = Field(foreign_key="agents.id")

    status: TestSessionStatus = Field(default=TestSessionStatus.ACTIVE)
    session_data: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))  # Conversation history

    # Metrics
    total_exchanges: int = Field(default=0, ge=0)
    avg_response_time: Optional[Decimal] = Field(default=None, ge=0.0)
    total_duration: Optional[int] = Field(default=None, ge=0)  # seconds

    # Error tracking
    error_count: int = Field(default=0, ge=0)
    last_error: Optional[str] = Field(default=None, max_length=1000)

    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    user: User = Relationship(back_populates="test_sessions")
    agent: Agent = Relationship(back_populates="test_sessions")
    conversation_logs: List["ConversationLog"] = Relationship(back_populates="test_session")


class ConversationLog(SQLModel, table=True):
    __tablename__ = "conversation_logs"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    test_session_id: int = Field(foreign_key="test_sessions.id")

    # Message details
    sequence_number: int = Field(ge=1)
    user_input: str = Field(max_length=2000)
    agent_response: str = Field(max_length=5000)

    # Performance metrics
    processing_time: Decimal = Field(ge=0.0)  # milliseconds
    tts_processing_time: Optional[Decimal] = Field(default=None, ge=0.0)
    stt_processing_time: Optional[Decimal] = Field(default=None, ge=0.0)
    llm_processing_time: Optional[Decimal] = Field(default=None, ge=0.0)

    # Audio metadata
    audio_input_duration: Optional[Decimal] = Field(default=None, ge=0.0)  # seconds
    audio_output_duration: Optional[Decimal] = Field(default=None, ge=0.0)  # seconds

    # Error handling
    has_error: bool = Field(default=False)
    error_message: Optional[str] = Field(default=None, max_length=1000)

    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    test_session: TestSession = Relationship(back_populates="conversation_logs")


# Non-persistent schemas (for validation, forms, API requests/responses)
class UserCreate(SQLModel, table=False):
    email: str = Field(max_length=255, regex=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
    username: str = Field(max_length=50)
    full_name: str = Field(max_length=100)
    password: str = Field(min_length=8, max_length=100)


class UserUpdate(SQLModel, table=False):
    full_name: Optional[str] = Field(default=None, max_length=100)
    username: Optional[str] = Field(default=None, max_length=50)


class AgentCreate(SQLModel, table=False):
    name: str = Field(max_length=100)
    description: str = Field(default="", max_length=500)
    system_message: str = Field(default="", max_length=2000)
    voice_pitch: Decimal = Field(default=Decimal("1.0"), ge=0.1, le=2.0)
    voice_speed: Decimal = Field(default=Decimal("1.0"), ge=0.1, le=3.0)
    voice_volume: Decimal = Field(default=Decimal("1.0"), ge=0.1, le=2.0)
    response_timeout: int = Field(default=30, ge=5, le=300)
    max_conversation_length: int = Field(default=50, ge=1, le=1000)


class AgentUpdate(SQLModel, table=False):
    name: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    system_message: Optional[str] = Field(default=None, max_length=2000)
    voice_pitch: Optional[Decimal] = Field(default=None, ge=0.1, le=2.0)
    voice_speed: Optional[Decimal] = Field(default=None, ge=0.1, le=3.0)
    voice_volume: Optional[Decimal] = Field(default=None, ge=0.1, le=2.0)
    response_timeout: Optional[int] = Field(default=None, ge=5, le=300)
    max_conversation_length: Optional[int] = Field(default=None, ge=1, le=1000)
    status: Optional[AgentStatus] = Field(default=None)


class ServiceConfigCreate(SQLModel, table=False):
    service_id: int
    config: Dict[str, Any] = Field(default={})
    is_primary: bool = Field(default=False)


class ServiceConfigUpdate(SQLModel, table=False):
    config: Optional[Dict[str, Any]] = Field(default=None)
    is_primary: Optional[bool] = Field(default=None)


class APIKeyCreate(SQLModel, table=False):
    name: str = Field(max_length=100)
    expires_at: Optional[datetime] = Field(default=None)
    rate_limit_per_hour: Optional[int] = Field(default=None, ge=1)
    rate_limit_per_day: Optional[int] = Field(default=None, ge=1)


class APIKeyUpdate(SQLModel, table=False):
    name: Optional[str] = Field(default=None, max_length=100)
    is_active: Optional[bool] = Field(default=None)
    expires_at: Optional[datetime] = Field(default=None)
    rate_limit_per_hour: Optional[int] = Field(default=None, ge=1)
    rate_limit_per_day: Optional[int] = Field(default=None, ge=1)


class TestSessionCreate(SQLModel, table=False):
    agent_id: int


class ConversationEntry(SQLModel, table=False):
    user_input: str = Field(max_length=2000)
    agent_response: str = Field(max_length=5000)
    processing_time: Decimal = Field(ge=0.0)
    tts_processing_time: Optional[Decimal] = Field(default=None, ge=0.0)
    stt_processing_time: Optional[Decimal] = Field(default=None, ge=0.0)
    llm_processing_time: Optional[Decimal] = Field(default=None, ge=0.0)
    audio_input_duration: Optional[Decimal] = Field(default=None, ge=0.0)
    audio_output_duration: Optional[Decimal] = Field(default=None, ge=0.0)
    has_error: bool = Field(default=False)
    error_message: Optional[str] = Field(default=None, max_length=1000)


class AIServiceCreate(SQLModel, table=False):
    name: str = Field(max_length=100)
    service_type: ServiceType
    provider: str = Field(max_length=100)
    description: str = Field(default="", max_length=500)
    default_config: Dict[str, Any] = Field(default={})


class AIServiceUpdate(SQLModel, table=False):
    name: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    is_active: Optional[bool] = Field(default=None)
    default_config: Optional[Dict[str, Any]] = Field(default=None)
