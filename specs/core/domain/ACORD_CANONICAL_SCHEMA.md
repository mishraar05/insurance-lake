# ACORD Canonical Schema

---

## Front Matter

```yaml
id: acord-canonical-schema
version: 1.0
status: approved
approved_date: 2026-06-18
tier: core
component: domain
backlog_ids:
  - DOM-001  # Define ACORD canonical model
  - META-002 # Silver layer schema design
dependencies:
  - metadata-models-spec
runtime: Python 3.10+
purpose: Define ACORD-aligned canonical data model for P&C insurance Silver layer (Party, Policy, Coverage, Claim, Payment, Loss)
inputs:
  - ACORD P&C standards (https://www.acord.org/)
  - PROJECT_CONTEXT.md §4 (ACORD canonical requirement)
outputs:
  - Python Pydantic models for ACORD entities
  - Delta table DDL schemas
  - Entity relationship documentation
```

---

## 1. Purpose

Define the **ACORD-aligned canonical data model** for the **Silver layer** of the InsureLake framework. This model follows ACORD P&C insurance standards and provides a consistent, industry-standard representation of insurance data across all source systems.

**Six core ACORD entities:**
* **Party** — individuals and organizations (policyholders, insurers, agents, vendors)
* **Policy** — insurance policies (auto, home, commercial, etc.)
* **Coverage** — coverage lines within a policy (liability, property, etc.)
* **Claim** — insurance claims filed against policies
* **Payment** — premium payments and claim payouts
* **Loss** — loss events and reserves

**Goals:**
1. **Standardization** — all Bronze sources harmonize to this canonical model in Silver
2. **Interoperability** — downstream Gold marts and analytics consume from Silver
3. **Type safety** — Pydantic models provide runtime validation
4. **Extensibility** — additional fields can be added while preserving core ACORD attributes

**Architectural alignment** (Decision: PROJECT_CONTEXT §4, 2026-06-17):
* Silver layer tables follow this schema
* Transformations (Bronze → Silver) map source data to ACORD fields
* Gold layer aggregates and denormalizes from Silver

---

## 2. Entity Relationship Diagram

```
Party (1) ──────< (N) Policy
                      │
                      ├──< (N) Coverage
                      │
                      └──< (N) Claim
                              │
                              ├──< (N) Payment
                              │
                              └──< (N) Loss
```

**Relationships:**
* One **Party** has many **Policies**
* One **Policy** has many **Coverages**
* One **Policy** has many **Claims**
* One **Claim** has many **Payments** (payouts)
* One **Claim** has many **Loss** records (reserves, loss estimates)
* **Payments** can also be premium payments (linked to Policy, not Claim)

---

## 3. Entity Definitions

### 3.1 Party Entity

**Purpose:** Represents individuals and organizations (policyholders, insurers, agents, vendors).

**Pydantic Model:**
```python
from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import date
from enum import Enum

class PartyType(str, Enum):
    """Type of party."""
    PERSON = "person"
    ORGANIZATION = "organization"

class PartyRole(str, Enum):
    """Role of party in insurance context."""
    POLICYHOLDER = "policyholder"
    INSURED = "insured"
    INSURER = "insurer"
    AGENT = "agent"
    BROKER = "broker"
    VENDOR = "vendor"
    CLAIMANT = "claimant"

class Party(BaseModel):
    """
    ACORD Party entity (person or organization).
    
    Attributes:
        party_id: Unique identifier (primary key)
        party_type: Person or organization
        party_role: Role in insurance context
        name: Full name (person) or legal name (organization)
        first_name: First name (person only)
        middle_name: Middle name (person only)
        last_name: Last name (person only)
        date_of_birth: DOB (person only)
        gender: Gender (person only)
        tax_id: SSN (person) or EIN (organization)
        email: Primary email address
        phone: Primary phone number
        address_line1: Street address line 1
        address_line2: Street address line 2 (apt, suite, etc.)
        city: City
        state: State/province code (2-letter)
        postal_code: ZIP/postal code
        country: Country code (ISO 3166-1 alpha-3)
        credit_score: Credit score (person only)
        preferred_language: ISO 639-1 language code (e.g., "en", "es")
        created_date: Record creation date
        updated_date: Record last update date
        source_system: Source system identifier
        source_party_id: Original party ID from source system
    """
    party_id: str
    party_type: PartyType
    party_role: list[PartyRole] = Field(default_factory=list)  # Party can have multiple roles
    name: str
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None  # "M", "F", "X", "U" (unknown)
    tax_id: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: str = "USA"
    credit_score: Optional[int] = Field(default=None, ge=300, le=850)
    preferred_language: str = "en"
    created_date: date
    updated_date: date
    source_system: str
    source_party_id: str
    
    class Config:
        frozen = True
```

**Delta DDL:**
```sql
CREATE TABLE IF NOT EXISTS {catalog}.silver.party (
    party_id STRING NOT NULL COMMENT 'Unique party identifier',
    party_type STRING NOT NULL COMMENT 'Person or organization',
    party_role ARRAY<STRING> COMMENT 'Roles (policyholder, agent, etc.)',
    name STRING NOT NULL COMMENT 'Full name',
    first_name STRING COMMENT 'First name (person)',
    middle_name STRING COMMENT 'Middle name (person)',
    last_name STRING COMMENT 'Last name (person)',
    date_of_birth DATE COMMENT 'Date of birth (person)',
    gender STRING COMMENT 'Gender (M/F/X/U)',
    tax_id STRING COMMENT 'SSN or EIN',
    email STRING COMMENT 'Email address',
    phone STRING COMMENT 'Phone number',
    address_line1 STRING COMMENT 'Address line 1',
    address_line2 STRING COMMENT 'Address line 2',
    city STRING COMMENT 'City',
    state STRING COMMENT 'State code (2-letter)',
    postal_code STRING COMMENT 'ZIP/postal code',
    country STRING NOT NULL COMMENT 'Country code (ISO 3166)',
    credit_score INT COMMENT 'Credit score (300-850)',
    preferred_language STRING NOT NULL COMMENT 'Language code (ISO 639)',
    created_date DATE NOT NULL COMMENT 'Record creation date',
    updated_date DATE NOT NULL COMMENT 'Record update date',
    source_system STRING NOT NULL COMMENT 'Source system identifier',
    source_party_id STRING NOT NULL COMMENT 'Original party ID from source',
    CONSTRAINT party_pk PRIMARY KEY (party_id)
)
USING DELTA
CLUSTER BY (party_id)
COMMENT 'ACORD Party entity - individuals and organizations';
```

---

### 3.2 Policy Entity

**Purpose:** Represents insurance policies.

**Pydantic Model:**
```python
class PolicyStatus(str, Enum):
    """Policy status."""
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    LAPSED = "lapsed"

class ProductType(str, Enum):
    """Insurance product type."""
    AUTO = "auto"
    HOME = "home"
    RENTERS = "renters"
    COMMERCIAL_AUTO = "commercial_auto"
    COMMERCIAL_PROPERTY = "commercial_property"
    WORKERS_COMP = "workers_comp"
    GENERAL_LIABILITY = "general_liability"
    UMBRELLA = "umbrella"

class Policy(BaseModel):
    """
    ACORD Policy entity.
    
    Attributes:
        policy_id: Unique identifier (primary key)
        policy_number: Human-readable policy number
        party_id: Foreign key to Party (policyholder)
        product_type: Type of insurance product
        status: Policy status
        effective_date: Policy effective date
        expiration_date: Policy expiration date
        issue_date: Policy issue date
        premium_amount: Total annual premium
        currency: Currency code (ISO 4217)
        payment_frequency: Premium payment frequency
        deductible_amount: Policy deductible
        policy_limit: Total policy limit
        agent_id: Foreign key to Party (agent)
        underwriter_id: Foreign key to Party (underwriter)
        created_date: Record creation date
        updated_date: Record last update date
        source_system: Source system identifier
        source_policy_id: Original policy ID from source system
    """
    policy_id: str
    policy_number: str
    party_id: str  # FK to Party
    product_type: ProductType
    status: PolicyStatus
    effective_date: date
    expiration_date: date
    issue_date: Optional[date] = None
    premium_amount: float = Field(ge=0.0)
    currency: str = "USD"
    payment_frequency: Optional[str] = None  # "monthly", "quarterly", "annual"
    deductible_amount: Optional[float] = Field(default=None, ge=0.0)
    policy_limit: Optional[float] = Field(default=None, ge=0.0)
    agent_id: Optional[str] = None  # FK to Party
    underwriter_id: Optional[str] = None  # FK to Party
    created_date: date
    updated_date: date
    source_system: str
    source_policy_id: str
    
    class Config:
        frozen = True
```

**Delta DDL:**
```sql
CREATE TABLE IF NOT EXISTS {catalog}.silver.policy (
    policy_id STRING NOT NULL COMMENT 'Unique policy identifier',
    policy_number STRING NOT NULL COMMENT 'Human-readable policy number',
    party_id STRING NOT NULL COMMENT 'FK to Party (policyholder)',
    product_type STRING NOT NULL COMMENT 'Insurance product type',
    status STRING NOT NULL COMMENT 'Policy status',
    effective_date DATE NOT NULL COMMENT 'Policy effective date',
    expiration_date DATE NOT NULL COMMENT 'Policy expiration date',
    issue_date DATE COMMENT 'Policy issue date',
    premium_amount DECIMAL(18,2) NOT NULL COMMENT 'Annual premium',
    currency STRING NOT NULL COMMENT 'Currency code (ISO 4217)',
    payment_frequency STRING COMMENT 'Payment frequency',
    deductible_amount DECIMAL(18,2) COMMENT 'Policy deductible',
    policy_limit DECIMAL(18,2) COMMENT 'Total policy limit',
    agent_id STRING COMMENT 'FK to Party (agent)',
    underwriter_id STRING COMMENT 'FK to Party (underwriter)',
    created_date DATE NOT NULL COMMENT 'Record creation date',
    updated_date DATE NOT NULL COMMENT 'Record update date',
    source_system STRING NOT NULL COMMENT 'Source system identifier',
    source_policy_id STRING NOT NULL COMMENT 'Original policy ID from source',
    CONSTRAINT policy_pk PRIMARY KEY (policy_id),
    CONSTRAINT policy_party_fk FOREIGN KEY (party_id) REFERENCES {catalog}.silver.party(party_id)
)
USING DELTA
CLUSTER BY (policy_id, effective_date)
COMMENT 'ACORD Policy entity - insurance policies';
```

---

### 3.3 Coverage Entity

**Purpose:** Represents coverage lines within a policy.

**Pydantic Model:**
```python
class CoverageType(str, Enum):
    """Coverage type."""
    LIABILITY = "liability"
    COLLISION = "collision"
    COMPREHENSIVE = "comprehensive"
    PROPERTY = "property"
    MEDICAL_PAYMENTS = "medical_payments"
    UNINSURED_MOTORIST = "uninsured_motorist"
    PERSONAL_INJURY = "personal_injury"

class Coverage(BaseModel):
    """
    ACORD Coverage entity.
    
    Attributes:
        coverage_id: Unique identifier (primary key)
        policy_id: Foreign key to Policy
        coverage_type: Type of coverage
        coverage_limit: Coverage limit amount
        deductible: Coverage-specific deductible
        premium: Coverage-specific premium
        currency: Currency code
        effective_date: Coverage effective date
        expiration_date: Coverage expiration date
        created_date: Record creation date
        updated_date: Record last update date
        source_system: Source system identifier
        source_coverage_id: Original coverage ID from source system
    """
    coverage_id: str
    policy_id: str  # FK to Policy
    coverage_type: CoverageType
    coverage_limit: float = Field(ge=0.0)
    deductible: Optional[float] = Field(default=None, ge=0.0)
    premium: float = Field(ge=0.0)
    currency: str = "USD"
    effective_date: date
    expiration_date: date
    created_date: date
    updated_date: date
    source_system: str
    source_coverage_id: str
    
    class Config:
        frozen = True
```

**Delta DDL:**
```sql
CREATE TABLE IF NOT EXISTS {catalog}.silver.coverage (
    coverage_id STRING NOT NULL COMMENT 'Unique coverage identifier',
    policy_id STRING NOT NULL COMMENT 'FK to Policy',
    coverage_type STRING NOT NULL COMMENT 'Type of coverage',
    coverage_limit DECIMAL(18,2) NOT NULL COMMENT 'Coverage limit',
    deductible DECIMAL(18,2) COMMENT 'Coverage deductible',
    premium DECIMAL(18,2) NOT NULL COMMENT 'Coverage premium',
    currency STRING NOT NULL COMMENT 'Currency code',
    effective_date DATE NOT NULL COMMENT 'Coverage effective date',
    expiration_date DATE NOT NULL COMMENT 'Coverage expiration date',
    created_date DATE NOT NULL COMMENT 'Record creation date',
    updated_date DATE NOT NULL COMMENT 'Record update date',
    source_system STRING NOT NULL COMMENT 'Source system identifier',
    source_coverage_id STRING NOT NULL COMMENT 'Original coverage ID from source',
    CONSTRAINT coverage_pk PRIMARY KEY (coverage_id),
    CONSTRAINT coverage_policy_fk FOREIGN KEY (policy_id) REFERENCES {catalog}.silver.policy(policy_id)
)
USING DELTA
CLUSTER BY (policy_id, coverage_id)
COMMENT 'ACORD Coverage entity - policy coverage lines';
```

---

### 3.4 Claim Entity

**Purpose:** Represents insurance claims.

**Pydantic Model:**
```python
class ClaimStatus(str, Enum):
    """Claim status."""
    OPEN = "open"
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    CLOSED = "closed"
    REOPENED = "reopened"

class ClaimType(str, Enum):
    """Claim type."""
    AUTO_LIABILITY = "auto_liability"
    AUTO_COLLISION = "auto_collision"
    PROPERTY_DAMAGE = "property_damage"
    THEFT = "theft"
    BODILY_INJURY = "bodily_injury"
    MEDICAL = "medical"
    WORKERS_COMP = "workers_comp"

class Claim(BaseModel):
    """
    ACORD Claim entity.
    
    Attributes:
        claim_id: Unique identifier (primary key)
        claim_number: Human-readable claim number
        policy_id: Foreign key to Policy
        coverage_id: Foreign key to Coverage
        claimant_id: Foreign key to Party (claimant)
        claim_type: Type of claim
        status: Claim status
        loss_date: Date of loss event
        report_date: Date claim was reported
        close_date: Date claim was closed (if closed)
        loss_location: Location of loss (address, lat/long)
        loss_description: Description of loss
        claim_amount: Total claimed amount
        paid_amount: Total amount paid (cumulative)
        reserved_amount: Amount reserved for claim
        currency: Currency code
        adjuster_id: Foreign key to Party (adjuster)
        created_date: Record creation date
        updated_date: Record last update date
        source_system: Source system identifier
        source_claim_id: Original claim ID from source system
    """
    claim_id: str
    claim_number: str
    policy_id: str  # FK to Policy
    coverage_id: Optional[str] = None  # FK to Coverage
    claimant_id: str  # FK to Party
    claim_type: ClaimType
    status: ClaimStatus
    loss_date: date
    report_date: date
    close_date: Optional[date] = None
    loss_location: Optional[str] = None
    loss_description: str
    claim_amount: float = Field(ge=0.0)
    paid_amount: float = Field(default=0.0, ge=0.0)
    reserved_amount: float = Field(default=0.0, ge=0.0)
    currency: str = "USD"
    adjuster_id: Optional[str] = None  # FK to Party
    created_date: date
    updated_date: date
    source_system: str
    source_claim_id: str
    
    class Config:
        frozen = True
```

**Delta DDL:**
```sql
CREATE TABLE IF NOT EXISTS {catalog}.silver.claim (
    claim_id STRING NOT NULL COMMENT 'Unique claim identifier',
    claim_number STRING NOT NULL COMMENT 'Human-readable claim number',
    policy_id STRING NOT NULL COMMENT 'FK to Policy',
    coverage_id STRING COMMENT 'FK to Coverage',
    claimant_id STRING NOT NULL COMMENT 'FK to Party (claimant)',
    claim_type STRING NOT NULL COMMENT 'Type of claim',
    status STRING NOT NULL COMMENT 'Claim status',
    loss_date DATE NOT NULL COMMENT 'Date of loss',
    report_date DATE NOT NULL COMMENT 'Date reported',
    close_date DATE COMMENT 'Date closed',
    loss_location STRING COMMENT 'Loss location',
    loss_description STRING NOT NULL COMMENT 'Loss description',
    claim_amount DECIMAL(18,2) NOT NULL COMMENT 'Claimed amount',
    paid_amount DECIMAL(18,2) NOT NULL COMMENT 'Paid amount (cumulative)',
    reserved_amount DECIMAL(18,2) NOT NULL COMMENT 'Reserved amount',
    currency STRING NOT NULL COMMENT 'Currency code',
    adjuster_id STRING COMMENT 'FK to Party (adjuster)',
    created_date DATE NOT NULL COMMENT 'Record creation date',
    updated_date DATE NOT NULL COMMENT 'Record update date',
    source_system STRING NOT NULL COMMENT 'Source system identifier',
    source_claim_id STRING NOT NULL COMMENT 'Original claim ID from source',
    CONSTRAINT claim_pk PRIMARY KEY (claim_id),
    CONSTRAINT claim_policy_fk FOREIGN KEY (policy_id) REFERENCES {catalog}.silver.policy(policy_id)
)
USING DELTA
CLUSTER BY (policy_id, claim_id, loss_date)
COMMENT 'ACORD Claim entity - insurance claims';
```

---

### 3.5 Payment Entity

**Purpose:** Represents premium payments and claim payouts.

**Pydantic Model:**
```python
class PaymentType(str, Enum):
    """Payment type."""
    PREMIUM = "premium"
    CLAIM_PAYOUT = "claim_payout"
    REFUND = "refund"
    ADJUSTMENT = "adjustment"

class PaymentMethod(str, Enum):
    """Payment method."""
    CASH = "cash"
    CHECK = "check"
    CREDIT_CARD = "credit_card"
    ACH = "ach"
    WIRE = "wire"

class PaymentStatus(str, Enum):
    """Payment status."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class Payment(BaseModel):
    """
    ACORD Payment entity.
    
    Attributes:
        payment_id: Unique identifier (primary key)
        payment_type: Premium or claim payout
        policy_id: Foreign key to Policy (for premiums)
        claim_id: Foreign key to Claim (for payouts)
        party_id: Foreign key to Party (payer or payee)
        amount: Payment amount
        currency: Currency code
        payment_date: Date of payment
        payment_method: Method of payment
        status: Payment status
        reference_number: External reference (check number, transaction ID)
        created_date: Record creation date
        updated_date: Record last update date
        source_system: Source system identifier
        source_payment_id: Original payment ID from source system
    """
    payment_id: str
    payment_type: PaymentType
    policy_id: Optional[str] = None  # FK to Policy (for premiums)
    claim_id: Optional[str] = None  # FK to Claim (for payouts)
    party_id: str  # FK to Party
    amount: float = Field(ge=0.0)
    currency: str = "USD"
    payment_date: date
    payment_method: PaymentMethod
    status: PaymentStatus
    reference_number: Optional[str] = None
    created_date: date
    updated_date: date
    source_system: str
    source_payment_id: str
    
    class Config:
        frozen = True
```

**Delta DDL:**
```sql
CREATE TABLE IF NOT EXISTS {catalog}.silver.payment (
    payment_id STRING NOT NULL COMMENT 'Unique payment identifier',
    payment_type STRING NOT NULL COMMENT 'Premium or claim payout',
    policy_id STRING COMMENT 'FK to Policy (premiums)',
    claim_id STRING COMMENT 'FK to Claim (payouts)',
    party_id STRING NOT NULL COMMENT 'FK to Party (payer/payee)',
    amount DECIMAL(18,2) NOT NULL COMMENT 'Payment amount',
    currency STRING NOT NULL COMMENT 'Currency code',
    payment_date DATE NOT NULL COMMENT 'Payment date',
    payment_method STRING NOT NULL COMMENT 'Payment method',
    status STRING NOT NULL COMMENT 'Payment status',
    reference_number STRING COMMENT 'External reference',
    created_date DATE NOT NULL COMMENT 'Record creation date',
    updated_date DATE NOT NULL COMMENT 'Record update date',
    source_system STRING NOT NULL COMMENT 'Source system identifier',
    source_payment_id STRING NOT NULL COMMENT 'Original payment ID from source',
    CONSTRAINT payment_pk PRIMARY KEY (payment_id),
    CONSTRAINT payment_policy_fk FOREIGN KEY (policy_id) REFERENCES {catalog}.silver.policy(policy_id),
    CONSTRAINT payment_claim_fk FOREIGN KEY (claim_id) REFERENCES {catalog}.silver.claim(claim_id)
)
USING DELTA
CLUSTER BY (policy_id, claim_id, payment_date)
COMMENT 'ACORD Payment entity - premium payments and claim payouts';
```

---

### 3.6 Loss Entity

**Purpose:** Represents loss events and reserves.

**Pydantic Model:**
```python
class LossType(str, Enum):
    """Loss type."""
    INCURRED = "incurred"
    PAID = "paid"
    RESERVED = "reserved"
    RECOVERED = "recovered"

class Loss(BaseModel):
    """
    ACORD Loss entity.
    
    Attributes:
        loss_id: Unique identifier (primary key)
        claim_id: Foreign key to Claim
        loss_type: Incurred, paid, reserved, or recovered
        loss_date: Date of loss transaction
        loss_amount: Loss amount
        currency: Currency code
        description: Loss description
        category: Loss category (indemnity, expense, etc.)
        created_date: Record creation date
        updated_date: Record last update date
        source_system: Source system identifier
        source_loss_id: Original loss ID from source system
    """
    loss_id: str
    claim_id: str  # FK to Claim
    loss_type: LossType
    loss_date: date
    loss_amount: float
    currency: str = "USD"
    description: Optional[str] = None
    category: Optional[str] = None  # "indemnity", "expense", "legal"
    created_date: date
    updated_date: date
    source_system: str
    source_loss_id: str
    
    class Config:
        frozen = True
```

**Delta DDL:**
```sql
CREATE TABLE IF NOT EXISTS {catalog}.silver.loss (
    loss_id STRING NOT NULL COMMENT 'Unique loss identifier',
    claim_id STRING NOT NULL COMMENT 'FK to Claim',
    loss_type STRING NOT NULL COMMENT 'Incurred/paid/reserved/recovered',
    loss_date DATE NOT NULL COMMENT 'Loss transaction date',
    loss_amount DECIMAL(18,2) NOT NULL COMMENT 'Loss amount',
    currency STRING NOT NULL COMMENT 'Currency code',
    description STRING COMMENT 'Loss description',
    category STRING COMMENT 'Loss category',
    created_date DATE NOT NULL COMMENT 'Record creation date',
    updated_date DATE NOT NULL COMMENT 'Record update date',
    source_system STRING NOT NULL COMMENT 'Source system identifier',
    source_loss_id STRING NOT NULL COMMENT 'Original loss ID from source',
    CONSTRAINT loss_pk PRIMARY KEY (loss_id),
    CONSTRAINT loss_claim_fk FOREIGN KEY (claim_id) REFERENCES {catalog}.silver.claim(claim_id)
)
USING DELTA
CLUSTER BY (claim_id, loss_date)
COMMENT 'ACORD Loss entity - loss events and reserves';
```

---

## 4. Transformation Guidelines

### 4.1 Bronze to Silver Mapping
* **Source system IDs** — always preserved in `source_system` + `source_*_id` fields
* **Data quality** — apply DQ checks before writing to Silver (see `dq-engine-spec.md`)
* **Standardization** — apply ACORD UDFs for field transformations (dates, phone formats, addresses)
* **Deduplication** — SCD2 strategy for historical tracking

### 4.2 ACORD UDFs (see `dataio/transform/transform-builders-spec.md`)
* **`acord_standardize_phone(raw_phone)`** — format phone to ACORD standard
* **`acord_standardize_address(address_dict)`** — normalize address fields
* **`acord_parse_policy_number(raw_policy_num)`** — extract policy number components

---

## 5. References

### 5.1 Internal Documents
* `metadata-models-spec.md` — metadata model definitions
* `PROJECT_CONTEXT.md` §4 — ACORD canonical requirement
* ACORD P&C standards — https://www.acord.org/

### 5.2 External Standards
* **ACORD AL3** — ACORD Library 3.0 data model
* **ISO 3166** — Country codes
* **ISO 4217** — Currency codes
* **ISO 639** — Language codes

---

**End of ACORD Canonical Schema**
